
"""Alert Manager - 简化版本"""

from enum import Enum
from typing import Dict, List, Optional
from datetime import datetime

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

class AlertManager:
    """警报管理器 - 简化版本"""

    def __init__(self):
        self.alerts: List[Alert] = []
        self.alert_rules = {}

    def create_alert(self, name: str, severity: AlertSeverity, alert_type: AlertType, message: str):
        """创建警报"""
        alert = Alert(name, severity, alert_type, message)
        self.alerts.append(alert)
        return alert

    def get_active_alerts(self) -> List[Alert]:
        """获取活跃警报"""
        return self.alerts[-10:]  # 返回最近10个


class AlertRule:
    """警报规则"""

    def __init__(self, name: str, condition: str, severity: AlertSeverity):
        self.name = name
        self.condition = condition
        self.severity = severity
        self.enabled = True
