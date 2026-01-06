#!/usr/bin/env python3
"""
监控告警系统 - Sprint 6核心组件

支持多渠道告警通知：
1. Telegram Bot 通知
2. 邮件告警 (SMTP)
3. Slack Webhook
4. 企业微信机器人
5. 自定义Webhook

特性：
- 智能告警聚合和去重
- 告警级别管理
- 模板化消息格式
- 告警历史记录
- 健康检查和故障转移

Role: 高级DevOps & 策略部署专家
Sprint: 实时化、可观测性与策略调优
"""

import asyncio
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.utils import formataddr
from enum import Enum
import hashlib
import json
import logging
import smtplib
import time
from typing import Any

import aiohttp
import jinja2

logger = logging.getLogger(__name__)


class AlertLevel(Enum):
    """告警级别"""

    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"
    FATAL = "fatal"


class NotificationChannel(Enum):
    """通知渠道"""

    TELEGRAM = "telegram"
    EMAIL = "email"
    SLACK = "slack"
    WEBHOOK = "webhook"
    WECHAT_WORK = "wechat_work"


class AlertStatus(Enum):
    """告警状态"""

    ACTIVE = "active"
    RESOLVED = "resolved"
    SUPPRESSED = "suppressed"
    ACKNOWLEDGED = "acknowledged"


@dataclass
class AlertConfig:
    """告警配置"""

    # Telegram配置
    telegram_bot_token: str | None = None
    telegram_chat_ids: list[str] = field(default_factory=list)

    # 邮件配置
    smtp_server: str | None = None
    smtp_port: int = 587
    smtp_username: str | None = None
    smtp_password: str | None = None
    email_from: str | None = None
    email_to: list[str] = field(default_factory=list)
    use_tls: bool = True

    # Slack配置
    slack_webhook_url: str | None = None

    # 企业微信配置
    wechat_work_webhook_url: str | None = None

    # 通用Webhook配置
    webhook_urls: list[str] = field(default_factory=list)

    # 告警策略
    enable_rate_limit: bool = True
    max_alerts_per_hour: int = 10
    alert_cooldown_minutes: int = 15
    enable_aggregation: bool = True
    aggregation_window_minutes: int = 5

    # 模板配置
    templates_dir: str = "./templates"

    # 其他配置
    enable_retry: bool = True
    max_retry_attempts: int = 3
    retry_delay_seconds: int = 5
    timeout_seconds: int = 30


@dataclass
class Alert:
    """告警对象"""

    id: str
    title: str
    message: str
    level: AlertLevel
    source: str  # 告警来源 (如 "backtester", "collector", "model")
    timestamp: datetime = field(default_factory=datetime.utcnow)
    status: AlertStatus = AlertStatus.ACTIVE
    metadata: dict[str, Any] = field(default_factory=dict)
    tags: list[str] = field(default_factory=list)
    resolved_at: datetime | None = None
    acknowledged_at: datetime | None = None
    acknowledged_by: str | None = None

    def __post_init__(self):
        """生成告警ID"""
        if not self.id:
            # 基于标题、消息、来源和时间生成唯一ID
            content = f"{self.title}_{self.message}_{self.source}_{self.timestamp.isoformat()}"
            self.id = hashlib.md5(content.encode()).hexdigest()[:16]

    def resolve(self) -> None:
        """解决告警"""
        self.status = AlertStatus.RESOLVED
        self.resolved_at = datetime.utcnow()

    def acknowledge(self, user: str) -> None:
        """确认告警"""
        self.status = AlertStatus.ACKNOWLEDGED
        self.acknowledged_at = datetime.utcnow()
        self.acknowledged_by = user

    def to_dict(self) -> dict[str, Any]:
        """转换为字典格式"""
        return {
            "id": self.id,
            "title": self.title,
            "message": self.message,
            "level": self.level.value,
            "source": self.source,
            "timestamp": self.timestamp.isoformat(),
            "status": self.status.value,
            "metadata": self.metadata,
            "tags": self.tags,
            "resolved_at": self.resolved_at.isoformat() if self.resolved_at else None,
            "acknowledged_at": (self.acknowledged_at.isoformat() if self.acknowledged_at else None),
            "acknowledged_by": self.acknowledged_by,
        }


