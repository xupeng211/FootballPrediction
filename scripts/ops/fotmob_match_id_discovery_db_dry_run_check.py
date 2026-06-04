#!/usr/bin/env python3
"""Checker for FotMob match ID discovery DB dry-run no-write phase.

lifecycle: permanent
phase: FOTMOB-RAW-JSON-LONG-RUN-COLLECTOR-MATCH-ID-DISCOVERY-DB-DRY-RUN-NO-WRITE

Validates manifest/report/review-report consistency and safety.
No network, no DB, no live fetch.
"""

from __future__ import annotations

import json
from pathlib import Path
import sys
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
MANIFEST_PATH = ROOT / "docs/_manifests/fotmob_match_id_discovery_db_dry_run_manifest.json"
REPORT_PATH = ROOT / "docs/_reports/FOTMOB_MATCH_ID_DISCOVERY_DB_DRY_RUN_NO_WRITE.md"
REVIEW_REPORT_PATH = ROOT / "docs/_reports/FOTMOB_MATCH_ID_DISCOVERY_DB_DRY_RUN_NO_WRITE_REVIEW.md"

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
    c = m.get("counts", {})
    check(
        c.get("input_target_count") == 14,
        f"input_target_count must be 14, got {c.get('input_target_count')}",
    )
    candidate_count = c.get("discovery_candidate_count", 0)
    check(candidate_count >= 14, f"discovery_candidate_count must be >= 14, got {candidate_count}")
    check(
        c.get("raw_write_eligible_count") == 0,
        f"raw_write_eligible_count must be 0, got {c.get('raw_write_eligible_count')}",
    )


def check_previous_blocker(m: dict[str, Any]) -> None:
    prev = m.get("previous_blocker", {})
    check(
        prev.get("route_review_status") == "blocked", "previous route_review_status must be blocked"
    )
    check(
        prev.get("reliable_route_candidate_found") is False,
        "previous reliable_route_candidate_found must be false",
    )
    check(
        prev.get("source_identity_quality") == "fixture_like",
        "previous source_identity_quality must be fixture_like",
    )
    check(
        prev.get("source_match_id_realism") == "all_fixture_like",
        "previous source_match_id_realism must be all_fixture_like",
    )
    check(
        prev.get("match_id_discovery_required") is True,
        "previous match_id_discovery_required must be true",
    )


def check_sources(m: dict[str, Any]) -> None:
    by_source = m.get("candidates_by_source", {})
    for s in ["team_calendar", "competition_fixtures", "date_fixtures"]:
        check(by_source.get(s, 0) > 0, f"candidates_by_source must include {s} with count > 0")


def check_candidates(m: dict[str, Any]) -> None:
    records = m.get("candidate_records", [])
    for c in records:
        state = c.get("source_identity_validation_state", "")
        check(
            state != "route_validated",
            f"candidate {c.get('candidate_id')} must not be route_validated",
        )
        check(
            state != "json_validated",
            f"candidate {c.get('candidate_id')} must not be json_validated",
        )
        check(
            c.get("raw_write_eligible") is False,
            f"candidate {c.get('candidate_id')} raw_write_eligible must be false",
        )
        check(
            c.get("candidate_match_id") is None,
            f"candidate {c.get('candidate_id')} candidate_match_id must be null",
        )
        check(
            c.get("candidate_hash_id") is None,
            f"candidate {c.get('candidate_id')} candidate_hash_id must be null",
        )


def check_safety(m: dict[str, Any]) -> None:
    safety = m.get("safety", {})
    check(safety.get("network_fetch_performed") is False, "network_fetch_performed must be false")
    check(safety.get("db_read_performed") is True, "db_read_performed must be true")
    check(safety.get("db_write_performed") is False, "db_write_performed must be false")
    check(safety.get("raw_json_write_performed") is False, "raw_json_write_performed must be false")
    check(safety.get("raw_response_body_saved") is False, "raw_response_body_saved must be false")
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


def check_readiness(m: dict[str, Any]) -> None:
    gates = m.get("raw_write_readiness", {})
    check(gates.get("route_validation_required") is True, "route_validation_required must be true")
    check(gates.get("json_validation_required") is True, "json_validation_required must be true")
    check(
        gates.get("raw_write_blocked_until_json_validated") is True,
        "raw_write_blocked_until_json_validated must be true",
    )
    check(gates.get("raw_write_eligible_count") == 0, "raw_write_eligible_count must be 0")


def check_next_phase(m: dict[str, Any]) -> None:
    rec = m.get("recommended_next_phase", "")
    forbidden = ["RAW-JSON-DEV-WRITE", "RAW-JSON-WRITE", "RAW-MATCH-DATA"]
    for f in forbidden:
        check(f not in rec, f"recommended_next_phase must not contain {f}: {rec}")


def check_embedded_review(m: dict[str, Any]) -> None:
    emb = m.get("embedded_review", {})
    check(
        emb.get("match_id_discovery_db_dry_run_status") == "pass",
        "embedded review status must be pass",
    )


def main() -> int:
    check_files()
    m = load_manifest()
    if m is None:
        print(f"FAIL: {len(errors)} error(s)")
        for e in errors:
            print(f"  - {e}")
        return FAIL

    check_counts(m)
    check_previous_blocker(m)
    check_sources(m)
    check_candidates(m)
    check_safety(m)
    check_readiness(m)
    check_next_phase(m)
    check_embedded_review(m)

    if errors:
        print(f"FAIL: {len(errors)} error(s)")
        for e in errors:
            print(f"  - {e}")
        return FAIL
    print("PASS: all checks passed")
    return PASS


if __name__ == "__main__":
    sys.exit(main())
