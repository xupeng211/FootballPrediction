"""
日志告警渠道
Log Alert Channel

将告警记录到日志系统。
Logs alerts to the logging system.
"""

import logging
from typing import Any, Dict

from .base_channel import BaseAlertChannel
from ...alert_manager_mod.models import Alert


class LogChannel(BaseAlertChannel):
    """
    日志告警渠道
    Log Alert Channel

    将告警记录到日志系统。
    Logs alerts to the logging system.
    """

    def __init__(self, name: str = "log", config: Dict[str, Any] | None = None):
        """
        初始化日志渠道
        Initialize Log Channel

        Args:
            name: 渠道名称 / Channel name
            config: 渠道配置 / Channel configuration
        """
        super().__init__(name, config)
        self.log_level = self.config.get("log_level", "warning")
        self.include_details = self.config.get("include_details", True)

    async def send(self, alert: Alert) -> bool:
        """
        记录告警到日志
        Log Alert

        Args:
            alert: 告警对象 / Alert object

        Returns:
            bool: 是否记录成功 / Whether logged successfully
        """
        try:
            log_message = f"[ALERT] {alert.title}: {alert.message}"
            log_data = {
                "alert_id": alert.alert_id,
                "title": alert.title,
                "message": alert.message,
                "level": alert.level.value,
                "severity": alert.severity.value,
                "source": alert.source,
                "status": alert.status.value,
                "created_at": alert.created_at.isoformat(),
                "labels": alert.labels,
                "annotations": alert.annotations,
            }

            # 根据告警级别选择日志级别
            if alert.level.value == "critical":
                self.logger.critical(log_message, extra=log_data)
            elif alert.level.value == "error":
                self.logger.error(log_message, extra=log_data)
            elif alert.level.value == "warning":
                self.logger.warning(log_message, extra=log_data)
            else:
                self.logger.info(log_message, extra=log_data)

            return True

        except Exception as e:
            self.logger.error(f"Failed to log alert: {e}")
            return False