@dataclass
class NotificationResult:
    """通知结果"""

    success: bool
    channel: NotificationChannel
    error_message: str | None = None
    response_time_ms: float = 0.0
    attempt_count: int = 1


class AlertAggregator:
    """告警聚合器"""

    def __init__(self, window_minutes: int = 5):
        self.window_minutes = window_minutes
        self.alert_buffer: list[Alert] = []
        self.lock = asyncio.Lock()

    async def add_alert(self, alert: Alert) -> Alert | None:
        """
        添加告警到聚合器

        Args:
            alert: 新告警

        Returns:
            Optional[Alert]: 聚合后的告警，如果不需要聚合则返回原告警
        """
        async with self.lock:
            # 清理过期告警
            self._cleanup_expired_alerts()

            # 检查是否有相似告警可以聚合
            similar_alerts = self._find_similar_alerts(alert)

            if similar_alerts:
                # 聚合告警
                aggregated_alert = self._aggregate_alerts(similar_alerts + [alert])
                self.alert_buffer.append(aggregated_alert)
                return aggregated_alert
            # 添加新告警
            self.alert_buffer.append(alert)
            return alert

    def _cleanup_expired_alerts(self) -> None:
        """清理过期的告警"""
        cutoff_time = datetime.utcnow() - timedelta(minutes=self.window_minutes)
        self.alert_buffer = [alert for alert in self.alert_buffer if alert.timestamp >= cutoff_time]

    def _find_similar_alerts(self, alert: Alert) -> list[Alert]:
        """查找相似的告警"""
        similar = []
        title_prefix = alert.title.split(":")[0] if ":" in alert.title else alert.title

        for existing_alert in self.alert_buffer:
            # 检查告警来源和级别是否相同
            if (
                existing_alert.source == alert.source
                and existing_alert.level == alert.level
                and existing_alert.status == AlertStatus.ACTIVE
            ):
                # 检查标题是否相似
                existing_prefix = (
                    existing_alert.title.split(":")[0] if ":" in existing_alert.title else existing_alert.title
                )
                if title_prefix == existing_prefix:
                    similar.append(existing_alert)

        return similar

    def _aggregate_alerts(self, alerts: list[Alert]) -> Alert:
        """聚合多个告警"""
        if not alerts:
            raise ValueError("告警列表不能为空")

        # 使用最新的告警作为基础
        base_alert = max(alerts, key=lambda a: a.timestamp)

        # 聚合消息
        if len(alerts) == 1:
            return base_alert

        # 创建聚合告警
        count = len(alerts)
        sources = list(set(alert.source for alert in alerts))
        earliest_time = min(alert.timestamp for alert in alerts)

        aggregated_title = f"[聚合] {base_alert.title} ({count}次)"
        aggregated_message = f"""
告警聚合报告:
- 告警次数: {count}
- 涉及来源: {", ".join(sources)}
- 时间范围: {earliest_time.strftime("%H:%M:%S")} - {base_alert.timestamp.strftime("%H:%M:%S")}

最新告警内容:
{base_alert.message}

相关告警ID: {[alert.id for alert in alerts]}
        """.strip()

        return Alert(
            id="",  # 将自动生成
            title=aggregated_title,
            message=aggregated_message,
            level=base_alert.level,
            source=f"aggregated_{'_'.join(sorted(sources))}",
            metadata={
                "aggregated_count": count,
                "original_alert_ids": [alert.id for alert in alerts],
                "sources": sources,
            },
            tags=["aggregated"] + base_alert.tags,
        )


