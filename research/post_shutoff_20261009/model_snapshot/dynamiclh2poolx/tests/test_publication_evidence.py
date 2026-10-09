"""Regression checks for the tracked manuscript evidence snapshot."""

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_stage_c_evidence_snapshot_is_complete_and_scoped() -> None:
    payload = json.loads((ROOT / "data" / "stage_c_evidence.json").read_text())

    assert payload["decision"] == "PASS_RESTRICTED_STAGE_C_COMPONENT_SCOPE"
    assert all(payload["component_checks"].values())
    assert payload["c2_juel_holdout"]["water_trial_4"]["video_band_coverage"] == 1.0
    assert payload["c2_juel_holdout"]["aluminium_trial_6"]["video_band_coverage"] == 1.0
    assert payload["c3_hse_test6"]["condensed_air_deposition_peak_reproduced"] is False
    assert "atmospheric dispersion" in payload["excluded_claims"]

