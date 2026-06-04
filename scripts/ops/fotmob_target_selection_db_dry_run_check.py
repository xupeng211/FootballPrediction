#!/usr/bin/env python3
"""Artifact checker for FotMob target selection DB dry-run.

lifecycle: permanent
phase: FOTMOB-RAW-JSON-LONG-RUN-COLLECTOR-TARGET-SELECTION-DB-DRY-RUN

Reads only the generated manifest and reports. No DB connection, no source
access, no raw payload storage, no SQL execution.

Permanent manual checker. It is not wired to Makefile, npm scripts, or CI;
cleanup only after the dry-run phase is replaced by a versioned gate.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_MANIFEST = ROOT / "docs/_manifests/fotmob_target_selection_db_dry_run_manifest.json"
DEFAULT_REPORT = ROOT / "docs/_reports/FOTMOB_TARGET_SELECTION_DB_DRY_RUN.md"
DEFAULT_REVIEW_REPORT = ROOT / "docs/_reports/FOTMOB_TARGET_SELECTION_DB_DRY_RUN_REVIEW.md"

REQUIRED_SKIP_REASONS = {"blocked", "stored", "budget_exhausted"}
EXPECTED_TEAM_COUNTS = {
    "manchester_united_target_count": 6,
    "england_target_count": 4,
    "kashima_antlers_target_count": 2,
    "leeds_united_target_count": 2,
}
SAFETY_FALSE_KEYS = [
    "network_fetch_performed",
    "raw_json_write_performed",
    "fotmob_raw_match_payloads_write_performed",
    "raw_match_data_write_performed",
    "feature_parse_performed",
    "scheduler_enabled",
    "raw_write_ready_marked",
]


def _read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(_read_text(path))


def run_checks(
    manifest_path: Path = DEFAULT_MANIFEST,
    report_path: Path = DEFAULT_REPORT,
    review_report_path: Path = DEFAULT_REVIEW_REPORT,
) -> dict[str, Any]:
    checks: list[dict[str, str]] = []

    def check(name: str, condition: bool, detail: str = "") -> None:
        checks.append(
            {
                "name": name,
                "status": "pass" if condition else "fail",
                "detail": detail,
            }
        )

    for label, path in [
        ("manifest", manifest_path),
        ("report", report_path),
        ("review_report", review_report_path),
    ]:
        check(f"file_exists:{label}", path.exists(), str(path))

    if not manifest_path.exists():
        return {"verdict": "fail", "checks": checks, "passed": 0, "failed": 1}

    manifest = _read_json(manifest_path)
    report = _read_text(report_path) if report_path.exists() else ""
    review_report = _read_text(review_report_path) if review_report_path.exists() else ""

    check("input_target_count=14", manifest.get("input_target_count") == 14)
    check("selected_target_count=10", manifest.get("selected_target_count") == 10)
    check("skipped_target_count=4", manifest.get("skipped_target_count") == 4)

    skip_reason_counts = manifest.get("skip_reason_counts", {})
    check(
        "skip_reasons_required",
        REQUIRED_SKIP_REASONS.issubset(set(skip_reason_counts)),
        str(skip_reason_counts),
    )

    budgets = manifest.get("budgets", {})
    check("request_budget_respected", budgets.get("request_budget_respected") is True)
    check("per_team_budget_respected", budgets.get("per_team_budget_respected") is True)
    check(
        "per_competition_budget_respected",
        budgets.get("per_competition_budget_respected") is True,
    )

    team_full_calendar = manifest.get("team_full_calendar", {})
    for key, expected in EXPECTED_TEAM_COUNTS.items():
        check(f"{key}={expected}", team_full_calendar.get(key) == expected)

    source_identity = manifest.get("source_identity", {})
    check(
        "all_selected_have_source_identity",
        source_identity.get("all_selected_have_source_identity") is True,
    )
    check(
        "unsupported_source_selected=false",
        source_identity.get("unsupported_source_selected") is False,
    )

    selected_ids = [
        target.get("source_match_id") for target in manifest.get("selected_targets", [])
    ]
    check("no_duplicate_selected_target", len(selected_ids) == len(set(selected_ids)))

    check("db_read_performed=true", manifest.get("db_read_performed") is True)
    check("db_write_performed=false", manifest.get("db_write_performed") is False)
    check(
        "production_db_write_performed=false",
        manifest.get("production_db_write_performed") is False,
    )
    safety = manifest.get("safety", {})
    for key in SAFETY_FALSE_KEYS:
        check(f"{key}=false", safety.get(key) is False)

    embedded_review = manifest.get("embedded_review", {})
    check(
        "embedded_review_status=pass",
        embedded_review.get("target_selection_db_dry_run_status") == "pass",
    )

    for phrase in [
        "no live fetch",
        "no DB write",
        "no raw JSON write",
        "Target Selection DB Dry-run",
    ]:
        check(f"report_contains:{phrase}", phrase in report)

    for phrase in [
        "status: pass",
        "DB read-only check: pass",
        "no network check: pass",
        "no raw JSON write check: pass",
    ]:
        check(f"review_contains:{phrase}", phrase in review_report)

    passed = sum(1 for item in checks if item["status"] == "pass")
    failed = sum(1 for item in checks if item["status"] == "fail")
    return {
        "verdict": "pass" if failed == 0 else "fail",
        "checks": checks,
        "passed": passed,
        "failed": failed,
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Check FotMob target selection dry-run artifacts")
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    parser.add_argument("--report", type=Path, default=DEFAULT_REPORT)
    parser.add_argument("--review-report", type=Path, default=DEFAULT_REVIEW_REPORT)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    result = run_checks(args.manifest, args.report, args.review_report)
    for item in result["checks"]:
        marker = "pass" if item["status"] == "pass" else "fail"
        detail = f" ({item['detail']})" if item.get("detail") else ""
        print(f"[{marker}] {item['name']}{detail}")
    print(f"Verdict: {result['verdict']}  Passed: {result['passed']}  Failed: {result['failed']}")
    return 0 if result["verdict"] == "pass" else 1


if __name__ == "__main__":
    sys.exit(main())
