"""Tests for FotMob endpoint runtime request discovery plan no-write.

lifecycle: permanent
"""

from __future__ import annotations

import json
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts/ops"))

SCRIPT = ROOT / "scripts/ops/fotmob_endpoint_runtime_request_discovery_plan_no_write.py"
CHECKER = ROOT / "scripts/ops/fotmob_endpoint_runtime_request_discovery_plan_no_write_check.py"

import fotmob_endpoint_runtime_request_discovery_plan_no_write as mod  # noqa: E402


def _base_argv(tmp_path: Path) -> list[str]:
    return [
        "--no-embedded-detail-manifest",
        "docs/_manifests/fotmob_page_no_embedded_detail_decision_no_write_manifest.json",
        "--route-variant-manifest",
        "docs/_manifests/fotmob_hydration_route_variant_followup_no_write_manifest.json",
        "--keyspace-manifest",
        "docs/_manifests/fotmob_hydration_keyspace_review_no_write_manifest.json",
        "--endpoint-probe-manifest",
        "docs/_manifests/fotmob_controlled_endpoint_candidate_probe_no_write_manifest.json",
        "--output-manifest",
        str(tmp_path / "m.json"),
        "--report",
        str(tmp_path / "r.md"),
        "--review-report",
        str(tmp_path / "rv.md"),
        "--next-plan",
        str(tmp_path / "n.md"),
        "--run-id",
        "test-run",
    ]


def _run(tmp_path: Path, extra: list[str] | None = None) -> subprocess.CompletedProcess[str]:
    argv = _base_argv(tmp_path) + (extra or [])
    return subprocess.run(
        [sys.executable, str(SCRIPT), *argv], cwd=ROOT, text=True, capture_output=True, check=False
    )


def _manifest(tmp_path: Path) -> dict:
    return json.loads((tmp_path / "m.json").read_text(encoding="utf-8"))


def test_script_exists():
    assert SCRIPT.exists()


def test_checker_exists():
    assert CHECKER.exists()


def test_missing_manifest_handled(tmp_path):
    argv = _base_argv(tmp_path)
    argv[1] = "docs/_manifests/missing.json"
    result = subprocess.run(
        [sys.executable, str(SCRIPT), *argv], cwd=ROOT, text=True, capture_output=True, check=False
    )
    assert result.returncode == 0
    m = json.loads((tmp_path / "m.json").read_text(encoding="utf-8"))
    assert "docs/_manifests/missing.json" in m.get("missing_inputs", [])


def test_html_hydration_exhausted_inherited(tmp_path):
    result = _run(tmp_path)
    assert result.returncode == 0
    d = _manifest(tmp_path)["inherited_no_embedded_detail_decision"]
    assert d["html_hydration_route_status"] == "exhausted_no_embedded_match_detail"
    assert d["page_level_next_data_status"] == "no_match_detail_json_embedded"


def test_direct_api_failures_inherited(tmp_path):
    result = _run(tmp_path)
    assert result.returncode == 0
    ep = _manifest(tmp_path)["inherited_endpoint_failures"]
    assert ep["api_matchDetails_status"] == "404_or_invalid"
    assert ep["api_data_matchDetails_status"] == "403_or_blocked"


def test_historical_code_review_generates_inventory(tmp_path):
    result = _run(tmp_path)
    assert result.returncode == 0
    hist = _manifest(tmp_path)["historical_code_review"]
    assert hist["files_reviewed_count"] > 0
    inv = _manifest(tmp_path)["endpoint_candidate_inventory"]
    assert inv["candidate_count"] > 0


def test_next_probe_candidate_count_bounded(tmp_path):
    result = _run(tmp_path)
    assert result.returncode == 0
    inv = _manifest(tmp_path)["endpoint_candidate_inventory"]
    assert inv["next_probe_candidate_count"] <= 3


def test_max_candidates_bounded(tmp_path):
    result = _run(tmp_path)
    assert result.returncode == 0
    probe = _manifest(tmp_path)["next_controlled_probe_plan"]
    assert probe["max_candidates"] <= 3


def test_max_samples_bounded(tmp_path):
    assert _run(tmp_path).returncode == 0
    probe = _manifest(tmp_path)["next_controlled_probe_plan"]
    assert probe["max_samples"] <= 2


def test_max_network_requests_bounded(tmp_path):
    assert _run(tmp_path).returncode == 0
    probe = _manifest(tmp_path)["next_controlled_probe_plan"]
    assert probe["max_network_requests"] <= 6


def test_max_body_bytes_bounded(tmp_path):
    assert _run(tmp_path).returncode == 0
    probe = _manifest(tmp_path)["next_controlled_probe_plan"]
    assert probe["max_body_bytes"] <= 262144


def test_browser_automation_forbidden(tmp_path):
    assert _run(tmp_path).returncode == 0
    probe = _manifest(tmp_path)["next_controlled_probe_plan"]
    assert probe["browser_automation_allowed"] is False


def test_cookie_harvesting_forbidden(tmp_path):
    assert _run(tmp_path).returncode == 0
    probe = _manifest(tmp_path)["next_controlled_probe_plan"]
    assert probe["cookie_harvesting_allowed"] is False


def test_captcha_bypass_forbidden(tmp_path):
    assert _run(tmp_path).returncode == 0
    probe = _manifest(tmp_path)["next_controlled_probe_plan"]
    assert probe["captcha_bypass_allowed"] is False


def test_proxy_rotation_forbidden(tmp_path):
    assert _run(tmp_path).returncode == 0
    probe = _manifest(tmp_path)["next_controlled_probe_plan"]
    assert probe["proxy_rotation_allowed"] is False


def test_db_write_forbidden(tmp_path):
    assert _run(tmp_path).returncode == 0
    probe = _manifest(tmp_path)["next_controlled_probe_plan"]
    assert probe["db_write_allowed"] is False


def test_raw_write_forbidden(tmp_path):
    assert _run(tmp_path).returncode == 0
    probe = _manifest(tmp_path)["next_controlled_probe_plan"]
    assert probe["raw_write_allowed"] is False


def test_no_network(tmp_path):
    assert _run(tmp_path).returncode == 0
    safety = _manifest(tmp_path)["safety"]
    assert safety["network_fetch_performed"] is False
    assert safety["response_body_read"] is False


def test_no_html_next_data_raw_json_db(tmp_path):
    assert _run(tmp_path).returncode == 0
    safety = _manifest(tmp_path)["safety"]
    for flag in [
        "full_html_saved",
        "html_body_saved",
        "full_next_data_saved",
        "raw_json_write_performed",
        "db_write_performed",
    ]:
        assert safety[flag] is False


def test_readiness_blocked(tmp_path):
    assert _run(tmp_path).returncode == 0
    readiness = _manifest(tmp_path)["raw_write_readiness"]
    assert readiness["json_validated_count"] == 0
    assert readiness["raw_write_eligible_count"] == 0


def test_recommended_next_safe(tmp_path):
    assert _run(tmp_path).returncode == 0
    rec = _manifest(tmp_path)["recommended_next_phase"]
    assert "DIRECT-RAW-WRITE" not in rec
    assert "RAW-JSON-WRITE" not in rec


def test_checker_passes(tmp_path):
    assert _run(tmp_path).returncode == 0
    cr = subprocess.run(
        [sys.executable, str(CHECKER)], cwd=ROOT, text=True, capture_output=True, check=False
    )
    assert cr.returncode == 0, f"checker failed: {cr.stderr}"
