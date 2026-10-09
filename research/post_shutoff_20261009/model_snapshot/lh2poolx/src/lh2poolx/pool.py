"""Quasi-steady LH2 pool source terms with explicit evidence boundaries."""

from __future__ import annotations

from dataclasses import dataclass
import math

import CoolProp.CoolProp as CP


CRITICAL_HEAT_FLUX_W_M2 = 120e3


@dataclass(frozen=True)
class Substrate:
    """Effective cryogenic substrate properties for the stated evidence case."""

    name: str
    conductivity_W_mK: float
    diffusivity_m2_s: float


# PRESLHY E3.4 Concrete02 effective cryogenic properties.  Do not use this as
# a generic concrete correlation without an explicit applicability decision.
CONCRETE_CRYOGENIC = Substrate("concrete_cryogenic_e34", 2.0, 2.5e-7)


@dataclass(frozen=True)
class LH2Release:
    """Declared inputs for an LH2 release reaching a possible ground pool."""

    rate_kg_s: float
    storage_pressure_barg: float
    deposition_fraction: float = 1.0
    max_radius_m: float | None = None

    def __post_init__(self) -> None:
        if self.rate_kg_s <= 0.0:
            raise ValueError("rate_kg_s must be > 0")
        if self.storage_pressure_barg < 0.0:
            raise ValueError("storage_pressure_barg must be >= 0")
        if not 0.0 <= self.deposition_fraction <= 1.0:
            raise ValueError("deposition_fraction must be in [0, 1]")
        if self.max_radius_m is not None and self.max_radius_m <= 0.0:
            raise ValueError("max_radius_m must be > 0 when supplied")


@dataclass(frozen=True)
class PoolSource:
    """A source term for one declared time window, not a pool trajectory."""

    elapsed_s: float
    flash_vapour_fraction: float
    deposition_fraction: float
    liquid_to_ground_kg_s: float
    pool_temperature_K: float
    latent_heat_J_kg: float
    evaporative_flux_kg_m2_s: float
    unconfined_radius_m: float
    radius_m: float
    area_m2: float
    evaporation_rate_kg_s: float
    liquid_accumulation_rate_kg_s: float
    confined: bool
    source_status: str


@dataclass(frozen=True)
class ObservedFootprintSource:
    """Heat-limited source for a declared, observed pool footprint.

    equivalent_radius_m [m] is the radius of the circular-equivalent area
    supplied by the analyst. required_liquid_ground_rate_kg_s [kg s-1] is the
    quasi-steady liquid inflow that would sustain the calculated evaporation.
    It is not a measured deposition rate.

    This route deliberately does not accept LH2Release or deposition_fraction.
    It converts an independently declared footprint into a conditional
    evaporation source and leaves jet impact, rainout and the release-to-ground
    handoff outside the calculation.
    """

    elapsed_s: float
    equivalent_radius_m: float
    area_m2: float
    pool_temperature_K: float
    latent_heat_J_kg: float
    evaporative_flux_kg_m2_s: float
    evaporation_rate_kg_s: float
    required_liquid_ground_rate_kg_s: float
    source_status: str


def flash_vapour_fraction(storage_pressure_barg: float, *,
                          ambient_pressure_Pa: float = 101325.0) -> float:
    """Isenthalpic saturated-liquid LH2 flash fraction at ambient pressure."""
    if storage_pressure_barg < 0.0:
        raise ValueError("storage_pressure_barg must be >= 0")
    p0 = storage_pressure_barg * 1e5 + ambient_pressure_Pa
    if p0 >= CP.PropsSI("Pcrit", "Hydrogen"):
        raise ValueError("storage pressure is at or above H2 critical pressure")
    h0 = CP.PropsSI("H", "P", p0, "Q", 0, "Hydrogen")
    x = CP.PropsSI("Q", "P", ambient_pressure_Pa, "H", h0, "Hydrogen")
    return min(max(float(x), 0.0), 1.0)


def _ground_flux(*, substrate: Substrate, latent_heat_J_kg: float,
                 ambient_temperature_K: float, pool_temperature_K: float,
                 elapsed_s: float,
                 critical_heat_flux_W_m2: float | None) -> float:
    if elapsed_s <= 0.0:
        raise ValueError("elapsed_s must be > 0")
    if latent_heat_J_kg <= 0.0:
        raise ValueError("latent_heat_J_kg must be > 0")
    if critical_heat_flux_W_m2 is not None and critical_heat_flux_W_m2 <= 0.0:
        raise ValueError("critical_heat_flux_W_m2 must be > 0 or None")
    delta_T = ambient_temperature_K - pool_temperature_K
    if delta_T <= 0.0:
        return 0.0
    q = substrate.conductivity_W_mK * delta_T / math.sqrt(
        math.pi * substrate.diffusivity_m2_s * elapsed_s
    )
    if critical_heat_flux_W_m2 is not None:
        q = min(q, critical_heat_flux_W_m2)
    return q / latent_heat_J_kg


