"""Run the frozen Stage C solution-verification matrix.

The JUEL Trial 6 aluminium case is used as a numerical benchmark. The script
separates spatial refinement, coupled dr-dt refinement, annulus alignment,
domain size, front observation, and the pre-declared momentum sensitivity.
"""
from __future__ import annotations

from dataclasses import asdict
import hashlib
import json
import math
from pathlib import Path
import sys

import CoolProp.CoolProp as CP

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from dynamiclh2poolx import (  # noqa: E402
    DeclaredInflow,
    DynamicPoolConfig,
    ShallowLayerNumerics,
    SolidSemiInfiniteSurface,
    run_dynamic_pool,
)


PROTOCOL_PATH = ROOT / "data" / "stage_c_protocol.json"
OUTPUT_DIR = ROOT / "outputs" / "stage_c" / "convergence"


def _case(
    dr: float,
    dt: float,
    *,
    domain: float = 1.2,
    front: float = 0.00075,
    closure: str = "zero_radial_momentum_vapor",
):
    pressure = 98_600.0
    density = float(CP.PropsSI("D", "P", pressure, "Q", 0, "Hydrogen"))
    surface = SolidSemiInfiniteSurface(
        "JUEL-3155 aluminium",
        204.0,
        204.0 / (2700.0 * 879.0),
        273.15 + 4.75,
        heat_flux_multiplier=0.40,
    )
    numerics = ShallowLayerNumerics(
        domain_radius_m=domain,
        radial_step_m=dr,
        maximum_time_step_s=dt,
        chezy_coefficient=1.0e-3,
        source_inner_radius_m=0.18,
        source_radius_m=0.22,
        dry_depth_m=1.0e-8,
        reported_front_depth_m=front,
    )
    return run_dynamic_pool(
        DynamicPoolConfig(
            surface,
            numerics,
            pressure,
            evaporation_momentum_closure=closure,
        ),
        DeclaredInflow((0.0, 62.0), (0.006 * density, 0.0)),
        (0.0, 60.0),
    )


def _summary(result) -> dict:
    last = result.ledger[-1]
    return {
        "reported_radius_m": last.reported_radius_m,
        "liquid_mass_kg": last.liquid_mass_kg,
        "cumulative_evaporation_kg": last.cumulative_evaporation_kg,
        "wet_area_m2": last.wet_area_m2,
        "unledgered_mass_residual_kg": last.unledgered_mass_residual_kg,
        "cumulative_numerical_mass_adjustment_kg": (
            last.cumulative_numerical_mass_adjustment_kg
        ),
        "source_status": last.source_status,
    }


def _relative(a: float, b: float) -> float:
    return abs(a - b) / max(abs(b), 1.0e-30)


def _fine_change(coarser: dict, finer: dict) -> dict:
    radius_delta = abs(
        coarser["reported_radius_m"] - finer["reported_radius_m"]
    )
    return {
        "coarser_radius_m": coarser["reported_radius_m"],
        "finer_radius_m": finer["reported_radius_m"],
        "coarser_radius_m_display": f"{coarser['reported_radius_m']:.6f}",
        "finer_radius_m_display": f"{finer['reported_radius_m']:.6f}",
        "radius_absolute_m": radius_delta,
        "radius_absolute_m_display": f"{radius_delta:.6f}",
        "liquid_mass_relative": _relative(
            coarser["liquid_mass_kg"], finer["liquid_mass_kg"]
        ),
        "cumulative_evaporation_relative": _relative(
            coarser["cumulative_evaporation_kg"],
            finer["cumulative_evaporation_kg"],
        ),
    }


def _alignment(dr: float) -> dict:
    inner = 0.18
    outer = 0.22
    inner_index = inner / dr
    outer_index = outer / dr
    aligned = math.isclose(inner_index, round(inner_index), abs_tol=1.0e-12)
    aligned = aligned and math.isclose(
        outer_index, round(outer_index), abs_tol=1.0e-12
    )
    centres = [(i + 0.5) * dr for i in range(math.ceil(1.2 / dr))]
    cells = [x for x in centres if inner <= x <= outer]
    return {
        "radial_step_m": dr,
        "annulus_edges_on_cell_faces": aligned,
        "source_cells": len(cells),
        "source_cell_centres_m": cells,
    }


