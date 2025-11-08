"""
企业级异常告警系统
Enterprise Alert System

提供全面的异常检测、告警管理和通知功能。
"""

import logging
import smtplib
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from enum import Enum
from typing import Any

import aiohttp
from jinja2 import Template

logger = logging.getLogger(__name__)

# ============================================================================
# 告警数据结构
# ============================================================================


class AlertLevel(Enum):
    """告警级别"""

    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


class AlertStatus(Enum):
    """告警状态"""

    ACTIVE = "active"
    ACKNOWLEDGED = "acknowledged"
    RESOLVED = "resolved"
    SUPPRESSED = "suppressed"


@dataclass
class Alert:
    """告警对象"""

    id: str
    title: str
    description: str
    level: AlertLevel
    status: AlertStatus
    source: str
    timestamp: datetime
    metadata: dict[str, Any] = field(default_factory=dict)
    labels: dict[str, str] = field(default_factory=dict)
    acknowledged_by: str | None = None
    acknowledged_at: datetime | None = None
    resolved_at: datetime | None = None
    resolved_by: str | None = None


@dataclass
class AlertRule:
    """告警规则"""

    id: str
    name: str
    description: str
    condition: str  # 条件表达式
    level: AlertLevel
    enabled: bool = True
    cooldown: int = 300  # 冷却时间（秒）
    labels: dict[str, str] = field(default_factory=dict)
    annotations: dict[str, str] = field(default_factory=dict)
    last_triggered: datetime | None = None
    trigger_count: int = 0


@dataclass
class NotificationChannel:
    """通知渠道"""

    id: str
    name: str
    type: str  # email, slack, webhook
    config: dict[str, Any]
    enabled: bool = True
    filters: dict[str, Any] = field(default_factory=dict)  # 过滤条件


# ============================================================================
# 通知渠道实现
# ============================================================================


class NotificationProvider(ABC):
    """通知提供者基类"""

    @abstractmethod
    async def send_notification(
        self, alert: Alert, channel: NotificationChannel
    ) -> bool:
        """发送通知"""
        pass


class EmailNotificationProvider(NotificationProvider):
    """邮件通知提供者"""

    async def send_notification(
        self, alert: Alert, channel: NotificationChannel
    ) -> bool:
        """发送邮件通知"""
        try:
            config = channel.config
            smtp_server = config.get("smtp_server", "localhost")
            smtp_port = config.get("smtp_port", 587)
            username = config.get("username")
            password = config.get("password")
            from_email = config.get("from_email", username)
            to_emails = config.get("to_emails", [])

            if not to_emails:
                logger.warning("邮件通知没有配置收件人")
                return False

            # 创建邮件内容
            subject = f"[{alert.level.value.upper()}] {alert.title}"

            # 使用Jinja2模板生成邮件内容
            template = Template(self._get_email_template())
            html_content = template.render(
                alert=alert,
                level_color=self._get_level_color(alert.level),
                timestamp_str=alert.timestamp.strftime("%Y-%m-%d %H:%M:%S UTC"),
            )

            # 创建邮件
            msg = MIMEMultipart("alternative")
            msg["Subject"] = subject
            msg["From"] = from_email
            msg["To"] = ", ".join(to_emails)

            # 添加HTML内容
            html_part = MIMEText(html_content, "html", "utf-8")
            msg.attach(html_part)

            # 发送邮件
            server = smtplib.SMTP(smtp_server, smtp_port)
            server.starttls()
            server.login(username, password)
            server.send_message(msg)
            server.quit()

            logger.info(f"邮件通知发送成功: {alert.title}")
            return True

        except Exception as e:
            logger.error(f"发送邮件通知失败: {e}")
            return False

    def _get_email_template(self) -> str:
        """获取邮件模板"""
        return """
        <html>
        <head>
            <style>
                body { font-family: Arial, sans-serif; margin: 0; padding: 20px; background-color: #f5f5f5; }
                .container { max-width: 600px; margin: 0 auto; background-color: white; padding: 30px; border-radius: 10px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }
                .header { text-align: center; margin-bottom: 30px; }
                .alert-level { padding: 10px 20px; border-radius: 5px; color: white; font-weight: bold; margin-bottom: 20px; }
                .alert-content { margin-bottom: 30px; }
                .metadata { background-color: #f8f9fa; padding: 15px; border-radius: 5px; margin-top: 20px; }
                .footer { text-align: center; margin-top: 30px; color: #666; font-size: 12px; }
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>🚨 系统告警通知</h1>
                </div>

                <div class="alert-level" style="background-color: {{ level_color }};">
                    级别: {{ alert.level.value.upper() }}
                </div>

                <div class="alert-content">
                    <h2>{{ alert.title }}</h2>
                    <p><strong>描述:</strong> {{ alert.description }}</p>
                    <p><strong>来源:</strong> {{ alert.source }}</p>
                    <p><strong>时间:</strong> {{ timestamp_str }}</p>
                </div>

                {% if alert.metadata %}
                <div class="metadata">
                    <h3>详细信息</h3>
                    {% for key, value in alert.metadata.items() %}
                    <p><strong>{{ key }}:</strong> {{ value }}</p>
                    {% endfor %}
                </div>
                {% endif %}

                {% if alert.labels %}
                <div class="metadata">
                    <h3>标签</h3>
                    {% for key, value in alert.labels.items() %}
                    <span style="background-color: #e9ecef; padding: 3px 8px; margin: 2px; border-radius: 3px; font-size: 12px;">
                        {{ key }}: {{ value }}
                    </span>
                    {% endfor %}
                </div>
                {% endif %}

                <div class="footer">
                    <p>此邮件由 FootballPrediction 监控系统自动发送</p>
                </div>
            </div>
        </body>
        </html>
        """

    def _get_level_color(self, level: AlertLevel) -> str:
        """获取级别对应的颜色"""
        colors = {
            AlertLevel.INFO: "#17a2b8",
            AlertLevel.WARNING: "#ffc107",
            AlertLevel.ERROR: "#fd7e14",
            AlertLevel.CRITICAL: "#dc3545",
        }
        return colors.get(level, "#6c757d")


