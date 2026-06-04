#!/usr/bin/env python3
"""Checker for FotMob controlled JSON probe no-write phase.

lifecycle: permanent
phase: FOTMOB-RAW-JSON-LONG-RUN-COLLECTOR-CONTROLLED-JSON-PROBE-NO-WRITE

Reads only manifest/report/review/endpoint-decision. No network, no DB, no raw write.
"""

from __future__ import annotations

import json
from pathlib import Path
import sys
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
MANIFEST_PATH = ROOT / "docs/_manifests/fotmob_controlled_json_probe_no_write_manifest.json"
REPORT_PATH = ROOT / "docs/_reports/FOTMOB_CONTROLLED_JSON_PROBE_NO_WRITE.md"
REVIEW_PATH = ROOT / "docs/_reports/FOTMOB_CONTROLLED_JSON_PROBE_NO_WRITE_REVIEW.md"
ENDPOINT_DECISION_PATH = (
    ROOT / "docs/_reports/FOTMOB_CONTROLLED_JSON_PROBE_NO_WRITE_ENDPOINT_DECISION.md"
)

EXPECTED_PHASE = "FOTMOB-RAW-JSON-LONG-RUN-COLLECTOR-CONTROLLED-JSON-PROBE-NO-WRITE"

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
    check(ENDPOINT_DECISION_PATH.exists(), "endpoint decision report missing")


def check_inherited(m: dict[str, Any]) -> None:
    ih = m.get("inherited_seed_status", {})
    check(ih.get("user_seed_count") == 12, "user_seed_count must be 12")
    check(ih.get("parsed_count") == 12, "parsed_count must be 12")
    check(ih.get("route_candidate_count") == 12, "route_candidate_count must be 12")


def check_probe_selection(m: dict[str, Any]) -> None:
    sel = m.get("probe_selection", {})
    check(sel.get("max_samples", 0) <= 3, "max_samples must be <= 3")
    check(sel.get("selected_sample_count", 0) <= 3, "selected_sample_count must be <= 3")
    check(len(sel.get("selected_match_ids", [])) <= 3, "selected_match_ids must be <= 3")


def check_probe_constraints(m: dict[str, Any]) -> None:
    ps = m.get("probe_summary", {})
    check(ps.get("max_network_requests", 0) <= 9, "max_network_requests must be <= 9")

    if not ps.get("allow_network_probe"):
        check(ps.get("network_requests_attempted", 0) == 0, "dry-run must have 0 network requests")
    else:
        check(
            ps.get("network_requests_attempted", 0) <= ps.get("max_network_requests", 9),
            "network requests exceeded max",
        )


def check_safety(m: dict[str, Any]) -> None:
    safety = m.get("safety", {})
    required_false = [
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
    rw = m.get("json_probe_readiness", {})
    check(rw.get("json_validated_count") == 0, "json_validated_count must be 0")
    check(rw.get("raw_write_eligible_count") == 0, "raw_write_eligible_count must be 0")
    check(
        rw.get("raw_write_blocked_until_json_validated") is True,
        "raw_write_blocked_until_json_validated must be true",
    )


def check_next_phase(m: dict[str, Any]) -> None:
    rec = m.get("recommended_next_phase", "")
    forbidden = ["RAW-JSON-DEV-WRITE", "RAW-MATCH-DATA", "DIRECT-RAW-WRITE"]
    for word in forbidden:
        check(word not in rec, f"recommended next phase must not contain {word}: {rec}")


def check_probe_results(m: dict[str, Any]) -> None:
    """Verify all probe results have safe states."""
    for r in m.get("probe_results", []):
        check(
            r.get("raw_write_eligible") is False,
            f"{r.get('probe_id')} raw_write_eligible must be false",
        )
        check(
            r.get("raw_json_write_performed") is False,
            f"{r.get('probe_id')} raw_json_write_performed must be false",
        )
        check(
            r.get("raw_response_body_saved") is False,
            f"{r.get('probe_id')} raw_response_body_saved must be false",
        )
        check(
            r.get("db_write_performed") is False,
            f"{r.get('probe_id')} db_write_performed must be false",
        )
        vs = r.get("validation_state", "")
        check(vs != "json_validated", f"{r.get('probe_id')} must not be json_validated")
        check(vs != "raw_write_ready", f"{r.get('probe_id')} must not be raw_write_ready")
        check(vs != "raw_write_eligible", f"{r.get('probe_id')} must not be raw_write_eligible")


def main() -> int:
    check_files()
    m = load_manifest()
    if m is None:
        print(f"FAIL: {len(errors)} error(s)")
        for item in errors:
            print(f"  - {item}")
        return FAIL

    check_inherited(m)
    check_probe_selection(m)
    check_probe_constraints(m)
    check_safety(m)
    check_readiness(m)
    check_next_phase(m)
    check_probe_results(m)

    if errors:
        print(f"FAIL: {len(errors)} error(s)")
        for item in errors:
            print(f"  - {item}")
        return FAIL
    print("PASS: all checks passed")
    return PASS


if __name__ == "__main__":
    sys.exit(main())
