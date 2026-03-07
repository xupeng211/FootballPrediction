#!/usr/bin/env python3
"""
V4.45 核心算力中心 - 金融数学计算模块
=====================================

核心数学公式实现:
- Kelly Criterion (凯利公式)
- 风险价值计算
- 组合优化算法

Author: V4.45 Grand Unification Team
Date: 2026-03-08
"""

from decimal import Decimal
from typing import Any


def kelly_criterion(probability: float, odds: float) -> float:
    """
    凯利公式 - 计算最优投注比例
    
    公式: f* = (bp - q) / b
    其中:
        f*: 最优投注比例
        b: 净赔率 (decimal odds - 1)
        p: 胜率
        q: 败率 = 1 - p
    
    Args:
        probability: 预测胜率 (0-1)
        odds: 十进制赔率 (如 2.5 表示投注 1 赢 2.5)
    
    Returns:
        float: 最优投注比例 (如 0.05 表示投注 5%)
    """
    if probability <= 0 or probability >= 1:
        return 0.0
    
    b = odds - 1  # 净赔率
    p = probability
    q = 1 - p
    
    kelly = (b * p - q) / b
    return max(0.0, kelly)


def fractional_kelly(probability: float, odds: float, fraction: float = 0.25) -> float:
    """
    分数凯利 - 降低风险的凯利变体
    
    Args:
        probability: 预测胜率
        odds: 十进制赔率
        fraction: 凯利分数 (默认 0.25 即 1/4 凯利)
    
    Returns:
        float: 分数凯利投注比例
    """
    full_kelly = kelly_criterion(probability, odds)
    return full_kelly * fraction


def expected_value(probability: float, odds: float) -> float:
    """
    计算期望值 (EV)
    
    EV = (p * win_amount) - (q * loss_amount)
    
    Args:
        probability: 胜率
        odds: 十进制赔率
    
    Returns:
        float: 期望值 (正数表示有利)
    """
    p = probability
    q = 1 - p
    win_amount = odds - 1
    loss_amount = 1
    
    return (p * win_amount) - (q * loss_amount)


def sharpe_ratio(returns: list[float], risk_free_rate: float = 0.0) -> float:
    """
    计算夏普比率
    
    Sharpe = (Rp - Rf) / σp
    
    Args:
        returns: 收益率列表
        risk_free_rate: 无风险利率
    
    Returns:
        float: 夏普比率
    """
    if not returns:
        return 0.0
    
    mean_return = sum(returns) / len(returns)
    variance = sum((r - mean_return) ** 2 for r in returns) / len(returns)
    std_dev = variance ** 0.5
    
    if std_dev == 0:
        return 0.0
    
    return (mean_return - risk_free_rate) / std_dev


# 向后兼容导出
__all__ = [
    "kelly_criterion",
    "fractional_kelly",
    "expected_value",
    "sharpe_ratio",
]
