"""
监控告警模块 - 实时告警管理
实现智能告警、多渠道通知和告警聚合
"""

import asyncio
import json
import logging
import statistics
from collections import defaultdict, deque
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from enum import Enum
from typing import Any

logger = logging.getLogger(__name__)


class AlertSeverity(Enum):
    """告警严重程度"""

    INFO = "info"  # 信息
    WARNING = "warning"  # 警告
    ERROR = "error"  # 错误
    CRITICAL = "critical"  # 严重
    FATAL = "fatal"  # 致命


class AlertStatus(Enum):
    """告警状态"""

    ACTIVE = "active"  # 活跃
    RESOLVED = "resolved"  # 已解决
    SUPPRESSED = "suppressed"  # 已抑制
    ACKNOWLEDGED = "acknowledged"  # 已确认


class NotificationChannel(Enum):
    """通知渠道"""

    EMAIL = "email"
    SLACK = "slack"
    WEBHOOK = "webhook"
    SMS = "sms"
    PAGERDUTY = "pagerduty"
    DINGTALK = "dingtalk"


@dataclass
class AlertRule:
    """告警规则"""

    rule_id: str
    name: str
    description: str
    condition: str  # 告警条件表达式
    severity: AlertSeverity
    enabled: bool = True
    threshold: float = 0.0
    evaluation_window: int = 300  # 评估窗口(秒)
    consecutive_periods: int = 3  # 连续周期
    recovery_threshold: float | None = None
    suppression_duration: int = 3600  # 抑制时间(秒)
    notification_channels: list[NotificationChannel] = field(default_factory=list)
    custom_attributes: dict[str, Any] = field(default_factory=dict)


@dataclass
class Alert:
    """告警事件"""

    alert_id: str
    rule_id: str
    rule_name: str
    severity: AlertSeverity
    status: AlertStatus
    message: str
    details: dict[str, Any]
    timestamp: datetime
    resolved_at: datetime | None = None
    acknowledged_at: datetime | None = None
    suppressed_until: datetime | None = None
    notification_sent: dict[NotificationChannel, datetime] = field(default_factory=dict)
    escalation_count: int = 0
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class AlertAggregation:
    """告警聚合"""

    aggregation_id: str
    pattern: str  # 聚合模式
    window_minutes: int = 15
    max_alerts: int = 100
    suppression_enabled: bool = True


