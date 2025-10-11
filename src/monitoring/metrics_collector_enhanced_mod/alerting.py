"""
告警管理 / Alerting Management

管理指标告警的触发、抑制和通知。
"""

import logging
from datetime import datetime, timedelta
from typing import Dict, Callable, Any, List, Optional

from .metric_types import AlertInfo

logger = logging.getLogger(__name__)


class AlertManager:
    """告警管理器

    负责管理指标告警规则和触发告警。
    """

    def __init__(self):
        """初始化告警管理器"""
        self.alert_rules: Dict[str, Dict[str, Any]] = {}
        self.active_alerts: Dict[str, AlertInfo] = {}
        self.alert_history: List[AlertInfo] = []
        self.alert_handlers: List[Callable[[AlertInfo], None]] = []
        self.suppression_rules: Dict[str, Dict[str, Any]] = {}

    def add_alert_rule(
        self,
        name: str,
        condition: Callable[[Dict[str, Any]], bool],
        severity: str = "medium",
        description: str = "",
        cooldown: int = 300,
    ):
        """
        添加告警规则

        Args:
            name: 告警名称
            condition: 告警条件函数
            severity: 严重程度
            description: 描述
            cooldown: 冷却时间（秒）
        """
        self.alert_rules[name] = {
            "condition": condition,
            "severity": severity,
            "description": description,
            "cooldown": cooldown,
            "last_triggered": None,
        }

    def remove_alert_rule(self, name: str):
        """
        移除告警规则

        Args:
            name: 告警名称
        """
        if name in self.alert_rules:
            del self.alert_rules[name]
            # 同时移除活跃的告警
            if name in self.active_alerts:
                del self.active_alerts[name]

    def check_alerts(self, metrics: Dict[str, Any]):
        """
        检查所有告警规则

        Args:
            metrics: 指标数据
        """
        now = datetime.now()

        for name, rule in self.alert_rules.items():
            try:
                # 检查冷却时间
                if rule["last_triggered"]:
                    cooldown_end = rule["last_triggered"] + timedelta(
                        seconds=rule["cooldown"]
                    )
                    if now < cooldown_end:
                        continue

                # 评估告警条件
                if rule["condition"](metrics):
                    self._trigger_alert(
                        name,
                        rule["description"] or f"Alert {name} triggered",
                        rule["severity"],
                        metrics,
                    )
                    rule["last_triggered"] = now

            except (ValueError, RuntimeError, TimeoutError) as e:
                logger.error(f"Error checking alert rule {name}: {e}")

    def _trigger_alert(
        self,
        name: str,
        message: str,
        severity: str,
        context: Dict[str, Any] = None,
    ):
        """
        触发告警

        Args:
            name: 告警名称
            message: 告警消息
            severity: 严重程度
            context: 上下文信息
        """
        # 创建告警信息
        alert = AlertInfo(
            name=name,
            message=message,
            severity=severity,
            context=context or {},
        )

        # 记录告警
        self.active_alerts[name] = alert
        self.alert_history.append(alert)

        # 限制历史记录大小
        if len(self.alert_history) > 1000:
            self.alert_history = self.alert_history[-500:]

        # 记录日志
        logger.warning(  # type: ignore
            f"ALERT: {name}",
            alert_name=name,
            message=message,
            severity=severity,
            timestamp=alert.timestamp.isoformat(),
            context=context,
        )

        # 调用告警处理器
        for handler in self.alert_handlers:
            try:
                handler(alert)
            except (ValueError, RuntimeError, TimeoutError) as e:
                logger.error(f"Error in alert handler: {e}")

    def resolve_alert(self, name: str, message: str = ""):
        """
        解决告警

        Args:
            name: 告警名称
            message: 解决消息
        """
        if name in self.active_alerts:
            alert = self.active_alerts[name]
            logger.info(  # type: ignore
                f"ALERT RESOLVED: {name}",
                alert_name=name,
                message=message or f"Alert {name} resolved",
                duration=str(datetime.now() - alert.timestamp),
            )
            del self.active_alerts[name]

    def add_alert_handler(self, handler: Callable[[AlertInfo], None]):
        """
        添加告警处理器

        Args:
            handler: 处理器函数
        """
        self.alert_handlers.append(handler)

    def get_active_alerts(self) -> List[AlertInfo]:
        """
        获取活跃的告警

        Returns:
            活跃告警列表
        """
        return list(self.active_alerts.values())

    def get_alert_history(
        self,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        severity: Optional[str] = None,
    ) -> List[AlertInfo]:
        """
        获取告警历史

        Args:
            start_time: 开始时间
            end_time: 结束时间
            severity: 严重程度过滤

        Returns:
            告警历史列表
        """
        history = self.alert_history

        # 时间过滤
        if start_time:
            history = [a for a in history if a.timestamp >= start_time]
        if end_time:
            history = [a for a in history if a.timestamp <= end_time]

        # 严重程度过滤
        if severity:
            history = [a for a in history if a.severity == severity]

        return history

    def get_alert_summary(self) -> Dict[str, Any]:
        """
        获取告警摘要

        Returns:
            告警摘要字典
        """
        # 统计各严重程度的告警数
        severity_counts = {}  # type: ignore
        for alert in self.active_alerts.values():
            severity_counts[alert.severity] = severity_counts.get(alert.severity, 0) + 1

        # 最近24小时告警趋势
        now = datetime.now()
        day_ago = now - timedelta(days=1)
        recent_alerts = [a for a in self.alert_history if a.timestamp >= day_ago]

        # 按小时统计
        hourly_counts = {}  # type: ignore
        for alert in recent_alerts:
            hour = alert.timestamp.strftime("%Y-%m-%d %H:00")
            hourly_counts[hour] = hourly_counts.get(hour, 0) + 1

        return {
            "active_alerts": len(self.active_alerts),
            "severity_breakdown": severity_counts,
            "recent_24h": len(recent_alerts),
            "hourly_trend": hourly_counts,
            "total_rules": len(self.alert_rules),
            "last_updated": now.isoformat(),
        }


