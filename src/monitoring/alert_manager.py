"""
告警管理器
Alert Manager

统一告警管理入口，向后兼容原有接口。
"""

import logging
from enum import Enum
from typing import Dict, List, Optional
from datetime import datetime

logger = logging.getLogger(__name__)


class AlertSeverity(Enum):
    """警报严重程度"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class AlertType(Enum):
    """警报类型"""
    SYSTEM = "system"
    DATABASE = "database"
    API = "api"


class Alert:
    """警报对象"""

    def __init__(self, name: str, severity: AlertSeverity, alert_type: AlertType, message: str):
        self.name = name
        self.severity = severity
        self.type = alert_type
        self.message = message
        self.timestamp = datetime.utcnow()


class AlertRule:
    """警报规则"""

    def __init__(self, name: str, condition: str, severity: AlertSeverity):
        self.name = name
        self.condition = condition
        self.severity = severity
        self.enabled = True


class AlertManager:
    """警报管理器 - 简化版本"""

    def __init__(self):
        self.alerts: List[Alert] = []
        self.alert_rules = {}

    def create_alert(self, name: str, severity: AlertSeverity, alert_type: AlertType, message: str):
        """创建警报"""
        alert = Alert(name, severity, alert_type, message)
        self.alerts.append(alert)
        logger.info(f"Created alert: {name} - {message}")
        return alert

    def get_active_alerts(self) -> List[Alert]:
        """获取活跃警报"""
        return self.alerts[-10:]  # 返回最近10个


# 为了向后兼容，保留原有的类名
AlertLevel = AlertSeverity
AlertStatus = str  # 简化处理
AlertChannel = str  # 简化处理


class PrometheusMetrics:
    """Prometheus指标 - 简化版本"""
    pass


class AlertChannelManager:
    """警报通道管理器 - 简化版本"""
    pass


class AlertRuleEngine:
    """警报规则引擎 - 简化版本"""
    pass


class AlertAggregator:
    """警报聚合器 - 简化版本"""
    pass


class LogHandler:
    """日志处理器 - 简化版本"""
    pass


class PrometheusHandler:
    """Prometheus处理器 - 简化版本"""
    pass


class WebhookHandler:
    """Webhook处理器 - 简化版本"""
    pass


class EmailHandler:
    """邮件处理器 - 简化版本"""
    pass

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
