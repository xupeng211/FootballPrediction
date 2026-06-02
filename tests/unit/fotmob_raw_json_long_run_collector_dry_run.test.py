"""Tests for the FotMob raw JSON long-run collector dry-run artifacts.

lifecycle: permanent
phase: FOTMOB-RAW-JSON-LONG-RUN-COLLECTOR-DRY-RUN
"""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
FIXTURE_PATH = REPO_ROOT / "docs/_fixtures/fotmob_long_run_collector_dry_run_targets.json"
HELPER_PATH = REPO_ROOT / "scripts/ops/fotmob_raw_json_long_run_collector_dry_run.py"
MANIFEST_PATH = (
    REPO_ROOT / "docs/_manifests/fotmob_raw_json_long_run_collector_dry_run_manifest.json"
)
REPORT_PATH = REPO_ROOT / "docs/_reports/FOTMOB_RAW_JSON_LONG_RUN_COLLECTOR_DRY_RUN.md"
DESIGN_PATH = REPO_ROOT / "docs/data/FOTMOB_RAW_JSON_LONG_RUN_COLLECTOR_DRY_RUN_DESIGN.md"


def _text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _json(path: Path) -> dict:
    return json.loads(_text(path))


def _load_helper():
    spec = importlib.util.spec_from_file_location(
        "fotmob_raw_json_long_run_collector_dry_run", HELPER_PATH
    )
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


# ---------------------------------------------------------------------------
# File existence
# ---------------------------------------------------------------------------
def test_fixture_exists():
    assert FIXTURE_PATH.exists(), "fixture 文件必须存在"


def test_helper_exists():
    assert HELPER_PATH.exists(), "helper 脚本必须存在"


def test_design_doc_exists():
    assert DESIGN_PATH.exists(), "design doc 必须存在"


def test_dry_run_manifest_and_report_exist():
    assert MANIFEST_PATH.exists(), "dry-run manifest 必须存在"
    assert REPORT_PATH.exists(), "dry-run report 必须存在"


# ---------------------------------------------------------------------------
# Manifest content
# ---------------------------------------------------------------------------
def test_manifest_schema_version():
    m = _json(MANIFEST_PATH)
    assert "schema_version" in m
    assert "dry_run_v1" in m["schema_version"]


def test_manifest_has_run_id():
    m = _json(MANIFEST_PATH)
    assert "run_id" in m
    assert m["run_id"]


def test_manifest_counts():
    m = _json(MANIFEST_PATH)
    assert m["input_target_count"] == 14
    assert m["selected_target_count"] > 0
    assert m["skipped_target_count"] > 0
    assert m["selected_target_count"] + m["skipped_target_count"] == m["input_target_count"]


def test_manifest_has_budget():
    m = _json(MANIFEST_PATH)
    assert m["request_budget"] == 10
    assert m["per_team_budget"] == 5
    assert m["per_competition_budget"] == 4


def test_manifest_has_selected_targets():
    m = _json(MANIFEST_PATH)
    targets = m["selected_targets"]
    assert len(targets) == m["selected_target_count"]
    for t in targets:
        assert "source_match_id" in t
        assert "team_names" in t
        assert "competition_name" in t
        assert "competition_type" in t
        assert "priority" in t
        assert "match_date" in t


def test_manifest_has_skipped_targets():
    m = _json(MANIFEST_PATH)
    skipped = m["skipped_targets"]
    assert len(skipped) == m["skipped_target_count"]
    for t in skipped:
        assert "skip_reason" in t


def test_manifest_has_no_raw_json_body():
    """Manifest must NOT contain raw JSON payloads."""
    manifest_text = _text(MANIFEST_PATH)
    # No __NEXT_DATA__ in manifest
    assert "__NEXT_DATA__" not in manifest_text
    # No pageProps content in manifest
    assert "pageProps" not in manifest_text.lower()


def test_manifest_has_stop_policy():
    m = _json(MANIFEST_PATH)
    policy = m["stop_policy"]
    assert policy["stop_on_403"] is True
    assert policy["stop_on_429"] is True
    assert policy["stop_on_captcha"] is True
    assert policy["stop_on_unexpected_html"] is True
    assert policy["stop_on_schema_shift"] is True
    assert policy["no_retry_storm"] is True
    assert policy["no_proxy_rotation"] is True
    assert policy["no_anti_bot_bypass"] is True
    assert policy["no_browser_automation"] is True


def test_manifest_coverage_flags_are_present():
    coverage = _json(MANIFEST_PATH)["coverage"]
    required_cases = {
        "club_calendar_case_present",
        "national_team_case_present",
        "domestic_cup_case_present",
        "continental_club_case_present",
        "international_qualifier_case_present",
        "nations_league_case_present",
        "japanese_club_case_present",
        "secondary_league_case_present",
        "man_united_cross_competition_present",
        "england_national_team_present",
    }
    for key in required_cases:
        assert coverage[key] is True, f"coverage.{key} 应为 True"
    # friendly_case_present may be False under tight budget; fixture still has it


