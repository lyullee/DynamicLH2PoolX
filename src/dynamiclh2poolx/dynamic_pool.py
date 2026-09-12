"""Coupled axisymmetric spreading, evaporation, and mass-balance route."""

from __future__ import annotations

from dataclasses import asdict, dataclass
import math
import platform
from typing import Any, Literal

import CoolProp.CoolProp as CP
import numpy as np

from .inflow import DeclaredInflow
from .spreading import (
    ShallowLayerNumerics,
    ShallowLayerState,
    advect_and_accelerate,
    normalised_central_source,
    radial_grid,
    stable_step_s,
)
from .substrates import ConstantHeatFluxWaterSurface, SolidSemiInfiniteSurface

DynamicSurface = SolidSemiInfiniteSurface | ConstantHeatFluxWaterSurface
EvaporationMomentumClosure = Literal[
    "zero_radial_momentum_vapor",
    "liquid_velocity_carryoff",
]


@dataclass(frozen=True)
class DynamicPoolConfig:
    """Configuration for an unconfined horizontal axisymmetric pool."""

    surface: DynamicSurface
    numerics: ShallowLayerNumerics = ShallowLayerNumerics()
    ambient_pressure_Pa: float = 101325.0
    initial_liquid_mass_kg: float = 0.0
    evaporation_momentum_closure: EvaporationMomentumClosure = (
        "zero_radial_momentum_vapor"
    )

    def __post_init__(self) -> None:
        if not isinstance(
            self.surface,
            (SolidSemiInfiniteSurface, ConstantHeatFluxWaterSurface),
        ):
            raise TypeError(
                "surface must be SolidSemiInfiniteSurface or "
                "ConstantHeatFluxWaterSurface"
            )
        if not math.isfinite(self.ambient_pressure_Pa) or self.ambient_pressure_Pa <= 0.0:
            raise ValueError("ambient_pressure_Pa must be finite and > 0")
        if not math.isfinite(self.initial_liquid_mass_kg) or self.initial_liquid_mass_kg < 0.0:
            raise ValueError("initial_liquid_mass_kg must be finite and >= 0")
        if self.initial_liquid_mass_kg:
            raise ValueError("initial inventory is not yet supported by the spreading route")
        if self.evaporation_momentum_closure not in (
            "zero_radial_momentum_vapor",
            "liquid_velocity_carryoff",
        ):
            raise ValueError("unsupported evaporation_momentum_closure")


@dataclass(frozen=True)
class DynamicPoolLedger:
    time_s: float
    liquid_inflow_rate_kg_s: float
    cumulative_inflow_kg: float
    liquid_mass_kg: float
    radius_m: float
    area_m2: float
    mean_depth_m: float
    pool_temperature_K: float
    liquid_density_kg_m3: float
    substrate_heat_flux_W_m2: float
    evaporation_flux_kg_m2_s: float
    evaporation_rate_kg_s: float
    cumulative_evaporation_kg: float
    escaped_domain_mass_kg: float
    heat_transfer_closure_id: str
    spreading_closure_id: str
    source_status: str
    warning: str | None
    cumulative_numerical_mass_adjustment_kg: float = 0.0
    unledgered_mass_residual_kg: float = 0.0
    wet_area_m2: float = 0.0
    reported_radius_m: float = 0.0
    reported_area_m2: float = 0.0
    wet_area_mean_depth_m: float = 0.0
    wet_area_mean_evaporation_flux_kg_m2_s: float = 0.0
    interval_mean_evaporation_rate_kg_s: float = 0.0
    last_substep_evaporation_rate_kg_s: float = 0.0
    evaporation_momentum_closure: str = "zero_radial_momentum_vapor"


@dataclass(frozen=True)
class DynamicPoolResult:
    ledger: tuple[DynamicPoolLedger, ...]
    mass_balance_residual_kg: float
    solver_id: str = "axisymmetric_rusanov_shallow_layer_v1"
    configuration_echo: dict[str, Any] | None = None
    software_versions: dict[str, str] | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "DynamicPoolResult":
        return cls(
            ledger=tuple(DynamicPoolLedger(**row) for row in payload["ledger"]),
            mass_balance_residual_kg=payload["mass_balance_residual_kg"],
            solver_id=payload.get("solver_id", "axisymmetric_rusanov_shallow_layer_v1"),
            configuration_echo=payload.get("configuration_echo"),
            software_versions=payload.get("software_versions"),
        )


