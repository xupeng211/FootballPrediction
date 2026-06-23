#!/usr/bin/env python3
"""
AI Workflow Gate — Python DB Write Enforcement tests (Phase2A).

lifecycle: permanent
scope: static verification only; does NOT execute target scripts or connect to DB.

Tests the Python DB write enforcement helper and its integration in
ai_workflow_gate.py main().
"""

from __future__ import annotations

import importlib
import importlib.util
import inspect
from pathlib import Path

import pytest

import scripts.ops.ai_workflow_gate as gate

# ── Helper to load the enforcement check module ──────────────────────────────


def _load_python_enforcement():
    """Load the python_db_write_enforcement_check module."""
    helper = (
        Path(__file__).resolve().parent.parent.parent
        / "scripts"
        / "ops"
        / "helpers"
        / "python_db_write_enforcement_check.py"
    )
    if not helper.exists():
        return None
    spec = importlib.util.spec_from_file_location("_pydbw", str(helper))
    if spec is None or spec.loader is None:
        return None
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


# ── Python enforcement function tests ────────────────────────────────────────


def test_python_enforcement_function_callable():
    """check_python_db_write_enforcement is importable and callable."""
    mod = _load_python_enforcement()
    if mod is None:
        pytest.skip("Enforcement helper module not found")
    assert callable(mod.check_python_db_write_enforcement), (
        "check_python_db_write_enforcement must be callable"
    )


def test_python_enforcement_docs_only_unaffected():
    """Docs-only changed files should not trigger Python enforcement."""
    mod = _load_python_enforcement()
    if mod is None:
        pytest.skip("Enforcement helper module not found")
    errors, _warnings = mod.check_python_db_write_enforcement(
        {"docs/PROJECT_STATUS.md", "README.md"}
    )
    assert len(errors) == 0, f"Docs-only PR should have 0 errors, got {errors}"


def test_python_enforcement_non_db_file_passes():
    """Python file with no DB signals should pass enforcement."""
    mod = _load_python_enforcement()
    if mod is None:
        pytest.skip("Enforcement helper module not found")
    errors, _warnings = mod.check_python_db_write_enforcement(
        {"scripts/ops/documentation_governance_check.py"}
    )
    assert len(errors) == 0, f"Non-DB Python file should have 0 errors, got {errors}"


def test_python_enforcement_empty_set_passes():
    """Empty changed set should pass."""
    mod = _load_python_enforcement()
    if mod is None:
        pytest.skip("Enforcement helper module not found")
    errors, _warnings = mod.check_python_db_write_enforcement(set())
    assert len(errors) == 0


# ── JS DB write guard enforcement still works (regression) ───────────────────


def test_js_db_write_guard_still_callable():
    """Existing JS DB write guard enforcement function is still callable."""
    assert callable(gate.check_db_write_guard_enforcement), (
        "check_db_write_guard_enforcement must remain callable"
    )


# ── AI Workflow Gate integrity ───────────────────────────────────────────────


def test_ai_workflow_gate_imports_cleanly():
    """The ai_workflow_gate module imports without errors."""
    mod = importlib.reload(gate)
    assert hasattr(mod, "check_db_write_guard_enforcement")
    assert hasattr(mod, "validate")
    assert hasattr(mod, "main")


def test_forbidden_phrases_check_function_exists():
    """check_safety_consistency function still exists."""
    assert callable(gate.check_safety_consistency), "check_safety_consistency must exist"


# ── AI Workflow Gate main() integration ──────────────────────────────────────


def test_main_function_calls_python_enforcement():
    """main() function references Python enforcement wrapper."""
    source = inspect.getsource(gate.main)
    assert "run_python_db_write_gate_check" in source, (
        "main() should call run_python_db_write_gate_check wrapper"
    )
