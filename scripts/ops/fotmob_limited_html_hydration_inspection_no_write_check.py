#!/usr/bin/env python3
"""Checker for limited HTML hydration inspection no-write.

lifecycle: permanent
phase: FOTMOB-RAW-JSON-LONG-RUN-COLLECTOR-LIMITED-HTML-HYDRATION-INSPECTION-NO-WRITE
"""

from __future__ import annotations

import json
from pathlib import Path
import sys
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
MP = ROOT / "docs/_manifests/fotmob_limited_html_hydration_inspection_no_write_manifest.json"
RP = ROOT / "docs/_reports/FOTMOB_LIMITED_HTML_HYDRATION_INSPECTION_NO_WRITE.md"
RR = ROOT / "docs/_reports/FOTMOB_LIMITED_HTML_HYDRATION_INSPECTION_NO_WRITE_REVIEW.md"
DR = ROOT / "docs/_reports/FOTMOB_HYDRATION_STRUCTURE_DECISION.md"
EP = "FOTMOB-RAW-JSON-LONG-RUN-COLLECTOR-LIMITED-HTML-HYDRATION-INSPECTION-NO-WRITE"

FAIL, PASS = 1, 0
errors: list[str] = []


def err(msg: str) -> None:
    errors.append(msg)


def check(cond: bool, msg: str) -> None:
    if not cond:
        err(msg)


def main() -> int:
    check(MP.exists(), "manifest")
    check(RP.exists(), "report")
    check(RR.exists(), "review")
    check(DR.exists(), "decision")
    m = json.loads(MP.read_text(encoding="utf-8")) if MP.exists() else None
    if m is None:
        return FAIL
    check(m.get("phase") == EP, "phase")
    sel = m.get("inspection_selection", {})
    check(sel.get("selected_sample_count", 99) <= 2, "samples > 2")
    check(len(sel.get("selected_route_templates", [])) <= 2, "templates > 2")
    check(sel.get("max_body_bytes", 999999) <= 524288, "body > 512K")

    ps = m.get("inspection_summary", {})
    check(ps.get("max_network_requests", 99) <= 4, "requests > 4")
    if not ps.get("allow_network_probe"):
        check(ps.get("network_requests_attempted", 1) == 0, "dry-run requests")
    else:
        check(ps.get("network_requests_attempted", 99) <= 4, "requests > 4")

    s = m.get("safety", {})
    for k in [
        "full_body_read_performed",
        "full_html_saved",
        "html_body_saved",
        "raw_json_write_performed",
        "db_write_performed",
        "scheduler_enabled",
        "browser_automation_performed",
    ]:
        check(s.get(k) is False, k)

    rw = m.get("raw_write_readiness", {})
    check(rw.get("json_validated_count") == 0, "json_validated")
    check(rw.get("raw_write_eligible_count") == 0, "raw_write_eligible")
    for w in ["RAW-JSON-DEV-WRITE", "DIRECT-RAW-WRITE"]:
        check(w not in m["recommended_next_phase"], f"forbidden: {w}")

    for r in m.get("inspection_results", []):
        check(r.get("full_html_saved") is False, "html_saved")
        check(r.get("raw_json_write_performed") is False, "raw_json")
        check(r.get("raw_write_eligible") is False, "raw_write_eligible")

    if errors:
        print(f"FAIL: {len(errors)} error(s)")
        for e in errors:
            print(f"  - {e}")
        return FAIL
    print("PASS: all checks passed")
    return PASS


if __name__ == "__main__":
    sys.exit(main())
