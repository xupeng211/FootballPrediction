#!/usr/bin/env python3
"""Checker for FotMob match ID route candidate no-write phase.

lifecycle: permanent
phase: FOTMOB-RAW-JSON-LONG-RUN-COLLECTOR-MATCH-ID-DISCOVERY-ROUTE-CANDIDATE-NO-WRITE

Reads only manifest/report/review-report. No network, no DB, no raw write.
"""

from __future__ import annotations

import json
from pathlib import Path
import sys
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
MANIFEST_PATH = ROOT / "docs/_manifests/fotmob_match_id_discovery_route_candidate_manifest.json"
REPORT_PATH = ROOT / "docs/_reports/FOTMOB_MATCH_ID_DISCOVERY_ROUTE_CANDIDATE_NO_WRITE.md"
REVIEW_REPORT_PATH = (
    ROOT / "docs/_reports/FOTMOB_MATCH_ID_DISCOVERY_ROUTE_CANDIDATE_NO_WRITE_REVIEW.md"
)
SAFE_NEXT_PHASES = {
    "FOTMOB-RAW-JSON-LONG-RUN-COLLECTOR-CONTROLLED-JSON-PROBE-NO-WRITE",
    "FOTMOB-RAW-JSON-LONG-RUN-COLLECTOR-KNOWN-MATCH-PAGE-PARSE-NO-WRITE-FOLLOWUP",
    "FOTMOB-RAW-JSON-LONG-RUN-COLLECTOR-MATCH-ID-DISCOVERY-ROUTE-CANDIDATE-RETRY-NO-WRITE",
}

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
    check(REVIEW_REPORT_PATH.exists(), "review report missing")


def check_counts(m: dict[str, Any]) -> None:
    inherited = m.get("source_review_inherited", {})
    check(inherited.get("input_target_count") == 14, "input_target_count must be 14")
    check(
        inherited.get("discovery_candidate_count") == 76,
        "discovery_candidate_count must be 76",
    )
    check(inherited.get("reviewed_sources") == 6, "reviewed_sources must be 6")


def check_samples(m: dict[str, Any]) -> None:
    selection = m.get("sample_selection", {})
    count = selection.get("selected_sample_count")
    check(isinstance(count, int) and count <= 3, "selected_sample_count must be <= 3")
    check(bool(m.get("route_candidates")), "route_candidates must exist")
    check(len(m.get("route_candidates", [])) == count, "route candidate count must match samples")


def check_route_status(m: dict[str, Any]) -> None:
    status = m.get("route_status_summary", {})
    check(status.get("route_validated_count") == 0, "route_validated_count must be 0")
    check(status.get("json_validated_count") == 0, "json_validated_count must be 0")
    for route in m.get("route_candidates", []):
        check(route.get("validation_state") != "json_validated", "json_validated state forbidden")
        check(route.get("raw_write_eligible") is False, "route raw_write_eligible must be false")


def check_readiness(m: dict[str, Any]) -> None:
    readiness = m.get("raw_write_readiness", {})
    check(readiness.get("raw_write_eligible_count") == 0, "raw_write_eligible_count must be 0")
    check(
        readiness.get("raw_write_blocked_until_json_validated") is True,
        "raw_write_blocked_until_json_validated must be true",
    )


def check_safety(m: dict[str, Any]) -> None:
    safety = m.get("safety", {})
    for key in [
        "db_write_performed",
        "raw_response_body_saved",
        "raw_json_write_performed",
        "scheduler_enabled",
        "feature_parse_performed",
        "browser_automation_performed",
        "captcha_bypass_performed",
        "proxy_rotation_performed",
    ]:
        check(safety.get(key) is False, f"{key} must be false")


def check_embedded_review(m: dict[str, Any]) -> None:
    embedded = m.get("embedded_review", {})
    check(embedded.get("route_candidate_status") == "pass", "embedded review status must be pass")


def check_next_phase(m: dict[str, Any]) -> None:
    rec = m.get("recommended_next_phase", "")
    check(rec in SAFE_NEXT_PHASES, f"recommended next phase not safe: {rec}")
    forbidden = ["RAW-JSON-DEV-WRITE", "RAW-MATCH-DATA", "RAW-WRITE"]
    for word in forbidden:
        check(word not in rec, f"recommended next phase must not contain {word}: {rec}")


def check_network(m: dict[str, Any]) -> None:
    network = m.get("network_probe_summary", {})
    attempted = network.get("network_requests_attempted")
    if network.get("allow_network_probe") is False:
        check(attempted == 0, "offline mode must attempt 0 network requests")
    if network.get("allow_network_probe") is True:
        check(isinstance(attempted, int) and attempted <= 3, "network requests must be <= 3")


def main() -> int:
    check_files()
    m = load_manifest()
    if m is None:
        print(f"FAIL: {len(errors)} error(s)")
        for item in errors:
            print(f"  - {item}")
        return FAIL

    check_counts(m)
    check_samples(m)
    check_route_status(m)
    check_readiness(m)
    check_safety(m)
    check_embedded_review(m)
    check_next_phase(m)
    check_network(m)

    if errors:
        print(f"FAIL: {len(errors)} error(s)")
        for item in errors:
            print(f"  - {item}")
        return FAIL
    print("PASS: all checks passed")
    return PASS


if __name__ == "__main__":
    sys.exit(main())
