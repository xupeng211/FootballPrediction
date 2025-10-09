"""
告警模型
Alert Models

定义告警相关的数据模型和枚举。
此文件已拆分为多个模块以提供更好的组织结构。
This file has been split into multiple modules for better organization.

为了向后兼容，此文件重新导出所有核心类和枚举。
For backward compatibility, this file re-exports all core classes and enums.
"""

import warnings

# 发出弃用警告
warnings.warn(
    "直接从 alert_manager_mod.models 导入已弃用。"
    "请从 src.monitoring.alerts.models 导入相关类。"
    "Direct imports from alert_manager_mod.models are deprecated. "
    "Please import from src.monitoring.alerts.models instead.",
    DeprecationWarning,
    stacklevel=2
)

# 从新模块重新导出所有核心类型
from ..alerts.models import (
    # 核心实体类
    Alert,
    AlertRule,

    # 枚举类型
    AlertSeverity,
    AlertType,
    AlertLevel,
    AlertStatus,
    AlertChannel,

    # 新增功能（可选导出）
    Incident,
    Escalation,
    EscalationRule,
    IncidentSeverity,
    IncidentStatus,
    EscalationStatus,
    NotificationStatus,

    # 序列化工具
    AlertSerializer,
    RuleSerializer,
    IncidentSerializer,
    EscalationSerializer,
    JSONSerializer,
)

# 保持向后兼容性的别名
# 所有类和枚举从上面的导入语句中获得

# 为了向后兼容，保留 __all__ 定义
__all__ = [
    # 核心实体类
    "Alert",
    "AlertRule",

    # 枚举类型
    "AlertSeverity",
    "AlertType",
    "AlertLevel",
    "AlertStatus",
    "AlertChannel",

    # 新增功能
    "Incident",
    "Escalation",
    "EscalationRule",
    "IncidentSeverity",
    "IncidentStatus",
    "EscalationStatus",
    "NotificationStatus",

    # 序列化工具
    "AlertSerializer",
    "RuleSerializer",
    "IncidentSerializer",
    "EscalationSerializer",
    "JSONSerializer",
]