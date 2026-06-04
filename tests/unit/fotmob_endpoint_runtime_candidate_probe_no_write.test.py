"""Tests for FotMob endpoint runtime candidate probe no-write.

lifecycle: permanent
"""

from __future__ import annotations

import json
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts/ops"))

SCRIPT = ROOT / "scripts/ops/fotmob_endpoint_runtime_candidate_probe_no_write.py"
CHECKER = ROOT / "scripts/ops/fotmob_endpoint_runtime_candidate_probe_no_write_check.py"

import fotmob_endpoint_runtime_candidate_probe_no_write as mod  # noqa: E402


def _base_argv(tmp_path: Path) -> list[str]:
    return [
        "--plan-manifest",
        "docs/_manifests/fotmob_endpoint_runtime_request_discovery_plan_no_write_manifest.json",
        "--seed-manifest",
        "docs/_manifests/fotmob_known_match_page_user_seeds_parse_no_write_manifest.json",
        "--output-manifest",
        str(tmp_path / "m.json"),
        "--report",
        str(tmp_path / "r.md"),
        "--review-report",
        str(tmp_path / "rv.md"),
        "--decision-report",
        str(tmp_path / "d.md"),
        "--run-id",
        "test-run",
        "--max-candidates",
        "3",
        "--max-samples",
        "2",
        "--max-network-requests",
        "6",
        "--max-body-bytes",
        "262144",
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


def test_dry_run_no_network(tmp_path):
    assert _run(tmp_path).returncode == 0
    m = _manifest(tmp_path)
    assert m["mode"] == "dry_run_endpoint_candidate_probe_plan_only"
    assert m["safety"]["network_fetch_performed"] is False
    assert m["probe_summary"]["network_requests_attempted"] == 0


def test_selected_candidates_limited(tmp_path):
    assert _run(tmp_path).returncode == 0
    selected = _manifest(tmp_path)["selected_candidates"]
    assert set(selected) == {"ep-004", "ep-005", "ep-006"}


def test_max_candidates_exceeded_fails(tmp_path):
    assert _run(tmp_path, ["--max-candidates", "5"]).returncode != 0


def test_max_samples_exceeded_fails(tmp_path):
    assert _run(tmp_path, ["--max-samples", "5"]).returncode != 0


def test_max_network_requests_exceeded_fails(tmp_path):
    assert _run(tmp_path, ["--max-network-requests", "10"]).returncode != 0


def test_max_body_bytes_exceeded_fails(tmp_path):
    assert _run(tmp_path, ["--max-body-bytes", "999999"]).returncode != 0


def test_no_response_body_saved(tmp_path):
    assert _run(tmp_path).returncode == 0
    safety = _manifest(tmp_path)["safety"]
    for flag in [
        "response_body_saved",
        "raw_response_body_saved",
        "raw_json_write_performed",
        "full_html_saved",
        "db_write_performed",
    ]:
        assert safety[flag] is False


def test_no_scheduler_no_feature_parse(tmp_path):
    assert _run(tmp_path).returncode == 0
    safety = _manifest(tmp_path)["safety"]
    assert safety["scheduler_enabled"] is False
    assert safety["feature_parse_performed"] is False


def test_no_browser_cookie_captcha_proxy(tmp_path):
    assert _run(tmp_path).returncode == 0
    safety = _manifest(tmp_path)["safety"]
    assert safety["browser_automation_performed"] is False
    assert safety["cookie_harvesting_performed"] is False
    assert safety["captcha_bypass_performed"] is False
    assert safety["proxy_rotation_performed"] is False


def test_readiness_blocked(tmp_path):
    assert _run(tmp_path).returncode == 0
    rd = _manifest(tmp_path)["raw_write_readiness"]
    assert rd["json_validated_count"] == 0
    assert rd["raw_write_eligible_count"] == 0


def test_recommended_next_safe(tmp_path):
    assert _run(tmp_path).returncode == 0
    rec = _manifest(tmp_path)["recommended_next_phase"]
    assert "DIRECT-RAW-WRITE" not in rec
    assert "RAW-JSON-WRITE" not in rec


def test_classify_strong():
    assert (
        mod._classify_candidate(8, "application/json", True, 200)
        == "strong_endpoint_match_detail_candidate"
    )


def test_classify_weak():
    assert (
        mod._classify_candidate(5, "application/json", True, 200)
        == "weak_endpoint_match_detail_candidate"
    )


def test_classify_blocked_403():
    assert mod._classify_candidate(0, "text/html", False, 403) == "blocked_403"


def test_classify_blocked_429():
    assert mod._classify_candidate(0, "text/html", False, 429) == "blocked_429"


def test_classify_not_found():
    assert mod._classify_candidate(0, "text/html", False, 404) == "not_found_404"


def test_classify_html_not_json():
    assert (
        mod._classify_candidate(0, "text/html", False, 200)
        == "rejected_or_generic_endpoint_candidate"
    )


def test_signal_score_matches_terms():
    paths = [
        {"key_path": "matchDetails.match.header", "key_name": "header"},
        {"key_path": "matchDetails.match.content.stats", "key_name": "stats"},
        {"key_path": "matchDetails.match.lineup", "key_name": "lineup"},
    ]
    assert mod._score_signal(paths, "4813722", "2ygkcb") > 3


def test_signal_score_penalizes_generic():
    paths = [
        {"key_path": "notableMatches", "key_name": "notableMatches"},
        {"key_path": "translations", "key_name": "translations"},
    ]
    assert mod._score_signal(paths, "4813722", "2ygkcb") < 0


def test_is_json_like_true():
    ok, parsed = mod._is_json_like('{"a": 1}', "application/json")
    assert ok
    assert parsed == {"a": 1}


def test_is_json_like_false_html():
    ok, _ = mod._is_json_like("<html>", "text/html")
    assert not ok


def test_checker_passes(tmp_path):
    assert _run(tmp_path).returncode == 0
    cr = subprocess.run(
        [sys.executable, str(CHECKER)], cwd=ROOT, text=True, capture_output=True, check=False
    )
    assert cr.returncode == 0, f"checker failed: {cr.stderr}"
