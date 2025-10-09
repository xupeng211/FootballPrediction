"""
邮件告警通道
Email Alert Channel

通过邮件发送告警
Sends alerts via email.
"""

import json
from typing import Any, Dict, List

from .base_channel import BaseAlertChannel
from ...alert_manager_mod.models import Alert


class EmailChannel(BaseAlertChannel):
    """
    邮件告警通道
    Email Alert Channel

    通过邮件发送告警
    Sends alerts via email.
    """

    def __init__(self, name: str = "email", config: Dict[str, Any] | None = None):
        """
        初始化邮件通道
        Initialize Email Channel

        Args:
            name: 通道名称 / Channel name
            config: 通道配置 / Channel configuration
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
        发送邮件告警
        Send Email Alert

        Args:
            alert: 告警对象 / Alert object

        Returns:
            bool: 是否发送成功 / Whether sent successfully
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
        格式化邮件正文
        Format Email Body

        Args:
            alert: 告警对象 / Alert object

        Returns:
            str: 格式化的邮件正文 / Formatted email body
        """
        body = f"""
告警通知 / Alert Notification
============================

告警ID / Alert ID: {alert.alert_id}
标题 / Title: {alert.title}
消息 / Message: {alert.message}
级别 / Level: {alert.level.value}
严重程度 / Severity: {alert.severity.value}
来源 / Source: {alert.source}
状态 / Status: {alert.status.value}
创建时间 / Created At: {alert.created_at.strftime('%Y-%m-%d %H:%M:%S UTC')}

标签 / Labels:
{json.dumps(alert.labels, indent=2, ensure_ascii=False)}

注释 / Annotations:
{json.dumps(alert.annotations, indent=2, ensure_ascii=False)}

---
此邮件由告警系统自动发送 / This email was sent automatically by the alert system
        """.strip()

        return body

    async def send_batch(self, alerts: List[Alert]) -> Dict[str, bool]:
        """
        批量发送邮件告警
        Send Batch Email Alerts

        Args:
            alerts: 告警列表 / List of alerts

        Returns:
            Dict[str, bool]: 发送结果 / Send results
        """
        results = {}

        # 为每个告警单独发送邮件
        for alert in alerts:
            results[alert.alert_id] = await self.send(alert)

        return results
