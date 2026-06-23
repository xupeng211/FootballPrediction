#!/usr/bin/env python3
"""AI Workflow Gate SQL Phase2B tests."""

from __future__ import annotations

import importlib.util
import inspect
from pathlib import Path

import scripts.ops.ai_workflow_gate as gate

_R = Path(__file__).resolve().parent.parent.parent


def _m():
    h = _R / "scripts/ops/helpers/sql_migration_policy_enforcement_check.py"
    if not h.exists():
        return None
    s = importlib.util.spec_from_file_location("_sq", str(h))
    if s is None or s.loader is None:
        return None
    m = importlib.util.module_from_spec(s)
    s.loader.exec_module(m)
    return m


def test_docs():
    m = _m()
    if m:
        assert len(m.check_sql_migration_policy_enforcement({"docs/README.md"})[0]) == 0


def test_allowlisted():
    m = _m()
    if m:
        assert (
            len(
                m.check_sql_migration_policy_enforcement(
                    {"database/migrations/V12.4__create_matches_oddsportal_mapping.sql"}
                )[0]
            )
            == 0
        )


def test_js_ok():
    assert callable(gate.check_db_write_guard_enforcement)


def test_python_ok():
    assert callable(gate.check_safety_consistency)


def test_main_has():
    assert "sql_migration_policy_enforcement_check" in inspect.getsource(gate.main)
