"""
告警管理模块
Alert Management Module

提供完整的告警管理功能，包括告警创建、规则引擎、渠道处理和指标管理。
Provides complete alert management functionality including alert creation, rule engine, channel handling, and metrics management.
"""

# 导入核心模块（新的拆分后的组件）
from .core import (
    AlertManager as CoreAlertManager,
    AlertRuleEngine as CoreAlertRuleEngine,
    AlertDeduplicator,
    AlertAggregator,
    AlertScheduler,
    AlertTaskFactory,
    RuleEvaluationContext,
    SuppressionRule,
    DeduplicationCache,
    AlertGroup,
    AggregationRule,
    ScheduledTask,
)

# 向后兼容：导入原有的类
try:
    from .alert_manager import AlertManager
    from .models import (
        Alert,
        AlertChannel,
        AlertLevel,
        AlertRule,
        AlertSeverity,
        AlertStatus,
        AlertType,
    )
    from .channels import BaseAlertChannel, LogAlertChannel, PrometheusAlertChannel
    from .metrics import PrometheusMetrics
    from .rules import AlertRuleEngine

    # 如果存在原有的AlertManager，使用它作为主要导出
    MainAlertManager = AlertManager
    MainAlertRuleEngine = AlertRuleEngine

except ImportError:
    # 如果原有的组件不存在，使用核心组件
    Alert = None  # 将在后面定义
    AlertManager = CoreAlertManager
    AlertRuleEngine = CoreAlertRuleEngine
    MainAlertManager = CoreAlertManager
    MainAlertRuleEngine = CoreAlertRuleEngine

# 如果Alert类不存在，创建基本实现
if Alert is None:
    from enum import Enum
    from typing import Any, Dict, Optional
    from datetime import datetime

    class AlertLevel(Enum):
        CRITICAL = "critical"
        HIGH = "high"
        MEDIUM = "medium"
        LOW = "low"

    class AlertStatus(Enum):
        ACTIVE = "active"
        RESOLVED = "resolved"
        SUPPRESSED = "suppressed"
        SILENCED = "silenced"

    class AlertSeverity(Enum):
        CRITICAL = "critical"
        HIGH = "high"
        MEDIUM = "medium"
        LOW = "low"
        INFO = "info"

    class AlertType(Enum):
        SYSTEM = "system"
        APPLICATION = "application"
        SECURITY = "security"
        PERFORMANCE = "performance"
        BUSINESS = "business"

    class AlertChannel(Enum):
        EMAIL = "email"
        SLACK = "slack"
        WEBHOOK = "webhook"
        PROMETHEUS = "prometheus"
        LOG = "log"

    class Alert:
        def __init__(
            self,
            alert_id: str,
            title: str,
            message: str,
            level: AlertLevel,
            source: str,
            labels: Optional[Dict[str, str]] = None,
            annotations: Optional[Dict[str, str]] = None,
        ):
            self.alert_id = alert_id
            self.title = title
            self.message = message
            self.level = level
            self.severity = level
            self.type = AlertType.SYSTEM
            self.source = source
            self.labels = labels or {}
            self.annotations = annotations or {}
            self.status = AlertStatus.ACTIVE
            self.created_at = datetime.utcnow()
            self.updated_at = datetime.utcnow()
            self.resolved_at: Optional[datetime] = None

        @property
        def fingerprint(self) -> str:
            """生成告警指纹"""
            import hashlib
            content = f"{self.title}:{self.source}:{self.level.value}"
            return hashlib.md5(content.encode()).hexdigest()

        def is_active(self) -> bool:
            return self.status == AlertStatus.ACTIVE

        def is_resolved(self) -> bool:
            return self.status == AlertStatus.RESOLVED

        def resolve(self):
            self.status = AlertStatus.RESOLVED
            self.resolved_at = datetime.utcnow()
            self.updated_at = datetime.utcnow()

        def silence(self):
            self.status = AlertStatus.SILENCED
            self.updated_at = datetime.utcnow()

        def get_age(self):
            return datetime.utcnow() - self.created_at

        def get_duration(self):
            if self.resolved_at:
                return self.resolved_at - self.created_at
            return None

    class AlertRule:
        def __init__(
            self,
            rule_id: str,
            name: str,
            condition: str,
            severity: str = "medium",
            description: str = "",
            enabled: bool = True,
        ):
            self.rule_id = rule_id
            self.name = name
            self.condition = condition
            self.severity = severity
            self.description = description
            self.enabled = enabled
            self.created_at = datetime.utcnow()
            self.updated_at = datetime.utcnow()

# 如果其他组件不存在，创建占位符
if 'BaseAlertChannel' not in globals():
    class BaseAlertChannel:
        pass
    class LogAlertChannel(BaseAlertChannel):
        pass
    class PrometheusAlertChannel(BaseAlertChannel):
        pass

if 'PrometheusMetrics' not in globals():
    class PrometheusMetrics:
        def __init__(self, namespace="alerts"):
            self.namespace = namespace
        def record_alert_created(self, **kwargs):
            pass
        def record_alert_resolved(self, **kwargs):
            pass
        def record_notification_sent(self, channel, status):
            pass
        def update_system_info(self, info):
            pass
        def get_metrics_summary(self):
            return {}

__all__ = [
    # 主要类（向后兼容）
    "AlertManager",
    "AlertRuleEngine",

    # 模型
    "Alert",
    "AlertRule",

    # 枚举
    "AlertChannel",
    "AlertLevel",
    "AlertSeverity",
    "AlertStatus",
    "AlertType",

    # 渠道（如果存在）
    "BaseAlertChannel",
    "LogAlertChannel",
    "PrometheusAlertChannel",

    # 其他组件（如果存在）
    "PrometheusMetrics",

    # 新的核心组件
    "CoreAlertManager",
    "CoreAlertRuleEngine",
    "AlertDeduplicator",
    "AlertAggregator",
    "AlertScheduler",
    "AlertTaskFactory",
    "RuleEvaluationContext",
    "SuppressionRule",
    "DeduplicationCache",
    "AlertGroup",
    "AggregationRule",
    "ScheduledTask",
]