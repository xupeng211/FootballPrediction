"""Tests for controlled FotMob subtree extraction no-write.

lifecycle: permanent
"""

from __future__ import annotations

import json
from pathlib import Path
import subprocess
import sys
from unittest import mock

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts/ops"))

SCRIPT = ROOT / "scripts/ops/fotmob_controlled_match_detail_subtree_extraction_no_write.py"
CHECKER = ROOT / "scripts/ops/fotmob_controlled_match_detail_subtree_extraction_no_write_check.py"

import fotmob_controlled_match_detail_subtree_extraction_no_write as mod  # noqa: E402


def _run(args):
    return subprocess.run(
        [sys.executable, str(SCRIPT), *args],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )


def _base(tmp_path):
    return [
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
        "--decision-report",
        str(tmp_path / "d.md"),
        "--run-id",
        "test",
    ]


def _mock_response(body: bytes):
    response = mock.MagicMock()
    response.status = 200
    response.headers = {
        "Content-Type": "text/html; charset=utf-8",
        "Content-Length": str(len(body)),
    }
    response.read.return_value = body
    response.close = mock.MagicMock()
    return response


def _html(page_props: dict) -> bytes:
    payload = json.dumps({"props": {"pageProps": page_props}})
    return (
        f'<html><script id="__NEXT_DATA__" type="application/json">{payload}</script></html>'
    ).encode()


def test_script_exists():
    assert SCRIPT.exists()


def test_checker_exists():
    assert CHECKER.exists()


def test_default_mode_does_not_perform_network(tmp_path):
    with mock.patch("urllib.request.urlopen") as urlopen:
        result = _run(_base(tmp_path))
    assert result.returncode == 0
    urlopen.assert_not_called()
    manifest = json.loads(Path(tmp_path / "m.json").read_text(encoding="utf-8"))
    assert manifest["mode"] == "dry_run_subtree_extraction_plan_only"
    assert manifest["extraction_summary"]["network_requests_attempted"] == 0


def test_allow_network_probe_required_for_live_extraction():
    page_props = {"fallback": {"x": {"data": {"matchId": 4813722, "header": {}}}}}
    with mock.patch(
        "urllib.request.urlopen", return_value=_mock_response(_html(page_props))
    ) as urlopen:
        result = mod.probe_and_extract(mod.SAMPLES[0], 524288, 8)
    assert result["network_performed"] is True
    assert result["target_match_id_seen"] is True
    urlopen.assert_called_once()


def test_max_samples_over_two_fails(tmp_path):
    assert _run(_base(tmp_path) + ["--max-samples", "3"]).returncode != 0


def test_max_network_requests_over_two_fails(tmp_path):
    assert _run(_base(tmp_path) + ["--max-network-requests", "3"]).returncode != 0


def test_max_body_bytes_over_limit_fails(tmp_path):
    assert _run(_base(tmp_path) + ["--max-body-bytes", "524289"]).returncode != 0


def test_max_subtree_scan_depth_over_limit_fails(tmp_path):
    assert _run(_base(tmp_path) + ["--max-subtree-scan-depth", "9"]).returncode != 0


def test_route_template_restricted_to_matches_path():
    assert mod.ROUTE_TEMPLATE == "/matches/{route_code}/{match_id}"
    assert "/api/" not in mod.ROUTE_TEMPLATE
    assert "{route_code}" in mod.ROUTE_TEMPLATE


def test_recursive_scanner_starts_from_pageprops():
    paths = mod.collect_key_path_metadata({"fallback": {"a": {"data": {}}}}, 8)
    assert paths[0]["path"] == "props.pageProps"
    assert any(path["path"].startswith("props.pageProps.fallback") for path in paths)


def test_fallback_priority_is_respected():
    page_props = {
        "fallback": {"a": {"data": {"header": {}, "team": "Liverpool"}}},
        "other": {"data": {"header": {}, "team": "Liverpool"}},
    }
    scan = mod.scan_page_props(page_props, "4813722", "Liverpool vs Manchester United", 8)
    assert scan["best_candidate"]["path"].startswith("props.pageProps.fallback")


def test_scoring_detects_target_match_id():
    result = mod.analyze_subtree(
        {"matchId": 4813722}, "props.pageProps.fallback.a", "4813722", "A vs B"
    )
    assert result["target_match_id_seen"] is True
    assert result["score"] >= 4


def test_scoring_detects_header_general_content():
    result = mod.analyze_subtree(
        {"header": {}, "general": {}, "content": {}, "homeTeam": {"name": "Liverpool"}},
        "props.pageProps.fallback.a",
        "4813722",
        "Liverpool vs Manchester United",
    )
    assert result["key_presence"]["header"] is True
    assert result["key_presence"]["general"] is True
    assert result["key_presence"]["content"] is True
    assert result["score"] >= 6


def test_scoring_detects_stats_events_lineup_teams():
    result = mod.analyze_subtree(
        {"stats": {}, "events": [], "lineup": [], "teams": {"home": "Everton"}},
        "props.pageProps.fallback.a",
        "4813492",
        "Everton vs Manchester United",
    )
    assert result["key_presence"]["stats"] is True
    assert result["key_presence"]["events"] is True
    assert result["key_presence"]["lineup"] is True
    assert result["key_presence"]["teams"] is True


def test_scoring_penalizes_translations_config():
    result = mod.analyze_subtree(
        {"translations": {"hello": "world"}, "Language": "en"},
        "props.pageProps.translations",
        "4813722",
        "Liverpool vs Manchester United",
    )
    assert result["score"] <= -5
    assert result["state"] == "generic_or_irrelevant_subtree"


def test_strong_candidate_classification_works():
    result = mod.analyze_subtree(
        {
            "matchId": 4813722,
            "header": {},
            "general": {},
            "content": {},
            "stats": {},
            "events": [],
            "lineup": [],
            "teams": {"home": "Liverpool"},
        },
        "props.pageProps.fallback.a",
        "4813722",
        "Liverpool vs Manchester United",
    )
    assert result["state"] == "match_detail_subtree_strong_candidate"


def test_weak_candidate_classification_works():
    result = mod.analyze_subtree(
        {"header": {}, "general": {}, "homeTeam": {"name": "Liverpool"}},
        "props.pageProps.fallback.a",
        "4813722",
        "Liverpool vs Manchester United",
    )
    assert result["state"] == "match_detail_subtree_weak_candidate"


def test_no_write_safety_flags_remain_false(tmp_path):
    result = _run(_base(tmp_path))
    assert result.returncode == 0
    manifest = json.loads(Path(tmp_path / "m.json").read_text(encoding="utf-8"))
    safety = manifest["safety"]
    for flag in [
        "full_body_read_performed",
        "full_html_saved",
        "full_next_data_saved",
        "candidate_subtree_value_saved",
        "raw_json_write_performed",
        "db_write_performed",
        "scheduler_enabled",
        "feature_parse_performed",
    ]:
        assert safety[flag] is False, flag


def test_json_validated_and_raw_write_counts_remain_zero(tmp_path):
    result = _run(_base(tmp_path))
    assert result.returncode == 0
    manifest = json.loads(Path(tmp_path / "m.json").read_text(encoding="utf-8"))
    assert manifest["raw_write_readiness"]["json_validated_count"] == 0
    assert manifest["raw_write_readiness"]["raw_write_eligible_count"] == 0


def test_checker_passes(tmp_path):
    result = _run(_base(tmp_path))
    assert result.returncode == 0
    check = subprocess.run(
        [sys.executable, str(CHECKER)],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )
    assert check.returncode == 0
