"""
告警管理器
Alert Manager

统一告警管理入口，向后兼容原有接口。
"""

# 为了向后兼容，从模块化实现重新导出核心类
from .alert_manager_mod import (
    AlertManager,
    Alert,
    AlertRule,
    AlertSeverity,
    AlertType,
    AlertLevel,
    AlertStatus,
    AlertChannel,
    PrometheusMetrics,
    AlertChannelManager,
    AlertRuleEngine,
    AlertAggregator,
    LogHandler,
    PrometheusHandler,
    WebhookHandler,
    EmailHandler,
)

__all__ = [
    "AlertManager",
    "Alert",
    "AlertRule",
    "AlertSeverity",
    "AlertType",
    "AlertLevel",
    "AlertStatus",
    "AlertChannel",
    "PrometheusMetrics",
    "AlertChannelManager",
    "AlertRuleEngine",
    "AlertAggregator",
    "LogHandler",
    "PrometheusHandler",
    "WebhookHandler",
    "EmailHandler",
]
