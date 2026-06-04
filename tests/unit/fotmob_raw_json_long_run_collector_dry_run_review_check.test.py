"""Tests for the FotMob raw JSON long-run collector dry-run review artifacts.

lifecycle: permanent
phase: FOTMOB-RAW-JSON-LONG-RUN-COLLECTOR-DRY-RUN-REVIEW
"""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
REVIEW_REPORT_PATH = (
    REPO_ROOT / "docs/_reports/FOTMOB_RAW_JSON_LONG_RUN_COLLECTOR_DRY_RUN_REVIEW.md"
)
REVIEW_MANIFEST_PATH = (
    REPO_ROOT / "docs/_manifests/fotmob_raw_json_long_run_collector_dry_run_review_manifest.json"
)
REVIEW_HELPER_PATH = (
    REPO_ROOT / "scripts/ops/fotmob_raw_json_long_run_collector_dry_run_review_check.py"
)
DRY_RUN_MANIFEST_PATH = (
    REPO_ROOT / "docs/_manifests/fotmob_raw_json_long_run_collector_dry_run_manifest.json"
)
DRY_RUN_REPORT_PATH = REPO_ROOT / "docs/_reports/FOTMOB_RAW_JSON_LONG_RUN_COLLECTOR_DRY_RUN.md"

REVIEWED_PR = 1425


def _text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _json(path: Path) -> dict:
    return json.loads(_text(path))


def _load_helper():
    spec = importlib.util.spec_from_file_location(
        "fotmob_raw_json_long_run_collector_dry_run_review_check", REVIEW_HELPER_PATH
    )
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


# ---------------------------------------------------------------------------
# File existence
# ---------------------------------------------------------------------------
def test_review_artifacts_exist():
    assert REVIEW_REPORT_PATH.exists(), "review report must exist"
    assert REVIEW_MANIFEST_PATH.exists(), "review manifest must exist"
    assert REVIEW_HELPER_PATH.exists(), "review helper must exist"


def test_dry_run_artifacts_still_exist():
    assert DRY_RUN_MANIFEST_PATH.exists(), "original dry-run manifest must exist"
    assert DRY_RUN_REPORT_PATH.exists(), "original dry-run report must exist"


# ---------------------------------------------------------------------------
# Review manifest content
# ---------------------------------------------------------------------------
def test_review_manifest_metadata():
    m = _json(REVIEW_MANIFEST_PATH)
    assert m["reviewed_pr"] == REVIEWED_PR
    assert m["dry_run_collector_status"] == "pass"
    assert m["input_target_count"] == 14
    assert m["selected_target_count"] == 10
    assert m["skipped_target_count"] == 4
    assert m["request_budget"] == 10
    assert m["per_team_budget"] == 5
    assert m["per_competition_budget"] == 4


def test_review_manifest_coverage_flags():
    flags = _json(REVIEW_MANIFEST_PATH)["coverage_flags"]
    for key, value in flags.items():
        assert value is True, f"coverage_flags.{key} 应为 True"


def test_review_manifest_budget_review():
    budget = _json(REVIEW_MANIFEST_PATH)["budget_review"]
    assert budget["request_budget_respected"] is True
    assert budget["per_team_budget_respected"] is True
    assert budget["per_competition_budget_respected"] is True


def test_review_manifest_stop_policy():
    policy = _json(REVIEW_MANIFEST_PATH)["stop_policy_review"]
    for key, value in policy.items():
        assert value is True, f"stop_policy.{key} 应为 True"


def test_review_manifest_safety_flags_are_false():
    safety = _json(REVIEW_MANIFEST_PATH)["safety"]
    assert safety["network_fetch_performed"] is False
    assert safety["db_write_performed"] is False
    assert safety["raw_json_write_performed"] is False
    assert safety["feature_parse_performed"] is False
    assert safety["scheduler_enabled"] is False
    assert safety["raw_write_ready_marked"] is False


def test_review_manifest_has_remaining_gaps():
    gaps = _json(REVIEW_MANIFEST_PATH)["remaining_gaps"]
    assert len(gaps) > 0
    assert any("real_registry_seed" in g for g in gaps)
    assert any("live_fetch" in g for g in gaps)
    assert any("raw_json_write" in g for g in gaps)
    assert any("scheduler" in g for g in gaps)


def test_review_manifest_recommended_next_phase():
    phase = _json(REVIEW_MANIFEST_PATH)["recommended_next_phase"]
    assert "REGISTRY-SEED-DRY-RUN" in phase or "REGISTRY_SEED_DRY_RUN" in phase


# ---------------------------------------------------------------------------
# Review report content
# ---------------------------------------------------------------------------
def test_review_report_has_phase():
    report = _text(REVIEW_REPORT_PATH)
    assert "FOTMOB-RAW-JSON-LONG-RUN-COLLECTOR-DRY-RUN-REVIEW" in report


def test_review_report_has_reviewed_pr():
    report = _text(REVIEW_REPORT_PATH)
    assert "1425" in report


def test_review_report_dry_run_collector_status_pass():
    report = _text(REVIEW_REPORT_PATH)
    assert "dry_run_collector_status" in report
    assert "pass" in report


