"""Tests for FotMob match ID discovery DB dry-run no-write phase.

lifecycle: permanent
phase: FOTMOB-RAW-JSON-LONG-RUN-COLLECTOR-MATCH-ID-DISCOVERY-DB-DRY-RUN-NO-WRITE

Validates DB dry-run output consistency and safety.
No network, no DB write in tests (manifest read only).
"""

from __future__ import annotations

import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts/ops"))

MANIFEST_PATH = ROOT / "docs/_manifests/fotmob_match_id_discovery_db_dry_run_manifest.json"


def _load():
    return json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))


# ---------------------------------------------------------------------------
# existence
# ---------------------------------------------------------------------------


def test_script_exists():
    assert (ROOT / "scripts/ops/fotmob_match_id_discovery_db_dry_run.py").exists()


def test_checker_exists():
    assert (ROOT / "scripts/ops/fotmob_match_id_discovery_db_dry_run_check.py").exists()


def test_manifest_exists():
    assert MANIFEST_PATH.exists()


def test_report_exists():
    assert (ROOT / "docs/_reports/FOTMOB_MATCH_ID_DISCOVERY_DB_DRY_RUN_NO_WRITE.md").exists()


def test_review_report_exists():
    assert (ROOT / "docs/_reports/FOTMOB_MATCH_ID_DISCOVERY_DB_DRY_RUN_NO_WRITE_REVIEW.md").exists()


# ---------------------------------------------------------------------------
# counts
# ---------------------------------------------------------------------------


def test_input_target_count():
    m = _load()
    assert m["counts"]["input_target_count"] == 14


def test_discovery_candidate_count():
    m = _load()
    assert m["counts"]["discovery_candidate_count"] >= 14


def test_raw_write_eligible_count_zero():
    m = _load()
    assert m["counts"]["raw_write_eligible_count"] == 0


# ---------------------------------------------------------------------------
# sources
# ---------------------------------------------------------------------------


def test_source_distribution_has_required():
    m = _load()
    src = m["candidates_by_source"]
    for s in ["team_calendar", "competition_fixtures", "date_fixtures"]:
        assert src.get(s, 0) > 0, f"source {s} must have count > 0"


def test_all_six_sources_present():
    m = _load()
    src = m["candidates_by_source"]
    for s in [
        "team_calendar",
        "competition_fixtures",
        "date_fixtures",
        "known_match_page",
        "historical_backfill",
        "manual_seed",
    ]:
        assert s in src, f"source {s} missing"


# ---------------------------------------------------------------------------
# teams
# ---------------------------------------------------------------------------


def test_teams_in_candidates():
    m = _load()
    teams = m["candidates_by_team"]
    for t in ["Manchester United", "England", "Kashima Antlers", "Leeds United"]:
        assert teams.get(t, 0) > 0, f"team {t} must have count > 0"


# ---------------------------------------------------------------------------
# previous blocker
# ---------------------------------------------------------------------------


def test_previous_blocker():
    m = _load()
    prev = m["previous_blocker"]
    assert prev["route_review_status"] == "blocked"
    assert prev["reliable_route_candidate_found"] is False
    assert prev["source_identity_quality"] == "fixture_like"
    assert prev["source_match_id_realism"] == "all_fixture_like"
    assert prev["match_id_discovery_required"] is True


# ---------------------------------------------------------------------------
# candidate state
# ---------------------------------------------------------------------------


def test_no_route_validated():
    m = _load()
    for c in m["candidate_records"]:
        assert c["source_identity_validation_state"] != "route_validated"


def test_no_json_validated():
    m = _load()
    for c in m["candidate_records"]:
        assert c["source_identity_validation_state"] != "json_validated"


def test_all_raw_write_eligible_false():
    m = _load()
    for c in m["candidate_records"]:
        assert c["raw_write_eligible"] is False


def test_all_candidate_match_id_null():
    m = _load()
    for c in m["candidate_records"]:
        assert c["candidate_match_id"] is None


def test_validation_state_summary():
    m = _load()
    st = m["validation_state_summary"]
    assert st["route_validated"] == 0
    assert st["json_validated"] == 0


# ---------------------------------------------------------------------------
# safety
# ---------------------------------------------------------------------------


def test_no_network():
    m = _load()
    assert m["safety"]["network_fetch_performed"] is False


def test_no_db_write():
    m = _load()
    assert m["safety"]["db_write_performed"] is False
    assert m["safety"]["production_db_write_performed"] is False


def test_no_raw_json_write():
    m = _load()
    assert m["safety"]["raw_json_write_performed"] is False


def test_no_scheduler():
    m = _load()
    assert m["safety"]["scheduler_enabled"] is False


def test_no_feature_parse():
    m = _load()
    assert m["safety"]["feature_parse_performed"] is False


def test_no_raw_write_ready():
    m = _load()
    assert m["safety"]["raw_write_ready_marked"] is False


def test_no_browser():
    m = _load()
    assert m["safety"]["browser_automation_performed"] is False


def test_no_captcha():
    m = _load()
    assert m["safety"]["captcha_bypass_performed"] is False


def test_no_proxy():
    m = _load()
    assert m["safety"]["proxy_rotation_performed"] is False


# ---------------------------------------------------------------------------
# readiness
# ---------------------------------------------------------------------------


def test_readiness_gates():
    m = _load()
    gates = m["raw_write_readiness"]
    assert gates["route_validation_required"] is True
    assert gates["json_validation_required"] is True
    assert gates["raw_write_blocked_until_json_validated"] is True
    assert gates["raw_write_eligible_count"] == 0


# ---------------------------------------------------------------------------
# next phase
# ---------------------------------------------------------------------------


def test_next_phase_not_raw_write():
    m = _load()
    rec = m["recommended_next_phase"]
    for forbidden in ["RAW-JSON-DEV-WRITE", "RAW-JSON-WRITE", "RAW-MATCH-DATA"]:
        assert forbidden not in rec, f"next phase must not be {forbidden}: {rec}"


# ---------------------------------------------------------------------------
# checker
# ---------------------------------------------------------------------------


def test_checker_passes():
    from fotmob_match_id_discovery_db_dry_run_check import (
        check_candidates,
        check_counts,
        check_next_phase,
        check_previous_blocker,
        check_readiness,
        check_safety,
        check_sources,
        load_manifest,
    )

    m = load_manifest()
    assert m is not None
    check_counts(m)
    check_previous_blocker(m)
    check_sources(m)
    check_candidates(m)
    check_safety(m)
    check_readiness(m)
    check_next_phase(m)
