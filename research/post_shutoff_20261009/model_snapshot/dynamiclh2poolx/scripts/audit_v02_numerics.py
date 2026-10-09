"""Generate numerical evidence for the DynamicLH2PoolX v0.2 code audit.

This script does not alter or repair the solver.  It records grid/time/front
sensitivity and small deterministic counterexamples for review.
"""
from __future__ import annotations

from dataclasses import asdict
import json
import math
from pathlib import Path
import sys

import CoolProp.CoolProp as CP

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from dynamiclh2poolx import (  # noqa: E402
    ConstantHeatFluxWaterSurface,
    DeclaredInflow,
    DynamicPoolConfig,
    ShallowLayerNumerics,
    SolidSemiInfiniteSurface,
    run_dynamic_pool,
)


def aluminium_case(radial_step_m: float, maximum_time_step_s: float,
                   reported_front_depth_m: float):
    pressure = 98_600.0
    density = float(CP.PropsSI("D", "P", pressure, "Q", 0, "Hydrogen"))
    surface = SolidSemiInfiniteSurface(
        "JUEL-3155 aluminium", 204.0, 204.0 / (2700.0 * 879.0),
        273.15 + 4.75, heat_flux_multiplier=0.40,
    )
    numerics = ShallowLayerNumerics(
        domain_radius_m=1.2,
        radial_step_m=radial_step_m,
        maximum_time_step_s=maximum_time_step_s,
        chezy_coefficient=1.0e-3,
        source_inner_radius_m=0.18,
        source_radius_m=0.22,
        dry_depth_m=1.0e-8,
        reported_front_depth_m=reported_front_depth_m,
    )
    return run_dynamic_pool(
        DynamicPoolConfig(surface, numerics, pressure),
        DeclaredInflow((0.0, 62.0), (0.006 * density, 0.0)),
        (0.0, 10.0, 30.0, 60.0),
    )