class RateLimiter:
    """速率限制器"""

    def __init__(self, max_alerts_per_hour: int = 10):
        self.max_alerts_per_hour = max_alerts_per_hour
        self.alert_history: list[datetime] = []

    def can_send_alert(self) -> bool:
        """检查是否可以发送告警"""
        now = datetime.utcnow()
        hour_ago = now - timedelta(hours=1)

        # 清理1小时前的记录
        self.alert_history = [timestamp for timestamp in self.alert_history if timestamp >= hour_ago]

        # 检查是否超过限制
        return len(self.alert_history) < self.max_alerts_per_hour

    def record_alert(self) -> None:
        """记录告警发送"""
        self.alert_history.append(datetime.utcnow())


class AlertNotifier:
    """
    告警通知系统

    支持多渠道告警通知，包括智能聚合、速率限制和模板化消息。
    """

    def __init__(self, config: AlertConfig):
        self.config = config

        # 初始化组件
        self.aggregator = AlertAggregator(window_minutes=config.aggregation_window_minutes)
        self.rate_limiter = RateLimiter(max_alerts_per_hour=config.max_alerts_per_hour)

        # 初始化模板引擎
        self.template_env = jinja2.Environment(loader=jinja2.FileSystemLoader(config.templates_dir), autoescape=True)

        # HTTP会话
        self.http_session: aiohttp.ClientSession | None = None

        # 告警历史
        self.alert_history: dict[str, Alert] = {}
        self.cooldown_cache: dict[str, datetime] = {}

        # 统计信息
        self.stats = {
            "total_alerts_sent": 0,
            "alerts_by_channel": {channel.value: 0 for channel in NotificationChannel},
            "alerts_by_level": {level.value: 0 for level in AlertLevel},
            "failed_alerts": 0,
            "last_alert_time": None,
        }

        logger.info("🔔 告警通知系统初始化完成")

    async def initialize(self) -> None:
        """初始化通知系统"""
        try:
            # 创建HTTP会话
            timeout = aiohttp.ClientTimeout(total=self.config.timeout_seconds)
            self.http_session = aiohttp.ClientSession(timeout=timeout)

            # 验证配置
            await self._validate_config()

            logger.info("✅ 告警通知系统初始化成功")

        except Exception as e:
            logger.error(f"❌ 告警通知系统初始化失败: {e}")
            raise

    async def _validate_config(self) -> None:
        """验证配置"""
        required_configs = []

        # 检查是否有至少一个通知渠道配置
        if self.config.telegram_bot_token and self.config.telegram_chat_ids:
            logger.info("✅ Telegram通知渠道已配置")
        elif self.config.smtp_server and self.config.email_to:
            logger.info("✅ 邮件通知渠道已配置")
        elif self.config.slack_webhook_url:
            logger.info("✅ Slack通知渠道已配置")
        elif self.config.webhook_urls:
            logger.info("✅ Webhook通知渠道已配置")
        elif self.config.wechat_work_webhook_url:
            logger.info("✅ 企业微信通知渠道已配置")
        else:
            logger.warning("⚠️ 未配置任何通知渠道")

    async def send_alert(
        self,
        title: str,
        message: str,
        level: AlertLevel = AlertLevel.INFO,
        source: str = "unknown",
        channels: list[NotificationChannel] | None = None,
        metadata: dict[str, Any] | None = None,
        tags: list[str] | None = None,
        force_send: bool = False,
    ) -> list[NotificationResult]:
        """
        发送告警

        Args:
            title: 告警标题
            message: 告警消息
            level: 告警级别
            source: 告警来源
            channels: 通知渠道列表 (None表示使用所有可用渠道)
            metadata: 附加元数据
            tags: 告警标签
            force_send: 强制发送 (忽略速率限制和冷却时间)

        Returns:
            List[NotificationResult]: 各渠道的通知结果
        """
        try:
            # 创建告警对象
            alert = Alert(
                id="",  # 自动生成
                title=title,
                message=message,
                level=level,
                source=source,
                metadata=metadata or {},
                tags=tags or [],
            )

            # 检查是否需要聚合
            if self.config.enable_aggregation and not force_send:
                alert = await self.aggregator.add_alert(alert)

            # 检查冷却时间
            alert_key = f"{alert.source}:{alert.title}"
            if not force_send and self._is_in_cooldown(alert_key):
                return []

            # 检查速率限制
            if not force_send and self.config.enable_rate_limit and not self.rate_limiter.can_send_alert():
                logger.warning("⚠️ 超过速率限制，跳过告警发送")
                return []

            # 确定通知渠道
            if channels is None:
                channels = self._get_available_channels()

            # 记录告警
            self.alert_history[alert.id] = alert
            if not force_send:
                self.cooldown_cache[alert_key] = datetime.utcnow()
                self.rate_limiter.record_alert()

            # 并发发送到各渠道
            results = await asyncio.gather(
                *[self._send_to_channel(alert, channel) for channel in channels],
                return_exceptions=True,
            )

            # 处理结果
            notification_results = []
            for i, result in enumerate(results):
                if isinstance(result, Exception):
                    logger.error(f"❌ 发送到{channels[i].value}失败: {result}")
                    notification_results.append(
                        NotificationResult(
                            success=False,
                            channel=channels[i],
                            error_message=str(result),
                        )
                    )
                    self.stats["failed_alerts"] += 1
                else:
                    notification_results.append(result)
                    self.stats["alerts_by_channel"][result.channel.value] += 1

            # 更新统计信息
            self.stats["total_alerts_sent"] += 1
            self.stats["alerts_by_level"][alert.level.value] += 1
            self.stats["last_alert_time"] = datetime.utcnow()

            return notification_results

        except Exception as e:
            logger.error(f"❌ 告警发送失败: {e}")
            return [
                NotificationResult(
                    success=False,
                    channel=NotificationChannel.EMAIL,  # 默认渠道
                    error_message=str(e),
                )
            ]

    def _is_in_cooldown(self, alert_key: str) -> bool:
        """检查告警是否在冷却期内"""
        if alert_key not in self.cooldown_cache:
            return False

        cooldown_time = timedelta(minutes=self.config.alert_cooldown_minutes)
        last_sent = self.cooldown_cache[alert_key]

        return datetime.utcnow() - last_sent < cooldown_time

    def _get_available_channels(self) -> list[NotificationChannel]:
        """获取可用的通知渠道"""
        channels = []

        if self.config.telegram_bot_token and self.config.telegram_chat_ids:
            channels.append(NotificationChannel.TELEGRAM)

        if self.config.smtp_server and self.config.email_to:
            channels.append(NotificationChannel.EMAIL)

        if self.config.slack_webhook_url:
            channels.append(NotificationChannel.SLACK)

        if self.config.wechat_work_webhook_url:
            channels.append(NotificationChannel.WECHAT_WORK)

        if self.config.webhook_urls:
            channels.append(NotificationChannel.WEBHOOK)

        return channels

    async def _send_to_channel(self, alert: Alert, channel: NotificationChannel) -> NotificationResult:
        """发送告警到指定渠道"""
        start_time = time.time()

        try:
            if channel == NotificationChannel.TELEGRAM:
                result = await self._send_telegram_alert(alert)
            elif channel == NotificationChannel.EMAIL:
                result = await self._send_email_alert(alert)
            elif channel == NotificationChannel.SLACK:
                result = await self._send_slack_alert(alert)
            elif channel == NotificationChannel.WECHAT_WORK:
                result = await self._send_wechat_work_alert(alert)
            elif channel == NotificationChannel.WEBHOOK:
                result = await self._send_webhook_alert(alert)
            else:
                raise ValueError(f"不支持的通知渠道: {channel}")

            result.response_time_ms = (time.time() - start_time) * 1000
            return result

        except Exception as e:
            logger.error(f"❌ 发送到{channel.value}失败: {e}")
            return NotificationResult(
                success=False,
                channel=channel,
                error_message=str(e),
                response_time_ms=(time.time() - start_time) * 1000,
            )

    async def _send_telegram_alert(self, alert: Alert) -> NotificationResult:
        """发送Telegram告警"""
        try:
            url = f"https://api.telegram.org/bot{self.config.telegram_bot_token}/sendMessage"

            # 格式化消息
            emoji_map = {
                AlertLevel.INFO: "ℹ️",
                AlertLevel.WARNING: "⚠️",
                AlertLevel.ERROR: "❌",
                AlertLevel.CRITICAL: "🚨",
                AlertLevel.FATAL: "💀",
            }

            text = f"""
{emoji_map.get(alert.level, "🔔")} *{alert.title}*

来源: {alert.source}
级别: {alert.level.value.upper()}
时间: {alert.timestamp.strftime("%Y-%m-%d %H:%M:%S")}

{alert.message}
            """.strip()

            # 发送到所有聊天ID
            results = []
            for chat_id in self.config.telegram_chat_ids:
                payload = {
                    "chat_id": chat_id,
                    "text": text,
                    "parse_mode": "Markdown",
                    "disable_web_page_preview": True,
                }

                async with self.http_session.post(url, json=payload) as response:
                    if response.status == 200:
                        logger.info(f"✅ Telegram告警发送成功: {chat_id}")
                        results.append(True)
                    else:
                        error_text = await response.text()
                        logger.error(f"❌ Telegram告警发送失败: {error_text}")
                        results.append(False)

            success = all(results)
            return NotificationResult(success=success, channel=NotificationChannel.TELEGRAM)

        except Exception as e:
            return NotificationResult(
                success=False,
                channel=NotificationChannel.TELEGRAM,
                error_message=str(e),
            )

    async def _send_email_alert(self, alert: Alert) -> NotificationResult:
        """发送邮件告警"""
        try:
            # 创建邮件内容
            msg = MIMEMultipart("alternative")
            msg["Subject"] = f"[{alert.level.value.upper()}] {alert.title}"
            msg["From"] = formataddr(("Football Prediction System", self.config.email_from))
            msg["To"] = ", ".join(self.config.email_to)

            # HTML内容
            html_content = f"""
<html>
<head>
    <style>
        body {{ font-family: Arial, sans-serif; }}
        .alert-header {{ background-color: #f0f0f0; padding: 10px; border-radius: 5px; }}
        .alert-content {{ margin: 20px 0; }}
        .alert-footer {{ font-size: 12px; color: #666; }}
        .level-{alert.level.value} {{ color: #d32f2f; }}
    </style>
</head>
<body>
    <div class="alert-header">
        <h2 class="level-{alert.level.value}">{alert.title}</h2>
        <p><strong>来源:</strong> {alert.source}</p>
        <p><strong>级别:</strong> {alert.level.value.upper()}</p>
        <p><strong>时间:</strong> {alert.timestamp.strftime("%Y-%m-%d %H:%M:%S")}</p>
    </div>

    <div class="alert-content">
        <pre>{alert.message}</pre>
    </div>

    <div class="alert-footer">
        <p>此邮件由足球预测系统自动发送</p>
    </div>
</body>
</html>
            """

            # 添加HTML和纯文本内容
            msg.attach(MIMEText(html_content, "html", "utf-8"))
            msg.attach(MIMEText(alert.message, "plain", "utf-8"))

            # 在线程池中发送邮件 (同步SMTP)
            loop = asyncio.get_event_loop()
            with ThreadPoolExecutor() as executor:
                result = await loop.run_in_executor(executor, self._send_email_sync, msg)

            if result:
                logger.info(f"✅ 邮件告警发送成功: {', '.join(self.config.email_to)}")
            else:
                logger.error("❌ 邮件告警发送失败")

            return NotificationResult(success=result, channel=NotificationChannel.EMAIL)

        except Exception as e:
            return NotificationResult(success=False, channel=NotificationChannel.EMAIL, error_message=str(e))

    def _send_email_sync(self, msg: MIMEMultipart) -> bool:
        """同步发送邮件"""
        try:
            with smtplib.SMTP(self.config.smtp_server, self.config.smtp_port) as server:
                if self.config.use_tls:
                    server.starttls()
                if self.config.smtp_username and self.config.smtp_password:
                    server.login(self.config.smtp_username, self.config.smtp_password)

                server.send_message(msg)
                return True

        except Exception as e:
            logger.error(f"❌ SMTP发送失败: {e}")
            return False

    async def _send_slack_alert(self, alert: Alert) -> NotificationResult:
        """发送Slack告警"""
        try:
            emoji_map = {
                AlertLevel.INFO: ":information_source:",
                AlertLevel.WARNING: ":warning:",
                AlertLevel.ERROR: ":x:",
                AlertLevel.CRITICAL: ":rotating_light:",
                AlertLevel.FATAL: ":skull:",
            }

            payload = {
                "username": "Football Prediction Alerts",
                "icon_emoji": emoji_map.get(alert.level, ":bell:"),
                "text": alert.title,
                "attachments": [
                    {
                        "color": self._get_slack_color(alert.level),
                        "fields": [
                            {"title": "来源", "value": alert.source, "short": True},
                            {
                                "title": "级别",
                                "value": alert.level.value.upper(),
                                "short": True,
                            },
                            {
                                "title": "时间",
                                "value": alert.timestamp.strftime("%Y-%m-%d %H:%M:%S"),
                                "short": True,
                            },
                        ],
                        "text": alert.message,
                    }
                ],
            }

            async with self.http_session.post(self.config.slack_webhook_url, json=payload) as response:
                if response.status == 200:
                    logger.info("✅ Slack告警发送成功")
                    return NotificationResult(success=True, channel=NotificationChannel.SLACK)
                error_text = await response.text()
                logger.error(f"❌ Slack告警发送失败: {error_text}")
                return NotificationResult(
                    success=False,
                    channel=NotificationChannel.SLACK,
                    error_message=error_text,
                )

        except Exception as e:
            return NotificationResult(success=False, channel=NotificationChannel.SLACK, error_message=str(e))

    def _get_slack_color(self, level: AlertLevel) -> str:
        """获取Slack颜色"""
        color_map = {
            AlertLevel.INFO: "good",
            AlertLevel.WARNING: "warning",
            AlertLevel.ERROR: "danger",
            AlertLevel.CRITICAL: "#ff0000",
            AlertLevel.FATAL: "#800000",
        }
        return color_map.get(level, "good")

    async def _send_wechat_work_alert(self, alert: Alert) -> NotificationResult:
        """发送企业微信告警"""
        try:
            emoji_map = {
                AlertLevel.INFO: "ℹ️",
                AlertLevel.WARNING: "⚠️",
                AlertLevel.ERROR: "❌",
                AlertLevel.CRITICAL: "🚨",
                AlertLevel.FATAL: "💀",
            }

            payload = {
                "msgtype": "markdown",
                "markdown": {
                    "content": f"""
{emoji_map.get(alert.level, "🔔")} **{alert.title}**

> **来源**: {alert.source}
> **级别**: {alert.level.value.upper()}
> **时间**: {alert.timestamp.strftime("%Y-%m-%d %H:%M:%S")}

{alert.message}
                    """.strip()
                },
            }

            async with self.http_session.post(self.config.wechat_work_webhook_url, json=payload) as response:
                if response.status == 200:
                    result = await response.json()
                    if result.get("errcode") == 0:
                        logger.info("✅ 企业微信告警发送成功")
                        return NotificationResult(success=True, channel=NotificationChannel.WECHAT_WORK)
                    error_msg = result.get("errmsg", "Unknown error")
                    logger.error(f"❌ 企业微信告警发送失败: {error_msg}")
                    return NotificationResult(
                        success=False,
                        channel=NotificationChannel.WECHAT_WORK,
                        error_message=error_msg,
                    )
                error_text = await response.text()
                logger.error(f"❌ 企业微信告警发送失败: {error_text}")
                return NotificationResult(
                    success=False,
                    channel=NotificationChannel.WECHAT_WORK,
                    error_message=error_text,
                )

        except Exception as e:
            return NotificationResult(
                success=False,
                channel=NotificationChannel.WECHAT_WORK,
                error_message=str(e),
            )

    async def _send_webhook_alert(self, alert: Alert) -> NotificationResult:
        """发送Webhook告警"""
        try:
            payload = {
                "alert_id": alert.id,
                "title": alert.title,
                "message": alert.message,
                "level": alert.level.value,
                "source": alert.source,
                "timestamp": alert.timestamp.isoformat(),
                "metadata": alert.metadata,
                "tags": alert.tags,
            }

            results = []
            for webhook_url in self.config.webhook_urls:
                async with self.http_session.post(webhook_url, json=payload) as response:
                    if response.status < 400:  # 2xx或3xx状态码
                        logger.info(f"✅ Webhook告警发送成功: {webhook_url}")
                        results.append(True)
                    else:
                        error_text = await response.text()
                        logger.error(f"❌ Webhook告警发送失败 ({webhook_url}): {error_text}")
                        results.append(False)

            success = all(results)
            return NotificationResult(success=success, channel=NotificationChannel.WEBHOOK)

        except Exception as e:
            return NotificationResult(success=False, channel=NotificationChannel.WEBHOOK, error_message=str(e))

    async def resolve_alert(self, alert_id: str) -> bool:
        """解决告警"""
        if alert_id not in self.alert_history:
            logger.warning(f"⚠️ 告警ID不存在: {alert_id}")
            return False

        alert = self.alert_history[alert_id]
        alert.resolve()

        # 发送解决通知
        await self.send_alert(
            title=f"[已解决] {alert.title}",
            message=f"告警已解决\n\n原始告警ID: {alert.id}\n解决时间: {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')}",
            level=AlertLevel.INFO,
            source="alert_system",
            tags=["alert_resolved"],
        )

        logger.info(f"✅ 告警已解决: {alert_id}")
        return True

    async def acknowledge_alert(self, alert_id: str, user: str) -> bool:
        """确认告警"""
        if alert_id not in self.alert_history:
            logger.warning(f"⚠️ 告警ID不存在: {alert_id}")
            return False

        alert = self.alert_history[alert_id]
        alert.acknowledge(user)

        logger.info(f"✅ 告警已确认: {alert_id} by {user}")
        return True

    def get_alert_history(
        self,
        hours: int = 24,
        level: AlertLevel | None = None,
        source: str | None = None,
        status: AlertStatus | None = None,
    ) -> list[Alert]:
        """获取告警历史"""
        cutoff_time = datetime.utcnow() - timedelta(hours=hours)

        filtered_alerts = []
        for alert in self.alert_history.values():
            # 时间过滤
            if alert.timestamp < cutoff_time:
                continue

            # 级别过滤
            if level and alert.level != level:
                continue

            # 来源过滤
            if source and alert.source != source:
                continue

            # 状态过滤
            if status and alert.status != status:
                continue

            filtered_alerts.append(alert)

        # 按时间倒序排列
        return sorted(filtered_alerts, key=lambda a: a.timestamp, reverse=True)

    def get_statistics(self) -> dict[str, Any]:
        """获取统计信息"""
        return {
            **self.stats,
            "total_alerts_in_history": len(self.alert_history),
            "active_alerts": len([a for a in self.alert_history.values() if a.status == AlertStatus.ACTIVE]),
            "resolved_alerts": len([a for a in self.alert_history.values() if a.status == AlertStatus.RESOLVED]),
            "acknowledged_alerts": len(
                [a for a in self.alert_history.values() if a.status == AlertStatus.ACKNOWLEDGED]
            ),
            "rate_limit_active": len(self.rate_limiter.alert_history),
            "aggregation_buffer_size": len(self.aggregator.alert_buffer),
        }

    def export_alerts(self, filepath: str, hours: int = 24) -> None:
        """导出告警数据"""
        try:
            alerts = self.get_alert_history(hours=hours)
            data = [alert.to_dict() for alert in alerts]

            with open(filepath, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)

            logger.info(f"💾 告警数据已导出: {filepath}")

        except Exception as e:
            logger.error(f"❌ 告警数据导出失败: {e}")

    async def shutdown(self) -> None:
        """关闭通知系统"""
        try:
            if self.http_session:
                await self.http_session.close()

            logger.info("✅ 告警通知系统已关闭")

        except Exception as e:
            logger.error(f"❌ 关闭告警通知系统失败: {e}")


