"""Reproduce and independently score Xie et al. (2023) Figure 11.

The published PTC curve is used only to recover its omitted thermal-age offset
and initial-temperature input. The black experimental points are then scored
without fitting. Figure 9 is not integrated: it is a different run/clock and
the paper does not publish the initial temperature field linking the figures.
"""
from __future__ import annotations

from pathlib import Path
import argparse
import hashlib
import json
import math
import sys

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pymupdf

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from dynamiclh2poolx import DeclaredInflow, FixedAreaPoolConfig, Substrate, run_fixed_area_pool
from run_dynamic_validation import dump_csv


def _curve_image(pdf: Path) -> np.ndarray:
    document = pymupdf.open(pdf)
    images = [item for item in document[10].get_images(full=True) if item[2:4] == (870, 649)]
    if len(images) != 1:
        raise RuntimeError("Expected one 870x649 Figure 11 image on PDF page 11")
    pixmap = pymupdf.Pixmap(document, images[0][0])
    return np.frombuffer(pixmap.samples, dtype=np.uint8).reshape(
        pixmap.height, pixmap.width, pixmap.n
    )[:, :, :3]


def _digitise(image: np.ndarray) -> tuple[list[dict], list[dict]]:
    x0, x150, y1e3, y4e4 = 151.0, 821.0, 27.0, 567.0
    to_time = lambda x: (x - x0) * 150.0 / (x150 - x0)
    to_velocity = lambda y: 1.0e-3 - (y - y1e3) * 6.0e-4 / (y4e4 - y1e3)
    red = (image[:, :, 0] > 180) & (image[:, :, 1] < 100) & (image[:, :, 2] < 100)
    predicted = []
    columns = np.where(red.sum(axis=0) > 4)[0]
    groups: list[list[int]] = []
    for column in columns:
        if not groups or column > groups[-1][-1] + 1:
            groups.append([int(column)])
        else:
            groups[-1].append(int(column))
    for group in groups:
        x = float(np.mean(group))
        y_values = np.where(red[:, group].any(axis=1))[0]
        if not len(y_values):
            continue
        y = float(np.median(y_values))
        time, velocity = to_time(x), to_velocity(y)
        if 0.0 <= time <= 150.0 and 4.0e-4 <= velocity <= 1.0e-3:
            if not (time > 50.0 and y < 300.0):
                predicted.append({"time_s": time, "velocity_m_s": velocity,
                                  "pixel_x": x, "pixel_y": y,
                                  "series": "published_PTC_prediction"})
    experimental = []
    black = np.all(image < 70, axis=2)
    for nominal_time in range(15, 136, 15):
        x = int(round(x0 + nominal_time * (x150 - x0) / 150.0))
        candidates = []
        for yy in range(60, 540):
            score = int(black[max(0, yy - 6):yy + 7, x - 7:x + 8].sum())
            if score >= 80:
                candidates.append((score, yy))
        if not candidates:
            raise RuntimeError(f"No experimental square found near {nominal_time} s")
        _, y = max(candidates)
        local_y, local_x = np.where(black[y - 7:y + 8, x - 7:x + 8])
        centre_x = float(np.mean(local_x + x - 7))
        centre_y = float(np.mean(local_y + y - 7))
        experimental.append({"time_s": float(nominal_time),
                             "velocity_m_s": to_velocity(centre_y),
                             "pixel_x": centre_x, "pixel_y": centre_y,
                             "read_off_time_bound_s": 1.0,
                             "read_off_velocity_bound_m_s": 6.0e-6,
                             "series": "experiment"})
    return predicted, experimental


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--pdf", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, default=ROOT / "outputs/xie2023")
    args = parser.parse_args()
    args.output_dir.mkdir(parents=True, exist_ok=True)
    image = _curve_image(args.pdf)
    red, experiment = _digitise(image)
    dump_csv(args.output_dir / "figure11_published_curve.csv", red)
    dump_csv(args.output_dir / "figure11_experiment.csv", experiment)

    red_time = np.array([row["time_s"] for row in red])
    red_velocity = np.array([row["velocity_m_s"] for row in red])
    slope, intercept = np.polyfit(red_time, 1.0 / red_velocity**2, 1)
    coefficient = 1.0 / math.sqrt(slope)
    initial_age = intercept / slope
    conductivity, diffusivity = 0.88, 1.5775e-7
    density, latent_heat, saturation_temperature = 70.899, 448_910.0, 20.324
    temperature_difference = (
        coefficient * density * latent_heat * math.sqrt(math.pi * diffusivity)
        / conductivity
    )
    initial_temperature = saturation_temperature + temperature_difference

    times = tuple([0.0] + [row["time_s"] for row in experiment])
    config = FixedAreaPoolConfig(
        area_m2=0.16, initial_liquid_mass_kg=10.0,
        substrate=Substrate("xie2023_table3", conductivity, diffusivity),
        ambient_temperature_K=initial_temperature,
        initial_thermal_age_s=initial_age, critical_heat_flux_W_m2=None,
    )
    result = run_fixed_area_pool(config, DeclaredInflow((0.0,), (0.0,)), times)
    model_velocity = np.array([
        row.evaporation_flux_kg_m2_s / row.liquid_density_kg_m3
        for row in result.ledger[1:]
    ])
    observed = np.array([row["velocity_m_s"] for row in experiment])
    residual = model_velocity - observed
    relative = np.abs(residual) / observed
    red_model = coefficient / np.sqrt(red_time + initial_age)
    metrics = {
        "n_experimental_points": len(observed),
        "mean_absolute_relative_error": float(np.mean(relative)),
        "maximum_absolute_relative_error": float(np.max(relative)),
        "rmse_m_s": float(np.sqrt(np.mean(residual**2))),
        "mae_m_s": float(np.mean(np.abs(residual))),
        "bias_m_s": float(np.mean(residual)),
        "published_mean_relative_error": 0.0748,
        "published_maximum_relative_error": 0.112,
        "published_curve_replication_rmse_m_s": float(np.sqrt(np.mean((red_model-red_velocity)**2))),
        "recovered_initial_thermal_age_s": float(initial_age),
        "recovered_initial_substrate_temperature_K": float(initial_temperature),
        "mass_balance_residual_kg": result.mass_balance_residual_kg,
    }
    gate = {
        "maximum_difference_from_published_relative_errors": 0.02,
        "maximum_published_curve_replication_rmse_m_s": 6.0e-6,
        "required_experimental_points": 9,
    }
    passed = (
        len(observed) == gate["required_experimental_points"]
        and abs(metrics["mean_absolute_relative_error"]
                - metrics["published_mean_relative_error"])
            <= gate["maximum_difference_from_published_relative_errors"]
        and abs(metrics["maximum_absolute_relative_error"]
                - metrics["published_maximum_relative_error"])
            <= gate["maximum_difference_from_published_relative_errors"]
        and metrics["published_curve_replication_rmse_m_s"]
            <= gate["maximum_published_curve_replication_rmse_m_s"]
    )
    rows = [{**source, "model_velocity_m_s": float(prediction),
             "absolute_relative_error": float(error)}
            for source, prediction, error in zip(experiment, model_velocity, relative)]
    dump_csv(args.output_dir / "figure11_comparison.csv", rows)

    figure, axes = plt.subplots(1, 2, figsize=(12, 4.8), layout="constrained")
    axes[0].errorbar([r["time_s"] for r in experiment], observed,
                     xerr=1.0, yerr=6.0e-6, fmt="ks", ms=4,
                     label="Figure 11 experiment")
    axes[0].plot(red_time, red_velocity, "r.", label="published PTC curve")
    axes[0].plot([r["time_s"] for r in experiment], model_velocity, "b-",
                 label="DynamicLH2PoolX PTC")
    axes[0].set(xlabel="Time after comparison origin [s]",
                ylabel="Vaporization velocity [m/s]",
                title="Independent score of experimental points")
    axes[0].grid(alpha=0.2); axes[0].legend()
    axes[1].imshow(image)
    axes[1].plot([r["pixel_x"] for r in experiment], [r["pixel_y"] for r in experiment],
                 "bo", fillstyle="none")
    axes[1].axis("off"); axes[1].set_title("Extraction audit on source figure")
    figure.suptitle("Xie et al. 2023 Figure 11 | CC BY 4.0 | no fit to experiment")
    figure.savefig(args.output_dir / "figure11_validation.png", dpi=180)
    plt.close(figure)

    manifest = {
        "source_doi": "10.3390/pr11051415",
        "source_sha256": hashlib.sha256(args.pdf.read_bytes()).hexdigest(),
        "licence": "CC BY 4.0 (PDF page 1)", "figure": 11, "pdf_page": 11,
        "method": "embedded 870x649 RGB; calibrated endpoints; red components and isolated black 11x11 markers",
        "role_separation": "red curve recovers omitted prediction inputs; black points are untouched validation observations",
        "figure9_exclusion": "different run/clock; initial temperature field linking Figures 9 and 11 is not published",
        "read_off_bounds": {"time_s": 1.0, "velocity_m_s": 6.0e-6},
        "metrics": metrics,
        "gate": gate,
        "decision": ("PASS_FIXED_AREA_PTC_RATE_REPRODUCTION"
                     if passed else "REQUIRES_ITERATION"),
    }
    (args.output_dir / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    print(json.dumps(manifest, indent=2))


if __name__ == "__main__":
    main()
