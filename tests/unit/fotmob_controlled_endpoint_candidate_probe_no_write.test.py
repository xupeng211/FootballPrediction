"""Tests for FotMob controlled endpoint candidate probe no-write.

lifecycle: permanent
phase: FOTMOB-RAW-JSON-LONG-RUN-COLLECTOR-CONTROLLED-ENDPOINT-CANDIDATE-PROBE-NO-WRITE

Validates URL construction, constraint enforcement, metadata-only safety.
Network tests use mocked responses. No real network, no DB, no raw write.
"""

from __future__ import annotations

import json
from pathlib import Path
import subprocess
import sys
from unittest import mock

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts/ops"))

SCRIPT = ROOT / "scripts/ops/fotmob_controlled_endpoint_candidate_probe_no_write.py"
CHECKER = ROOT / "scripts/ops/fotmob_controlled_endpoint_candidate_probe_no_write_check.py"

import fotmob_controlled_endpoint_candidate_probe_no_write as pm  # noqa: E402


def _run(args: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(SCRIPT), *args], cwd=ROOT, text=True, capture_output=True, check=False
    )


def _base_args(tmp_path) -> list[str]:
    return [
        "--endpoint-review-manifest",
        "docs/_manifests/fotmob_json_endpoint_review_no_write_manifest.json",
        "--seed-manifest",
        "docs/_manifests/fotmob_known_match_page_user_seeds_parse_no_write_manifest.json",
        "--output-manifest",
        str(tmp_path / "manifest.json"),
        "--report",
        str(tmp_path / "report.md"),
        "--review-report",
        str(tmp_path / "review.md"),
        "--decision-report",
        str(tmp_path / "decision.md"),
        "--run-id",
        "test_v1",
    ]


# --- file existence ---
def test_script_exists():
    assert SCRIPT.exists()


def test_checker_exists():
    assert CHECKER.exists()


# --- URL construction ---
def test_url_builder_api_data():
    samples = [{"match_id": "4813722", "route_code": "2ygkcb", "team_pair": "test"}]
    plan = pm.build_urls(samples, [pm.ENDPOINT_TEMPLATES[0]])
    assert plan[0]["url_redacted"] == "https://www.fotmob.com/api/data/matchDetails?matchId=4813722"


def test_url_builder_match_page():
    samples = [{"match_id": "4813722", "route_code": "2ygkcb", "team_pair": "test"}]
    plan = pm.build_urls(samples, [pm.ENDPOINT_TEMPLATES[1]])
    assert plan[0]["url_redacted"] == "https://www.fotmob.com/match/4813722"


def test_url_builder_matches_route():
    samples = [{"match_id": "4813722", "route_code": "2ygkcb", "team_pair": "test"}]
    plan = pm.build_urls(samples, [pm.ENDPOINT_TEMPLATES[2]])
    assert plan[0]["url_redacted"] == "https://www.fotmob.com/matches/2ygkcb/4813722"


# --- dry-run ---
def test_dry_run_no_network(tmp_path):
    r = _run(_base_args(tmp_path) + ["--max-samples", "3", "--max-endpoint-templates", "3"])
    assert r.returncode == 0, r.stderr
    m = json.loads(Path(tmp_path / "manifest.json").read_text(encoding="utf-8"))
    assert m["mode"] == "dry_run_probe_plan_only"
    assert m["probe_summary"]["network_requests_attempted"] == 0


# --- constraint validation ---
def test_max_samples_4_fails(tmp_path):
    r = _run(_base_args(tmp_path) + ["--max-samples", "4"])
    assert r.returncode != 0


def test_max_templates_4_fails(tmp_path):
    r = _run(_base_args(tmp_path) + ["--max-endpoint-templates", "4"])
    assert r.returncode != 0


def test_max_requests_10_fails(tmp_path):
    r = _run(_base_args(tmp_path) + ["--max-network-requests", "10"])
    assert r.returncode != 0


# --- validation states ---
def test_validation_state_json_ok():
    assert pm.validation_state({"json_parse_ok": True}) == "endpoint_candidate_json_observed"


def test_validation_state_blocked_403():
    assert pm.validation_state({"stop_reason": "blocked_403"}) == "endpoint_candidate_blocked"


def test_validation_state_blocked_429():
    assert pm.validation_state({"stop_reason": "blocked_429"}) == "endpoint_candidate_blocked"


def test_validation_state_invalid_404():
    assert pm.validation_state({"stop_reason": "invalid_404"}) == "endpoint_candidate_invalid"


