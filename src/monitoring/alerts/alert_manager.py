"""
告警管理器主类

整合所有告警组件，提供统一的告警管理接口。
"""

import logging
import uuid
from collections import defaultdict
from datetime import datetime, timedelta
from typing import Any, Callable, Dict, List, Optional

from .channels import BaseAlertChannel, LogAlertChannel, PrometheusAlertChannel
from .metrics import PrometheusMetrics
from .models import Alert, AlertChannel, AlertLevel, AlertRule, AlertStatus
from .rules import AlertRuleEngine

logger = logging.getLogger(__name__)


class AlertManager:
    """
    告警管理器主类

    负责：
    - 告警创建和管理
    - 告警路由和发送
    - 告警状态跟踪
    - 各类指标的更新
    """

    def __init__(self, registry=None):
        """
        初始化告警管理器

        Args:
            registry: Prometheus注册表
        """
        # 告警存储
        self.alerts: List[Alert] = []

        # 组件初始化
        self.rule_engine = AlertRuleEngine()
        self.metrics = PrometheusMetrics(registry)

        # 告警处理器（渠道）
        self.alert_handlers: Dict[AlertChannel, List[BaseAlertChannel]] = defaultdict(list)

        # 注册默认渠道
        self._register_default_channels()

        # 处理统计
        self.stats = {
            "alerts_created": 0,
            "alerts_sent": 0,
            "alerts_failed": 0,
            "alerts_resolved": 0,
        }

        self.logger = logging.getLogger(f"alerts.{self.__class__.__name__}")

    def _register_default_channels(self) -> None:
        """注册默认的告警渠道"""
        # 注册日志渠道
        log_channel = LogAlertChannel()
        self.register_handler(AlertChannel.LOG, log_channel)

        # 注册Prometheus渠道
        prometheus_channel = PrometheusAlertChannel(metrics=self.metrics)
        self.register_handler(AlertChannel.PROMETHEUS, prometheus_channel)

    def register_handler(self, channel: AlertChannel, handler: BaseAlertChannel) -> None:
        """
        注册告警处理器

        Args:
            channel: 渠道类型
            handler: 处理器实例
        """
        self.alert_handlers[channel].append(handler)
        self.logger.info(f"注册 {channel.value} 渠道处理器")

    def fire_alert(
        self,
        title: str,
        message: str,
        level: AlertLevel,
        source: str,
        labels: Optional[Dict[str, str]] = None,
        annotations: Optional[Dict[str, str]] = None,
        rule_id: Optional[str] = None,
        alert_id: Optional[str] = None,
    ) -> Optional[Alert]:
        """
        触发告警

        Args:
            title: 告警标题
            message: 告警消息
            level: 告警级别
            source: 告警源
            labels: 标签
            annotations: 注释
            rule_id: 规则ID
            alert_id: 告警ID

        Returns:
            创建的告警对象或None
        """
        try:
            # 生成告警ID
            alert_id = alert_id or self._generate_alert_id(title, source)

            # 检查是否需要限流
            if rule_id and self._should_throttle(alert_id, rule_id):
                self.logger.debug(f"告警被限流: {alert_id}")
                return None

            # 创建告警
            alert = Alert(
                alert_id=alert_id,
                title=title,
                message=message,
                level=level,
                source=source,
                labels=labels,
                annotations=annotations,
            )

            # 添加到存储
            self.add_alert(alert)

            # 发送告警
            self._send_alert(alert, rule_id)

            # 更新指标
            self._update_alert_metrics(alert, rule_id)

            self.stats["alerts_created"] += 1
            return alert

        except Exception as e:
            self.logger.error(f"创建告警失败: {e}", exc_info=True)
            return None

    def _generate_alert_id(self, title: str, source: str) -> str:
        """
        生成告警ID

        Args:
            title: 告警标题
            source: 告警源

        Returns:
            告警ID
        """
        # 使用时间戳和UUID确保唯一性
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        unique_id = str(uuid.uuid4())[:8]
        return f"{source}_{title}_{timestamp}_{unique_id}".replace(" ", "_")

    def _should_throttle(self, alert_id: str, rule_id: str) -> bool:
        """
        检查是否应该限流

        Args:
            alert_id: 告警ID
            rule_id: 规则ID

        Returns:
            是否应该限流
        """
        rule = self.rule_engine.get_rule(rule_id)
        if rule:
            current_time = datetime.now()
            return rule.should_throttle(current_time)
        return False

    def _send_alert(self, alert: Alert, rule_id: Optional[str]) -> None:
        """
        发送告警

        Args:
            alert: 告警对象
            rule_id: 规则ID
        """
        # 获取规则指定的渠道
        channels = []
        if rule_id:
            rule = self.rule_engine.get_rule(rule_id)
            if rule:
                channels = rule.channels

        # 如果没有指定渠道，使用默认渠道
        if not channels:
            channels = [AlertChannel.LOG, AlertChannel.PROMETHEUS]

        # 发送到所有指定渠道
        for channel in channels:
            handlers = self.alert_handlers.get(channel, [])
            for handler in handlers:
                try:
                    success = handler.send_alert(alert, rule_id=rule_id)
                    if success:
                        self.stats["alerts_sent"] += 1
                    else:
                        self.stats["alerts_failed"] += 1
                except Exception as e:
                    self.logger.error(f"发送告警失败: {e}")
                    self.stats["alerts_failed"] += 1

    def _update_alert_metrics(self, alert: Alert, rule_id: Optional[str]) -> None:
        """
        更新告警指标

        Args:
            alert: 告警对象
            rule_id: 规则ID
        """
        # 更新Prometheus指标
        self.metrics.update_alert_metrics(alert, rule_id)

        # 更新活跃告警计数
        self._update_active_alerts_metrics()

    def _update_active_alerts_metrics(self) -> None:
        """更新活跃告警指标"""
        # 统计各级别活跃告警数量
        level_counts: Dict[str, int] = defaultdict(int)
        for alert in self.alerts:
            if alert.status == AlertStatus.ACTIVE:
                level_counts[alert.level.value] += 1

        # 更新Prometheus指标
        for level, count in level_counts.items():
            self.metrics.active_alerts.labels(level=level).set(count)

    def add_alert(self, alert: Alert) -> None:
        """
        添加告警

        Args:
            alert: 告警对象
        """
        self.alerts.append(alert)
        self.logger.debug(f"添加告警: {alert.alert_id}")

    def resolve_alert(self, alert_id: str) -> bool:
        """
        解决告警

        Args:
            alert_id: 告警ID

        Returns:
            是否成功
        """
        for alert in self.alerts:
            if alert.alert_id == alert_id and alert.status == AlertStatus.ACTIVE:
                alert.resolve()
                self.stats["alerts_resolved"] += 1
                self._update_active_alerts_metrics()
                self.logger.info(f"解决告警: {alert_id}")
                return True
        return False

    def get_active_alerts(self, level: Optional[AlertLevel] = None) -> List[Alert]:
        """
        获取活跃告警

        Args:
            level: 告警级别过滤

        Returns:
            活跃告警列表
        """
        alerts = [a for a in self.alerts if a.status == AlertStatus.ACTIVE]

        if level:
            alerts = [a for a in alerts if a.level == level]

        return alerts

    def get_alert_summary(self) -> Dict[str, Any]:
        """
        获取告警摘要

        Returns:
            告警摘要
        """
        total_alerts = len(self.alerts)
        active_alerts = len(self.get_active_alerts())

        # 按级别统计
        by_level: Dict[str, int] = defaultdict(int)
        for alert in self.alerts:
            by_level[alert.level.value] += 1

        # 按来源统计
        by_source: Dict[str, int] = defaultdict(int)
        for alert in self.alerts:
            by_source[alert.source] += 1

        return {
            "total_alerts": total_alerts,
            "active_alerts": active_alerts,
            "resolved_alerts": total_alerts - active_alerts,
            "by_level": dict(by_level),
            "by_source": dict(by_source),
            "statistics": self.stats,
        }

    def update_quality_metrics(self, quality_data: Dict[str, Any]) -> None:
        """
        更新数据质量指标

        Args:
            quality_data: 质量数据
        """
        try:
            self.metrics.update_quality_metrics(quality_data)

            # 检查是否需要触发告警
            self._check_quality_alerts(quality_data)

        except Exception as e:
            self.logger.error(f"更新质量指标失败: {e}")

    def update_anomaly_metrics(self, anomalies: List[Any]) -> None:
        """
        更新异常指标

        Args:
            anomalies: 异常列表
        """
        try:
            self.metrics.update_anomaly_metrics(anomalies)

            # 检查是否需要触发告警
            self._check_anomaly_alerts(anomalies)

        except Exception as e:
            self.logger.error(f"更新异常指标失败: {e}")

    def _check_quality_alerts(self, quality_data: Dict[str, Any]) -> None:
        """
        检查并触发质量告警

        Args:
            quality_data: 质量数据
        """
        table_name = quality_data.get("table_name", "unknown")
        quality_score = quality_data.get("quality_score", 1.0)
        freshness_hours = quality_data.get("freshness_hours", 0)

        # 评估质量分数规则
        if quality_score < 0.5:
            self.fire_alert(
                title=f"数据质量严重告警 - {table_name}",
                message=f"数据质量评分过低: {quality_score:.2f}",
                level=AlertLevel.CRITICAL,
                source="quality_monitor",
                labels={"table": table_name, "metric": "quality_score"},
                rule_id="data_quality_critical",
            )
        elif quality_score < 0.8:
            self.fire_alert(
                title=f"数据质量警告 - {table_name}",
                message=f"数据质量评分较低: {quality_score:.2f}",
                level=AlertLevel.WARNING,
                source="quality_monitor",
                labels={"table": table_name, "metric": "quality_score"},
                rule_id="data_quality_warning",
            )

        # 评估新鲜度规则
        if freshness_hours > 24:
            self.fire_alert(
                title=f"数据新鲜度告警 - {table_name}",
                message=f"数据已 {freshness_hours:.1f} 小时未更新",
                level=AlertLevel.WARNING,
                source="quality_monitor",
                labels={"table": table_name, "metric": "freshness"},
                rule_id="data_freshness",
            )

    def _check_anomaly_alerts(self, anomalies: List[Any]) -> None:
        """
        检查并触发异常告警

        Args:
            anomalies: 异常列表
        """
        for anomaly in anomalies:
            if hasattr(anomaly, 'anomaly_score'):
                if anomaly.anomaly_score > 0.2:
                    self.fire_alert(
                        title=f"数据异常严重告警 - {anomaly.table_name}.{anomaly.column_name}",
                        message=f"{anomaly.description} (得分: {anomaly.anomaly_score:.3f})",
                        level=AlertLevel.CRITICAL,
                        source="anomaly_detector",
                        labels={
                            "table": anomaly.table_name,
                            "column": anomaly.column_name,
                            "anomaly_type": getattr(anomaly, 'anomaly_type', 'unknown').value,
                        },
                        rule_id="anomaly_critical",
                    )
                elif anomaly.anomaly_score > 0.1:
                    self.fire_alert(
                        title=f"数据异常警告 - {anomaly.table_name}.{anomaly.column_name}",
                        message=f"{anomaly.description} (得分: {anomaly.anomaly_score:.3f})",
                        level=AlertLevel.WARNING,
                        source="anomaly_detector",
                        labels={
                            "table": anomaly.table_name,
                            "column": anomaly.column_name,
                            "anomaly_type": getattr(anomaly, 'anomaly_type', 'unknown').value,
                        },
                        rule_id="anomaly_warning",
                    )

    def clear_resolved_alerts(self, older_than_hours: int = 24) -> int:
        """
        清理已解决的告警

        Args:
            older_than_hours: 清理多少小时前的告警

        Returns:
            清理的告警数量
        """
        cutoff_time = datetime.now() - timedelta(hours=older_than_hours)

        original_count = len(self.alerts)
        self.alerts = [
            alert for alert in self.alerts
            if not (
                alert.status == AlertStatus.RESOLVED
                and alert.resolved_at
                and alert.resolved_at < cutoff_time
            )
        ]

        cleared_count = original_count - len(self.alerts)
        if cleared_count > 0:
            self.logger.info(f"清理了 {cleared_count} 个已解决的告警")

        return cleared_count