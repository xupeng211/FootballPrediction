#!/usr/bin/env python3
"""Checker for FotMob endpoint runtime candidate probe no-write outputs.

lifecycle: permanent
phase: FOTMOB-RAW-JSON-LONG-RUN-COLLECTOR-ENDPOINT-RUNTIME-CANDIDATE-PROBE-NO-WRITE
"""

from __future__ import annotations

import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
MANIFEST = ROOT / "docs/_manifests/fotmob_endpoint_runtime_candidate_probe_no_write_manifest.json"
REPORT = ROOT / "docs/_reports/FOTMOB_ENDPOINT_RUNTIME_CANDIDATE_PROBE_NO_WRITE.md"
REVIEW = ROOT / "docs/_reports/FOTMOB_ENDPOINT_RUNTIME_CANDIDATE_PROBE_NO_WRITE_REVIEW.md"
DECISION = ROOT / "docs/_reports/FOTMOB_ENDPOINT_RUNTIME_CANDIDATE_DECISION.md"

PHASE = "FOTMOB-RAW-JSON-LONG-RUN-COLLECTOR-ENDPOINT-RUNTIME-CANDIDATE-PROBE-NO-WRITE"
VALID_PHASES = [
    "FOTMOB-RAW-JSON-LONG-RUN-COLLECTOR-ENDPOINT-CANDIDATE-RESPONSE-VALIDATION-NO-WRITE",
    "FOTMOB-RAW-JSON-LONG-RUN-COLLECTOR-FOTMOB-RAW-DETAIL-DOWNGRADE-DECISION-NO-WRITE",
]
FORBIDDEN_REC = ["DIRECT-RAW-WRITE", "RAW-JSON-WRITE", "RAW-WRITE-EXECUTION"]

FALSE_SAFETY = [
    "full_body_read_performed",
    "response_body_saved",
    "raw_response_body_saved",
    "full_html_saved",
    "html_body_saved",
    "full_next_data_saved",
    "value_persistence_performed",
    "raw_json_write_performed",
    "db_read_performed",
    "db_write_performed",
    "production_db_write_performed",
    "feature_parse_performed",
    "scheduler_enabled",
    "raw_write_ready_marked",
    "browser_automation_performed",
    "cookie_harvesting_performed",
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
    check(DECISION.exists(), "decision report exists", errors)
    if not MANIFEST.exists():
        print("FAIL: manifest missing")
        return 1

    m = json.loads(MANIFEST.read_text(encoding="utf-8"))
    limits = m.get("probe_limits", {})
    summary = m.get("probe_summary", {})
    safety = m.get("safety", {})
    readiness = m.get("raw_write_readiness", {})
    results = m.get("probe_results", [])

    check(m.get("phase") == PHASE, "phase correct", errors)
    selected = m.get("selected_candidates", [])
    check(set(selected) == {"ep-004", "ep-005", "ep-006"}, "selected=ep-004/005/006", errors)
    check(limits.get("max_candidates", 99) <= 3, "max_candidates<=3", errors)
    check(limits.get("max_samples", 99) <= 2, "max_samples<=2", errors)
    check(limits.get("max_network_requests", 99) <= 6, "max_network_requests<=6", errors)
    check(limits.get("max_body_bytes", 999999) <= 262144, "max_body_bytes<=262144", errors)

    allow_net = summary.get("allow_network_probe", False)
    attempted = summary.get("network_requests_attempted", 0)
    if not allow_net:
        check(attempted == 0, "dry-run: network=0", errors)
    else:
        check(attempted <= 6, "live: network<=6", errors)

    for flag in FALSE_SAFETY:
        check(safety.get(flag) is False, f"{flag}=false", errors)
    for r in results:
        for k in [
            "response_body_saved",
            "raw_response_body_saved",
            "raw_json_write_performed",
            "db_write_performed",
        ]:
            check(r.get(k) is not True, f"result {r.get('candidate_id')}.{k}=false", errors)

    check(readiness.get("json_validated_count") == 0, "json_validated=0", errors)
    check(readiness.get("raw_write_eligible_count") == 0, "raw_write_eligible=0", errors)

    rec = m.get("recommended_next_phase", "")
    check(rec in VALID_PHASES or rec == PHASE, f"next phase valid: {rec}", errors)
    check(not any(t in rec for t in FORBIDDEN_REC), "no direct raw write", errors)

    if errors:
        print(f"FAIL: {len(errors)} error(s)")
        for e in errors:
            print(f"  - {e}")
        return 1
    print("PASS: endpoint runtime candidate probe no-write checks passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
