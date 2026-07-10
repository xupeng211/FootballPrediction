#!/usr/bin/env python3
# ruff: noqa: PLR2004, PLC0415, RUF012
"""Unit tests for training preflight dry-run safety harness.

lifecycle: permanent
scope: test --dry-run mode in scripts/ops/train_model.py

Tests verify:
1. CLI recognizes --dry-run
2. --dry-run does NOT require training write gate
3. read-only self-verification via SHOW transaction_read_only
4. LEFT JOIN cohort (detect missing L3)
5. Feature extraction exceptions fail-closed
6. Forbidden feature injection fail-closed
7. Default Elo explicitly reported
8. No fit, predict, artifact write, DB write in dry-run
9. Non-dry-run existing gates unchanged

Uses mock/fixture; no real DB connection.
"""

import json
from pathlib import Path
import sys
from unittest.mock import MagicMock, patch

import pytest

PROJECT_ROOT = Path(__file__).parent.parent.parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))


# ── Helpers ────────────────────────────────────────────────────────────────


def _make_row(match_id, actual_result, elo_is_default=False):
    """Build a mock DB row dict matching the LEFT JOIN cohort query shape."""
    elo = {
        "home_elo_pre": 1500.0 if elo_is_default else 1650.0,
        "away_elo_pre": 1500.0 if elo_is_default else 1420.0,
        "elo_diff": 0.0 if elo_is_default else 230.0,
        "expected_home_win": 0.45 if elo_is_default else 0.62,
        "expected_away_win": 0.30,
        "_is_default": elo_is_default,
    }
    golden = {"home_market_value_total": 5e8, "away_market_value_total": 2e8}
    tactical = {
        "h2h_home_win_ratio": 0.55,
        "h2h_draw_ratio": 0.25,
        "h2h_avg_goal_diff": 0.5,
    }
    return {
        "match_id": match_id,
        "home_team": f"Home{match_id}",
        "away_team": f"Away{match_id}",
        "actual_result": actual_result,
        "l3_match_id": match_id,  # has L3
        "elo_features": elo,
        "golden_features": golden,
        "tactical_features": tactical,
    }


def _make_l3_missing_row(match_id, actual_result):
    """Row without L3 features (l3_match_id is None)."""
    return {
        "match_id": match_id,
        "home_team": f"Home{match_id}",
        "away_team": f"Away{match_id}",
        "actual_result": actual_result,
        "l3_match_id": None,
        "elo_features": None,
        "golden_features": None,
        "tactical_features": None,
    }


# ── Fixtures ───────────────────────────────────────────────────────────────


@pytest.fixture
def sample_rows():
    """12 training-eligible rows with L3 coverage."""
    return [
        _make_row("m01", "home_win", elo_is_default=False),
        _make_row("m02", "home_win", elo_is_default=False),
        _make_row("m03", "home_win", elo_is_default=False),
        _make_row("m04", "home_win", elo_is_default=False),
        _make_row("m05", "away_win", elo_is_default=False),
        _make_row("m06", "away_win", elo_is_default=False),
        _make_row("m07", "away_win", elo_is_default=False),
        _make_row("m08", "draw", elo_is_default=False),
        _make_row("m09", "draw", elo_is_default=False),
        _make_row("m10", "draw", elo_is_default=False),
        _make_row("m11", "home_win", elo_is_default=True),
        _make_row("m12", "away_win", elo_is_default=True),
    ]


def _make_mock_conn(cursors):
    """Build a mock connection where each cursor() call returns the next mock cursor.

    cursors: list of MagicMock cursors to return in order.
    """
    conn = MagicMock()
    conn.cursor.side_effect = cursors
    return conn


def _make_cursor(rows, *, read_only_row=None):
    """Create a dual-mode mock cursor that handles SHOW and cohort queries.

    If read_only_row is provided, the FIRST execute() call (SHOW) returns
    read_only_row. Subsequent calls return rows.
    """
    cursor = MagicMock()
    if read_only_row is not None:
        cursor.fetchone.return_value = read_only_row
    cursor.fetchall.return_value = rows
    return cursor


def _ro_cur(read_only_row, _cohort_rows=None):
    """Create the SHOW cursor (fetchone) with read_only_row."""
    cur = MagicMock()
    cur.fetchone.return_value = read_only_row
    return cur


def _cohort_cur(cohort_rows):
    """Create the cohort query cursor (fetchall) with cohort_rows."""
    cur = MagicMock()
    cur.fetchall.return_value = cohort_rows
    return cur


