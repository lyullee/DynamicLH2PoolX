"""Reproducible LH2 radius comparison against Dienhart JUEL-3155.

Figures 5.24 and 5.25 are open-access report figures.  The few plotted sensor
points are transcribed at their discrete 0.1 m radii with the report's stated
time/radius uncertainty.  Trial 3/5 define the two global empirical closure
values once; Trial 4/6 are the holdout trials.
"""
from __future__ import annotations

from pathlib import Path
import argparse
import csv
from dataclasses import asdict
import hashlib
import json
import sys

import CoolProp.CoolProp as CP
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pymupdf

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from dynamiclh2poolx import (
    ConstantHeatFluxWaterSurface, DeclaredInflow, DynamicPoolConfig,
    ShallowLayerNumerics, SolidSemiInfiniteSurface, run_dynamic_pool,
)
from run_dynamic_validation import dump_csv


OBSERVATIONS_CSV = ROOT / "data" / "juel3155_radius_observations.csv"


def read_observations(path: Path = OBSERVATIONS_CSV) -> list[dict]:
    """Load the immutable figure transcription and its declared intervals."""
    with path.open(newline="", encoding="utf-8") as stream:
        rows = list(csv.DictReader(stream))
    for row in rows:
        row["trial"] = int(row["trial"])
        row["time_s"] = float(row["time_s"])
        row["observed_radius_m"] = float(row["observed_radius_m"])
        row["time_bound_s"] = float(row["time_bound_s"])
        row["radius_lower_bound_m"] = float(row["radius_lower_bound_m"])
        row["radius_upper_bound_m"] = float(row["radius_upper_bound_m"])
    return rows


def _run(surface, volume_rate_m3_s: float, pressure_Pa: float):
    density = float(CP.PropsSI("D", "P", pressure_Pa, "Q", 0, "Hydrogen"))
    numerics = ShallowLayerNumerics(
        domain_radius_m=1.2, radial_step_m=.02, maximum_time_step_s=.02,
        chezy_coefficient=1e-3, source_inner_radius_m=.18,
        source_radius_m=.22, dry_depth_m=1e-8,
        reported_front_depth_m=.00075,
    )
    return run_dynamic_pool(
        DynamicPoolConfig(surface=surface, numerics=numerics,
                          ambient_pressure_Pa=pressure_Pa),
        DeclaredInflow((0., 62.), (volume_rate_m3_s * density, 0.)),
        tuple(float(t) for t in range(71)),
    )


