"""Tests for the football calendar target registry review artifacts.

lifecycle: permanent
"""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import re

REPO_ROOT = Path(__file__).resolve().parents[2]
REPORT_PATH = REPO_ROOT / "docs/_reports/FOTMOB_FOOTBALL_CALENDAR_TARGET_REGISTRY_REVIEW.md"
MANIFEST_PATH = (
    REPO_ROOT / "docs/_manifests/fotmob_football_calendar_target_registry_review_manifest.json"
)
MIGRATION_PATH = (
    REPO_ROOT / "database/migrations/V26.6__create_football_calendar_target_registry.sql"
)
HELPER_PATH = REPO_ROOT / "scripts/ops/fotmob_football_calendar_target_registry_review_check.py"

TABLES = [
    "football_teams",
    "football_competitions",
    "football_competition_editions",
    "football_team_competition_participation",
    "football_match_targets",
    "football_match_target_teams",
    "football_source_identities",
]
REQUIRED_COMPETITION_TYPES = [
    "domestic_cup",
    "continental_club",
    "international_tournament",
    "international_qualifier",
    "nations_league",
    "friendly",
    "super_cup",
    "other",
]
REQUIRED_TARGET_STATES = ["raw_json_stored", "blocked", "failed"]
REVIEWED_PR = 1423


def _text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _manifest() -> dict:
    return json.loads(_text(MANIFEST_PATH))


def _load_helper():
    spec = importlib.util.spec_from_file_location("registry_review_check", HELPER_PATH)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_review_artifacts_exist():
    assert REPORT_PATH.exists()
    assert MANIFEST_PATH.exists()
    assert HELPER_PATH.exists()


def test_review_metadata():
    manifest = _manifest()
    assert manifest["reviewed_pr"] == REVIEWED_PR
    assert manifest["registry_foundation_status"] == "foundation_solid"
    assert manifest["recommended_next_phase"] == "FOTMOB-RAW-JSON-LONG-RUN-COLLECTOR-DRY-RUN"


def test_all_seven_tables_reviewed():
    manifest = _manifest()
    assert manifest["tables_reviewed"] == TABLES


def test_support_flags_are_true():
    flags = _manifest()["support_flags"]
    assert all(flags.values())


def test_safety_flags_are_false():
    flags = _manifest()["safety"]
    assert all(value is False for value in flags.values())


def test_migration_has_no_destructive_sql():
    migration = _text(MIGRATION_PATH)
    forbidden = [
        "".join(chars)
        for chars in [
            ("D", "R", "O", "P"),
            ("T", "R", "U", "N", "C", "A", "T", "E"),
            ("D", "E", "L", "E", "T", "E"),
            ("U", "P", "D", "A", "T", "E"),
            ("A", "L", "T", "E", "R"),
        ]
    ]
    assert not re.search(r"\b(" + "|".join(forbidden) + r")\b", migration, flags=re.IGNORECASE)


def test_team_and_competition_types_cover_calendar_scope():
    manifest = _manifest()
    assert manifest["enums_reviewed"]["team_type"] == ["club", "national"]
    for value in REQUIRED_COMPETITION_TYPES:
        assert value in manifest["enums_reviewed"]["competition_type"]
    assert manifest["support_flags"]["supports_secondary_leagues"] is True


def test_target_state_supports_raw_lifecycle_exceptions():
    states = _manifest()["enums_reviewed"]["target_state"]
    for value in REQUIRED_TARGET_STATES:
        assert value in states


def test_report_next_phase_and_current_stage_boundaries():
    report = _text(REPORT_PATH)
    assert "dry-run 不应 live fetch" in report
    assert "parser/feature 是未来阶段" in report
    assert "不得访问 FotMob" in report
    assert "不得写 raw JSON" in report
    assert "不得写 raw_match_data" in report


def test_read_only_helper_passes():
    result = _load_helper().run_checks()
    assert result["verdict"] == "pass"
    assert result["network_fetch_performed"] is False
    assert result["db_data_write_performed"] is False
    assert result["migration_performed"] is False
    assert result["raw_json_write_performed"] is False
    assert result["feature_parse_performed"] is False
    assert result["scheduler_enabled"] is False
    assert result["raw_write_ready_marked"] is False