def test_manifest_safety_flags_are_false():
    safety = _json(MANIFEST_PATH)["safety"]
    assert safety["network_fetch_performed"] is False
    assert safety["db_write_performed"] is False
    assert safety["raw_json_write_performed"] is False
    assert safety["feature_parse_performed"] is False
    assert safety["scheduler_enabled"] is False
    assert safety["raw_write_ready_marked"] is False


# ---------------------------------------------------------------------------
# Selection logic
# ---------------------------------------------------------------------------
def test_selected_targets_exclude_stored():
    """raw_json_status=stored targets must be skipped."""
    skipped = _json(MANIFEST_PATH)["skipped_targets"]
    stored_skip = [t for t in skipped if "stored" in t.get("raw_json_status", "")]
    assert len(stored_skip) > 0, "至少有一个 stored target 被跳过"


def test_selected_targets_exclude_blocked_by_default():
    """target_state=blocked must be skipped by default."""
    skipped = _json(MANIFEST_PATH)["skipped_targets"]
    blocked_skip = [t for t in skipped if t.get("target_state") == "blocked"]
    assert len(blocked_skip) > 0, "至少有一个 blocked target 被跳过"


def test_request_budget_applied():
    m = _json(MANIFEST_PATH)
    assert m["selected_target_count"] <= m["request_budget"], (
        f"选中数量 {m['selected_target_count']} 不应超过预算 {m['request_budget']}"
    )


def test_per_team_budget_applied():
    """No team should exceed per_team_budget in selected targets."""
    m = _json(MANIFEST_PATH)
    per_team = m["per_team_budget"]
    selected = m["selected_targets"]

    team_counts: dict[str, int] = {}
    for t in selected:
        for name in t.get("team_names", []):
            team_counts[name] = team_counts.get(name, 0) + 1
    for tid, count in team_counts.items():
        assert count <= per_team, f"Team {tid} 出现 {count} 次超过 per_team_budget={per_team}"


def test_per_competition_budget_applied():
    """No competition should exceed per_competition_budget in selected targets."""
    m = _json(MANIFEST_PATH)
    per_comp = m["per_competition_budget"]
    selected = m["selected_targets"]

    comp_counts: dict[str, int] = {}
    for t in selected:
        comp = t.get("competition_name", "")
        comp_counts[comp] = comp_counts.get(comp, 0) + 1
    for comp, count in comp_counts.items():
        assert count <= per_comp, (
            f"Competition {comp} 出现 {count} 次超过 per_competition_budget={per_comp}"
        )


# ---------------------------------------------------------------------------
# Coverage
# ---------------------------------------------------------------------------
def test_man_united_cross_competition_present():
    selected = _json(MANIFEST_PATH)["selected_targets"]
    cases = {t.get("team_calendar_case", "") for t in selected}
    man_cases = [c for c in cases if "man_united" in c.lower()]
    assert len(man_cases) > 0, "Manchester United 跨赛事目标必须存在"


def test_national_team_present():
    coverage = _json(MANIFEST_PATH)["coverage"]
    assert coverage["national_team_case_present"] is True


def test_domestic_cup_present():
    coverage = _json(MANIFEST_PATH)["coverage"]
    assert coverage["domestic_cup_case_present"] is True


def test_continental_club_present():
    coverage = _json(MANIFEST_PATH)["coverage"]
    assert coverage["continental_club_case_present"] is True


def test_japanese_club_present():
    coverage = _json(MANIFEST_PATH)["coverage"]
    assert coverage["japanese_club_case_present"] is True


def test_secondary_league_present():
    coverage = _json(MANIFEST_PATH)["coverage"]
    assert coverage["secondary_league_case_present"] is True


def test_international_qualifier_present():
    coverage = _json(MANIFEST_PATH)["coverage"]
    assert coverage["international_qualifier_case_present"] is True


# ---------------------------------------------------------------------------
# Report content
# ---------------------------------------------------------------------------
def test_report_states_no_live_fetch():
    report = _text(REPORT_PATH)
    assert "没有 live fetch" in report


def test_report_states_no_db_write():
    report = _text(REPORT_PATH)
    assert "没有 DB write" in report


def test_report_states_no_raw_json_write():
    report = _text(REPORT_PATH)
    assert "没有 raw JSON write" in report


def test_report_states_no_feature_parse():
    report = _text(REPORT_PATH)
    assert "没有 feature parse" in report


