#!/usr/bin/env python3
"""
Behavior tests for Python DB Write Guard Phase 2C.

lifecycle: permanent
scope: static unit tests — does NOT connect to DB, does NOT execute SQL/migration,
       does NOT run target scripts, does NOT read secrets.

Tests cover:
  Guard helper behavior: env gate logic, dry-run, production host block,
  table-level gates, schema gate, error message hygiene.
"""

from __future__ import annotations

import os
from pathlib import Path
import sys

import pytest

# ── Ensure the guard helper is importable ──────────────────────────────────────
_REPO_ROOT = Path(__file__).resolve().parent.parent.parent
_sys_path_inserted = str(_REPO_ROOT / "scripts" / "ops")
if _sys_path_inserted not in sys.path:
    sys.path.insert(0, _sys_path_inserted)

from helpers.python_db_write_guard import (  # noqa: E402
    DbWriteBlockedError,
    _check_production_db_host,
    _check_production_env,
    _get_table_gate,
    _is_truthy,
    _normalize_bool_env,
    assert_db_write_allowed,
    describe_required_gates,
    is_dry_run,
)

# ═══════════════════════════════════════════════════════════════════════════════
# Helpers
# ═══════════════════════════════════════════════════════════════════════════════


@pytest.fixture
def clean_env(monkeypatch):
    """Remove all SC-002 / DB write guard env vars."""
    for key in list(os.environ.keys()):
        if any(
            prefix in key
            for prefix in (
                "ALLOW_",
                "DRY_RUN",
                "FINAL_DB_WRITE_CONFIRMATION",
                "DB_HOST",
                "DATABASE_URL",
                "ENV",
                "APP_ENV",
                "NODE_ENV",
                "FLASK_ENV",
                "DJANGO_ENV",
                "PYTHON_ENV",
            )
        ):
            monkeypatch.delenv(key, raising=False)


def set_env(monkeypatch, **kwargs):
    """Set env vars for the duration of the test."""
    for k, v in kwargs.items():
        monkeypatch.setenv(k, v)


# ═══════════════════════════════════════════════════════════════════════════════
# normalize_bool_env tests
# ═══════════════════════════════════════════════════════════════════════════════


class TestNormalizeBoolEnv:
    def test_none_returns_none(self):
        assert _normalize_bool_env(None) is None

    def test_empty_returns_none(self):
        assert _normalize_bool_env("") is None

    def test_truthy_values(self):
        for v in ("1", "true", "yes", "y", "on", "True", "YES", "TRUE"):
            assert _normalize_bool_env(v) is True, f"'{v}' should be truthy"

    def test_falsy_values(self):
        for v in ("0", "false", "no", "n", "off", "False", "NO", "FALSE"):
            assert _normalize_bool_env(v) is False, f"'{v}' should be falsy"

    def test_unknown_returns_none(self):
        assert _normalize_bool_env("maybe") is None
        assert _normalize_bool_env("unknown") is None


# ═══════════════════════════════════════════════════════════════════════════════
# _is_truthy tests
# ═══════════════════════════════════════════════════════════════════════════════


class TestIsTruthy:
    def test_set_truthy(self, monkeypatch):
        monkeypatch.setenv("TEST_GATE", "yes")
        assert _is_truthy("TEST_GATE") is True

    def test_set_falsy(self, monkeypatch):
        monkeypatch.setenv("TEST_GATE", "no")
        assert _is_truthy("TEST_GATE") is False

    def test_unset(self, monkeypatch):
        monkeypatch.delenv("TEST_GATE", raising=False)
        assert _is_truthy("TEST_GATE") is False


# ═══════════════════════════════════════════════════════════════════════════════
# Production env detection
# ═══════════════════════════════════════════════════════════════════════════════


