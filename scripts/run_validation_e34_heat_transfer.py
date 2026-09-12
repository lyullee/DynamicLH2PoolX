"""Reproduce the restricted PRESLHY E3.4 Concrete02 heat-transfer check.

This compares the DynamicLH2PoolX solid semi-infinite-conduction closure against
the 42 derived Concrete02 mass-loss-rate points.  It does not assess spreading,
fixed-area dynamics as a whole, impact deposition, water behaviour, or gas
dispersion.  The input CSV remains external because its provenance belongs to
the connected SLABx-LH2 workspace.
"""

from __future__ import annotations

import argparse
import csv
import json
import math
import statistics
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from dynamiclh2poolx import LH2Release, evaluate_pool_source


def read_rows(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-csv", required=True, type=Path)
    parser.add_argument("--thermal-origin-orig-s", required=True, type=float,
                        help="Declared origin on scale Orig.Time. Do not reuse legacy t_ground_s: old extraction mixed instrument clocks.")
    parser.add_argument("--output-dir", type=Path, default=Path("outputs/e34_heat_transfer"))
    args = parser.parse_args()
    if not args.source_csv.is_file():
        raise SystemExit(f"source CSV not found: {args.source_csv}")

    rows: list[dict[str, object]] = []
    for raw in read_rows(args.source_csv):
        if raw["run"] != "Concrete02":
            continue
        elapsed_s = float(raw["t_orig_s"]) - args.thermal_origin_orig_s
        observed_flux = float(raw["flux_kg_m2_s"])
        if elapsed_s <= 0.0 or observed_flux <= 0.0:
            continue
        predicted = evaluate_pool_source(
            LH2Release(rate_kg_s=1.0, storage_pressure_barg=1.0),
            elapsed_s=elapsed_s,
            ambient_temperature_K=282.0,
        ).evaporative_flux_kg_m2_s
        rows.append({
            "run": raw["run"],
            "fill": raw["fill"],
            "elapsed_since_ground_cooling_s": elapsed_s,
            "observed_flux_kg_m2_s": observed_flux,
            "predicted_flux_kg_m2_s": predicted,
            "residual_kg_m2_s": predicted - observed_flux,
            "predicted_to_observed": predicted / observed_flux,
        })
    if not rows:
        raise SystemExit("no positive Concrete02 rate points found")

    residuals = [float(row["residual_kg_m2_s"]) for row in rows]
    ratios = [float(row["predicted_to_observed"]) for row in rows]
    summary = {
        "dataset": "PRESLHY E3.4 Concrete02 derived rate points",
        "source_file": str(args.source_csv),
        "thermal_origin_orig_s": args.thermal_origin_orig_s,
        "clock_correction": "t_orig_s minus declared synchronised origin; legacy t_ground_s is withdrawn",
        "n_points": len(rows),
        "rmse_kg_m2_s": math.sqrt(statistics.mean(value * value for value in residuals)),
        "mae_kg_m2_s": statistics.mean(abs(value) for value in residuals),
        "bias_kg_m2_s": statistics.mean(residuals),
        "median_predicted_to_observed": statistics.median(ratios),
        "claim": "restricted solid-conduction/evaporation component comparison",
        "not_validated": [
            "full fixed-area transient pool trajectory",
            "axisymmetric spreading or pool radius",
            "liquid deposition from a release jet",
            "sand, water, RPT, or arbitrary substrates",
            "downstream dispersion",
        ],
    }
    args.output_dir.mkdir(parents=True, exist_ok=True)
    with (args.output_dir / "concrete02_component_rows.csv").open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    (args.output_dir / "summary.json").write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
