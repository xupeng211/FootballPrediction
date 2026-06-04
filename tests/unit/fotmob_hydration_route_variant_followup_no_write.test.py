"""Tests for FotMob hydration route variant follow-up no-write.

lifecycle: permanent
"""

from __future__ import annotations

import json
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts/ops"))

SCRIPT = ROOT / "scripts/ops/fotmob_hydration_route_variant_followup_no_write.py"
CHECKER = ROOT / "scripts/ops/fotmob_hydration_route_variant_followup_no_write_check.py"

import fotmob_hydration_route_variant_followup_no_write as mod  # noqa: E402


def _base_argv(tmp_path: Path) -> list[str]:
    return [
        "--keyspace-manifest",
        "docs/_manifests/fotmob_hydration_keyspace_review_no_write_manifest.json",
        "--review-followup-manifest",
        "docs/_manifests/fotmob_match_detail_subtree_review_followup_no_write_manifest.json",
        "--seed-manifest",
        "docs/_manifests/fotmob_known_match_page_user_seeds_parse_no_write_manifest.json",
        "--output-manifest",
        str(tmp_path / "m.json"),
        "--report",
        str(tmp_path / "r.md"),
        "--review-report",
        str(tmp_path / "rv.md"),
        "--decision-report",
        str(tmp_path / "d.md"),
        "--run-id",
        "test-run",
        "--max-samples",
        "2",
        "--max-route-variants",
        "2",
        "--max-body-bytes",
        "524288",
        "--max-scan-depth",
        "12",
        "--max-key-paths-recorded",
        "500",
    ]


def _run(tmp_path: Path, extra: list[str] | None = None) -> subprocess.CompletedProcess[str]:
    argv = _base_argv(tmp_path) + (extra or [])
    return subprocess.run(
        [sys.executable, str(SCRIPT), *argv], cwd=ROOT, text=True, capture_output=True, check=False
    )


def _manifest(tmp_path: Path) -> dict:
    return json.loads((tmp_path / "m.json").read_text(encoding="utf-8"))


def test_script_exists():
    assert SCRIPT.exists()


def test_checker_exists():
    assert CHECKER.exists()


def test_dry_run_no_network(tmp_path):
    result = _run(tmp_path)
    assert result.returncode == 0
    m = _manifest(tmp_path)
    assert m["mode"] == "dry_run_route_variant_followup_plan_only"
    assert m["safety"]["network_fetch_performed"] is False
    assert m["route_variant_summary"]["network_requests_attempted"] == 0


def test_dry_run_inherits_1449(tmp_path):
    result = _run(tmp_path)
    assert result.returncode == 0
    inherited = _manifest(tmp_path)["inherited_keyspace_review"]
    assert inherited["default_route_strong_path_candidate_count"] == 0
    assert inherited["zh_hans_route_strong_path_candidate_count"] == 0
    assert inherited["weak_path_candidate_count"] == 0
    assert inherited["best_path_candidate"] == "props.pageProps.fetchingLeagueData"
    assert inherited["notable_matches_rejected"] is True


def test_dry_run_no_value_persistence(tmp_path):
    result = _run(tmp_path)
    assert result.returncode == 0
    safety = _manifest(tmp_path)["safety"]
    for flag in [
        "value_persistence_performed",
        "full_html_saved",
        "raw_response_body_saved",
        "html_body_saved",
        "full_next_data_saved",
        "raw_json_write_performed",
        "db_write_performed",
    ]:
        assert safety[flag] is False


def test_dry_run_no_scheduler_no_feature_parse(tmp_path):
    result = _run(tmp_path)
    assert result.returncode == 0
    safety = _manifest(tmp_path)["safety"]
    assert safety["scheduler_enabled"] is False
    assert safety["feature_parse_performed"] is False


def test_dry_run_readiness_blocked(tmp_path):
    result = _run(tmp_path)
    assert result.returncode == 0
    readiness = _manifest(tmp_path)["raw_write_readiness"]
    assert readiness["json_validated_count"] == 0
    assert readiness["raw_write_eligible_count"] == 0
    assert readiness["raw_write_blocked_until_json_validated"] is True


