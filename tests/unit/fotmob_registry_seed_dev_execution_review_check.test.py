"""Tests for FotMob registry seed dev execution review artifacts.

lifecycle: permanent
phase: FOTMOB-RAW-JSON-LONG-RUN-COLLECTOR-REGISTRY-SEED-DEV-EXECUTION-REVIEW
"""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
REVIEW_REPORT_PATH = REPO_ROOT / "docs/_reports/FOTMOB_REGISTRY_SEED_DEV_EXECUTION_REVIEW.md"
REVIEW_MANIFEST_PATH = (
    REPO_ROOT / "docs/_manifests/fotmob_registry_seed_dev_execution_review_manifest.json"
)
REVIEW_HELPER_PATH = REPO_ROOT / "scripts/ops/fotmob_registry_seed_dev_execution_review_check.py"
MANIFEST_PATH = REPO_ROOT / "docs/_manifests/fotmob_registry_seed_dev_execution_manifest.json"

REVIEWED_PR = 1429


def _text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _json(path: Path) -> dict:
    return json.loads(_text(path))


def _load_helper():
    spec = importlib.util.spec_from_file_location(
        "fotmob_registry_seed_dev_execution_review_check", REVIEW_HELPER_PATH
    )
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


# File existence
def test_review_report_exists():
    assert REVIEW_REPORT_PATH.exists()


def test_review_manifest_exists():
    assert REVIEW_MANIFEST_PATH.exists()


def test_review_helper_exists():
    assert REVIEW_HELPER_PATH.exists()


# Review manifest
def test_review_manifest_metadata():
    m = _json(REVIEW_MANIFEST_PATH)
    assert m["reviewed_pr"] == REVIEWED_PR
    assert m["registry_seed_dev_execution_status"] == "pass"


def test_review_manifest_db_environment():
    m = _json(REVIEW_MANIFEST_PATH)
    assert m["production_db_guard"] == "pass"
    assert m["production_db_write_performed"] is False
    assert m["db_write_scope"] == "registry_tables_only"


def test_review_manifest_counts():
    c = _json(REVIEW_MANIFEST_PATH)["final_counts"]
    assert c["football_teams"] == 18
    assert c["football_competitions"] == 10
    assert c["football_competition_editions"] == 10
    assert c["football_team_competition_participation"] == 11
    assert c["football_match_targets"] == 14
    assert c["football_match_target_teams"] == 28
    assert c["football_source_identities"] == 10
    assert c["total"] == 101


def test_review_manifest_idempotency():
    idem = _json(REVIEW_MANIFEST_PATH)["idempotency"]
    assert idem["first_run_inserted_total"] == 101
    assert idem["second_run_inserted_total"] == 0
    assert idem["pass"] is True


def test_review_manifest_target_selection():
    ts = _json(REVIEW_MANIFEST_PATH)["target_selection"]
    assert ts["selected_target_count"] == 10
    assert ts["skipped_target_count"] == 4
    assert ts["request_budget_respected"] is True
    assert ts["per_team_budget_respected"] is True
    assert ts["per_competition_budget_respected"] is True


def test_review_manifest_team_calendar():
    tc = _json(REVIEW_MANIFEST_PATH)["team_full_calendar"]
    assert tc["manchester_united_target_count"] == 6
    assert tc["england_target_count"] == 4
    assert tc["kashima_antlers_target_count"] == 2
    assert tc["leeds_united_target_count"] == 2


def test_review_manifest_safety():
    s = _json(REVIEW_MANIFEST_PATH)["safety"]
    assert s["network_fetch_performed"] is False
    assert s["raw_json_write_performed"] is False
    assert s["fotmob_raw_match_payloads_write_performed"] is False
    assert s["raw_match_data_write_performed"] is False
    assert s["feature_parse_performed"] is False
    assert s["scheduler_enabled"] is False
    assert s["raw_write_ready_marked"] is False


def test_review_manifest_gaps():
    gaps = _json(REVIEW_MANIFEST_PATH)["remaining_gaps"]
    assert any("live_fetch" in g for g in gaps)
    assert any("scheduler" in g for g in gaps)
    assert any("production" in g for g in gaps)


def test_review_manifest_next_phase():
    phase = _json(REVIEW_MANIFEST_PATH)["recommended_next_phase"]
    assert "TARGET-SELECTION-DB-DRY-RUN" in phase


# Review report
def test_review_report_status():
    report = _text(REVIEW_REPORT_PATH)
    assert "registry_seed_dev_execution_status" in report
    assert "pass" in report


def test_review_report_has_pr():
    assert "1429" in _text(REVIEW_REPORT_PATH)


# Review helper
def test_review_helper_passes():
    result = _load_helper().run_checks()
    assert result["verdict"] == "pass"
    assert result["reviewed_pr"] == REVIEWED_PR


def test_review_helper_no_network():
    code = _text(REVIEW_HELPER_PATH)
    for p in ["requests.get(url", "httpx.post(", "fetch(url", "playwright.chromium.launch"]:
        assert p not in code, f"Helper must not contain '{p}'"


# Manifest no raw JSON
def test_review_manifest_no_raw_json():
    text = _text(REVIEW_MANIFEST_PATH)
    assert "__NEXT_DATA__" not in text
