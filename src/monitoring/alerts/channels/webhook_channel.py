"""
WebhookJf S
Webhook Alert Channel

ÇHTTP webhookÑJf
Sends alerts via HTTP webhook.
"""

import asyncio
import json
from datetime import datetime
from typing import Any, Dict, List

import aiohttp

from .base_channel import BaseAlertChannel
from ...alert_manager_mod.models import Alert


class WebhookChannel(BaseAlertChannel):
    """
    WebhookJf S
    Webhook Alert Channel

    ÇHTTP webhookÑJf
    Sends alerts via HTTP webhook.
    """

    def __init__(self, name: str = "webhook", config: Dict[str, Any] | None = None):
        """
        ËWebhook S
        Initialize Webhook Channel

        Args:
            name:  Sð / Channel name
            config:  SMn / Channel configuration
        """
        super().__init__(name, config)
        self.url = self.config.get("url")
        self.method = self.config.get("method", "POST").upper()
        self.headers = self.config.get("headers", {"Content-Type": "application/json"})
        self.timeout = self.config.get("timeout", 10)
        self.retry_count = self.config.get("retry_count", 3)
        self.retry_delay = self.config.get("retry_delay", 1)

        if not self.url:
            raise ValueError("Webhook URL is required")

    async def send(self, alert: Alert) -> bool:
        """
        ÑWebhook÷B
        Send Webhook Request

        Args:
            alert: Jfùa / Alert object

        Returns:
            bool: /&ÑŸ / Whether sent successfully
        """
        if not self.is_enabled():
            return False

        payload = {
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
            "timestamp": datetime.utcnow().isoformat(),
        }

        for attempt in range(self.retry_count):
            try:
                async with aiohttp.ClientSession() as session:
                    async with session.request(
                        method=self.method,
                        url=self.url,
                        headers=self.headers,
                        json=payload,
                        timeout=self.timeout
                    ) as response:
                        if 200 <= response.status < 300:
                            self.logger.info(f"Webhook sent successfully: {alert.alert_id}")
                            return True
                        else:
                            self.logger.warning(
                                f"Webhook failed with status {response.status}: {alert.alert_id}"
                            )

            except Exception as e:
                self.logger.error(
                    f"Webhook attempt {attempt + 1} failed: {e}"
                )

            if attempt < self.retry_count - 1:
                await asyncio.sleep(self.retry_delay)

        return False

    async def send_batch(self, alerts: List[Alert]) -> Dict[str, bool]:
        """
        yÏÑWebhook
        Send Batch Webhook

        Args:
            alerts: Jfh / List of alerts

        Returns:
            Dict[str, bool]: ÑÓœ / Send results
        """
        if not self.is_enabled():
            return {alert.alert_id: False for alert in alerts}

        payload = {
            "alerts": [
                {
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
                for alert in alerts
            ],
            "timestamp": datetime.utcnow().isoformat(),
            "count": len(alerts),
        }

        try:
            async with aiohttp.ClientSession() as session:
                async with session.request(
                    method=self.method,
                    url=self.url,
                    headers=self.headers,
                    json=payload,
                    timeout=self.timeout
                ) as response:
                    success = 200 <= response.status < 300
                    return {alert.alert_id: success for alert in alerts}

        except Exception as e:
            self.logger.error(f"Batch webhook failed: {e}")
            return {alert.alert_id: False for alert in alerts}