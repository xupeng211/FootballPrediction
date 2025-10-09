"""
SlackJf S
Slack Alert Channel

ÇSlack webhookÑJf
Sends alerts via Slack webhook.
"""

from typing import Any, Dict

import aiohttp

from .base_channel import BaseAlertChannel
from ...alert_manager_mod.models import Alert


class SlackChannel(BaseAlertChannel):
    """
    SlackJf S
    Slack Alert Channel

    ÇSlack webhookÑJf
    Sends alerts via Slack webhook.
    """

    def __init__(self, name: str = "slack", config: Dict[str, Any] | None = None):
        """
        ËSlack S
        Initialize Slack Channel

        Args:
            name:  Sð / Channel name
            config:  SMn / Channel configuration
        """
        super().__init__(name, config)
        self.webhook_url = self.config.get("webhook_url")
        self.channel = self.config.get("channel")
        self.username = self.config.get("username", "AlertBot")
        self.icon_emoji = self.config.get("icon_emoji", ":warning:")

        if not self.webhook_url:
            self.logger.warning("Slack webhook URL not configured")
            self.enabled = False

    async def send(self, alert: Alert) -> bool:
        """
        ÑSlackˆo
        Send Slack Message

        Args:
            alert: Jfùa / Alert object

        Returns:
            bool: /&ÑŸ / Whether sent successfully
        """
        if not self.is_enabled():
            return False

        try:
            payload = {
                "username": self.username,
                "icon_emoji": self.icon_emoji,
                "text": f"[{alert.level.value.upper()}] {alert.title}",
                "attachments": [
                    {
                        "color": self._get_color_by_level(alert.level.value),
                        "fields": [
                            {
                                "title": "Message",
                                "value": alert.message,
                                "short": False,
                            },
                            {
                                "title": "Source",
                                "value": alert.source,
                                "short": True,
                            },
                            {
                                "title": "Severity",
                                "value": alert.severity.value,
                                "short": True,
                            },
                            {
                                "title": "Alert ID",
                                "value": alert.alert_id,
                                "short": True,
                            },
                            {
                                "title": "Created At",
                                "value": alert.created_at.strftime('%Y-%m-%d %H:%M:%S UTC'),
                                "short": True,
                            },
                        ],
                    }
                ],
            }

            if self.channel:
                payload["channel"] = self.channel

            async with aiohttp.ClientSession() as session:
                async with session.post(
                    self.webhook_url,
                    json=payload,
                    timeout=10
                ) as response:
                    success = response.status == 200
                    if success:
                        self.logger.info(f"Slack message sent: {alert.alert_id}")
                    else:
                        self.logger.warning(f"Slack API returned {response.status}")
                    return success

        except Exception as e:
            self.logger.error(f"Failed to send Slack message: {e}")
            return False

    def _get_color_by_level(self, level: str) -> str:
        """
        9n§+·Öœr
        Get Color by Level

        Args:
            level: Jf§+ / Alert level

        Returns:
            str: œrã / Color code
        """
        colors = {
            "info": "#36a64f",      # ÿr
            "warning": "#ff9500",   # Yr
            "error": "#ff0000",     # ¢r
            "critical": "#8b0000",  # ñ¢r
        }
        return colors.get(level, "#808080")  # Ø¤pr