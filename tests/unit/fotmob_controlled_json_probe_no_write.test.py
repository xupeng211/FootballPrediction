"""Tests for FotMob controlled JSON probe no-write phase.

lifecycle: permanent
phase: FOTMOB-RAW-JSON-LONG-RUN-COLLECTOR-CONTROLLED-JSON-PROBE-NO-WRITE

Validates probe plan construction, constraint enforcement, metadata-only safety.
Network tests use mocked responses. No real network, no DB, no raw write.
"""

from __future__ import annotations

import json
from pathlib import Path
import subprocess
import sys
from typing import Any
from unittest import mock

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts/ops"))

SCRIPT = ROOT / "scripts/ops/fotmob_controlled_json_probe_no_write.py"
CHECKER = ROOT / "scripts/ops/fotmob_controlled_json_probe_no_write_check.py"

import fotmob_controlled_json_probe_no_write as probe_mod  # noqa: E402


def _run_script(args: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(SCRIPT), *args],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )


def _make_sample_seeds() -> list[dict[str, Any]]:
    """Minimal seeds for probe selection tests."""
    return [
        {
            "parsed_seed_id": "s01",
            "source_seed_id": "u01",
            "team_hint": "Manchester United",
            "opponent_hint": "Liverpool",
            "route_code": "2ygkcb",
            "fotmob_match_id": "4813722",
            "is_exact_or_reversed_pair": True,
            "target_relevance": "current_target_exact_or_reversed_pair",
            "source_url": "https://www.fotmob.com/zh-Hans/matches/liverpool-vs-manchester-united/2ygkcb#4813722",
            "locale": "zh-Hans",
            "match_slug": "liverpool-vs-manchester-united",
            "fragment_match_id": "4813722",
            "parse_status": "parsed",
            "current_target_match": "true",
            "validation_state": "route_candidate",
            "route_probe_performed": False,
            "network_fetch_performed": False,
            "db_write_performed": False,
            "raw_response_body_saved": False,
            "raw_json_write_performed": False,
            "raw_write_eligible": False,
        },
        {
            "parsed_seed_id": "s02",
            "source_seed_id": "u02",
            "team_hint": "Manchester United",
            "opponent_hint": "Everton",
            "route_code": "2ynv4k",
            "fotmob_match_id": "4813492",
            "is_exact_or_reversed_pair": True,
            "target_relevance": "current_target_exact_or_reversed_pair",
            "source_url": "https://www.fotmob.com/zh-Hans/matches/everton-vs-manchester-united/2ynv4k#4813492",
            "locale": "zh-Hans",
            "match_slug": "everton-vs-manchester-united",
            "fragment_match_id": "4813492",
            "parse_status": "parsed",
            "current_target_match": "true",
            "validation_state": "route_candidate",
            "route_probe_performed": False,
            "network_fetch_performed": False,
            "db_write_performed": False,
            "raw_response_body_saved": False,
            "raw_json_write_performed": False,
            "raw_write_eligible": False,
        },
        {
            "parsed_seed_id": "s03",
            "source_seed_id": "u03",
            "team_hint": "England",
            "opponent_hint": "Poland",
            "route_code": "2en1da",
            "fotmob_match_id": "3495351",
            "is_exact_or_reversed_pair": True,
            "target_relevance": "current_target_exact_or_reversed_pair",
            "source_url": "https://www.fotmob.com/zh-Hans/matches/england-vs-poland/2en1da#3495351",
            "locale": "zh-Hans",
            "match_slug": "england-vs-poland",
            "fragment_match_id": "3495351",
            "parse_status": "parsed",
            "current_target_match": "true",
            "validation_state": "route_candidate",
            "route_probe_performed": False,
            "network_fetch_performed": False,
            "db_write_performed": False,
            "raw_response_body_saved": False,
            "raw_json_write_performed": False,
            "raw_write_eligible": False,
        },
    ]


# --- file existence ---


def test_script_exists():
    assert SCRIPT.exists()


def test_checker_exists():
    assert CHECKER.exists()


# --- probe selection ---


def test_select_exact_reversed_first():
    seeds = _make_sample_seeds()
    selected = probe_mod.select_probe_samples(seeds, 3)
    assert len(selected) <= 3
    assert all(s["is_exact_or_reversed_pair"] for s in selected)


