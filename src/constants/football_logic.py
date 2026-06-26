"""Football domain constants — restored import-contract stub (Refs #1631).

This module was missing from the repository.  Symbols required by
src/constants/__init__.py and active production consumers are restored
with minimal implementations based on usage evidence.

lifecycle: permanent
"""

from __future__ import annotations

import decimal
from types import SimpleNamespace
from typing import Any

# ============================================================================
# Actively used symbols (reconstructed from usage evidence in src/ml/
# and src/strategy/)
# ============================================================================


class PrecisionContext:
    """Numeric precision settings for football probability calculations.

    Used as both a context-manager factory (``with PrecisionContext.high_precision():``)
    and as an instance store (``self._decimal_ctx = PrecisionContext.high_precision()``)
    in src/ml/inference/predictor.py and src/ml/features/extractor.py.
    """

    @staticmethod
    def high_precision() -> Any:
        """Return a decimal localcontext with high precision."""
        return decimal.localcontext(decimal.Context(prec=28))

    @staticmethod
    def medium_precision() -> Any:
        """Return a decimal localcontext with medium precision."""
        return decimal.localcontext(decimal.Context(prec=14))

    @staticmethod
    def low_precision() -> Any:
        """Return a decimal localcontext with low precision."""
        return decimal.localcontext(decimal.Context(prec=8))


# -- FOOTBALL: match-outcome and regulation constants --

FOOTBALL = SimpleNamespace(
    HOME_WIN=2,
    DRAW=1,
    AWAY_WIN=0,
    REGULATION_TIME_MINUTES=90,
)

# -- MATH: safe arithmetic helpers --

MATH = SimpleNamespace(
    safe_divide=lambda a, b, default: a / b if b != 0 else default,
)

# -- PROBABILITY: probability boundaries and epsilon --

PROBABILITY = SimpleNamespace(
    MIN_PROBABILITY=0.001,
    MAX_PROBABILITY=0.999,
    PROBABILITY_EPSILON=1e-10,
    MIN_REASONABLE_PROB=0.01,
    MAX_REASONABLE_PROB=0.99,
)

# -- SCORING: default H2H rates and smoothing values --

SCORING = SimpleNamespace(
    DEFAULT_H2H_WIN_RATE=0.5,
    DEFAULT_H2H_DRAW_RATE=0.25,
    DEFAULT_H2H_LOSS_RATE=0.25,
    DEFAULT_AVG_GOAL_DIFF=0.0,
    SMOOTHING_EPSILON=1e-6,
)

# -- STATISTICAL: sample-size and window thresholds --

STATISTICAL = SimpleNamespace(
    MIN_H2H_SAMPLE_SIZE=30,
    MEDIUM_TERM_WINDOW=5,
)

# -- VALIDATION: feature-value clamping --

VALIDATION = SimpleNamespace(
    MAX_FEATURE_VALUE=100.0,
    MIN_FEATURE_VALUE=-100.0,
)

# -- VALIDATOR: probability normalisation --

VALIDATOR = SimpleNamespace(
    normalize_probabilities=lambda probs: (
        [p / sum(probs) for p in probs] if sum(probs) > 0 else probs
    ),
)

# ============================================================================
# Import-contract placeholders
# ============================================================================
# These symbols are exported by src/constants/__init__.py but are not
# currently consumed by any production Python code.  They are set to None
# so that the import contract is satisfied without inventing semantics.

DECIMAL_PRECISION: Any = None
DEFAULT_H2H_STATS: Any = None
ODDS: Any = None
BusinessRuleValidator: Any = None
FinancialMath: Any = None
FootballConstants: Any = None
OddsConstants: Any = None
ProbabilityConstants: Any = None
ScoringConstants: Any = None
StatisticalConstants: Any = None
ValidationConstants: Any = None

# ============================================================================
# Public API
# ============================================================================

__all__ = [
    "DECIMAL_PRECISION",
    "DEFAULT_H2H_STATS",
    "FOOTBALL",
    "MATH",
    "ODDS",
    "PROBABILITY",
    "SCORING",
    "STATISTICAL",
    "VALIDATION",
    "VALIDATOR",
    "BusinessRuleValidator",
    "FinancialMath",
    "FootballConstants",
    "OddsConstants",
    "PrecisionContext",
    "ProbabilityConstants",
    "ScoringConstants",
    "StatisticalConstants",
    "ValidationConstants",
]