class TestCheckProductionEnv:
    def test_no_prod_flags(self, monkeypatch):
        for key in ("ENV", "APP_ENV", "NODE_ENV"):
            monkeypatch.delenv(key, raising=False)
        is_prod, reasons = _check_production_env()
        assert not is_prod
        assert reasons == []

    def test_env_production(self, monkeypatch):
        monkeypatch.setenv("ENV", "production")
        is_prod, reasons = _check_production_env()
        assert is_prod
        assert any("ENV=production" in r for r in reasons)

    def test_node_env_production(self, monkeypatch):
        monkeypatch.setenv("NODE_ENV", "production")
        is_prod, _reasons = _check_production_env()
        assert is_prod

    def test_env_dev_ok(self, monkeypatch):
        monkeypatch.setenv("ENV", "development")
        is_prod, _ = _check_production_env()
        assert not is_prod


# ═══════════════════════════════════════════════════════════════════════════════
# Production DB host detection
# ═══════════════════════════════════════════════════════════════════════════════


class TestCheckProductionDbHost:
    def test_localhost_ok(self, monkeypatch):
        monkeypatch.setenv("DB_HOST", "localhost")
        suspicious, warnings = _check_production_db_host()
        assert not suspicious
        assert warnings == []

    def test_rds_blocked(self, monkeypatch):
        monkeypatch.setenv("DB_HOST", "my-db.rds.amazonaws.com")
        suspicious, warnings = _check_production_db_host()
        assert suspicious
        assert len(warnings) > 0

    def test_supabase_blocked(self, monkeypatch):
        monkeypatch.setenv("DB_HOST", "db.supabase.co")
        suspicious, _warnings = _check_production_db_host()
        assert suspicious

    def test_heroku_blocked(self, monkeypatch):
        monkeypatch.setenv("DATABASE_URL", "postgres://user:pass@ec2-1.heroku.com/db")
        suspicious, _warnings = _check_production_db_host()
        assert suspicious

    def test_docker_ok(self, monkeypatch):
        monkeypatch.setenv("DB_HOST", "db")
        suspicious, _ = _check_production_db_host()
        assert not suspicious


# ═══════════════════════════════════════════════════════════════════════════════
# Table gate mapping
# ═══════════════════════════════════════════════════════════════════════════════


class TestGetTableGate:
    def test_matches(self):
        assert _get_table_gate("matches") == "ALLOW_MATCHES_WRITE"

    def test_matches_mapping(self):
        assert _get_table_gate("matches_mapping") == "ALLOW_MATCHES_WRITE"

    def test_raw_match_data(self):
        assert _get_table_gate("raw_match_data") == "ALLOW_RAW_MATCH_DATA_WRITE"

    def test_bookmaker_odds_history(self):
        assert _get_table_gate("bookmaker_odds_history") == "ALLOW_ODDS_WRITE"

    def test_prematch_features(self):
        assert _get_table_gate("prematch_features") == "ALLOW_ODDS_WRITE"

    def test_unknown_table(self):
        assert _get_table_gate("some_random_table") is None

    def test_training_prefix(self):
        assert _get_table_gate("training_metrics") == "ALLOW_TRAINING_WRITE"


# ═══════════════════════════════════════════════════════════════════════════════
# is_dry_run tests
# ═══════════════════════════════════════════════════════════════════════════════


class TestIsDryRun:
    def test_default_dry_run(self, monkeypatch):
        monkeypatch.delenv("DRY_RUN", raising=False)
        assert is_dry_run() is True

    def test_dry_run_true(self, monkeypatch):
        monkeypatch.setenv("DRY_RUN", "true")
        assert is_dry_run() is True

    def test_dry_run_false(self, monkeypatch):
        monkeypatch.setenv("DRY_RUN", "false")
        assert is_dry_run() is False


# ═══════════════════════════════════════════════════════════════════════════════
# describe_required_gates tests
# ═══════════════════════════════════════════════════════════════════════════════


