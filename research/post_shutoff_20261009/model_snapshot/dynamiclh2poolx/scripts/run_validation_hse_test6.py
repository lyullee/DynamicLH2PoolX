"""Assess the frozen dynamic pool against HSE RR985/RR986 Test 6.

No radius observation is used to fit a model coefficient. The measured initial
ground temperature and the published GASP concrete defaults/5 mm physical
roughness are declared inputs. The condensed-air solid pulse is diagnostic.
"""
from __future__ import annotations

import argparse
import csv
from dataclasses import asdict
import hashlib
import json
import math
from pathlib import Path
import sys

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from dynamiclh2poolx import (  # noqa: E402
    DeclaredInflow,
    DynamicPoolConfig,
    ShallowLayerNumerics,
    SolidSemiInfiniteSurface,
    __version__,
    run_dynamic_pool,
)
from run_dynamic_validation import dump_csv  # noqa: E402


DATA_PATH = ROOT / "data" / "hse_rr985_test6_radius.csv"
PROTOCOL_PATH = ROOT / "data" / "stage_c_protocol.json"
SOURCE_MANIFEST_PATH = ROOT / "data" / "source_manifest.json"


def read_observations() -> list[dict]:
    with DATA_PATH.open(newline="", encoding="utf-8") as stream:
        rows = list(csv.DictReader(stream))
    for row in rows:
        for key in ("time_s", "observed_radius_m", "time_bound_s", "radius_bound_m"):
            row[key] = float(row[key])
    return rows


def run_case(*, source_radius_m: float = 0.025,
             retention_depth_m: float = 0.005,
             radial_step_m: float = 0.01):
    surface = SolidSemiInfiniteSurface(
        "HSE Test 6 concrete; RR985 GASP default properties",
        conductivity_W_mK=0.93,
        diffusivity_m2_s=4.8e-7,
        initial_temperature_K=266.0,
    )
    numerics = ShallowLayerNumerics(
        domain_radius_m=2.0,
        radial_step_m=radial_step_m,
        maximum_time_step_s=0.02,
        chezy_coefficient=1.0e-3,
        source_radius_m=source_radius_m,
        surface_retention_depth_m=retention_depth_m,
        dry_depth_m=1.0e-8,
        reported_front_depth_m=0.00075,
    )
    return run_dynamic_pool(
        DynamicPoolConfig(
            surface,
            numerics,
            evaporation_momentum_closure="zero_radial_momentum_vapor",
        ),
        DeclaredInflow((0.0, 561.0), (0.0707, 0.0)),
        tuple(float(t) for t in range(621)),
    )


