"""Tests for FotMob safe parser schema reuse plan no-write.

lifecycle: permanent
"""

from __future__ import annotations

import json
from pathlib import Path
import subprocess
import sys

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts/ops"))

SCRIPT = ROOT / "scripts/ops/fotmob_safe_parser_schema_reuse_plan_no_write.py"
CHECKER = ROOT / "scripts/ops/fotmob_safe_parser_schema_reuse_plan_no_write_check.py"

import fotmob_safe_parser_schema_reuse_plan_no_write as mod  # noqa: E402

HIGH_RISK_PATHS = [
    "SessionManager",
    "AutoAuthManager",
    "SessionWarmer",
    "StealthNavigator",
    "StealthFingerprint",
    "enhanced_stealth_config",
    "FotMobApiClient",
    "BrowserFactory",
    "ContextPoolManager",
    "NetworkInterceptor",
    "archive_vault_2026",
    "legacy_v446",
    "FotMobExtractor",
]


def _base_argv(tmp_path: Path) -> list[str]:
    return [
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


def _run(tmp_path: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(SCRIPT), *_base_argv(tmp_path)],
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


def test_manifest_generated(tmp_path):
    assert _run(tmp_path).returncode == 0
    m = _manifest(tmp_path)
    assert m["mode"] == "offline_safe_parser_schema_reuse_plan"
    assert m["phase"] == "SAFE-PARSER-SCHEMA-REUSE-PLAN-NO-WRITE"


def test_report_generated(tmp_path):
    assert _run(tmp_path).returncode == 0
    assert (tmp_path / "r.md").exists()


def test_review_generated(tmp_path):
    assert _run(tmp_path).returncode == 0
    assert (tmp_path / "rv.md").exists()


def test_next_plan_generated(tmp_path):
    assert _run(tmp_path).returncode == 0
    assert (tmp_path / "n.md").exists()


def test_safe_reuse_includes_parsers(tmp_path):
    assert _run(tmp_path).returncode == 0
    safe = _manifest(tmp_path)["safe_reuse_assets"]
    categories = {a["category"] for a in safe}
    assert "parser" in categories


def test_safe_reuse_includes_schema(tmp_path):
    assert _run(tmp_path).returncode == 0
    safe = _manifest(tmp_path)["safe_reuse_assets"]
    categories = {a["category"] for a in safe}
    assert "schema" in categories


def test_safe_reuse_includes_fixture(tmp_path):
    assert _run(tmp_path).returncode == 0
    safe = _manifest(tmp_path)["safe_reuse_assets"]
    categories = {a["category"] for a in safe}
    assert "fixture" in categories


def test_read_only_includes_browser_session(tmp_path):
    assert _run(tmp_path).returncode == 0
    risky = _manifest(tmp_path)["read_only_reference_assets"]
    categories = {a["category"] for a in risky}
    assert any("browser" in c or "anti_bot" in c for c in categories)


def test_no_high_risk_in_safe_reuse(tmp_path):
    assert _run(tmp_path).returncode == 0
    safe = _manifest(tmp_path)["safe_reuse_assets"]
    for asset in safe:
        path = asset.get("path", "")
        for risk_path in HIGH_RISK_PATHS:
            assert risk_path.lower() not in path.lower(), (
                f"{asset['asset_id']} ({path}) should not be in safe_reuse"
            )


def test_canonical_shape_includes_key_sections(tmp_path):
    assert _run(tmp_path).returncode == 0
    shape = _manifest(tmp_path)["canonical_payload_shape_plan"]
    required = shape.get("required_sections", [])
    for key in ["general", "header", "content.stats", "content.lineup", "content.events"]:
        assert key in required, f"{key} should be in required sections"


def test_raw_write_allowed_false(tmp_path):
    assert _run(tmp_path).returncode == 0
    gate = _manifest(tmp_path)["raw_write_gate"]
    assert gate["raw_write_allowed"] is False


def test_db_write_allowed_false(tmp_path):
    assert _run(tmp_path).returncode == 0
    gate = _manifest(tmp_path)["raw_write_gate"]
    assert gate["db_write_allowed"] is False


def test_json_validated_zero(tmp_path):
    assert _run(tmp_path).returncode == 0
    gate = _manifest(tmp_path)["raw_write_gate"]
    assert gate["json_validated_count"] == 0


def test_raw_write_eligible_zero(tmp_path):
    assert _run(tmp_path).returncode == 0
    gate = _manifest(tmp_path)["raw_write_gate"]
    assert gate["raw_write_eligible_count"] == 0


def test_no_network(tmp_path):
    assert _run(tmp_path).returncode == 0
    safety = _manifest(tmp_path)["safety"]
    assert safety["network_fetch_performed"] is False
    assert safety["db_read_performed"] is False
    assert safety["db_write_performed"] is False


def test_no_browser_cookie_captcha_proxy(tmp_path):
    assert _run(tmp_path).returncode == 0
    safety = _manifest(tmp_path)["safety"]
    for flag in [
        "browser_automation_performed",
        "cookie_harvesting_performed",
        "captcha_bypass_performed",
        "proxy_rotation_performed",
    ]:
        assert safety[flag] is False


def test_recommended_next_safe(tmp_path):
    assert _run(tmp_path).returncode == 0
    rec = _manifest(tmp_path)["recommended_next_phase"]
    assert "DIRECT-RAW-WRITE" not in rec
    assert "RAW-JSON-WRITE" not in rec
    assert rec in mod.ALLOWED_NEXT


def test_historical_success_confirmed(tmp_path):
    assert _run(tmp_path).returncode == 0
    ctx = _manifest(tmp_path)["historical_success_context"]
    assert ctx["historical_success_confirmed"] is True
    assert ctx["historical_payload_is_match_detail"] is True


def test_enforce_safety_rejects_high_risk_in_safe():
    manifest = {
        "safe_reuse_assets": [
            {
                "asset_id": "bad",
                "path": "src/infrastructure/network/SessionManager.js",
                "category": "bad",
            }
        ],
        "safety": {},
        "raw_write_gate": {
            "raw_write_allowed": False,
            "json_validated_count": 0,
            "raw_write_eligible_count": 0,
        },
        "recommended_next_phase": mod.NEXT_PHASE_RECONSTRUCTION,
    }
    with pytest.raises(ValueError, match="HIGH-RISK"):
        mod.enforce_safety(manifest)


def test_checker_passes(tmp_path):
    assert _run(tmp_path).returncode == 0
    cr = subprocess.run(
        [sys.executable, str(CHECKER)], cwd=ROOT, text=True, capture_output=True, check=False
    )
    assert cr.returncode == 0, f"checker failed: {cr.stderr}"
