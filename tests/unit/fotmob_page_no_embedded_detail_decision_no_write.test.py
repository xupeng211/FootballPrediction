"""Tests for FotMob page no embedded detail decision no-write.

lifecycle: permanent
"""

from __future__ import annotations

import json
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts/ops"))

SCRIPT = ROOT / "scripts/ops/fotmob_page_no_embedded_detail_decision_no_write.py"
CHECKER = ROOT / "scripts/ops/fotmob_page_no_embedded_detail_decision_no_write_check.py"

import fotmob_page_no_embedded_detail_decision_no_write as mod  # noqa: E402, F401


def _base_argv(tmp_path: Path) -> list[str]:
    return [
        "--route-variant-manifest",
        "docs/_manifests/fotmob_hydration_route_variant_followup_no_write_manifest.json",
        "--keyspace-manifest",
        "docs/_manifests/fotmob_hydration_keyspace_review_no_write_manifest.json",
        "--subtree-manifest",
        "docs/_manifests/fotmob_controlled_match_detail_subtree_extraction_no_write_manifest.json",
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


def test_missing_route_variant_manifest_handled(tmp_path):
    argv = _base_argv(tmp_path)
    argv[1] = "docs/_manifests/missing.json"
    result = subprocess.run(
        [sys.executable, str(SCRIPT), *argv], cwd=ROOT, text=True, capture_output=True, check=False
    )
    # Should not crash — missing manifests produce empty dicts and recorded in missing_inputs
    assert result.returncode == 0
    m = json.loads((tmp_path / "m.json").read_text(encoding="utf-8"))
    assert "docs/_manifests/missing.json" in m.get("missing_inputs", [])


def test_decision_generated(tmp_path):
    result = _run(tmp_path)
    assert result.returncode == 0
    m = _manifest(tmp_path)
    assert m["mode"] == "offline_no_embedded_detail_decision"


def test_route_variant_unlocks_zero_inherited(tmp_path):
    result = _run(tmp_path)
    assert result.returncode == 0
    inherited = _manifest(tmp_path)["inherited_route_variant_followup"]
    assert inherited["route_variant_unlocks_detail_candidate_count"] == 0
    assert inherited["en_variant_detail_unlocked"] is False
    assert inherited["slug_variant_detail_unlocked"] is False


def test_html_hydration_route_exhausted(tmp_path):
    result = _run(tmp_path)
    assert result.returncode == 0
    d = _manifest(tmp_path)["formal_decision"]
    assert d["html_hydration_route_status"] == "exhausted_no_embedded_match_detail"


def test_page_level_next_data_no_detail(tmp_path):
    result = _run(tmp_path)
    assert result.returncode == 0
    d = _manifest(tmp_path)["formal_decision"]
    assert d["page_level_next_data_status"] == "no_match_detail_json_embedded"


def test_raw_json_readiness_not_ready(tmp_path):
    result = _run(tmp_path)
    assert result.returncode == 0
    d = _manifest(tmp_path)["formal_decision"]
    assert d["raw_json_readiness"] == "not_ready"


def test_db_write_readiness_blocked(tmp_path):
    result = _run(tmp_path)
    assert result.returncode == 0
    d = _manifest(tmp_path)["formal_decision"]
    assert d["db_write_readiness"] == "blocked"


def test_l2_harvesting_blocked(tmp_path):
    result = _run(tmp_path)
    assert result.returncode == 0
    d = _manifest(tmp_path)["formal_decision"]
    assert d["l2_harvesting_readiness"] == "blocked"


def test_next_endpoint_discovery_plan_generated(tmp_path):
    result = _run(tmp_path)
    assert result.returncode == 0
    plan = _manifest(tmp_path)["next_endpoint_runtime_discovery_plan"]
    assert plan["network_allowed"] is False
    assert plan["browser_automation_allowed"] is False
    assert plan["cookie_harvesting_allowed"] is False
    assert plan["captcha_bypass_allowed"] is False
    assert plan["raw_write_allowed"] is False


def test_no_network(tmp_path):
    result = _run(tmp_path)
    assert result.returncode == 0
    safety = _manifest(tmp_path)["safety"]
    assert safety["network_fetch_performed"] is False
    assert safety["response_body_read"] is False
    assert safety["bounded_body_read_performed"] is False


def test_no_html_next_data_raw_json_db(tmp_path):
    result = _run(tmp_path)
    assert result.returncode == 0
    safety = _manifest(tmp_path)["safety"]
    for flag in [
        "full_html_saved",
        "html_body_saved",
        "full_next_data_saved",
        "raw_json_write_performed",
        "db_write_performed",
    ]:
        assert safety[flag] is False


def test_no_scheduler_no_feature_parse(tmp_path):
    result = _run(tmp_path)
    assert result.returncode == 0
    safety = _manifest(tmp_path)["safety"]
    assert safety["scheduler_enabled"] is False
    assert safety["feature_parse_performed"] is False


def test_no_browser_captcha_proxy(tmp_path):
    result = _run(tmp_path)
    assert result.returncode == 0
    safety = _manifest(tmp_path)["safety"]
    assert safety["browser_automation_performed"] is False
    assert safety["captcha_bypass_performed"] is False
    assert safety["proxy_rotation_performed"] is False


def test_readiness_blocked(tmp_path):
    result = _run(tmp_path)
    assert result.returncode == 0
    readiness = _manifest(tmp_path)["raw_write_readiness"]
    assert readiness["json_validated_count"] == 0
    assert readiness["raw_write_eligible_count"] == 0
    assert readiness["raw_write_blocked_until_json_validated"] is True


def test_recommended_next_safe(tmp_path):
    result = _run(tmp_path)
    assert result.returncode == 0
    rec = _manifest(tmp_path)["recommended_next_phase"]
    assert "DIRECT-RAW-WRITE" not in rec
    assert "RAW-JSON-WRITE" not in rec


def test_checker_passes(tmp_path):
    result = _run(tmp_path)
    assert result.returncode == 0
    cr = subprocess.run(
        [sys.executable, str(CHECKER)], cwd=ROOT, text=True, capture_output=True, check=False
    )
    assert cr.returncode == 0, f"checker failed: {cr.stderr}"
