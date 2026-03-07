"""
V4.45 核心算力中心 - 数学计算模块
===================================

核心数学能力:
- finance: 金融数学公式 (Kelly Criterion, EV, Sharpe Ratio)
- evaluator: 安全表达式求值

Author: V4.45 Grand Unification Team
Date: 2026-03-08
"""

from .finance import (
    expected_value,
    fractional_kelly,
    kelly_criterion,
    sharpe_ratio,
)
from .evaluator import safe_eval

__all__ = [
    # 金融数学
    "kelly_criterion",
    "fractional_kelly",
    "expected_value",
    "sharpe_ratio",
    # 表达式求值
    "safe_eval",
]
