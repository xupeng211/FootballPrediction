#!/usr/bin/env python3
"""
常量模块初始化 - V4.17
======================

提供统一的常量访问接口，确保整个系统使用一致的数值定义。

V4.17 更新:
- 新增 shared_constants 模块，提供 Python/Node.js 共享常量
- HOME_WIN/DRAW/AWAY_WIN 统一为 2/1/0
- 比赛状态常量统一来源

使用示例:
    from src.constants import SCORING, FOOTBALL, HOME_WIN, DRAW, AWAY_WIN
    from src.constants.shared_constants import MATCH_STATUS, MATCH_OUTCOME

    default_rate = SCORING.DEFAULT_H2H_WIN_RATE
    regulation_time = FOOTBALL.REGULATION_TIME_MINUTES
    home_win_label = HOME_WIN  # 2
    status_finished = MATCH_STATUS.FINISHED  # "finished"
"""

# V4.17: 从共享常量导入核心定义（优先级最高）
from .shared_constants import (
    # 枚举类
    MatchOutcome,
    MatchStatus,
    # 配置类
    ConfidenceThresholds,
    DefaultProbabilities,
    OddsLimits,
    StatisticalThresholds,
    # 全局实例
    CONFIDENCE_THRESHOLDS,
    DEFAULT_PROBABILITIES,
    MATCH_OUTCOME,
    MATCH_STATUS,
    ODDS_LIMITS,
    STATISTICAL_THRESHOLDS,
    # 向后兼容常量（整数）
    AWAY_WIN,
    DRAW,
    HOME_WIN,
    # 比赛状态常量（字符串）
    STATUS_CANCELLED,
    STATUS_FINISHED,
    STATUS_LIVE,
    STATUS_SCHEDULED,
    # 工具函数
    get_constants,
    reload_constants,
)

# 从 football_logic 导入其余常量
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

__version__ = "V4.17.0"
__author__ = "Advanced ML Engineer"

# 导出的公共接口
__all__ = [
    # V4.17: 共享常量（优先）
    "MatchOutcome",
    "MatchStatus",
    "ConfidenceThresholds",
    "DefaultProbabilities",
    "OddsLimits",
    "StatisticalThresholds",
    "MATCH_OUTCOME",
    "MATCH_STATUS",
    "CONFIDENCE_THRESHOLDS",
    "DEFAULT_PROBABILITIES",
    "ODDS_LIMITS",
    "STATISTICAL_THRESHOLDS",
    # V4.17: 向后兼容常量（整数）
    "HOME_WIN",
    "DRAW",
    "AWAY_WIN",
    # V4.17: 比赛状态常量（字符串）
    "STATUS_FINISHED",
    "STATUS_LIVE",
    "STATUS_SCHEDULED",
    "STATUS_CANCELLED",
    # 工具函数
    "get_constants",
    "reload_constants",
    # 原有常量
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
    "CalculationThresholds",
    "Constants",
    "FinancialMath",
    "FootballConstants",
    "OddsConstants",
    "PrecisionContext",
    "ProbabilityConstants",
    "ScoringConstants",
    "StatisticalConstants",
    "ValidationConstants",
]
