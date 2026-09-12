"""Axisymmetric shallow-layer finite-volume solver.

The equations and friction terms follow Dienhart, JUEL-3155 (1995),
equations 4.2--4.3 and 4.18--4.22.  This implementation uses conservative
radial finite volumes and a Rusanov flux instead of the report's historical
forward-difference discretisation. Source mass is injected with zero radial
momentum. Evaporation momentum coupling is applied by the calling model.
"""

from __future__ import annotations

from dataclasses import dataclass
import math

import numpy as np


@dataclass(frozen=True)
class ShallowLayerNumerics:
    """Numerical and front-observation settings, all in SI units."""

    domain_radius_m: float = 10.0
    radial_step_m: float = 0.02
    maximum_time_step_s: float = 0.01
    cfl: float = 0.2
    chezy_coefficient: float = 1.0e-3
    source_inner_radius_m: float = 0.0
    source_radius_m: float = 0.25
    surface_retention_depth_m: float = 0.0
    dry_depth_m: float = 1.0e-8
    reported_front_depth_m: float = 7.5e-4

    def __post_init__(self) -> None:
        positive = (
            ("domain_radius_m", self.domain_radius_m),
            ("radial_step_m", self.radial_step_m),
            ("maximum_time_step_s", self.maximum_time_step_s),
            ("cfl", self.cfl),
            ("source_radius_m", self.source_radius_m),
            ("dry_depth_m", self.dry_depth_m),
            ("reported_front_depth_m", self.reported_front_depth_m),
        )
        for name, value in positive:
            if not math.isfinite(value) or value <= 0.0:
                raise ValueError(f"{name} must be finite and > 0")
        if self.domain_radius_m <= self.source_radius_m:
            raise ValueError("domain_radius_m must exceed source_radius_m")
        if (not math.isfinite(self.source_inner_radius_m)
                or self.source_inner_radius_m < 0.0
                or self.source_inner_radius_m >= self.source_radius_m):
            raise ValueError("source_inner_radius_m must be finite and in [0, source_radius_m)")
        if not 0.0 < self.cfl <= 0.5:
            raise ValueError("cfl must be in (0, 0.5]")
        if not math.isfinite(self.chezy_coefficient) or self.chezy_coefficient < 0.0:
            raise ValueError("chezy_coefficient must be finite and >= 0")
        if (not math.isfinite(self.surface_retention_depth_m)
                or self.surface_retention_depth_m < 0.0):
            raise ValueError(
                "surface_retention_depth_m must be finite and >= 0"
            )


@dataclass
class ShallowLayerState:
    """Internal radial-cell state."""

    depth_m: np.ndarray
    momentum_m2_s: np.ndarray
    cumulative_contact_age_s: np.ndarray


def radial_grid(numerics: ShallowLayerNumerics) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    count = int(math.ceil(numerics.domain_radius_m / numerics.radial_step_m))
    faces = np.arange(count + 1, dtype=float) * numerics.radial_step_m
    centres = (np.arange(count, dtype=float) + 0.5) * numerics.radial_step_m
    annular_areas = math.pi * (faces[1:] ** 2 - faces[:-1] ** 2)
    return centres, faces, annular_areas


def normalised_central_source(
    centres_m: np.ndarray,
    annular_areas_m2: np.ndarray,
    source_radius_m: float,
    source_inner_radius_m: float = 0.0,
) -> np.ndarray:
    """Return a unit-integral disk or annular source profile [m-2].

    A zero inner radius gives the parabolic central source used by Dienhart.
    A positive inner radius gives a uniform annulus for an explicitly declared
    overflow lip or ring distributor.
    """
    if source_inner_radius_m == 0.0:
        shape = np.maximum(0.0, 1.0 - (centres_m / source_radius_m) ** 2)
    else:
        shape = (
            (centres_m >= source_inner_radius_m)
            & (centres_m <= source_radius_m)
        ).astype(float)
    integral = float(np.dot(shape, annular_areas_m2))
    if integral <= 0.0:
        raise ValueError("source radius is unresolved by radial grid")
    return shape / integral


def stable_step_s(
    state: ShallowLayerState,
    numerics: ShallowLayerNumerics,
    reduced_gravity_m_s2: float,
) -> float:
    h = state.depth_m
    mobile_h = np.maximum(h - numerics.surface_retention_depth_m, 0.0)
    velocity = np.divide(
        state.momentum_m2_s,
        mobile_h,
        out=np.zeros_like(h),
        where=mobile_h > numerics.dry_depth_m,
    )
    wave_speed = np.sqrt(np.maximum(0.0, reduced_gravity_m_s2 * mobile_h))
    maximum = float(np.max(np.abs(velocity) + wave_speed))
    if maximum <= 1.0e-12:
        return numerics.maximum_time_step_s
    return min(
        numerics.maximum_time_step_s,
        numerics.cfl * numerics.radial_step_m / maximum,
    )