def test_select_max_samples_respected():
    seeds = _make_sample_seeds()
    selected = probe_mod.select_probe_samples(seeds, 2)
    assert len(selected) == 2


def test_select_handles_empty():
    assert probe_mod.select_probe_samples([], 3) == []


# --- probe plan ---


def test_build_probe_plan():
    seeds = _make_sample_seeds()[:2]
    eps = probe_mod.ENDPOINT_CANDIDATES[:2]
    plan = probe_mod.build_probe_plan(seeds, eps, 2)
    assert len(plan) == 4  # 2 seeds x 2 endpoints
    assert all("probe_id" in p for p in plan)
    assert all("url_redacted" in p for p in plan)
    assert all("{match_id}" not in p["url_redacted"] for p in plan)


def test_build_probe_plan_max_endpoints():
    seeds = _make_sample_seeds()[:1]
    eps = probe_mod.ENDPOINT_CANDIDATES
    plan = probe_mod.build_probe_plan(seeds, eps, 1)
    assert len(plan) == 1


# --- constraint validation ---


def test_dry_run_no_network(tmp_path):
    manifest = tmp_path / "manifest.json"
    report = tmp_path / "report.md"
    review = tmp_path / "review.md"
    endpoint = tmp_path / "endpoint.md"

    result = _run_script(
        [
            "--seed-manifest",
            "docs/_manifests/fotmob_known_match_page_user_seeds_parse_no_write_manifest.json",
            "--output-manifest",
            str(manifest),
            "--report",
            str(report),
            "--review-report",
            str(review),
            "--endpoint-decision-report",
            str(endpoint),
            "--run-id",
            "test_dry_v1",
            "--max-samples",
            "3",
            "--max-endpoints-per-sample",
            "3",
        ]
    )
    assert result.returncode == 0, f"Dry-run failed: {result.stderr}"
    assert manifest.exists()

    m = json.loads(manifest.read_text(encoding="utf-8"))
    assert m["mode"] == "dry_run_probe_plan_only"
    assert m["probe_summary"]["network_requests_attempted"] == 0
    assert m["probe_summary"]["allow_network_probe"] is False


def test_max_samples_exceeded_fails(tmp_path):
    manifest = tmp_path / "manifest.json"
    report = tmp_path / "report.md"
    review = tmp_path / "review.md"
    endpoint = tmp_path / "endpoint.md"

    result = _run_script(
        [
            "--seed-manifest",
            "docs/_manifests/fotmob_known_match_page_user_seeds_parse_no_write_manifest.json",
            "--output-manifest",
            str(manifest),
            "--report",
            str(report),
            "--review-report",
            str(review),
            "--endpoint-decision-report",
            str(endpoint),
            "--run-id",
            "test_fail_v1",
            "--max-samples",
            "4",
        ]
    )
    assert result.returncode != 0


def test_max_endpoints_exceeded_fails(tmp_path):
    manifest = tmp_path / "manifest.json"
    report = tmp_path / "report.md"
    review = tmp_path / "review.md"
    endpoint = tmp_path / "endpoint.md"

    result = _run_script(
        [
            "--seed-manifest",
            "docs/_manifests/fotmob_known_match_page_user_seeds_parse_no_write_manifest.json",
            "--output-manifest",
            str(manifest),
            "--report",
            str(report),
            "--review-report",
            str(review),
            "--endpoint-decision-report",
            str(endpoint),
            "--run-id",
            "test_fail_v2",
            "--max-endpoints-per-sample",
            "4",
        ]
    )
    assert result.returncode != 0


def test_max_network_requests_exceeded_fails(tmp_path):
    manifest = tmp_path / "manifest.json"
    report = tmp_path / "report.md"
    review = tmp_path / "review.md"
    endpoint = tmp_path / "endpoint.md"

    result = _run_script(
        [
            "--seed-manifest",
            "docs/_manifests/fotmob_known_match_page_user_seeds_parse_no_write_manifest.json",
            "--output-manifest",
            str(manifest),
            "--report",
            str(report),
            "--review-report",
            str(review),
            "--endpoint-decision-report",
            str(endpoint),
            "--run-id",
            "test_fail_v3",
            "--max-network-requests",
            "10",
        ]
    )
    assert result.returncode != 0


