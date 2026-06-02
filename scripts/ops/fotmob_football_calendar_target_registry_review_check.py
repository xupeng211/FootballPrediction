#!/usr/bin/env python3
"""Read-only review checks for the football calendar target registry foundation.

lifecycle: permanent

This helper reads local files only. It does not access the network, connect to
a database, execute migrations, write raw JSON, or parse feature fields.
"""

from __future__ import annotations

import json
from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parents[2]
MIGRATION_PATH = ROOT / "database/migrations/V26.6__create_football_calendar_target_registry.sql"
DESIGN_PATH = ROOT / "docs/data/FOTMOB_FOOTBALL_CALENDAR_TARGET_REGISTRY_DESIGN.md"
DESIGN_MANIFEST_PATH = (
    ROOT / "docs/_manifests/fotmob_football_calendar_target_registry_design_manifest.json"
)
REPORT_PATH = ROOT / "docs/_reports/FOTMOB_FOOTBALL_CALENDAR_TARGET_REGISTRY_REVIEW.md"
REVIEW_MANIFEST_PATH = (
    ROOT / "docs/_manifests/fotmob_football_calendar_target_registry_review_manifest.json"
)

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
    "other",
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
SUPPORT_FLAGS = [
    "supports_club_teams",
    "supports_national_teams",
    "supports_domestic_cups",
    "supports_continental_club_competitions",
    "supports_international_tournaments",
    "supports_international_qualifiers",
    "supports_secondary_leagues",
    "supports_team_full_calendar_reconstruction",
    "supports_raw_json_db_linkage",
]
SAFETY_FLAGS = [
    "network_fetch_performed",
    "db_data_write_performed",
    "migration_performed",
    "raw_json_write_performed",
    "feature_parse_performed",
    "scheduler_enabled",
    "raw_write_ready_marked",
]
NEXT_PHASE = "FOTMOB-RAW-JSON-LONG-RUN-COLLECTOR-DRY-RUN"
REVIEWED_PR = 1423
FORBIDDEN_SQL = [
    "".join(parts)
    for parts in [
        ("D", "R", "O", "P"),
        ("T", "R", "U", "N", "C", "A", "T", "E"),
        ("D", "E", "L", "E", "T", "E"),
        ("U", "P", "D", "A", "T", "E"),
        ("A", "L", "T", "E", "R"),
    ]
]


def _read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _read_json(path: Path) -> dict:
    return json.loads(_read_text(path))


def _check(name: str, passed: bool, details: object | None = None) -> dict:
    item = {"name": name, "pass": passed}
    if details is not None:
        item["details"] = details
    return item


def _has_create_table(text: str, table: str) -> bool:
    pattern = rf"\bCREATE\s+TABLE\s+IF\s+NOT\s+EXISTS\s+{re.escape(table)}\b"
    return re.search(pattern, text, flags=re.IGNORECASE) is not None


def _contains_all(text: str, values: list[str]) -> bool:
    return all(f"'{value}'" in text or f'"{value}"' in text for value in values)


def run_checks() -> dict:
    """Validate review artifacts without side effects."""
    required_paths = [
        MIGRATION_PATH,
        DESIGN_PATH,
        DESIGN_MANIFEST_PATH,
        REPORT_PATH,
        REVIEW_MANIFEST_PATH,
    ]
    checks = [_check(f"{path.name}_exists", path.exists()) for path in required_paths]

    if not all(path.exists() for path in required_paths):
        return {"verdict": "fail", "checks": checks, "network_fetch_performed": False}

    migration = _read_text(MIGRATION_PATH)
    report = _read_text(REPORT_PATH)
    manifest = _read_json(REVIEW_MANIFEST_PATH)

    checks.extend(
        [
            _check(f"table_{table}_present", _has_create_table(migration, table))
            for table in REQUIRED_TABLES
        ]
    )

    forbidden_hits = sorted(
        {
            match.group(0).upper()
            for match in re.finditer(
                r"\b(" + "|".join(FORBIDDEN_SQL) + r")\b",
                migration,
                flags=re.IGNORECASE,
            )
        }
    )
    checks.append(_check("migration_has_no_destructive_sql", not forbidden_hits, forbidden_hits))
    checks.append(_check("team_type_complete", _contains_all(migration, TEAM_TYPES)))
    checks.append(_check("competition_type_complete", _contains_all(migration, COMPETITION_TYPES)))
    checks.append(_check("target_state_complete", _contains_all(migration, TARGET_STATES)))

    support_flags = manifest.get("support_flags", {})
    checks.extend(
        [_check(f"{flag}_true", support_flags.get(flag) is True) for flag in SUPPORT_FLAGS]
    )

    safety = manifest.get("safety", {})
    checks.extend([_check(f"{flag}_false", safety.get(flag) is False) for flag in SAFETY_FLAGS])

    checks.append(_check("reviewed_pr_1423", manifest.get("reviewed_pr") == REVIEWED_PR))
    checks.append(
        _check("foundation_solid", manifest.get("registry_foundation_status") == "foundation_solid")
    )
    checks.append(
        _check("recommended_next_phase", manifest.get("recommended_next_phase") == NEXT_PHASE)
    )
    checks.append(
        _check(
            "report_business_fit_review",
            "Business Fit Review" in report and "业务适配审查" in report,
        )
    )
    checks.append(_check("report_parser_feature_future", "parser/feature 是未来阶段" in report))
    checks.append(_check("report_dry_run_no_live_fetch", "dry-run 不应 live fetch" in report))

    passed_count = sum(1 for item in checks if item["pass"])
    failed_count = len(checks) - passed_count
    return {
        "verdict": "pass" if failed_count == 0 else "fail",
        "checks": checks,
        "passed_count": passed_count,
        "failed_count": failed_count,
        "network_fetch_performed": False,
        "db_data_write_performed": False,
        "migration_performed": False,
        "raw_json_write_performed": False,
        "feature_parse_performed": False,
        "scheduler_enabled": False,
        "raw_write_ready_marked": False,
    }


def main() -> int:
    """Run review checks and return a shell exit status."""
    result = run_checks()
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["verdict"] == "pass" else 1


if __name__ == "__main__":
    sys.exit(main())
