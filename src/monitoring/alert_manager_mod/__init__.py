"""
告警管理器模块
Alert Manager Module

提供数据质量监控和异常检测的告警机制。
"""

from .models import (
    Alert,
    AlertRule,
    AlertSeverity,
    AlertType,
    AlertLevel,
    AlertStatus,
    AlertChannel,
)

from .metrics import PrometheusMetrics

from .channels import (
    LogChannel,
    PrometheusChannel,
    WebhookChannel,
    EmailChannel,
    AlertChannelManager,
)

from .manager import AlertManager

from .rules import AlertRuleEngine

from .aggregator import AlertAggregator

__all__ = [
    # 模型
    "Alert",
    "AlertRule",
    "AlertSeverity",
    "AlertType",
    "AlertLevel",
    "AlertStatus",
    "AlertChannel",
    # 指标
    "PrometheusMetrics",
    # 渠道
    "LogChannel",
    "PrometheusChannel",
    "WebhookChannel",
    "EmailChannel",
    "AlertChannelManager",
    # 管理器
    "AlertManager",
    # 规则引擎
    "AlertRuleEngine",
    # 聚合器
    "AlertAggregator",
]
