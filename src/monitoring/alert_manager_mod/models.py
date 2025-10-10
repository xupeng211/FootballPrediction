"""
告警数据模型
Alert Data Models

定义告警相关的数据结构和枚举。
"""

from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Dict, List, Optional


class AlertSeverity(Enum):
    """告警严重程度"""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class AlertType(Enum):
    """告警类型"""

    ERROR = "error"
    WARNING = "warning"
    INFO = "info"
    SYSTEM = "system"


class AlertLevel(Enum):
    """告警级别（向后兼容）"""

    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


class AlertStatus(Enum):
    """告警状态"""

    ACTIVE = "active"
    RESOLVED = "resolved"
    SILENCED = "silenced"


class AlertChannel(Enum):
    """告警渠道"""

    LOG = "log"
    PROMETHEUS = "prometheus"
    EMAIL = "email"
    SLACK = "slack"
    WEBHOOK = "webhook"


class Alert:
    """告警对象"""

    def __init__(
        self,
        title: str,
        message: str,
        level: AlertLevel,
        source: str,
        timestamp: Optional[datetime] = None,
        context: Optional[Dict[str, Any]] = None,
        alert_id: Optional[str] = None,
        status: AlertStatus = AlertStatus.ACTIVE,
        severity: Optional[AlertSeverity] = None,
        alert_type: Optional[AlertType] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> None:
        self.id = alert_id or self._generate_alert_id()
        self.title = title
        self.message = message
        self.level = level
        self.source = source
        self.timestamp = timestamp or datetime.utcnow()
        self.context = context or {}
        self.status = status
        self.severity = severity or self._level_to_severity(level)
        self.type = alert_type or self._level_to_type(level)
        self.metadata = metadata or {}
        self.resolved_at: Optional[datetime] = None
        self.silenced_until: Optional[datetime] = None

    def _level_to_type(self, level: AlertLevel) -> AlertType:
        """转换级别为类型"""
        mapping = {
            AlertLevel.INFO: AlertType.INFO,
            AlertLevel.WARNING: AlertType.WARNING,
            AlertLevel.ERROR: AlertType.ERROR,
            AlertLevel.CRITICAL: AlertType.ERROR,
        }
        return mapping.get(level, AlertType.INFO)

    def _level_to_severity(self, level: AlertLevel) -> AlertSeverity:
        """转换级别为严重程度"""
        mapping = {
            AlertLevel.INFO: AlertSeverity.LOW,
            AlertLevel.WARNING: AlertSeverity.MEDIUM,
            AlertLevel.ERROR: AlertSeverity.HIGH,
            AlertLevel.CRITICAL: AlertSeverity.CRITICAL,
        }
        return mapping.get(level, AlertSeverity.LOW)

    def _generate_alert_id(self) -> str:
        """生成告警ID"""
        import uuid

        return str(uuid.uuid4())

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "id": self.id,
            "title": self.title,
            "message": self.message,
            "level": self.level.value,
            "severity": self.severity.value,
            "type": self.type.value,
            "source": self.source,
            "timestamp": self.timestamp.isoformat(),
            "status": self.status.value,
            "context": self.context,
            "metadata": self.metadata,
            "resolved_at": self.resolved_at.isoformat() if self.resolved_at else None,
            "silenced_until": self.silenced_until.isoformat()
            if self.silenced_until
            else None,
        }

    def resolve(self) -> None:
        """解决告警"""
        self.status = AlertStatus.RESOLVED
        self.resolved_at = datetime.utcnow()

    def silence(self, duration: Optional[timedelta] = None) -> None:
        """静默告警"""
        self.status = AlertStatus.SILENCED
        if duration:
            self.silenced_until = datetime.utcnow() + duration
        else:
            self.silenced_until = datetime.utcnow() + timedelta(hours=1)


class AlertRule:
    """告警规则"""

    def __init__(
        self,
        rule_id: str,
        name: str,
        condition: str,
        severity: AlertSeverity,
        channels: List[AlertChannel],
        enabled: bool = True,
        throttle_duration: Optional[timedelta] = None,
        description: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> None:
        self.id = rule_id
        self.name = name
        self.condition = condition
        self.severity = severity
        self.channels = channels
        self.enabled = enabled
        self.throttle_duration = throttle_duration or timedelta(minutes=5)
        self.description = description
        self.metadata = metadata or {}
        self.last_triggered: Optional[datetime] = None
        self.trigger_count = 0


# 不需要重新定义，类已经在上面定义了
