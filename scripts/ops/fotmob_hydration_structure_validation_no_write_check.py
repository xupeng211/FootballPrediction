#!/usr/bin/env python3
"""Checker for hydration structure validation no-write."""

import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
MP = ROOT / "docs/_manifests/fotmob_hydration_structure_validation_no_write_manifest.json"
RP = ROOT / "docs/_reports/FOTMOB_HYDRATION_STRUCTURE_VALIDATION_NO_WRITE.md"
RR = ROOT / "docs/_reports/FOTMOB_HYDRATION_STRUCTURE_VALIDATION_NO_WRITE_REVIEW.md"
DR = ROOT / "docs/_reports/FOTMOB_MATCH_DETAIL_CANDIDATE_DECISION.md"
EP = "FOTMOB-RAW-JSON-LONG-RUN-COLLECTOR-HYDRATION-STRUCTURE-VALIDATION-NO-WRITE"

errors = []


def check(c, m):
    if not c:
        errors.append(m)


def main():
    check(MP.exists(), "manifest")
    check(RP.exists(), "report")
    check(RR.exists(), "review")
    check(DR.exists(), "decision")
    if not MP.exists():
        return 1
    m = json.loads(MP.read_text(encoding="utf-8"))
    check(m.get("phase") == EP, "phase")
    sel = m.get("validation_selection", {})
    check(sel.get("selected_sample_count", 99) <= 2, "samples > 2")
    check("/matches/" in sel.get("route_template", ""), "wrong route")
    check(sel.get("max_body_bytes", 999999) <= 524288, "body > 512K")
    ps = m.get("validation_summary", {})
    check(ps.get("max_network_requests", 99) <= 2, "requests > 2")
    if not ps.get("allow_network_probe"):
        check(ps.get("network_requests_attempted", 1) == 0, "dry-run requests")
    else:
        check(ps.get("network_requests_attempted", 99) <= 2, "requests > 2")
    s = m.get("safety", {})
    for k in [
        "full_html_saved",
        "full_next_data_saved",
        "raw_json_write_performed",
        "db_write_performed",
    ]:
        check(s.get(k) is False, k)
    rw = m.get("raw_write_readiness", {})
    check(rw.get("json_validated_count") == 0, "json_validated")
    check(rw.get("raw_write_eligible_count") == 0, "raw_write_eligible")
    for w in ["RAW-JSON-DEV-WRITE", "DIRECT-RAW-WRITE"]:
        check(w not in m["recommended_next_phase"], f"forbidden: {w}")
    if errors:
        print(f"FAIL: {len(errors)} error(s)")
        for e in errors:
            print(f"  - {e}")
        return 1
    print("PASS: all checks passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
