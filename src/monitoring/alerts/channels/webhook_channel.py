"""
Webhook Alert Channel
Webhook Alert Channel

Sends alerts via HTTP webhook.
"""

import asyncio
import json
from datetime import datetime
from typing import Any, Dict, List

import aiohttp

from .base_channel import BaseAlertChannel
from ...core.exceptions import ValidationError


class WebhookChannel(BaseAlertChannel):
    """
    Webhook Alert Channel

    Sends alerts via HTTP webhook.
    """

    def __init__(self, name: str = "webhook", config: Dict[str, Any] | None = None):
        """
        Initialize Webhook Channel

        Args:
            name: Channel name
            config: Channel configuration
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

    async def send(self, alert) -> bool:
        """
        Send Webhook Request

        Args:
            alert: Alert object

        Returns:
            bool: Whether sent successfully
        """
        if not self.is_enabled():
            return False

        payload = {
            "alert_id": alert.alert_id,
            "title": alert.title,
            "message": alert.message,
            "severity": alert.severity,
            "source": alert.source,
            "timestamp": alert.timestamp.isoformat(),
            "metadata": alert.metadata,
        }

        for attempt in range(self.retry_count):
            try:
                async with aiohttp.ClientSession() as session:
                    async with session.request(
                        method=self.method,
                        url=self.url,
                        json=payload,
                        headers=self.headers,
                        timeout=aiohttp.ClientTimeout(total=self.timeout),
                    ) as response:
                        if response.status < 400:
                            return True
                        else:
                            self.logger.warning(
                                f"Webhook failed with status {response.status}: {await response.text()}"
                            )

            except Exception as e:
                self.logger.error(f"Webhook send failed (attempt {attempt + 1}): {e}")

            if attempt < self.retry_count - 1:
                await asyncio.sleep(self.retry_delay)

        return False

    async def send_batch(self, alerts: List) -> Dict[str, bool]:
        """
        Send Batch Webhook

        Args:
            alerts: List of alerts

        Returns:
            Dict[str, bool]: Send results
        """
        if not self.is_enabled():
            return {alert.alert_id: False for alert in alerts}

        payload = {
            "alerts": [
                {
                    "alert_id": alert.alert_id,
                    "title": alert.title,
                    "message": alert.message,
                    "severity": alert.severity,
                    "source": alert.source,
                    "timestamp": alert.timestamp.isoformat(),
                    "metadata": alert.metadata,
                }
                for alert in alerts
            ],
            "batch_timestamp": datetime.utcnow().isoformat(),
        }

        results = {}

        for attempt in range(self.retry_count):
            try:
                async with aiohttp.ClientSession() as session:
                    async with session.request(
                        method=self.method,
                        url=self.url,
                        json=payload,
                        headers=self.headers,
                        timeout=aiohttp.ClientTimeout(total=self.timeout),
                    ) as response:
                        if response.status < 400:
                            # Assume all alerts in batch were sent successfully
                            for alert in alerts:
                                results[alert.alert_id] = True
                            return results
                        else:
                            self.logger.warning(
                                f"Batch webhook failed with status {response.status}: {await response.text()}"
                            )

            except Exception as e:
                self.logger.error(
                    f"Batch webhook send failed (attempt {attempt + 1}): {e}"
                )

            if attempt < self.retry_count - 1:
                await asyncio.sleep(self.retry_delay)

        # If all retries failed, mark all as failed
        for alert in alerts:
            results[alert.alert_id] = False

        return results

    def validate_config(self) -> bool:
        """Validate webhook configuration"""
        if not self.url:
            return False

        # Basic URL validation
        if not (self.url.startswith("http://") or self.url.startswith("https://")):
            return False

        return True