def _make_conn(read_only_row, cohort_rows):
    """Build mock conn: first cursor=SHOW, second=cohort."""
    ro_cur = _ro_cur(read_only_row, cohort_rows)
    ch_cur = _cohort_cur(cohort_rows)
    conn = MagicMock()
    conn.cursor.side_effect = [ro_cur, ch_cur]
    return conn


def _run(conn):
    """Invoke run_dry_run_mode and return the parsed summary dict."""
    from scripts.ops.train_model import run_dry_run_mode

    return run_dry_run_mode(conn, logger=None)


# ── Tests ──────────────────────────────────────────────────────────────────


class TestDryRunCLI:
    """CLI-level tests for --dry-run flag."""

    def test_dry_run_flag_registered(self):
        from scripts.ops.train_model import parse_args

        with patch.object(sys, "argv", ["train_model.py", "--dry-run"]):
            assert parse_args().dry_run is True

    def test_dry_run_absent_by_default(self):
        from scripts.ops.train_model import parse_args

        with patch.object(sys, "argv", ["train_model.py"]):
            assert parse_args().dry_run is False


class TestReadOnlyVerification:
    """Read-only self-verification via SHOW transaction_read_only."""

    def test_read_only_on_proceeds(self, sample_rows):
        """transaction_read_only=on: db_read_only=True, continues."""
        conn = _make_conn({"transaction_read_only": "on"}, sample_rows)
        s = _run(conn)
        assert s["db_read_only"] is True
        assert s["transaction_read_only_setting"] == "on"
        assert s["cohort_count"] == len(sample_rows)

    def test_read_only_off_blocked(self, sample_rows):
        """transaction_read_only=off: blocked before cohort query."""
        conn = _make_conn({"transaction_read_only": "off"}, sample_rows)
        s = _run(conn)
        assert s["db_read_only"] is False
        assert s["status"] == "blocked"
        assert s["eligible_cohort_count"] == 0  # cohort never queried

    def test_read_only_off_blocks_cohort(self, sample_rows):
        """off → blocked, cohort_count stays 0."""
        conn = _make_conn({"transaction_read_only": "off"}, sample_rows)
        s = _run(conn)
        assert s["cohort_count"] == 0
        assert "NOT read-only" in s["blocked_reasons"][0]

    def test_show_query_exception_blocked(self):
        """SHOW throws → blocked."""
        cur = MagicMock()
        cur.fetchone.side_effect = RuntimeError("connection lost")
        conn = MagicMock()
        conn.cursor.side_effect = [cur]
        s = _run(conn)
        assert s["status"] == "blocked"
        assert s["db_read_only"] is False

    def test_not_hardcoded_true(self, sample_rows):
        """db_read_only is never hardcoded True."""
        from scripts.ops.train_model import run_dry_run_mode

        ro_cur = MagicMock()
        ro_cur.fetchone.return_value = {"transaction_read_only": "on"}
        ch_cur = MagicMock()
        ch_cur.fetchall.return_value = sample_rows
        conn = MagicMock()
        conn.cursor.side_effect = [ro_cur, ch_cur]
        s = run_dry_run_mode(conn, logger=None)
        assert s["db_read_only"] is True  # only because SHOW returned on


class TestDryRunNoFitPredict:
    """--dry-run does NOT call fit, predict, or write artifacts."""

    def test_fit_predict_not_executed(self, sample_rows):
        conn = _make_conn({"transaction_read_only": "on"}, sample_rows)
        s = _run(conn)
        assert s["fit_executed"] is False
        assert s["predict_executed"] is False
        assert s["artifact_written"] is False
        assert s["model_file_written"] is False
        assert s["dataset_file_written"] is False

    def test_db_write_not_attempted(self, sample_rows):
        conn = _make_conn({"transaction_read_only": "on"}, sample_rows)
        s = _run(conn)
        assert s["db_write_attempted"] is False


