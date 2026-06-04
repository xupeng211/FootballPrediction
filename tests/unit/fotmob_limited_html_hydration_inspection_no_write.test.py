"""Tests for limited HTML hydration inspection no-write.

lifecycle: permanent
phase: FOTMOB-RAW-JSON-LONG-RUN-COLLECTOR-LIMITED-HTML-HYDRATION-INSPECTION-NO-WRITE
"""

from __future__ import annotations

import json
from pathlib import Path
import subprocess
import sys
from unittest import mock

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts/ops"))

SCRIPT = ROOT / "scripts/ops/fotmob_limited_html_hydration_inspection_no_write.py"
CHECKER = ROOT / "scripts/ops/fotmob_limited_html_hydration_inspection_no_write_check.py"

import fotmob_limited_html_hydration_inspection_no_write as pm  # noqa: E402


def _run(args):
    return subprocess.run(
        [sys.executable, str(SCRIPT), *args], cwd=ROOT, text=True, capture_output=True, check=False
    )


def _base(tmp_path):
    return [
        "--extraction-plan-manifest",
        "docs/_manifests/fotmob_html_hydration_extraction_plan_no_write_manifest.json",
        "--route-probe-manifest",
        "docs/_manifests/fotmob_html_hydration_route_probe_no_write_manifest.json",
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


# --- constraints ---
def test_max_samples_3_fails(tmp_path):
    assert _run(_base(tmp_path) + ["--max-samples", "3"]).returncode != 0


def test_max_templates_3_fails(tmp_path):
    assert _run(_base(tmp_path) + ["--max-route-templates", "3"]).returncode != 0


def test_max_requests_5_fails(tmp_path):
    assert _run(_base(tmp_path) + ["--max-network-requests", "5"]).returncode != 0


def test_max_body_exceeded_fails(tmp_path):
    assert _run(_base(tmp_path) + ["--max-body-bytes", "999999"]).returncode != 0


# --- URL builder ---
def test_url_match_page():
    samples = [{"match_id": "4813722", "route_code": "2ygkcb", "team_pair": "test"}]
    plan = pm.build_plan(samples, pm.ROUTES, 262144)
    assert "https://www.fotmob.com/match/4813722" in plan[0]["url_redacted"]


def test_url_matches_route():
    samples = [{"match_id": "4813722", "route_code": "2ygkcb", "team_pair": "test"}]
    plan = pm.build_plan(samples, pm.ROUTES, 262144)
    assert "https://www.fotmob.com/matches/2ygkcb/4813722" in plan[1]["url_redacted"]


# --- dry-run ---
def test_dry_run(tmp_path):
    r = _run(_base(tmp_path) + ["--max-samples", "2", "--max-route-templates", "2"])
    assert r.returncode == 0
    m = json.loads(Path(tmp_path / "m.json").read_text(encoding="utf-8"))
    assert m["mode"] == "dry_run_inspection_plan_only"
    assert m["inspection_summary"]["network_requests_attempted"] == 0


# --- mocked marker detection ---
def test_mocked_nextdata_marker():
    html = b'<html><head></head><body><script id="__NEXT_DATA__" type="application/json">{"props":{"pageProps":{"matchId":4813722}}}</script></body></html>'
    mr = mock.MagicMock()
    mr.status = 200
    mr.headers = {"Content-Type": "text/html; charset=utf-8", "Content-Length": str(len(html))}
    mr.read.return_value = html
    mr.close = mock.MagicMock()
    with mock.patch("urllib.request.urlopen", return_value=mr):
        r = pm.inspect_url("https://test", 262144)
        assert r["marker_presence"]["__NEXT_DATA__"] is True
        assert r["marker_presence"]["pageProps"] is True
        assert r["match_id_seen"] is True


def test_mocked_no_marker():
    html = b"<html><head></head><body><p>No markers here</p></body></html>"
    mr = mock.MagicMock()
    mr.status = 200
    mr.headers = {"Content-Type": "text/html; charset=utf-8"}
    mr.read.return_value = html
    mr.close = mock.MagicMock()
    with mock.patch("urllib.request.urlopen", return_value=mr):
        r = pm.inspect_url("https://test", 262144)
        assert pm.val_state(r) == "hydration_marker_missing"


def test_mocked_structure_observed():
    html = b'<script id="__NEXT_DATA__" type="application/json">{"matchId":4813722,"header":{"teams":[]},"general":{},"content":{}}</script>'
    mr = mock.MagicMock()
    mr.status = 200
    mr.headers = {"Content-Type": "text/html; charset=utf-8"}
    mr.read.return_value = html
    mr.close = mock.MagicMock()
    with mock.patch("urllib.request.urlopen", return_value=mr):
        r = pm.inspect_url("https://test", 262144)
        assert pm.val_state(r) == "hydration_structure_observed"
        assert len(r["top_level_key_names"]) >= 2


# --- mocked error states ---
def test_mocked_403():
    from urllib import error

    with mock.patch("urllib.request.urlopen", side_effect=error.HTTPError("", 403, "F", {}, None)):
        r = pm.inspect_url("https://test", 262144)
        assert pm.val_state(r) == "hydration_route_blocked"


def test_mocked_404():
    from urllib import error

    with mock.patch("urllib.request.urlopen", side_effect=error.HTTPError("", 404, "NF", {}, None)):
        r = pm.inspect_url("https://test", 262144)
        assert pm.val_state(r) == "hydration_route_invalid"


# --- safety ---
def test_safety_flags(tmp_path):
    r = _run(_base(tmp_path) + ["--max-samples", "2"])
    assert r.returncode == 0
    m = json.loads(Path(tmp_path / "m.json").read_text(encoding="utf-8"))
    s = m["safety"]
    for k in [
        "full_html_saved",
        "html_body_saved",
        "raw_json_write_performed",
        "db_write_performed",
    ]:
        assert s[k] is False, k


def test_readiness(tmp_path):
    r = _run(_base(tmp_path) + ["--max-samples", "2"])
    assert r.returncode == 0
    m = json.loads(Path(tmp_path / "m.json").read_text(encoding="utf-8"))
    rw = m["raw_write_readiness"]
    assert rw["json_validated_count"] == 0
    assert rw["raw_write_eligible_count"] == 0


def test_next_phase_not_raw(tmp_path):
    r = _run(_base(tmp_path) + ["--max-samples", "2"])
    assert r.returncode == 0
    m = json.loads(Path(tmp_path / "m.json").read_text(encoding="utf-8"))
    for w in ["RAW-JSON-DEV-WRITE", "DIRECT-RAW-WRITE"]:
        assert w not in m["recommended_next_phase"]
