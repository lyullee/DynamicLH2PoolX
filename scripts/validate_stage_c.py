"""Run and integrate the frozen Stage C reinforcement protocol."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import sys


ROOT = Path(__file__).resolve().parents[1]
PROTOCOL = ROOT / "data" / "stage_c_protocol.json"
SOURCES = ROOT / "data" / "source_manifest.json"
OUTPUT = ROOT / "outputs" / "stage_c"


def _run(command: list[str]) -> None:
    subprocess.run(command, cwd=ROOT, check=True)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dienhart-pdf", type=Path, required=True)
    parser.add_argument("--rr985-pdf", type=Path, required=True)
    parser.add_argument("--rr986-pdf", type=Path, required=True)
    parser.add_argument(
        "--reuse-existing", action="store_true",
        help="Integrate already-generated component manifests without rerunning",
    )
    args = parser.parse_args()
    if not args.reuse_existing:
        _run([sys.executable, "-m", "pytest", "-q"])
        _run([sys.executable, "scripts/run_stage_c_convergence.py"])
        _run([
            sys.executable, "scripts/run_validation_spreading.py",
            "--report-pdf", str(args.dienhart_pdf.resolve()),
        ])
        _run([
            sys.executable, "scripts/run_validation_hse_test6.py",
            "--rr985-pdf", str(args.rr985_pdf.resolve()),
            "--rr986-pdf", str(args.rr986_pdf.resolve()),
        ])

    paths = {
        "solution_verification": OUTPUT / "convergence" / "manifest.json",
        "juel_holdout": ROOT / "outputs" / "spreading_validation" / "manifest.json",
        "hse_radius_assessment": OUTPUT / "hse_test6" / "manifest.json",
    }
    missing = [str(path) for path in paths.values() if not path.exists()]
    if missing:
        raise FileNotFoundError(f"missing Stage C manifests: {missing}")
    manifests = {
        name: json.loads(path.read_text(encoding="utf-8"))
        for name, path in paths.items()
    }
    expected = {
        "solution_verification": "PASS_STAGE_C_SOLUTION_VERIFICATION",
        "juel_holdout": "PASS_RESTRICTED_SPREADING",
        "hse_radius_assessment": (
            "PASS_HSE_RADIUS_ASSESSMENT_ENDPOINTS_WITH_STRUCTURAL_LIMITATION"
        ),
    }
    checks = {
        name: manifests[name]["decision"] == decision
        for name, decision in expected.items()
    }
    protocol = json.loads(PROTOCOL.read_text(encoding="utf-8"))
    hse = manifests["hse_radius_assessment"]
    convergence = manifests["solution_verification"]
    juel = manifests["juel_holdout"]
    passed = all(checks.values())
    summary = {
        "protocol_id": protocol["protocol_id"],
        "integration_runner_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        "protocol_sha256": hashlib.sha256(PROTOCOL.read_bytes()).hexdigest(),
        "source_manifest_sha256": hashlib.sha256(SOURCES.read_bytes()).hexdigest(),
        "component_manifest_sha256": {
            name: hashlib.sha256(path.read_bytes()).hexdigest()
            for name, path in paths.items()
        },
        "component_checks": checks,
        "numerical_evidence": {
            "spatial_fine_change": convergence["spatial_fine_change"],
            "coupled_fine_change": convergence["coupled_fine_change"],
            "default_momentum_closure": (
                convergence["default_momentum_closure_fixed_before_run"]
            ),
        },
        "juel_holdout_metrics": [
            item for item in juel["metrics"] if item["role"] == "holdout"
        ],
        "juel_video_band_coverage": (
            juel["video_band_coverage_fraction_10_to_60_s"]
        ),
        "juel_parameter_sensitivity_not_ci": (
            juel["predeclared_parameter_sensitivity_not_confidence_interval"]
        ),
        "hse_assessment": {
            "data_quality": hse["data_quality"],
            "classification": hse["assessment_label"],
            "primary_result": hse["primary_result"],
            "checks": hse["assessment_checks"],
            "trajectory_diagnostic": hse["trajectory_metrics_diagnostic_only"],
        },
        "scope_and_use": {
            "dynamic_route": (
                "qualified only for the frozen declared-ground-inflow, horizontal, "
                "smooth-axisymmetric component scope"
            ),
            "hse_limit": (
                "end radius and thermocouple-defined dryout agree; the observed "
                "condensed-air solid expansion/retraction pulse is not reproduced"
            ),
            "ffi_manuscript": (
                "not a retroactive source reconstruction; the prior FFI manuscript "
                "continues to use static LH2PoolX v0.1.2 observed-footprint inputs"
            ),
        },
        "decision": (
            "PASS_RESTRICTED_STAGE_C_COMPONENT_SCOPE"
            if passed else "STAGE_C_REQUIRES_ITERATION"
        ),
    }
    OUTPUT.mkdir(parents=True, exist_ok=True)
    target = OUTPUT / "manifest.json"
    target.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(json.dumps(summary, indent=2))
    if not passed:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
