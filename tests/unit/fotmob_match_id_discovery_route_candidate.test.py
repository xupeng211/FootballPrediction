"""Tests for FotMob match ID route candidate no-write phase.

lifecycle: permanent
phase: FOTMOB-RAW-JSON-LONG-RUN-COLLECTOR-MATCH-ID-DISCOVERY-ROUTE-CANDIDATE-NO-WRITE

Validates route candidate output consistency and no-write safety.
No network, no DB, no raw write.
"""

from __future__ import annotations

import json
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts/ops"))

SCRIPT = ROOT / "scripts/ops/fotmob_match_id_discovery_route_candidate.py"
CHECKER = ROOT / "scripts/ops/fotmob_match_id_discovery_route_candidate_check.py"
MANIFEST_PATH = ROOT / "docs/_manifests/fotmob_match_id_discovery_route_candidate_manifest.json"


def _load() -> dict:
    return json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))


def _run_script(args: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(SCRIPT), *args],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )


def test_script_exists():
    assert SCRIPT.exists()


def test_checker_exists():
    assert CHECKER.exists()


def test_missing_source_review_manifest_fails(tmp_path):
    result = _run_script(
        [
            "--source-review-manifest",
            str(tmp_path / "missing-source-review.json"),
            "--candidate-manifest",
            "docs/_manifests/fotmob_match_id_discovery_db_dry_run_manifest.json",
            "--output-manifest",
            str(tmp_path / "out.json"),
            "--report",
            str(tmp_path / "report.md"),
            "--review-report",
            str(tmp_path / "review.md"),
        ]
    )
    assert result.returncode != 0
    assert "source review manifest missing" in result.stderr


def test_missing_candidate_manifest_fails(tmp_path):
    result = _run_script(
        [
            "--source-review-manifest",
            "docs/_manifests/fotmob_match_id_discovery_source_review_manifest.json",
            "--candidate-manifest",
            str(tmp_path / "missing-candidates.json"),
            "--output-manifest",
            str(tmp_path / "out.json"),
            "--report",
            str(tmp_path / "report.md"),
            "--review-report",
            str(tmp_path / "review.md"),
        ]
    )
    assert result.returncode != 0
    assert "candidate manifest missing" in result.stderr


def test_max_samples_gt_3_fails(tmp_path):
    result = _run_script(
        [
            "--output-manifest",
            str(tmp_path / "out.json"),
            "--report",
            str(tmp_path / "report.md"),
            "--review-report",
            str(tmp_path / "review.md"),
            "--max-samples",
            "4",
        ]
    )
    assert result.returncode != 0
    assert "--max-samples must be between 1 and 3" in result.stderr


def test_default_mode_does_not_perform_network():
    manifest = _load()
    assert manifest["mode"] == "offline"
    assert manifest["network_probe_summary"]["allow_network_probe"] is False
    assert manifest["network_probe_summary"]["network_requests_attempted"] == 0


def test_allow_network_probe_requires_max_network_requests_lte_3(tmp_path):
    result = _run_script(
        [
            "--output-manifest",
            str(tmp_path / "out.json"),
            "--report",
            str(tmp_path / "report.md"),
            "--review-report",
            str(tmp_path / "review.md"),
            "--allow-network-probe",
            "--max-network-requests",
            "4",
        ]
    )
    assert result.returncode != 0
    assert "--max-network-requests must be between 0 and 3" in result.stderr


def test_url_fragment_parser_extracts_match_id():
    from fotmob_match_id_discovery_route_candidate import parse_fotmob_match_page_url

    parsed = parse_fotmob_match_page_url(
        "https://www.fotmob.com/matches/manchester-city-vs-afc-bournemouth/2feiv3#4813735"
    )
    assert parsed["fotmob_match_id"] == "4813735"


def test_route_code_parser_extracts_path_segment():
    from fotmob_match_id_discovery_route_candidate import parse_fotmob_match_page_url

    parsed = parse_fotmob_match_page_url(
        "https://www.fotmob.com/matches/manchester-city-vs-afc-bournemouth/2feiv3#4813735"
    )
    assert parsed["route_code"] == "2feiv3"


def test_route_candidate_records_generated():
    manifest = _load()
    assert manifest["route_candidates"]
    assert manifest["sample_selection"]["selected_sample_count"] == len(
        manifest["route_candidates"]
    )


def test_selected_sample_count_lte_3():
    assert _load()["sample_selection"]["selected_sample_count"] <= 3


def test_route_validated_count_remains_0():
    assert _load()["route_status_summary"]["route_validated_count"] == 0


def test_json_validated_count_remains_0():
    assert _load()["route_status_summary"]["json_validated_count"] == 0


def test_raw_write_eligible_count_0():
    manifest = _load()
    assert manifest["raw_write_readiness"]["raw_write_eligible_count"] == 0
    for route in manifest["route_candidates"]:
        assert route["raw_write_eligible"] is False


def test_no_db_write():
    assert _load()["safety"]["db_write_performed"] is False


def test_no_raw_json_write():
    assert _load()["safety"]["raw_json_write_performed"] is False


def test_no_raw_response_body_saved():
    assert _load()["safety"]["raw_response_body_saved"] is False
    for route in _load()["route_candidates"]:
        assert route["raw_response_body_saved"] is False


def test_no_scheduler():
    assert _load()["safety"]["scheduler_enabled"] is False


def test_no_feature_parse():
    assert _load()["safety"]["feature_parse_performed"] is False


def test_no_browser_automation():
    assert _load()["safety"]["browser_automation_performed"] is False


def test_no_proxy_rotation():
    assert _load()["safety"]["proxy_rotation_performed"] is False


def test_recommended_next_phase_not_raw_write():
    rec = _load()["recommended_next_phase"]
    assert "RAW-JSON-DEV-WRITE" not in rec
    assert "RAW-MATCH-DATA" not in rec


def test_checker_passes():
    from fotmob_match_id_discovery_route_candidate_check import (
        check_counts,
        check_embedded_review,
        check_network,
        check_next_phase,
        check_readiness,
        check_route_status,
        check_safety,
        check_samples,
        load_manifest,
    )

    manifest = load_manifest()
    assert manifest is not None
    check_counts(manifest)
    check_samples(manifest)
    check_route_status(manifest)
    check_readiness(manifest)
    check_safety(manifest)
    check_embedded_review(manifest)
    check_next_phase(manifest)
    check_network(manifest)
