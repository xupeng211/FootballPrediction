"""Tests for FotMob JSON endpoint review no-write phase.

lifecycle: permanent
phase: FOTMOB-RAW-JSON-LONG-RUN-COLLECTOR-CONTROLLED-JSON-PROBE-ENDPOINT-REVIEW-NO-WRITE

Validates offline endpoint review correctness, candidate generation, and no-write safety.
No network, no DB, no raw write.
"""

from __future__ import annotations

import json
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts/ops"))

SCRIPT = ROOT / "scripts/ops/fotmob_json_endpoint_review_no_write.py"
CHECKER = ROOT / "scripts/ops/fotmob_json_endpoint_review_no_write_check.py"

import fotmob_json_endpoint_review_no_write as review_mod  # noqa: E402


def _run_script(args: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(SCRIPT), *args],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )


# --- file existence ---


def test_script_exists():
    assert SCRIPT.exists()


def test_checker_exists():
    assert CHECKER.exists()


# --- missing manifest fails ---


def test_missing_controlled_probe_manifest_fails(tmp_path):
    result = _run_script(
        [
            "--controlled-probe-manifest",
            str(tmp_path / "missing.json"),
            "--seed-manifest",
            "docs/_manifests/fotmob_known_match_page_user_seeds_parse_no_write_manifest.json",
            "--output-manifest",
            str(tmp_path / "out.json"),
            "--report",
            str(tmp_path / "report.md"),
            "--review-report",
            str(tmp_path / "review.md"),
            "--next-probe-plan",
            str(tmp_path / "plan.md"),
            "--run-id",
            "test_v1",
        ]
    )
    assert result.returncode != 0


def test_missing_seed_manifest_fails(tmp_path):
    result = _run_script(
        [
            "--controlled-probe-manifest",
            "docs/_manifests/fotmob_controlled_json_probe_no_write_manifest.json",
            "--seed-manifest",
            str(tmp_path / "missing.json"),
            "--output-manifest",
            str(tmp_path / "out.json"),
            "--report",
            str(tmp_path / "report.md"),
            "--review-report",
            str(tmp_path / "review.md"),
            "--next-probe-plan",
            str(tmp_path / "plan.md"),
            "--run-id",
            "test_v2",
        ]
    )
    assert result.returncode != 0


# --- missing historical files do not fail ---


def test_script_runs_with_missing_historical_files(tmp_path):
    """The script should tolerate missing historical files."""
    result = _run_script(
        [
            "--controlled-probe-manifest",
            "docs/_manifests/fotmob_controlled_json_probe_no_write_manifest.json",
            "--seed-manifest",
            "docs/_manifests/fotmob_known_match_page_user_seeds_parse_no_write_manifest.json",
            "--output-manifest",
            str(tmp_path / "out.json"),
            "--report",
            str(tmp_path / "report.md"),
            "--review-report",
            str(tmp_path / "review.md"),
            "--next-probe-plan",
            str(tmp_path / "plan.md"),
            "--run-id",
            "test_v3",
        ]
    )
    assert result.returncode == 0


# --- full script run ---