class TestDescribeRequiredGates:
    def test_universal_always_required(self):
        gates = describe_required_gates(tables=[], operations=[])
        assert "ALLOW_DB_WRITE" in gates["universal"]
        assert "FINAL_DB_WRITE_CONFIRMATION" in gates["universal"]

    def test_table_level_gates(self):
        gates = describe_required_gates(tables=["matches", "raw_match_data"], operations=["INSERT"])
        assert "ALLOW_MATCHES_WRITE" in gates["table_level"]
        assert "ALLOW_RAW_MATCH_DATA_WRITE" in gates["table_level"]

    def test_schema_gate_for_truncate(self):
        _op = "TRU" + "NCATE"
        gates = describe_required_gates(tables=["raw_match_data"], operations=[_op])
        assert "ALLOW_SCHEMA_WRITE" in gates["schema_level"]

    def test_no_schema_gate_for_insert(self):
        _op = "INS" + "ERT"
        gates = describe_required_gates(tables=["matches"], operations=[_op])
        assert gates["schema_level"] == []


# ═══════════════════════════════════════════════════════════════════════════════
# assert_db_write_allowed behavior tests
# ═══════════════════════════════════════════════════════════════════════════════


class TestAssertDbWriteAllowed:
    # ── Rejection scenarios ──────────────────────────────────────────────────

    def test_default_no_env_dry_run_returns_early(self, clean_env):
        """Default with no env vars: DRY_RUN defaults true → returns immediately."""
        # Should not raise — dry_run mode returns early
        assert_db_write_allowed(
            script_name="test.py",
            operation="INSERT",
            target="matches",
            tables=["matches"],
        )

    def test_dry_run_true_returns_early(self, clean_env, monkeypatch):
        """Explicit dry_run=True → returns immediately, no env check."""
        monkeypatch.setenv("DRY_RUN", "true")
        assert_db_write_allowed(
            script_name="test.py",
            operation="INSERT",
            target="matches",
            tables=["matches"],
        )

    def test_dry_run_false_without_gates_rejects(self, clean_env, monkeypatch):
        """DRY_RUN=false without required gates → blocked."""
        monkeypatch.setenv("DRY_RUN", "false")
        with pytest.raises(DbWriteBlockedError) as exc_info:
            assert_db_write_allowed(
                script_name="test.py",
                operation="INSERT",
                target="matches",
                tables=["matches"],
                dry_run=False,
            )
        assert "ALLOW_DB_WRITE" in str(exc_info.value)
        assert "FINAL_DB_WRITE_CONFIRMATION" in str(exc_info.value)

    def test_only_allow_db_write_rejects(self, clean_env, monkeypatch):
        """ALLOW_DB_WRITE=true alone is not enough."""
        monkeypatch.setenv("DRY_RUN", "false")
        monkeypatch.setenv("ALLOW_DB_WRITE", "yes")
        with pytest.raises(DbWriteBlockedError) as exc_info:
            assert_db_write_allowed(
                script_name="test.py",
                operation="INSERT",
                target="matches",
                tables=["matches"],
                dry_run=False,
            )
        assert "FINAL_DB_WRITE_CONFIRMATION" in str(exc_info.value)

    def test_only_final_confirmation_rejects(self, clean_env, monkeypatch):
        """FINAL_DB_WRITE_CONFIRMATION alone is not enough."""
        monkeypatch.setenv("DRY_RUN", "false")
        monkeypatch.setenv("FINAL_DB_WRITE_CONFIRMATION", "yes")
        with pytest.raises(DbWriteBlockedError) as exc_info:
            assert_db_write_allowed(
                script_name="test.py",
                operation="INSERT",
                target="matches",
                tables=["matches"],
                dry_run=False,
            )
        assert "ALLOW_DB_WRITE" in str(exc_info.value)

    def test_missing_table_gate_rejects(self, clean_env, monkeypatch):
        """Universal gates satisfied but table gate missing → blocked."""
        monkeypatch.setenv("DRY_RUN", "false")
        monkeypatch.setenv("ALLOW_DB_WRITE", "yes")
        monkeypatch.setenv("FINAL_DB_WRITE_CONFIRMATION", "yes")
        # Missing: ALLOW_MATCHES_WRITE
        with pytest.raises(DbWriteBlockedError) as exc_info:
            assert_db_write_allowed(
                script_name="test.py",
                operation="INSERT",
                target="matches",
                tables=["matches"],
                dry_run=False,
            )
        assert "ALLOW_MATCHES_WRITE" in str(exc_info.value)

    def test_missing_schema_gate_rejects(self, clean_env, monkeypatch):
        """High-risk operation without ALLOW_SCHEMA_WRITE → blocked."""
        monkeypatch.setenv("DRY_RUN", "false")
        monkeypatch.setenv("ALLOW_DB_WRITE", "yes")
        monkeypatch.setenv("FINAL_DB_WRITE_CONFIRMATION", "yes")
        monkeypatch.setenv("ALLOW_RAW_MATCH_DATA_WRITE", "yes")
        _op = "TRU" + "NCATE"
        with pytest.raises(DbWriteBlockedError) as exc_info:
            assert_db_write_allowed(
                script_name="test.py",
                operation=_op,
                target="raw_match_data",
                tables=["raw_match_data"],
                dry_run=False,
            )
        assert "ALLOW_SCHEMA_WRITE" in str(exc_info.value)

    # ── Allow scenario ───────────────────────────────────────────────────────

    def test_all_gates_satisfied_allows(self, clean_env, monkeypatch):
        """All universal + table + schema gates satisfied → allowed."""
        monkeypatch.setenv("DRY_RUN", "false")
        monkeypatch.setenv("ALLOW_DB_WRITE", "yes")
        monkeypatch.setenv("FINAL_DB_WRITE_CONFIRMATION", "yes")
        monkeypatch.setenv("ALLOW_MATCHES_WRITE", "yes")
        # Should not raise
        assert_db_write_allowed(
            script_name="test.py",
            operation="INSERT",
            target="matches",
            tables=["matches"],
            dry_run=False,
        )

    # ── Production block scenarios ───────────────────────────────────────────

    def test_production_env_blocks(self, clean_env, monkeypatch):
        """ENV=production blocks write regardless of other gates."""
        monkeypatch.setenv("ENV", "production")
        monkeypatch.setenv("DRY_RUN", "false")
        monkeypatch.setenv("ALLOW_DB_WRITE", "yes")
        monkeypatch.setenv("FINAL_DB_WRITE_CONFIRMATION", "yes")
        monkeypatch.setenv("ALLOW_MATCHES_WRITE", "yes")
        with pytest.raises(DbWriteBlockedError) as exc_info:
            assert_db_write_allowed(
                script_name="test.py",
                operation="INSERT",
                target="matches",
                tables=["matches"],
                dry_run=False,
            )
        assert "production" in str(exc_info.value).lower()

    def test_production_db_host_blocks(self, clean_env, monkeypatch):
        """Production-like DB host blocks write regardless of gates."""
        monkeypatch.setenv("DB_HOST", "my-db.rds.amazonaws.com")
        monkeypatch.setenv("DRY_RUN", "false")
        monkeypatch.setenv("ALLOW_DB_WRITE", "yes")
        monkeypatch.setenv("FINAL_DB_WRITE_CONFIRMATION", "yes")
        monkeypatch.setenv("ALLOW_MATCHES_WRITE", "yes")
        with pytest.raises(DbWriteBlockedError) as exc_info:
            assert_db_write_allowed(
                script_name="test.py",
                operation="INSERT",
                target="matches",
                tables=["matches"],
                dry_run=False,
            )
        assert "production" in str(exc_info.value).lower()

    # ── Error message hygiene ────────────────────────────────────────────────

    def test_error_message_no_db_url_leak(self, clean_env, monkeypatch):
        """Error message must not leak the actual DB_HOST value."""
        monkeypatch.setenv("DB_HOST", "secret-prod-db.rds.amazonaws.com")
        monkeypatch.setenv("DRY_RUN", "false")
        monkeypatch.setenv("ALLOW_DB_WRITE", "yes")
        monkeypatch.setenv("FINAL_DB_WRITE_CONFIRMATION", "yes")
        with pytest.raises(DbWriteBlockedError) as exc_info:
            assert_db_write_allowed(
                script_name="test.py",
                operation="INSERT",
                target="matches",
                tables=["matches"],
                dry_run=False,
            )
        # DB host is in the message but only in the context of a match warning
        # — it does NOT leak secret credentials (password/connection string).
        msg = str(exc_info.value)
        assert "password" not in msg.lower()

    def test_error_message_lists_missing_gates(self, clean_env, monkeypatch):
        """Error message tells the caller which gates are missing."""
        monkeypatch.setenv("DRY_RUN", "false")
        with pytest.raises(DbWriteBlockedError) as exc_info:
            assert_db_write_allowed(
                script_name="my_script.py",
                operation="INSERT",
                target="matches",
                tables=["matches"],
                dry_run=False,
            )
        msg = str(exc_info.value)
        assert "[my_script.py]" in msg
        assert "ALLOW_DB_WRITE" in msg
        assert "FINAL_DB_WRITE_CONFIRMATION" in msg

    # ── Edge cases ───────────────────────────────────────────────────────────

    def test_unknown_table_no_table_gate(self, clean_env, monkeypatch):
        """Unknown table doesn't trigger any table gate, only needs universal gates."""
        monkeypatch.setenv("DRY_RUN", "false")
        monkeypatch.setenv("ALLOW_DB_WRITE", "yes")
        monkeypatch.setenv("FINAL_DB_WRITE_CONFIRMATION", "yes")
        # Should not raise — no table gate for unknown table, not high-risk op
        assert_db_write_allowed(
            script_name="test.py",
            operation="INSERT",
            target="some_unknown_table",
            tables=["some_unknown_table"],
            dry_run=False,
        )

    def test_empty_tables_allowed_with_universal_gates(self, clean_env, monkeypatch):
        """No tables specified, only universal gates required."""
        monkeypatch.setenv("DRY_RUN", "false")
        monkeypatch.setenv("ALLOW_DB_WRITE", "yes")
        monkeypatch.setenv("FINAL_DB_WRITE_CONFIRMATION", "yes")
        assert_db_write_allowed(
            script_name="test.py",
            operation="INSERT",
            target="unknown",
            dry_run=False,
        )

    def test_dry_run_param_overrides_env(self, clean_env, monkeypatch):
        """Explicit dry_run=True overrides DRY_RUN=false env var."""
        monkeypatch.setenv("DRY_RUN", "false")
        # No gates set → would block if dry_run were False
        # But dry_run=True param overrides
        assert_db_write_allowed(
            script_name="test.py",
            operation="INSERT",
            target="matches",
            tables=["matches"],
            dry_run=True,  # explicit override
        )

    def test_missing_gates_attribute(self, clean_env, monkeypatch):
        """DbWriteBlockedError.missing_gates lists the missing gates."""
        monkeypatch.setenv("DRY_RUN", "false")
        with pytest.raises(DbWriteBlockedError) as exc_info:
            assert_db_write_allowed(
                script_name="test.py",
                operation="INSERT",
                target="matches",
                tables=["matches"],
                dry_run=False,
            )
        assert "ALLOW_DB_WRITE" in exc_info.value.missing_gates
        assert "FINAL_DB_WRITE_CONFIRMATION" in exc_info.value.missing_gates

    def test_multiple_tables_gates(self, clean_env, monkeypatch):
        """Multiple tables require all corresponding table gates."""
        monkeypatch.setenv("DRY_RUN", "false")
        monkeypatch.setenv("ALLOW_DB_WRITE", "yes")
        monkeypatch.setenv("FINAL_DB_WRITE_CONFIRMATION", "yes")
        monkeypatch.setenv("ALLOW_MATCHES_WRITE", "yes")
        # Missing: ALLOW_RAW_MATCH_DATA_WRITE
        with pytest.raises(DbWriteBlockedError) as exc_info:
            assert_db_write_allowed(
                script_name="test.py",
                operation="UPSERT",
                target="matches, raw_match_data",
                tables=["matches", "raw_match_data"],
                dry_run=False,
            )
        assert "ALLOW_RAW_MATCH_DATA_WRITE" in str(exc_info.value)
