#!/usr/bin/env python3
"""Checker for FotMob HTML hydration route probe no-write.

lifecycle: permanent
phase: FOTMOB-RAW-JSON-LONG-RUN-COLLECTOR-HTML-HYDRATION-ROUTE-PROBE-NO-WRITE
"""

from __future__ import annotations

import json
from pathlib import Path
import sys
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
MP = ROOT / "docs/_manifests/fotmob_html_hydration_route_probe_no_write_manifest.json"
RP = ROOT / "docs/_reports/FOTMOB_HTML_HYDRATION_ROUTE_PROBE_NO_WRITE.md"
RR = ROOT / "docs/_reports/FOTMOB_HTML_HYDRATION_ROUTE_PROBE_NO_WRITE_REVIEW.md"
DR = ROOT / "docs/_reports/FOTMOB_HTML_HYDRATION_ROUTE_DECISION.md"
EP = "FOTMOB-RAW-JSON-LONG-RUN-COLLECTOR-HTML-HYDRATION-ROUTE-PROBE-NO-WRITE"

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


def check_files():
    check(MP.exists(), "manifest missing")
    check(RP.exists(), "report missing")
    check(RR.exists(), "review missing")
    check(DR.exists(), "decision missing")


def main() -> int:
    check_files()
    m = load()
    if m is None:
        print(f"FAIL: {len(errors)} error(s)")
        for e in errors:
            print(f"  - {e}")
        return FAIL

    check(m.get("phase") == EP, "phase mismatch")
    sel = m.get("probe_selection", {})
    check(sel.get("selected_sample_count", 99) <= 3, "samples > 3")
    check(len(sel.get("selected_route_templates", [])) <= 2, "templates > 2")

    ps = m.get("probe_summary", {})
    check(ps.get("max_network_requests", 99) <= 6, "max_requests > 6")
    if not ps.get("allow_network_probe"):
        check(ps.get("network_requests_attempted", 1) == 0, "dry-run requests != 0")
    else:
        check(ps.get("network_requests_attempted", 99) <= 6, "requests > 6")

    s = m.get("safety", {})
    for k in [
        "db_read_performed",
        "db_write_performed",
        "response_body_read",
        "raw_response_body_saved",
        "html_body_saved",
        "raw_json_write_performed",
        "scheduler_enabled",
        "feature_parse_performed",
        "browser_automation_performed",
        "captcha_bypass_performed",
        "proxy_rotation_performed",
    ]:
        check(s.get(k) is False, f"{k} must be false")

    rw = m.get("raw_write_readiness", {})
    check(rw.get("json_validated_count") == 0, "json_validated != 0")
    check(rw.get("raw_write_eligible_count") == 0, "raw_write_eligible != 0")

    rec = m.get("recommended_next_phase", "")
    for w in ["RAW-JSON-DEV-WRITE", "DIRECT-RAW-WRITE"]:
        check(w not in rec, f"forbidden: {w}")

    for r in m.get("probe_results", []):
        check(r.get("body_read") is False, f"{r.get('probe_id')} body_read")
        check(r.get("raw_response_body_saved") is False, f"{r.get('probe_id')} body_saved")
        check(r.get("html_body_saved") is False, f"{r.get('probe_id')} html_saved")
        check(r.get("raw_write_eligible") is False, f"{r.get('probe_id')} raw_write_eligible")

    if errors:
        print(f"FAIL: {len(errors)} error(s)")
        for e in errors:
            print(f"  - {e}")
        return FAIL
    print("PASS: all checks passed")
    return PASS


if __name__ == "__main__":
    sys.exit(main())