def test_script_run_succeeds(tmp_path):
    result = _run_script(
        [
            "--controlled-probe-manifest",
            "docs/_manifests/fotmob_controlled_json_probe_no_write_manifest.json",
            "--seed-manifest",
            "docs/_manifests/fotmob_known_match_page_user_seeds_parse_no_write_manifest.json",
            "--output-manifest",
            str(tmp_path / "manifest.json"),
            "--report",
            str(tmp_path / "report.md"),
            "--review-report",
            str(tmp_path / "review.md"),
            "--next-probe-plan",
            str(tmp_path / "plan.md"),
            "--run-id",
            "test_full_v1",
        ]
    )
    assert result.returncode == 0, f"Script failed: {result.stderr}"

    m = json.loads(Path(tmp_path / "manifest.json").read_text(encoding="utf-8"))

    # Check core structure
    assert m["phase"] == review_mod.PHASE
    assert m["mode"] == "offline_endpoint_review"

    # Check inheritance
    ih = m["inherited_probe_status"]
    assert ih["network_requests_attempted"] == 9
    assert ih["json_parse_ok_count"] == 0
    assert ih["invalid_count"] == 9

    # Check rejected endpoints
    assert len(m["rejected_endpoints"]) >= 3

    # Check candidates
    assert len(m["endpoint_candidates"]) >= 1
    for c in m["endpoint_candidates"]:
        assert "endpoint_candidate_id" in c
        assert "confidence_score" in c
        assert "risk_score" in c
        assert "recommended_probe_priority" in c
        assert "next_phase_probe_allowed" in c

    # Check next probe plan
    plan = m["next_probe_plan"]
    assert plan["selected_candidate_count"] >= 1
    assert plan["max_samples"] == 3
    assert plan["max_network_requests"] == 9
    assert len(plan["selected_match_ids"]) >= 1
    assert len(plan["selected_route_codes"]) >= 1

    # Check readiness
    rw = m["raw_write_readiness"]
    assert rw["json_validated_count"] == 0
    assert rw["raw_write_eligible_count"] == 0
    assert rw["raw_write_blocked_until_json_validated"] is True

    # Check safety
    safety = m["safety"]
    assert safety["network_fetch_performed"] is False
    assert safety["db_write_performed"] is False
    assert safety["raw_json_write_performed"] is False
    assert safety["raw_response_body_saved"] is False
    assert safety["scheduler_enabled"] is False
    assert safety["feature_parse_performed"] is False
    assert safety["browser_automation_performed"] is False
    assert safety["captcha_bypass_performed"] is False
    assert safety["proxy_rotation_performed"] is False

    # Check next phase
    assert m["recommended_next_phase"] == review_mod.NEXT_PHASE
    assert "RAW-JSON-DEV-WRITE" not in m["recommended_next_phase"]


# --- endpoint candidate properties ---


def test_endpoint_candidates_have_required_fields():
    candidates = review_mod.build_endpoint_candidates()
    assert len(candidates) >= 5
    required_fields = [
        "endpoint_candidate_id",
        "category",
        "endpoint_template",
        "source",
        "confidence_score",
        "risk_score",
        "recommended_probe_priority",
        "next_phase_probe_allowed",
        "reason",
    ]
    for c in candidates:
        for field in required_fields:
            assert field in c, f"Missing {field} in {c['endpoint_candidate_id']}"


def test_rejected_endpoints_not_in_next_probe():
    candidates = review_mod.build_endpoint_candidates()
    rejected = [c for c in candidates if c["category"] == "rejected"]
    for r in rejected:
        assert r["next_phase_probe_allowed"] is False
        assert r["recommended_probe_priority"] == 0


def test_api_json_direct_candidate_has_data_prefix():
    """The canonical endpoint must have /api/data/ prefix."""
    candidates = review_mod.build_endpoint_candidates()
    api_direct = [c for c in candidates if c["category"] == "api_json_direct"]
    assert len(api_direct) >= 1
    assert any("/api/data/" in c["endpoint_template"] for c in api_direct)


def test_html_hydration_candidates_exist():
    candidates = review_mod.build_endpoint_candidates()
    hydration = [c for c in candidates if c["category"] == "html_hydration"]
    assert len(hydration) >= 1
    for h in hydration:
        assert h["next_phase_probe_allowed"] is True


def test_deferred_candidates_not_in_next_probe():
    candidates = review_mod.build_endpoint_candidates()
    deferred = [c for c in candidates if c["category"] == "deferred"]
    for d in deferred:
        assert d["next_phase_probe_allowed"] is False


# --- next probe plan ---


def test_next_probe_plan_generated():
    candidates = review_mod.build_endpoint_candidates()
    plan = review_mod.build_next_probe_plan(
        candidates, ["4813722", "4813492", "4813622"], ["2ygkcb", "2ynv4k", "2xqo0r"]
    )
    assert plan["selected_candidate_count"] >= 1
    assert plan["max_samples"] == 3
    assert plan["max_network_requests"] == 9
    assert plan["raw_response_body_saved"] is False
    assert plan["raw_json_write"] is False
    assert plan["db_write"] is False
    assert len(plan["selected_endpoint_templates"]) >= 1
    assert plan["allow_network_required"] is True


# --- manifest sections ---


