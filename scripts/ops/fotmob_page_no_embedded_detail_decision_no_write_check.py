#!/usr/bin/env python3
"""Checker for FotMob page no embedded detail decision no-write outputs.

lifecycle: permanent
phase: FOTMOB-RAW-JSON-LONG-RUN-COLLECTOR-FOTMOB-PAGE-NO-EMBEDDED-DETAIL-DECISION-NO-WRITE
"""

from __future__ import annotations

import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
MANIFEST = ROOT / "docs/_manifests/fotmob_page_no_embedded_detail_decision_no_write_manifest.json"
REPORT = ROOT / "docs/_reports/FOTMOB_PAGE_NO_EMBEDDED_DETAIL_DECISION_NO_WRITE.md"
REVIEW = ROOT / "docs/_reports/FOTMOB_PAGE_NO_EMBEDDED_DETAIL_DECISION_NO_WRITE_REVIEW.md"
NEXT_PLAN = ROOT / "docs/_reports/FOTMOB_ENDPOINT_RUNTIME_REQUEST_DISCOVERY_NEXT_PLAN.md"

PHASE = "FOTMOB-RAW-JSON-LONG-RUN-COLLECTOR-FOTMOB-PAGE-NO-EMBEDDED-DETAIL-DECISION-NO-WRITE"
NEXT_PHASE = "FOTMOB-RAW-JSON-LONG-RUN-COLLECTOR-ENDPOINT-RUNTIME-REQUEST-DISCOVERY-PLAN-NO-WRITE"
FORBIDDEN_REC = ["DIRECT-RAW-WRITE", "RAW-JSON-WRITE", "RAW-WRITE-EXECUTION"]

FALSE_SAFETY_FLAGS = [
    "network_fetch_performed",
    "response_body_read",
    "bounded_body_read_performed",
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


def main() -> int:
    errors: list[str] = []
    check(MANIFEST.exists(), "manifest exists", errors)
    check(REPORT.exists(), "report exists", errors)
    check(REVIEW.exists(), "review report exists", errors)
    check(NEXT_PLAN.exists(), "next plan exists", errors)
    if not MANIFEST.exists():
        print("FAIL: manifest missing")
        return 1

    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    inherited_rv = manifest.get("inherited_route_variant_followup", {})
    decision = manifest.get("formal_decision", {})
    safety = manifest.get("safety", {})
    readiness = manifest.get("raw_write_readiness", {})
    next_plan = manifest.get("next_endpoint_runtime_discovery_plan", {})

    check(manifest.get("phase") == PHASE, "phase correct", errors)
    check(manifest.get("mode") == "offline_no_embedded_detail_decision", "mode correct", errors)
    check(
        inherited_rv.get("route_variant_unlocks_detail_candidate_count") == 0,
        "route_variant_unlocks_detail=0",
        errors,
    )
    check(
        inherited_rv.get("en_variant_detail_unlocked") is False,
        "en_variant_detail_unlocked=false",
        errors,
    )
    check(
        inherited_rv.get("slug_variant_detail_unlocked") is False,
        "slug_variant_detail_unlocked=false",
        errors,
    )
    check(
        decision.get("html_hydration_route_status") == "exhausted_no_embedded_match_detail",
        "html_hydration_route_status exhausted",
        errors,
    )
    check(
        decision.get("page_level_next_data_status") == "no_match_detail_json_embedded",
        "page_level_next_data_status no detail",
        errors,
    )
    check(decision.get("raw_json_readiness") == "not_ready", "raw_json_readiness not_ready", errors)
    check(decision.get("db_write_readiness") == "blocked", "db_write_readiness blocked", errors)
    check(
        decision.get("l2_harvesting_readiness") == "blocked",
        "l2_harvesting_readiness blocked",
        errors,
    )
    check(
        manifest.get("recommended_next_phase") == NEXT_PHASE,
        "recommended next phase is endpoint/runtime plan",
        errors,
    )
    for flag in FALSE_SAFETY_FLAGS:
        check(safety.get(flag) is False, f"{flag}=false", errors)
    check(safety.get("db_read_performed") is False, "db_read_performed=false", errors)
    check(readiness.get("json_validated_count") == 0, "json_validated_count=0", errors)
    check(readiness.get("raw_write_eligible_count") == 0, "raw_write_eligible_count=0", errors)
    check(next_plan.get("network_allowed") is False, "next network_allowed=false", errors)
    check(
        next_plan.get("browser_automation_allowed") is False,
        "next browser_automation_allowed=false",
        errors,
    )
    check(next_plan.get("raw_write_allowed") is False, "next raw_write_allowed=false", errors)
    rec = manifest.get("recommended_next_phase", "")
    check(
        not any(token in rec for token in FORBIDDEN_REC),
        "no direct raw write recommendation",
        errors,
    )

    if errors:
        print(f"FAIL: {len(errors)} error(s)")
        for error in errors:
            print(f"  - {error}")
        return 1
    print("PASS: no embedded detail decision no-write checks passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
