"""
告警模型包
Alert Models Package

导出所有告警相关的模型和工具类。
Exports all alert-related models and utility classes.
"""

# 枚举类型
from .enums import (
    AlertChannel,
    AlertLevel,
    AlertSeverity,
    AlertStatus,
    AlertType,
    EscalationStatus,
    IncidentSeverity,
    IncidentStatus,
    NotificationStatus,
)

# 核心实体类
from .alert import Alert
from .rule import AlertRule

# 事件和升级管理
from .incident import Incident
from .escalation import Escalation, EscalationRule

# 通知模板
from .templates import (
    EmailTemplate,
    SMSTemplate,
    SlackTemplate,
    TemplateManager,
    WebhookTemplate,
)

# 序列化工具
from .serializers import (
    AlertSerializer,
    EscalationSerializer,
    EnumSerializer,
    IncidentSerializer,
    JSONSerializer,
    RuleSerializer,
    ValidationSerializer,
)

__all__ = [
    # 枚举类型
    "AlertChannel",
    "AlertLevel",
    "AlertSeverity",
    "AlertStatus",
    "AlertType",
    "EscalationStatus",
    "IncidentSeverity",
    "IncidentStatus",
    "NotificationStatus",

    # 核心实体类
    "Alert",
    "AlertRule",

    # 事件和升级管理
    "Incident",
    "Escalation",
    "EscalationRule",

    # 通知模板
    "EmailTemplate",
    "SMSTemplate",
    "SlackTemplate",
    "WebhookTemplate",
    "TemplateManager",

    # 序列化工具
    "AlertSerializer",
    "RuleSerializer",
    "IncidentSerializer",
    "EscalationSerializer",
    "EnumSerializer",
    "JSONSerializer",
    "ValidationSerializer",
]