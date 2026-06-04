#!/usr/bin/env python3
"""Checker for FotMob endpoint runtime request discovery plan no-write.

lifecycle: permanent
phase: FOTMOB-RAW-JSON-LONG-RUN-COLLECTOR-ENDPOINT-RUNTIME-REQUEST-DISCOVERY-PLAN-NO-WRITE
"""

from __future__ import annotations

import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
MANIFEST = (
    ROOT / "docs/_manifests/fotmob_endpoint_runtime_request_discovery_plan_no_write_manifest.json"
)
REPORT = ROOT / "docs/_reports/FOTMOB_ENDPOINT_RUNTIME_REQUEST_DISCOVERY_PLAN_NO_WRITE.md"
REVIEW = ROOT / "docs/_reports/FOTMOB_ENDPOINT_RUNTIME_REQUEST_DISCOVERY_PLAN_NO_WRITE_REVIEW.md"
NEXT_PLAN = ROOT / "docs/_reports/FOTMOB_ENDPOINT_RUNTIME_CANDIDATE_PROBE_NEXT_PLAN.md"

PHASE = "FOTMOB-RAW-JSON-LONG-RUN-COLLECTOR-ENDPOINT-RUNTIME-REQUEST-DISCOVERY-PLAN-NO-WRITE"
NEXT_PHASE = "FOTMOB-RAW-JSON-LONG-RUN-COLLECTOR-ENDPOINT-RUNTIME-CANDIDATE-PROBE-NO-WRITE"
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
    "browser_automation_allowed",
    "cookie_harvesting_allowed",
    "captcha_bypass_allowed",
    "proxy_rotation_allowed",
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
    decision = manifest.get("inherited_no_embedded_detail_decision", {})
    safety = manifest.get("safety", {})
    readiness = manifest.get("raw_write_readiness", {})
    probe = manifest.get("next_controlled_probe_plan", {})
    inv = manifest.get("endpoint_candidate_inventory", {})

    check(manifest.get("phase") == PHASE, "phase correct", errors)
    check(manifest.get("mode") == "offline_endpoint_runtime_discovery_plan", "mode correct", errors)
    check(
        decision.get("html_hydration_route_status") == "exhausted_no_embedded_match_detail",
        "html_hydration exhausted",
        errors,
    )
    check(
        decision.get("page_level_next_data_status") == "no_match_detail_json_embedded",
        "page no detail",
        errors,
    )
    check(decision.get("raw_json_readiness") == "not_ready", "raw_json not_ready", errors)
    check(decision.get("db_write_readiness") == "blocked", "db_write blocked", errors)
    check(decision.get("l2_harvesting_readiness") == "blocked", "l2 blocked", errors)
    check(inv.get("next_probe_candidate_count", 99) <= 3, "next_probe_candidates <= 3", errors)
    check(probe.get("max_candidates", 99) <= 3, "max_candidates <= 3", errors)
    check(probe.get("max_samples", 99) <= 2, "max_samples <= 2", errors)
    check(probe.get("max_network_requests", 99) <= 6, "max_network_requests <= 6", errors)
    check(probe.get("max_body_bytes", 999999) <= 262144, "max_body_bytes <= 262144", errors)
    check(
        probe.get("browser_automation_allowed") is False, "browser_automation_allowed=false", errors
    )
    check(
        probe.get("cookie_harvesting_allowed") is False, "cookie_harvesting_allowed=false", errors
    )
    check(probe.get("captcha_bypass_allowed") is False, "captcha_bypass_allowed=false", errors)
    check(probe.get("proxy_rotation_allowed") is False, "proxy_rotation_allowed=false", errors)
    check(probe.get("db_write_allowed") is False, "db_write_allowed=false", errors)
    check(probe.get("raw_write_allowed") is False, "raw_write_allowed=false", errors)
    check(
        manifest.get("recommended_next_phase") == NEXT_PHASE,
        "recommended next phase is endpoint probe",
        errors,
    )
    for flag in FALSE_SAFETY_FLAGS:
        check(safety.get(flag) is False, f"{flag}=false", errors)
    check(readiness.get("json_validated_count") == 0, "json_validated_count=0", errors)
    check(readiness.get("raw_write_eligible_count") == 0, "raw_write_eligible_count=0", errors)
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
    print("PASS: endpoint runtime discovery plan no-write checks passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