# --- validation state determination ---


def test_validation_state_json_ok():
    assert probe_mod.determine_validation_state({"json_parse_ok": True}) == "json_probe_observed"


def test_validation_state_blocked_403():
    assert (
        probe_mod.determine_validation_state({"stop_reason": "blocked_403"}) == "json_probe_blocked"
    )


def test_validation_state_blocked_429():
    assert (
        probe_mod.determine_validation_state({"stop_reason": "blocked_429_rate_limited"})
        == "json_probe_blocked"
    )


def test_validation_state_invalid_404():
    assert (
        probe_mod.determine_validation_state({"stop_reason": "invalid_404"}) == "json_probe_invalid"
    )


def test_validation_state_html():
    assert (
        probe_mod.determine_validation_state(
            {"status_code": 200, "content_type": "text/html", "json_parse_ok": False}
        )
        == "json_probe_not_json"
    )


# --- dry-run manifest checks ---


def test_dry_run_manifest_inheritance(tmp_path):
    manifest = tmp_path / "manifest.json"
    report = tmp_path / "report.md"
    review = tmp_path / "review.md"
    endpoint = tmp_path / "endpoint.md"

    result = _run_script(
        [
            "--seed-manifest",
            "docs/_manifests/fotmob_known_match_page_user_seeds_parse_no_write_manifest.json",
            "--output-manifest",
            str(manifest),
            "--report",
            str(report),
            "--review-report",
            str(review),
            "--endpoint-decision-report",
            str(endpoint),
            "--run-id",
            "test_inherit_v1",
            "--max-samples",
            "3",
        ]
    )
    assert result.returncode == 0

    m = json.loads(manifest.read_text(encoding="utf-8"))
    ih = m["inherited_seed_status"]
    assert ih["user_seed_count"] == 12
    assert ih["parsed_count"] == 12
    assert ih["route_candidate_count"] == 12
    assert ih["route_validated_count"] == 0
    assert ih["json_validated_count"] == 0
    assert ih["raw_write_eligible_count"] == 0


def test_dry_run_safety_flags(tmp_path):
    manifest = tmp_path / "manifest.json"
    report = tmp_path / "report.md"
    review = tmp_path / "review.md"
    endpoint = tmp_path / "endpoint.md"

    result = _run_script(
        [
            "--seed-manifest",
            "docs/_manifests/fotmob_known_match_page_user_seeds_parse_no_write_manifest.json",
            "--output-manifest",
            str(manifest),
            "--report",
            str(report),
            "--review-report",
            str(review),
            "--endpoint-decision-report",
            str(endpoint),
            "--run-id",
            "test_safety_v1",
            "--max-samples",
            "3",
        ]
    )
    assert result.returncode == 0

    m = json.loads(manifest.read_text(encoding="utf-8"))
    safety = m["safety"]
    assert safety["raw_response_body_saved"] is False
    assert safety["raw_json_write_performed"] is False
    assert safety["db_write_performed"] is False
    assert safety["scheduler_enabled"] is False
    assert safety["feature_parse_performed"] is False
    assert safety["browser_automation_performed"] is False
    assert safety["captcha_bypass_performed"] is False
    assert safety["proxy_rotation_performed"] is False


def test_dry_run_readiness_gate(tmp_path):
    manifest = tmp_path / "manifest.json"
    report = tmp_path / "report.md"
    review = tmp_path / "review.md"
    endpoint = tmp_path / "endpoint.md"

    result = _run_script(
        [
            "--seed-manifest",
            "docs/_manifests/fotmob_known_match_page_user_seeds_parse_no_write_manifest.json",
            "--output-manifest",
            str(manifest),
            "--report",
            str(report),
            "--review-report",
            str(review),
            "--endpoint-decision-report",
            str(endpoint),
            "--run-id",
            "test_gate_v1",
            "--max-samples",
            "3",
        ]
    )
    assert result.returncode == 0

    m = json.loads(manifest.read_text(encoding="utf-8"))
    rw = m["json_probe_readiness"]
    assert rw["json_validated_count"] == 0
    assert rw["raw_write_eligible_count"] == 0
    assert rw["raw_write_blocked_until_json_validated"] is True


