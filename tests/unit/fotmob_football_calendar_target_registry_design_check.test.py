"""Tests for the FotMob football calendar target registry design check.

lifecycle: permanent
"""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import re

REPO_ROOT = Path(__file__).resolve().parents[2]
DESIGN_PATH = REPO_ROOT / "docs/data/FOTMOB_FOOTBALL_CALENDAR_TARGET_REGISTRY_DESIGN.md"
MANIFEST_PATH = (
    REPO_ROOT / "docs/_manifests/fotmob_football_calendar_target_registry_design_manifest.json"
)
MIGRATION_PATH = (
    REPO_ROOT / "database/migrations/V26.6__create_football_calendar_target_registry.sql"
)
HELPER_PATH = REPO_ROOT / "scripts/ops/fotmob_football_calendar_target_registry_design_check.py"

TABLES = [
    "football_teams",
    "football_competitions",
    "football_competition_editions",
    "football_team_competition_participation",
    "football_match_targets",
    "football_match_target_teams",
    "football_source_identities",
]

COMPETITION_TYPES = [
    "league",
    "domestic_cup",
    "continental_club",
    "international_tournament",
    "international_qualifier",
    "nations_league",
    "friendly",
    "super_cup",
]

TARGET_STATES = [
    "discovered",
    "pending_raw_fetch",
    "raw_fetched",
    "raw_json_stored",
    "blocked",
    "failed",
    "retired",
]


def _text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _manifest() -> dict:
    return json.loads(_text(MANIFEST_PATH))


def _load_helper():
    spec = importlib.util.spec_from_file_location("registry_design_check", HELPER_PATH)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_design_doc_manifest_and_migration_exist():
    assert DESIGN_PATH.exists()
    assert MANIFEST_PATH.exists()
    assert MIGRATION_PATH.exists()
    assert HELPER_PATH.exists()


def test_all_seven_tables_are_declared():
    design_doc = _text(DESIGN_PATH)
    migration_sql = _text(MIGRATION_PATH)
    manifest = _manifest()

    assert manifest["tables"] == TABLES
    for table in TABLES:
        assert table in design_doc
        assert re.search(
            rf"\bCREATE\s+TABLE\s+IF\s+NOT\s+EXISTS\s+{re.escape(table)}\b",
            migration_sql,
            flags=re.IGNORECASE,
        )


def test_team_type_supports_club_and_national():
    migration_sql = _text(MIGRATION_PATH)
    manifest = _manifest()
    assert manifest["enums"]["team_type"] == ["club", "national"]
    assert "'club'" in migration_sql
    assert "'national'" in migration_sql


def test_competition_type_supports_required_calendar_scope():
    migration_sql = _text(MIGRATION_PATH)
    manifest = _manifest()
    for value in COMPETITION_TYPES:
        assert value in manifest["enums"]["competition_type"]
        assert f"'{value}'" in migration_sql


def test_target_state_supports_raw_collection_lifecycle():
    migration_sql = _text(MIGRATION_PATH)
    manifest = _manifest()
    for value in TARGET_STATES:
        assert value in manifest["enums"]["target_state"]
        assert f"'{value}'" in migration_sql


def test_migration_has_no_drop_truncate_delete_update_or_alter():
    migration_sql = _text(MIGRATION_PATH)
    forbidden = re.findall(
        r"\b(DROP|TRUNCATE|DELETE|UPDATE|ALTER)\b", migration_sql, flags=re.IGNORECASE
    )
    assert forbidden == []


def test_manifest_supports_full_calendar_and_required_scopes():
    manifest = _manifest()
    assert manifest["supports_team_full_calendar"] is True
    assert manifest["supports_national_team_matches"] is True
    assert manifest["supports_domestic_cup"] is True
    assert manifest["supports_continental_club"] is True
    assert manifest["supports_international_tournament"] is True
    assert manifest["supports_international_qualifier"] is True
    assert manifest["supports_secondary_leagues"] is True


def test_safety_flags_are_false():
    safety = _manifest()["safety"]
    assert safety["network_fetch_performed"] is False
    assert safety["db_data_write_performed"] is False
    assert safety["raw_json_write_performed"] is False
    assert safety["feature_parse_performed"] is False
    assert safety["scheduler_enabled"] is False
    assert safety["raw_write_ready_marked"] is False


def test_read_only_helper_passes_all_checks():
    helper = _load_helper()
    result = helper.run_checks()
    assert result["verdict"] == "pass"
    assert result["network_fetch_performed"] is False
    assert result["db_data_write_performed"] is False
    assert result["raw_json_write_performed"] is False
    assert result["feature_parse_performed"] is False
    assert result["scheduler_enabled"] is False
    assert result["raw_write_ready_marked"] is False
