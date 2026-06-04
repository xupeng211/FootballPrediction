"""Tests for FotMob target selection DB dry-run artifacts.

lifecycle: permanent
phase: FOTMOB-RAW-JSON-LONG-RUN-COLLECTOR-TARGET-SELECTION-DB-DRY-RUN
"""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPT_PATH = REPO_ROOT / "scripts/ops/fotmob_target_selection_db_dry_run.py"
CHECKER_PATH = REPO_ROOT / "scripts/ops/fotmob_target_selection_db_dry_run_check.py"
MANIFEST_PATH = REPO_ROOT / "docs/_manifests/fotmob_target_selection_db_dry_run_manifest.json"
REPORT_PATH = REPO_ROOT / "docs/_reports/FOTMOB_TARGET_SELECTION_DB_DRY_RUN.md"
REVIEW_REPORT_PATH = REPO_ROOT / "docs/_reports/FOTMOB_TARGET_SELECTION_DB_DRY_RUN_REVIEW.md"


def _text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _json(path: Path) -> dict:
    return json.loads(_text(path))


def _load_module(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_script_exists():
    assert SCRIPT_PATH.exists()


def test_checker_exists():
    assert CHECKER_PATH.exists()


def test_report_exists():
    assert REPORT_PATH.exists()


def test_review_report_exists():
    assert REVIEW_REPORT_PATH.exists()


def test_manifest_exists():
    assert MANIFEST_PATH.exists()


def test_production_guard_blocks_production_like_env():
    module = _load_module(SCRIPT_PATH, "fotmob_target_selection_db_dry_run")
    blocked, reasons = module.check_production_guard("prod-db.rds.amazonaws.com")
    assert blocked is True
    assert reasons


def test_db_dry_run_is_read_only():
    code = _text(SCRIPT_PATH).lower()
    assert "set_session(readonly=true" in code
    assert '"db_write_performed": false' in code
    assert '"production_db_write_performed": false' in code


def test_no_db_mutation_sql_execution():
    code = _text(SCRIPT_PATH).lower()
    for token in ["ins" + "ert ", "upd" + "ate ", "del" + "ete ", "trun" + "cate ", "dr" + "op "]:
        assert token not in code


def test_no_network_fetch_code():
    code = _text(SCRIPT_PATH)
    forbidden = [
        "requests" + ".get",
        "http" + "x",
        "aio" + "http",
        "axi" + "os",
        "fetch" + "(",
        "play" + "wright",
        "chrom" + "ium",
    ]
    for token in forbidden:
        assert token not in code


def test_manifest_target_counts():
    manifest = _json(MANIFEST_PATH)
    assert manifest["input_target_count"] == 14
    assert manifest["selected_target_count"] == 10
    assert manifest["skipped_target_count"] == 4


def test_budgets_respected():
    budgets = _json(MANIFEST_PATH)["budgets"]
    assert budgets["request_budget"] == 10
    assert budgets["per_team_budget"] == 5
    assert budgets["per_competition_budget"] == 4
    assert budgets["request_budget_respected"] is True
    assert budgets["per_team_budget_respected"] is True
    assert budgets["per_competition_budget_respected"] is True


def test_skip_reasons_include_required_categories():
    skip_reasons = set(_json(MANIFEST_PATH)["skip_reason_counts"])
    assert {"blocked", "stored", "budget_exhausted"}.issubset(skip_reasons)


def test_all_selected_have_source_identity():
    source_identity = _json(MANIFEST_PATH)["source_identity"]
    assert source_identity["all_selected_have_source_identity"] is True
    assert source_identity["unsupported_source_selected"] is False


def test_no_duplicate_selected_target():
    selected = _json(MANIFEST_PATH)["selected_targets"]
    source_match_ids = [target["source_match_id"] for target in selected]
    assert len(source_match_ids) == len(set(source_match_ids))


def test_full_calendar_counts_match_expected():
    counts = _json(MANIFEST_PATH)["team_full_calendar"]
    assert counts["manchester_united_target_count"] == 6
    assert counts["england_target_count"] == 4
    assert counts["kashima_antlers_target_count"] == 2
    assert counts["leeds_united_target_count"] == 2


def test_embedded_review_status_pass():
    review = _json(MANIFEST_PATH)["embedded_review"]
    assert review["target_selection_db_dry_run_status"] == "pass"


def test_checker_passes():
    checker = _load_module(CHECKER_PATH, "fotmob_target_selection_db_dry_run_check")
    result = checker.run_checks()
    assert result["verdict"] == "pass"


def test_safety_flags_false():
    manifest = _json(MANIFEST_PATH)
    assert manifest["db_read_performed"] is True
    assert manifest["db_write_performed"] is False
    assert manifest["production_db_write_performed"] is False
    safety = manifest["safety"]
    assert safety["network_fetch_performed"] is False
    assert safety["raw_json_write_performed"] is False
    assert safety["fotmob_raw_match_payloads_write_performed"] is False
    assert safety["raw_match_data_write_performed"] is False
    assert safety["feature_parse_performed"] is False
    assert safety["scheduler_enabled"] is False
    assert safety["raw_write_ready_marked"] is False


def test_reports_declare_safety_and_review():
    report = _text(REPORT_PATH)
    review_report = _text(REVIEW_REPORT_PATH)
    assert "no live fetch" in report
    assert "no DB write" in report
    assert "status: pass" in review_report
    assert "DB read-only check: pass" in review_report