def test_report_states_no_scheduler():
    report = _text(REPORT_PATH)
    assert "没有 scheduler" in report


def test_report_has_stop_policy():
    report = _text(REPORT_PATH)
    assert "Stop Policy" in report or "stop_on_403" in report.lower()


def test_report_has_recommended_next_phase():
    report = _text(REPORT_PATH)
    assert "FOTMOB-RAW-JSON-LONG-RUN-COLLECTOR-DRY-RUN-REVIEW" in report


def test_report_has_remaining_gaps():
    report = _text(REPORT_PATH)
    assert "Remaining Gaps" in report


def test_report_fixture_validation():
    """Validation checks from helper should be present in report."""
    report = _text(REPORT_PATH)
    assert "验证" in report  # Chinese for validation


# ---------------------------------------------------------------------------
# Static safety — no forbidden code paths in the helper script
# ---------------------------------------------------------------------------
def test_helper_no_network_fetch():
    """Helper script must not contain forbidden network fetch patterns."""
    code = _text(HELPER_PATH)
    forbidden = [
        "requests.get",
        "requests.post",
        "requests.put",
        "httpx.get",
        "httpx.post",
        "urllib.request",
        "fetch(",
        "socket.create_connection",
    ]
    for pattern in forbidden:
        assert pattern not in code, f"Helper script must not contain '{pattern}'"


def test_helper_no_db_write():
    code = _text(HELPER_PATH)
    forbidden = [
        "INSERT ",
        "UPDATE ",
        "DELETE ",
        "TRUNCATE ",
        "DROP ",
        "psycopg2",
        "asyncpg",
        "sqlalchemy",
        "engine.connect",
        "session.execute",
    ]
    for pattern in forbidden:
        assert pattern not in code, f"Helper script must not contain '{pattern}'"


def test_helper_no_raw_json_write():
    code = _text(HELPER_PATH)
    forbidden = [
        "fotmob_raw_match_payloads",
        "next_data_json",
        "page_props_json",
        "raw_payload_file",
    ]
    for pattern in forbidden:
        assert pattern not in code, f"Helper script must not contain '{pattern}'"


def test_helper_no_browser_automation():
    code = _text(HELPER_PATH)
    forbidden = [
        "playwright",
        "chromium",
        "selenium",
        "browser.launch",
        "browser.new_page",
    ]
    for pattern in forbidden:
        assert pattern not in code, f"Helper script must not contain '{pattern}'"


def test_helper_no_raw_write_ready_true():
    code = _text(HELPER_PATH)
    assert "raw_write_ready" not in code.lower() or (
        "raw_write_ready_marked" in code and "false" in code.lower()
    ), "Helper must not set raw_write_ready=true"


def test_helper_no_scheduler_enable():
    code = _text(HELPER_PATH)
    assert "scheduler" not in code.lower() or (
        "scheduler_enabled" in code and "false" in code.lower()
    ), "Helper must not enable scheduler"


# ---------------------------------------------------------------------------
# Fixture integrity
# ---------------------------------------------------------------------------
def test_fixture_has_14_targets():
    fixture = _json(FIXTURE_PATH)
    assert len(fixture["targets"]) == 14


def test_fixture_has_no_raw_json():
    """Fixture must be metadata-only — no raw JSON payloads."""
    fixture_text = _text(FIXTURE_PATH)
    assert "__NEXT_DATA__" not in fixture_text
    assert "pageProps" not in fixture_text.lower()
    assert "raw_payload" not in fixture_text.lower()


def test_fixture_has_man_united_targets():
    fixture = _json(FIXTURE_PATH)
    mun_targets = [
        t for t in fixture["targets"] if "man_united" in t.get("team_calendar_case", "").lower()
    ]
    assert len(mun_targets) >= 4, f"Manchester United targets >= 4, got {len(mun_targets)}"


def test_fixture_has_england_national_targets():
    fixture = _json(FIXTURE_PATH)
    eng_targets = [
        t
        for t in fixture["targets"]
        if "england_national" in t.get("team_calendar_case", "").lower()
    ]
    assert len(eng_targets) >= 3, f"England national targets >= 3, got {len(eng_targets)}"


def test_fixture_has_japanese_club_targets():
    fixture = _json(FIXTURE_PATH)
    jpn_targets = [
        t for t in fixture["targets"] if "japanese_club" in t.get("team_calendar_case", "").lower()
    ]
    assert len(jpn_targets) >= 2, f"Japanese club targets >= 2, got {len(jpn_targets)}"


def test_fixture_has_secondary_league_targets():
    fixture = _json(FIXTURE_PATH)
    sec_targets = [
        t
        for t in fixture["targets"]
        if "secondary_league" in t.get("team_calendar_case", "").lower()
    ]
    assert len(sec_targets) >= 2, f"Secondary league targets >= 2, got {len(sec_targets)}"


