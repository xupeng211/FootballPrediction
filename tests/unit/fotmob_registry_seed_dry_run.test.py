"""Tests for the FotMob registry seed dry-run artifacts.

lifecycle: permanent
phase: FOTMOB-RAW-JSON-LONG-RUN-COLLECTOR-REGISTRY-SEED-DRY-RUN
"""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
PLAN_PATH = REPO_ROOT / "docs/_fixtures/fotmob_registry_seed_dry_run_plan.json"
HELPER_PATH = REPO_ROOT / "scripts/ops/fotmob_registry_seed_dry_run.py"
MANIFEST_PATH = REPO_ROOT / "docs/_manifests/fotmob_registry_seed_dry_run_manifest.json"
REPORT_PATH = REPO_ROOT / "docs/_reports/FOTMOB_REGISTRY_SEED_DRY_RUN.md"
SQL_PREVIEW_PATH = REPO_ROOT / "docs/_reports/FOTMOB_REGISTRY_SEED_DRY_RUN_SQL_PREVIEW.sql"
DESIGN_PATH = REPO_ROOT / "docs/data/FOTMOB_REGISTRY_SEED_DRY_RUN_DESIGN.md"


def _text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _json(path: Path) -> dict:
    return json.loads(_text(path))


def _load_helper():
    spec = importlib.util.spec_from_file_location("fotmob_registry_seed_dry_run", HELPER_PATH)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


# ---------------------------------------------------------------------------
# File existence
# ---------------------------------------------------------------------------
def test_fixture_exists():
    assert PLAN_PATH.exists()


def test_helper_exists():
    assert HELPER_PATH.exists()


def test_design_exists():
    assert DESIGN_PATH.exists()


def test_manifest_exists():
    assert MANIFEST_PATH.exists()


def test_report_exists():
    assert REPORT_PATH.exists()


def test_sql_preview_exists():
    assert SQL_PREVIEW_PATH.exists()


# ---------------------------------------------------------------------------
# Plan fixture
# ---------------------------------------------------------------------------
def test_plan_has_all_sections():
    plan = _json(PLAN_PATH)
    for section in [
        "teams",
        "competitions",
        "competition_editions",
        "team_competition_participation",
        "match_targets",
        "match_target_teams",
        "source_identities",
    ]:
        assert section in plan, f"Missing section: {section}"


def test_teams_count():
    plan = _json(PLAN_PATH)
    assert len(plan["teams"]) >= 5


def test_team_types():
    types = {t["team_type"] for t in _json(PLAN_PATH)["teams"]}
    assert "club" in types
    assert "national" in types


def test_competitions_count():
    assert len(_json(PLAN_PATH)["competitions"]) >= 8


def test_competition_types():
    types = {c["competition_type"] for c in _json(PLAN_PATH)["competitions"]}
    for expected in [
        "league",
        "domestic_cup",
        "continental_club",
        "international_qualifier",
        "nations_league",
        "friendly",
    ]:
        assert expected in types, f"Missing competition_type: {expected}"


def test_editions_count():
    assert len(_json(PLAN_PATH)["competition_editions"]) >= 8


def test_participation_count():
    assert len(_json(PLAN_PATH)["team_competition_participation"]) >= 10


def test_match_targets_count():
    assert len(_json(PLAN_PATH)["match_targets"]) >= 12


def test_match_target_teams_count():
    assert len(_json(PLAN_PATH)["match_target_teams"]) >= 24


def test_blocked_target_present():
    states = {mt["target_state"] for mt in _json(PLAN_PATH)["match_targets"]}
    assert "blocked" in states


def test_stored_target_present():
    statuses = {mt["raw_json_status"] for mt in _json(PLAN_PATH)["match_targets"]}
    assert "stored" in statuses


def test_failed_target_present():
    statuses = {mt["raw_json_status"] for mt in _json(PLAN_PATH)["match_targets"]}
    assert "failed" in statuses


# ---------------------------------------------------------------------------
# Manifest
# ---------------------------------------------------------------------------
def test_manifest_counts():
    m = _json(MANIFEST_PATH)
    assert m["teams_count"] >= 5
    assert m["competitions_count"] >= 8
    assert m["editions_count"] >= 8
    assert m["participation_count"] >= 10
    assert m["match_targets_count"] >= 12
    assert m["match_target_teams_count"] >= 24


def test_manifest_coverage():
    c = _json(MANIFEST_PATH)["coverage"]
    assert c["manchester_united_calendar_present"] is True
    assert c["england_national_team_calendar_present"] is True
    assert c["japanese_club_calendar_present"] is True
    assert c["secondary_league_calendar_present"] is True
    assert c["domestic_cup_present"] is True
    assert c["continental_club_present"] is True
    assert c["international_qualifier_present"] is True
    assert c["nations_league_present"] is True
    assert c["friendly_present"] is True


