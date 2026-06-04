#!/usr/bin/env python3
"""Checker for FotMob known match page user seeds parse no-write phase.

lifecycle: permanent
phase: FOTMOB-RAW-JSON-LONG-RUN-COLLECTOR-KNOWN-MATCH-PAGE-PARSE-NO-WRITE-WITH-USER-SEEDS

Reads only manifest/report/review-report/user seed. No network, no DB, no raw write.
"""

from __future__ import annotations

import json
from pathlib import Path
import sys
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
MANIFEST_PATH = (
    ROOT / "docs/_manifests/fotmob_known_match_page_user_seeds_parse_no_write_manifest.json"
)
REPORT_PATH = ROOT / "docs/_reports/FOTMOB_KNOWN_MATCH_PAGE_USER_SEEDS_PARSE_NO_WRITE.md"
REVIEW_REPORT_PATH = (
    ROOT / "docs/_reports/FOTMOB_KNOWN_MATCH_PAGE_USER_SEEDS_PARSE_NO_WRITE_REVIEW.md"
)
INPUT_INSTRUCTIONS_PATH = (
    ROOT / "docs/_reports/FOTMOB_KNOWN_MATCH_PAGE_USER_SEED_INPUT_INSTRUCTIONS.md"
)
USER_SEED_PATH = ROOT / "docs/_examples/fotmob_known_match_page_user_seeds.example.json"

SAFE_NEXT_PHASE = "FOTMOB-RAW-JSON-LONG-RUN-COLLECTOR-CONTROLLED-JSON-PROBE-NO-WRITE"
EXPECTED_PHASE = (
    "FOTMOB-RAW-JSON-LONG-RUN-COLLECTOR-KNOWN-MATCH-PAGE-PARSE-NO-WRITE-WITH-USER-SEEDS"
)

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
    check(INPUT_INSTRUCTIONS_PATH.exists(), "user seed input instructions missing")
    check(USER_SEED_PATH.exists(), "user seed file missing")


def check_phase(m: dict[str, Any]) -> None:
    check(m.get("phase") == EXPECTED_PHASE, f"phase must be {EXPECTED_PHASE}")
    check(m.get("mode") == "offline_parse_only", "mode must be offline_parse_only")


def check_seed_counts(m: dict[str, Any]) -> None:
    seed_summary = m.get("seed_input_summary", {})
    check(seed_summary.get("user_seed_count") == 12, "user_seed_count must be 12")
    total = seed_summary.get("total_seed_count", 0)
    check(total >= 12, f"total_seed_count must be >= 12, got {total}")


def check_parse_counts(m: dict[str, Any]) -> None:
    parse_summary = m.get("parse_summary", {})
    parsed = parse_summary.get("parsed_count", 0)
    check(parsed >= 12, f"parsed_count must be >= 12, got {parsed}")
    check(
        parse_summary.get("route_candidate_count", 0) >= 12, "route_candidate_count must be >= 12"
    )


def check_extracted(m: dict[str, Any]) -> None:
    match_ids = m.get("extracted_match_ids", [])
    route_codes = m.get("extracted_route_codes", [])
    check(len(match_ids) >= 12, f"extracted_match_ids count must be >= 12, got {len(match_ids)}")
    check(
        len(route_codes) >= 12, f"extracted_route_codes count must be >= 12, got {len(route_codes)}"
    )


def check_target_match(m: dict[str, Any]) -> None:
    target = m.get("target_match_summary", {})
    check(
        target.get("current_target_match_true_count", 0) >= 1,
        "current_target_match_true_count must be >= 1",
    )
    check(
        target.get("exact_or_reversed_pair_count", 0) >= 1,
        "exact_or_reversed_pair_count must be >= 1",
    )


