#!/usr/bin/env python3
"""Checker for FotMob match ID discovery design no-write phase.

lifecycle: permanent
phase: FOTMOB-RAW-JSON-LONG-RUN-COLLECTOR-MATCH-ID-DISCOVERY-DESIGN-NO-WRITE

Validates design doc / manifest / report / review-report consistency and safety boundaries.
No network access, no DB connection, no live fetch, no write of any kind.
"""

from __future__ import annotations

import json
from pathlib import Path
import sys
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
DESIGN_PATH = ROOT / "docs/data/FOTMOB_MATCH_ID_DISCOVERY_DESIGN_NO_WRITE.md"
MANIFEST_PATH = ROOT / "docs/_manifests/fotmob_match_id_discovery_design_manifest.json"
REPORT_PATH = ROOT / "docs/_reports/FOTMOB_MATCH_ID_DISCOVERY_DESIGN_NO_WRITE.md"
REVIEW_REPORT_PATH = ROOT / "docs/_reports/FOTMOB_MATCH_ID_DISCOVERY_DESIGN_NO_WRITE_REVIEW.md"

FAIL, PASS = 1, 0
errors: list[str] = []

REQUIRED_VALIDATION_STATES = [
    "unknown",
    "fixture_like",
    "candidate",
    "route_candidate",
    "route_validated",
    "json_validated",
    "blocked",
    "invalid",
    "stale",
]

SAFETY_KEYS = [
    "network_fetch_performed",
    "db_write_performed",
    "production_db_write_performed",
    "raw_json_write_performed",
    "fotmob_raw_match_payloads_write_performed",
    "raw_match_data_write_performed",
    "raw_response_body_saved",
    "feature_parse_performed",
    "scheduler_enabled",
    "raw_write_ready_marked",
    "browser_automation_performed",
    "captcha_bypass_performed",
    "proxy_rotation_performed",
]


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
    check(DESIGN_PATH.exists(), f"design doc missing: {DESIGN_PATH}")
    check(MANIFEST_PATH.exists(), f"manifest missing: {MANIFEST_PATH}")
    check(REPORT_PATH.exists(), f"report missing: {REPORT_PATH}")
    check(REVIEW_REPORT_PATH.exists(), f"review report missing: {REVIEW_REPORT_PATH}")


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


def check_discovery_sources(m: dict[str, Any]) -> None:
    sources = m.get("discovery_sources", {})
    check(len(sources) >= 5, f"discovery_sources must have at least 5 entries, got {len(sources)}")
    expected = [
        "team_calendar",
        "competition_fixtures",
        "date_fixtures",
        "known_match_page",
        "historical_raw_payload_backfill",
        "manual_known_good_seed",
    ]
    for key in expected:
        check(key in sources, f"discovery_sources missing expected key: {key}")


def check_validation_states(m: dict[str, Any]) -> None:
    states = m.get("source_identity_validation_states", {})
    for state in REQUIRED_VALIDATION_STATES:
        check(state in states, f"validation state missing: {state}")
    for state_name, state_def in states.items():
        check(
            state_def.get("allows_raw_write") is False,
            f"validation state {state_name} must have allows_raw_write=false",
        )


def check_state_transitions(m: dict[str, Any]) -> None:
    rules = m.get("state_transition_rules", [])
    check(len(rules) >= 5, f"state_transition_rules must have at least 5 entries, got {len(rules)}")
    from_states = {r["from"] for r in rules}
    to_states = {r["to"] for r in rules}
    check("fixture_like" in from_states, "state_transition_rules must include from=fixture_like")
    check("candidate" in to_states, "state_transition_rules must include to=candidate")
    check("route_validated" in to_states, "state_transition_rules must include to=route_validated")
    check("json_validated" in to_states, "state_transition_rules must include to=json_validated")
    check("blocked" in to_states, "state_transition_rules must include to=blocked")
    check("invalid" in to_states, "state_transition_rules must include to=invalid")


def check_safety(m: dict[str, Any]) -> None:
    guards = m.get("no_write_guards", {})
    for key in SAFETY_KEYS:
        check(guards.get(key) is False, f"no_write_guards.{key} must be false")


def check_readiness_gates(m: dict[str, Any]) -> None:
    gates = m.get("readiness_gates", {})
    check(
        gates.get("raw_write_blocked_until_json_validated") is True,
        "raw_write_blocked_until_json_validated must be true",
    )
    check(gates.get("route_validation_required") is True, "route_validation_required must be true")
    check(gates.get("json_validation_required") is True, "json_validation_required must be true")


def check_candidate_schema(m: dict[str, Any]) -> None:
    schema = m.get("candidate_record_schema", {})
    fields = schema.get("fields", [])
    required_fields = [
        "candidate_match_id",
        "candidate_hash_id",
        "validation_state",
        "discovery_source",
        "confidence_score",
        "target_id",
    ]
    for f in required_fields:
        check(f in fields, f"candidate_record_schema.fields missing: {f}")


def check_recommended_next_phase(m: dict[str, Any]) -> None:
    recommended = m.get("recommended_next_phase", "")
    raw_write_phrases = ["RAW-JSON-DEV-WRITE", "RAW-JSON-WRITE", "RAW-MATCH-DATA"]
    for phrase in raw_write_phrases:
        check(
            phrase not in recommended,
            f"recommended_next_phase must not contain {phrase}: {recommended}",
        )
    check(
        "DISCOVERY" in recommended or "DRY-RUN" in recommended,
        f"recommended_next_phase must be discovery/dry-run related: {recommended}",
    )


def main() -> int:
    check_files_exist()

    m = load_manifest()
    if m is None:
        print(f"FAIL: {len(errors)} error(s)")
        for e in errors:
            print(f"  - {e}")
        return FAIL

    check_previous_blocker(m)
    check_discovery_sources(m)
    check_validation_states(m)
    check_state_transitions(m)
    check_safety(m)
    check_readiness_gates(m)
    check_candidate_schema(m)
    check_recommended_next_phase(m)

    if errors:
        print(f"FAIL: {len(errors)} error(s)")
        for e in errors:
            print(f"  - {e}")
        return FAIL

    print("PASS: all checks passed")
    return PASS


if __name__ == "__main__":
    sys.exit(main())
