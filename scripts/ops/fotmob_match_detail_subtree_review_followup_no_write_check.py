#!/usr/bin/env python3
"""Checker for FotMob subtree review follow-up no-write outputs.

lifecycle: permanent
phase: FOTMOB-RAW-JSON-LONG-RUN-COLLECTOR-MATCH-DETAIL-SUBTREE-REVIEW-FOLLOWUP-NO-WRITE
"""

from __future__ import annotations

import json
from pathlib import Path
import sys
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
MANIFEST = (
    ROOT / "docs/_manifests/fotmob_match_detail_subtree_review_followup_no_write_manifest.json"
)
REPORT = ROOT / "docs/_reports/FOTMOB_MATCH_DETAIL_SUBTREE_REVIEW_FOLLOWUP_NO_WRITE.md"
REVIEW = ROOT / "docs/_reports/FOTMOB_MATCH_DETAIL_SUBTREE_REVIEW_FOLLOWUP_NO_WRITE_REVIEW.md"
NEXT_PLAN = ROOT / "docs/_reports/FOTMOB_HYDRATION_KEYSPACE_REVIEW_NEXT_PLAN.md"

PHASE = "FOTMOB-RAW-JSON-LONG-RUN-COLLECTOR-MATCH-DETAIL-SUBTREE-REVIEW-FOLLOWUP-NO-WRITE"
MODE = "offline_subtree_review_followup"
NEXT_PHASE = "FOTMOB-RAW-JSON-LONG-RUN-COLLECTOR-HYDRATION-KEYSPACE-REVIEW-NO-WRITE"

FALSE_SAFETY_FLAGS = [
    "network_fetch_performed",
    "response_body_read",
    "full_html_saved",
    "html_body_saved",
    "full_next_data_saved",
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


def load_manifest(errors: list[str]) -> dict[str, Any]:
    check(MANIFEST.exists(), "manifest exists", errors)
    check(REPORT.exists(), "report exists", errors)
    check(REVIEW.exists(), "review report exists", errors)
    check(NEXT_PLAN.exists(), "next plan exists", errors)
    if not MANIFEST.exists():
        return {}
    return json.loads(MANIFEST.read_text(encoding="utf-8"))


def no_direct_raw_write_recommendation(manifest: dict[str, Any], errors: list[str]) -> None:
    rec = manifest.get("recommended_next_phase", "")
    forbidden = ["DIRECT-RAW-WRITE", "RAW-JSON-WRITE", "RAW-WRITE-EXECUTION"]
    check(
        not any(token in rec for token in forbidden), "no direct raw write recommendation", errors
    )


def main() -> int:
    errors: list[str] = []
    manifest = load_manifest(errors)
    if not manifest:
        print("FAIL: manifest missing")
        return 1
    inherited = manifest.get("inherited_controlled_subtree_extraction", {})
    negative = manifest.get("negative_findings", {})
    readiness = manifest.get("raw_write_readiness", {})
    safety = manifest.get("safety", {})
    next_plan = manifest.get("next_keyspace_review_plan", {})

    check(manifest.get("phase") == PHASE, "phase correct", errors)
    check(manifest.get("mode") == MODE, "mode=offline_subtree_review_followup", errors)
    check(
        inherited.get("fallback_present_count") == 2, "inherited fallback_present_count=2", errors
    )
    check(inherited.get("target_match_id_seen_count") == 0, "target_match_id_seen_count=0", errors)
    check(inherited.get("strong_candidate_count") == 0, "strong_candidate_count=0", errors)
    check(
        inherited.get("generic_or_irrelevant_count") == 2, "generic_or_irrelevant_count=2", errors
    )
    check(
        negative.get("notable_matches_is_not_match_detail") is True,
        "notable_matches_is_not_match_detail=true",
        errors,
    )
    check(negative.get("keyspace_review_required") is True, "keyspace_review_required=true", errors)
    check(
        negative.get("route_variant_review_required") is True,
        "route_variant_review_required=true",
        errors,
    )
    check(
        manifest.get("recommended_next_phase") == NEXT_PHASE,
        "recommended next phase is keyspace review no-write",
        errors,
    )
    check(next_plan.get("max_network_requests", 99) <= 2, "next max_network_requests<=2", errors)
    check(next_plan.get("max_body_bytes", 999999) <= 524288, "next max_body_bytes<=524288", errors)
    check(
        next_plan.get("max_key_paths_recorded", 999) <= 500,
        "next max_key_paths_recorded<=500",
        errors,
    )
    for flag in FALSE_SAFETY_FLAGS:
        check(safety.get(flag) is False, f"{flag}=false", errors)
    check(safety.get("raw_response_body_saved") is False, "raw_response_body_saved=false", errors)
    check(safety.get("db_read_performed") is False, "db_read_performed=false", errors)
    check(readiness.get("json_validated_count") == 0, "json_validated_count=0", errors)
    check(readiness.get("raw_write_eligible_count") == 0, "raw_write_eligible_count=0", errors)
    no_direct_raw_write_recommendation(manifest, errors)

    if errors:
        print(f"FAIL: {len(errors)} error(s)")
        for error in errors:
            print(f"  - {error}")
        return 1
    print("PASS: subtree review follow-up no-write checks passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
