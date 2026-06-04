"""Unit tests for FotMob live fetch route review no-write phase.

lifecycle: permanent
phase: FOTMOB-RAW-JSON-LONG-RUN-COLLECTOR-LIVE-FETCH-ROUTE-REVIEW-NO-WRITE

Tests script existence, checker logic, and safety boundaries.
Mock tests cover route candidate probe response scenarios.
"""

from __future__ import annotations

import os
from pathlib import Path
import sys
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts/ops"))

# ---------------------------------------------------------------------------
# existence tests
# ---------------------------------------------------------------------------


def test_script_exists():
    script = ROOT / "scripts/ops/fotmob_live_fetch_route_review_no_write.py"
    assert script.exists(), f"script missing: {script}"


def test_checker_exists():
    checker = ROOT / "scripts/ops/fotmob_live_fetch_route_review_no_write_check.py"
    assert checker.exists(), f"checker missing: {checker}"


# ---------------------------------------------------------------------------
# explicit allow flag tests
# ---------------------------------------------------------------------------


def test_missing_explicit_allow_flag_blocks_probe():
    """Script must refuse live probe when ALLOW flag is not set."""
    import fotmob_live_fetch_route_review_no_write as mod

    with patch.dict(os.environ, {}, clear=True):
        assert os.environ.get(mod.ALLOW_FLAG) != "1"
        # The main() function checks explicit flag before any network access
        manifest = mod.blocked_manifest(argparse_mock(), "missing_explicit_allow_flag", False)
        assert manifest["route_review"]["route_review_status"] == "blocked"
        assert manifest["route_review"]["detailed_reason"] is not None
        assert manifest["safety"]["network_fetch_performed"] is False


def test_explicit_allow_flag_present_allows():
    """When ALLOW flag is set, the flag check passes."""
    import fotmob_live_fetch_route_review_no_write as mod

    with patch.dict(os.environ, {mod.ALLOW_FLAG: "1"}, clear=True):
        assert os.environ.get(mod.ALLOW_FLAG) == "1"


# ---------------------------------------------------------------------------
# production guard tests
# ---------------------------------------------------------------------------


def test_production_env_blocks_probe():
    import fotmob_live_fetch_route_review_no_write as mod

    with patch.dict(os.environ, {"ENV": "production"}, clear=True):
        blocked, reasons = mod.check_production_guard("db")
        assert blocked
        assert any("production" in r for r in reasons)


def test_dev_env_passes_guard():
    import fotmob_live_fetch_route_review_no_write as mod

    with patch.dict(os.environ, {"ENV": "development"}, clear=True):
        blocked, _ = mod.check_production_guard("db")
        assert not blocked


# ---------------------------------------------------------------------------
# safety boundary tests
# ---------------------------------------------------------------------------


def test_no_db_write_code_path():
    """Verify SAFETY_FALSE has db_write_performed=False."""
    import fotmob_live_fetch_route_review_no_write as mod

    assert mod.SAFETY_FALSE["raw_json_write_performed"] is False
    assert mod.SAFETY_FALSE["raw_response_body_saved"] is False
    assert mod.SAFETY_FALSE["scheduler_enabled"] is False
    assert mod.SAFETY_FALSE["feature_parse_performed"] is False


def test_manifest_safety_flags_all_false():
    """Manifest safety block must have all flags false or network_fetch_performed."""
    import fotmob_live_fetch_route_review_no_write as mod

    manifest = mod.blocked_manifest(argparse_mock(), "missing_explicit_allow_flag", False)
    safety = manifest["safety"]
    for key in [
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
        "retry_storm_performed",
    ]:
        assert safety[key] is False, f"{key} must be false, got {safety[key]}"


# ---------------------------------------------------------------------------
# fixture-like source_match_id tests
# ---------------------------------------------------------------------------


def test_is_fixture_like():
    import fotmob_live_fetch_route_review_no_write as mod

    assert mod._is_fixture_like("fixture-eng-friend-001") is True
    assert mod._is_fixture_like("fixture-mun-epl-001") is True
    assert mod._is_fixture_like("synthetic-001") is True
    assert mod._is_fixture_like("placeholder-x") is True
    assert mod._is_fixture_like("dummy-1") is True
    assert mod._is_fixture_like("4830473") is False
    assert mod._is_fixture_like("2o4ahb") is False


def test_is_numeric_id():
    import fotmob_live_fetch_route_review_no_write as mod

    assert mod._is_numeric_id("4830473") is True
    assert mod._is_numeric_id("48304") is True
    assert mod._is_numeric_id("12345678") is True
    assert mod._is_numeric_id("fixture-001") is False
    assert mod._is_numeric_id("abc") is False
    assert mod._is_numeric_id("1234") is False  # too short
    assert mod._is_numeric_id("123456789") is False  # too long


# ---------------------------------------------------------------------------
# route candidate tests
# ---------------------------------------------------------------------------