def test_manifest_has_required_sections(tmp_path):
    result = _run_script(
        [
            "--controlled-probe-manifest",
            "docs/_manifests/fotmob_controlled_json_probe_no_write_manifest.json",
            "--seed-manifest",
            "docs/_manifests/fotmob_known_match_page_user_seeds_parse_no_write_manifest.json",
            "--output-manifest",
            str(tmp_path / "manifest.json"),
            "--report",
            str(tmp_path / "report.md"),
            "--review-report",
            str(tmp_path / "review.md"),
            "--next-probe-plan",
            str(tmp_path / "plan.md"),
            "--run-id",
            "test_sections_v1",
        ]
    )
    assert result.returncode == 0

    m = json.loads(Path(tmp_path / "manifest.json").read_text(encoding="utf-8"))
    required = [
        "schema_version",
        "phase",
        "run_id",
        "mode",
        "inherited_probe_status",
        "rejected_endpoints",
        "historical_files_reviewed",
        "endpoint_candidates",
        "next_probe_plan",
        "raw_write_readiness",
        "safety",
        "embedded_review",
        "recommended_next_phase",
    ]
    for section in required:
        assert section in m, f"Missing section: {section}"


# --- historical file review ---


def test_historical_files_reviewed():
    reviewed = review_mod.review_historical_files(ROOT)
    assert len(reviewed) >= 3
    found = sum(1 for r in reviewed if r["exists"])
    assert found >= 3, f"Expected at least 3 files, found {found}"


# --- next phase safety ---


def test_next_phase_never_recommends_raw_write(tmp_path):
    result = _run_script(
        [
            "--controlled-probe-manifest",
            "docs/_manifests/fotmob_controlled_json_probe_no_write_manifest.json",
            "--seed-manifest",
            "docs/_manifests/fotmob_known_match_page_user_seeds_parse_no_write_manifest.json",
            "--output-manifest",
            str(tmp_path / "manifest.json"),
            "--report",
            str(tmp_path / "report.md"),
            "--review-report",
            str(tmp_path / "review.md"),
            "--next-probe-plan",
            str(tmp_path / "plan.md"),
            "--run-id",
            "test_safe_next_v1",
        ]
    )
    assert result.returncode == 0
    m = json.loads(Path(tmp_path / "manifest.json").read_text(encoding="utf-8"))
    rec = m["recommended_next_phase"]
    forbidden = ["RAW-JSON-DEV-WRITE", "RAW-MATCH-DATA", "DIRECT-RAW-WRITE", "L2-RAW-HARVESTING"]
    for word in forbidden:
        assert word not in rec, f"Next phase contains forbidden word: {word}"


# --- no-write safety on all probe results ---


def test_all_probe_flags_false(tmp_path):
    result = _run_script(
        [
            "--controlled-probe-manifest",
            "docs/_manifests/fotmob_controlled_json_probe_no_write_manifest.json",
            "--seed-manifest",
            "docs/_manifests/fotmob_known_match_page_user_seeds_parse_no_write_manifest.json",
            "--output-manifest",
            str(tmp_path / "manifest.json"),
            "--report",
            str(tmp_path / "report.md"),
            "--review-report",
            str(tmp_path / "review.md"),
            "--next-probe-plan",
            str(tmp_path / "plan.md"),
            "--run-id",
            "test_flags_v1",
        ]
    )
    assert result.returncode == 0
    m = json.loads(Path(tmp_path / "manifest.json").read_text(encoding="utf-8"))
    safety = m["safety"]
    assert safety["network_fetch_performed"] is False
    assert safety["db_read_performed"] is False
    assert safety["db_write_performed"] is False
    assert safety["raw_response_body_saved"] is False
    assert safety["raw_json_write_performed"] is False
    assert safety["scheduler_enabled"] is False
    assert safety["feature_parse_performed"] is False
    assert safety["browser_automation_performed"] is False


# --- next probe plan report generated ---


def test_next_probe_plan_report_exists(tmp_path):
    result = _run_script(
        [
            "--controlled-probe-manifest",
            "docs/_manifests/fotmob_controlled_json_probe_no_write_manifest.json",
            "--seed-manifest",
            "docs/_manifests/fotmob_known_match_page_user_seeds_parse_no_write_manifest.json",
            "--output-manifest",
            str(tmp_path / "manifest.json"),
            "--report",
            str(tmp_path / "report.md"),
            "--review-report",
            str(tmp_path / "review.md"),
            "--next-probe-plan",
            str(tmp_path / "plan.md"),
            "--run-id",
            "test_plan_v1",
        ]
    )
    assert result.returncode == 0
    plan_path = tmp_path / "plan.md"
    assert plan_path.exists()
    content = plan_path.read_text(encoding="utf-8")
    assert "Next Probe Plan" in content
    assert "endpoint" in content.lower()
    assert "no-write" in content.lower()
