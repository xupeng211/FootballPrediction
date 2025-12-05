from typing import Optional

"""足球预测系统数据模型.

包含所有SQLAlchemy数据模型定义.
"""

from src.database.base import Base

from .audit_log import AuditAction, AuditLog, AuditLogSummary, AuditSeverity
from .data_collection_log import CollectionStatus, CollectionType, DataCollectionLog
from .features import Features, TeamType
from .league import League
from .match import Match, MatchResult, MatchStatus
from .odds import MarketType, Odds
from .predictions import PredictedResult, Predictions
from .raw_data import RawData, RawMatchData, RawOddsData, RawScoresData
from .team import Team
from .user import User

# 导入多租户相关类
from .tenant import (
    PermissionScope,
    ResourceType,
    RolePermission,
    Tenant,
    TenantPermission,
    TenantPlan,
    TenantRole,
    TenantStatus,
    UserRoleAssignment,
)

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
    "RawData",
    "RawMatchData",
    "RawOddsData",
    "RawScoresData",
    # 审计日志模型
    "AuditLog",
    "AuditLogSummary",
    # 多租户模型
    "Tenant",
    "TenantRole",
    "TenantPermission",
    "RolePermission",
    "UserRoleAssignment",
    # 枚举类
    "MatchStatus",
    "MatchResult",
    "MarketType",
    "TeamType",
    "PredictedResult",
    "CollectionStatus",
    "CollectionType",
    "AuditAction",
    "AuditSeverity",
    "TenantStatus",
    "TenantPlan",
    "PermissionScope",
    "ResourceType",
]