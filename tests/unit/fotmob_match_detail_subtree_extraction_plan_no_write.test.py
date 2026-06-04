"""Tests for match detail subtree extraction plan no-write."""

from __future__ import annotations

import json
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts/ops"))

SCRIPT = ROOT / "scripts/ops/fotmob_match_detail_subtree_extraction_plan_no_write.py"
CHECKER = ROOT / "scripts/ops/fotmob_match_detail_subtree_extraction_plan_no_write_check.py"

import fotmob_match_detail_subtree_extraction_plan_no_write as pm  # noqa: E402


def _run(args):
    return subprocess.run(
        [sys.executable, str(SCRIPT), *args], cwd=ROOT, text=True, capture_output=True, check=False
    )


def _base(tmp_path):
    return [
        "--hydration-validation-manifest",
        "docs/_manifests/fotmob_hydration_structure_validation_no_write_manifest.json",
        "--inspection-manifest",
        "docs/_manifests/fotmob_limited_html_hydration_inspection_no_write_manifest.json",
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
        "test",
    ]


def test_script_exists():
    assert SCRIPT.exists()


def test_checker_exists():
    assert CHECKER.exists()


def test_missing_hydration_manifest_fails(tmp_path):
    args = _base(tmp_path)
    args[1] = str(tmp_path / "missing.json")
    assert _run(args).returncode != 0


def test_script_run_succeeds(tmp_path):
    r = _run(_base(tmp_path))
    assert r.returncode == 0
    m = json.loads(Path(tmp_path / "m.json").read_text(encoding="utf-8"))
    assert m["mode"] == "offline_subtree_extraction_plan"


def test_inherited_values(tmp_path):
    r = _run(_base(tmp_path))
    assert r.returncode == 0
    m = json.loads(Path(tmp_path / "m.json").read_text(encoding="utf-8"))
    ih = m["inherited_hydration_validation"]
    assert ih["next_data_parse_ok_count"] == 2
    assert ih["pageProps_present_count"] == 2
    assert ih["match_detail_candidate_observed_count"] == 2
    assert ih["target_match_id_seen_count"] == 0


def test_root_path_is_pageprops(tmp_path):
    r = _run(_base(tmp_path))
    assert r.returncode == 0
    m = json.loads(Path(tmp_path / "m.json").read_text(encoding="utf-8"))
    assert m["subtree_extraction_plan"]["root_path"] == "props.pageProps"


def test_priority_paths_include_fallback():
    assert any("fallback" in p[0] for p in pm.PRIORITY_PATHS)


def test_scoring_rules_exist():
    assert len(pm.SCORING_RULES) >= 5
    assert any(r["signal"] == "target match_id found in subtree" for r in pm.SCORING_RULES)
    assert any("header" in r["signal"] for r in pm.SCORING_RULES)
    assert any("translation" in r["signal"] or "config" in r["signal"] for r in pm.SCORING_RULES)


def test_generic_config_negative_score():
    neg = [r for r in pm.SCORING_RULES if r["score"] < 0]
    assert len(neg) >= 1


def test_next_plan_constraints(tmp_path):
    r = _run(_base(tmp_path))
    assert r.returncode == 0
    m = json.loads(Path(tmp_path / "m.json").read_text(encoding="utf-8"))
    scope = m["selected_next_phase_scope"]
    assert scope["max_samples"] <= 2
    assert scope["max_network_requests"] <= 2
    assert scope["max_body_bytes"] <= 524288
    assert scope["max_subtree_scan_depth"] <= 8


def test_safety_flags(tmp_path):
    r = _run(_base(tmp_path))
    assert r.returncode == 0
    m = json.loads(Path(tmp_path / "m.json").read_text(encoding="utf-8"))
    s = m["safety"]
    for k in [
        "network_fetch_performed",
        "response_body_read",
        "full_html_saved",
        "full_next_data_saved",
        "raw_json_write_performed",
        "db_write_performed",
    ]:
        assert s[k] is False, k


def test_readiness(tmp_path):
    r = _run(_base(tmp_path))
    assert r.returncode == 0
    m = json.loads(Path(tmp_path / "m.json").read_text(encoding="utf-8"))
    rw = m["raw_write_readiness"]
    assert rw["json_validated_count"] == 0
    assert rw["raw_write_eligible_count"] == 0


def test_next_phase_not_raw(tmp_path):
    r = _run(_base(tmp_path))
    assert r.returncode == 0
    m = json.loads(Path(tmp_path / "m.json").read_text(encoding="utf-8"))
    assert m["recommended_next_phase"] == pm.NEXT_PHASE
    for w in ["RAW-JSON-DEV-WRITE", "DIRECT-RAW-WRITE"]:
        assert w not in m["recommended_next_phase"]
