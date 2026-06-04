"""Tests for FotMob registry seed dry-run review artifacts.

lifecycle: permanent
phase: FOTMOB-RAW-JSON-LONG-RUN-COLLECTOR-REGISTRY-SEED-DRY-RUN-REVIEW
"""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
REVIEW_REPORT_PATH = REPO_ROOT / "docs/_reports/FOTMOB_REGISTRY_SEED_DRY_RUN_REVIEW.md"
REVIEW_MANIFEST_PATH = (
    REPO_ROOT / "docs/_manifests/fotmob_registry_seed_dry_run_review_manifest.json"
)
REVIEW_HELPER_PATH = REPO_ROOT / "scripts/ops/fotmob_registry_seed_dry_run_review_check.py"
MANIFEST_PATH = REPO_ROOT / "docs/_manifests/fotmob_registry_seed_dry_run_manifest.json"
SQL_PATH = REPO_ROOT / "docs/_reports/FOTMOB_REGISTRY_SEED_DRY_RUN_SQL_PREVIEW.sql"

REVIEWED_PR = 1427


def _text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _json(path: Path) -> dict:
    return json.loads(_text(path))


def _load_helper():
    spec = importlib.util.spec_from_file_location(
        "fotmob_registry_seed_dry_run_review_check", REVIEW_HELPER_PATH
    )
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


# File existence
def test_review_report_exists():
    assert REVIEW_REPORT_PATH.exists()


def test_review_manifest_exists():
    assert REVIEW_MANIFEST_PATH.exists()


def test_review_helper_exists():
    assert REVIEW_HELPER_PATH.exists()


# Review manifest
def test_review_manifest_metadata():
    m = _json(REVIEW_MANIFEST_PATH)
    assert m["reviewed_pr"] == REVIEWED_PR
    assert m["registry_seed_dry_run_status"] == "pass"


def test_review_manifest_counts():
    c = _json(REVIEW_MANIFEST_PATH)["counts"]
    assert c["teams"] == 18
    assert c["competitions"] == 10
    assert c["editions"] == 10
    assert c["participations"] == 11
    assert c["match_targets"] == 14
    assert c["match_target_teams"] == 28
    assert c["source_identities"] == 10
    assert c["selected"] == 10
    assert c["skipped"] == 4


def test_review_manifest_coverage():
    flags = _json(REVIEW_MANIFEST_PATH)["coverage_flags"]
    for key, value in flags.items():
        assert value is True, f"coverage_flags.{key} 应为 True"


def test_review_manifest_sql_safety():
    sql = _json(REVIEW_MANIFEST_PATH)["sql_preview_safety"]
    assert sql["has_dry_run_header"] is True
    assert sql["has_do_not_execute"] is True
    assert sql["all_inserts_commented"] is True
    assert sql["sql_executed_flag"] is False


def test_review_manifest_safety():
    s = _json(REVIEW_MANIFEST_PATH)["safety"]
    assert s["network_fetch_performed"] is False
    assert s["db_write_performed"] is False
    assert s["sql_executed"] is False
    assert s["raw_json_write_performed"] is False
    assert s["scheduler_enabled"] is False
    assert s["raw_write_ready_marked"] is False


def test_review_manifest_gaps():
    gaps = _json(REVIEW_MANIFEST_PATH)["remaining_gaps"]
    assert any("db_seed" in g or "registry_data" in g for g in gaps)
    assert any("live_fetch" in g for g in gaps)
    assert any("scheduler" in g for g in gaps)


def test_review_manifest_next_phase():
    phase = _json(REVIEW_MANIFEST_PATH)["recommended_next_phase"]
    assert "DEV-EXECUTION-NO-LIVE-FETCH" in phase


# Review report
def test_review_report_status():
    report = _text(REVIEW_REPORT_PATH)
    assert "registry_seed_dry_run_status" in report
    assert "pass" in report


def test_review_report_has_pr():
    assert "1427" in _text(REVIEW_REPORT_PATH)


def test_review_report_coverage_mentions():
    report = _text(REVIEW_REPORT_PATH)
    for name in ["Manchester United", "England", "Kashima Antlers", "Leeds United"]:
        assert name in report, f"Report must mention {name}"


def test_review_report_sql_safety():
    report = _text(REVIEW_REPORT_PATH)
    assert "SQL" in report
    assert "安全" in report or "safety" in report.lower()


def test_review_report_recommended_next_phase():
    report = _text(REVIEW_REPORT_PATH)
    assert "DEV-EXECUTION-NO-LIVE-FETCH" in report


# SQL preview
def test_sql_preview_has_header():
    sql = _text(SQL_PATH)
    assert "DRY-RUN SQL PREVIEW ONLY" in sql
    assert "DO NOT EXECUTE" in sql


def test_sql_preview_all_commented():
    sql = _text(SQL_PATH)
    for line in sql.split("\n"):
        if "INSERT INTO" in line:
            assert line.strip().startswith("--"), f"INSERT not commented: {line[:60]}"


# Review helper
def test_review_helper_passes():
    result = _load_helper().run_checks()
    assert result["verdict"] == "pass"
    assert result["reviewed_pr"] == REVIEWED_PR


def test_review_helper_no_network():
    code = _text(REVIEW_HELPER_PATH)
    for p in ["requests.get(url", "httpx.post(", "fetch(url", "playwright.chromium.launch"]:
        assert p not in code, f"Helper must not contain '{p}'"


# Manifest no raw JSON
def test_review_manifest_no_raw_json():
    text = _text(REVIEW_MANIFEST_PATH)
    assert "__NEXT_DATA__" not in text
    assert "pageProps" not in text.lower()