def run_dynamic_pool(
    config: DynamicPoolConfig,
    inflow: DeclaredInflow,
    output_times_s: tuple[float, ...],
) -> DynamicPoolResult:
    """Run the cited shallow-layer route for a declared ground-inflow history."""
    _validate_times(output_times_s)
    pressure = config.ambient_pressure_Pa
    try:
        saturation_temperature = float(
            CP.PropsSI("T", "P", pressure, "Q", 0, "Hydrogen")
        )
        liquid_density = float(
            CP.PropsSI("D", "P", pressure, "Q", 0, "Hydrogen")
        )
        liquid_viscosity = float(
            CP.PropsSI("V", "P", pressure, "Q", 0, "Hydrogen")
        )
        latent_heat = float(
            CP.PropsSI("H", "P", pressure, "Q", 1, "Hydrogen")
            - CP.PropsSI("H", "P", pressure, "Q", 0, "Hydrogen")
        )
    except Exception as exc:
        raise ValueError(
            "ambient_pressure_Pa is outside the CoolProp hydrogen "
            "saturation-property range"
        ) from exc
    kinematic_viscosity = liquid_viscosity / liquid_density
    density_factor = (
        1.0 - liquid_density / 1000.0
        if isinstance(config.surface, ConstantHeatFluxWaterSurface)
        else 1.0
    )
    reduced_gravity = 9.80665 * density_factor
    centres, faces, annular_areas = radial_grid(config.numerics)
    source_shape = normalised_central_source(
        centres, annular_areas, config.numerics.source_radius_m,
        config.numerics.source_inner_radius_m,
    )
    if isinstance(config.surface, SolidSemiInfiniteSurface):
        solid_coefficient = (
            config.surface.conductivity_W_mK
            * max(0.0, config.surface.initial_temperature_K - saturation_temperature)
            * config.surface.heat_flux_multiplier
            / (liquid_density * latent_heat
               * math.sqrt(math.pi * config.surface.diffusivity_m2_s))
        )
        solid_cap = (
            config.surface.heat_flux_cap_W_m2 / (liquid_density * latent_heat)
            if config.surface.heat_flux_cap_W_m2 is not None else None
        )
    else:
        solid_coefficient = None
        solid_cap = None
    state = ShallowLayerState(
        depth_m=np.zeros_like(centres),
        momentum_m2_s=np.zeros_like(centres),
        cumulative_contact_age_s=np.zeros_like(centres),
    )
    time_s = 0.0
    cumulative_inflow = 0.0
    cumulative_evaporation = 0.0
    escaped_mass = 0.0
    cumulative_numerical_adjustment = 0.0
    last_evaporation_rate = 0.0
    ledger: list[DynamicPoolLedger] = []
    for target_time in output_times_s:
        interval_start_time = ledger[-1].time_s if ledger else target_time
        interval_start_evaporation = (
            ledger[-1].cumulative_evaporation_kg if ledger else cumulative_evaporation
        )
        while time_s < target_time - 1.0e-12:
            dt = min(
                stable_step_s(state, config.numerics, reduced_gravity),
                target_time - time_s,
            )
            rate = inflow.rate_at(time_s)
            next_change = next((x for x in inflow.times_s if x > time_s + 1.0e-12), None)
            if next_change is not None:
                dt = min(dt, next_change - time_s)
            new_h, new_momentum, escaped_volume, numerical_volume_adjustment = (
                advect_and_accelerate(
                state, dt, centres, faces, reduced_gravity, kinematic_viscosity,
                config.numerics,
                )
            )
            cumulative_numerical_adjustment += (
                numerical_volume_adjustment * liquid_density
            )
            new_h += (rate / liquid_density) * source_shape * dt
            attempted_contact = new_h > config.numerics.dry_depth_m
            old_age = state.cumulative_contact_age_s.copy()
            new_age = old_age.copy()
            new_age[attempted_contact] += dt
            evaporation_capacity = np.zeros_like(new_h)
            if isinstance(config.surface, ConstantHeatFluxWaterSurface):
                evaporation_capacity[attempted_contact] = (
                    config.surface.heat_flux_W_m2 * dt / (liquid_density * latent_heat)
                )
            elif solid_cap is None:
                evaporation_capacity[attempted_contact] = 2.0 * solid_coefficient * (
                    np.sqrt(new_age[attempted_contact]) - np.sqrt(old_age[attempted_contact])
                )
            else:
                switch_age = (solid_coefficient / solid_cap) ** 2
                capped_duration = np.maximum(
                    0.0,
                    np.minimum(new_age, switch_age) - np.minimum(old_age, switch_age),
                )
                conduction_start = np.maximum(old_age, switch_age)
                conduction = np.where(
                    new_age > conduction_start,
                    2.0 * solid_coefficient * (
                        np.sqrt(new_age) - np.sqrt(conduction_start)
                    ),
                    0.0,
                )
                evaporation_capacity[attempted_contact] = (
                    solid_cap * capped_duration[attempted_contact]
                    + conduction[attempted_contact]
                )
            depth_before_evaporation = new_h.copy()
            evaporated_depth = np.minimum(
                evaporation_capacity, np.maximum(new_h, 0.0)
            )
            new_h -= evaporated_depth
            if config.evaporation_momentum_closure == "liquid_velocity_carryoff":
                remaining_fraction = np.divide(
                    new_h,
                    depth_before_evaporation,
                    out=np.zeros_like(new_h),
                    where=depth_before_evaporation > 0.0,
                )
                new_momentum *= remaining_fraction
            mobile_depth = np.maximum(
                new_h - config.numerics.surface_retention_depth_m,
                0.0,
            )
            new_momentum[mobile_depth <= config.numerics.dry_depth_m] = 0.0
            evaporated_mass = float(np.dot(evaporated_depth, annular_areas) * liquid_density)
            cumulative_inflow += rate * dt
            cumulative_evaporation += evaporated_mass
            escaped_mass += escaped_volume * liquid_density
            last_evaporation_rate = evaporated_mass / dt
            state = ShallowLayerState(new_h, new_momentum, new_age)
            time_s += dt
        interval_duration = target_time - interval_start_time
        interval_mean_evaporation_rate = (
            (cumulative_evaporation - interval_start_evaporation) / interval_duration
            if interval_duration > 0.0 else 0.0
        )
        ledger.append(_ledger_record(
            target_time, inflow.rate_at(target_time), cumulative_inflow,
            cumulative_evaporation, escaped_mass, cumulative_numerical_adjustment,
            interval_mean_evaporation_rate, last_evaporation_rate, state,
            faces, annular_areas, saturation_temperature, liquid_density, latent_heat,
            config,
        ))
    final_mass = ledger[-1].liquid_mass_kg
    residual = (
        config.initial_liquid_mass_kg
        + cumulative_inflow
        + cumulative_numerical_adjustment
        - (
        cumulative_evaporation + escaped_mass + final_mass
        )
    )
    return DynamicPoolResult(
        tuple(ledger),
        residual,
        solver_id="axisymmetric_rusanov_shallow_layer_v2",
        configuration_echo={
            "surface_type": type(config.surface).__name__,
            "surface": asdict(config.surface),
            "numerics": asdict(config.numerics),
            "ambient_pressure_Pa": config.ambient_pressure_Pa,
            "initial_liquid_mass_kg": config.initial_liquid_mass_kg,
            "evaporation_momentum_closure": (
                config.evaporation_momentum_closure
            ),
            "inflow": asdict(inflow),
            "output_times_s": list(output_times_s),
        },
        software_versions={
            "python": platform.python_version(),
            "numpy": np.__version__,
            "coolprop": CP.get_global_param_string("version"),
        },
    )