def main() -> None:
    protocol = json.loads(PROTOCOL_PATH.read_text(encoding="utf-8"))
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    cache = {}

    def run(dr, dt, domain=1.2, front=0.00075,
            closure="zero_radial_momentum_vapor"):
        key = (dr, dt, domain, front, closure)
        if key not in cache:
            cache[key] = _case(
                dr, dt, domain=domain, front=front, closure=closure
            )
        return _summary(cache[key])

    spatial = {
        f"dr_{dr:g}": run(dr, 0.005)
        for dr in (0.04, 0.02, 0.01, 0.005)
    }
    coupled = {
        f"dr_{dr:g}_dt_{dt:g}": run(dr, dt)
        for dr, dt in ((0.02, 0.02), (0.01, 0.01), (0.005, 0.005))
    }
    domains = {
        f"domain_{domain:g}": run(0.01, 0.01, domain=domain)
        for domain in (1.2, 1.6)
    }
    fronts = {
        f"front_{front:g}": run(0.01, 0.01, front=front)
        for front in (0.0005, 0.00075, 0.001)
    }
    momentum = {
        closure: run(0.01, 0.01, closure=closure)
        for closure in (
            "zero_radial_momentum_vapor",
            "liquid_velocity_carryoff",
        )
    }
    spatial_fine = _fine_change(spatial["dr_0.01"], spatial["dr_0.005"])
    coupled_fine = _fine_change(
        coupled["dr_0.01_dt_0.01"], coupled["dr_0.005_dt_0.005"]
    )
    gates = protocol["solution_verification"]["fine_change_gates"]
    alignment = [_alignment(dr) for dr in (0.04, 0.02, 0.01, 0.005)]
    unledgered_limit = max(
        1.0e-12,
        1.0e-10 * spatial["dr_0.005"]["cumulative_evaporation_kg"],
    )
    passed = all(
        change["radius_absolute_m"] <= gates["radius_m"]
        and change["liquid_mass_relative"] <= gates["liquid_mass_relative"]
        and change["cumulative_evaporation_relative"]
        <= gates["cumulative_evaporation_relative"]
        for change in (spatial_fine, coupled_fine)
    )
    passed = passed and all(
        abs(item["unledgered_mass_residual_kg"]) <= unledgered_limit
        for item in cache.values()
        for item in [_summary(item)]
    )
    passed = passed and all(
        item["annulus_edges_on_cell_faces"] and item["source_cells"] >= 2
        for item in alignment
        if item["radial_step_m"] <= 0.02
    )
    passed = passed and all(
        item["cumulative_numerical_mass_adjustment_kg"] == 0.0
        for item in spatial.values()
    )
    manifest = {
        "protocol_id": protocol["protocol_id"],
        "protocol_sha256": hashlib.sha256(PROTOCOL_PATH.read_bytes()).hexdigest(),
        "implementation_sha256": {
            name: hashlib.sha256((ROOT / "src" / "dynamiclh2poolx" / name).read_bytes()).hexdigest()
            for name in ("dynamic_pool.py", "spreading.py")
        },
        "benchmark": "JUEL3155_FIG5_25_TRIAL6_ALUMINIUM_AT_60S",
        "default_momentum_closure_fixed_before_run": (
            protocol["default_evaporation_momentum_closure"]["id"]
        ),
        "source_annulus_alignment": alignment,
        "spatial_refinement_fixed_dt_0.005s": spatial,
        "coupled_dr_dt_refinement": coupled,
        "domain_sensitivity": domains,
        "reported_front_observation_sensitivity": fronts,
        "momentum_closure_structural_sensitivity": momentum,
        "spatial_fine_change": spatial_fine,
        "coupled_fine_change": coupled_fine,
        "unledgered_mass_limit_kg": unledgered_limit,
        "decision": (
            "PASS_STAGE_C_SOLUTION_VERIFICATION"
            if passed else "REQUIRES_NUMERICAL_REFINEMENT"
        ),
    }
    target = OUTPUT_DIR / "manifest.json"
    target.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    print(json.dumps(manifest, indent=2))


if __name__ == "__main__":
    main()