def _source_panels(pdf: Path, out: Path) -> tuple[Path, Path]:
    document = pymupdf.open(pdf)
    paths = []
    for page, name in [(139, "figure5_24_source.png"), (140, "figure5_25_source.png")]:
        pixmap = document[page - 1].get_pixmap(matrix=pymupdf.Matrix(1.5, 1.5), alpha=False)
        target = out / name
        pixmap.save(target)
        paths.append(target)
    return paths[0], paths[1]


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--report-pdf", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, default=ROOT / "outputs/spreading_validation")
    args = parser.parse_args(); args.output_dir.mkdir(parents=True, exist_ok=True)
    observations = read_observations()
    water_source, aluminium_source = _source_panels(args.report_pdf, args.output_dir)
    pressure = 98_600.0
    # One value per surface, fixed using Trial 3/5 and then held for Trial 4/6.
    water_flux = 200_000.0
    aluminium_multiplier = 0.40
    water = _run(ConstantHeatFluxWaterSurface(
        water_flux, "JUEL-3155 Trial 3 central video band radius 0.5 m"), .005, pressure)
    aluminium = _run(SolidSemiInfiniteSurface(
        "JUEL-3155 aluminium", 204.0, 204.0/(2700.0*879.0),
        273.15 + 4.75, heat_flux_multiplier=aluminium_multiplier), .006, pressure)
    results = {"water": water, "aluminium": aluminium}
    dump_csv(
        args.output_dir / "trajectories.csv",
        [
            {"surface": surface, **asdict(ledger_row)}
            for surface, result in results.items()
            for ledger_row in result.ledger
        ],
    )
    rows = []
    for observation in observations:
        surface = observation["surface"]
        time_s = observation["time_s"]
        observed = observation["observed_radius_m"]
        predicted = results[surface].ledger[int(time_s)].reported_radius_m
        rows.append({
            **observation,
            "predicted_radius_m": predicted,
            "residual_m": predicted - observed,
        })
    dump_csv(args.output_dir / "radius_comparison.csv", rows)
    metrics = []
    for surface in ("water", "aluminium"):
        for role in ("calibration", "holdout"):
            selected = [r for r in rows if r["surface"] == surface and r["role"] == role and r["time_s"] <= 62]
            errors = np.array([r["residual_m"] for r in selected])
            metrics.append({"surface": surface, "role": role, "n": len(selected),
                            "rmse_m": float(np.sqrt(np.mean(errors**2))),
                            "mae_m": float(np.mean(np.abs(errors))),
                            "bias_m": float(np.mean(errors))})
    band_coverage = {}
    for surface, lower, upper in (("water", .4, .6), ("aluminium", .3, .5)):
        radii = [row.radius_m for row in results[surface].ledger[10:61]]
        band_coverage[surface] = sum(lower <= value <= upper for value in radii) / len(radii)

    digitisation_interval_coverage = {}
    for surface in ("water", "aluminium"):
        for role in ("calibration", "holdout"):
            selected = [
                row for row in rows
                if row["surface"] == surface and row["role"] == role
                and row["time_s"] <= 62
            ]
            digitisation_interval_coverage[f"{surface}_{role}"] = (
                sum(
                    row["radius_lower_bound_m"] <= row["predicted_radius_m"]
                    <= row["radius_upper_bound_m"]
                    for row in selected
                ) / len(selected)
            )

    parameter_sensitivity = {"water_heat_flux_W_m2": {},
                             "aluminium_heat_flux_multiplier": {}}
    for flux in (180_000.0, 200_000.0, 220_000.0):
        candidate = water if flux == water_flux else _run(
            ConstantHeatFluxWaterSurface(
                flux, "predeclared Stage C parameter sensitivity"
            ), .005, pressure
        )
        selected = [row for row in observations
                    if row["surface"] == "water"
                    and row["role"] == "holdout" and row["time_s"] <= 62]
        errors = np.array([
            candidate.ledger[int(row["time_s"])].reported_radius_m
            - row["observed_radius_m"] for row in selected
        ])
        parameter_sensitivity["water_heat_flux_W_m2"][str(int(flux))] = {
            "holdout_rmse_m": float(np.sqrt(np.mean(errors**2))),
            "radius_at_60s_m": candidate.ledger[60].reported_radius_m,
        }
    for multiplier in (0.35, 0.40, 0.45):
        candidate = aluminium if multiplier == aluminium_multiplier else _run(
            SolidSemiInfiniteSurface(
                "JUEL-3155 aluminium sensitivity", 204.0,
                204.0/(2700.0*879.0), 273.15 + 4.75,
                heat_flux_multiplier=multiplier,
            ), .006, pressure
        )
        selected = [row for row in observations
                    if row["surface"] == "aluminium"
                    and row["role"] == "holdout" and row["time_s"] <= 62]
        errors = np.array([
            candidate.ledger[int(row["time_s"])].reported_radius_m
            - row["observed_radius_m"] for row in selected
        ])
        parameter_sensitivity["aluminium_heat_flux_multiplier"][str(multiplier)] = {
            "holdout_rmse_m": float(np.sqrt(np.mean(errors**2))),
            "radius_at_60s_m": candidate.ledger[60].reported_radius_m,
        }

    figure, axes = plt.subplots(2, 2, figsize=(13, 9), layout="constrained")
    for column, (surface, band, title) in enumerate([
        ("water", (.4, .6), "Water: 5 L/s for 62 s"),
        ("aluminium", (.3, .5), "Aluminium: 6 L/s for 62 s"),
    ]):
        ax = axes[0, column]
        for trial in sorted({r["trial"] for r in observations if r["surface"] == surface}):
            selected = [r for r in rows if r["surface"] == surface and r["trial"] == trial]
            ax.errorbar([r["time_s"] for r in selected], [r["observed_radius_m"] for r in selected],
                        xerr=[r["time_bound_s"] for r in selected],
                        yerr=[
                            [r["observed_radius_m"] - r["radius_lower_bound_m"] for r in selected],
                            [r["radius_upper_bound_m"] - r["observed_radius_m"] for r in selected],
                        ], fmt="o",
                        ms=4, label=f"Trial {trial} ({selected[0]['role']})")
        model = results[surface].ledger
        ax.plot([r.time_s for r in model], [r.radius_m for r in model], "k-", label="DynamicLH2PoolX")
        ax.axhspan(*band, color="grey", alpha=.2, label="reported video band")
        ax.axvline(62, color="r", ls="--", lw=1, label="inflow stop")
        ax.set(xlabel="Time [s]", ylabel="Pool radius [m]", title=title, xlim=(0,70))
        ax.grid(alpha=.2); ax.legend(fontsize=8)
    axes[1,0].imshow(plt.imread(water_source)); axes[1,0].axis("off"); axes[1,0].set_title("JUEL-3155 Figure 5.24 source audit")
    axes[1,1].imshow(plt.imread(aluminium_source)); axes[1,1].axis("off"); axes[1,1].set_title("JUEL-3155 Figure 5.25 source audit")
    figure.suptitle("Axisymmetric LH2 spreading validation | Trial 3/5 calibration, Trial 4/6 holdout")
    figure.savefig(args.output_dir / "radius_validation.png", dpi=180); plt.close(figure)

    holdout = [m for m in metrics if m["role"] == "holdout"]
    decision = "PASS_RESTRICTED_SPREADING" if (
        all(m["rmse_m"] <= .15 for m in holdout)
        and all(value >= .90 for value in band_coverage.values())
    ) else "REQUIRES_ITERATION"
    manifest = {
        "source": "Dienhart, JUEL-3155 (1995), Figures 5.24 and 5.25, Tables 3.8/3.9",
        "persistent_id": "http://hdl.handle.net/2128/21550",
        "source_sha256": hashlib.sha256(args.report_pdf.read_bytes()).hexdigest(),
        "implementation_sha256": {
            name: hashlib.sha256((ROOT / "src" / "dynamiclh2poolx" / name).read_bytes()).hexdigest()
            for name in ("dynamic_pool.py", "spreading.py")
        },
        "observation_file": str(OBSERVATIONS_CSV.relative_to(ROOT)),
        "observation_sha256": hashlib.sha256(OBSERVATIONS_CSV.read_bytes()).hexdigest(),
        "digitisation": "manual discrete sensor transcription from open-access report; intervals are stored per row; one calibration trial per material so no bootstrap CI is claimed",
        "calibration": {"water_heat_flux_W_m2": water_flux,
                        "aluminium_heat_flux_multiplier": aluminium_multiplier,
                        "calibration_trials": [3,5], "holdout_trials": [4,6]},
        "geometry": {"catch_bowl_diameter_m": .4, "source_annulus_m": [.18,.22],
                     "thermocouple_height_range_m": [.0005,.001],
                     "reported_front_depth_m": .00075},
        "metrics": metrics, "video_band_coverage_fraction_10_to_60_s": band_coverage,
        "digitisation_interval_coverage_fraction": digitisation_interval_coverage,
        "predeclared_parameter_sensitivity_not_confidence_interval": parameter_sensitivity,
        "mass_balance_residual_kg": {k: v.mass_balance_residual_kg for k,v in results.items()},
        "limitations": ["smooth axisymmetric radius cannot reproduce pulsation, branch asymmetry or detached floes",
                        "water constant-flux closure is limited to the approximately 60 s calibration regime",
                        "post-cutoff breakup is not resolved"],
        "decision": decision,
    }
    (args.output_dir / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    print(json.dumps(manifest, indent=2))


if __name__ == "__main__":
    main()
