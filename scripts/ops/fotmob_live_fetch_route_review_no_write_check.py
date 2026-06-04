#!/usr/bin/env python3
"""Checker for FotMob live fetch route review no-write phase.

lifecycle: permanent
phase: FOTMOB-RAW-JSON-LONG-RUN-COLLECTOR-LIVE-FETCH-ROUTE-REVIEW-NO-WRITE

Validates manifest / report / review-report consistency and safety boundaries.
No network access, no DB connection, no live fetch.
"""

from __future__ import annotations

import json
from pathlib import Path
import sys
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
MANIFEST_PATH = ROOT / "docs/_manifests/fotmob_live_fetch_route_review_no_write_manifest.json"
REPORT_PATH = ROOT / "docs/_reports/FOTMOB_LIVE_FETCH_ROUTE_REVIEW_NO_WRITE.md"
REVIEW_REPORT_PATH = ROOT / "docs/_reports/FOTMOB_LIVE_FETCH_ROUTE_REVIEW_NO_WRITE_REVIEW.md"

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


def check_files_exist() -> None:
    check(MANIFEST_PATH.exists(), f"manifest missing: {MANIFEST_PATH}")
    check(REPORT_PATH.exists(), f"report missing: {REPORT_PATH}")
    check(REVIEW_REPORT_PATH.exists(), f"review report missing: {REVIEW_REPORT_PATH}")


def check_previous_phase(m: dict[str, Any]) -> None:
    prev = m.get("reviewed_previous_phase", {})
    check(
        prev.get("previous_stop_reason") == "unexpected_html",
        f"expected previous_stop_reason=unexpected_html, got {prev.get('previous_stop_reason')}",
    )
    check(
        prev.get("previous_status_code") == 404,
        f"expected previous_status_code=404, got {prev.get('previous_status_code')}",
    )
    check(
        prev.get("previous_json_parse_ok_count") == 0,
        "expected previous_json_parse_ok_count=0",
    )


def check_route_review(m: dict[str, Any]) -> None:
    review = m.get("route_review", {})
    check("route_review_status" in review, "route_review_status missing")
    check("source_identity_quality" in review, "source_identity_quality missing")
    check("likely_failure_reason" in review, "likely_failure_reason missing")
    check("match_id_discovery_required" in review, "match_id_discovery_required missing")
    check("reliable_route_candidate_found" in review, "reliable_route_candidate_found missing")

    # If no reliable candidates, status must be blocked or partial, not pass
    if review.get("reliable_route_candidate_found") is False:
        check(
            review.get("route_review_status") != "pass",
            "route_review_status cannot be pass when no reliable route candidates",
        )


def check_safety(m: dict[str, Any]) -> None:
    safety = m.get("safety", {})
    check(safety.get("raw_response_body_saved") is False, "raw_response_body_saved must be false")
    check(safety.get("raw_json_write_performed") is False, "raw_json_write_performed must be false")
    check(
        safety.get("fotmob_raw_match_payloads_write_performed") is False,
        "fotmob_raw_match_payloads_write_performed must be false",
    )
    check(
        safety.get("raw_match_data_write_performed") is False,
        "raw_match_data_write_performed must be false",
    )
    check(safety.get("feature_parse_performed") is False, "feature_parse_performed must be false")
    check(safety.get("scheduler_enabled") is False, "scheduler_enabled must be false")
    check(safety.get("raw_write_ready_marked") is False, "raw_write_ready_marked must be false")
    check(
        safety.get("browser_automation_performed") is False,
        "browser_automation_performed must be false",
    )
    check(safety.get("captcha_bypass_performed") is False, "captcha_bypass_performed must be false")
    check(safety.get("proxy_rotation_performed") is False, "proxy_rotation_performed must be false")
    check(safety.get("retry_storm_performed") is False, "retry_storm_performed must be false")


def check_db_safety(m: dict[str, Any]) -> None:
    check(m.get("db_write_performed") is False, "db_write_performed must be false")
    check(
        m.get("production_db_write_performed") is False,
        "production_db_write_performed must be false",
    )


def check_embedded_review(m: dict[str, Any]) -> None:
    embedded = m.get("embedded_review", {})
    check(
        "live_fetch_route_review_no_write_status" in embedded,
        "embedded review status missing",
    )


def check_recommended_next_phase(m: dict[str, Any]) -> None:
    recommended = m.get("recommended_next_phase", "")
    route_review = m.get("route_review", {})

    # If json_parse_ok is false everywhere and no probe found JSON,
    # next phase must not be raw write
    probe_results = m.get("probe_results", [])
    any_json_ok = any(r.get("json_parse_ok") for r in probe_results)

    if not any_json_ok and route_review.get("route_review_status") != "pass":
        check(
            "RAW-JSON" not in recommended or "CONTROLLED-RAW-JSON-DEV-WRITE" not in recommended,
            f"recommended_next_phase cannot be raw write when json_parse_ok=false: {recommended}",
        )


def check_rate_limits(m: dict[str, Any]) -> None:
    budget = m.get("request_budget", {})
    check(
        budget.get("max_route_candidates", 0) <= 3,
        "max_route_candidates must be <= 3",
    )
    check(
        budget.get("max_live_probe_requests", 0) <= 3,
        "max_live_probe_requests must be <= 3",
    )
    rate = m.get("rate_limit", {})
    check(rate.get("concurrency") == 1, "concurrency must be 1")
    check(rate.get("sleep_seconds", 0) >= 5, "sleep_seconds must be >= 5")
    check(rate.get("max_attempts_per_route") == 1, "max_attempts_per_route must be 1")


def check_reports_mention_key_terms() -> None:
    """Ensure reports contain expected key terms."""
    try:
        report_text = REPORT_PATH.read_text(encoding="utf-8")
        review_text = REVIEW_REPORT_PATH.read_text(encoding="utf-8")
    except Exception as exc:
        err(f"cannot read reports: {exc}")
        return

    for term in ["fixture", "404", "unexpected_html", "source_match_id"]:
        check(term.lower() in report_text.lower(), f"report missing key term: {term}")

    for term in ["raw write", "DB write", "no raw body"]:
        check(term.lower() in review_text.lower(), f"review report missing key term: {term}")


def main() -> int:
    check_files_exist()

    m = load_manifest()
    if m is None:
        print(f"FAIL: {len(errors)} error(s)")
        for e in errors:
            print(f"  - {e}")
        return FAIL

    check_previous_phase(m)
    check_route_review(m)
    check_safety(m)
    check_db_safety(m)
    check_embedded_review(m)
    check_recommended_next_phase(m)
    check_rate_limits(m)
    check_reports_mention_key_terms()

    if errors:
        print(f"FAIL: {len(errors)} error(s)")
        for e in errors:
            print(f"  - {e}")
        return FAIL

    print("PASS: all checks passed")
    return PASS


if __name__ == "__main__":
    sys.exit(main())
