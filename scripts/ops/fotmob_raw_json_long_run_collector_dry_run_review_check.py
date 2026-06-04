#!/usr/bin/env python3
"""Read-only review checks for the FotMob raw JSON long-run collector dry-run.

lifecycle: permanent
phase: FOTMOB-RAW-JSON-LONG-RUN-COLLECTOR-DRY-RUN-REVIEW

This helper reads local files only. It does not access the network, connect to
a database, execute the dry-run collector live path, write raw JSON, or parse
feature fields.
"""

from __future__ import annotations

import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]

FIXTURE_PATH = ROOT / "docs/_fixtures/fotmob_long_run_collector_dry_run_targets.json"
HELPER_PATH = ROOT / "scripts/ops/fotmob_raw_json_long_run_collector_dry_run.py"
MANIFEST_PATH = ROOT / "docs/_manifests/fotmob_raw_json_long_run_collector_dry_run_manifest.json"
REPORT_PATH = ROOT / "docs/_reports/FOTMOB_RAW_JSON_LONG_RUN_COLLECTOR_DRY_RUN.md"
DESIGN_PATH = ROOT / "docs/data/FOTMOB_RAW_JSON_LONG_RUN_COLLECTOR_DRY_RUN_DESIGN.md"
TEST_PATH = ROOT / "tests/unit/fotmob_raw_json_long_run_collector_dry_run.test.py"
REVIEW_REPORT_PATH = ROOT / "docs/_reports/FOTMOB_RAW_JSON_LONG_RUN_COLLECTOR_DRY_RUN_REVIEW.md"
REVIEW_MANIFEST_PATH = (
    ROOT / "docs/_manifests/fotmob_raw_json_long_run_collector_dry_run_review_manifest.json"
)

REQUIRED_FILES = [
    ("fixture", FIXTURE_PATH),
    ("dry-run helper", HELPER_PATH),
    ("dry-run manifest", MANIFEST_PATH),
    ("dry-run report", REPORT_PATH),
    ("design doc", DESIGN_PATH),
    ("test file", TEST_PATH),
]

COVERAGE_FLAGS = [
    "club_calendar_case_present",
    "national_team_case_present",
    "domestic_cup_case_present",
    "continental_club_case_present",
    "international_qualifier_case_present",
    "japanese_club_case_present",
    "secondary_league_case_present",
    "man_united_cross_competition_present",
    "england_national_team_present",
]

STOP_POLICY_KEYS = [
    "stop_on_403",
    "stop_on_429",
    "stop_on_captcha",
    "stop_on_unexpected_html",
    "stop_on_schema_shift",
    "no_retry_storm",
    "no_proxy_rotation",
    "no_anti_bot_bypass",
    "no_browser_automation",
]

