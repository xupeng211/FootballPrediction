#!/usr/bin/env python3
"""Artifact checker for one-day FotMob live fetch probe.

lifecycle: permanent
phase: FOTMOB-RAW-JSON-LONG-RUN-COLLECTOR-ONE-DAY-LIVE-FETCH-NO-RAW-WRITE

Reads generated artifacts only. No DB connection, no live request, no source
access, no raw payload persistence.
Permanent manual checker. Not wired to Makefile, npm scripts, or CI; cleanup
after a versioned probe gate supersedes it.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_MANIFEST = ROOT / "docs/_manifests/fotmob_one_day_live_fetch_no_raw_write_manifest.json"
DEFAULT_REPORT = ROOT / "docs/_reports/FOTMOB_ONE_DAY_LIVE_FETCH_NO_RAW_WRITE.md"
DEFAULT_REVIEW = ROOT / "docs/_reports/FOTMOB_ONE_DAY_LIVE_FETCH_NO_RAW_WRITE_REVIEW.md"
ALLOWED_REVIEW_STATUS = {"pass", "partial", "blocked"}
SAFETY_FALSE_KEYS = [
    "raw_response_body_saved",
    "raw_json_write_performed",
    "fotmob_raw_match_payloads_write_performed",
    "raw_match_data_write_performed",
    "feature_parse_performed",
    "scheduler_enabled",
    "raw_write_ready_marked",
    "browser_automation_performed",
    "captcha_bypass_performed",
    "proxy_rotation_performed",
    "retry_storm_performed",
]


def _text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _json(path: Path) -> dict[str, Any]:
    return json.loads(_text(path))


def run_checks(
    manifest_path: Path = DEFAULT_MANIFEST,
    report_path: Path = DEFAULT_REPORT,
    review_path: Path = DEFAULT_REVIEW,
) -> dict[str, Any]:
    checks: list[dict[str, str]] = []

    def check(name: str, condition: bool, detail: str = "") -> None:
        checks.append({"name": name, "status": "pass" if condition else "fail", "detail": detail})

    for label, path in [
        ("manifest", manifest_path),
        ("report", report_path),
        ("review", review_path),
    ]:
        check(f"file_exists:{label}", path.exists(), str(path))
    if not manifest_path.exists():
        return {"verdict": "fail", "checks": checks, "passed": 0, "failed": 1}

    manifest = _json(manifest_path)
    report = _text(report_path) if report_path.exists() else ""
    review = _text(review_path) if review_path.exists() else ""
    safety = manifest.get("safety", {})
    rate_limit = manifest.get("rate_limit", {})
    embedded = manifest.get("embedded_review", {})
    status = embedded.get("one_day_live_fetch_no_raw_write_status")

    check("explicit_allow_flag_present=true", manifest.get("explicit_allow_flag_present") is True)
    check("max_live_fetch_targets<=3", manifest.get("max_live_fetch_targets", 999) <= 3)
    check("network_fetch_performed=true", safety.get("network_fetch_performed") is True)
    for key in SAFETY_FALSE_KEYS:
        check(f"{key}=false", safety.get(key) is False)
    check("db_write_performed=false", manifest.get("db_write_performed") is False)
    check(
        "production_db_write_performed=false",
        manifest.get("production_db_write_performed") is False,
    )
    check("concurrency=1", rate_limit.get("concurrency") == 1)
    check("max_attempts_per_target=1", rate_limit.get("max_attempts_per_target") == 1)
    check("sleep_seconds>=5", rate_limit.get("sleep_seconds", 0) >= 5)
    check("stopped_early_present", "stopped_early" in manifest)
    check("stop_reason_present", "stop_reason" in manifest)
    check("fetch_results_present", isinstance(manifest.get("fetch_results"), list))
    for item in manifest.get("fetch_results", []):
        check(f"result_has_status:{item.get('source_match_id')}", "status_code" in item)
        check(f"result_has_content_type:{item.get('source_match_id')}", "content_type" in item)
        check(f"result_has_no_body:{item.get('source_match_id')}", "body" not in item)
    check("embedded_review_status_valid", status in ALLOWED_REVIEW_STATUS, str(status))
    for phrase in ["raw_response_body_saved: false", "db_write_performed: false"]:
        check(f"report_contains:{phrase}", phrase in report)
    for phrase in ["explicit allow flag review", "stop policy present"]:
        check(f"review_contains:{phrase}", phrase in review)

    passed = sum(1 for item in checks if item["status"] == "pass")
    failed = sum(1 for item in checks if item["status"] == "fail")
    return {
        "verdict": "pass" if failed == 0 else "fail",
        "checks": checks,
        "passed": passed,
        "failed": failed,
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Check one-day FotMob live fetch artifacts")
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    parser.add_argument("--report", type=Path, default=DEFAULT_REPORT)
    parser.add_argument("--review-report", type=Path, default=DEFAULT_REVIEW)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    result = run_checks(args.manifest, args.report, args.review_report)
    for item in result["checks"]:
        detail = f" ({item['detail']})" if item.get("detail") else ""
        print(f"[{item['status']}] {item['name']}{detail}")
    print(f"Verdict: {result['verdict']}  Passed: {result['passed']}  Failed: {result['failed']}")
    return 0 if result["verdict"] == "pass" else 1


if __name__ == "__main__":
    sys.exit(main())
