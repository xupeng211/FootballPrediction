#!/usr/bin/env python3
"""Checker for FotMob JSON endpoint review no-write phase.

lifecycle: permanent
phase: FOTMOB-RAW-JSON-LONG-RUN-COLLECTOR-CONTROLLED-JSON-PROBE-ENDPOINT-REVIEW-NO-WRITE

Reads only manifest/report/review/next-probe-plan. No network, no DB, no raw write.
"""

from __future__ import annotations

import json
from pathlib import Path
import sys
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
MANIFEST_PATH = ROOT / "docs/_manifests/fotmob_json_endpoint_review_no_write_manifest.json"
REPORT_PATH = ROOT / "docs/_reports/FOTMOB_JSON_ENDPOINT_REVIEW_NO_WRITE.md"
REVIEW_PATH = ROOT / "docs/_reports/FOTMOB_JSON_ENDPOINT_REVIEW_NO_WRITE_REVIEW.md"
NEXT_PROBE_PLAN_PATH = ROOT / "docs/_reports/FOTMOB_JSON_ENDPOINT_NEXT_PROBE_PLAN_NO_WRITE.md"

EXPECTED_PHASE = "FOTMOB-RAW-JSON-LONG-RUN-COLLECTOR-CONTROLLED-JSON-PROBE-ENDPOINT-REVIEW-NO-WRITE"
EXPECTED_NEXT = "FOTMOB-RAW-JSON-LONG-RUN-COLLECTOR-CONTROLLED-ENDPOINT-CANDIDATE-PROBE-NO-WRITE"

FAIL, PASS = 1, 0
errors: list[str] = []


def err(msg: str) -> None:
    errors.append(msg)


def check(condition: bool, msg: str) -> None:
    if not condition:
        err(msg)


def load_manifest() -> dict[str, Any] | None:
    if not MANIFEST_PATH.exists():
        err(f"manifest missing: {MANIFEST_PATH}")
        return None
    try:
        return json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    except Exception as exc:
        err(f"manifest parse error: {exc}")
        return None


def check_files() -> None:
    check(MANIFEST_PATH.exists(), "manifest missing")
    check(REPORT_PATH.exists(), "report missing")
    check(REVIEW_PATH.exists(), "review report missing")
    check(NEXT_PROBE_PLAN_PATH.exists(), "next probe plan missing")


def check_phase(m: dict[str, Any]) -> None:
    check(m.get("phase") == EXPECTED_PHASE, f"phase must be {EXPECTED_PHASE}")
    check(m.get("mode") == "offline_endpoint_review", "mode must be offline_endpoint_review")


def check_inherited(m: dict[str, Any]) -> None:
    ih = m.get("inherited_probe_status", {})
    check(ih.get("network_requests_attempted") == 9, "network_requests_attempted must be 9")
    check(ih.get("json_parse_ok_count") == 0, "json_parse_ok_count must be 0")
    check(ih.get("invalid_count") == 9, "invalid_count must be 9")


def check_rejected(m: dict[str, Any]) -> None:
    rejected = m.get("rejected_endpoints", [])
    check(len(rejected) >= 3, f"rejected_endpoints count >= 3, got {len(rejected)}")


def check_historical_files(m: dict[str, Any]) -> None:
    hf = m.get("historical_files_reviewed", [])
    check(len(hf) >= 3, f"historical_files_reviewed count >= 3, got {len(hf)}")


def check_endpoint_candidates(m: dict[str, Any]) -> None:
    cands = m.get("endpoint_candidates", [])
    check(len(cands) >= 1, f"endpoint_candidates count >= 1, got {len(cands)}")


def check_next_probe_plan(m: dict[str, Any]) -> None:
    plan = m.get("next_probe_plan", {})
    check(plan.get("selected_candidate_count", 0) >= 1, "next probe plan must have >= 1 candidate")
    check(plan.get("max_samples") <= 3, "max_samples must be <= 3")
    check(plan.get("max_endpoint_templates") <= 3, "max_endpoint_templates must be <= 3")
    check(plan.get("max_network_requests") <= 9, "max_network_requests must be <= 9")


def check_safety(m: dict[str, Any]) -> None:
    safety = m.get("safety", {})
    required_false = [
        "network_fetch_performed",
        "db_read_performed",
        "db_write_performed",
        "production_db_write_performed",
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
    ]
    for key in required_false:
        check(safety.get(key) is False, f"{key} must be false")


def check_readiness(m: dict[str, Any]) -> None:
    rw = m.get("raw_write_readiness", {})
    check(rw.get("json_validated_count") == 0, "json_validated_count must be 0")
    check(rw.get("raw_write_eligible_count") == 0, "raw_write_eligible_count must be 0")
    check(
        rw.get("raw_write_blocked_until_json_validated") is True,
        "raw_write_blocked_until_json_validated must be true",
    )


def check_next_phase(m: dict[str, Any]) -> None:
    rec = m.get("recommended_next_phase", "")
    check(rec == EXPECTED_NEXT, f"recommended next phase must be {EXPECTED_NEXT}, got {rec}")
    forbidden = ["RAW-JSON-DEV-WRITE", "RAW-MATCH-DATA", "DIRECT-RAW-WRITE", "L2-RAW-HARVESTING"]
    for word in forbidden:
        check(word not in rec, f"recommended next phase must not contain {word}: {rec}")


def main() -> int:
    check_files()
    m = load_manifest()
    if m is None:
        print(f"FAIL: {len(errors)} error(s)")
        for item in errors:
            print(f"  - {item}")
        return FAIL

    check_phase(m)
    check_inherited(m)
    check_rejected(m)
    check_historical_files(m)
    check_endpoint_candidates(m)
    check_next_probe_plan(m)
    check_safety(m)
    check_readiness(m)
    check_next_phase(m)

    if errors:
        print(f"FAIL: {len(errors)} error(s)")
        for item in errors:
            print(f"  - {item}")
        return FAIL
    print("PASS: all checks passed")
    return PASS


if __name__ == "__main__":
    sys.exit(main())