SAFETY_KEYS = [
    "network_fetch_performed",
    "db_write_performed",
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
    """Run all review checks and return a structured result dict."""
    result: dict[str, object] = {
        "reviewed_pr": 1425,
        "network_fetch_performed": False,
        "db_data_write_performed": False,
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

    # 1. Required files exist
    for label, path in REQUIRED_FILES:
        _check(f"file_exists:{label}", path.exists(), str(path))

    # 2. Manifest review
    manifest = _json(MANIFEST_PATH)

    _check("reviewed_pr=1425", result["reviewed_pr"] == 1425)

    _check(
        "input_target_count=14",
        manifest["input_target_count"] == 14,
        f"got {manifest['input_target_count']}",
    )
    _check(
        "selected_target_count=10",
        manifest["selected_target_count"] == 10,
        f"got {manifest['selected_target_count']}",
    )
    _check(
        "skipped_target_count=4",
        manifest["skipped_target_count"] == 4,
        f"got {manifest['skipped_target_count']}",
    )
    _check(
        "request_budget=10",
        manifest["request_budget"] == 10,
        f"got {manifest['request_budget']}",
    )
    _check(
        "per_team_budget=5",
        manifest["per_team_budget"] == 5,
        f"got {manifest['per_team_budget']}",
    )
    _check(
        "per_competition_budget=4",
        manifest["per_competition_budget"] == 4,
        f"got {manifest['per_competition_budget']}",
    )

    # 3. Budget respected
    _check(
        "request_budget_respected",
        manifest["selected_target_count"] <= manifest["request_budget"],
    )
    _check(
        "counts_consistent",
        manifest["selected_target_count"] + manifest["skipped_target_count"]
        == manifest["input_target_count"],
    )

    # 4. Coverage flags (from original manifest)
    coverage = manifest["coverage"]
    for flag in COVERAGE_FLAGS:
        _check(f"coverage:{flag}", coverage.get(flag, False) is True)

    # 5. Stop policy
    stop_policy = manifest["stop_policy"]
    for key in STOP_POLICY_KEYS:
        _check(f"stop_policy:{key}", stop_policy.get(key, False) is True)

    # 6. Safety flags
    safety = manifest["safety"]
    for key in SAFETY_KEYS:
        _check(f"safety:{key}=false", safety.get(key, True) is False, f"got {safety.get(key)}")

    # 7. Skip reasons
    skip_reasons = [t.get("skip_reason", "") for t in manifest["skipped_targets"]]
    _check("has_blocked_skip", any("blocked" in r for r in skip_reasons))
    _check("has_stored_skip", any("stored" in r for r in skip_reasons))
    _check("has_budget_exhausted_skip", any("request_budget exhausted" in r for r in skip_reasons))

    # 8. Manifest has no raw JSON
    manifest_text = _text(MANIFEST_PATH)
    _check("manifest_no___NEXT_DATA__", "__NEXT_DATA__" not in manifest_text)
    _check("manifest_no_pageProps", "pageProps" not in manifest_text.lower())

    # 9. Report content
    report = _text(REPORT_PATH)
    _check("report_dry_run_no_live_fetch", "没有 live fetch" in report)
    _check("report_dry_run_no_db_write", "没有 DB write" in report)
    _check("report_dry_run_no_raw_json_write", "没有 raw JSON write" in report)
    _check("report_dry_run_no_feature_parse", "没有 feature parse" in report)
    _check("report_dry_run_no_scheduler", "没有 scheduler" in report)
    _check("report_has_stop_policy", "Stop Policy" in report)
    _check("report_has_selected_targets", "选中目标明细" in report)
    _check("report_has_skipped_targets", "跳过目标明细" in report)
    _check("report_has_team_calendar_examples", "Manchester United" in report)
    _check("report_has_england_example", "England" in report)
    _check("report_has_recommended_next_phase", "FOTMOB-RAW-JSON-LONG-RUN-COLLECTOR" in report)

    # 10. Helper script static safety
    helper_code = _text(HELPER_PATH)
    forbidden_network = [
        "requests.get",
        "requests.post",
        "httpx.get",
        "httpx.post",
        "aiohttp",
        "fetch(",
        "playwright",
        "chromium",
    ]
    for pattern in forbidden_network:
        _check(f"helper_no_{pattern}", pattern not in helper_code)

    forbidden_db = ["INSERT ", "UPDATE ", "DELETE ", "TRUNCATE ", "DROP TABLE"]
    for pattern in forbidden_db:
        _check(f"helper_no_{pattern}", pattern not in helper_code)

    forbidden_raw = [
        "fotmob_raw_match_payloads",
        "next_data_json",
        "page_props_json",
    ]
    for pattern in forbidden_raw:
        _check(f"helper_no_{pattern}", pattern not in helper_code)

    _check(
        "helper_no_raw_write_ready_true",
        "raw_write_ready = True" not in helper_code and "raw_write_ready=True" not in helper_code,
    )

    # 11. Test file exists and has expected tests
    test_code = _text(TEST_PATH)
    expected_test_names = [
        "test_fixture_exists",
        "test_helper_exists",
        "test_manifest_counts",
        "test_selected_targets_exclude_stored",
        "test_selected_targets_exclude_blocked_by_default",
        "test_request_budget_applied",
        "test_per_team_budget_applied",
        "test_man_united_cross_competition_present",
        "test_national_team_present",
        "test_domestic_cup_present",
        "test_continental_club_present",
        "test_japanese_club_present",
        "test_secondary_league_present",
        "test_report_states_no_live_fetch",
        "test_report_states_no_db_write",
        "test_report_states_no_raw_json_write",
        "test_helper_no_network_fetch",
        "test_helper_no_db_write",
        "test_helper_no_raw_json_write",
        "test_helper_no_browser_automation",
        "test_manifest_safety_flags_are_false",
    ]
    for name in expected_test_names:
        _check(f"test_exists:{name}", f"def {name}(" in test_code)

    # 12. Design doc content
    design = _text(DESIGN_PATH)
    _check("design_no_network_fetch", "no network fetch" in design.lower())
    _check("design_no_db_write", "no db write" in design.lower())
    _check("design_no_raw_json_write", "no raw json write" in design.lower())
    _check("design_dry_run", "dry-run" in design.lower())

    # 13. Fixture integrity
    fixture = _json(FIXTURE_PATH)
    _check("fixture_schema_version", "schema_version" in fixture)
    _check("fixture_targets_exist", len(fixture.get("targets", [])) == 14)
    fixture_text = _text(FIXTURE_PATH)
    _check("fixture_no___NEXT_DATA__", "__NEXT_DATA__" not in fixture_text)

    # Compile verdict
    verdict = "pass" if failed == 0 else "fail"
    result["verdict"] = verdict
    result["checks"] = checks
    result["passed"] = passed
    result["failed"] = failed

    return result


def main() -> int:
    verbose = "--verbose" in sys.argv or "-v" in sys.argv or len(sys.argv) <= 1

    result = run_checks()
    checks = result["checks"]
    assert isinstance(checks, list)

    if verbose:
        for c in checks:
            status_icon = "✓" if c["status"] == "pass" else "✗"
            detail_str = f" ({c['detail']})" if c.get("detail") else ""
            print(f"  {status_icon} {c['name']}{detail_str}")

        print()
        print(f"Verdict: {result['verdict']}")
        print(f"Passed:  {result['passed']}")
        print(f"Failed:  {result['failed']}")
        print(f"Total:   {result['passed'] + result['failed']}")

    if result["verdict"] == "fail":
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