# 便捷函数
async def create_notifier(
    telegram_bot_token: str | None = None,
    telegram_chat_ids: list[str] | None = None,
    smtp_server: str | None = None,
    smtp_username: str | None = None,
    smtp_password: str | None = None,
    email_from: str | None = None,
    email_to: list[str] | None = None,
    **kwargs,
) -> AlertNotifier:
    """
    创建告警通知器

    Args:
        telegram_bot_token: Telegram机器人令牌
        telegram_chat_ids: Telegram聊天ID列表
        smtp_server: SMTP服务器
        smtp_username: SMTP用户名
        smtp_password: SMTP密码
        email_from: 发件人邮箱
        email_to: 收件人邮箱列表
        **kwargs: 其他配置参数

    Returns:
        AlertNotifier: 配置好的通知器
    """
    config = AlertConfig(
        telegram_bot_token=telegram_bot_token,
        telegram_chat_ids=telegram_chat_ids or [],
        smtp_server=smtp_server,
        smtp_username=smtp_username,
        smtp_password=smtp_password,
        email_from=email_from,
        email_to=email_to or [],
        **kwargs,
    )

    notifier = AlertNotifier(config)
    await notifier.initialize()

    return notifier


# 预定义告警模板
ALERT_TEMPLATES = {
    "system_error": {
        "title": "系统错误",
        "message": "系统发生错误，需要立即处理\n\n错误详情: {error}\n组件: {component}\n时间: {time}",
    },
    "performance_degradation": {
        "title": "性能下降",
        "message": "系统性能检测到下降\n\n指标: {metric}\n当前值: {current_value}\n阈值: {threshold}\n时间: {time}",
    },
    "model_accuracy_drop": {
        "title": "模型准确率下降",
        "message": "预测模型准确率下降\n\n模型: {model_name}\n当前准确率: {current_accuracy}%\n基线准确率: {baseline_accuracy}%\n时间: {time}",
    },
    "data_collection_failure": {
        "title": "数据收集失败",
        "message": "数据收集遇到问题\n\n数据源: {data_source}\n错误信息: {error}\n时间: {time}",
    },
    "strategy_performance": {
        "title": "策略性能报告",
        "message": "策略性能更新\n\n策略: {strategy_name}\n当前ROI: {roi}%\n胜率: {win_rate}%\n最大回撤: {max_drawdown}%\n时间: {time}",
    },
}