def test_dry_run_probe_results_safe(tmp_path):
    manifest = tmp_path / "manifest.json"
    report = tmp_path / "report.md"
    review = tmp_path / "review.md"
    endpoint = tmp_path / "endpoint.md"

    result = _run_script(
        [
            "--seed-manifest",
            "docs/_manifests/fotmob_known_match_page_user_seeds_parse_no_write_manifest.json",
            "--output-manifest",
            str(manifest),
            "--report",
            str(report),
            "--review-report",
            str(review),
            "--endpoint-decision-report",
            str(endpoint),
            "--run-id",
            "test_probe_result_v1",
            "--max-samples",
            "3",
        ]
    )
    assert result.returncode == 0

    m = json.loads(manifest.read_text(encoding="utf-8"))
    for r in m["probe_results"]:
        assert r["raw_write_eligible"] is False
        assert r["raw_json_write_performed"] is False
        assert r["raw_response_body_saved"] is False
        assert r["db_write_performed"] is False
        assert r["validation_state"] not in (
            "json_validated",
            "raw_write_ready",
            "raw_write_eligible",
        )
        assert r["network_performed"] is False  # dry-run


def test_dry_run_recommended_next_phase(tmp_path):
    manifest = tmp_path / "manifest.json"
    report = tmp_path / "report.md"
    review = tmp_path / "review.md"
    endpoint = tmp_path / "endpoint.md"

    result = _run_script(
        [
            "--seed-manifest",
            "docs/_manifests/fotmob_known_match_page_user_seeds_parse_no_write_manifest.json",
            "--output-manifest",
            str(manifest),
            "--report",
            str(report),
            "--review-report",
            str(review),
            "--endpoint-decision-report",
            str(endpoint),
            "--run-id",
            "test_next_v1",
            "--max-samples",
            "3",
        ]
    )
    assert result.returncode == 0

    m = json.loads(manifest.read_text(encoding="utf-8"))
    assert m["recommended_next_phase"] == probe_mod.DRY_RUN_NEXT
    assert "RAW-JSON-DEV-WRITE" not in m["recommended_next_phase"]


# --- endpoint candidates ---


def test_endpoint_candidates_exist():
    assert len(probe_mod.ENDPOINT_CANDIDATES) >= 3
    for ep in probe_mod.ENDPOINT_CANDIDATES:
        assert "{match_id}" in ep["endpoint_template"]


def test_url_redaction():
    seeds = _make_sample_seeds()[:1]
    plan = probe_mod.build_probe_plan(seeds, probe_mod.ENDPOINT_CANDIDATES[:1], 1)
    assert plan[0]["url_redacted"] == "https://www.fotmob.com/api/matchDetails?matchId=4813722"


# --- mocked network probe ---


def test_probe_endpoint_json_ok():
    """Mock a successful JSON response."""
    mock_resp = mock.MagicMock()
    mock_resp.status = 200
    mock_resp.headers = {"Content-Type": "application/json; charset=utf-8"}
    mock_resp.geturl.return_value = "https://www.fotmob.com/api/matchDetails?matchId=4813722"
    mock_resp.read.return_value = (
        b'{"matchId":4813722,"header":{"teams":[]},"general":{},"content":{}}'
    )

    with mock.patch("urllib.request.urlopen", return_value=mock_resp):
        result = probe_mod.probe_endpoint(
            "https://www.fotmob.com/api/matchDetails?matchId=4813722", 10
        )
        assert result["status_code"] == 200
        assert result["json_parse_ok"] is True
        assert "matchId" in result["top_level_key_names"]
        assert result["required_key_presence"].get("matchId") is True


def test_probe_endpoint_html_response():
    """Mock an HTML response (not JSON)."""
    mock_resp = mock.MagicMock()
    mock_resp.status = 200
    mock_resp.headers = {"Content-Type": "text/html; charset=utf-8"}
    mock_resp.geturl.return_value = "https://www.fotmob.com/matches/test"

    with mock.patch("urllib.request.urlopen", return_value=mock_resp):
        result = probe_mod.probe_endpoint("https://www.fotmob.com/matches/test", 10)
        assert result["status_code"] == 200
        assert result["json_parse_ok"] is False
        assert result["stop_reason"] == "not_json_content_type"


