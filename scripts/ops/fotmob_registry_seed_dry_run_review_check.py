#!/usr/bin/env python3
"""Read-only review checks for FotMob registry seed dry-run.

lifecycle: permanent
phase: FOTMOB-RAW-JSON-LONG-RUN-COLLECTOR-REGISTRY-SEED-DRY-RUN-REVIEW

No network fetch. No DB connection. No SQL execution. No raw JSON write.
"""

from __future__ import annotations

import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]

PLAN_PATH = ROOT / "docs/_fixtures/fotmob_registry_seed_dry_run_plan.json"
HELPER_PATH = ROOT / "scripts/ops/fotmob_registry_seed_dry_run.py"
SQL_PATH = ROOT / "docs/_reports/FOTMOB_REGISTRY_SEED_DRY_RUN_SQL_PREVIEW.sql"
MANIFEST_PATH = ROOT / "docs/_manifests/fotmob_registry_seed_dry_run_manifest.json"
REPORT_PATH = ROOT / "docs/_reports/FOTMOB_REGISTRY_SEED_DRY_RUN.md"
TEST_PATH = ROOT / "tests/unit/fotmob_registry_seed_dry_run.test.py"
DESIGN_PATH = ROOT / "docs/data/FOTMOB_REGISTRY_SEED_DRY_RUN_DESIGN.md"

REVIEWED_PR = 1427
EXPECTED_COUNTS = {
    "teams_count": 18,
    "competitions_count": 10,
    "editions_count": 10,
    "participation_count": 11,
    "match_targets_count": 14,
    "match_target_teams_count": 28,
    "source_identities_count": 10,
}

COVERAGE_CHECKS = [
    "manchester_united_calendar_present",
    "england_national_team_calendar_present",
    "japanese_club_calendar_present",
    "secondary_league_calendar_present",
    "domestic_cup_present",
    "continental_club_present",
    "international_qualifier_present",
    "nations_league_present",
    "friendly_present",
]

SAFETY_KEYS = [
    "network_fetch_performed",
    "db_write_performed",
    "sql_executed",
    "raw_json_write_performed",
    "feature_parse_performed",
    "scheduler_enabled",
    "raw_write_ready_marked",
]


def _text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _json(path: Path) -> dict:
    return json.loads(_text(path))


def run_checks() -> dict:
    result: dict[str, object] = {
        "reviewed_pr": REVIEWED_PR,
        "network_fetch_performed": False,
        "db_data_write_performed": False,
        "sql_executed": False,
        "raw_json_write_performed": False,
        "feature_parse_performed": False,
        "scheduler_enabled": False,
        "raw_write_ready_marked": False,
    }
    checks: list[dict] = []
    passed = 0
    failed = 0

    def _check(name: str, condition: bool, detail: str = "") -> None:
        nonlocal passed, failed
        status = "pass" if condition else "fail"
        if condition:
            passed += 1
        else:
            failed += 1
        checks.append({"name": name, "status": status, "detail": detail})

    # Files exist
    for label, path in [
        ("plan", PLAN_PATH),
        ("helper", HELPER_PATH),
        ("sql", SQL_PATH),
        ("manifest", MANIFEST_PATH),
        ("report", REPORT_PATH),
        ("test", TEST_PATH),
        ("design", DESIGN_PATH),
    ]:
        _check(f"file:{label}", path.exists(), str(path))

    # Manifest counts
    manifest = _json(MANIFEST_PATH)
    for key, expected in EXPECTED_COUNTS.items():
        actual = manifest.get(key)
        _check(f"count:{key}={expected}", actual == expected, f"got {actual}")

    # Manifest coverage
    coverage = manifest.get("coverage", {})
    for flag in COVERAGE_CHECKS:
        _check(f"coverage:{flag}", coverage.get(flag, False) is True)

    # Target selection
    ts = manifest.get("target_selection", {})
    _check("target_selection:selected>0", ts.get("selected_target_count", 0) > 0)
    _check("target_selection:skipped>0", ts.get("skipped_target_count", 0) > 0)
    _check("target_selection:budget_respected", ts.get("budget_respected", False) is True)
    _check(
        "target_selection:selected<=budget",
        ts.get("selected_target_count", 999) <= ts.get("request_budget", 0),
    )

    # Team full-calendar
    tc = manifest.get("team_full_calendar", {})
    _check("calendar:MU>=4", tc.get("manchester_united_target_count", 0) >= 4)
    _check("calendar:ENG>=3", tc.get("england_target_count", 0) >= 3)
    _check("calendar:JPN>=2", tc.get("japanese_club_target_count", 0) >= 2)
    _check("calendar:LEE>=2", tc.get("secondary_league_target_count", 0) >= 2)

    # Safety flags
    safety = manifest.get("safety", {})
    for key in SAFETY_KEYS:
        _check(f"safety:{key}=false", safety.get(key, True) is False, f"got {safety.get(key)}")

    # SQL preview safety
    if SQL_PATH.exists():
        sql = _text(SQL_PATH)
        _check("sql:DRY-RUN header", "DRY-RUN SQL PREVIEW ONLY" in sql)
        _check("sql:DO NOT EXECUTE", "DO NOT EXECUTE" in sql)
        insert_lines = [l for l in sql.split("\n") if "INSERT INTO" in l]
        all_commented = all(l.strip().startswith("--") for l in insert_lines)
        _check("sql:all INSERTs commented", all_commented)
    else:
        _check("sql:file missing", False)

    # Report content
    report = _text(REPORT_PATH)
    _check("report:no live fetch", "没有访问 FotMob" in report)
    _check("report:no DB write", "没有写 DB" in report)
    _check("report:no SQL exec", "没有执行 SQL" in report)
    _check("report:MU present", "Manchester United" in report)
    _check("report:ENG present", "England" in report)
    _check("report:KAS present", "Kashima Antlers" in report)
    _check("report:LEE present", "Leeds United" in report)
    _check("report:next phase", "REGISTRY-SEED" in report)

    # Helper static safety
    helper_code = _text(HELPER_PATH)
    for p in ["requests.get(", "httpx.get(", "playwright.chromium", "psycopg2", "engine.execute"]:
        _check(f"helper:no_{p}", p not in helper_code)

    # Manifest no raw JSON
    manifest_text = _text(MANIFEST_PATH)
    _check("manifest:no __NEXT_DATA__", "__NEXT_DATA__" not in manifest_text)

    # Test file
    test_code = _text(TEST_PATH)
    for name in [
        "test_sql_preview_has_dry_run_header",
        "test_sql_preview_all_inserts_are_commented",
        "test_manifest_safety",
        "test_manifest_coverage",
        "test_helper_validate_plan",
    ]:
        _check(f"test:has_{name}", f"def {name}(" in test_code)

    verdict = "pass" if failed == 0 else "fail"
    result["verdict"] = verdict
    result["checks"] = checks
    result["passed"] = passed
    result["failed"] = failed
    return result


def main() -> int:
    result = run_checks()
    checks = result["checks"]
    assert isinstance(checks, list)
    for c in checks:
        icon = "✓" if c["status"] == "pass" else "✗"
        d = f" ({c['detail']})" if c.get("detail") else ""
        print(f"  {icon} {c['name']}{d}")
    print(f"\nVerdict: {result['verdict']}  Passed: {result['passed']}  Failed: {result['failed']}")
    return 0 if result["verdict"] == "pass" else 1


if __name__ == "__main__":
    sys.exit(main())
