"""Tests for FotMob registry seed dev execution artifacts.

lifecycle: permanent
phase: FOTMOB-RAW-JSON-LONG-RUN-COLLECTOR-REGISTRY-SEED-DEV-EXECUTION-NO-LIVE-FETCH
"""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
HELPER_PATH = REPO_ROOT / "scripts/ops/fotmob_registry_seed_dev_execution.py"
MANIFEST_PATH = REPO_ROOT / "docs/_manifests/fotmob_registry_seed_dev_execution_manifest.json"
REPORT_PATH = REPO_ROOT / "docs/_reports/FOTMOB_REGISTRY_SEED_DEV_EXECUTION.md"
PLAN_PATH = REPO_ROOT / "docs/_fixtures/fotmob_registry_seed_dry_run_plan.json"


def _text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _json(path: Path) -> dict:
    return json.loads(_text(path))


def _load_helper():
    spec = importlib.util.spec_from_file_location("fotmob_registry_seed_dev_execution", HELPER_PATH)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


# File existence
def test_helper_exists():
    assert HELPER_PATH.exists()


def test_manifest_exists():
    assert MANIFEST_PATH.exists()


def test_report_exists():
    assert REPORT_PATH.exists()


def test_plan_exists():
    assert PLAN_PATH.exists()


# Manifest content
def test_manifest_counts():
    m = _json(MANIFEST_PATH)
    fc = m["final_counts"]
    assert fc["football_teams"] == 18
    assert fc["football_competitions"] == 10
    assert fc["football_competition_editions"] == 10
    assert fc["football_team_competition_participation"] == 11
    assert fc["football_match_targets"] == 14
    assert fc["football_match_target_teams"] == 28
    assert fc["football_source_identities"] == 10


def test_manifest_idempotency():
    idem = _json(MANIFEST_PATH)["idempotency"]
    assert idem["first_run_total"] == 101
    assert idem["second_run_total"] == 0
    assert idem["pass"] is True


def test_manifest_target_selection():
    ts = _json(MANIFEST_PATH)["target_selection"]
    assert ts["input_target_count"] == 14
    assert ts["selected_target_count"] == 10
    assert ts["skipped_target_count"] == 4
    assert ts["budget_respected"] is True


def test_manifest_team_calendar():
    tc = _json(MANIFEST_PATH)["team_full_calendar"]
    assert tc["manchester_united_target_count"] == 6
    assert tc["england_target_count"] == 4
    assert tc["kashima_antlers_target_count"] == 2
    assert tc["leeds_united_target_count"] == 2


def test_manifest_safety():
    s = _json(MANIFEST_PATH)["safety"]
    assert s["network_fetch_performed"] is False
    assert s["db_write_performed"] is True
    assert s["db_write_scope"] == "registry_tables_only"
    assert s["raw_json_write_performed"] is False
    assert s["fotmob_raw_match_payloads_write_performed"] is False
    assert s["raw_match_data_write_performed"] is False
    assert s["feature_parse_performed"] is False
    assert s["scheduler_enabled"] is False
    assert s["raw_write_ready_marked"] is False


def test_manifest_environment():
    m = _json(MANIFEST_PATH)
    assert m["db_environment"] in ("docker_dev", "local", "ci")
    assert m["production_db_guard"] == "pass"
    assert m["production_db_write_performed"] is False


# Report content
def test_report_safety_declarations():
    report = _text(REPORT_PATH)
    assert "没有访问 FotMob" in report
    assert "没有写 raw JSON" in report
    assert "registry_tables_only" in report.lower()
    assert "dev" in report.lower() or "Dev" in report


def test_report_has_team_calendar():
    report = _text(REPORT_PATH)
    assert "Manchester United" in report or "Man United" in report
    assert "England" in report
    assert "Kashima Antlers" in report
    assert "Leeds United" in report


def test_report_has_recommended_next_phase():
    report = _text(REPORT_PATH)
    assert "REGISTRY-SEED-DEV-EXECUTION-REVIEW" in report


# Helper — production guard
def test_helper_production_guard_blocked():
    module = _load_helper()
    blocked, reasons = module.check_production_guard("prod-db.rds.amazonaws.com")
    assert blocked is True
    assert len(reasons) > 0


def test_helper_production_guard_dev_pass():
    module = _load_helper()
    blocked, _reasons = module.check_production_guard("localhost")
    assert blocked is False


# Static safety
def test_helper_no_network_code():
    code = _text(HELPER_PATH)
    for p in ["requests.get(", "httpx.get(", "fetch(url", "playwright.chromium"]:
        assert p not in code, f"Helper must not contain '{p}'"


def test_manifest_no_raw_json():
    text = _text(MANIFEST_PATH)
    assert "__NEXT_DATA__" not in text
    assert "pageProps" not in text.lower()