def evaluate_pool_source(release: LH2Release, *, elapsed_s: float,
                         substrate: Substrate = CONCRETE_CRYOGENIC,
                         ambient_temperature_K: float = 282.0,
                         ambient_pressure_Pa: float = 101325.0,
                         critical_heat_flux_W_m2: float | None =
                         CRITICAL_HEAT_FLUX_W_M2) -> PoolSource:
    """Calculate a quasi-steady pool source for one elapsed-time window.

    The pool area instantaneously balances the declared liquid-to-ground rate
    against heat-limited evaporation.  This is appropriate only after a pool
    exists and where a quasi-steady source approximation is justified.
    """
    x = flash_vapour_fraction(release.storage_pressure_barg,
                              ambient_pressure_Pa=ambient_pressure_Pa)
    T_pool = float(CP.PropsSI("T", "P", ambient_pressure_Pa, "Q", 0,
                              "Hydrogen"))
    latent = float(CP.PropsSI("H", "P", ambient_pressure_Pa, "Q", 1,
                              "Hydrogen") - CP.PropsSI(
                                  "H", "P", ambient_pressure_Pa, "Q", 0,
                                  "Hydrogen"))
    flux = _ground_flux(
        substrate=substrate, latent_heat_J_kg=latent,
        ambient_temperature_K=ambient_temperature_K,
        pool_temperature_K=T_pool, elapsed_s=elapsed_s,
        critical_heat_flux_W_m2=critical_heat_flux_W_m2,
    )
    liquid_to_ground = release.rate_kg_s * (1.0 - x) * release.deposition_fraction
    radius_unconfined = (0.0 if liquid_to_ground == 0.0 else math.sqrt(
        liquid_to_ground / (math.pi * flux)))
    radius = radius_unconfined if release.max_radius_m is None else min(
        radius_unconfined, release.max_radius_m)
    area = math.pi * radius * radius
    evaporation = area * flux
    confined = (release.max_radius_m is not None and
                 radius_unconfined > release.max_radius_m)
    return PoolSource(
        elapsed_s=elapsed_s, flash_vapour_fraction=x,
        deposition_fraction=release.deposition_fraction,
        liquid_to_ground_kg_s=liquid_to_ground, pool_temperature_K=T_pool,
        latent_heat_J_kg=latent, evaporative_flux_kg_m2_s=flux,
        unconfined_radius_m=radius_unconfined, radius_m=radius, area_m2=area,
        evaporation_rate_kg_s=evaporation,
        liquid_accumulation_rate_kg_s=max(liquid_to_ground - evaporation, 0.0),
        confined=confined,
        source_status=("quasi_steady_equilibrium" if not confined else
                       "confined_pool_requires_inventory_model"),
    )


def evaluate_observed_footprint_source(
    *, equivalent_radius_m: float, elapsed_s: float,
    substrate: Substrate = CONCRETE_CRYOGENIC,
    ambient_temperature_K: float = 282.0,
    ambient_pressure_Pa: float = 101325.0,
    critical_heat_flux_W_m2: float | None = CRITICAL_HEAT_FLUX_W_M2,
) -> ObservedFootprintSource:
    """Convert a declared circular-equivalent LH2 footprint into a source term.

    The specified footprint is held fixed only for this quasi-steady source
    evaluation. The function calculates the heat-limited evaporation rate on
    the declared solid substrate at elapsed_s; it does not infer a liquid
    deposition fraction, pool inventory, pool-growth history or footprint
    trajectory.

    This route is useful when an experiment or site record constrains a
    footprint more directly than it constrains the release-to-ground handoff.
    If an observation reports a range, evaluate each bound separately rather
    than fitting or silently selecting a central radius.
    """
    if (not math.isfinite(equivalent_radius_m) or
            equivalent_radius_m <= 0.0):
        raise ValueError("equivalent_radius_m must be finite and > 0")
    if not math.isfinite(elapsed_s) or elapsed_s <= 0.0:
        raise ValueError("elapsed_s must be finite and > 0")
    if (not math.isfinite(ambient_temperature_K) or
            ambient_temperature_K <= 0.0):
        raise ValueError("ambient_temperature_K must be finite and > 0")
    if (not math.isfinite(ambient_pressure_Pa) or
            ambient_pressure_Pa <= 0.0):
        raise ValueError("ambient_pressure_Pa must be finite and > 0")

    pool_temperature = float(CP.PropsSI(
        "T", "P", ambient_pressure_Pa, "Q", 0, "Hydrogen"
    ))
    latent_heat = float(
        CP.PropsSI("H", "P", ambient_pressure_Pa, "Q", 1, "Hydrogen")
        - CP.PropsSI("H", "P", ambient_pressure_Pa, "Q", 0, "Hydrogen")
    )
    evaporative_flux = _ground_flux(
        substrate=substrate,
        latent_heat_J_kg=latent_heat,
        ambient_temperature_K=ambient_temperature_K,
        pool_temperature_K=pool_temperature,
        elapsed_s=elapsed_s,
        critical_heat_flux_W_m2=critical_heat_flux_W_m2,
    )
    if evaporative_flux <= 0.0:
        raise ValueError(
            "evaporative flux is zero; an observed-footprint source is undefined"
        )
    area = math.pi * equivalent_radius_m * equivalent_radius_m
    evaporation_rate = area * evaporative_flux
    return ObservedFootprintSource(
        elapsed_s=elapsed_s,
        equivalent_radius_m=equivalent_radius_m,
        area_m2=area,
        pool_temperature_K=pool_temperature,
        latent_heat_J_kg=latent_heat,
        evaporative_flux_kg_m2_s=evaporative_flux,
        evaporation_rate_kg_s=evaporation_rate,
        required_liquid_ground_rate_kg_s=evaporation_rate,
        source_status="observed_footprint_conditional_source",
    )