class SlackNotificationProvider(NotificationProvider):
    """Slack通知提供者"""

    async def send_notification(
        self, alert: Alert, channel: NotificationChannel
    ) -> bool:
        """发送Slack通知"""
        try:
            config = channel.config
            webhook_url = config.get("webhook_url")
            channel_name = config.get("channel", "#alerts")

            if not webhook_url:
                logger.warning("Slack通知没有配置webhook_url")
                return False

            # 构建Slack消息
            color = self._get_slack_color(alert.level)

            payload = {
                "channel": channel_name,
                "username": "FootballPrediction Monitor",
                "icon_emoji": self._get_slack_emoji(alert.level),
                "attachments": [
                    {
                        "color": color,
                        "title": f"[{alert.level.value.upper()}] {alert.title}",
                        "text": alert.description,
                        "fields": [
                            {"title": "来源", "value": alert.source, "short": True},
                            {
                                "title": "时间",
                                "value": alert.timestamp.strftime(
                                    "%Y-%m-%d %H:%M:%S UTC"
                                ),
                                "short": True,
                            },
                        ],
                        "footer": "FootballPrediction 监控系统",
                        "ts": int(alert.timestamp.timestamp()),
                    }
                ],
            }

            # 添加元数据
            if alert.metadata:
                metadata_fields = []
                for key, value in alert.metadata.items():
                    metadata_fields.append(
                        {"title": key, "value": str(value), "short": True}
                    )
                payload["attachments"][0]["fields"].extend(metadata_fields)

            # 发送请求
            async with aiohttp.ClientSession() as session:
                async with session.post(webhook_url, json=payload) as response:
                    if response.status == 200:
                        logger.info(f"Slack通知发送成功: {alert.title}")
                        return True
                    else:
                        logger.error(f"Slack通知发送失败: {response.status}")
                        return False

        except Exception as e:
            logger.error(f"发送Slack通知失败: {e}")
            return False

    def _get_slack_color(self, level: AlertLevel) -> str:
        """获取Slack颜色"""
        colors = {
            AlertLevel.INFO: "#36a64f",
            AlertLevel.WARNING: "#ff9500",
            AlertLevel.ERROR: "#ff0000",
            AlertLevel.CRITICAL: "#8b0000",
        }
        return colors.get(level, "#808080")

    def _get_slack_emoji(self, level: AlertLevel) -> str:
        """获取Slack表情"""
        emojis = {
            AlertLevel.INFO: ":information_source:",
            AlertLevel.WARNING: ":warning:",
            AlertLevel.ERROR: ":x:",
            AlertLevel.CRITICAL: ":rotating_light:",
        }
        return emojis.get(level, ":bell:")


