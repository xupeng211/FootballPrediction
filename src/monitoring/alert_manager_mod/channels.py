"""
告警渠道管理
Alert Channel Management

统一管理不同的告警渠道。
"""

import logging
from typing import Any, Dict, List, Optional

from .models import Alert, AlertChannel
from .manager import (
    AlertHandler,
    LogHandler,
    PrometheusHandler,
    WebhookHandler,
    EmailHandler,
)

logger = logging.getLogger(__name__)


class AlertChannelManager:
    """告警渠道管理器"""

    def __init__(self):
        """初始化渠道管理器"""
        self.channels: Dict[AlertChannel, List[AlertHandler]] = {}
        self.channel_configs: Dict[AlertChannel, Dict[str, Any]] = {}

    def add_channel(
        self,
        channel: AlertChannel,
        handler: AlertHandler,
        config: Optional[Dict[str, Any]] = None,
    ) -> None:
        """
        添加告警渠道

        Args:
            channel: 渠道类型
            handler: 处理器实例
            config: 渠道配置
        """
        if channel not in self.channels:
            self.channels[channel] = []
        self.channels[channel].append(handler)

        if config:
            self.channel_configs[channel] = config

    def remove_channel(
        self, channel: AlertChannel, handler: Optional[AlertHandler] = None
    ) -> bool:
        """
        移除告警渠道

        Args:
            channel: 渠道类型
            handler: 特定处理器（可选）

        Returns:
            bool: 是否成功移除
        """
        if channel not in self.channels:
            return False

        if handler:
            if handler in self.channels[channel]:
                self.channels[channel].remove(handler)
                if not self.channels[channel]:
                    del self.channels[channel]
                return True
            return False
        else:
            del self.channels[channel]
            return True

    def send_alert(
        self, alert: Alert, channels: Optional[List[AlertChannel]] = None
    ) -> None:
        """
        发送告警到指定渠道

        Args:
            alert: 告警对象
            channels: 指定渠道列表（可选，默认使用所有渠道）
        """
        target_channels = channels or list(self.channels.keys())

        for channel in target_channels:
            if channel in self.channels:
                for handler in self.channels[channel]:
                    try:
                        handler.handle(alert)
                    except (ValueError, RuntimeError, TimeoutError) as e:
                        logger.error(f"Failed to send alert via {channel.value}: {e}")

    def get_channel_status(self) -> Dict[str, Any]:
        """
        获取渠道状态

        Returns:
            Dict[str, Any]: 渠道状态信息
        """
        return {
            "total_channels": len(self.channels),
            "channels": {
                channel.value: {
                    "handlers": len(handlers),
                    "config": self.channel_configs.get(channel, {}),
                }
                for channel, handlers in self.channels.items()
            },
        }

    @staticmethod
    def create_default_channels() -> "AlertChannelManager":
        """
        创建默认的渠道配置

        Returns:
            AlertChannelManager: 配置好的渠道管理器
        """
        manager = AlertChannelManager()

        # 添加日志渠道
        manager.add_channel(AlertChannel.LOG, LogHandler())

        # 添加 Prometheus 渠道
        try:
            from .metrics import PrometheusMetrics

            prometheus_metrics = PrometheusMetrics()
            manager.add_channel(
                AlertChannel.PROMETHEUS, PrometheusHandler(prometheus_metrics)
            )
        except (ValueError, RuntimeError, TimeoutError) as e:
            logger.warning(f"Failed to initialize Prometheus channel: {e}")

        return manager


# 为了向后兼容，导出原有的处理器类
LogChannel = LogHandler
PrometheusChannel = PrometheusHandler
WebhookChannel = WebhookHandler
EmailChannel = EmailHandler