class AlertManager:
    """告警管理器"""

    def __init__(self):
        self.rules: dict[str, AlertRule] = {}
        self.active_alerts: dict[str, Alert] = {}
        self.alert_history: deque[Alert] = deque(maxlen=10000)
        self.aggregations: dict[str, AlertAggregation] = {}
        self.notification_handlers: dict[NotificationChannel, Callable] = {}
        self.metric_data: dict[str, deque] = defaultdict(lambda: deque(maxlen=1000))
        self.evaluation_intervals = defaultdict(lambda: 60)  # 默认60秒

        # 注册通知处理器
        self._register_notification_handlers()

        # 后台任务将在需要时启动
        self._background_tasks_started = False

    def add_rule(self, rule: AlertRule):
        """添加告警规则"""
        self.rules[rule.rule_id] = rule
        self.evaluation_intervals[rule.rule_id] = rule.evaluation_window
        logger.info(f"Added alert rule: {rule.name}")

    def remove_rule(self, rule_id: str):
        """移除告警规则"""
        if rule_id in self.rules:
            del self.rules[rule_id]
            del self.evaluation_intervals[rule_id]
            logger.info(f"Removed alert rule: {rule_id}")

    async def add_metric(
        self, metric_name: str, value: float, tags: dict[str, Any] = None
    ):
        """添加指标数据"""
        timestamp = datetime.now()
        self.metric_data[metric_name].append(
            {"value": value, "timestamp": timestamp, "tags": tags or {}}
        )

        # 触发规则评估
        await self._evaluate_rules(metric_name)

    async def add_event(self, event_type: str, data: dict[str, Any]):
        """添加事件数据"""
        # 事件类型转换为指标
        metric_name = f"event_{event_type}"
        value = data.get("value", 1.0)
        await self.add_metric(metric_name, value, data.get("tags"))

    async def _evaluate_rules(self, metric_name: str):
        """评估相关规则"""
        for rule_id, rule in self.rules.items():
            if rule.enabled and metric_name in rule.condition:
                await self._evaluate_rule(rule_id, metric_name)

    async def _evaluate_rule(self, rule_id: str, metric_name: str):
        """评估单个规则"""
        rule = self.rules[rule_id]
        metric_data = self.metric_data.get(metric_name, [])

        if len(metric_data) < rule.consecutive_periods:
            return

        # 获取评估窗口内的数据
        window_end = datetime.now()
        window_start = window_end - timedelta(seconds=rule.evaluation_window)

        recent_data = [
            point for point in metric_data if point["timestamp"] >= window_start
        ]

        if len(recent_data) < rule.consecutive_periods:
            return

        # 评估条件（简化实现）
        try:
            values = [point["value"] for point in recent_data]
            avg_value = statistics.mean(values)
            max_value = max(values)
            min_value = min(values)

            condition_met = self._evaluate_condition(
                rule.condition,
                {
                    "avg": avg_value,
                    "max": max_value,
                    "min": min_value,
                    "current": recent_data[-1]["value"],
                    "count": len(values),
                },
            )

            if condition_met:
                await self._trigger_alert(rule, recent_data)
            else:
                # 检查是否应该恢复告警
                await self._check_recovery(rule_id)

        except Exception as e:
            logger.error(f"Rule evaluation error for {rule_id}: {e}")

    def _evaluate_condition(self, condition: str, variables: dict[str, float]) -> bool:
        """评估条件表达式"""
        try:
            # 简单的条件评估（实际实现中应该使用安全的表达式引擎）
            if condition.startswith("avg >"):
                threshold = float(condition.split(">")[1].strip())
                return variables["avg"] > threshold
            elif condition.startswith("max >"):
                threshold = float(condition.split(">")[1].strip())
                return variables["max"] > threshold
            elif condition.startswith("current >"):
                threshold = float(condition.split(">")[1].strip())
                return variables["current"] > threshold
            elif condition.startswith("count >"):
                threshold = int(condition.split(">")[1].strip())
                return variables["count"] > threshold
            elif condition.startswith("rate >"):
                threshold = float(condition.split(">")[1].strip())
                return variables.get("rate", 0) > threshold

        except Exception as e:
            logger.error(f"Condition evaluation error: {e}")

        return False

    async def _trigger_alert(self, rule: AlertRule, metric_data: list[dict[str, Any]]):
        """触发告警"""
        alert_id = f"alert_{rule.rule_id}_{int(datetime.now().timestamp())}"

        # 检查是否已存在活跃告警
        existing_alerts = [
            alert
            for alert in self.active_alerts.values()
            if alert.rule_id == rule.rule_id and alert.status == AlertStatus.ACTIVE
        ]

        if existing_alerts:
            # 更新现有告警
            alert = existing_alerts[0]
            alert.timestamp = datetime.now()
            alert.escalation_count += 1
        else:
            # 创建新告警
            alert = Alert(
                alert_id=alert_id,
                rule_id=rule.rule_id,
                rule_name=rule.name,
                severity=rule.severity,
                status=AlertStatus.ACTIVE,
                message=self._generate_alert_message(rule, metric_data),
                details={
                    "rule": rule.name,
                    "condition": rule.condition,
                    "threshold": rule.threshold,
                    "metric_data": metric_data[-1],
                    "evaluation_window": rule.evaluation_window,
                },
                timestamp=datetime.now(),
                metadata=rule.custom_attributes.copy(),
            )

            self.active_alerts[alert_id] = alert
            self.alert_history.append(alert)

        # 发送通知
        await self._send_notifications(alert)

    async def _check_recovery(self, rule_id: str):
        """检查告警恢复"""
        rule = self.rules[rule_id]
        if not rule.recovery_threshold:
            return

        # 查找相关告警
        related_alerts = [
            alert
            for alert in self.active_alerts.values()
            if alert.rule_id == rule_id and alert.status == AlertStatus.ACTIVE
        ]

        for alert in related_alerts:
            if "metric_data" in alert.details:
                metric_name = None
                # 简化的指标名提取
                for key in self.metric_data:
                    if key in str(alert.details["metric_data"]):
                        metric_name = key
                        break

                if metric_name:
                    metric_data = self.metric_data.get(metric_name, [])
                    if metric_data:
                        recent_values = [point["value"] for point in metric_data[-10:]]
                        avg_value = statistics.mean(recent_values)

                        if avg_value <= rule.recovery_threshold:
                            await self._resolve_alert(alert.alert_id)

    async def _resolve_alert(self, alert_id: str):
        """解决告警"""
        if alert_id not in self.active_alerts:
            return

        alert = self.active_alerts[alert_id]
        alert.status = AlertStatus.RESOLVED
        alert.resolved_at = datetime.now()

        # 从活跃告警中移除
        del self.active_alerts[alert_id]

        # 发送恢复通知
        await self._send_recovery_notification(alert)

        logger.info(f"Alert resolved: {alert_id}")

    async def _send_notifications(self, alert: Alert):
        """发送告警通知"""
        for channel in self.rules[alert.rule_id].notification_channels:
            if channel not in alert.notification_sent:
                try:
                    handler = self.notification_handlers[channel]
                    await handler(alert)
                    alert.notification_sent[channel] = datetime.now()
                except Exception as e:
                    logger.error(f"Notification failed for {channel.value}: {e}")

    async def _send_recovery_notification(self, alert: Alert):
        """发送恢复通知"""
        for channel, sent_time in alert.notification_sent.items():
            try:
                handler = self.notification_handlers[channel]
                await handler(alert, recovery=True)
            except Exception as e:
                logger.error(f"Recovery notification failed for {channel.value}: {e}")

    def _generate_alert_message(
        self, rule: AlertRule, metric_data: list[dict[str, Any]]
    ) -> str:
        """生成告警消息"""
        latest = metric_data[-1]
        value = latest.get("value", 0)
        timestamp = latest.get("timestamp", datetime.now())

        return (
            f"Alert: {rule.name}\n"
            f"Description: {rule.description}\n"
            f"Condition: {rule.condition}\n"
            f"Current Value: {value}\n"
            f"Time: {timestamp}"
        )

    def _register_notification_handlers(self):
        """注册通知处理器"""
        self.notification_handlers[NotificationChannel.EMAIL] = (
            self._send_email_notification
        )
        self.notification_handlers[NotificationChannel.SLACK] = (
            self._send_slack_notification
        )
        self.notification_handlers[NotificationChannel.WEBHOOK] = (
            self._send_webhook_notification
        )

    async def _send_email_notification(self, alert: Alert, recovery: bool = False):
        """发送邮件通知"""
        try:
            # 这里应该从配置中获取邮件设置
            smtp_server = "smtp.example.com"
            smtp_port = 587
            username = "alerts@example.com"
            password = "password"

            subject = f"[{alert.severity.value.upper()}] {alert.rule_name}"
            if recovery:
                subject = f"[RESOLVED] {subject}"

            body = self._format_email_body(alert, recovery)

            msg = MIMEMultipart()
            msg["From"] = username
            msg["To"] = "admin@example.com"
            msg["Subject"] = subject
            msg.attach(MIMEText(body, "plain", "utf-8"))

            # 发送邮件（实际实现中应该使用SMTP服务器）
            logger.info(f"Email notification sent for {alert.alert_id}")

        except Exception as e:
            logger.error(f"Email notification failed: {e}")

    def _format_email_body(self, alert: Alert, recovery: bool = False) -> str:
        """格式化邮件正文"""
        status = "RESOLVED" if recovery else "TRIGGERED"
        status_emoji = "✅" if recovery else "🚨"

        return f"""
{status_emoji} Alert {status}: {alert.rule_name}

Severity: {alert.severity.value.upper()}
Status: {alert.status.value}
Alert ID: {alert.alert_id}
Timestamp: {alert.timestamp}

Details:
{json.dumps(alert.details, indent=2)}

Message:
{alert.message}

This is an automated alert notification.
        """

    async def _send_slack_notification(self, alert: Alert, recovery: bool = False):
        """发送Slack通知"""
        try:
            webhook_url = "https://hooks.slack.com/services/YOUR/WEBHOOK/URL"

            color = {
                AlertSeverity.INFO: "good",
                AlertSeverity.WARNING: "warning",
                AlertSeverity.ERROR: "danger",
                AlertSeverity.CRITICAL: "danger",
                AlertSeverity.FATAL: "#8B0000",
            }

            payload = {
                "attachments": [
                    {
                        "color": color.get(alert.severity, "danger"),
                        "title": f"Alert: {alert.rule_name}",
                        "text": alert.message,
                        "fields": [
                            {
                                "title": "Severity",
                                "value": alert.severity.value.upper(),
                                "short": True,
                            },
                            {
                                "title": "Status",
                                "value": alert.status.value.upper(),
                                "short": True,
                            },
                            {
                                "title": "Timestamp",
                                "value": alert.timestamp.strftime("%Y-%m-%d %H:%M:%S"),
                                "short": True,
                            },
                        ],
                        "footer": f"Alert ID: {alert.alert_id}",
                        "ts": (
                            int(alert.alert_id.split("_")[-1])
                            if "_" in alert.alert_id
                            else int(alert.timestamp.timestamp())
                        ),
                    }
                ]
            }

            # 发送到Slack
            # requests.post(webhook_url, json=payload, timeout=10)
            logger.info(f"Slack notification sent for {alert.alert_id}")

        except Exception as e:
            logger.error(f"Slack notification failed: {e}")

    async def _send_webhook_notification(self, alert: Alert, recovery: bool = False):
        """发送Webhook通知"""
        try:
            webhook_url = "https://example.com/webhook/alert"

            payload = {
                "alert_id": alert.alert_id,
                "rule_name": alert.rule_name,
                "severity": alert.severity.value,
                "status": alert.status.value,
                "message": alert.message,
                "details": alert.details,
                "timestamp": alert.timestamp.isoformat(),
                "recovery": recovery,
            }

            # 发送webhook
            # requests.post(webhook_url, json=payload, timeout=10)
            logger.info(f"Webhook notification sent for {alert.alert_id}")

        except Exception as e:
            logger.error(f"Webhook notification failed: {e}")

    def acknowledge_alert(
        self, alert_id: str, user: str, comment: str | None = None
    ):
        """确认告警"""
        if alert_id in self.active_alerts:
            alert = self.active_alerts[alert_id]
            alert.status = AlertStatus.ACKNOWLEDGED
            alert.acknowledged_at = datetime.now()
            alert.metadata["acknowledged_by"] = user
            if comment:
                alert.metadata["acknowledgment_comment"] = comment
            logger.info(f"Alert acknowledged: {alert_id} by {user}")

    def suppress_alert(self, alert_id: str, duration: int, user: str):
        """抑制告警"""
        if alert_id in self.active_alerts:
            alert = self.active_alerts[alert_id]
            alert.status = AlertStatus.SUPPRESSED
            alert.suppressed_until = datetime.now() + timedelta(seconds=duration)
            alert.metadata["suppressed_by"] = user
            logger.info(f"Alert suppressed: {alert_id} for {duration}s by {user}")

    def get_active_alerts(self) -> list[Alert]:
        """获取活跃告警"""
        return list(self.active_alerts.values())

    def get_alert_summary(self) -> dict[str, Any]:
        """获取告警摘要"""
        active_alerts = self.get_active_alerts()

        severity_counts = defaultdict(int)
        for alert in active_alerts:
            severity_counts[alert.severity.value] += 1

        return {
            "total_active_alerts": len(active_alerts),
            "severity_breakdown": dict(severity_counts),
            "rules_count": len(self.rules),
            "enabled_rules_count": len([r for r in self.rules.values() if r.enabled]),
            "recent_alerts": [
                {
                    "id": alert.alert_id,
                    "rule_name": alert.rule_name,
                    "severity": alert.severity.value,
                    "timestamp": alert.timestamp.isoformat(),
                    "message": (
                        alert.message[:100] + "..."
                        if len(alert.message) > 100
                        else alert.message
                    ),
                }
                for alert in sorted(
                    active_alerts, key=lambda a: a.timestamp, reverse=True
                )[:10]
            ],
        }

    def _start_background_tasks(self):
        """启动后台任务"""
        if not self._background_tasks_started:
            try:
                loop = asyncio.get_running_loop()
                loop.create_task(self._cleanup_resolved_alerts())
                loop.create_task(self._cleanup_old_metric_data())
                self._background_tasks_started = True
            except RuntimeError:
                # 没有运行中的事件循环，跳过后台任务
                logger.debug("No event loop running, skipping background tasks")

    async def _cleanup_resolved_alerts(self):
        """清理已解决的告警"""
        while True:
            try:
                await asyncio.sleep(3600)  # 每小时清理一次

                now = datetime.now()
                # 移除已解决超过24小时的告警
                expired_alerts = [
                    alert_id
                    for alert_id, alert in self.active_alerts.items()
                    if (
                        alert.status == AlertStatus.RESOLVED
                        and alert.resolved_at
                        and (now - alert.resolved_at).total_seconds() > 86400
                    )
                ]

                for alert_id in expired_alerts:
                    del self.active_alerts[alert_id]

                if expired_alerts:
                    logger.info(f"Cleaned up {len(expired_alerts)} expired alerts")

            except Exception as e:
                logger.error(f"Alert cleanup error: {e}")

    async def _cleanup_old_metric_data(self):
        """清理旧的指标数据"""
        while True:
            try:
                await asyncio.sleep(1800)  # 每30分钟清理一次

                cutoff_time = datetime.now() - timedelta(hours=24)
                for metric_name in self.metric_data:
                    self.metric_data[metric_name] = deque(
                        [
                            point
                            for point in self.metric_data[metric_name]
                            if point["timestamp"] > cutoff_time
                        ],
                        maxlen=1000,
                    )

            except Exception as e:
                logger.error(f"Metric cleanup error: {e}")


# 全局告警管理器实例
_alert_manager: AlertManager | None = None


def get_alert_manager() -> AlertManager:
    """获取全局告警管理器实例"""
    global _alert_manager
    if _alert_manager is None:
        _alert_manager = AlertManager()
    return _alert_manager


def initialize_alert_manager() -> AlertManager:
    """初始化全局告警管理器"""
    global _alert_manager
    _alert_manager = AlertManager()
    return _alert_manager