def _ledger_record(
    time_s: float,
    inflow_rate: float,
    cumulative_inflow: float,
    cumulative_evaporation: float,
    escaped_mass: float,
    cumulative_numerical_adjustment: float,
    interval_mean_evaporation_rate: float,
    last_substep_evaporation_rate: float,
    state: ShallowLayerState,
    faces: np.ndarray,
    annular_areas: np.ndarray,
    temperature: float,
    density: float,
    latent_heat: float,
    config: DynamicPoolConfig,
) -> DynamicPoolLedger:
    mass = float(np.dot(state.depth_m, annular_areas) * density)
    wet = state.depth_m > 0.0
    wet_area = float(np.sum(annular_areas[wet]))
    detected = np.flatnonzero(state.depth_m >= config.numerics.reported_front_depth_m)
    radius = float(faces[detected[-1] + 1]) if len(detected) else 0.0
    area = math.pi * radius**2
    mean_depth = mass / (density * wet_area) if wet_area > 0.0 else 0.0
    evaporation_flux = (
        interval_mean_evaporation_rate / wet_area if wet_area > 0.0 else 0.0
    )
    unledgered_residual = (
        config.initial_liquid_mass_kg
        + cumulative_inflow
        + cumulative_numerical_adjustment
        - cumulative_evaporation
        - escaped_mass
        - mass
    )
    boundary_warning = escaped_mass > 1.0e-9
    handled_mass = max(
        config.initial_liquid_mass_kg + cumulative_inflow,
        cumulative_evaporation + escaped_mass + mass,
        1.0e-30,
    )
    numerical_adjustment_significant = abs(cumulative_numerical_adjustment) > max(
        1.0e-12, 1.0e-10 * handled_mass
    )
    if isinstance(config.surface, ConstantHeatFluxWaterSurface):
        warning = (
            "water heat flux is a limited empirical 50-60 s closure; ice growth, "
            "waves, pool-front pulsation and detached floes are unresolved"
        )
    else:
        warning = (
            "solid heat transfer uses cumulative local contact age; film/nucleate "
            "boiling, reheating and horizontal substrate conduction are unresolved"
        )
        if config.surface.heat_flux_multiplier != 1.0:
            warning += (
                f"; limited empirical heat-flux multiplier="
                f"{config.surface.heat_flux_multiplier:g}"
            )
    if boundary_warning:
        warning += "; liquid reached the numerical domain boundary"
    if config.numerics.surface_retention_depth_m > 0.0:
        warning += (
            "; surface-retention depth is a declared roughness/puddle closure="
            f"{config.numerics.surface_retention_depth_m:g} m"
        )
    if numerical_adjustment_significant:
        warning += (
            "; positivity clipping required an explicitly ledgered numerical "
            f"mass adjustment={cumulative_numerical_adjustment:.6g} kg"
        )
    return DynamicPoolLedger(
        time_s=time_s,
        liquid_inflow_rate_kg_s=inflow_rate,
        cumulative_inflow_kg=cumulative_inflow,
        liquid_mass_kg=mass,
        radius_m=radius,
        area_m2=area,
        mean_depth_m=mean_depth,
        pool_temperature_K=temperature,
        liquid_density_kg_m3=density,
        substrate_heat_flux_W_m2=evaporation_flux * latent_heat,
        evaporation_flux_kg_m2_s=evaporation_flux,
        evaporation_rate_kg_s=interval_mean_evaporation_rate,
        cumulative_evaporation_kg=cumulative_evaporation,
        escaped_domain_mass_kg=escaped_mass,
        heat_transfer_closure_id=config.surface.closure_id,
        spreading_closure_id=(
            "dienhart_shallow_layer_rusanov_retention_v2"
            if config.numerics.surface_retention_depth_m > 0.0
            else "dienhart_shallow_layer_rusanov_v2"
        ),
        source_status="out_of_scope" if boundary_warning else (
            "numerically_adjusted" if numerical_adjustment_significant else (
            "input_limited" if mass == 0.0 and inflow_rate == 0.0 else "within_declared_scope"
            )
        ),
        warning=warning,
        cumulative_numerical_mass_adjustment_kg=cumulative_numerical_adjustment,
        unledgered_mass_residual_kg=unledgered_residual,
        wet_area_m2=wet_area,
        reported_radius_m=radius,
        reported_area_m2=area,
        wet_area_mean_depth_m=mean_depth,
        wet_area_mean_evaporation_flux_kg_m2_s=evaporation_flux,
        interval_mean_evaporation_rate_kg_s=interval_mean_evaporation_rate,
        last_substep_evaporation_rate_kg_s=last_substep_evaporation_rate,
        evaporation_momentum_closure=config.evaporation_momentum_closure,
    )


def _validate_times(times: tuple[float, ...]) -> None:
    if len(times) < 2 or times[0] != 0.0:
        raise ValueError("output_times_s must start at 0 and contain a later time")
    if any(not math.isfinite(x) or x < 0.0 for x in times):
        raise ValueError("output times must be finite and non-negative")
    if any(b <= a for a, b in zip(times, times[1:])):
        raise ValueError("output times must be strictly increasing")
