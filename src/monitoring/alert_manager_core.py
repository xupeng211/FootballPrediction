"""
告警管理器核心
Alert Manager Core

告警管理的主要业务逻辑。
"""

import logging
from collections import defaultdict
from datetime import datetime, timedelta
from typing import Any, Callable, Dict, List, Optional

from .alert_models import Alert, AlertRule, AlertSeverity, AlertChannel, AlertStatus
from .alert_handlers import (
    AlertHandler,
    LogHandler,
    PrometheusHandler,
    WebhookHandler,
    EmailHandler,
    PrometheusMetrics,
)

logger = logging.getLogger(__name__)


class AlertManager:
    """告警管理器"""

    def __init__(self) -> None:
        """初始化告警管理器"""
        self.rules: Dict[str, AlertRule] = {}
        self.handlers: Dict[AlertChannel, List[AlertHandler]] = defaultdict(list)
        self.alert_history: List[Alert] = []
        self.throttled_alerts: Dict[str, datetime] = {}

        # 初始化 Prometheus 指标
        self.metrics = PrometheusMetrics()

        # 注册默认处理器
        self._register_default_handlers()

    def _init_default_rules(self) -> None:
        """初始化默认告警规则"""
        # 数据质量告警规则
        data_quality_rules = [
            AlertRule(
                rule_id="dq_null_rate_high",
                name="空值率过高",
                condition="null_rate > 0.1",
                severity=AlertSeverity.HIGH,
                channels=[AlertChannel.LOG, AlertChannel.PROMETHEUS],
                description="当数据空值率超过10%时触发",
            ),
            AlertRule(
                rule_id="dq_duplicate_rate_high",
                name="重复率过高",
                condition="duplicate_rate > 0.05",
                severity=AlertSeverity.MEDIUM,
                channels=[AlertChannel.LOG],
                description="当数据重复率超过5%时触发",
            ),
            AlertRule(
                rule_id="dq_data_freshness",
                name="数据新鲜度不足",
                condition="data_age_hours > 24",
                severity=AlertSeverity.MEDIUM,
                channels=[AlertChannel.LOG],
                description="当数据超过24小时未更新时触发",
            ),
        ]

        for rule in data_quality_rules:
            self.add_rule(rule)

    def _register_default_handlers(self) -> None:
        """注册默认处理器"""
        # 日志处理器
        log_handler = LogHandler()
        self.handlers[AlertChannel.LOG].append(log_handler)

        # Prometheus 处理器
        prometheus_handler = PrometheusHandler(self.metrics)
        self.handlers[AlertChannel.PROMETHEUS].append(prometheus_handler)

    def register_handler(
        self,
        channel: AlertChannel,
        handler: AlertHandler,
        replace: bool = False,
    ) -> None:
        """注册告警处理器"""
        if replace:
            self.handlers[channel] = [handler]
        else:
            self.handlers[channel].append(handler)
        logger.info(f"Registered handler for channel {channel.value}")

    def add_rule(self, rule: AlertRule) -> None:
        """添加告警规则"""
        self.rules[rule.id] = rule
        logger.info(f"Added alert rule: {rule.name}")

    def remove_rule(self, rule_id: str) -> bool:
        """移除告警规则"""
        if rule_id in self.rules:
            del self.rules[rule_id]
            logger.info(f"Removed alert rule: {rule_id}")
            return True
        return False

    def fire_alert(
        self,
        title: str,
        message: str,
        level: str,
        source: str,
        rule_id: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Optional[Alert]:
        """触发告警"""
        try:
            # 检查规则
            if rule_id and rule_id in self.rules:
                rule = self.rules[rule_id]
                if not rule.enabled:
                    logger.debug(f"Rule {rule_id} is disabled")
                    return None

                # 检查节流
                if self._should_throttle(title, rule_id):
                    logger.debug(f"Alert throttled: {title}")
                    return None

                # 更新规则触发信息
                rule.last_triggered = datetime.utcnow()
                rule.trigger_count += 1

            # 创建告警
            from .alert_models import AlertLevel

            alert = Alert(
                title=title,
                message=message,
                level=AlertLevel(level.upper()),
                source=source,
                context=context,
                metadata=metadata,
            )

            # 检查是否已存在相同的活跃告警
            if self._has_active_alert(alert):
                logger.debug(f"Alert already active: {alert.id}")
                return alert

            # 添加到历史记录
            self.alert_history.append(alert)
            self._cleanup_old_alerts()

            # 发送告警
            self._send_alert(alert, rule_id)

            # 更新指标
            self._update_alert_metrics(alert, rule_id)

            logger.info(f"Alert fired: {alert.id} - {title}")
            return alert

        except Exception as e:
            logger.error(f"Failed to fire alert: {str(e)}")
            return None

    def _generate_alert_id(self, title: str, source: str) -> str:
        """生成告警ID"""
        import hashlib

        timestamp = datetime.utcnow().isoformat()
        content = f"{title}{source}{timestamp}"
        return hashlib.md5(content.encode()).hexdigest()[:16]

    def _should_throttle(self, alert_id: str, rule_id: Optional[str]) -> bool:
        """检查是否应该节流"""
        if not rule_id or rule_id not in self.rules:
            return False

        rule = self.rules[rule_id]
        throttle_key = f"{rule_id}:{alert_id}"

        if throttle_key in self.throttled_alerts:
            last_time = self.throttled_alerts[throttle_key]
            if datetime.utcnow() - last_time < rule.throttle_duration:
                return True

        self.throttled_alerts[throttle_key] = datetime.utcnow()
        return False

    def _send_alert(self, alert: Alert, rule_id: Optional[str]) -> None:
        """发送告警"""
        # 确定发送渠道
        channels = [AlertChannel.LOG]  # 默认总是记录日志

        if rule_id and rule_id in self.rules:
            channels.extend(self.rules[rule_id].channels)

        # 去重
        channels = list(set(channels))

        # 发送到各渠道
        for channel in channels:
            if channel in self.handlers:
                for handler in self.handlers[channel]:
                    try:
                        import asyncio

                        if asyncio.iscoroutinefunction(handler.handle):
                            # 异步处理器
                            asyncio.create_task(handler.handle(alert))
                            # 不等待结果，让它在后台执行
                        else:
                            # 同步处理器
                            handler.handle(alert)
                    except Exception as e:
                        logger.error(f"Handler error: {str(e)}")

    def _update_alert_metrics(self, alert: Alert, rule_id: Optional[str]) -> None:
        """更新告警指标"""
        try:
            # 更新计数器
            self.metrics.increment_counter(alert)

            # 更新活跃告警数量
            active_alerts = [
                a for a in self.alert_history if a.status == AlertStatus.ACTIVE
            ]
            self.metrics.set_active_gauge(active_alerts)

        except Exception as e:
            logger.error(f"Failed to update metrics: {str(e)}")

    def _cleanup_old_alerts(self) -> None:
        """清理旧告警记录"""
        # 只保留最近1000条记录
        if len(self.alert_history) > 1000:
            self.alert_history = self.alert_history[-1000:]

        # 清理节流记录
        now = datetime.utcnow()
        expired_throttles = [
            key
            for key, time in self.throttled_alerts.items()
            if now - time > timedelta(hours=1)
        ]
        for key in expired_throttles:
            del self.throttled_alerts[key]

    def _has_active_alert(self, new_alert: Alert) -> bool:
        """检查是否已存在相同的活跃告警"""
        for alert in self.alert_history:
            if (
                alert.status == AlertStatus.ACTIVE
                and alert.title == new_alert.title
                and alert.source == new_alert.source
                and (datetime.utcnow() - alert.timestamp).minutes < 5
            ):
                return True
        return False

    def get_active_alerts(self, source: Optional[str] = None) -> List[Alert]:
        """获取活跃告警"""
        alerts = [
            alert for alert in self.alert_history if alert.status == AlertStatus.ACTIVE
        ]

        if source:
            alerts = [a for a in alerts if a.source == source]

        return sorted(alerts, key=lambda x: x.timestamp, reverse=True)

    def get_alert_statistics(self) -> Dict[str, Any]:
        """获取告警统计"""
        active_alerts = [
            a for a in self.alert_history if a.status == AlertStatus.ACTIVE
        ]
        resolved_alerts = [
            a for a in self.alert_history if a.status == AlertStatus.RESOLVED
        ]

        # 按严重程度统计
        severity_counts = defaultdict(int)
        for alert in active_alerts:
            severity_counts[alert.severity.value] += 1

        # 按来源统计
        source_counts = defaultdict(int)
        for alert in active_alerts:
            source_counts[alert.source] += 1

        return {
            "total_active": len(active_alerts),
            "total_resolved": len(resolved_alerts),
            "by_severity": dict(severity_counts),
            "by_source": dict(source_counts),
            "total_rules": len(self.rules),
            "enabled_rules": sum(1 for rule in self.rules.values() if rule.enabled),
        }