def check_raw_write_readiness(m: dict[str, Any]) -> None:
    readiness = m.get("raw_write_readiness", {})
    check(readiness.get("route_validated_count") == 0, "route_validated_count must be 0")
    check(readiness.get("json_validated_count") == 0, "json_validated_count must be 0")
    check(readiness.get("raw_write_eligible_count") == 0, "raw_write_eligible_count must be 0")
    check(
        readiness.get("raw_write_blocked_until_json_validated") is True,
        "raw_write_blocked_until_json_validated must be true",
    )


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


def check_embedded_review(m: dict[str, Any]) -> None:
    embedded = m.get("embedded_review", {})
    check(embedded.get("user_seed_parse_status") == "pass", "embedded review status must be pass")


def check_next_phase(m: dict[str, Any]) -> None:
    rec = m.get("recommended_next_phase", "")
    check(rec == SAFE_NEXT_PHASE, f"recommended next phase must be {SAFE_NEXT_PHASE}, got {rec}")
    forbidden = ["RAW-JSON-DEV-WRITE", "RAW-MATCH-DATA", "RAW-WRITE", "L2-RAW-HARVESTING"]
    for word in forbidden:
        check(
            word not in rec.upper().replace("-", ""),
            f"recommended next phase must not contain {word}: {rec}",
        )


def check_parsed_seeds(m: dict[str, Any]) -> None:
    """Verify no seed has forbidden states."""
    for seed in m.get("parsed_seeds", []):
        check(
            seed.get("raw_write_eligible") is False,
            f"seed {seed.get('parsed_seed_id')} raw_write_eligible must be false",
        )
        check(
            seed.get("raw_json_write_performed") is False,
            f"seed {seed.get('parsed_seed_id')} raw_json_write_performed must be false",
        )
        check(
            seed.get("db_write_performed") is False,
            f"seed {seed.get('parsed_seed_id')} db_write_performed must be false",
        )
        check(
            seed.get("network_fetch_performed") is False,
            f"seed {seed.get('parsed_seed_id')} network_fetch_performed must be false",
        )
        check(
            seed.get("validation_state") != "json_validated",
            f"seed {seed.get('parsed_seed_id')} must not be json_validated",
        )


def check_route_codes(m: dict[str, Any]) -> None:
    """Verify all expected route codes are present."""
    expected = {
        "3h9f6s",
        "2viayw",
        "2f8a75",
        "2ygkcb",
        "2ynv4k",
        "2xqo0r",
        "2w9xj5",
        "2wdjjd",
        "2bhzy5",
        "2azd0v",
        "2en1da",
        "n1c6d",
    }
    extracted = set(m.get("extracted_route_codes", []))
    missing = expected - extracted
    check(len(missing) == 0, f"missing expected route codes: {missing}")


def check_match_ids(m: dict[str, Any]) -> None:
    """Verify all expected match IDs are present."""
    expected = {
        "4506597",
        "4667825",
        "4813754",
        "4813722",
        "4813492",
        "4813622",
        "4813421",
        "4813398",
        "4359098",
        "4044692",
        "3495351",
        "5130312",
    }
    extracted = set(m.get("extracted_match_ids", []))
    missing = expected - extracted
    check(len(missing) == 0, f"missing expected match IDs: {missing}")


def main() -> int:
    check_files()
    m = load_manifest()
    if m is None:
        print(f"FAIL: {len(errors)} error(s)")
        for item in errors:
            print(f"  - {item}")
        return FAIL

    check_phase(m)
    check_seed_counts(m)
    check_parse_counts(m)
    check_extracted(m)
    check_target_match(m)
    check_raw_write_readiness(m)
    check_safety(m)
    check_embedded_review(m)
    check_next_phase(m)
    check_parsed_seeds(m)
    check_route_codes(m)
    check_match_ids(m)

    if errors:
        print(f"FAIL: {len(errors)} error(s)")
        for item in errors:
            print(f"  - {item}")
        return FAIL
    print("PASS: all checks passed")
    return PASS


if __name__ == "__main__":
    sys.exit(main())