def result_summary(result) -> dict:
    end = result.ledger[561]
    reported_dryout_time = next(
        (row.time_s for row in result.ledger[562:] if row.reported_radius_m == 0.0),
        None,
    )
    inventory_exhaustion_time = next(
        (row.time_s for row in result.ledger[562:] if row.liquid_mass_kg <= 1.0e-12),
        None,
    )
    return {
        "end_of_release_radius_m": end.reported_radius_m,
        "end_of_release_liquid_mass_kg": end.liquid_mass_kg,
        "reported_dryout_after_release_stop_s": (
            reported_dryout_time - 561.0
            if reported_dryout_time is not None else None
        ),
        "inventory_exhaustion_after_release_stop_s": (
            inventory_exhaustion_time - 561.0
            if inventory_exhaustion_time is not None else None
        ),
        "maximum_reported_radius_m": max(row.reported_radius_m for row in result.ledger),
        "mass_balance_residual_kg": result.mass_balance_residual_kg,
        "maximum_absolute_unledgered_mass_residual_kg": max(
            abs(row.unledgered_mass_residual_kg) for row in result.ledger
        ),
        "cumulative_numerical_mass_adjustment_kg": (
            result.ledger[-1].cumulative_numerical_mass_adjustment_kg
        ),
        "escaped_domain_mass_kg": result.ledger[-1].escaped_domain_mass_kg,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--rr985-pdf", type=Path, required=True)
    parser.add_argument("--rr986-pdf", type=Path, required=True)
    parser.add_argument(
        "--output-dir", type=Path,
        default=ROOT / "outputs" / "stage_c" / "hse_test6",
    )
    args = parser.parse_args()
    args.output_dir.mkdir(parents=True, exist_ok=True)
    protocol = json.loads(PROTOCOL_PATH.read_text(encoding="utf-8"))
    observations = read_observations()

    cache = {}
    def cached(source_radius=0.025, retention=0.005, dr=0.01):
        key = (source_radius, retention, dr)
        if key not in cache:
            cache[key] = run_case(
                source_radius_m=source_radius,
                retention_depth_m=retention,
                radial_step_m=dr,
            )
        return cache[key]

    result = cached()
    comparison = []
    for observation in observations:
        index = int(observation["time_s"])
        predicted = result.ledger[index].reported_radius_m
        lo = max(0, int(math.floor(observation["time_s"] - observation["time_bound_s"])))
        hi = min(620, int(math.ceil(observation["time_s"] + observation["time_bound_s"])))
        interval_predictions = [
            result.ledger[i].reported_radius_m for i in range(lo, hi + 1)
        ]
        interval_residual = min(
            (value - observation["observed_radius_m"] for value in interval_predictions),
            key=abs,
        )
        comparison.append({
            **observation,
            "predicted_radius_m": predicted,
            "point_residual_m": predicted - observation["observed_radius_m"],
            "minimum_time_interval_residual_m": interval_residual,
        })
    dump_csv(args.output_dir / "radius_comparison.csv", comparison)
    dump_csv(
        args.output_dir / "trajectory.csv",
        [asdict(row) for row in result.ledger],
    )

    release_rows = [row for row in comparison if row["phase"] == "release"]
    point_errors = np.array([row["point_residual_m"] for row in release_rows])
    interval_errors = np.array([
        row["minimum_time_interval_residual_m"] for row in release_rows
    ])
    summary = result_summary(result)
    sensitivity = {
        "source_footprint_radius_m": {
            str(radius): result_summary(cached(source_radius=radius))
            for radius in (0.0125, 0.025, 0.05)
        },
        "surface_retention_depth_m": {
            str(depth): result_summary(cached(retention=depth))
            for depth in (0.004, 0.005, 0.006)
        },
    }
    targets = protocol["hse_rr985_test6"]["assessment_targets"]
    radius_pass = (
        targets["end_of_release_radius_m"][0]
        <= summary["end_of_release_radius_m"]
        <= targets["end_of_release_radius_m"][1]
    )
    dryout_pass = (
        summary["reported_dryout_after_release_stop_s"] is not None
        and targets["dryout_after_stop_s"][0]
        <= summary["reported_dryout_after_release_stop_s"]
        <= targets["dryout_after_stop_s"][1]
    )
    conservation_pass = (
        summary["maximum_absolute_unledgered_mass_residual_kg"] <= 4.0e-9
        and summary["cumulative_numerical_mass_adjustment_kg"] == 0.0
        and summary["escaped_domain_mass_kg"] == 0.0
    )

    figure, axis = plt.subplots(figsize=(10, 6), layout="constrained")
    axis.errorbar(
        [row["time_s"] for row in observations],
        [row["observed_radius_m"] for row in observations],
        xerr=[row["time_bound_s"] for row in observations],
        yerr=[row["radius_bound_m"] for row in observations],
        fmt="o", label="HSE RR985 Figure 2 digitisation",
    )
    axis.plot(
        [row.time_s for row in result.ledger],
        [row.reported_radius_m for row in result.ledger],
        "k-", label="DynamicLH2PoolX (no radius fit)",
    )
    axis.axvline(561.0, color="grey", linestyle="--", label="release stop")
    axis.axhspan(0.9, 1.0, color="green", alpha=0.12,
                label="reported end-radius band")
    axis.set(
        xlabel="Time [s]", ylabel="Pool radius [m]", xlim=(0, 590), ylim=(0, 1.5),
        title="HSE Test 6: same-case-thermal-input-constrained radius assessment",
    )
    axis.grid(alpha=0.2)
    axis.legend()
    figure.savefig(args.output_dir / "radius_assessment.png", dpi=180)
    plt.close(figure)

    manifest = {
        "protocol_id": protocol["protocol_id"],
        "data_quality": "figure_digitised",
        "assessment_label": protocol["hse_rr985_test6"]["assessment_label"],
        "independence_statement": (
            "radius observations were not used to fit any coefficient; same-case "
            "initial ground temperature is a measured input; k and alpha are the "
            "RR985-published GASP defaults, not inferred from Test 6 radius"
        ),
        "source_record_ids": protocol["hse_rr985_test6"]["source_ids"],
        "source_hashes_sha256": {
            "rr985_pdf": hashlib.sha256(args.rr985_pdf.read_bytes()).hexdigest(),
            "rr986_pdf": hashlib.sha256(args.rr986_pdf.read_bytes()).hexdigest(),
            "radius_csv": hashlib.sha256(DATA_PATH.read_bytes()).hexdigest(),
            "protocol": hashlib.sha256(PROTOCOL_PATH.read_bytes()).hexdigest(),
            "source_manifest": hashlib.sha256(SOURCE_MANIFEST_PATH.read_bytes()).hexdigest(),
            "runner": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
            "dynamic_pool.py": hashlib.sha256(
                (ROOT / "src" / "dynamiclh2poolx" / "dynamic_pool.py").read_bytes()
            ).hexdigest(),
            "spreading.py": hashlib.sha256(
                (ROOT / "src" / "dynamiclh2poolx" / "spreading.py").read_bytes()
            ).hexdigest(),
        },
        "software": {"dynamiclh2poolx": __version__, "python": sys.version},
        "declared_inputs": protocol["hse_rr985_test6"],
        "primary_result": summary,
        "trajectory_metrics_diagnostic_only": {
            "release_points": len(release_rows),
            "point_rmse_m": float(np.sqrt(np.mean(point_errors**2))),
            "time_interval_minimum_residual_rmse_m": float(
                np.sqrt(np.mean(interval_errors**2))
            ),
            "solid_deposition_peak_reproduced": (
                summary["maximum_reported_radius_m"] >= 1.2
            ),
            "reason_non_gating": (
                "RR985 attributes the 1.3-1.4 m expansion/retraction pulse to "
                "condensed-air solid deposition, outside the smooth pool model"
            ),
        },
        "predeclared_input_sensitivity": sensitivity,
        "assessment_checks": {
            "end_of_release_radius": radius_pass,
            "dryout_time": dryout_pass,
            "conservation_and_domain": conservation_pass,
        },
        "decision": (
            "PASS_HSE_RADIUS_ASSESSMENT_ENDPOINTS_WITH_STRUCTURAL_LIMITATION"
            if radius_pass and dryout_pass and conservation_pass
            else "REQUIRES_HSE_ASSESSMENT_REPAIR"
        ),
    }
    (args.output_dir / "manifest.json").write_text(
        json.dumps(manifest, indent=2), encoding="utf-8"
    )
    print(json.dumps(manifest, indent=2))


if __name__ == "__main__":
    main()