def advect_and_accelerate(
    state: ShallowLayerState,
    dt_s: float,
    centres_m: np.ndarray,
    faces_m: np.ndarray,
    reduced_gravity_m_s2: float,
    liquid_kinematic_viscosity_m2_s: float,
    numerics: ShallowLayerNumerics,
) -> tuple[np.ndarray, np.ndarray, float, float]:
    """Advance flow and return boundary loss plus signed positivity correction.

    Positive depths below ``dry_depth_m`` remain in the conserved inventory;
    only their momentum is suppressed. If the first-order update creates a
    negative depth, clipping adds volume. That signed addition is returned so
    the public mass ledger cannot silently hide the numerical correction.
    """
    h = state.depth_m
    mobile_h = np.maximum(h - numerics.surface_retention_depth_m, 0.0)
    momentum = state.momentum_m2_s
    velocity = np.divide(
        momentum,
        mobile_h,
        out=np.zeros_like(h),
        where=mobile_h > numerics.dry_depth_m,
    )
    count = len(h)
    mass_flux = np.zeros(count + 1)
    momentum_flux = np.zeros(count + 1)
    if count > 1:
        h_left, h_right = mobile_h[:-1], mobile_h[1:]
        m_left, m_right = momentum[:-1], momentum[1:]
        u_left, u_right = velocity[:-1], velocity[1:]
        signal = np.maximum(
            np.abs(u_left) + np.sqrt(reduced_gravity_m_s2 * h_left),
            np.abs(u_right) + np.sqrt(reduced_gravity_m_s2 * h_right),
        )
        mass_flux[1:count] = 0.5 * (m_left + m_right) - 0.5 * signal * (h_right - h_left)
        momentum_flux[1:count] = 0.5 * (
            m_left * u_left + 0.5 * reduced_gravity_m_s2 * h_left**2
            + m_right * u_right + 0.5 * reduced_gravity_m_s2 * h_right**2
        ) - 0.5 * signal * (m_right - m_left)
    outer_signal = abs(velocity[-1]) + math.sqrt(
        reduced_gravity_m_s2 * mobile_h[-1]
    )
    mass_flux[-1] = (
        0.5 * momentum[-1] + 0.5 * outer_signal * mobile_h[-1]
    )
    momentum_flux[-1] = 0.5 * (
        momentum[-1] * velocity[-1]
        + 0.5 * reduced_gravity_m_s2 * mobile_h[-1] ** 2
    ) + 0.5 * outer_signal * momentum[-1]
    dr = numerics.radial_step_m
    new_h = h - dt_s / (centres_m * dr) * (
        faces_m[1:] * mass_flux[1:] - faces_m[:-1] * mass_flux[:-1]
    )
    new_momentum = momentum - dt_s / (centres_m * dr) * (
        faces_m[1:] * momentum_flux[1:] - faces_m[:-1] * momentum_flux[:-1]
    )
    new_momentum += (
        dt_s * 0.5 * reduced_gravity_m_s2 * mobile_h**2 / centres_m
    )
    escaped_volume_m3 = max(0.0, 2.0 * math.pi * faces_m[-1] * mass_flux[-1] * dt_s)

    negative = new_h < 0.0
    annular_areas_m2 = math.pi * (faces_m[1:] ** 2 - faces_m[:-1] ** 2)
    numerical_volume_adjustment_m3 = float(
        np.dot(np.maximum(-new_h, 0.0), annular_areas_m2)
    )
    new_h[negative] = 0.0
    new_momentum[negative] = 0.0
    new_mobile_h = np.maximum(
        new_h - numerics.surface_retention_depth_m, 0.0
    )
    new_velocity = np.divide(
        new_momentum,
        new_mobile_h,
        out=np.zeros_like(new_h),
        where=new_mobile_h > 0.0,
    )
    damping = 1.0 + dt_s * (
        numerics.chezy_coefficient * np.abs(new_velocity)
        / np.maximum(new_mobile_h, numerics.dry_depth_m)
        + liquid_kinematic_viscosity_m2_s
        / np.maximum(new_mobile_h, numerics.dry_depth_m) ** 2
    )
    new_momentum = new_mobile_h * new_velocity / damping
    new_momentum[new_mobile_h <= numerics.dry_depth_m] = 0.0
    return (
        new_h,
        new_momentum,
        escaped_volume_m3,
        numerical_volume_adjustment_m3,
    )
