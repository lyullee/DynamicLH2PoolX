"""DynamicLH2PoolX Stage-B fixed-area dynamic LH2 pool mass-balance route.

This module intentionally does not implement a spreading closure.  It is a
bounded-pool numerical and heat-transfer component of the dynamic route.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
import math
from typing import Any

import CoolProp.CoolProp as CP

from .inflow import DeclaredInflow
from .conduction import ConductionCapacity
from .pool import (
    CONCRETE_CRYOGENIC,
    CRITICAL_HEAT_FLUX_W_M2,
    Substrate,
    _ground_flux,
)


@dataclass(frozen=True)
class FixedAreaPoolConfig:
    """Inputs to the bounded fixed-area dynamic route.

    Units: ``area_m2`` [m2], ``initial_liquid_mass_kg`` [kg],
    ``ambient_temperature_K`` [K], ``ambient_pressure_Pa`` [Pa], and
    ``critical_heat_flux_W_m2`` [W m-2] when supplied.  ``substrate`` is a
    solid closure only; water, ice and RPT are outside this route.
    """

    area_m2: float
    initial_liquid_mass_kg: float = 0.0
    substrate: Substrate = CONCRETE_CRYOGENIC
    ambient_temperature_K: float = 282.0
    ambient_pressure_Pa: float = 101325.0
    critical_heat_flux_W_m2: float | None = CRITICAL_HEAT_FLUX_W_M2
    initial_thermal_age_s: float = 0.0

    def __post_init__(self) -> None:
        if not math.isfinite(self.initial_thermal_age_s) or self.initial_thermal_age_s < 0:
            raise ValueError("initial_thermal_age_s must be finite and >= 0")
        for name, value in (
            ("area_m2", self.area_m2),
            ("ambient_temperature_K", self.ambient_temperature_K),
            ("ambient_pressure_Pa", self.ambient_pressure_Pa),
        ):
            if not math.isfinite(value) or value <= 0.0:
                raise ValueError(f"{name} must be finite and > 0")
        if (not math.isfinite(self.initial_liquid_mass_kg) or
                self.initial_liquid_mass_kg < 0.0):
            raise ValueError("initial_liquid_mass_kg must be finite and >= 0")
        if self.critical_heat_flux_W_m2 is not None and (
            not math.isfinite(self.critical_heat_flux_W_m2)
            or self.critical_heat_flux_W_m2 <= 0.0
        ):
            raise ValueError("critical_heat_flux_W_m2 must be finite and > 0 or None")


@dataclass(frozen=True)
class FixedAreaPoolLedger:
    """One time-indexed fixed-area pool record; every field uses SI units.

    Time [s], liquid inflow rate [kg s-1], cumulative inflow [kg], liquid mass
    [kg], radius [m], area [m2], mean depth [m], pool temperature [K], liquid
    density [kg m-3], substrate heat flux [W m-2], evaporation flux
    [kg m-2 s-1], evaporation rate [kg s-1], and accumulated evaporation [kg].
    """

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
    heat_transfer_closure_id: str
    spreading_closure_id: str
    source_status: str
    warning: str | None


@dataclass(frozen=True)
class FixedAreaPoolResult:
    """Serializable result for a fixed-area simulation.

    ``ledger`` contains one record per requested output time.  The source is
    ``within_declared_scope`` only for an explicitly declared liquid-to-ground
    inflow on the stated solid, level, homogeneous, fixed-area pool.
    """

    ledger: tuple[FixedAreaPoolLedger, ...]
    mass_balance_residual_kg: float
    solver_id: str = "fixed_area_exact_reflected_v2"
    disappearance_times_s: tuple[float, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        """Return a JSON-serialisable representation without loss of units."""
        return asdict(self)

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "FixedAreaPoolResult":
        """Reload a result previously produced by :meth:`to_dict`."""
        return cls(
            ledger=tuple(FixedAreaPoolLedger(**item) for item in payload["ledger"]),
            mass_balance_residual_kg=payload["mass_balance_residual_kg"],
            solver_id=payload.get("solver_id", "fixed_area_exact_reflected_v2"),
            disappearance_times_s=tuple(payload.get("disappearance_times_s", ())),
        )


def run_fixed_area_pool(
    config: FixedAreaPoolConfig,
    inflow: DeclaredInflow,
    output_times_s: tuple[float, ...],
) -> FixedAreaPoolResult:
    """Integrate a declared inflow and heat-limited evaporation on fixed area.

    Integrates min(C/sqrt(thermal_age), cap) analytically, with continuous
    mass reflection at zero and bracketed disappearance events (80 bisections).
    Inflow changes are internal integration boundaries. Output spacing does
    not control numerical accuracy. Thermal age starts at initial_thermal_age_s;
    dry-surface reheating is excluded. A post-fill window must declare its
    pre-existing cooling age instead of restarting substrate conduction.
    Ledger fluxes are instantaneous; cumulative columns are integrals. With
    an uncapped singular initial flux, its initial sample is set to zero and
    flagged in the warning; the integral still includes the singular start.
    This numerical route is not a spreading model and has no water-surface
    closure or experimental validation claim.
    """
    _validate_output_times(output_times_s)
    temperature = float(CP.PropsSI("T", "P", config.ambient_pressure_Pa, "Q", 0, "Hydrogen"))
    density = float(CP.PropsSI("D", "P", config.ambient_pressure_Pa, "Q", 0, "Hydrogen"))
    latent_heat = float(
        CP.PropsSI("H", "P", config.ambient_pressure_Pa, "Q", 1, "Hydrogen")
        - CP.PropsSI("H", "P", config.ambient_pressure_Pa, "Q", 0, "Hydrogen")
    )
    radius = math.sqrt(config.area_m2 / math.pi)
    mass = config.initial_liquid_mass_kg
    cumulative_inflow = 0.0
    cumulative_evaporation = 0.0
    coefficient = (config.area_m2 * config.substrate.conductivity_W_mK
                   * max(0.0, config.ambient_temperature_K - temperature)
                   / (latent_heat * math.sqrt(math.pi * config.substrate.diffusivity_m2_s)))
    cap = (config.area_m2 * config.critical_heat_flux_W_m2 / latent_heat
           if config.critical_heat_flux_W_m2 is not None else math.inf)
    capacity = ConductionCapacity(coefficient, cap)
    offset = config.initial_thermal_age_s
    ledger, events = [], []
    boundaries = sorted(set(output_times_s) | {t for t in inflow.times_s if t < output_times_s[-1]})
    previous = 0.0
    requested = set(output_times_s)
    for t in boundaries:
        if t > previous:
            added = inflow.rate_at(previous) * (t - previous)
            next_mass, empty_age = capacity.advance(mass, inflow.rate_at(previous), previous + offset, t + offset)
            cumulative_evaporation += mass + added - next_mass
            cumulative_inflow += added
            mass = next_mass
            if empty_age is not None:
                events.append(empty_age - offset)
        if t in requested:
            potential = capacity.rate(t + offset)
            actual = potential if mass > 0 else min(potential, inflow.rate_at(t))
            if not math.isfinite(actual):
                actual = 0.0
            flux = actual / config.area_m2
            ledger.append(_record(t, inflow.rate_at(t), cumulative_inflow, mass, radius,
                                  config.area_m2, temperature, density, flux * latent_heat,
                                  flux, actual, cumulative_evaporation))
        previous = t
    residual = config.initial_liquid_mass_kg + cumulative_inflow - cumulative_evaporation - mass
    return FixedAreaPoolResult(tuple(ledger), residual, disappearance_times_s=tuple(events))


def _validate_output_times(output_times_s: tuple[float, ...]) -> None:
    if len(output_times_s) < 2:
        raise ValueError("output_times_s must contain at least 0 s and one later time")
    if output_times_s[0] != 0.0:
        raise ValueError("the first output time must be 0 s")
    if any(not math.isfinite(value) or value < 0.0 for value in output_times_s):
        raise ValueError("output_times_s must be finite and >= 0")
    if any(right <= left for left, right in zip(output_times_s, output_times_s[1:])):
        raise ValueError("output_times_s must be strictly increasing")


def _record(time_s: float, inflow_rate: float, cumulative_inflow: float, mass: float,
            radius: float, area: float, temperature: float, density: float, heat_flux: float,
            evaporation_flux: float, evaporation_rate: float,
            cumulative_evaporation: float) -> FixedAreaPoolLedger:
    source_status = (
        "input_limited" if mass == 0.0 and inflow_rate == 0.0 else
        "within_declared_scope"
    )
    return FixedAreaPoolLedger(
        time_s=time_s,
        liquid_inflow_rate_kg_s=inflow_rate,
        cumulative_inflow_kg=cumulative_inflow,
        liquid_mass_kg=mass,
        radius_m=radius,
        area_m2=area,
        mean_depth_m=mass / (density * area),
        pool_temperature_K=temperature,
        liquid_density_kg_m3=density,
        substrate_heat_flux_W_m2=heat_flux,
        evaporation_flux_kg_m2_s=evaporation_flux,
        evaporation_rate_kg_s=evaporation_rate,
        cumulative_evaporation_kg=cumulative_evaporation,
        heat_transfer_closure_id="solid_semi_infinite_conduction_v01",
        spreading_closure_id="fixed_area_no_spreading_v1",
        source_status=source_status,
        warning="experimental fixed-area closure; continuous thermal-age assumption; no dry-surface reheating; uncapped initial singular flux sample stored as 0; no experimental pass implied",
    )