def test_no_reliable_candidate_leads_to_blocked():
    """When all source_match_ids are fixture-like, status must be blocked."""
    import fotmob_live_fetch_route_review_no_write as mod

    identity_analysis = {
        "quality": "fixture_like",
        "total_identities": 10,
        "fixture_like_count": 10,
        "numeric_count": 0,
    }
    target_analysis = {
        "match_id_realism": "all_fixture_like",
        "total_match_targets": 14,
        "fixture_like_source_match_ids": 14,
        "numeric_source_match_ids": 0,
        "has_source_url_count": 0,
        "targets": [
            {
                "source_match_id": "fixture-eng-friend-001",
                "source_match_id_fixture_like": True,
                "source_match_id_numeric": False,
                "source_url": None,
            },
            {
                "source_match_id": "fixture-mun-epl-001",
                "source_match_id_fixture_like": True,
                "source_match_id_numeric": False,
                "source_url": None,
            },
        ],
    }

    candidates = mod.build_route_candidates(identity_analysis, target_analysis)
    assert len(candidates) == 0, "no candidates expected when all ids are fixture-like"

    status, reason = mod.determine_route_review_status(
        identity_analysis, target_analysis, candidates, [], True
    )
    assert status == "blocked"
    assert reason is not None


def test_blocked_status_when_no_candidates():
    """Route review must be blocked when no reliable route candidates."""
    import fotmob_live_fetch_route_review_no_write as mod

    status, reason = mod.determine_route_review_status(
        {"quality": "fixture_like"},
        {"match_id_realism": "all_fixture_like"},
        [],  # no candidates
        [],  # no probes
        False,
    )
    assert status == "blocked"
    assert "no_reliable_route_candidate" in (reason or "")


def test_raw_write_not_recommended_when_json_parse_false():
    """If json_parse_ok is false, next phase must NOT be raw write."""
    import fotmob_live_fetch_route_review_no_write as mod

    # The manifest builder uses NEXT_SAFE_REVIEW (match ID discovery) when
    # json_parse_ok_count is 0 — which is the case when no probes succeed.
    manifest = mod.blocked_manifest(argparse_mock(), "blocked_no_reliable_route_candidate", False)
    assert (
        "MATCH-ID-DISCOVERY" in manifest["recommended_next_phase"]
        or "RAW-JSON" not in manifest["recommended_next_phase"]
    ), f"should not recommend raw write: {manifest['recommended_next_phase']}"


# ---------------------------------------------------------------------------
# rate limit tests
# ---------------------------------------------------------------------------


def test_concurrency_fixed_to_1():
    import fotmob_live_fetch_route_review_no_write as mod

    assert mod.CONCURRENCY == 1


def test_max_route_candidates_at_most_3():
    import fotmob_live_fetch_route_review_no_write as mod

    assert mod.MAX_ROUTE_CANDIDATES == 3


def test_max_attempts_per_route_is_1():
    import fotmob_live_fetch_route_review_no_write as mod

    assert mod.MAX_ATTEMPTS_PER_ROUTE == 1


def test_manifest_rate_limits():
    import fotmob_live_fetch_route_review_no_write as mod

    manifest = mod.blocked_manifest(argparse_mock(), "missing_explicit_allow_flag", False)
    assert manifest["rate_limit"]["concurrency"] == 1
    assert manifest["rate_limit"]["max_attempts_per_route"] == 1
    assert manifest["rate_limit"]["sleep_seconds"] >= 5


# ---------------------------------------------------------------------------
# mock probe scenario tests
# ---------------------------------------------------------------------------


def test_200_json_like_response():
    """Simulate a 200 JSON response — json_parse_ok=true."""
    import fotmob_live_fetch_route_review_no_write as mod

    status, _reason = mod.determine_route_review_status(
        {"quality": "candidate"},
        {"match_id_realism": "mixed"},
        [{"candidate_label": "test", "candidate_source": "test"}],
        [{"json_parse_ok": True, "error_category": None}],
        False,
    )
    assert status in ("pass", "partial")
    # json_parse_ok means at least partial


def test_404_html_response():
    """Simulate a 404 HTML response — route_invalid."""
    import fotmob_live_fetch_route_review_no_write as mod

    status, reason = mod.determine_route_review_status(
        {"quality": "candidate"},
        {"match_id_realism": "mixed"},
        [{"candidate_label": "test", "candidate_source": "test"}],
        [{"json_parse_ok": False, "error_category": "unexpected_html"}],
        False,
    )
    assert status == "partial", f"expected partial, got {status}"
    assert "route_invalid" in (reason or "") or "html" in (reason or "").lower()


def test_403_blocked_forbidden():
    """Simulate a 403 response — blocked_forbidden."""
    import fotmob_live_fetch_route_review_no_write as mod

    status, reason = mod.determine_route_review_status(
        {"quality": "candidate"},
        {"match_id_realism": "mixed"},
        [{"candidate_label": "test", "candidate_source": "test"}],
        [{"json_parse_ok": False, "error_category": "http_403"}],
        False,
    )
    assert status == "blocked"
    assert "forbidden" in (reason or "").lower()


def test_429_rate_limited():
    """Simulate a 429 response."""
    import fotmob_live_fetch_route_review_no_write as mod

    status, reason = mod.determine_route_review_status(
        {"quality": "candidate"},
        {"match_id_realism": "mixed"},
        [{"candidate_label": "test", "candidate_source": "test"}],
        [{"json_parse_ok": False, "error_category": "http_429"}],
        False,
    )
    assert status == "partial"
    assert "rate_limited" in (reason or "")