# 示例使用
async def main():
    """示例使用告警通知系统"""
    # 创建通知器 (实际使用时需要真实的配置)
    notifier = await create_notifier(
        telegram_bot_token="your_bot_token",
        telegram_chat_ids=["your_chat_id"],
        smtp_server="smtp.gmail.com",
        smtp_username="your_email@gmail.com",
        smtp_password="your_password",
        email_from="system@example.com",
        email_to=["admin@example.com"],
    )

    try:
        # 发送不同级别的告警
        await notifier.send_alert(
            title="系统启动成功",
            message="足球预测系统已成功启动",
            level=AlertLevel.INFO,
            source="system",
            tags=["startup"],
        )

        await notifier.send_alert(
            title="模型训练完成",
            message="XGBoost模型训练已完成，准确率达到85.3%",
            level=AlertLevel.INFO,
            source="model_training",
            metadata={"model_name": "xgboost_v2", "accuracy": 0.853},
        )

        await notifier.send_alert(
            title="数据收集延迟",
            message="FotMob API数据收集延迟超过5分钟",
            level=AlertLevel.WARNING,
            source="data_collector",
            tags=["performance", "data"],
        )

        # 获取统计信息
        stats = notifier.get_statistics()

    finally:
        await notifier.shutdown()


if __name__ == "__main__":
    asyncio.run(main())
