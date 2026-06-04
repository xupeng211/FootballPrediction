"""Tests for FotMob HTML hydration route probe no-write.

lifecycle: permanent
phase: FOTMOB-RAW-JSON-LONG-RUN-COLLECTOR-HTML-HYDRATION-ROUTE-PROBE-NO-WRITE

Validates URL construction, constraint enforcement, body-not-read safety.
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

SCRIPT = ROOT / "scripts/ops/fotmob_html_hydration_route_probe_no_write.py"
CHECKER = ROOT / "scripts/ops/fotmob_html_hydration_route_probe_no_write_check.py"

import fotmob_html_hydration_route_probe_no_write as pm  # noqa: E402


def _run(args: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(SCRIPT), *args], cwd=ROOT, text=True, capture_output=True, check=False
    )


def _base(tmp_path) -> list[str]:
    return [
        "--endpoint-probe-manifest",
        "docs/_manifests/fotmob_controlled_endpoint_candidate_probe_no_write_manifest.json",
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
        "test",
    ]


def test_script_exists():
    assert SCRIPT.exists()


def test_checker_exists():
    assert CHECKER.exists()


# --- URL construction ---
def test_url_builder_match_page():
    s = [{"match_id": "4813722", "route_code": "2ygkcb", "team_pair": "test"}]
    p = pm.build_plan(s, pm.ROUTE_TEMPLATES)
    assert p[0]["url_redacted"] == "https://www.fotmob.com/match/4813722"


def test_url_builder_matches_route():
    s = [{"match_id": "4813722", "route_code": "2ygkcb", "team_pair": "test"}]
    p = pm.build_plan(s, pm.ROUTE_TEMPLATES)
    assert p[1]["url_redacted"] == "https://www.fotmob.com/matches/2ygkcb/4813722"


# --- constraint validation ---
def test_max_samples_4_fails(tmp_path):
    assert _run(_base(tmp_path) + ["--max-samples", "4"]).returncode != 0


def test_max_templates_3_fails(tmp_path):
    assert _run(_base(tmp_path) + ["--max-route-templates", "3"]).returncode != 0


def test_max_requests_7_fails(tmp_path):
    assert _run(_base(tmp_path) + ["--max-network-requests", "7"]).returncode != 0


# --- dry-run ---
def test_dry_run_no_network(tmp_path):
    r = _run(_base(tmp_path) + ["--max-samples", "3", "--max-route-templates", "2"])
    assert r.returncode == 0
    m = json.loads(Path(tmp_path / "m.json").read_text(encoding="utf-8"))
    assert m["mode"] == "dry_run_probe_plan_only"
    assert m["probe_summary"]["network_requests_attempted"] == 0


# --- validation states ---
def test_observed():
    assert (
        pm.val_state({"status_code": 200, "content_type": "text/html; charset=utf-8"})
        == "html_route_observed"
    )


def test_redirect():
    assert (
        pm.val_state({"status_code": 301, "stop_reason": "redirect"})
        == "html_route_redirect_observed"
    )


def test_blocked_403():
    assert pm.val_state({"stop_reason": "blocked_403"}) == "html_route_blocked"


def test_invalid_404():
    assert pm.val_state({"stop_reason": "invalid_404"}) == "html_route_invalid"


def test_not_html():
    assert (
        pm.val_state({"status_code": 200, "content_type": "application/json"})
        == "html_route_not_html"
    )


# --- mocked probes ---
def test_mocked_200_html():
    mr = mock.MagicMock()
    mr.status = 200
    mr.headers = {"Content-Type": "text/html; charset=utf-8"}
    mr.geturl.return_value = "https://www.fotmob.com/match/4813722"
    mr.close = mock.MagicMock()
    with mock.patch("urllib.request.urlopen", return_value=mr):
        r = pm.probe_url("https://test")
        assert r["status_code"] == 200
        assert pm.val_state(r) == "html_route_observed"


def test_mocked_redirect():
    mr = mock.MagicMock()
    mr.status = 301
    mr.headers = {"Content-Type": "text/html", "Location": "https://www.fotmob.com/match/4813722/"}
    mr.geturl.return_value = "https://www.fotmob.com/match/4813722"
    mr.close = mock.MagicMock()
    with mock.patch("urllib.request.urlopen", return_value=mr):
        r = pm.probe_url("https://test")
        assert r["status_code"] == 301
        assert pm.val_state(r) == "html_route_redirect_observed"


def test_mocked_404():
    from urllib import error

    with mock.patch(
        "urllib.request.urlopen", side_effect=error.HTTPError("https://test", 404, "NF", {}, None)
    ):
        r = pm.probe_url("https://test")
        assert pm.val_state(r) == "html_route_invalid"


def test_mocked_403():
    from urllib import error

    with mock.patch(
        "urllib.request.urlopen", side_effect=error.HTTPError("https://test", 403, "F", {}, None)
    ):
        r = pm.probe_url("https://test")
        assert pm.val_state(r) == "html_route_blocked"


# --- manifest sections ---
def test_manifest_sections(tmp_path):
    r = _run(_base(tmp_path) + ["--max-samples", "3", "--max-route-templates", "2"])
    assert r.returncode == 0
    m = json.loads(Path(tmp_path / "m.json").read_text(encoding="utf-8"))
    for sec in [
        "schema_version",
        "phase",
        "mode",
        "inherited_endpoint_probe",
        "probe_selection",
        "probe_results",
        "probe_summary",
        "route_decision",
        "raw_write_readiness",
        "safety",
        "embedded_review",
        "recommended_next_phase",
    ]:
        assert sec in m, f"Missing: {sec}"


# --- safety ---
def test_dry_run_safety(tmp_path):
    r = _run(_base(tmp_path) + ["--max-samples", "3"])
    assert r.returncode == 0
    m = json.loads(Path(tmp_path / "m.json").read_text(encoding="utf-8"))
    s = m["safety"]
    for k in [
        "response_body_read",
        "raw_response_body_saved",
        "html_body_saved",
        "raw_json_write_performed",
        "db_write_performed",
        "scheduler_enabled",
        "browser_automation_performed",
    ]:
        assert s[k] is False, f"{k} must be false"


def test_readiness_values(tmp_path):
    r = _run(_base(tmp_path) + ["--max-samples", "3"])
    assert r.returncode == 0
    m = json.loads(Path(tmp_path / "m.json").read_text(encoding="utf-8"))
    rw = m["raw_write_readiness"]
    assert rw["json_validated_count"] == 0
    assert rw["raw_write_eligible_count"] == 0


def test_next_phase_not_raw(tmp_path):
    r = _run(_base(tmp_path) + ["--max-samples", "3"])
    assert r.returncode == 0
    m = json.loads(Path(tmp_path / "m.json").read_text(encoding="utf-8"))
    for w in ["RAW-JSON-DEV-WRITE", "DIRECT-RAW-WRITE"]:
        assert w not in m["recommended_next_phase"]


def test_all_probe_results_safe(tmp_path):
    r = _run(_base(tmp_path) + ["--max-samples", "3", "--max-route-templates", "2"])
    assert r.returncode == 0
    m = json.loads(Path(tmp_path / "m.json").read_text(encoding="utf-8"))
    for p in m["probe_results"]:
        assert p["body_read"] is False
        assert p["raw_response_body_saved"] is False
        assert p["html_body_saved"] is False
        assert p["raw_write_eligible"] is False


# --- API endpoint exclusion ---
def test_no_api_endpoint_in_templates():
    for t in pm.ROUTE_TEMPLATES:
        assert "/api/" not in t["template"]
        assert "matchDetails" not in t["template"]