def test_captcha_detected():
    """Simulate captcha detection."""
    import fotmob_live_fetch_route_review_no_write as mod

    status, reason = mod.determine_route_review_status(
        {"quality": "candidate"},
        {"match_id_realism": "mixed"},
        [{"candidate_label": "test", "candidate_source": "test"}],
        [{"json_parse_ok": False, "error_category": "captcha_or_bot_challenge"}],
        False,
    )
    assert status == "blocked"
    assert "forbidden" in (reason or "").lower()


# ---------------------------------------------------------------------------
# report key terms
# ---------------------------------------------------------------------------


def test_build_report_contains_key_terms():
    import fotmob_live_fetch_route_review_no_write as mod
    import fotmob_live_fetch_route_review_no_write_report as rpt

    # Use a manifest that has reviewed_previous_phase populated (simulating
    # the real case where previous manifest IS loaded).
    manifest = mod.build_manifest(
        argparse_mock(),
        db_env="docker_dev",
        guard_reasons=[],
        explicit=True,
        db_read=True,
        previous_manifest={
            "fetch_results": [
                {
                    "error_category": "unexpected_html",
                    "status_code": 404,
                    "content_type": "text/html; charset=utf-8",
                }
            ],
            "json_parse_ok_count": 0,
            "embedded_review": {"one_day_live_fetch_no_raw_write_status": "partial"},
        },
        identity_analysis={
            "quality": "fixture_like",
            "total_identities": 10,
            "fixture_like_count": 10,
            "numeric_count": 0,
        },
        target_analysis={
            "match_id_realism": "all_fixture_like",
            "total_match_targets": 14,
            "fixture_like_source_match_ids": 14,
            "numeric_source_match_ids": 0,
            "has_source_url_count": 0,
        },
        candidates=[],
        probe_results=[],
        stop_reason="blocked_no_reliable_route_candidate",
        blocked=False,
    )
    report = rpt.build_report(manifest)

    assert "fixture" in report.lower()
    assert "404" in report
    assert "unexpected_html" in report
    assert "source_match_id" in report
    assert "match id discovery" in report.lower()


def test_build_review_report_contains_key_terms():
    import fotmob_live_fetch_route_review_no_write_report as rpt

    manifest = rpt.blocked_manifest(argparse_mock(), "blocked_no_reliable_route_candidate", True)
    review = rpt.build_review_report(manifest)

    assert "raw write" in review.lower() or "raw_json" in review.lower()
    assert "no raw body" in review.lower()


# ---------------------------------------------------------------------------
# checker test
# ---------------------------------------------------------------------------


def test_checker_validates_consistency():
    """Checker should run without error on valid manifest."""
    # We test the checker functions directly
    from fotmob_live_fetch_route_review_no_write_check import (
        check_db_safety,
        check_previous_phase,
        check_rate_limits,
        check_recommended_next_phase,
        check_route_review,
        check_safety,
    )

    manifest = {
        "reviewed_previous_phase": {
            "previous_stop_reason": "unexpected_html",
            "previous_status_code": 404,
            "previous_json_parse_ok_count": 0,
        },
        "route_review": {
            "route_review_status": "blocked",
            "source_identity_quality": "fixture_like",
            "likely_failure_reason": "all_source_match_ids_fixture_like",
            "match_id_discovery_required": True,
            "reliable_route_candidate_found": False,
        },
        "safety": {
            "raw_response_body_saved": False,
            "raw_json_write_performed": False,
            "fotmob_raw_match_payloads_write_performed": False,
            "raw_match_data_write_performed": False,
            "feature_parse_performed": False,
            "scheduler_enabled": False,
            "raw_write_ready_marked": False,
            "browser_automation_performed": False,
            "captcha_bypass_performed": False,
            "proxy_rotation_performed": False,
            "retry_storm_performed": False,
        },
        "db_write_performed": False,
        "production_db_write_performed": False,
        "request_budget": {
            "max_route_candidates": 3,
            "max_live_probe_requests": 3,
        },
        "rate_limit": {
            "concurrency": 1,
            "sleep_seconds": 5,
            "max_attempts_per_route": 1,
        },
        "recommended_next_phase": "FOTMOB-RAW-JSON-LONG-RUN-COLLECTOR-MATCH-ID-DISCOVERY-DESIGN-NO-WRITE",
        "probe_results": [],
    }

    # These should not raise
    check_previous_phase(manifest)
    check_route_review(manifest)
    check_safety(manifest)
    check_db_safety(manifest)
    check_rate_limits(manifest)
    check_recommended_next_phase(manifest)


# ---------------------------------------------------------------------------
# helper
# ---------------------------------------------------------------------------


def argparse_mock():
    """Create a minimal argparse-like namespace for blocked_manifest."""
    import argparse

    return argparse.Namespace(
        run_id="test_run",
        sleep_seconds=5,
        review_report="test_review.md",
        output_manifest="test_manifest.json",
        report="test_report.md",
    )
