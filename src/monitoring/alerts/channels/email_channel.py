"""
��Jf S
Email Alert Channel

Ǯ��Jf
Sends alerts via email.
"""

import json
from typing import Any, Dict, List

from .base_channel import BaseAlertChannel
from ...alert_manager_mod.models import Alert


class EmailChannel(BaseAlertChannel):
    """
    ��Jf S
    Email Alert Channel

    Ǯ��Jf
    Sends alerts via email.
    """

    def __init__(self, name: str = "email", config: Dict[str, Any] | None = None):
        """
        ��� S
        Initialize Email Channel

        Args:
            name:  S� / Channel name
            config:  SMn / Channel configuration
        """
        super().__init__(name, config)
        self.smtp_host = self.config.get("smtp_host")
        self.smtp_port = self.config.get("smtp_port", 587)
        self.username = self.config.get("username")
        self.password = self.config.get("password")
        self.from_address = self.config.get("from_address")
        self.to_addresses = self.config.get("to_addresses", [])
        self.use_tls = self.config.get("use_tls", True)

        if not all([self.smtp_host, self.from_address, self.to_addresses]):
            self.logger.warning("Email channel not properly configured")
            self.enabled = False

    async def send(self, alert: Alert) -> bool:
        """
        ���Jf
        Send Email Alert

        Args:
            alert: Jf�a / Alert object

        Returns:
            bool: /&�� / Whether sent successfully
        """
        if not self.is_enabled():
            return False

        try:
            import aiosmtplib

            subject = f"[{alert.level.value.upper()}] {alert.title}"
            body = self._format_email_body(alert)

            message = aiosmtplib.SMTPMessage()
            message["From"] = self.from_address
            message["To"] = ", ".join(self.to_addresses)
            message["Subject"] = subject
            message.set_content(body)

            smtp = aiosmtplib.SMTP(
                hostname=self.smtp_host,
                port=self.smtp_port,
                use_tls=self.use_tls,
            )

            await smtp.connect()
            if self.username and self.password:
                await smtp.login(self.username, self.password)
            await smtp.send_message(message)
            await smtp.quit()

            self.logger.info(f"Email sent successfully: {alert.alert_id}")
            return True

        except Exception as e:
            self.logger.error(f"Failed to send email: {e}")
            return False

    def _format_email_body(self, alert: Alert) -> str:
        """
        <��c�
        Format Email Body

        Args:
            alert: Jf�a / Alert object

        Returns:
            str: <���c� / Formatted email body
        """
        body = f"""
Jf� / Alert Notification
============================

JfID / Alert ID: {alert.alert_id}
� / Title: {alert.title}
�o / Message: {alert.message}
�+ / Level: {alert.level.value}
%�� / Severity: {alert.severity.value}
e� / Source: {alert.source}
� / Status: {alert.status.value}
��� / Created At: {alert.created_at.strftime('%Y-%m-%d %H:%M:%S UTC')}

~ / Labels:
{json.dumps(alert.labels, indent=2, ensure_ascii=False)}

�� / Annotations:
{json.dumps(alert.annotations, indent=2, ensure_ascii=False)}

---
d��1Jf���� / This email was sent automatically by the alert system
        """.strip()

        return body

    async def send_batch(self, alerts: List[Alert]) -> Dict[str, bool]:
        """
        y����Jf
        Send Batch Email Alerts

        Args:
            alerts: Jfh / List of alerts

        Returns:
            Dict[str, bool]: �Ӝ / Send results
        """
        results = {}

        # ����*��M���'
        for alert in alerts:
            results[alert.alert_id] = await self.send(alert)

        return results