"""
告警渠道基类
Base Alert Channel

定义告警渠道的通用接口和基础功能。
Defines common interface and base functionality for alert channels.
"""

import logging
from abc import ABC, abstractmethod
from typing import Any, Dict, List

from ...alert_manager_mod.models import Alert

logger = logging.getLogger(__name__)


class BaseAlertChannel(ABC):
    """
    告警渠道基类
    Base Alert Channel

    定义告警渠道的通用接口。
    Defines common interface for alert channels.
    """

    def __init__(self, name: str, config: Dict[str, Any] | None = None):
        """
        初始化告警渠道
        Initialize Alert Channel

        Args:
            name: 渠道名称 / Channel name
            config: 渠道配置 / Channel configuration
        """
        self.name = name
        self.config = config or {}
        self.enabled = self.config.get("enabled", True)
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")

    @abstractmethod
    async def send(self, alert: Alert) -> bool:
        """
        发送告警
        Send Alert

        Args:
            alert: 告警对象 / Alert object

        Returns:
            bool: 是否发送成功 / Whether sent successfully
        """
        pass

    async def send_batch(self, alerts: List[Alert]) -> Dict[str, bool]:
        """
        批量发送告警
        Send Batch Alerts

        Args:
            alerts: 告警列表 / List of alerts

        Returns:
            Dict[str, bool]: 发送结果 / Send results
        """
        results = {}
        for alert in alerts:
            results[alert.alert_id] = await self.send(alert)
        return results

    def is_enabled(self) -> bool:
        """
        检查渠道是否启用
        Check if Channel is Enabled

        Returns:
            bool: 是否启用 / Whether enabled
        """
        return self.enabled

    def enable(self):
        """启用渠道"""
        self.enabled = True

    def disable(self):
        """禁用渠道"""
        self.enabled = False