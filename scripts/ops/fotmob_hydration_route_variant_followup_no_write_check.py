#!/usr/bin/env python3
"""Checker for FotMob hydration route variant follow-up no-write outputs.

lifecycle: permanent
phase: FOTMOB-RAW-JSON-LONG-RUN-COLLECTOR-HYDRATION-ROUTE-VARIANT-FOLLOWUP-NO-WRITE
"""

from __future__ import annotations

import json
from pathlib import Path
import sys
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
MANIFEST = ROOT / "docs/_manifests/fotmob_hydration_route_variant_followup_no_write_manifest.json"
REPORT = ROOT / "docs/_reports/FOTMOB_HYDRATION_ROUTE_VARIANT_FOLLOWUP_NO_WRITE.md"
REVIEW = ROOT / "docs/_reports/FOTMOB_HYDRATION_ROUTE_VARIANT_FOLLOWUP_NO_WRITE_REVIEW.md"
DECISION = ROOT / "docs/_reports/FOTMOB_HYDRATION_ROUTE_VARIANT_DECISION.md"

PHASE = "FOTMOB-RAW-JSON-LONG-RUN-COLLECTOR-HYDRATION-ROUTE-VARIANT-FOLLOWUP-NO-WRITE"
FORBIDDEN_REC = ["DIRECT-RAW-WRITE", "RAW-JSON-WRITE", "RAW-WRITE-EXECUTION"]

FALSE_SAFETY_FLAGS = [
    "full_body_read_performed",
    "full_html_saved",
    "raw_response_body_saved",
    "html_body_saved",
    "full_next_data_saved",
    "value_persistence_performed",
    "raw_json_write_performed",
    "db_write_performed",
    "production_db_write_performed",
    "feature_parse_performed",
    "scheduler_enabled",
    "raw_write_ready_marked",
    "browser_automation_performed",
    "captcha_bypass_performed",
    "proxy_rotation_performed",
]


def check(condition: bool, message: str, errors: list[str]) -> None:
    if not condition:
        errors.append(message)


def load_manifest(errors: list[str]) -> dict[str, Any]:
    check(MANIFEST.exists(), "manifest exists", errors)
    check(REPORT.exists(), "report exists", errors)
    check(REVIEW.exists(), "review report exists", errors)
    check(DECISION.exists(), "decision report exists", errors)
    if not MANIFEST.exists():
        return {}
    return json.loads(MANIFEST.read_text(encoding="utf-8"))


def no_direct_raw_write_recommendation(manifest: dict[str, Any], errors: list[str]) -> None:
    rec = manifest.get("recommended_next_phase", "")
    check(
        not any(token in rec for token in FORBIDDEN_REC),
        "no direct raw write recommendation",
        errors,
    )


def main() -> int:
    errors: list[str] = []
    manifest = load_manifest(errors)
    if not manifest:
        print("FAIL: manifest missing")
        return 1

    selection = manifest.get("route_variant_selection", {})
    summary = manifest.get("route_variant_summary", {})
    readiness = manifest.get("raw_write_readiness", {})
    safety = manifest.get("safety", {})
    results = manifest.get("route_variant_results", [])

    check(manifest.get("phase") == PHASE, "phase correct", errors)
    check(selection.get("max_samples", 99) <= 2, "max_samples<=2", errors)
    check(selection.get("max_route_variants", 99) <= 2, "max_route_variants<=2", errors)
    check(summary.get("max_network_requests", 99) <= 4, "max_network_requests<=4", errors)
    check(selection.get("max_body_bytes", 999999) <= 524288, "max_body_bytes<=524288", errors)
    check(selection.get("max_scan_depth", 99) <= 12, "max_scan_depth<=12", errors)
    check(
        selection.get("max_key_paths_recorded", 999) <= 500, "max_key_paths_recorded<=500", errors
    )
    check(selection.get("max_value_preview_chars", -1) == 0, "max_value_preview_chars=0", errors)

    allow_network = summary.get("allow_network_probe", False)
    attempted = summary.get("network_requests_attempted", 0)
    if not allow_network:
        check(attempted == 0, "dry-run: network_requests_attempted=0", errors)
    else:
        check(attempted <= 4, "live: network_requests_attempted<=4", errors)

    for flag in FALSE_SAFETY_FLAGS:
        check(safety.get(flag) is False, f"safety.{flag}=false", errors)

    check(safety.get("db_read_performed") is False, "db_read_performed=false", errors)
    check(readiness.get("json_validated_count") == 0, "json_validated_count=0", errors)
    check(readiness.get("raw_write_eligible_count") == 0, "raw_write_eligible_count=0", errors)

    for entry in results:
        for key in [
            "full_html_saved",
            "raw_response_body_saved",
            "html_body_saved",
            "full_next_data_saved",
            "raw_json_write_performed",
            "db_write_performed",
            "raw_write_eligible",
        ]:
            check(
                entry.get(key) is not True, f"result {entry.get('review_id')}.{key}=false", errors
            )
        check(
            entry.get("value_persistence_performed") is not True,
            f"result {entry.get('review_id')}.value_persistence_performed=false",
            errors,
        )

    no_direct_raw_write_recommendation(manifest, errors)

    if errors:
        print(f"FAIL: {len(errors)} error(s)")
        for error in errors:
            print(f"  - {error}")
        return 1
    print("PASS: route variant follow-up no-write checks passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
