#!/usr/bin/env python3
"""Read-only checks for the FotMob football calendar target registry design.

lifecycle: permanent

This helper reads local design, manifest, and migration files only. It does not
access the network, connect to a database, execute a migration, or parse match
business fields.
"""

from __future__ import annotations

import json
from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parents[2]
DESIGN_PATH = ROOT / "docs/data/FOTMOB_FOOTBALL_CALENDAR_TARGET_REGISTRY_DESIGN.md"
MANIFEST_PATH = (
    ROOT / "docs/_manifests/fotmob_football_calendar_target_registry_design_manifest.json"
)
MIGRATION_PATH = ROOT / "database/migrations/V26.6__create_football_calendar_target_registry.sql"

REQUIRED_TABLES = [
    "football_teams",
    "football_competitions",
    "football_competition_editions",
    "football_team_competition_participation",
    "football_match_targets",
    "football_match_target_teams",
    "football_source_identities",
]

TEAM_TYPES = ["club", "national"]

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

FORBIDDEN_MIGRATION_SQL = ["DROP", "TRUNCATE", "DELETE", "UPDATE", "ALTER"]


def _read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _read_json(path: Path) -> dict:
    return json.loads(_read_text(path))


def _check(name: str, passed: bool, details: object | None = None) -> dict:
    item = {"name": name, "pass": passed}
    if details is not None:
        item["details"] = details
    return item


def _has_create_table(migration_sql: str, table_name: str) -> bool:
    pattern = rf"\bCREATE\s+TABLE\s+IF\s+NOT\s+EXISTS\s+{re.escape(table_name)}\b"
    return re.search(pattern, migration_sql, flags=re.IGNORECASE) is not None


def _contains_all_values(text: str, values: list[str]) -> bool:
    return all(f"'{value}'" in text or f'"{value}"' in text for value in values)


def run_checks() -> dict:
    """Validate local registry design artifacts without side effects."""
    checks: list[dict] = []
    checks.append(_check("design_doc_exists", DESIGN_PATH.exists()))
    checks.append(_check("manifest_exists", MANIFEST_PATH.exists()))
    checks.append(_check("migration_exists", MIGRATION_PATH.exists()))

    if not DESIGN_PATH.exists() or not MANIFEST_PATH.exists() or not MIGRATION_PATH.exists():
        return {
            "verdict": "fail",
            "checks": checks,
            "network_fetch_performed": False,
            "db_data_write_performed": False,
        }

    design_doc = _read_text(DESIGN_PATH)
    manifest = _read_json(MANIFEST_PATH)
    migration_sql = _read_text(MIGRATION_PATH)

    for table_name in REQUIRED_TABLES:
        checks.append(
            _check(
                f"migration_declares_{table_name}",
                _has_create_table(migration_sql, table_name),
            )
        )
        checks.append(
            _check(
                f"design_declares_{table_name}",
                table_name in design_doc,
            )
        )

    forbidden_hits = sorted(
        {
            match.group(0).upper()
            for match in re.finditer(
                r"\b(" + "|".join(FORBIDDEN_MIGRATION_SQL) + r")\b",
                migration_sql,
                flags=re.IGNORECASE,
            )
        }
    )
    checks.append(
        _check(
            "migration_has_no_drop_truncate_delete_update_or_alter",
            not forbidden_hits,
            forbidden_hits,
        )
    )

    checks.append(
        _check(
            "competition_type_enum_complete", _contains_all_values(migration_sql, COMPETITION_TYPES)
        )
    )
    checks.append(
        _check("team_type_enum_complete", _contains_all_values(migration_sql, TEAM_TYPES))
    )
    checks.append(
        _check("target_state_enum_complete", _contains_all_values(migration_sql, TARGET_STATES))
    )

    checks.append(
        _check(
            "manifest_supports_team_full_calendar",
            manifest.get("supports_team_full_calendar") is True,
        )
    )
    checks.append(
        _check(
            "manifest_raw_write_ready_marked_false",
            manifest.get("safety", {}).get("raw_write_ready_marked") is False,
        )
    )

    safety = manifest.get("safety", {})
    checks.extend(
        [
            _check(f"safety_{key}_false", safety.get(key) is False)
            for key in [
                "network_fetch_performed",
                "db_data_write_performed",
                "raw_json_write_performed",
                "feature_parse_performed",
                "scheduler_enabled",
                "raw_write_ready_marked",
            ]
        ]
    )

    passed_count = sum(1 for item in checks if item["pass"])
    failed_count = len(checks) - passed_count
    return {
        "verdict": "pass" if failed_count == 0 else "fail",
        "checks": checks,
        "passed_count": passed_count,
        "failed_count": failed_count,
        "network_fetch_performed": False,
        "db_data_write_performed": False,
        "raw_json_write_performed": False,
        "feature_parse_performed": False,
        "scheduler_enabled": False,
        "raw_write_ready_marked": False,
    }


def main() -> int:
    """Run the local read-only checks and return a shell exit status."""
    result = run_checks()
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["verdict"] == "pass" else 1


if __name__ == "__main__":
    sys.exit(main())
