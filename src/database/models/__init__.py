"""
足球预测系统数据模型

包含所有SQLAlchemy数据模型定义。
"""

from ..base import Base
from .audit_log import AuditAction, AuditLog, AuditLogSummary, AuditSeverity
from .data_collection_log import (CollectionStatus, CollectionType,
                                  DataCollectionLog)
from .features import Features, TeamType
from .league import League
from .match import Match, MatchStatus
from .odds import MarketType, Odds
from .predictions import PredictedResult, Predictions
from .raw_data import RawMatchData, RawOddsData, RawScoresData
from .team import Team
from .user import User

# 为API兼容性创建别名
Prediction = Predictions

# 导出所有模型和枚举类
__all__ = [
    # 基础类
    "Base",
    # 核心业务模型
    "League",
    "Team",
    "User",
    "Match",
    "Odds",
    "Features",
    "Predictions",
    "Prediction",  # 别名
    # 数据管道模型
    "DataCollectionLog",
    "RawMatchData",
    "RawOddsData",
    "RawScoresData",
    # 审计日志模型
    "AuditLog",
    "AuditLogSummary",
    # 枚举类
    "MatchStatus",
    "MarketType",
    "TeamType",
    "PredictedResult",
    "CollectionStatus",
    "CollectionType",
    "AuditAction",
    "AuditSeverity",
]
