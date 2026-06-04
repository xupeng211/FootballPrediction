"""Tests for FotMob match ID discovery design no-write phase.

lifecycle: permanent
phase: FOTMOB-RAW-JSON-LONG-RUN-COLLECTOR-MATCH-ID-DISCOVERY-DESIGN-NO-WRITE

Validates design output consistency and safety boundaries.
No network, no DB, no live fetch.
"""

from __future__ import annotations

import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts/ops"))

MANIFEST_PATH = ROOT / "docs/_manifests/fotmob_match_id_discovery_design_manifest.json"


# ---------------------------------------------------------------------------
# file existence
# ---------------------------------------------------------------------------


def test_design_doc_exists():
    path = ROOT / "docs/data/FOTMOB_MATCH_ID_DISCOVERY_DESIGN_NO_WRITE.md"
    assert path.exists(), f"design doc missing: {path}"


def test_manifest_exists():
    assert MANIFEST_PATH.exists(), f"manifest missing: {MANIFEST_PATH}"


def test_report_exists():
    path = ROOT / "docs/_reports/FOTMOB_MATCH_ID_DISCOVERY_DESIGN_NO_WRITE.md"
    assert path.exists(), f"report missing: {path}"


def test_review_report_exists():
    path = ROOT / "docs/_reports/FOTMOB_MATCH_ID_DISCOVERY_DESIGN_NO_WRITE_REVIEW.md"
    assert path.exists(), f"review report missing: {path}"


def test_checker_exists():
    path = ROOT / "scripts/ops/fotmob_match_id_discovery_design_check.py"
    assert path.exists(), f"checker missing: {path}"


# ---------------------------------------------------------------------------
# manifest content
# ---------------------------------------------------------------------------


def _load_manifest():
    return json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))


def test_previous_blocker_inherited():
    m = _load_manifest()
    prev = m.get("previous_blocker", {})
    assert prev.get("route_review_status") == "blocked"
    assert prev.get("reliable_route_candidate_found") is False
    assert prev.get("source_identity_quality") == "fixture_like"
    assert prev.get("source_match_id_realism") == "all_fixture_like"
    assert prev.get("match_id_discovery_required") is True


def test_discovery_sources_count():
    m = _load_manifest()
    sources = m.get("discovery_sources", {})
    assert len(sources) >= 5, f"expected >= 5 discovery sources, got {len(sources)}"


def test_discovery_sources_keys():
    m = _load_manifest()
    sources = m.get("discovery_sources", {})
    expected = [
        "team_calendar",
        "competition_fixtures",
        "date_fixtures",
        "known_match_page",
        "historical_raw_payload_backfill",
        "manual_known_good_seed",
    ]
    for key in expected:
        assert key in sources, f"discovery source missing: {key}"


