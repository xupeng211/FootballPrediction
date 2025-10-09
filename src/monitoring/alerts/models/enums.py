"""
告警枚举类型
Alert Enums

定义告警系统相关的所有枚举类型。
Defines all enumeration types for the alert system.
"""



class AlertSeverity(Enum):
    """
    告警严重程度枚举
    Alert Severity Enumeration

    定义告警的严重级别。
    Defines severity levels for alerts.
    """

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class AlertType(Enum):
    """
    告警类型枚举
    Alert Type Enumeration

    定义告警的类型分类。
    Defines type categories for alerts.
    """

    ERROR = "error"
    WARNING = "warning"
    INFO = "info"
    SYSTEM = "system"
    PERFORMANCE = "performance"
    SECURITY = "security"
    BUSINESS = "business"


class AlertLevel(Enum):
    """
    告警级别枚举（向后兼容）
    Alert Level Enumeration (Backward Compatible)

    保持与旧版本的兼容性。
    Maintains compatibility with older versions.
    """

    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


class AlertStatus(Enum):
    """
    告警状态枚举
    Alert Status Enumeration

    定义告警的生命周期状态。
    Defines lifecycle states for alerts.
    """

    ACTIVE = "active"
    RESOLVED = "resolved"
    SILENCED = "silenced"
    SUPPRESSED = "suppressed"


class AlertChannel(Enum):
    """
    告警渠道枚举
    Alert Channel Enumeration

    定义告警通知的发送渠道。
    Defines notification channels for alerts.
    """

    LOG = "log"
    PROMETHEUS = "prometheus"
    WEBHOOK = "webhook"
    EMAIL = "email"
    SLACK = "slack"
    SMS = "sms"
    DINGTALK = "dingtalk"
    WECHAT = "wechat"


class IncidentStatus(Enum):
    """
    事件状态枚举
    Incident Status Enumeration

    定义告警事件的状态。
    Defines status for alert incidents.
    """

    OPEN = "open"
    INVESTIGATING = "investigating"
    RESOLVED = "resolved"
    CLOSED = "closed"


class IncidentSeverity(Enum):
    """
    事件严重程度枚举
    Incident Severity Enumeration

    定义事件严重级别。
    Defines severity levels for incidents.
    """

    MINOR = "minor"
    MAJOR = "major"
    CRITICAL = "critical"
    BLOCKER = "blocker"


class EscalationStatus(Enum):
    """
    升级状态枚举
    Escalation Status Enumeration

    定义告警升级的状态。
    Defines status for alert escalations.
    """

    PENDING = "pending"
    TRIGGERED = "triggered"
    ACKNOWLEDGED = "acknowledged"
    RESOLVED = "resolved"


class NotificationStatus(Enum):
    """
    通知状态枚举
    Notification Status Enumeration

    定义通知发送状态。
    Defines notification delivery status.
    """

    PENDING = "pending"

    SENT = "sent"
    DELIVERED = "delivered"
    FAILED = "failed"
    RETRY = "retry"