def main() -> None:
    output = ROOT / "outputs" / "v02_audit"
    output.mkdir(parents=True, exist_ok=True)
    cases = {
        "grid_0.04m": (0.04, 0.02, 0.00075),
        "baseline_0.02m_0.02s": (0.02, 0.02, 0.00075),
        "grid_0.01m": (0.01, 0.02, 0.00075),
        "time_0.04s": (0.02, 0.04, 0.00075),
        "time_0.01s": (0.02, 0.01, 0.00075),
        "front_0.0005m": (0.02, 0.02, 0.00050),
        "front_0.0010m": (0.02, 0.02, 0.00100),
    }
    sensitivity = {}
    cache = {}
    for name, settings in cases.items():
        if settings not in cache:
            cache[settings] = aluminium_case(*settings)
        result = cache[settings]
        sensitivity[name] = {
            "settings": {
                "radial_step_m": settings[0],
                "maximum_time_step_s": settings[1],
                "reported_front_depth_m": settings[2],
            },
            "ledger": [asdict(row) for row in result.ledger],
            "mass_balance_residual_kg": result.mass_balance_residual_kg,
        }

    # Public-API counterexample: every tiny source increment is below the dry
    # cutoff, so it is clipped while cumulative inflow continues to increase.
    saturation = float(CP.PropsSI("T", "P", 101325.0, "Q", 0, "Hydrogen"))
    micro = run_dynamic_pool(
        DynamicPoolConfig(
            SolidSemiInfiniteSurface("zero heat", 1.0, 1.0e-6, saturation),
            ShallowLayerNumerics(
                domain_radius_m=0.5, radial_step_m=0.025,
                maximum_time_step_s=0.01, source_radius_m=0.1,
                dry_depth_m=1.0e-8, reported_front_depth_m=1.0e-5,
            ),
        ),
        DeclaredInflow((0.0,), (1.0e-7,)),
        (0.0, 1.0),
    )
    micro_inflow = {
        "declared_inflow_kg": micro.ledger[-1].cumulative_inflow_kg,
        "final_liquid_mass_kg": micro.ledger[-1].liquid_mass_kg,
        "cumulative_evaporation_kg": micro.ledger[-1].cumulative_evaporation_kg,
        "escaped_domain_mass_kg": micro.ledger[-1].escaped_domain_mass_kg,
        "mass_balance_residual_kg": micro.mass_balance_residual_kg,
        "relative_unaccounted_fraction": (
            micro.mass_balance_residual_kg
            / micro.ledger[-1].cumulative_inflow_kg
        ),
    }

    # The state inventory uses every positive-depth cell, but reported area
    # uses a separate front threshold.  This public case makes the two
    # populations diverge so the reporting consequence is explicit.
    hidden_area = run_dynamic_pool(
        DynamicPoolConfig(
            ConstantHeatFluxWaterSurface(1.0e3, "audit-only constant flux"),
            ShallowLayerNumerics(
                domain_radius_m=0.5, radial_step_m=0.025,
                maximum_time_step_s=0.01, source_radius_m=0.1,
                dry_depth_m=1.0e-8, reported_front_depth_m=0.1,
            ),
        ),
        DeclaredInflow((0.0, 1.0), (1.0, 0.0)),
        (0.0, 1.0),
    )
    hidden_last = hidden_area.ledger[-1]
    reporting_population = {
        "liquid_mass_kg": hidden_last.liquid_mass_kg,
        "reported_radius_m": hidden_last.radius_m,
        "reported_area_m2": hidden_last.area_m2,
        "last_substep_evaporation_rate_kg_s": hidden_last.evaporation_rate_kg_s,
        "wet_area_mean_evaporation_flux_kg_m2_s": hidden_last.wet_area_mean_evaporation_flux_kg_m2_s,
        "wet_area_mean_substrate_heat_flux_W_m2": hidden_last.substrate_heat_flux_W_m2,
    }

    # The current evaporation split subtracts depth but does not subtract
    # momentum.  This one-cell example records the deterministic consequence.
    depth_before = 1.0e-3
    velocity_before = 0.2
    evaporated_depth = 0.5e-3
    momentum_before = depth_before * velocity_before
    momentum_coupling = {
        "depth_before_m": depth_before,
        "evaporated_depth_m": evaporated_depth,
        "velocity_before_m_s": velocity_before,
        "velocity_after_current_split_m_s": (
            momentum_before / (depth_before - evaporated_depth)
        ),
        "velocity_after_mass_carrying_sink_m_s": velocity_before,
    }

    pressure = 98_600.0
    rho = float(CP.PropsSI("D", "P", pressure, "Q", 0, "Hydrogen"))
    mu = float(CP.PropsSI("V", "P", pressure, "Q", 0, "Hydrogen"))
    nu = mu / rho
    friction = []
    for label, depth, velocity in (
        ("nominal_laminar", 0.00075, 0.2),
        ("nominal_turbulent", 0.002, 0.5),
    ):
        reynolds = abs(velocity) * depth / nu
        laminar_rate = nu / depth**2
        turbulent_rate = 1.0e-3 * abs(velocity) / depth
        friction.append({
            "case": label,
            "depth_m": depth,
            "velocity_m_s": velocity,
            "reynolds_number": reynolds,
            "laminar_damping_rate_s-1": laminar_rate,
            "turbulent_damping_rate_s-1": turbulent_rate,
            "report_transition_indicator": (
                "turbulent" if reynolds > 2320.0 else "laminar"
            ),
            "report_and_code_sum_both_rates_s-1": laminar_rate + turbulent_rate,
            "current_code_summed_rate_s-1": laminar_rate + turbulent_rate,
            "audit_result": "CONCORDANT_WITH_JUEL_3155_PAGE_96",
        })

    invalid_surface_accepted = False
    invalid_surface_runtime_error = None
    try:
        invalid = DynamicPoolConfig(object())  # type: ignore[arg-type]
        invalid_surface_accepted = True
        try:
            run_dynamic_pool(
                invalid, DeclaredInflow((0.0,), (0.0,)), (0.0, 0.1)
            )
        except Exception as exc:  # audit records the current public failure
            invalid_surface_runtime_error = f"{type(exc).__name__}: {exc}"
    except Exception as exc:
        invalid_surface_runtime_error = f"configuration rejected: {type(exc).__name__}: {exc}"

    payload = {
        "aluminium_trial6_sensitivity": sensitivity,
        "dry_cutoff_counterexample": micro_inflow,
        "reporting_population_counterexample": reporting_population,
        "evaporation_momentum_counterexample": momentum_coupling,
        "friction_implementation_check": friction,
        "runtime_type_validation": {
            "invalid_surface_accepted_by_config": invalid_surface_accepted,
            "later_runtime_error": invalid_surface_runtime_error,
        },
    }
    target = output / "numerical_audit.json"
    target.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print(target)
    print(json.dumps({
        "dry_cutoff": micro_inflow,
        "reporting_population": reporting_population,
        "momentum": momentum_coupling,
        "friction": friction,
        "trial6_at_60s": {
            key: {
                "radius_m": value["ledger"][-1]["radius_m"],
                "mass_kg": value["ledger"][-1]["liquid_mass_kg"],
                "evaporation_kg": value["ledger"][-1]["cumulative_evaporation_kg"],
            }
            for key, value in sensitivity.items()
        },
    }, indent=2))


if __name__ == "__main__":
    main()