def test_manifest_team_calendar():
    tc = _json(MANIFEST_PATH)["team_full_calendar"]
    assert tc["manchester_united_target_count"] >= 4
    assert tc["england_target_count"] >= 3
    assert tc["japanese_club_target_count"] >= 2
    assert tc["secondary_league_target_count"] >= 2


def test_manifest_target_selection():
    ts = _json(MANIFEST_PATH)["target_selection"]
    assert ts["selected_target_count"] > 0
    assert ts["skipped_target_count"] > 0
    assert ts["budget_respected"] is True
    assert ts["selected_target_count"] <= ts["request_budget"]


def test_manifest_safety():
    s = _json(MANIFEST_PATH)["safety"]
    assert s["network_fetch_performed"] is False
    assert s["db_write_performed"] is False
    assert s["sql_executed"] is False
    assert s["raw_json_write_performed"] is False
    assert s["feature_parse_performed"] is False
    assert s["scheduler_enabled"] is False
    assert s["raw_write_ready_marked"] is False


def test_manifest_recommended_next_phase():
    phase = _json(MANIFEST_PATH)["recommended_next_phase"]
    assert "REVIEW" in phase


# ---------------------------------------------------------------------------
# Report
# ---------------------------------------------------------------------------
def test_report_safety_declarations():
    report = _text(REPORT_PATH)
    assert "没有执行 SQL" in report
    assert "没有写 DB" in report
    assert "没有访问 FotMob" in report
    assert "没有写 raw JSON" in report


def test_report_has_team_calendar():
    report = _text(REPORT_PATH)
    assert "Manchester United" in report
    assert "England" in report
    assert "Kashima Antlers" in report
    assert "Leeds United" in report


def test_report_has_recommended_next_phase():
    report = _text(REPORT_PATH)
    assert "REGISTRY-SEED-DRY-RUN-REVIEW" in report


# ---------------------------------------------------------------------------
# SQL preview
# ---------------------------------------------------------------------------
def test_sql_preview_has_dry_run_header():
    sql = _text(SQL_PREVIEW_PATH)
    assert "DRY-RUN SQL PREVIEW ONLY" in sql
    assert "DO NOT EXECUTE" in sql


def test_sql_preview_all_inserts_are_commented():
    sql = _text(SQL_PREVIEW_PATH)
    lines = [line for line in sql.split("\n") if "INSERT INTO" in line]
    for line in lines:
        stripped = line.strip()
        assert stripped.startswith("--"), f"INSERT not commented: {stripped[:60]}"


def test_sql_preview_has_tables():
    sql = _text(SQL_PREVIEW_PATH)
    assert "football_teams" in sql
    assert "football_competitions" in sql
    assert "football_competition_editions" in sql
    assert "football_team_competition_participation" in sql
    assert "football_match_targets" in sql
    assert "football_match_target_teams" in sql
    assert "football_source_identities" in sql


# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------
def test_helper_loads():
    assert _load_helper() is not None


def test_helper_validate_plan():
    plan = _json(PLAN_PATH)
    errors = _load_helper().validate_plan(plan)
    assert len(errors) == 0, f"Unexpected validation errors: {errors}"


def test_helper_classify_skips_blocked():
    module = _load_helper()
    match_targets = _json(PLAN_PATH)["match_targets"]
    _selectable, skipped = module.classify_targets(match_targets)
    reasons = [s.get("skip_reason", "") for s in skipped]
    assert any("blocked" in r for r in reasons)


def test_helper_classify_skips_stored():
    module = _load_helper()
    match_targets = _json(PLAN_PATH)["match_targets"]
    _selectable, skipped = module.classify_targets(match_targets)
    reasons = [s.get("skip_reason", "") for s in skipped]
    assert any("stored" in r for r in reasons)


def test_helper_team_calendar():
    module = _load_helper()
    plan = _json(PLAN_PATH)
    cal = module.team_calendar(
        "team-mun-01",
        plan["match_targets"],
        plan["competitions"],
        plan["match_target_teams"],
    )
    assert len(cal) >= 4
    comps = {t["competition_type"] for t in cal}
    assert "league" in comps or "domestic_cup" in comps or "continental_club" in comps


# ---------------------------------------------------------------------------
# Static safety
# ---------------------------------------------------------------------------
def test_helper_no_network_fetch_code():
    code = _text(HELPER_PATH)
    forbidden = [
        "requests.get(",
        "requests.post(",
        "httpx.get(",
        "fetch(url",
        "playwright.chromium",
    ]
    for p in forbidden:
        assert p not in code, f"Helper must not contain '{p}'"


def test_helper_no_db_write_code():
    code = _text(HELPER_PATH)
    forbidden = ["engine.execute", "cursor.execute", "psycopg2", "asyncpg"]
    for p in forbidden:
        assert p not in code, f"Helper must not contain '{p}'"


def test_plan_has_no_raw_json():
    text = _text(PLAN_PATH)
    assert "__NEXT_DATA__" not in text


def test_manifest_has_no_raw_json():
    text = _text(MANIFEST_PATH)
    assert "__NEXT_DATA__" not in text
    assert "pageProps" not in text.lower()