class DefaultAlertHandlers:
    """默认告警处理器集合"""

    @staticmethod
    def log_handler(alert: AlertInfo):
        """
        日志告警处理器

        Args:
            alert: 告警信息
        """
        if alert.severity == "critical":
            logger.critical(
                f"CRITICAL ALERT: {alert.name}",
                extra={
                    "alert_name": alert.name,
                    "message": alert.message,
                    "severity": alert.severity,
                    "timestamp": alert.timestamp.isoformat(),
                },
            )
        elif alert.severity == "high":
            logger.error(
                f"HIGH ALERT: {alert.name}",
                extra={
                    "alert_name": alert.name,
                    "message": alert.message,
                    "severity": alert.severity,
                    "timestamp": alert.timestamp.isoformat(),
                },
            )

    @staticmethod
    def console_handler(alert: AlertInfo):
        """
        控制台告警处理器

        Args:
            alert: 告警信息
        """
        timestamp = alert.timestamp.strftime("%Y-%m-%d %H:%M:%S")
        print(f"\n[{timestamp}] 🚨 {alert.severity.upper()} ALERT: {alert.name}")
        print(f"   Message: {alert.message}")
        if alert.context:
            print(f"   Context: {alert.context}")
        print("-" * 50)

    @staticmethod
    def webhook_handler(webhook_url: str):
        """
        Webhook告警处理器工厂

        Args:
            webhook_url: Webhook URL

        Returns:
            Webhook处理器函数
        """

        def handler(alert: AlertInfo):
            try:
                import requests

                payload = {
                    "alert_name": alert.name,
                    "message": alert.message,
                    "severity": alert.severity,
                    "timestamp": alert.timestamp.isoformat(),
                    "context": alert.context,
                }

                requests.post(webhook_url, json=payload, timeout=5)
            except (ValueError, RuntimeError, TimeoutError) as e:
                logger.error(f"Failed to send webhook alert: {e}")

        return handler