def test_fixture_has_blocked_target():
    fixture = _json(FIXTURE_PATH)
    blocked = [t for t in fixture["targets"] if t.get("target_state") == "blocked"]
    assert len(blocked) >= 1, "Must have at least 1 blocked target for skip logic testing"


def test_fixture_has_stored_target():
    fixture = _json(FIXTURE_PATH)
    stored = [t for t in fixture["targets"] if t.get("raw_json_status") == "stored"]
    assert len(stored) >= 1, "Must have at least 1 stored target for skip logic testing"


# ---------------------------------------------------------------------------
# Helper module static validation
# ---------------------------------------------------------------------------
def test_helper_module_loads():
    module = _load_helper()
    assert module is not None


def test_helper_constants():
    module = _load_helper()
    assert module.SELECTABLE_STATES
    assert "pending_raw_fetch" in module.SELECTABLE_STATES
    assert "blocked" not in module.SELECTABLE_STATES


def test_helper_classify_targets():
    module = _load_helper()
    targets = [
        {
            "source_match_id": "t1",
            "target_state": "pending_raw_fetch",
            "raw_json_status": "missing",
            "priority": 5,
        },
        {
            "source_match_id": "t2",
            "target_state": "blocked",
            "raw_json_status": "missing",
            "priority": 3,
        },
        {
            "source_match_id": "t3",
            "target_state": "raw_json_stored",
            "raw_json_status": "stored",
            "priority": 1,
        },
        {
            "source_match_id": "t4",
            "target_state": "pending_raw_fetch",
            "raw_json_status": "failed",
            "priority": 10,
        },
    ]
    selectable, skipped = module.classify_targets(targets)
    assert len(selectable) == 2
    assert len(skipped) == 2
    assert selectable[0]["source_match_id"] == "t1"  # priority 5 before 10
    assert selectable[1]["source_match_id"] == "t4"


def test_helper_apply_budget():
    module = _load_helper()
    targets = [
        {"source_match_id": "a", "team_names": ["T1"], "competition_name": "C1", "priority": 1},
        {"source_match_id": "b", "team_names": ["T1"], "competition_name": "C1", "priority": 2},
        {"source_match_id": "c", "team_names": ["T1"], "competition_name": "C1", "priority": 3},
        {"source_match_id": "d", "team_names": ["T2"], "competition_name": "C1", "priority": 4},
    ]
    # per_team_budget=2, per_competition_budget=3, request_budget=10
    selected, skipped = module.apply_budget(targets, 10, 2, 3)
    # T1 has 3 targets (a,b,c), per_team_budget=2 limits T1 to 2
    # T2 has 1 target (d), within budget
    # C1 has per_competition_budget=3, so a,b,d are selected
    assert len(selected) == 3
    assert len(skipped) == 1
    # d (T2) should be selected, a and b for T1 selected, c skipped (T1 exhausted)
    selected_ids = [t["source_match_id"] for t in selected]
    assert "a" in selected_ids
    assert "b" in selected_ids
    assert "c" not in selected_ids
    assert "d" in selected_ids


def test_helper_validate_fixture():
    module = _load_helper()
    targets = [
        {
            "source": "fotmob",
            "source_match_id": "m1",
            "team_names": ["Manchester United"],
            "team_type": "club",
            "competition_name": "Premier League",
            "competition_type": "league",
            "team_calendar_case": "man_united_all_competitions",
            "target_state": "pending_raw_fetch",
            "raw_json_status": "missing",
            "priority": 10,
            "match_date": "2026-01-01T00:00:00Z",
        },
    ]
    errors = module.validate_fixture(targets)
    # Should have errors for missing coverage categories
    assert len(errors) > 0, "至少有几个 coverage 缺失警告"


def test_manifest_recommended_next_phase():
    m = _json(MANIFEST_PATH)
    assert m["recommended_next_phase"] == "FOTMOB-RAW-JSON-LONG-RUN-COLLECTOR-DRY-RUN-REVIEW"


def test_design_doc_contains_dry_run_scenarios():
    design = _text(DESIGN_PATH)
    assert "dry-run" in design.lower()
    assert "dry run" in design.lower() or "dry-run" in design.lower()


def test_design_doc_contains_no_network_no_db():
    design = _text(DESIGN_PATH)
    assert "no network fetch" in design.lower()
    assert "no db write" in design.lower()
    assert "no raw json write" in design.lower()


def test_report_contains_man_united_example():
    report = _text(REPORT_PATH)
    assert "Manchester United" in report


def test_report_contains_england_example():
    report = _text(REPORT_PATH)
    assert "England" in report
