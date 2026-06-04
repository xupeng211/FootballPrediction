"""Tests for FotMob match ID discovery source review no-write phase.

lifecycle: permanent
phase: FOTMOB-RAW-JSON-LONG-RUN-COLLECTOR-MATCH-ID-DISCOVERY-SOURCE-REVIEW-NO-WRITE

Validates source review output consistency and safety.
No network, no DB, no raw write.
"""

from __future__ import annotations

import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts/ops"))

MANIFEST_PATH = ROOT / "docs/_manifests/fotmob_match_id_discovery_source_review_manifest.json"


def _load():
    return json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))


# ---------------------------------------------------------------------------
# existence
# ---------------------------------------------------------------------------


def test_script_exists():
    assert (ROOT / "scripts/ops/fotmob_match_id_discovery_source_review.py").exists()


def test_checker_exists():
    assert (ROOT / "scripts/ops/fotmob_match_id_discovery_source_review_check.py").exists()


def test_manifest_exists():
    assert MANIFEST_PATH.exists()


def test_report_exists():
    assert (ROOT / "docs/_reports/FOTMOB_MATCH_ID_DISCOVERY_SOURCE_REVIEW_NO_WRITE.md").exists()


def test_review_report_exists():
    assert (
        ROOT / "docs/_reports/FOTMOB_MATCH_ID_DISCOVERY_SOURCE_REVIEW_NO_WRITE_REVIEW.md"
    ).exists()


# ---------------------------------------------------------------------------
# counts
# ---------------------------------------------------------------------------


def test_previous_stage_counts():
    m = _load()
    prev = m["previous_stage"]
    assert prev["input_target_count"] == 14
    assert prev["discovery_candidate_count"] == 76
    assert prev["route_validated"] == 0
    assert prev["json_validated"] == 0
    assert prev["raw_write_eligible_count"] == 0


# ---------------------------------------------------------------------------
# sources
# ---------------------------------------------------------------------------


def test_six_sources_reviewed():
    m = _load()
    smry = m["source_review_summary"]
    assert smry["total_sources"] == 6
    assert smry["reviewed_sources"] == 6


def test_source_scores_count():
    m = _load()
    assert len(m["source_scores"]) == 6


def test_bootstrap_source_selected():
    m = _load()
    assert m["source_review_summary"]["selected_bootstrap_source"] is not None


def test_primary_source_selected():
    m = _load()
    assert m["source_review_summary"]["selected_primary_source"] is not None


def test_secondary_source_selected():
    m = _load()
    assert m["source_review_summary"]["selected_secondary_source"] is not None


def test_fallback_source_selected():
    m = _load()
    assert m["source_review_summary"]["selected_fallback_source"] is not None


def test_deferred_sources_present():
    m = _load()
    deferred = m["source_review_summary"]["deferred_sources"]
    assert len(deferred) > 0


# ---------------------------------------------------------------------------
# samples
# ---------------------------------------------------------------------------


def test_samples_max_3():
    m = _load()
    assert len(m["recommended_next_stage_samples"]) <= 3


# ---------------------------------------------------------------------------
# validation states
# ---------------------------------------------------------------------------


def test_route_validated_remains_0():
    m = _load()
    assert m["previous_stage"]["route_validated"] == 0
    assert m["raw_write_readiness"]["route_validated_count"] == 0


def test_json_validated_remains_0():
    m = _load()
    assert m["previous_stage"]["json_validated"] == 0
    assert m["raw_write_readiness"]["json_validated_count"] == 0


def test_raw_write_eligible_count_0():
    m = _load()
    assert m["raw_write_readiness"]["raw_write_eligible_count"] == 0


# ---------------------------------------------------------------------------
# safety
# ---------------------------------------------------------------------------


def test_no_network():
    assert _load()["safety"]["network_fetch_performed"] is False


def test_no_db_read():
    assert _load()["safety"]["db_read_performed"] is False


def test_no_db_write():
    s = _load()["safety"]
    assert s["db_write_performed"] is False


def test_no_raw_json_write():
    assert _load()["safety"]["raw_json_write_performed"] is False


def test_no_scheduler():
    assert _load()["safety"]["scheduler_enabled"] is False


def test_no_feature_parse():
    assert _load()["safety"]["feature_parse_performed"] is False


def test_no_raw_write_ready():
    assert _load()["safety"]["raw_write_ready_marked"] is False


# ---------------------------------------------------------------------------
# next phase
# ---------------------------------------------------------------------------


def test_next_phase_not_raw_write():
    rec = _load()["recommended_next_phase"]
    for forbidden in ["RAW-JSON-DEV-WRITE", "RAW-JSON-WRITE", "RAW-MATCH-DATA"]:
        assert forbidden not in rec, f"must not be {forbidden}: {rec}"


# ---------------------------------------------------------------------------
# checker integration
# ---------------------------------------------------------------------------


def test_checker_passes():
    from fotmob_match_id_discovery_source_review_check import (
        check_counts,
        check_next_phase,
        check_readiness,
        check_safety,
        check_samples,
        check_sources,
        load_manifest,
    )

    m = load_manifest()
    assert m is not None
    check_counts(m)
    check_sources(m)
    check_samples(m)
    check_safety(m)
    check_readiness(m)
    check_next_phase(m)
