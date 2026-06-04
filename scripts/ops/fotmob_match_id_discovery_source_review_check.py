#!/usr/bin/env python3
"""Checker for FotMob match ID discovery source review no-write phase.

lifecycle: permanent
phase: FOTMOB-RAW-JSON-LONG-RUN-COLLECTOR-MATCH-ID-DISCOVERY-SOURCE-REVIEW-NO-WRITE

Validates manifest/report/review-report consistency and safety.
No network, no DB, no raw write.
"""

from __future__ import annotations

import json
from pathlib import Path
import sys
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
MANIFEST_PATH = ROOT / "docs/_manifests/fotmob_match_id_discovery_source_review_manifest.json"
REPORT_PATH = ROOT / "docs/_reports/FOTMOB_MATCH_ID_DISCOVERY_SOURCE_REVIEW_NO_WRITE.md"
REVIEW_REPORT_PATH = (
    ROOT / "docs/_reports/FOTMOB_MATCH_ID_DISCOVERY_SOURCE_REVIEW_NO_WRITE_REVIEW.md"
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


def check_counts(m: dict[str, Any]) -> None:
    prev = m.get("previous_stage", {})
    check(prev.get("input_target_count") == 14, "input_target_count must be 14")
    check(prev.get("discovery_candidate_count") == 76, "discovery_candidate_count must be 76")
    check(prev.get("route_validated") == 0, "route_validated must be 0")
    check(prev.get("json_validated") == 0, "json_validated must be 0")
    check(prev.get("raw_write_eligible_count") == 0, "raw_write_eligible_count must be 0")


def check_sources(m: dict[str, Any]) -> None:
    smry = m.get("source_review_summary", {})
    check(smry.get("total_sources") == 6, "total_sources must be 6")
    check(smry.get("reviewed_sources") == 6, "reviewed_sources must be 6")
    check(
        smry.get("selected_bootstrap_source") is not None, "selected_bootstrap_source must be set"
    )
    check(smry.get("selected_primary_source") is not None, "selected_primary_source must be set")
    check(
        smry.get("selected_secondary_source") is not None, "selected_secondary_source must be set"
    )
    check(smry.get("selected_fallback_source") is not None, "selected_fallback_source must be set")
    scores = m.get("source_scores", [])
    check(len(scores) == 6, f"source_scores must have 6 entries, got {len(scores)}")


def check_samples(m: dict[str, Any]) -> None:
    samples = m.get("recommended_next_stage_samples", [])
    check(len(samples) <= 3, f"samples must be <= 3, got {len(samples)}")


def check_safety(m: dict[str, Any]) -> None:
    safety = m.get("safety", {})
    check(safety.get("network_fetch_performed") is False, "network must be false")
    check(safety.get("db_read_performed") is False, "db_read must be false")
    check(safety.get("db_write_performed") is False, "db_write must be false")
    check(safety.get("raw_json_write_performed") is False, "raw_json must be false")
    check(safety.get("scheduler_enabled") is False, "scheduler must be false")
    check(safety.get("feature_parse_performed") is False, "feature_parse must be false")
    check(safety.get("raw_write_ready_marked") is False, "raw_write_ready must be false")


def check_readiness(m: dict[str, Any]) -> None:
    gates = m.get("raw_write_readiness", {})
    check(gates.get("raw_write_eligible_count") == 0, "raw_write_eligible_count must be 0")
    check(gates.get("route_validated_count") == 0, "route_validated_count must be 0")
    check(gates.get("json_validated_count") == 0, "json_validated_count must be 0")
    check(
        gates.get("raw_write_blocked_until_json_validated") is True,
        "raw_write_blocked must be true",
    )


def check_next_phase(m: dict[str, Any]) -> None:
    rec = m.get("recommended_next_phase", "")
    forbidden = ["RAW-JSON-DEV-WRITE", "RAW-JSON-WRITE", "RAW-MATCH-DATA"]
    for f in forbidden:
        check(f not in rec, f"next phase must not contain {f}: {rec}")


def check_embedded_review(m: dict[str, Any]) -> None:
    emb = m.get("embedded_review", {})
    check(emb.get("source_review_status") == "pass", "embedded review status must be pass")


def main() -> int:
    check_files()
    m = load_manifest()
    if m is None:
        print(f"FAIL: {len(errors)} error(s)")
        for e in errors:
            print(f"  - {e}")
        return FAIL

    check_counts(m)
    check_sources(m)
    check_samples(m)
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
