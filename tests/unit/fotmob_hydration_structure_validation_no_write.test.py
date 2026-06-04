"""Tests for hydration structure validation no-write."""

from __future__ import annotations

import json
from pathlib import Path
import subprocess
import sys
from unittest import mock

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts/ops"))

SCRIPT = ROOT / "scripts/ops/fotmob_hydration_structure_validation_no_write.py"
CHECKER = ROOT / "scripts/ops/fotmob_hydration_structure_validation_no_write_check.py"

import fotmob_hydration_structure_validation_no_write as pm  # noqa: E402


def _run(args):
    return subprocess.run(
        [sys.executable, str(SCRIPT), *args], cwd=ROOT, text=True, capture_output=True, check=False
    )


def _base(tmp_path):
    return [
        "--inspection-manifest",
        "docs/_manifests/fotmob_limited_html_hydration_inspection_no_write_manifest.json",
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


def test_max_samples_3_fails(tmp_path):
    assert _run(_base(tmp_path) + ["--max-samples", "3"]).returncode != 0


def test_max_requests_3_fails(tmp_path):
    assert _run(_base(tmp_path) + ["--max-network-requests", "3"]).returncode != 0


def test_max_body_exceeded_fails(tmp_path):
    assert _run(_base(tmp_path) + ["--max-body-bytes", "999999"]).returncode != 0


def test_route_restricted():
    assert "/matches/" in pm.ROUTE["template"]
    assert "/api/" not in pm.ROUTE["template"]


def test_dry_run(tmp_path):
    r = _run(_base(tmp_path) + ["--max-samples", "2"])
    assert r.returncode == 0
    m = json.loads(Path(tmp_path / "m.json").read_text(encoding="utf-8"))
    assert m["mode"] == "dry_run_validation_plan_only"


# --- structure validation scoring ---
def test_score_high_on_match_detail():
    paths = ["matchId", "header", "general", "content", "teams", "status"]
    assert pm.score_subtree(paths, "4813722") >= 8


def test_score_low_on_config():
    paths = ["CountryCodes", "ENG", "Language", "MON"]
    assert pm.score_subtree(paths, "4813722") <= 0


def test_scan_keys_dict():
    obj = {"props": {"pageProps": {"matchId": 1, "header": {"teams": []}, "general": {}}}}
    paths = pm.scan_keys(obj)
    assert any("pageProps.matchId" in p or "matchId" in p for p in paths)
    assert any("header" in p for p in paths)


# --- state from validation ---
def test_state_candidate():
    r = {
        "next_data_marker_present": True,
        "next_data_json_parse_ok": True,
        "candidate_match_detail_score": 7,
    }
    assert pm.state_from_validation(r, "4813722") == "hydration_match_detail_candidate_observed"


def test_state_partial():
    r = {
        "next_data_marker_present": True,
        "next_data_json_parse_ok": True,
        "candidate_match_detail_score": 4,
    }
    assert pm.state_from_validation(r, "4813722") == "hydration_partial_match_detail_candidate"


def test_state_generic():
    r = {
        "next_data_marker_present": True,
        "next_data_json_parse_ok": True,
        "candidate_match_detail_score": 0,
        "pageProps_present": True,
    }
    assert pm.state_from_validation(r, "4813722") == "hydration_generic_structure_only"


# --- mocked structure validation ---
def test_mocked_structure_with_matchdetail():
    html = b'<script id="__NEXT_DATA__" type="application/json">{"props":{"pageProps":{"matchId":4813722,"header":{"teams":[]},"general":{"matchTimeUTC":"2026-01-01T12:00:00Z"},"content":{}}}}</script>'
    mr = mock.MagicMock()
    mr.status = 200
    mr.headers = {"Content-Type": "text/html; charset=utf-8"}
    mr.read.return_value = html
    mr.close = mock.MagicMock()
    with mock.patch("urllib.request.urlopen", return_value=mr):
        r = pm.probe_and_validate("https://test", 524288, "4813722")
        assert r["next_data_json_parse_ok"] is True
        assert r["pageProps_present"] is True
        assert r["target_match_id_seen"] is True
        assert r["candidate_match_detail_score"] >= 3


# --- safety ---
def test_safety_flags(tmp_path):
    r = _run(_base(tmp_path) + ["--max-samples", "2"])
    assert r.returncode == 0
    m = json.loads(Path(tmp_path / "m.json").read_text(encoding="utf-8"))
    s = m["safety"]
    for k in [
        "full_html_saved",
        "full_next_data_saved",
        "raw_json_write_performed",
        "db_write_performed",
    ]:
        assert s[k] is False


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
