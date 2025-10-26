"""
告警处理器
Alert Handlers

处理不同类型的告警输出。
"""

import logging
from typing import Any, Dict, List, Optional

from prometheus_client import CollectorRegistry, Counter, Gauge, Histogram

from .alert_manager_mod.models import Alert, AlertChannel

class PrometheusMetrics:
    """Prometheus 指标管理"""

    def __init__(self, registry: Optional[CollectorRegistry] = None) -> None:
        self.registry = registry or CollectorRegistry()

        # 定义指标
        self.alerts_total = Counter(
            "alerts_total",
            "Total number of alerts",
            ["severity", "type", "source"],
            registry=self.registry,
        )

        self.active_alerts = Gauge(
            "active_alerts",
            "Number of active alerts",
            ["severity", "source"],
            registry=self.registry,
        )

        self.alert_duration = Histogram(
            "alert_duration_seconds",
            "Alert resolution duration",
            ["severity"],
            registry=self.registry,
        )

    def increment_counter(self, alert: Alert) -> None:
        """增加告警计数"""
        self.alerts_total.labels(
            severity=alert.severity.value, type=alert.type.value, source=alert.source
        ).inc()

    def set_active_gauge(self, alerts: List[Alert]) -> None:
        """设置活跃告警数量"""
        # 重置所有活跃告警
        self.active_alerts.clear()

        # 按严重程度和来源分组
        for alert in alerts:
            if alert.status.value == "active":
                self.active_alerts.labels(
                    severity=alert.severity.value, source=alert.source
                ).set(1)

    def observe_resolution_time(self, alert: Alert, duration: float) -> None:
        """记录告警解决时间"""
        self.alert_duration.labels(severity=alert.severity.value).observe(duration)

class AlertHandler:
    """告警处理器基类"""

    def __init__(self, channel: AlertChannel) -> None:
        self.channel = channel

    async def handle(self, alert: Alert) -> bool:
        """处理告警"""
        raise NotImplementedError

    def get_name(self) -> str:
        """获取处理器名称"""
        return self.__class__.__name__

class LogHandler(AlertHandler):
    """日志告警处理器"""

    def __init__(self) -> None:
        super().__init__(AlertChannel.LOG)
        self.logger = logging.getLogger("alerts")

    async def handle(self, alert: Alert) -> bool:
        """处理日志告警"""
        try:
            # 根据严重程度选择日志级别
            level_map = {
                "low": logging.INFO,
                "medium": logging.WARNING,
                "high": logging.ERROR,
                "critical": logging.CRITICAL,
            }

            log_level = level_map.get(alert.severity.value, logging.INFO)

            # 格式化日志消息
            message = (
                f"[{alert.severity.value.upper()}] {alert.title} - {alert.message}"
            )
            if alert.context:
                message += f" | Context: {alert.context}"

            self.logger.log(log_level, message, extra={"alert": alert.to_dict()})
            return True

        except (ValueError, RuntimeError, TimeoutError) as e:
            self.logger.error(f"Failed to log alert: {str(e)}")
            return False

class PrometheusHandler(AlertHandler):
    """Prometheus 告警处理器"""

    def __init__(self, metrics: PrometheusMetrics) -> None:
        super().__init__(AlertChannel.PROMETHEUS)
        self.metrics = metrics

    async def handle(self, alert: Alert) -> bool:
        """处理 Prometheus 告警"""
        try:
            # 更新指标
            self.metrics.increment_counter(alert)
            return True

        except (ValueError, RuntimeError, TimeoutError) as e:
            logging.error(f"Failed to update Prometheus metrics: {str(e)}")
            return False

class WebhookHandler(AlertHandler):
    """Webhook 告警处理器"""

    def __init__(self, url: str, headers: Optional[Dict[str, str]] = None) -> None:
        super().__init__(AlertChannel.WEBHOOK)
        self.url = url
        self.headers = headers or {}

    async def handle(self, alert: Alert) -> bool:
        """处理 Webhook 告警"""
        try:
            import aiohttp

            async with aiohttp.ClientSession() as session:
                payload = {
                    "alert": alert.to_dict(),
                    "timestamp": alert.timestamp.isoformat(),
                }

                async with session.post(
                    self.url,
                    json=payload,
                    headers=self.headers,
                    timeout=aiohttp.ClientTimeout(total=10),
                ) as response:
                    return response.status == 200

        except (ValueError, RuntimeError, TimeoutError) as e:
            logging.error(f"Failed to send webhook alert: {str(e)}")
            return False

class EmailHandler(AlertHandler):
    """邮件告警处理器"""

    def __init__(self, smtp_config: Dict[str, Any]) -> None:
        super().__init__(AlertChannel.EMAIL)
        self.smtp_config = smtp_config

    async def handle(self, alert: Alert) -> bool:
        """处理邮件告警"""
        try:
            import smtplib
            from email.mime.text import MIMEText
            from email.mime.multipart import MIMEMultipart

            # 创建邮件
            msg = MIMEMultipart()
            msg["From"] = self.smtp_config["from"]
            msg["To"] = ", ".join(self.smtp_config["to"])
            msg["Subject"] = f"[{alert.severity.value.upper()}] {alert.title}"

            # 邮件正文
            body = f"""
            Alert: {alert.title}
            Level: {alert.level.value}
            Severity: {alert.severity.value}
            Source: {alert.source}
            Time: {alert.timestamp}

            Message:
            {alert.message}

            Context:
            {alert.context}
            """

            msg.attach(MIMEText(body, "plain"))

            # 发送邮件
            with smtplib.SMTP(
                self.smtp_config["host"], self.smtp_config["port"]
            ) as server:
                if self.smtp_config.get("use_tls"):
                    server.starttls()
                if self.smtp_config.get("username"):
                    server.login(
                        self.smtp_config["username"], self.smtp_config["password"]
                    )
                server.send_message(msg)

            return True

        except (ValueError, RuntimeError, TimeoutError) as e:
            logging.error(f"Failed to send email alert: {str(e)}")
            return False
