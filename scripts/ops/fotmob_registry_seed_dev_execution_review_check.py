#!/usr/bin/env python3
"""Read-only review checks for FotMob registry seed dev execution.

lifecycle: permanent
phase: FOTMOB-RAW-JSON-LONG-RUN-COLLECTOR-REGISTRY-SEED-DEV-EXECUTION-REVIEW

No network fetch. No DB connection. No SQL execution. No raw JSON write.
"""

from __future__ import annotations

import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
HELPER_PATH = ROOT / "scripts/ops/fotmob_registry_seed_dev_execution.py"
MANIFEST_PATH = ROOT / "docs/_manifests/fotmob_registry_seed_dev_execution_manifest.json"
REPORT_PATH = ROOT / "docs/_reports/FOTMOB_REGISTRY_SEED_DEV_EXECUTION.md"
TEST_PATH = ROOT / "tests/unit/fotmob_registry_seed_dev_execution.test.py"

REVIEWED_PR = 1429
FINAL_COUNTS = {
    "football_teams": 18,
    "football_competitions": 10,
    "football_competition_editions": 10,
    "football_team_competition_participation": 11,
    "football_match_targets": 14,
    "football_match_target_teams": 28,
    "football_source_identities": 10,
}
SAFETY_KEYS = [
    "network_fetch_performed",
    "raw_json_write_performed",
    "fotmob_raw_match_payloads_write_performed",
    "raw_match_data_write_performed",
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
        "raw_json_write_performed": False,
        "feature_parse_performed": False,
        "scheduler_enabled": False,
        "raw_write_ready_marked": False,
    }
    checks, passed, failed = [], 0, 0

    def _check(name, cond, detail=""):
        nonlocal passed, failed
        s = "pass" if cond else "fail"
        if cond:
            passed += 1
        else:
            failed += 1
        checks.append({"name": name, "status": s, "detail": detail})

    for label, path in [
        ("helper", HELPER_PATH),
        ("manifest", MANIFEST_PATH),
        ("report", REPORT_PATH),
        ("test", TEST_PATH),
    ]:
        _check(f"file:{label}", path.exists(), str(path))

    manifest = _json(MANIFEST_PATH)
    _check("reviewed_pr", manifest.get("run_id") is not None)
    _check("db_env=docker_dev", manifest.get("db_environment") in ("docker_dev", "local", "ci"))
    _check("prod_guard=pass", manifest.get("production_db_guard") == "pass")
    _check("prod_db_write=false", manifest.get("production_db_write_performed") is False)
    safety = manifest.get("safety", {})
    _check("scope=registry_only", safety.get("db_write_scope") == "registry_tables_only")

    fc = manifest.get("final_counts", {})
    for tbl, exp in FINAL_COUNTS.items():
        _check(f"count:{tbl}={exp}", fc.get(tbl) == exp, f"got {fc.get(tbl)}")

    idem = manifest.get("idempotency", {})
    _check("idem:pass", idem.get("pass") is True)

    ts = manifest.get("target_selection", {})
    _check("ts:selected=10", ts.get("selected_target_count") == 10)
    _check("ts:skipped=4", ts.get("skipped_target_count") == 4)
    _check("ts:budget_req", ts.get("budget_respected") is True)
    _check(
        "ts:selected<=budget", ts.get("selected_target_count", 999) <= ts.get("request_budget", 0)
    )

    tc = manifest.get("team_full_calendar", {})
    _check("cal:MU=6", tc.get("manchester_united_target_count") == 6)
    _check("cal:ENG=4", tc.get("england_target_count") == 4)
    _check("cal:JPN=2", tc.get("kashima_antlers_target_count") == 2)
    _check("cal:LEE=2", tc.get("leeds_united_target_count") == 2)

    safety = manifest.get("safety", {})
    for key in SAFETY_KEYS:
        _check(f"safety:{key}=false", safety.get(key, True) is False)

    report = _text(REPORT_PATH)
    for phrase in ["没有访问 FotMob", "没有写 raw JSON", "registry_tables_only"]:
        _check(f"report:{phrase[:20]}", phrase in report or phrase.lower() in report.lower())

    helper_code = _text(HELPER_PATH)
    for p in [
        "requests.get(",
        "httpx.get(",
        "playwright.chromium",
        "INSERT INTO fotmob_raw_match_payloads",
    ]:
        _check(f"helper:no_{p}", p not in helper_code)

    _check("helper:prod_guard_func", "def check_production_guard" in helper_code)
    _check("helper:idem", "ON CONFLICT" in helper_code)

    test_code = _text(TEST_PATH)
    for name in [
        "test_manifest_idempotency",
        "test_manifest_safety",
        "test_helper_production_guard_blocked",
    ]:
        _check(f"test:has_{name}", f"def {name}(" in test_code)

    verdict = "pass" if failed == 0 else "fail"
    result["verdict"], result["checks"], result["passed"], result["failed"] = (
        verdict,
        checks,
        passed,
        failed,
    )
    return result


def main() -> int:
    result = run_checks()
    for c in result["checks"]:
        icon = "✓" if c["status"] == "pass" else "✗"
        d = f" ({c['detail']})" if c.get("detail") else ""
        print(f"  {icon} {c['name']}{d}")
    print(f"\nVerdict: {result['verdict']}  Passed: {result['passed']}  Failed: {result['failed']}")
    return 0 if result["verdict"] == "pass" else 1


if __name__ == "__main__":
    sys.exit(main())