def test_validation_state_html():
    assert pm.validation_state({"content_type": "text/html"}) == "endpoint_candidate_html"


# --- mocked probes ---
def test_mocked_json_response():
    mr = mock.MagicMock()
    mr.status = 200
    mr.headers = {"Content-Type": "application/json; charset=utf-8"}
    mr.geturl.return_value = "https://www.fotmob.com/api/data/matchDetails?matchId=4813722"
    mr.read.return_value = b'{"matchId":4813722,"header":{"teams":[]},"general":{},"content":{}}'
    with mock.patch("urllib.request.urlopen", return_value=mr):
        r = pm.probe_url("https://test", 10)
        assert r["json_parse_ok"] is True
        assert "matchId" in r["top_level_key_names"]


def test_mocked_html_response():
    mr = mock.MagicMock()
    mr.status = 200
    mr.headers = {"Content-Type": "text/html; charset=utf-8"}
    mr.geturl.return_value = "https://www.fotmob.com/match/4813722"
    with mock.patch("urllib.request.urlopen", return_value=mr):
        r = pm.probe_url("https://test", 10)
        assert r["json_parse_ok"] is False
        assert pm.validation_state(r) == "endpoint_candidate_html"


def test_mocked_404():
    from urllib import error

    with mock.patch(
        "urllib.request.urlopen",
        side_effect=error.HTTPError("https://test", 404, "Not Found", {}, None),
    ):
        r = pm.probe_url("https://test", 10)
        assert r["status_code"] == 404
        assert pm.validation_state(r) == "endpoint_candidate_invalid"


def test_mocked_403():
    from urllib import error

    with mock.patch(
        "urllib.request.urlopen",
        side_effect=error.HTTPError("https://test", 403, "Forbidden", {}, None),
    ):
        r = pm.probe_url("https://test", 10)
        assert pm.validation_state(r) == "endpoint_candidate_blocked"


# --- manifest sections ---
def test_manifest_sections(tmp_path):
    r = _run(_base_args(tmp_path) + ["--max-samples", "3", "--max-endpoint-templates", "3"])
    assert r.returncode == 0
    m = json.loads(Path(tmp_path / "manifest.json").read_text(encoding="utf-8"))
    for sec in [
        "schema_version",
        "phase",
        "mode",
        "inherited_endpoint_review",
        "probe_selection",
        "probe_results",
        "probe_summary",
        "endpoint_decision",
        "raw_write_readiness",
        "safety",
        "embedded_review",
        "recommended_next_phase",
    ]:
        assert sec in m, f"Missing: {sec}"


# --- safety ---
def test_dry_run_safety(tmp_path):
    r = _run(_base_args(tmp_path) + ["--max-samples", "3"])
    assert r.returncode == 0
    m = json.loads(Path(tmp_path / "manifest.json").read_text(encoding="utf-8"))
    s = m["safety"]
    for k in [
        "raw_response_body_saved",
        "raw_json_write_performed",
        "db_write_performed",
        "scheduler_enabled",
        "feature_parse_performed",
        "browser_automation_performed",
    ]:
        assert s[k] is False, f"{k} must be false"


def test_dry_run_readiness(tmp_path):
    r = _run(_base_args(tmp_path) + ["--max-samples", "3"])
    assert r.returncode == 0
    m = json.loads(Path(tmp_path / "manifest.json").read_text(encoding="utf-8"))
    rw = m["raw_write_readiness"]
    assert rw["json_validated_count"] == 0
    assert rw["raw_write_eligible_count"] == 0


def test_next_phase_not_raw_write(tmp_path):
    r = _run(_base_args(tmp_path) + ["--max-samples", "3"])
    assert r.returncode == 0
    m = json.loads(Path(tmp_path / "manifest.json").read_text(encoding="utf-8"))
    for w in ["RAW-JSON-DEV-WRITE", "DIRECT-RAW-WRITE"]:
        assert w not in m["recommended_next_phase"]


# --- probe results safety ---
def test_all_probe_results_safe(tmp_path):
    r = _run(_base_args(tmp_path) + ["--max-samples", "3", "--max-endpoint-templates", "3"])
    assert r.returncode == 0
    m = json.loads(Path(tmp_path / "manifest.json").read_text(encoding="utf-8"))
    for p in m["probe_results"]:
        assert p["raw_write_eligible"] is False
        assert p["raw_json_write_performed"] is False
        assert p["raw_response_body_saved"] is False
        assert p["db_write_performed"] is False