class WebhookNotificationProvider(NotificationProvider):
    """Webhook通知提供者"""

    async def send_notification(
        self, alert: Alert, channel: NotificationChannel
    ) -> bool:
        """发送Webhook通知"""
        try:
            config = channel.config
            url = config.get("url")
            method = config.get("method", "POST").upper()
            headers = config.get("headers", {})
            timeout = config.get("timeout", 10)

            if not url:
                logger.warning("Webhook通知没有配置URL")
                return False

            # 构建payload
            payload = {
                "alert": {
                    "id": alert.id,
                    "title": alert.title,
                    "description": alert.description,
                    "level": alert.level.value,
                    "status": alert.status.value,
                    "source": alert.source,
                    "timestamp": alert.timestamp.isoformat(),
                    "metadata": alert.metadata,
                    "labels": alert.labels,
                }
            }

            # 发送请求
            async with aiohttp.ClientSession() as session:
                async with session.request(
                    method,
                    url,
                    json=payload,
                    headers=headers,
                    timeout=aiohttp.ClientTimeout(total=timeout),
                ) as response:
                    if 200 <= response.status < 300:
                        logger.info(f"Webhook通知发送成功: {alert.title}")
                        return True
                    else:
                        logger.error(f"Webhook通知发送失败: {response.status}")
                        return False

        except Exception as e:
            logger.error(f"发送Webhook通知失败: {e}")
            return False


# ============================================================================
# 告警管理器
# ============================================================================