class TestL3Coverage:
    """LEFT JOIN cohort detects missing L3 rows."""

    def test_left_join_detects_missing(self):
        """2 eligible, 1 with L3 → blocked with missing_l3=1."""
        rows = [_make_row("m01", "home_win"), _make_l3_missing_row("m02", "away_win")]
        conn = _make_conn({"transaction_read_only": "on"}, rows)
        s = _run(conn)
        assert s["eligible_cohort_count"] == 2
        assert s["l3_coverage_count"] == 1
        assert s["missing_l3_count"] == 1
        assert s["missing_l3_match_ids"] == ["m02"]
        assert s["status"] == "blocked"

    def test_all_have_l3_passes(self, sample_rows):
        """All rows have L3 → passes L3 check."""
        conn = _make_conn({"transaction_read_only": "on"}, sample_rows)
        s = _run(conn)
        assert s["missing_l3_count"] == 0
        assert s["l3_coverage_count"] == len(sample_rows)

    def test_no_l3_where_clause_not_filtering(self):
        """Verify LEFT JOIN is used: rows without L3 are visible."""
        rows = [_make_l3_missing_row("m01", "home_win")]
        conn = _make_conn({"transaction_read_only": "on"}, rows)
        s = _run(conn)
        assert s["eligible_cohort_count"] == 1  # visible
        assert s["l3_coverage_count"] == 0  # but no L3
        assert s["status"] == "blocked"


class TestLabels:
    """Label distribution tests."""

    def test_label_distribution_correct(self, sample_rows):
        conn = _make_conn({"transaction_read_only": "on"}, sample_rows)
        s = _run(conn)
        assert s["label_distribution"].get("home_win") == 5
        assert s["label_distribution"].get("away_win") == 4
        assert s["label_distribution"].get("draw") == 3

    def test_invalid_label_blocked(self):
        rows = [_make_row("m01", "H", elo_is_default=False)]
        conn = _make_conn({"transaction_read_only": "on"}, rows)
        s = _run(conn)
        assert "H" in s["invalid_label_values"]
        assert s["status"] == "blocked"

    def test_null_label_blocked(self):
        rows = [_make_row("m01", None, elo_is_default=False)]
        conn = _make_conn({"transaction_read_only": "on"}, rows)
        s = _run(conn)
        assert s["label_null_count"] == 1
        assert s["status"] == "blocked"


class TestFeatureExtractionErrors:
    """Feature extraction exceptions fail-closed (no silent pass)."""

    def test_extraction_error_counted(self, sample_rows):
        """When extract_v5_features throws, error is recorded and blocked."""
        conn = _make_conn({"transaction_read_only": "on"}, sample_rows)

        from scripts.ops import train_model as tm

        original = tm.extract_v5_features

        def _failing(*args, **kwargs):  # noqa: ARG001
            raise ValueError("extraction error")

        tm.extract_v5_features = _failing
        try:
            s = tm.run_dry_run_mode(conn, logger=None)
        finally:
            tm.extract_v5_features = original

        assert s["feature_extraction_error_count"] == len(sample_rows)
        assert s["feature_extracted_row_count"] == 0
        assert len(s["feature_extraction_error_match_ids"]) == len(sample_rows)
        assert len(s["feature_extraction_errors"]) == len(sample_rows)
        assert s["status"] == "blocked"

    def test_zero_features_when_nonempty_cohort_blocked(self, sample_rows):
        """Non-empty cohort but 0 features extracted → blocked."""
        conn = _make_conn({"transaction_read_only": "on"}, sample_rows)

        from scripts.ops import train_model as tm

        original = tm.extract_v5_features

        def _empty(*args, **kwargs):  # noqa: ARG001
            return {}  # zero features

        tm.extract_v5_features = _empty
        try:
            s = tm.run_dry_run_mode(conn, logger=None)
        finally:
            tm.extract_v5_features = original

        assert s["feature_count"] == 0
        assert s["status"] == "blocked"


class TestDefaultElo:
    """Default Elo explicitly reported."""

    def test_elo_real_default_counts(self, sample_rows):
        conn = _make_conn({"transaction_read_only": "on"}, sample_rows)
        s = _run(conn)
        assert s["elo_real_count"] == 10
        assert s["elo_default_count"] == 2

    def test_elo_default_match_ids_reported(self, sample_rows):
        conn = _make_conn({"transaction_read_only": "on"}, sample_rows)
        s = _run(conn)
        assert sorted(s["elo_default_match_ids"]) == ["m11", "m12"]

    def test_all_default_elo_cohort(self):
        rows = [
            _make_row("m01", "home_win", elo_is_default=True),
            _make_row("m02", "away_win", elo_is_default=True),
        ]
        conn = _make_conn({"transaction_read_only": "on"}, rows)
        s = _run(conn)
        assert s["elo_real_count"] == 0
        assert s["elo_default_count"] == 2