def test_validation_states_complete():
    m = _load_manifest()
    states = m.get("source_identity_validation_states", {})
    required = [
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
    for state in required:
        assert state in states, f"validation state missing: {state}"


def test_validation_states_all_block_raw_write():
    m = _load_manifest()
    states = m.get("source_identity_validation_states", {})
    for state_name, state_def in states.items():
        assert state_def.get("allows_raw_write") is False, (
            f"state {state_name} must have allows_raw_write=false"
        )


def test_state_transition_rules_present():
    m = _load_manifest()
    rules = m.get("state_transition_rules", [])
    assert len(rules) >= 5, f"expected >= 5 transition rules, got {len(rules)}"
    from_states = {r["from"] for r in rules}
    to_states = {r["to"] for r in rules}
    assert "fixture_like" in from_states
    assert "candidate" in to_states
    assert "route_validated" in to_states
    assert "json_validated" in to_states
    assert "blocked" in to_states
    assert "invalid" in to_states


def test_raw_write_blocked_until_json_validated():
    m = _load_manifest()
    gates = m.get("readiness_gates", {})
    assert gates.get("raw_write_blocked_until_json_validated") is True


def test_route_validation_required():
    m = _load_manifest()
    gates = m.get("readiness_gates", {})
    assert gates.get("route_validation_required") is True


def test_json_validation_required():
    m = _load_manifest()
    gates = m.get("readiness_gates", {})
    assert gates.get("json_validation_required") is True


# ---------------------------------------------------------------------------
# safety
# ---------------------------------------------------------------------------


def test_no_network_fetch():
    m = _load_manifest()
    assert m["no_write_guards"]["network_fetch_performed"] is False


def test_no_db_write():
    m = _load_manifest()
    assert m["no_write_guards"]["db_write_performed"] is False
    assert m["no_write_guards"]["production_db_write_performed"] is False


def test_no_raw_json_write():
    m = _load_manifest()
    assert m["no_write_guards"]["raw_json_write_performed"] is False
    assert m["no_write_guards"]["fotmob_raw_match_payloads_write_performed"] is False
    assert m["no_write_guards"]["raw_match_data_write_performed"] is False


def test_no_raw_response_body_saved():
    m = _load_manifest()
    assert m["no_write_guards"]["raw_response_body_saved"] is False


def test_no_scheduler():
    m = _load_manifest()
    assert m["no_write_guards"]["scheduler_enabled"] is False


def test_no_feature_parse():
    m = _load_manifest()
    assert m["no_write_guards"]["feature_parse_performed"] is False


def test_no_raw_write_ready():
    m = _load_manifest()
    assert m["no_write_guards"]["raw_write_ready_marked"] is False


def test_no_browser_automation():
    m = _load_manifest()
    assert m["no_write_guards"]["browser_automation_performed"] is False


def test_no_captcha_bypass():
    m = _load_manifest()
    assert m["no_write_guards"]["captcha_bypass_performed"] is False


def test_no_proxy_rotation():
    m = _load_manifest()
    assert m["no_write_guards"]["proxy_rotation_performed"] is False


# ---------------------------------------------------------------------------
# next phase
# ---------------------------------------------------------------------------


def test_recommended_next_phase_not_raw_write():
    m = _load_manifest()
    recommended = m.get("recommended_next_phase", "")
    raw_phrases = ["RAW-JSON-DEV-WRITE", "RAW-JSON-WRITE", "RAW-MATCH-DATA"]
    for phrase in raw_phrases:
        assert phrase not in recommended, f"next phase must not be {phrase}: {recommended}"


def test_recommended_next_phase_is_dry_run():
    m = _load_manifest()
    recommended = m.get("recommended_next_phase", "")
    assert "DRY-RUN" in recommended or "DISCOVERY" in recommended, (
        f"next phase must be discovery/dry-run: {recommended}"
    )


# ---------------------------------------------------------------------------
# candidate schema
# ---------------------------------------------------------------------------


def test_candidate_schema_has_required_fields():
    m = _load_manifest()
    fields = m.get("candidate_record_schema", {}).get("fields", [])
    required = [
        "candidate_match_id",
        "candidate_hash_id",
        "validation_state",
        "discovery_source",
        "confidence_score",
        "target_id",
    ]
    for f in required:
        assert f in fields, f"candidate schema missing field: {f}"


# ---------------------------------------------------------------------------
# checker integration
# ---------------------------------------------------------------------------


def test_checker_passes_on_valid_manifest():
    from fotmob_match_id_discovery_design_check import (
        check_candidate_schema,
        check_discovery_sources,
        check_previous_blocker,
        check_readiness_gates,
        check_safety,
        check_state_transitions,
        check_validation_states,
        load_manifest,
    )

    m = load_manifest()
    assert m is not None

    # All checks should run without triggering errors
    check_previous_blocker(m)
    check_discovery_sources(m)
    check_validation_states(m)
    check_state_transitions(m)
    check_safety(m)
    check_readiness_gates(m)
    check_candidate_schema(m)
