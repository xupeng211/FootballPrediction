"""Tests for FotMob match detail subtree review follow-up no-write.

lifecycle: permanent
"""

from __future__ import annotations

import json
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts/ops"))

SCRIPT = ROOT / "scripts/ops/fotmob_match_detail_subtree_review_followup_no_write.py"
CHECKER = ROOT / "scripts/ops/fotmob_match_detail_subtree_review_followup_no_write_check.py"

import fotmob_match_detail_subtree_review_followup_no_write as mod  # noqa: E402


def _base_args(tmp_path: Path, controlled: str | None = None) -> list[str]:
    return [
        "--controlled-subtree-manifest",
        controlled
        or "docs/_manifests/fotmob_controlled_match_detail_subtree_extraction_no_write_manifest.json",
        "--subtree-plan-manifest",
        "docs/_manifests/fotmob_match_detail_subtree_extraction_plan_no_write_manifest.json",
        "--hydration-validation-manifest",
        "docs/_manifests/fotmob_hydration_structure_validation_no_write_manifest.json",
        "--seed-manifest",
        "docs/_manifests/fotmob_known_match_page_user_seeds_parse_no_write_manifest.json",
        "--output-manifest",
        str(tmp_path / "m.json"),
        "--report",
        str(tmp_path / "r.md"),
        "--review-report",
        str(tmp_path / "rv.md"),
        "--next-plan",
        str(tmp_path / "n.md"),
        "--run-id",
        "test-run",
    ]


def _run(tmp_path: Path, controlled: str | None = None) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(SCRIPT), *_base_args(tmp_path, controlled)],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )


def _manifest(tmp_path: Path) -> dict:
    return json.loads((tmp_path / "m.json").read_text(encoding="utf-8"))


def test_script_exists():
    assert SCRIPT.exists()


def test_checker_exists():
    assert CHECKER.exists()


def test_missing_controlled_subtree_manifest_fails(tmp_path):
    result = _run(tmp_path, "docs/_manifests/missing_controlled_subtree.json")
    assert result.returncode != 0
    assert "controlled subtree manifest missing" in result.stderr


def test_inherits_1447_negative_counts(tmp_path):
    result = _run(tmp_path)
    assert result.returncode == 0
    inherited = _manifest(tmp_path)["inherited_controlled_subtree_extraction"]
    assert inherited["fallback_present_count"] == 2
    assert inherited["target_match_id_seen_count"] == 0
    assert inherited["strong_candidate_count"] == 0
    assert inherited["generic_or_irrelevant_count"] == 2
    assert inherited["best_candidate_path"] == mod.BEST_GENERIC_PATH


def test_notable_matches_marked_not_match_detail(tmp_path):
    assert _run(tmp_path).returncode == 0
    negative = _manifest(tmp_path)["negative_findings"]
    assert negative["notable_matches_is_not_match_detail"] is True
    assert negative["target_match_id_missing"] is True


def test_keyspace_and_route_review_required(tmp_path):
    assert _run(tmp_path).returncode == 0
    negative = _manifest(tmp_path)["negative_findings"]
    assert negative["keyspace_review_required"] is True
    assert negative["route_variant_review_required"] is True


def test_next_phase_limits_are_bounded(tmp_path):
    assert _run(tmp_path).returncode == 0
    plan = _manifest(tmp_path)["next_keyspace_review_plan"]
    assert plan["max_network_requests"] <= 2
    assert plan["max_body_bytes"] <= 524288
    assert plan["max_key_paths_recorded"] <= 500
    assert plan["max_scan_depth"] <= 12
    assert plan["max_value_preview_chars"] == 0


def test_no_network_or_response_body_read(tmp_path):
    assert _run(tmp_path).returncode == 0
    safety = _manifest(tmp_path)["safety"]
    assert safety["network_fetch_performed"] is False
    assert safety["response_body_read"] is False
    assert safety["bounded_body_read_performed"] is False


def test_no_html_next_data_raw_json_or_db_write(tmp_path):
    assert _run(tmp_path).returncode == 0
    safety = _manifest(tmp_path)["safety"]
    for flag in [
        "full_html_saved",
        "html_body_saved",
        "full_next_data_saved",
        "raw_json_write_performed",
        "db_write_performed",
    ]:
        assert safety[flag] is False


def test_no_scheduler_or_feature_parse(tmp_path):
    assert _run(tmp_path).returncode == 0
    safety = _manifest(tmp_path)["safety"]
    assert safety["scheduler_enabled"] is False
    assert safety["feature_parse_performed"] is False


def test_raw_write_readiness_remains_blocked(tmp_path):
    assert _run(tmp_path).returncode == 0
    readiness = _manifest(tmp_path)["raw_write_readiness"]
    assert readiness["json_validated_count"] == 0
    assert readiness["raw_write_eligible_count"] == 0
    assert readiness["raw_write_blocked_until_json_validated"] is True


def test_historical_code_review_records_parser_hints(tmp_path):
    assert _run(tmp_path).returncode == 0
    review = _manifest(tmp_path)["historical_code_review"]
    files = set(review["files_reviewed"])
    assert "src/parsers/fotmob/NextDataParser.js" in files
    assert "src/infrastructure/services/FotMobRawDetailFetcher.js" in files
    assert "props.pageProps.content" in review["suspected_existing_parser_paths"]


def test_route_variant_review_includes_locale_and_original_path(tmp_path):
    assert _run(tmp_path).returncode == 0
    variants = {
        item["variant"]: item["recommendation"]
        for item in _manifest(tmp_path)["route_variant_review"]["candidates"]
    }
    assert variants["/matches/{route_code}/{match_id}"] == "keep"
    assert variants["/zh-Hans/matches/{route_code}/{match_id}"] == "review next"
    assert variants["/en/matches/{route_code}/{match_id}"] == "review next"
    assert variants["original user URL path without fragment"] == "review next"


def test_recommended_next_phase_is_keyspace_review(tmp_path):
    assert _run(tmp_path).returncode == 0
    assert _manifest(tmp_path)["recommended_next_phase"] == mod.NEXT_PHASE


def test_checker_passes():
    result = subprocess.run(
        [sys.executable, str(CHECKER)],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )
    assert result.returncode == 0
