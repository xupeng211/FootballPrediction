#!/usr/bin/env python3
"""Checker for HTML hydration extraction plan no-write.

lifecycle: permanent
phase: FOTMOB-RAW-JSON-LONG-RUN-COLLECTOR-HTML-HYDRATION-EXTRACTION-PLAN-NO-WRITE
"""

from __future__ import annotations

import json
from pathlib import Path
import sys
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
MP = ROOT / "docs/_manifests/fotmob_html_hydration_extraction_plan_no_write_manifest.json"
RP = ROOT / "docs/_reports/FOTMOB_HTML_HYDRATION_EXTRACTION_PLAN_NO_WRITE.md"
RR = ROOT / "docs/_reports/FOTMOB_HTML_HYDRATION_EXTRACTION_PLAN_NO_WRITE_REVIEW.md"
NP = ROOT / "docs/_reports/FOTMOB_LIMITED_HTML_HYDRATION_INSPECTION_NEXT_PLAN.md"
EP = "FOTMOB-RAW-JSON-LONG-RUN-COLLECTOR-HTML-HYDRATION-EXTRACTION-PLAN-NO-WRITE"
EN = "FOTMOB-RAW-JSON-LONG-RUN-COLLECTOR-LIMITED-HTML-HYDRATION-INSPECTION-NO-WRITE"

FAIL, PASS = 1, 0
errors: list[str] = []


def err(msg: str) -> None:
    errors.append(msg)


def check(cond: bool, msg: str) -> None:
    if not cond:
        err(msg)


def load() -> dict[str, Any] | None:
    if not MP.exists():
        err("manifest missing")
        return None
    return json.loads(MP.read_text(encoding="utf-8"))


def main() -> int:
    check(MP.exists(), "manifest missing")
    check(RP.exists(), "report missing")
    check(RR.exists(), "review missing")
    check(NP.exists(), "next plan missing")
    m = load()
    if m is None:
        print(f"FAIL: {len(errors)} error(s)")
        return FAIL

    check(m.get("phase") == EP, "phase mismatch")
    check(m.get("mode") == "offline_extraction_plan", "mode mismatch")
    ih = m.get("inherited_route_probe", {})
    check(ih.get("html_route_observed_count") == 6, "inherited observed != 6")
    check(ih.get("response_body_read") is False, "inherited body_read not false")
    check(len(m.get("extraction_plan_candidates", [])) >= 1, "no extraction candidates")

    np = m.get("limited_inspection_next_plan", {})
    check(np.get("max_body_bytes", 999999) <= 524288, "max_body_bytes > 512KB")
    check(np.get("max_network_requests", 99) <= 4, "max_requests > 4")
    check(m["recommended_next_phase"] == EN, f"next phase mismatch: {m['recommended_next_phase']}")

    s = m["safety"]
    for k in [
        "network_fetch_performed",
        "response_body_read",
        "raw_response_body_saved",
        "html_body_saved",
        "raw_json_write_performed",
        "db_write_performed",
        "scheduler_enabled",
        "feature_parse_performed",
        "browser_automation_performed",
    ]:
        check(s.get(k) is False, f"{k} must be false")

    rw = m["raw_write_readiness"]
    check(rw.get("json_validated_count") == 0, "json_validated != 0")
    check(rw.get("raw_write_eligible_count") == 0, "raw_write_eligible != 0")
    for w in ["RAW-JSON-DEV-WRITE", "DIRECT-RAW-WRITE"]:
        check(w not in m["recommended_next_phase"], f"forbidden: {w}")

    if errors:
        print(f"FAIL: {len(errors)} error(s)")
        for e in errors:
            print(f"  - {e}")
        return FAIL
    print("PASS: all checks passed")
    return PASS


if __name__ == "__main__":
    sys.exit(main())