class AlertManager:
    """告警管理器"""

    def __init__(self):
        self.rules: dict[str, AlertRule] = {}
        self.active_alerts: dict[str, Alert] = {}
        self.alert_history: list[Alert] = []
        self.channels: dict[str, NotificationChannel] = {}
        self.providers: dict[str, NotificationProvider] = {}
        self.suppression_rules: list[dict[str, Any]] = []
        self.max_history_size = 10000

        # 初始化通知提供者
        self._initialize_providers()

    def _initialize_providers(self):
        """初始化通知提供者"""
        self.providers = {
            "email": EmailNotificationProvider(),
            "slack": SlackNotificationProvider(),
            "webhook": WebhookNotificationProvider(),
        }

    async def add_rule(self, rule: AlertRule):
        """添加告警规则"""
        self.rules[rule.id] = rule
        logger.info(f"添加告警规则: {rule.name}")

    async def remove_rule(self, rule_id: str):
        """移除告警规则"""
        if rule_id in self.rules:
            del self.rules[rule_id]
            logger.info(f"移除告警规则: {rule_id}")

    async def add_channel(self, channel: NotificationChannel):
        """添加通知渠道"""
        self.channels[channel.id] = channel
        logger.info(f"添加通知渠道: {channel.name}")

    async def remove_channel(self, channel_id: str):
        """移除通知渠道"""
        if channel_id in self.channels:
            del self.channels[channel_id]
            logger.info(f"移除通知渠道: {channel_id}")

    async def evaluate_metrics(self, metrics: dict[str, Any]) -> list[Alert]:
        """评估指标并生成告警"""
        alerts = []
        current_time = datetime.now(UTC)

        for rule in self.rules.values():
            if not rule.enabled:
                continue

            # 检查冷却时间
            if (
                rule.last_triggered
                and (current_time - rule.last_triggered).total_seconds() < rule.cooldown
            ):
                continue

            # 评估规则条件
            if self._evaluate_condition(rule.condition, metrics):
                # 创建告警
                alert = Alert(
                    id=f"{rule.id}_{int(current_time.timestamp())}",
                    title=rule.name,
                    description=rule.description,
                    level=rule.level,
                    status=AlertStatus.ACTIVE,
                    source="metrics_evaluation",
                    timestamp=current_time,
                    labels=rule.labels.copy(),
                    annotations=rule.annotations.copy(),
                    metadata={
                        "rule_id": rule.id,
                        "condition": rule.condition,
                        "metrics": metrics,
                    },
                )

                # 检查抑制规则
                if not self._is_suppressed(alert):
                    alerts.append(alert)
                    self.active_alerts[alert.id] = alert
                    self.alert_history.append(alert)

                    # 更新规则触发信息
                    rule.last_triggered = current_time
                    rule.trigger_count += 1

                    # 发送通知
                    await self._send_notifications(alert)

        # 清理历史记录
        if len(self.alert_history) > self.max_history_size:
            self.alert_history = self.alert_history[-self.max_history_size :]

        return alerts

    def _evaluate_condition(self, condition: str, metrics: dict[str, Any]) -> bool:
        """评估条件表达式"""
        try:
            # 创建安全的执行环境
            safe_dict = {
                "__builtins__": {},
                "abs": abs,
                "min": min,
                "max": max,
                "len": len,
                "sum": sum,
                "float": float,
                "int": int,
                "str": str,
            }

            # 添加指标数据
            safe_dict.update(metrics)

            # 执行条件表达式
            result = eval(condition, safe_dict, {})
            return bool(result)

        except Exception as e:
            logger.error(f"评估条件表达式失败: {condition}, 错误: {e}")
            return False

    def _is_suppressed(self, alert: Alert) -> bool:
        """检查告警是否被抑制"""
        for suppression in self.suppression_rules:
            if self._matches_suppression(alert, suppression):
                logger.info(f"告警被抑制: {alert.title}")
                return True
        return False

    def _matches_suppression(self, alert: Alert, suppression: dict[str, Any]) -> bool:
        """检查告警是否匹配抑制规则"""
        # 检查标签匹配
        if "labels" in suppression:
            for key, value in suppression["labels"].items():
                if alert.labels.get(key) != value:
                    return False

        # 检查级别匹配
        if "levels" in suppression:
            if alert.level not in suppression["levels"]:
                return False

        # 检查时间窗口
        if "time_window" in suppression:
            window = suppression["time_window"]
            current_time = datetime.now(UTC)
            start_time = current_time - timedelta(minutes=window)

            # 检查是否有相同类型的活跃告警
            for active_alert in self.active_alerts.values():
                if (
                    active_alert.title == alert.title
                    and active_alert.timestamp > start_time
                ):
                    return True

        return True

    async def _send_notifications(self, alert: Alert):
        """发送通知"""
        for channel in self.channels.values():
            if not channel.enabled:
                continue

            # 检查渠道过滤条件
            if not self._matches_channel_filters(alert, channel):
                continue

            # 获取通知提供者
            provider = self.providers.get(channel.type)
            if not provider:
                logger.warning(f"未知的通知渠道类型: {channel.type}")
                continue

            # 发送通知
            try:
                success = await provider.send_notification(alert, channel)
                if success:
                    logger.info(f"通知发送成功: {channel.name} -> {alert.title}")
                else:
                    logger.warning(f"通知发送失败: {channel.name} -> {alert.title}")
            except Exception as e:
                logger.error(
                    f"发送通知异常: {channel.name} -> {alert.title}, 错误: {e}"
                )

    def _matches_channel_filters(
        self, alert: Alert, channel: NotificationChannel
    ) -> bool:
        """检查告警是否匹配渠道过滤条件"""
        filters = channel.filters

        # 检查级别过滤
        if "levels" in filters:
            if alert.level not in filters["levels"]:
                return False

        # 检查标签过滤
        if "labels" in filters:
            for key, value in filters["labels"].items():
                if alert.labels.get(key) != value:
                    return False

        # 检查来源过滤
        if "sources" in filters:
            if alert.source not in filters["sources"]:
                return False

        return True

    async def acknowledge_alert(self, alert_id: str, acknowledged_by: str) -> bool:
        """确认告警"""
        if alert_id in self.active_alerts:
            alert = self.active_alerts[alert_id]
            alert.status = AlertStatus.ACKNOWLEDGED
            alert.acknowledged_by = acknowledged_by
            alert.acknowledged_at = datetime.now(UTC)
            logger.info(f"告警已确认: {alert.title} by {acknowledged_by}")
            return True
        return False

    async def resolve_alert(self, alert_id: str, resolved_by: str) -> bool:
        """解决告警"""
        if alert_id in self.active_alerts:
            alert = self.active_alerts[alert_id]
            alert.status = AlertStatus.RESOLVED
            alert.resolved_by = resolved_by
            alert.resolved_at = datetime.now(UTC)

            # 从活跃告警中移除
            del self.active_alerts[alert_id]
            logger.info(f"告警已解决: {alert.title} by {resolved_by}")
            return True
        return False

    def get_active_alerts(self) -> list[Alert]:
        """获取活跃告警"""
        return list(self.active_alerts.values())

    def get_alert_history(self, hours: int = 24) -> list[Alert]:
        """获取告警历史"""
        cutoff_time = datetime.now(UTC) - timedelta(hours=hours)
        return [alert for alert in self.alert_history if alert.timestamp > cutoff_time]

    def get_alert_statistics(self) -> dict[str, Any]:
        """获取告警统计"""
        stats = {
            "total_active": len(self.active_alerts),
            "total_rules": len(self.rules),
            "enabled_rules": sum(1 for rule in self.rules.values() if rule.enabled),
            "total_channels": len(self.channels),
            "enabled_channels": sum(
                1 for channel in self.channels.values() if channel.enabled
            ),
        }

        # 按级别统计活跃告警
        level_counts = {}
        for alert in self.active_alerts.values():
            level = alert.level.value
            level_counts[level] = level_counts.get(level, 0) + 1
        stats["active_by_level"] = level_counts

        # 按来源统计活跃告警
        source_counts = {}
        for alert in self.active_alerts.values():
            source = alert.source
            source_counts[source] = source_counts.get(source, 0) + 1
        stats["active_by_source"] = source_counts

        # 最近24小时告警统计
        recent_alerts = self.get_alert_history(24)
        recent_level_counts = {}
        for alert in recent_alerts:
            level = alert.level.value
            recent_level_counts[level] = recent_level_counts.get(level, 0) + 1
        stats["recent_24h_by_level"] = recent_level_counts

        return stats


# ============================================================================
# 全局告警管理器实例
# ============================================================================

alert_manager = AlertManager()
