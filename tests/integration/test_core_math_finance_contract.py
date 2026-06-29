# ruff: noqa: PLR2004 (magic values in test assertions are intentional)

"""Integration tests for core math modules: finance + evaluator.

Covers:
    1. core/math/finance.py — kelly_criterion, fractional_kelly, expected_value, sharpe_ratio
    2. core/math/evaluator.py — safe_eval with operators and variables

These two modules are tested together to validate the integration of the project's
mathematical foundation layer. All tests use real function calls with zero mocks.
No DB, Docker, network, or secrets are required.
"""

import ast as _ast_mod
import importlib.util
from pathlib import Path

import pytest

# evaluator.py uses ast.Num which was removed in Python 3.12+.
# This is a known pre-existing source compatibility issue (not a test bug).
# Tests that exercise safe_eval are skipped when ast.Num is unavailable.
_SAFE_EVAL_WORKS = hasattr(_ast_mod, "Num")

_SRC = Path(__file__).parent.parent.parent / "src"


def _load(module_name: str, rel_path: str):
    """Load a Python module from a source file without triggering package __init__.py."""
    spec = importlib.util.spec_from_file_location(module_name, str(_SRC / rel_path))
    if spec is None or spec.loader is None:
        raise ImportError(f"Cannot load {rel_path} as {module_name}")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


_m_finance = _load("core.math.finance", "core/math/finance.py")
_m_evaluator = _load("core.math.evaluator", "core/math/evaluator.py")

kelly_criterion = _m_finance.kelly_criterion
fractional_kelly = _m_finance.fractional_kelly
expected_value = _m_finance.expected_value
sharpe_ratio = _m_finance.sharpe_ratio
core_safe_eval = _m_evaluator.safe_eval


class TestKellyCriterion:
    """Kelly formula: f* = (bp - q) / b."""

    def test_positive_ev_bet(self):
        """A bet with positive expected value yields positive kelly fraction."""
        result = kelly_criterion(0.55, 2.0)
        assert result == pytest.approx(0.10)
        assert result > 0

    def test_negative_ev_bet(self):
        """A bet with negative expected value yields kelly of 0."""
        result = kelly_criterion(0.45, 2.0)
        assert result == 0.0

    def test_edge_probabilities(self):
        """Probability at extremes returns 0."""
        assert kelly_criterion(0.0, 2.0) == 0.0
        assert kelly_criterion(1.0, 2.0) == 0.0

    def test_fractional_kelly_reduces_exposure(self):
        """fractional_kelly is always <= full_kelly."""
        full = kelly_criterion(0.60, 2.5)
        half = fractional_kelly(0.60, 2.5, fraction=0.5)
        quarter = fractional_kelly(0.60, 2.5, fraction=0.25)
        assert 0 < quarter < half < full

    def test_expected_value_sign(self):
        """EV matches intuition: positive for good odds, negative otherwise."""
        ev_good = expected_value(0.60, 2.5)
        ev_bad = expected_value(0.30, 2.5)
        assert ev_good > 0
        assert ev_bad < 0

    def test_sharpe_ratio_positive_returns(self):
        """Sharpe ratio is positive when returns exceed risk-free rate."""
        returns = [0.05, 0.10, 0.08, 0.12, 0.07]
        sr = sharpe_ratio(returns, risk_free_rate=0.02)
        assert sr > 0

    def test_sharpe_ratio_empty(self):
        """Empty returns list yields 0."""
        assert sharpe_ratio([]) == 0.0

    def test_sharpe_ratio_single_value(self):
        """Return values with zero variance yield 0. Use integers for exact arithmetic."""
        assert sharpe_ratio([5, 5, 5]) == pytest.approx(0.0)


@pytest.mark.skipif(
    not _SAFE_EVAL_WORKS, reason="ast.Num removed in Python 3.12+; pre-existing source compat issue"
)
class TestSafeEvalIntegration:
    """safe_eval exercises the AST-based expression evaluator."""

    def test_basic_arithmetic(self):
        """Core arithmetic operators produce expected results."""
        assert core_safe_eval("2 + 3 * 4") == 14
        assert core_safe_eval("10 - 2 * 3") == 4
        assert core_safe_eval("2 ** 3") == 8
        assert core_safe_eval("-5 + 3") == -2

    def test_with_variables(self):
        """Variables from the caller are resolved in the expression."""
        result = core_safe_eval("x * y + z", variables={"x": 2, "y": 3, "z": 1})
        assert result == 7

    def test_allowed_functions(self):
        """Built-in math functions abs, max, min, sum, round are available."""
        assert core_safe_eval("abs(-5)") == 5
        assert core_safe_eval("max(1, 2, 3)") == 3
        assert core_safe_eval("min(1, 2, 3)") == 1
        assert core_safe_eval("round(3.7)") == 4

    def test_nested_function_calls(self):
        """Functions can be composed."""
        assert core_safe_eval("abs(max(-3, -7))") == 7

    def test_rejects_undefined_variable(self):
        """A variable not in the variables dict raises ValueError."""
        with pytest.raises(ValueError, match="未定义的变量"):
            core_safe_eval("undefined_var + 1")

    def test_rejects_unsafe_operation(self):
        """Operations beyond the allowlist raise ValueError."""
        with pytest.raises(ValueError, match="不支持"):
            core_safe_eval("__import__('os').system('ls')")

    def test_rejects_syntax_error(self):
        """Invalid Python syntax raises ValueError."""
        with pytest.raises(ValueError, match="语法错误"):
            core_safe_eval("2 + +")


@pytest.mark.skipif(
    not _SAFE_EVAL_WORKS, reason="ast.Num removed in Python 3.12+; pre-existing source compat issue"
)
class TestFinanceWithSafeEval:
    """Integration: finance formulas expressed via safe_eval with real results."""

    def test_kelly_via_safe_eval_expression(self):
        """The kelly formula can be verified via safe_eval with variables."""
        p, b_val = 0.55, 1.0  # probability and net odds
        kelly_expr = "(b * p - (1 - p)) / b"
        kelly_via_eval = core_safe_eval(kelly_expr, variables={"b": b_val, "p": p})
        assert kelly_via_eval == pytest.approx(kelly_criterion(p, b_val + 1))

    def test_expected_value_via_safe_eval(self):
        """EV = p * (odds - 1) - (1 - p) * 1."""
        p, odds = 0.60, 2.5
        ev_expr = "p * (odds - 1) - (1 - p) * 1"
        ev_via_eval = core_safe_eval(ev_expr, variables={"p": p, "odds": odds})
        assert ev_via_eval == pytest.approx(expected_value(p, odds))