def test_dry_run_recommended_next_safe(tmp_path):
    result = _run(tmp_path)
    assert result.returncode == 0
    rec = _manifest(tmp_path)["recommended_next_phase"]
    assert "DIRECT-RAW-WRITE" not in rec
    assert "RAW-JSON-WRITE" not in rec


def test_max_samples_exceeded_fails(tmp_path):
    result = _run(tmp_path, ["--max-samples", "5"])
    assert result.returncode != 0


def test_max_route_variants_exceeded_fails(tmp_path):
    result = _run(tmp_path, ["--max-route-variants", "5"])
    assert result.returncode != 0


def test_max_network_requests_exceeded_fails(tmp_path):
    result = _run(tmp_path, ["--max-network-requests", "10"])
    assert result.returncode != 0


def test_max_body_bytes_exceeded_fails(tmp_path):
    result = _run(tmp_path, ["--max-body-bytes", "999999"])
    assert result.returncode != 0


def test_max_scan_depth_exceeded_fails(tmp_path):
    result = _run(tmp_path, ["--max-scan-depth", "50"])
    assert result.returncode != 0


def test_max_key_paths_exceeded_fails(tmp_path):
    result = _run(tmp_path, ["--max-key-paths-recorded", "999"])
    assert result.returncode != 0


def test_max_value_preview_always_zero(tmp_path):
    result = _run(tmp_path)
    assert result.returncode == 0
    assert _manifest(tmp_path)["route_variant_selection"]["max_value_preview_chars"] == 0


def test_selected_variants_include_en_and_slug(tmp_path):
    result = _run(tmp_path)
    assert result.returncode == 0
    variants = _manifest(tmp_path)["route_variant_selection"]["selected_route_variants"]
    assert any("en" in v.lower() for v in variants)
    assert any("slug" in v.lower() for v in variants)


def test_selected_variants_exclude_api_endpoints(tmp_path):
    result = _run(tmp_path)
    assert result.returncode == 0
    variants = _manifest(tmp_path)["route_variant_selection"]["selected_route_variants"]
    for v in variants:
        assert "api/matchDetails" not in v.lower()
        assert "api/data/matchDetails" not in v.lower()


def test_variant_decision_strong():
    assert mod._determine_variant_decision(1, 0, False) == "route_variant_unlocks_detail_candidate"
    assert mod._determine_variant_decision(0, 1, False) == "route_variant_unlocks_detail_candidate"


def test_variant_decision_differs():
    assert mod._determine_variant_decision(0, 0, True) == "route_variant_differs_but_no_detail"


def test_variant_decision_same():
    assert mod._determine_variant_decision(0, 0, False) == "route_variant_same_generic_keyspace"


def test_url_en_variant():
    url = mod._build_url("en", "2ygkcb", "4813722")
    assert "/en/matches/" in url
    assert "2ygkcb" in url
    assert "4813722" in url


def test_url_slug_variant():
    url = mod._build_url("slug", "2ygkcb", "4813722", "liverpool-vs-manchester-united")
    assert "liverpool-vs-manchester-united" in url
    assert "2ygkcb" in url
    assert "4813722" not in url  # slug route does not include match_id


def test_scoring_penalizes_notable_matches():
    score = mod._score_key_path(
        "props.pageProps.fallback.notableMatches", "notableMatches", "4813722", "2ygkcb"
    )
    assert score < 0


def test_scoring_penalizes_translations():
    score = mod._score_key_path("props.pageProps.translations", "translations", "4813722", "2ygkcb")
    assert score < 0


def test_no_value_persistence_flags(tmp_path):
    result = _run(tmp_path)
    assert result.returncode == 0
    safety = _manifest(tmp_path)["safety"]
    for flag in mod.SAFETY_FALSE_NAMES:
        assert safety.get(flag) is False, f"safety.{flag} must be false"


def test_checker_passes_after_dry_run(tmp_path):
    result = _run(tmp_path)
    assert result.returncode == 0
    cr = subprocess.run(
        [sys.executable, str(CHECKER)], cwd=ROOT, text=True, capture_output=True, check=False
    )
    assert cr.returncode == 0, f"checker failed: {cr.stderr}"