def test_probe_endpoint_403():
    """Mock a 403 response."""
    from urllib import error

    with mock.patch(
        "urllib.request.urlopen",
        side_effect=error.HTTPError("https://test", 403, "Forbidden", {}, None),
    ):
        result = probe_mod.probe_endpoint("https://test", 10)
        assert result["status_code"] == 403
        assert result["stop_reason"] == "blocked_403"


def test_probe_endpoint_429():
    """Mock a 429 response."""
    from urllib import error

    with mock.patch(
        "urllib.request.urlopen",
        side_effect=error.HTTPError("https://test", 429, "Too Many Requests", {}, None),
    ):
        result = probe_mod.probe_endpoint("https://test", 10)
        assert result["status_code"] == 429
        assert result["stop_reason"] == "blocked_429_rate_limited"


def test_probe_endpoint_404():
    """Mock a 404 response."""
    from urllib import error

    with mock.patch(
        "urllib.request.urlopen",
        side_effect=error.HTTPError("https://test", 404, "Not Found", {}, None),
    ):
        result = probe_mod.probe_endpoint("https://test", 10)
        assert result["status_code"] == 404
        assert result["stop_reason"] == "invalid_404"


# --- manifest sections ---


def test_manifest_has_required_sections(tmp_path):
    manifest = tmp_path / "manifest.json"
    report = tmp_path / "report.md"
    review = tmp_path / "review.md"
    endpoint = tmp_path / "endpoint.md"

    result = _run_script(
        [
            "--seed-manifest",
            "docs/_manifests/fotmob_known_match_page_user_seeds_parse_no_write_manifest.json",
            "--output-manifest",
            str(manifest),
            "--report",
            str(report),
            "--review-report",
            str(review),
            "--endpoint-decision-report",
            str(endpoint),
            "--run-id",
            "test_sections_v1",
            "--max-samples",
            "3",
        ]
    )
    assert result.returncode == 0

    m = json.loads(manifest.read_text(encoding="utf-8"))
    required = [
        "schema_version",
        "phase",
        "run_id",
        "mode",
        "inherited_seed_status",
        "probe_selection",
        "endpoint_candidates",
        "probe_results",
        "probe_summary",
        "json_probe_readiness",
        "safety",
        "embedded_review",
        "recommended_next_phase",
    ]
    for section in required:
        assert section in m, f"Missing section: {section}"


# --- selected match IDs verification ---


def test_selected_match_ids_match_expected(tmp_path):
    manifest = tmp_path / "manifest.json"
    report = tmp_path / "report.md"
    review = tmp_path / "review.md"
    endpoint = tmp_path / "endpoint.md"

    result = _run_script(
        [
            "--seed-manifest",
            "docs/_manifests/fotmob_known_match_page_user_seeds_parse_no_write_manifest.json",
            "--output-manifest",
            str(manifest),
            "--report",
            str(report),
            "--review-report",
            str(review),
            "--endpoint-decision-report",
            str(endpoint),
            "--run-id",
            "test_mids_v1",
            "--max-samples",
            "3",
        ]
    )
    assert result.returncode == 0

    m = json.loads(manifest.read_text(encoding="utf-8"))
    mids = m["probe_selection"]["selected_match_ids"]
    # First selected should be exact/reversed pairs from the 7 available
    for mid in mids:
        assert mid in {"4813722", "4813492", "3495351", "4813622", "4813421", "4044692", "4359098"}


# --- endpoint decision report ---


def test_endpoint_decision_report_generated(tmp_path):
    manifest = tmp_path / "manifest.json"
    report = tmp_path / "report.md"
    review = tmp_path / "review.md"
    endpoint = tmp_path / "endpoint.md"

    result = _run_script(
        [
            "--seed-manifest",
            "docs/_manifests/fotmob_known_match_page_user_seeds_parse_no_write_manifest.json",
            "--output-manifest",
            str(manifest),
            "--report",
            str(report),
            "--review-report",
            str(review),
            "--endpoint-decision-report",
            str(endpoint),
            "--run-id",
            "test_edr_v1",
            "--max-samples",
            "3",
        ]
    )
    assert result.returncode == 0
    assert endpoint.exists()
    content = endpoint.read_text(encoding="utf-8")
    assert "Endpoint" in content
    assert "matchDetails" in content
