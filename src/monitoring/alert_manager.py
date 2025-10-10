"""
告警管理器
Alert Manager

实现数据质量监控和异常检测的告警机制。
"""

# 导入所有必要的类，保持向后兼容
from .alert_models import (
    AlertSeverity,
    AlertType,
    AlertLevel,
    AlertStatus,
    AlertChannel,
    Alert,
    AlertRule,
)

from .alert_handlers import (
    PrometheusMetrics,
    AlertHandler,
    LogHandler,
    PrometheusHandler,
    WebhookHandler,
    EmailHandler,
)

from .alert_manager_core import AlertManager

# 导出所有公共接口
__all__ = [
    # 枚举
    "AlertSeverity",
    "AlertType",
    "AlertLevel",
    "AlertStatus",
    "AlertChannel",
    # 模型
    "Alert",
    "AlertRule",
    # 处理器
    "AlertHandler",
    "LogHandler",
    "PrometheusHandler",
    "WebhookHandler",
    "EmailHandler",
    "PrometheusMetrics",
    # 主要类
    "AlertManager",
]
