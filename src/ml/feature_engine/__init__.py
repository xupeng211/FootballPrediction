"""
FootballPrediction V23.0 Feature Engine
========================================

模块化特征工程框架 - 工业级重构版本

架构设计:
    - BaseProcessor: 抽象基类接口
    - Processors: 各类特征处理器插件
    - Models: Pydantic 数据模型
    - FeatureEngine: 主引擎编排器

V22.0 新增:
    - LineupValueProcessor: 阵容价值处理器（50+维）
    - AdvancedPassingProcessor: 深度传球处理器（60+维）

V23.0 新增:
    - MarketOddsProcessor: 市场赔率与偏见处理器（30+维）
    - InjuryImpactProcessor: 战损与伤停深度处理器（40+维）

作者: FootballPrediction Architecture Team
版本: V23.0-final
许可: MIT License
"""

from .base import BaseProcessor, ProcessorResult
from .engine import FeatureEngine
from .h2h_estimator import H2HEstimator
from .models import (
    FeatureVector,
    HomeAway,
    LeagueTier,
    LineupInfo,
    MatchContext,
    MatchData,
    MatchStatus,
    PlayerStats,
    ProcessingContext,
    TeamStats,
)

__all__ = [
    "BaseProcessor",
    "FeatureEngine",
    "FeatureVector",
    "H2HEstimator",
    "HomeAway",
    "LeagueTier",
    "LineupInfo",
    "MatchContext",
    "MatchData",
    "MatchStatus",
    "PlayerStats",
    "ProcessingContext",
    "ProcessorResult",
    "TeamStats",
]

__version__ = "23.0.0-final"
