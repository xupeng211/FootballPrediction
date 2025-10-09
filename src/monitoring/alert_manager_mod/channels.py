"""
告警渠道
Alert Channels

定义各种告警通知渠道的实现。
这个文件保持向后兼容性，重新导出新拆分的模块。
Defines various alert notification channels implementations.
This file maintains backward compatibility by re-exporting the split modules.
"""

# 导入所有拆分后的类以保持向后兼容性
from ..alerts.channels import (
    BaseAlertChannel,
    LogChannel,
    WebhookChannel,
    EmailChannel,
    SlackChannel,
    TeamsChannel,
    SMSChannel,
    AlertChannelManager,
)

# 为了保持完全的向后兼容性，也需要重新导出原始的PrometheusChannel
# 因为这个依赖于具体的metrics模块
from ..alerts.channels.base_channel import BaseAlertChannel as _BaseAlertChannel
from ...alert_manager_mod.models import Alert, AlertChannel as OriginalAlertChannel
import logging

logger = logging.getLogger(__name__)


class PrometheusChannel(_BaseAlertChannel):
    """
    Prometheus告警渠道
    Prometheus Alert Channel

    通过Prometheus指标暴露告警信息。
    Exposes alert information through Prometheus metrics.
    """

    def __init__(self, name: str = "prometheus", config=None):
        """
        初始化Prometheus渠道
        Initialize Prometheus Channel

        Args:
            name: 渠道名称 / Channel name
            config: 渠道配置 / Channel configuration
        """
        super().__init__(name, config)
        self.metrics = None

        # 延迟初始化指标
        try:
            from .metrics import PrometheusMetrics
            self.metrics = PrometheusMetrics()
        except ImportError:
            logger.warning("PrometheusMetrics not available, PrometheusChannel will be disabled")

    async def send(self, alert: Alert) -> bool:
        """
        更新Prometheus指标
        Update Prometheus Metrics

        Args:
            alert: 告警对象 / Alert object

        Returns:
            bool: 是否更新成功 / Whether updated successfully
        """
        try:
            if not self.metrics:
                return False

            # 记录告警创建
            self.metrics.record_alert_created(
                level=alert.level.value,
                alert_type=alert.type.value,
                source=alert.source
            )

            return True

        except Exception as e:
            logger.error(f"Failed to update Prometheus metrics: {e}")
            return False


# 导出所有类以保持向后兼容性
__all__ = [
    "BaseAlertChannel",
    "LogChannel",
    "PrometheusChannel",
    "WebhookChannel",
    "EmailChannel",
    "SlackChannel",
    "TeamsChannel",
    "SMSChannel",
    "AlertChannelManager",
]