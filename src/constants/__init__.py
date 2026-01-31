#!/usr/bin/env python3
"""
常量模块初始化

提供统一的常量访问接口，确保整个系统使用一致的数值定义。

使用示例:
    from src.constants import SCORING, FOOTBALL
    default_rate = SCORING.DEFAULT_H2H_WIN_RATE
    regulation_time = FOOTBALL.REGULATION_TIME_MINUTES
"""

from .football_logic import (  # 配置; 实例; 工具类; 主要常量类
    DECIMAL_PRECISION,
    DEFAULT_H2H_STATS,
    FOOTBALL,
    MATH,
    ODDS,
    PROBABILITY,
    SCORING,
    STATISTICAL,
    VALIDATION,
    VALIDATOR,
    BusinessRuleValidator,
    FinancialMath,
    FootballConstants,
    OddsConstants,
    PrecisionContext,
    ProbabilityConstants,
    ScoringConstants,
    StatisticalConstants,
    ValidationConstants,
)

# 向后兼容的别名
Constants = FootballConstants

__version__ = "1.0.0"
__author__ = "Advanced ML Engineer"

# 导出的公共接口
__all__ = [
    "DECIMAL_PRECISION",
    # 配置
    "DEFAULT_H2H_STATS",
    # 实例
    "FOOTBALL",
    "MATH",
    "ODDS",
    "PROBABILITY",
    "SCORING",
    "STATISTICAL",
    "VALIDATION",
    "VALIDATOR",
    "BusinessRuleValidator",
    "CalculationThresholds",
    "Constants",  # 向后兼容别名
    # 工具类
    "FinancialMath",
    # 主要常量类
    "FootballConstants",
    "OddsConstants",
    "PrecisionContext",
    "ProbabilityConstants",
    "ScoringConstants",
    "StatisticalConstants",
    "ValidationConstants",
]
