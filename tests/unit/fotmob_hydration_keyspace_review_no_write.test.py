"""Tests for FotMob hydration keyspace review no-write.

lifecycle: permanent
"""

from __future__ import annotations

import json
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts/ops"))

SCRIPT = ROOT / "scripts/ops/fotmob_hydration_keyspace_review_no_write.py"
CHECKER = ROOT / "scripts/ops/fotmob_hydration_keyspace_review_no_write_check.py"

import fotmob_hydration_keyspace_review_no_write as mod  # noqa: E402


def _base_argv(tmp_path: Path) -> list[str]:
    return [
        "--review-followup-manifest",
        "docs/_manifests/fotmob_match_detail_subtree_review_followup_no_write_manifest.json",
        "--controlled-subtree-manifest",
        "docs/_manifests/fotmob_controlled_match_detail_subtree_extraction_no_write_manifest.json",
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
        [sys.executable, str(SCRIPT), *argv],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )


def _manifest(tmp_path: Path) -> dict:
    return json.loads((tmp_path / "m.json").read_text(encoding="utf-8"))


# --- Basic existence ---


def test_script_exists():
    assert SCRIPT.exists()


def test_checker_exists():
    assert CHECKER.exists()


# --- Dry-run tests ---


def test_dry_run_no_network(tmp_path):
    result = _run(tmp_path)
    assert result.returncode == 0
    m = _manifest(tmp_path)
    assert m["mode"] == "dry_run_keyspace_review_plan_only"
    assert m["safety"]["network_fetch_performed"] is False
    assert m["keyspace_summary"]["network_requests_attempted"] == 0


def test_dry_run_inherits_1448(tmp_path):
    result = _run(tmp_path)
    assert result.returncode == 0
    inherited = _manifest(tmp_path)["inherited_review_followup"]
    assert inherited["notable_matches_is_not_match_detail"] is True
    assert inherited["keyspace_review_required"] is True
    assert inherited["route_variant_review_required"] is True
    assert inherited["json_validated_count"] == 0
    assert inherited["raw_write_eligible_count"] == 0


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


# --- Bound validation ---


def test_max_samples_exceeded_fails(tmp_path):
    result = _run(tmp_path, ["--max-samples", "5"])
    assert result.returncode != 0


def test_max_network_requests_exceeded_fails(tmp_path):
    result = _run(tmp_path, ["--max-network-requests", "5"])
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
    assert _manifest(tmp_path)["keyspace_selection"]["max_value_preview_chars"] == 0


# --- Scoring ---


def test_scoring_detects_positive_terms():
    assert mod._score_key_path("props.pageProps.content", "content", "4813722", "2ygkcb") > 2
    assert mod._score_key_path("props.pageProps.general", "general", "4813722", "2ygkcb") > 2
    assert mod._score_key_path("props.pageProps.header", "header", "4813722", "2ygkcb") > 2


def test_scoring_penalizes_notable_matches():
    score = mod._score_key_path(
        "props.pageProps.fallback.notableMatches", "notableMatches", "4813722", "2ygkcb"
    )
    assert score < 0


def test_scoring_penalizes_translations():
    score = mod._score_key_path("props.pageProps.translations", "translations", "4813722", "2ygkcb")
    assert score < 0


def test_scoring_bonus_for_match_id_in_path():
    base = mod._score_key_path("props.pageProps.data", "data", "4813722", "2ygkcb")
    with_id = mod._score_key_path("props.pageProps.4813722.data", "data", "4813722", "2ygkcb")
    assert with_id > base


def test_scoring_bonus_for_route_code_in_path():
    base = mod._score_key_path("props.pageProps.data", "data", "4813722", "2ygkcb")
    with_code = mod._score_key_path("props.pageProps.2ygkcb.data", "data", "4813722", "2ygkcb")
    assert with_code > base


# --- Classification ---


def test_classification_strong():
    assert mod._classify_path(8) == "strong_match_detail_path_candidate"
    assert mod._classify_path(10) == "strong_match_detail_path_candidate"


def test_classification_weak():
    assert mod._classify_path(4) == "weak_match_detail_path_candidate"
    assert mod._classify_path(7) == "weak_match_detail_path_candidate"


def test_classification_partial():
    assert mod._classify_path(1) == "partial_or_ambiguous_path"
    assert mod._classify_path(3) == "partial_or_ambiguous_path"


def test_classification_generic():
    assert mod._classify_path(0) == "generic_or_irrelevant_path"
    assert mod._classify_path(-5) == "generic_or_irrelevant_path"


# --- Key path scanner ---


def test_keyspace_scanner_records_paths():
    sample = {"a": 1, "b": {"c": 2, "d": {"e": 3}}}
    paths = mod._scan_keyspace(sample, "", 0, 3, [], "4813722", "2ygkcb")
    path_set = {p["key_path"] for p in paths}
    assert "a" in path_set
    assert "b" in path_set
    assert "b.c" in path_set
    assert "b.d" in path_set
    assert "b.d.e" in path_set


def test_keyspace_scanner_does_not_record_values():
    sample = {"secret": "my-password-12345"}
    paths = mod._scan_keyspace(sample, "", 0, 3, [], "4813722", "2ygkcb")
    for p in paths:
        assert "my-password" not in str(p)


def test_keyspace_scanner_records_types():
    sample = {"num": 42, "text": "hello", "flag": True, "none_val": None}
    paths = mod._scan_keyspace(sample, "", 0, 3, [], "4813722", "2ygkcb")
    types = {p["key_path"]: p["data_type"] for p in paths}
    assert types.get("num") in ("int", "float")
    assert types.get("text") == "str"
    assert types.get("flag") == "bool"
    assert types.get("none_val") == "null"


def test_keyspace_scanner_respects_depth():
    deep = {"a": {"b": {"c": {"d": {"e": {"f": {"g": "deep"}}}}}}}
    paths = mod._scan_keyspace(deep, "", 0, 3, [], "4813722", "2ygkcb")
    max_depth = max(p["depth"] for p in paths)
    assert max_depth <= 3


# --- Route variant ---


def test_route_variant_default():
    url = mod._build_url("default", "2ygkcb", "4813722")
    assert "matches/2ygkcb/4813722" in url
    assert "zh-Hans" not in url


def test_route_variant_zh_hans():
    url = mod._build_url("zh-Hans", "2ygkcb", "4813722")
    assert "zh-Hans" in url
    assert "matches/2ygkcb/4813722" in url


# --- Safety enforcement ---


def test_safety_exits_on_forbidden_flags(tmp_path):
    result = _run(tmp_path)
    assert result.returncode == 0
    m = _manifest(tmp_path)
    # Verify safety flags are all false
    safety = m["safety"]
    for flag in mod.SAFETY_FALSE_NAMES:
        assert safety.get(flag) is False, f"safety.{flag} must be false"


def test_readiness_never_ready(tmp_path):
    result = _run(tmp_path)
    assert result.returncode == 0
    readiness = _manifest(tmp_path)["raw_write_readiness"]
    assert readiness["json_validated_count"] == 0
    assert readiness["raw_write_eligible_count"] == 0


# --- Dry-run checker ---


def test_checker_passes_after_dry_run(tmp_path):
    result = _run(tmp_path)
    assert result.returncode == 0
    cr = subprocess.run(
        [sys.executable, str(CHECKER)],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )
    assert cr.returncode == 0, f"checker failed: {cr.stderr}"
