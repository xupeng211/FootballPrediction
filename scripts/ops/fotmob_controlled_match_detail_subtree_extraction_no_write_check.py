#!/usr/bin/env python3
"""Checker for controlled FotMob subtree extraction no-write outputs.

lifecycle: permanent
phase: FOTMOB-RAW-JSON-LONG-RUN-COLLECTOR-CONTROLLED-MATCH-DETAIL-SUBTREE-EXTRACTION-NO-WRITE
"""

from __future__ import annotations

import json
from pathlib import Path
import sys
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
MANIFEST = (
    ROOT
    / "docs/_manifests/fotmob_controlled_match_detail_subtree_extraction_no_write_manifest.json"
)
REPORT = ROOT / "docs/_reports/FOTMOB_CONTROLLED_MATCH_DETAIL_SUBTREE_EXTRACTION_NO_WRITE.md"
REVIEW = ROOT / "docs/_reports/FOTMOB_CONTROLLED_MATCH_DETAIL_SUBTREE_EXTRACTION_NO_WRITE_REVIEW.md"
DECISION = ROOT / "docs/_reports/FOTMOB_MATCH_DETAIL_SUBTREE_CANDIDATE_DECISION.md"
PHASE = "FOTMOB-RAW-JSON-LONG-RUN-COLLECTOR-CONTROLLED-MATCH-DETAIL-SUBTREE-EXTRACTION-NO-WRITE"
ROUTE_TEMPLATE = "/matches/{route_code}/{match_id}"

FALSE_FLAGS = [
    "full_body_read_performed",
    "full_html_saved",
    "raw_response_body_saved",
    "html_body_saved",
    "full_next_data_saved",
    "candidate_subtree_value_saved",
    "raw_json_write_performed",
    "db_write_performed",
    "production_db_write_performed",
    "scheduler_enabled",
    "feature_parse_performed",
    "browser_automation_performed",
    "captcha_bypass_performed",
    "proxy_rotation_performed",
]


def check(condition: bool, message: str, errors: list[str]) -> None:
    if not condition:
        errors.append(message)


def _load_manifest(errors: list[str]) -> dict[str, Any]:
    check(MANIFEST.exists(), "manifest exists", errors)
    check(REPORT.exists(), "report exists", errors)
    check(REVIEW.exists(), "review report exists", errors)
    check(DECISION.exists(), "decision report exists", errors)
    if not MANIFEST.exists():
        return {}
    return json.loads(MANIFEST.read_text(encoding="utf-8"))


def _check_no_direct_raw_write_recommendation(manifest: dict[str, Any], errors: list[str]) -> None:
    rec = manifest.get("recommended_next_phase", "")
    forbidden = ["DIRECT-RAW-WRITE", "RAW-JSON-WRITE", "RAW-WRITE-EXECUTION"]
    check(
        not any(token in rec for token in forbidden),
        "recommended next phase is not direct raw write",
        errors,
    )


def main() -> int:
    errors: list[str] = []
    manifest = _load_manifest(errors)
    if not manifest:
        print("FAIL: manifest missing")
        return 1

    check(manifest.get("phase") == PHASE, "phase correct", errors)
    selection = manifest.get("extraction_selection", {})
    summary = manifest.get("extraction_summary", {})
    safety = manifest.get("safety", {})
    readiness = manifest.get("raw_write_readiness", {})
    check(selection.get("selected_sample_count", 99) <= 2, "selected_sample_count<=2", errors)
    check(
        selection.get("route_template") == ROUTE_TEMPLATE,
        "route_template=/matches/{route_code}/{match_id}",
        errors,
    )
    check(summary.get("max_network_requests", 99) <= 2, "max_network_requests<=2", errors)
    check(selection.get("max_body_bytes", 999999) <= 524288, "max_body_bytes<=524288", errors)
    check(selection.get("max_subtree_scan_depth", 99) <= 8, "max_subtree_scan_depth<=8", errors)
    if summary.get("allow_network_probe") is False:
        check(
            summary.get("network_requests_attempted") == 0,
            "dry-run has zero network requests",
            errors,
        )
    if summary.get("allow_network_probe") is True:
        check(summary.get("network_requests_attempted", 99) <= 2, "live requests<=2", errors)
    for flag in FALSE_FLAGS:
        check(safety.get(flag) is False, f"{flag}=false", errors)
    check(safety.get("db_read_performed") is False, "db_read_performed=false", errors)
    check(readiness.get("json_validated_count") == 0, "json_validated_count=0", errors)
    check(readiness.get("raw_write_eligible_count") == 0, "raw_write_eligible_count=0", errors)
    for result in manifest.get("extraction_results", []):
        for flag in [
            "full_html_saved",
            "raw_response_body_saved",
            "html_body_saved",
            "full_next_data_saved",
            "candidate_subtree_value_saved",
            "raw_json_write_performed",
            "db_write_performed",
            "raw_write_eligible",
        ]:
            check(result.get(flag) is False, f"{result.get('extraction_id')} {flag}=false", errors)
    _check_no_direct_raw_write_recommendation(manifest, errors)
    if errors:
        print(f"FAIL: {len(errors)} error(s)")
        for error in errors:
            print(f"  - {error}")
        return 1
    print("PASS: controlled subtree extraction no-write checks passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