def test_review_report_no_live_fetch_review():
    report = _text(REVIEW_REPORT_PATH)
    assert "No-live-fetch" in report or "no-live-fetch" in report.lower()
    assert "网络请求" in report or "网络调用" in report


def test_review_report_no_write_review():
    report = _text(REVIEW_REPORT_PATH)
    assert "No-write" in report or "no-write" in report.lower() or "数据库写入" in report


def test_review_report_fixture_coverage_review():
    report = _text(REVIEW_REPORT_PATH)
    assert (
        "Fixture Coverage" in report
        or "fixture coverage" in report.lower()
        or "Fixture 覆盖" in report
    )


def test_review_report_selection_logic_review():
    report = _text(REVIEW_REPORT_PATH)
    assert (
        "Selection Logic" in report or "selection logic" in report.lower() or "选择逻辑" in report
    )


def test_review_report_budget_review():
    report = _text(REVIEW_REPORT_PATH)
    assert "Budget Review" in report or "budget review" in report.lower() or "预算" in report


def test_review_report_stop_policy_review():
    report = _text(REVIEW_REPORT_PATH)
    assert "Stop Policy" in report or "stop policy" in report.lower()


def test_review_report_business_fit():
    report = _text(REVIEW_REPORT_PATH)
    assert "Business Fit" in report or "业务适配" in report


def test_review_report_remaining_gaps():
    report = _text(REVIEW_REPORT_PATH)
    assert "Remaining Gaps" in report


def test_review_report_recommended_next_phase():
    report = _text(REVIEW_REPORT_PATH)
    assert "Recommended Next Phase" in report or "推荐下一阶段" in report


def test_review_report_safe_next_phase():
    """Next phase is registry-seed-dry-run or one-day preflight — not direct live fetch."""
    report = _text(REVIEW_REPORT_PATH)
    assert "REGISTRY-SEED-DRY-RUN" in report or "ONE-DAY" in report
    # Should NOT recommend direct unlimited live fetch
    assert "直接" not in report or "不允许直接" in report or "当前阶段不允许" in report


# ---------------------------------------------------------------------------
# Review helper validation
# ---------------------------------------------------------------------------
def test_review_helper_loads():
    module = _load_helper()
    assert module is not None


def test_review_helper_passes():
    result = _load_helper().run_checks()
    assert result["verdict"] == "pass"
    assert result["reviewed_pr"] == REVIEWED_PR
    assert result["network_fetch_performed"] is False
    assert result["db_data_write_performed"] is False
    assert result["raw_json_write_performed"] is False
    assert result["feature_parse_performed"] is False
    assert result["scheduler_enabled"] is False
    assert result["raw_write_ready_marked"] is False


def test_review_helper_no_network_code():
    code = _text(REVIEW_HELPER_PATH)
    # Check for actual function calls, not string literals in forbidden-list checks
    forbidden = [
        "requests.get(",
        "requests.post(",
        "httpx.get(",
        "httpx.post(",
        "aiohttp.ClientSession",
        "fetch(url",
        "fetch( url",
        "playwright.chromium",
        "chromium.launch",
    ]
    for pattern in forbidden:
        assert pattern not in code, f"Review helper must not contain '{pattern}'"


def test_review_helper_no_db_write_code():
    code = _text(REVIEW_HELPER_PATH)
    # Check for actual SQL execution patterns, not string literals in forbidden-list checks
    forbidden = [
        "engine.execute",
        "cursor.execute",
        "session.execute",
        "psycopg2",
        "asyncpg",
    ]
    for pattern in forbidden:
        assert pattern not in code, f"Review helper must not contain '{pattern}'"


# ---------------------------------------------------------------------------
# Review manifest has no raw JSON
# ---------------------------------------------------------------------------
def test_review_manifest_has_no_raw_json():
    manifest_text = _text(REVIEW_MANIFEST_PATH)
    assert "__NEXT_DATA__" not in manifest_text
    assert "pageProps" not in manifest_text.lower()


# ---------------------------------------------------------------------------
# Original dry-run manifest consistency check
# ---------------------------------------------------------------------------
def test_original_manifest_request_budget_respected():
    m = _json(DRY_RUN_MANIFEST_PATH)
    assert m["selected_target_count"] <= m["request_budget"]


def test_original_manifest_per_team_budget_respected():
    m = _json(DRY_RUN_MANIFEST_PATH)
    per_team = m["per_team_budget"]
    team_counts: dict[str, int] = {}
    for t in m["selected_targets"]:
        for name in t.get("team_names", []):
            team_counts[name] = team_counts.get(name, 0) + 1
    for count in team_counts.values():
        assert count <= per_team


def test_original_manifest_per_competition_budget_respected():
    m = _json(DRY_RUN_MANIFEST_PATH)
    per_comp = m["per_competition_budget"]
    comp_counts: dict[str, int] = {}
    for t in m["selected_targets"]:
        comp = t.get("competition_name", "")
        comp_counts[comp] = comp_counts.get(comp, 0) + 1
    for count in comp_counts.values():
        assert count <= per_comp