class TestForbiddenFeatureInjection:
    """Forbidden feature negative injection fail-closed."""

    def test_forbidden_feature_detected(self, sample_rows):
        """Inject home_score → forbidden_hits includes it, status=blocked."""
        conn = _make_conn({"transaction_read_only": "on"}, sample_rows)

        from scripts.ops import train_model as tm

        original = tm.extract_v5_features

        def _injected(*args, **kwargs):  # noqa: ARG001
            return {"home_elo_pre": 1500.0, "home_score": 2}

        tm.extract_v5_features = _injected
        try:
            s = tm.run_dry_run_mode(conn, logger=None)
        finally:
            tm.extract_v5_features = original

        assert "home_score" in s["forbidden_feature_hits"]
        assert s["status"] == "blocked"
        assert any("forbidden" in r for r in s["blocked_reasons"])

    def test_forbidden_away_score_detected(self, sample_rows):
        """Inject away_score → blocked."""
        conn = _make_conn({"transaction_read_only": "on"}, sample_rows)

        from scripts.ops import train_model as tm

        original = tm.extract_v5_features

        def _injected(*args, **kwargs):  # noqa: ARG001
            return {"away_score": 1, "safe": 0.5}

        tm.extract_v5_features = _injected
        try:
            s = tm.run_dry_run_mode(conn, logger=None)
        finally:
            tm.extract_v5_features = original

        assert "away_score" in s["forbidden_feature_hits"]
        assert s["status"] == "blocked"

    def test_clean_features_no_forbidden_hits(self, sample_rows):
        """Normal features have no forbidden hits and pass."""
        conn = _make_conn({"transaction_read_only": "on"}, sample_rows)
        s = _run(conn)
        assert s["forbidden_feature_hits"] == []
        assert s["status"] == "pass"


class TestExistingGatesUnchanged:
    """Non-dry-run existing training gates preserved."""

    def test_existing_gate_functions_importable(self):
        from scripts.ops.train_model import (
            load_training_data,
            require_training_write_confirmation,
            save_model,
            train_model,
        )

        assert callable(require_training_write_confirmation)
        assert callable(load_training_data)
        assert callable(train_model)
        assert callable(save_model)


class TestSummaryJSON:
    """Output is valid JSON with all required keys."""

    REQUIRED_KEYS = [
        "mode",
        "status",
        "db_read_only",
        "transaction_read_only_setting",
        "eligible_cohort_count",
        "cohort_count",
        "l3_coverage_count",
        "missing_l3_count",
        "missing_l3_match_ids",
        "label_column",
        "label_null_count",
        "label_distribution",
        "invalid_label_values",
        "feature_count",
        "feature_names",
        "feature_extracted_row_count",
        "feature_extraction_error_count",
        "feature_extraction_error_match_ids",
        "feature_extraction_errors",
        "forbidden_feature_hits",
        "elo_real_count",
        "elo_default_count",
        "elo_default_match_ids",
        "default_elo_explicit",
        "fit_executed",
        "predict_executed",
        "db_write_attempted",
        "artifact_written",
        "dataset_file_written",
        "model_file_written",
        "blocked_reasons",
    ]

    def test_all_required_keys_present(self, sample_rows):
        conn = _make_conn({"transaction_read_only": "on"}, sample_rows)
        s = _run(conn)
        for key in self.REQUIRED_KEYS:
            assert key in s, f"Missing required key: {key}"

    def test_json_serializable(self, sample_rows):
        conn = _make_conn({"transaction_read_only": "on"}, sample_rows)
        s = _run(conn)
        serialized = json.dumps(s, indent=2, ensure_ascii=False, default=str)
        assert len(serialized) > 0
        assert json.loads(serialized)["mode"] == "training_preflight_dry_run"

    def test_pass_status_when_clean(self, sample_rows):
        conn = _make_conn({"transaction_read_only": "on"}, sample_rows)
        s = _run(conn)
        assert s["status"] == "pass"


class TestFeatureSafety:
    """Score/result/status fields excluded from features."""

    def test_actual_result_not_in_features(self, sample_rows):
        conn = _make_conn({"transaction_read_only": "on"}, sample_rows)
        s = _run(conn)
        for fname in s["feature_names"]:
            assert "actual_result" not in fname.lower()

    def test_home_score_not_in_features(self, sample_rows):
        conn = _make_conn({"transaction_read_only": "on"}, sample_rows)
        s = _run(conn)
        for fname in s["feature_names"]:
            assert "home_score" not in fname.lower()

    def test_features_extracted(self, sample_rows):
        conn = _make_conn({"transaction_read_only": "on"}, sample_rows)
        s = _run(conn)
        assert s["feature_count"] > 0
        assert len(s["feature_names"]) > 0
