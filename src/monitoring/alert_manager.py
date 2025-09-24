"""
告警管理器

实现数据质量监控和异常检测的告警机制，支持：
- 日志告警
- Prometheus指标告警
- 告警规则配置
- 告警去重和聚合

基于 DATA_DESIGN.md 数据质量监控设计。
"""

import logging
from collections import defaultdict
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Callable, Dict, List, Optional

from prometheus_client import REGISTRY, CollectorRegistry, Counter, Gauge, Histogram

logger = logging.getLogger(__name__)


class AlertLevel(Enum):
    """告警级别"""

    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


class AlertStatus(Enum):
    """告警状态"""

    ACTIVE = "active"
    RESOLVED = "resolved"
    SILENCED = "silenced"


class AlertChannel(Enum):
    """告警渠道"""

    LOG = "log"
    PROMETHEUS = "prometheus"
    WEBHOOK = "webhook"
    EMAIL = "email"


class Alert:
    """告警对象"""

    def __init__(
        self,
        alert_id: str,
        title: str,
        message: str,
        level: AlertLevel,
        source: str,
        labels: Optional[Dict[str, str]] = None,
        annotations: Optional[Dict[str, str]] = None,
        created_at: Optional[datetime] = None,
    ):
        """
        初始化告警

        Args:
            alert_id: 告警ID
            title: 告警标题
            message: 告警消息
            level: 告警级别
            source: 告警源
            labels: 标签
            annotations: 注释
            created_at: 创建时间
        """
        self.alert_id = alert_id
        self.title = title
        self.message = message
        self.level = level
        self.source = source
        self.labels = labels or {}
        self.annotations = annotations or {}
        self.created_at = created_at or datetime.now()
        self.status = AlertStatus.ACTIVE
        self.resolved_at: Optional[datetime] = None

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            "alert_id": self.alert_id,
            "title": self.title,
            "message": self.message,
            "level": self.level.value,
            "source": self.source,
            "labels": self.labels,
            "annotations": self.annotations,
            "status": self.status.value,
            "created_at": self.created_at.isoformat(),
            "resolved_at": self.resolved_at.isoformat() if self.resolved_at else None,
        }

    def resolve(self) -> None:
        """解决告警"""
        self.status = AlertStatus.RESOLVED
        self.resolved_at = datetime.now()

    def silence(self) -> None:
        """静默告警"""
        self.status = AlertStatus.SILENCED


class AlertRule:
    """告警规则"""

    def __init__(
        self,
        rule_id: str,
        name: str,
        condition: str,
        level: AlertLevel,
        channels: List[AlertChannel],
        throttle_seconds: int = 300,  # 5分钟内去重
        enabled: bool = True,
    ):
        """
        初始化告警规则

        Args:
            rule_id: 规则ID
            name: 规则名称
            condition: 告警条件
            level: 告警级别
            channels: 告警渠道
            throttle_seconds: 去重时间（秒）
            enabled: 是否启用
        """
        self.rule_id = rule_id
        self.name = name
        self.condition = condition
        self.level = level
        self.channels = channels
        self.throttle_seconds = throttle_seconds
        self.enabled = enabled
        self.last_fired: Optional[datetime] = None


class PrometheusMetrics:
    """Prometheus指标管理"""

    def __init__(self, registry: Optional[CollectorRegistry] = None):
        """
        初始化Prometheus指标

        Args:
            registry: Prometheus注册表，默认使用全局注册表
                     在测试环境中，使用独立的 CollectorRegistry 实例能够：
                     1. 避免不同测试间指标状态的相互干扰
                     2. 确保测试隔离性和可重复性
                     3. 防止指标名称冲突导致的注册错误
                     这是处理 Prometheus 指标测试的标准做法。
        """
        self.registry = registry or REGISTRY

        # 数据质量指标
        self.data_freshness_hours = Gauge(
            "data_freshness_hours",
            "Data freshness in hours",
            ["table_name"],
            registry=self.registry,
        )

        self.data_completeness_ratio = Gauge(
            "data_completeness_ratio",
            "Data completeness ratio",
            ["table_name"],
            registry=self.registry,
        )

        self.data_quality_score = Gauge(
            "data_quality_score",
            "Overall data quality score",
            ["table_name"],
            registry=self.registry,
        )

        # 异常检测指标
        self.anomalies_detected_total = Counter(
            "anomalies_detected_total",
            "Total number of anomalies detected",
            ["table_name", "column_name", "anomaly_type", "severity"],
            registry=self.registry,
        )

        self.anomaly_score = Gauge(
            "anomaly_score",
            "Anomaly score for data",
            ["table_name", "column_name"],
            registry=self.registry,
        )

        # 告警指标
        self.alerts_fired_total = Counter(
            "alerts_fired_total",
            "Total number of alerts fired",
            ["level", "source", "rule_id"],
            registry=self.registry,
        )

        self.active_alerts = Gauge(
            "active_alerts",
            "Number of active alerts",
            ["level"],
            registry=self.registry,
        )

        # 系统健康指标
        self.monitoring_check_duration_seconds = Histogram(
            "monitoring_check_duration_seconds",
            "Duration of monitoring checks",
            ["check_type"],
            registry=self.registry,
        )

        self.monitoring_errors_total = Counter(
            "monitoring_errors_total",
            "Total number of monitoring errors",
            ["error_type"],
            registry=self.registry,
        )


class AlertManager:
    """
    告警管理器主类

    负责：
    - 告警规则管理
    - 告警发送和路由
    - 告警去重和聚合
    - Prometheus指标更新
    """

    def __init__(self):
        """初始化告警管理器"""
        self.alerts: List[Alert] = []
        self.rules: Dict[str, AlertRule] = {}
        self.alert_handlers: Dict[AlertChannel, List[Callable]] = defaultdict(list)
        self.metrics = PrometheusMetrics()

        # 初始化默认告警规则
        self._init_default_rules()

        # 注册默认处理器
        self._register_default_handlers()

        logger.info("告警管理器初始化完成")

    def _init_default_rules(self) -> None:
        """初始化默认告警规则"""
        default_rules = [
            # 数据新鲜度告警
            AlertRule(
                rule_id="data_freshness_critical",
                name="数据新鲜度严重告警",
                condition="freshness_hours > 24",
                level=AlertLevel.CRITICAL,
                channels=[AlertChannel.LOG, AlertChannel.PROMETHEUS],
                throttle_seconds=1800,  # 30分钟去重
            ),
            AlertRule(
                rule_id="data_freshness_warning",
                name="数据新鲜度警告",
                condition="freshness_hours > 12",
                level=AlertLevel.WARNING,
                channels=[AlertChannel.LOG, AlertChannel.PROMETHEUS],
                throttle_seconds=3600,  # 1小时去重
            ),
            # 数据完整性告警
            AlertRule(
                rule_id="data_completeness_critical",
                name="数据完整性严重告警",
                condition="completeness_ratio < 0.8",
                level=AlertLevel.CRITICAL,
                channels=[AlertChannel.LOG, AlertChannel.PROMETHEUS],
                throttle_seconds=900,  # 15分钟去重
            ),
            AlertRule(
                rule_id="data_completeness_warning",
                name="数据完整性警告",
                condition="completeness_ratio < 0.95",
                level=AlertLevel.WARNING,
                channels=[AlertChannel.LOG, AlertChannel.PROMETHEUS],
                throttle_seconds=1800,
            ),
            # 数据质量告警
            AlertRule(
                rule_id="data_quality_critical",
                name="数据质量严重告警",
                condition="quality_score < 0.7",
                level=AlertLevel.CRITICAL,
                channels=[AlertChannel.LOG, AlertChannel.PROMETHEUS],
                throttle_seconds=900,
            ),
            # 异常检测告警
            AlertRule(
                rule_id="anomaly_critical",
                name="数据异常严重告警",
                condition="anomaly_score > 0.2",
                level=AlertLevel.CRITICAL,
                channels=[AlertChannel.LOG, AlertChannel.PROMETHEUS],
                throttle_seconds=300,  # 5分钟去重
            ),
            AlertRule(
                rule_id="anomaly_warning",
                name="数据异常警告",
                condition="anomaly_score > 0.1",
                level=AlertLevel.WARNING,
                channels=[AlertChannel.LOG, AlertChannel.PROMETHEUS],
                throttle_seconds=600,
            ),
        ]

        for rule in default_rules:
            self.rules[rule.rule_id] = rule

    def _register_default_handlers(self) -> None:
        """注册默认告警处理器"""
        # 注册日志处理器
        self.register_handler(AlertChannel.LOG, self._log_handler)

        # 注册Prometheus处理器
        self.register_handler(AlertChannel.PROMETHEUS, self._prometheus_handler)

    def register_handler(
        self, channel: AlertChannel, handler: Callable[[Alert], None]
    ) -> None:
        """
        注册告警处理器

        Args:
            channel: 告警渠道
            handler: 处理器函数
        """
        self.alert_handlers[channel].append(handler)
        logger.info(f"注册告警处理器: {channel.value}")

    def add_rule(self, rule: AlertRule) -> None:
        """
        添加告警规则

        Args:
            rule: 告警规则
        """
        self.rules[rule.rule_id] = rule
        logger.info(f"添加告警规则: {rule.name}")

    def remove_rule(self, rule_id: str) -> bool:
        """
        移除告警规则

        Args:
            rule_id: 规则ID

        Returns:
            bool: 是否成功移除
        """
        if rule_id in self.rules:
            del self.rules[rule_id]
            logger.info(f"移除告警规则: {rule_id}")
            return True
        return False

    def fire_alert(
        self,
        title: str,
        message: str,
        level: AlertLevel,
        source: str,
        labels: Optional[Dict[str, str]] = None,
        annotations: Optional[Dict[str, str]] = None,
        rule_id: Optional[str] = None,
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
            rule_id: 关联的规则ID

        Returns:
            Optional[Alert]: 创建的告警对象，如果被去重则返回None
        """
        # 生成告警ID
        alert_id = self._generate_alert_id(title, source, labels)

        # 检查去重
        if self._should_throttle(alert_id, rule_id):
            logger.debug(f"告警被去重: {alert_id}")
            return None

        # 创建告警
        alert = Alert(
            alert_id=alert_id,
            title=title,
            message=message,
            level=level,
            source=source,
            labels=labels or {},
            annotations=annotations or {},
        )

        # 添加到告警列表
        self.alerts.append(alert)

        # 更新规则最后触发时间
        if rule_id and rule_id in self.rules:
            self.rules[rule_id].last_fired = datetime.now()

        # 发送告警
        self._send_alert(alert, rule_id)

        # 更新指标
        self._update_alert_metrics(alert, rule_id)

        logger.info(f"触发告警: {title} [{level.value}]")
        return alert

    def _generate_alert_id(
        self, title: str, source: str, labels: Optional[Dict[str, str]]
    ) -> str:
        """
        生成告警ID

        Args:
            title: 告警标题
            source: 告警源
            labels: 标签

        Returns:
            str: 告警ID
        """
        import hashlib

        content = f"{title}|{source}"
        if labels:
            sorted_labels = sorted(labels.items())
            content += "|" + "|".join([f"{k}={v}" for k, v in sorted_labels])

        return hashlib.md5(content.encode(), usedforsecurity=False).hexdigest()[:12]

    def _should_throttle(self, alert_id: str, rule_id: Optional[str]) -> bool:
        """
        检查是否应该去重

        Args:
            alert_id: 告警ID
            rule_id: 规则ID

        Returns:
            bool: 是否应该去重
        """
        if not rule_id or rule_id not in self.rules:
            return False

        rule = self.rules[rule_id]
        if not rule.last_fired:
            return False

        # 检查去重时间
        throttle_delta = timedelta(seconds=rule.throttle_seconds)
        return datetime.now() - rule.last_fired < throttle_delta

    def _send_alert(self, alert: Alert, rule_id: Optional[str]) -> None:
        """
        发送告警

        Args:
            alert: 告警对象
            rule_id: 规则ID
        """
        # 获取告警渠道
        channels = []
        if rule_id and rule_id in self.rules:
            channels = self.rules[rule_id].channels
        else:
            # 默认渠道
            channels = [AlertChannel.LOG]

        # 发送到各个渠道
        for channel in channels:
            handlers = self.alert_handlers.get(channel, [])
            for handler in handlers:
                try:
                    handler(alert)
                except Exception as e:
                    logger.error(f"告警处理器错误 {channel.value}: {e}")
                    self.metrics.monitoring_errors_total.labels(
                        error_type="alert_handler"
                    ).inc()

    def _update_alert_metrics(self, alert: Alert, rule_id: Optional[str]) -> None:
        """
        更新告警指标

        Args:
            alert: 告警对象
            rule_id: 规则ID
        """
        # 更新告警计数
        self.metrics.alerts_fired_total.labels(
            level=alert.level.value, source=alert.source, rule_id=rule_id or "unknown"
        ).inc()

        # 更新活跃告警数量
        # Count active alerts for monitoring purposes
        _ = len([a for a in self.alerts if a.status == AlertStatus.ACTIVE])
        level_counts: Dict[str, int] = defaultdict(int)
        for a in self.alerts:
            if a.status == AlertStatus.ACTIVE:
                level_counts[a.level.value] += 1

        for level, count in level_counts.items():
            self.metrics.active_alerts.labels(level=level).set(count)

    def _log_handler(self, alert: Alert) -> None:
        """
        日志告警处理器

        Args:
            alert: 告警对象
        """
        log_level = {
            AlertLevel.INFO: logging.INFO,
            AlertLevel.WARNING: logging.WARNING,
            AlertLevel.ERROR: logging.ERROR,
            AlertLevel.CRITICAL: logging.CRITICAL,
        }.get(alert.level, logging.INFO)

        logger.log(
            log_level,
            f"[ALERT] {alert.title}: {alert.message} "
            f"(ID: {alert.alert_id}, Source: {alert.source}, Labels: {alert.labels})",
        )

    def _prometheus_handler(self, alert: Alert) -> None:
        """
        Prometheus告警处理器

        Args:
            alert: 告警对象
        """
        # Prometheus指标在_update_alert_metrics中已更新
        # 这里可以添加额外的Prometheus特定逻辑

    def resolve_alert(self, alert_id: str) -> bool:
        """
        解决告警

        Args:
            alert_id: 告警ID

        Returns:
            bool: 是否成功解决
        """
        for alert in self.alerts:
            if alert.alert_id == alert_id and alert.status == AlertStatus.ACTIVE:
                alert.resolve()
                self._update_alert_metrics(alert, None)
                logger.info(f"解决告警: {alert_id}")
                return True
        return False

    def get_active_alerts(self, level: Optional[AlertLevel] = None) -> List[Alert]:
        """
        获取活跃告警

        Args:
            level: 过滤告警级别

        Returns:
            List[Alert]: 活跃告警列表
        """
        active_alerts = [a for a in self.alerts if a.status == AlertStatus.ACTIVE]

        if level:
            active_alerts = [a for a in active_alerts if a.level == level]

        return sorted(active_alerts, key=lambda x: x.created_at, reverse=True)

    def get_alert_summary(self) -> Dict[str, Any]:
        """
        获取告警摘要

        Returns:
            Dict[str, Any]: 告警摘要
        """
        total_alerts = len(self.alerts)
        active_alerts = len([a for a in self.alerts if a.status == AlertStatus.ACTIVE])

        # 按级别统计
        by_level: Dict[str, int] = defaultdict(int)
        for alert in self.alerts:
            if alert.status == AlertStatus.ACTIVE:
                by_level[alert.level.value] += 1

        # 按来源统计
        by_source: Dict[str, int] = defaultdict(int)
        for alert in self.alerts:
            if alert.status == AlertStatus.ACTIVE:
                by_source[alert.source] += 1

        return {
            "total_alerts": total_alerts,
            "active_alerts": active_alerts,
            "resolved_alerts": len(
                [a for a in self.alerts if a.status == AlertStatus.RESOLVED]
            ),
            "by_level": dict(by_level),
            "by_source": dict(by_source),
            "critical_alerts": by_level.get("critical", 0),
            "rules_count": len(self.rules),
            "enabled_rules": len([r for r in self.rules.values() if r.enabled]),
            "summary_time": datetime.now().isoformat(),
        }

    def update_quality_metrics(self, quality_data: Dict[str, Any]) -> None:
        """
        更新数据质量指标

        Args:
            quality_data: 质量数据
        """
        freshness_data = quality_data.get("freshness", {})
        for table_name, result in freshness_data.items():
            if isinstance(result, dict) and "hours_since_last_update" in result:
                hours = result["hours_since_last_update"]
                self.metrics.data_freshness_hours.labels(table_name=table_name).set(
                    hours
                )

        completeness_data = quality_data.get("completeness", {})
        for table_name, result in completeness_data.items():
            if isinstance(result, dict) and "completeness_ratio" in result:
                ratio = result["completeness_ratio"]
                self.metrics.data_completeness_ratio.labels(table_name=table_name).set(
                    ratio
                )

        if "overall_score" in quality_data:
            score = quality_data["overall_score"]
            # 为每个表设置总分
            for table_name in freshness_data.keys():
                self.metrics.data_quality_score.labels(table_name=table_name).set(score)

    def update_anomaly_metrics(self, anomalies: List[Any]) -> None:
        """
        更新异常检测指标

        Args:
            anomalies: 异常列表
        """
        for anomaly in anomalies:
            # 更新异常计数
            self.metrics.anomalies_detected_total.labels(
                table_name=anomaly.table_name,
                column_name=anomaly.column_name,
                anomaly_type=anomaly.anomaly_type.value,
                severity=anomaly.severity.value,
            ).inc()

            # 更新异常得分
            self.metrics.anomaly_score.labels(
                table_name=anomaly.table_name, column_name=anomaly.column_name
            ).set(anomaly.anomaly_score)

    def check_and_fire_quality_alerts(
        self, quality_data: Dict[str, Any]
    ) -> List[Alert]:
        """
        检查数据质量并触发告警

        Args:
            quality_data: 质量数据

        Returns:
            List[Alert]: 触发的告警列表
        """
        fired_alerts = []

        # 检查新鲜度告警
        freshness_data = quality_data.get("freshness", {})
        for table_name, result in freshness_data.items():
            if isinstance(result, dict) and "hours_since_last_update" in result:
                hours = result["hours_since_last_update"]

                if hours > 24:
                    alert = self.fire_alert(
                        title=f"数据新鲜度严重告警 - {table_name}",
                        message=f"表 {table_name} 数据已经 {hours:.1f} 小时未更新",
                        level=AlertLevel.CRITICAL,
                        source="quality_monitor",
                        labels={"table": table_name, "metric": "freshness"},
                        rule_id="data_freshness_critical",
                    )
                    if alert:
                        fired_alerts.append(alert)
                elif hours > 12:
                    alert = self.fire_alert(
                        title=f"数据新鲜度警告 - {table_name}",
                        message=f"表 {table_name} 数据已经 {hours:.1f} 小时未更新",
                        level=AlertLevel.WARNING,
                        source="quality_monitor",
                        labels={"table": table_name, "metric": "freshness"},
                        rule_id="data_freshness_warning",
                    )
                    if alert:
                        fired_alerts.append(alert)

        # 检查完整性告警
        completeness_data = quality_data.get("completeness", {})
        for table_name, result in completeness_data.items():
            if isinstance(result, dict) and "completeness_ratio" in result:
                ratio = result["completeness_ratio"]

                if ratio < 0.8:
                    alert = self.fire_alert(
                        title=f"数据完整性严重告警 - {table_name}",
                        message=f"表 {table_name} 数据完整性仅为 {ratio:.1%}",
                        level=AlertLevel.CRITICAL,
                        source="quality_monitor",
                        labels={"table": table_name, "metric": "completeness"},
                        rule_id="data_completeness_critical",
                    )
                    if alert:
                        fired_alerts.append(alert)
                elif ratio < 0.95:
                    alert = self.fire_alert(
                        title=f"数据完整性警告 - {table_name}",
                        message=f"表 {table_name} 数据完整性为 {ratio:.1%}",
                        level=AlertLevel.WARNING,
                        source="quality_monitor",
                        labels={"table": table_name, "metric": "completeness"},
                        rule_id="data_completeness_warning",
                    )
                    if alert:
                        fired_alerts.append(alert)

        # 检查质量得分告警
        if "overall_score" in quality_data:
            score = quality_data["overall_score"]
            if score < 0.7:
                alert = self.fire_alert(
                    title="数据质量严重告警",
                    message=f"整体数据质量得分为 {score:.1%}，低于阈值",
                    level=AlertLevel.CRITICAL,
                    source="quality_monitor",
                    labels={"metric": "quality_score"},
                    rule_id="data_quality_critical",
                )
                if alert:
                    fired_alerts.append(alert)

        return fired_alerts

    def check_and_fire_anomaly_alerts(self, anomalies: List[Any]) -> List[Alert]:
        """
        检查异常并触发告警

        Args:
            anomalies: 异常列表

        Returns:
            List[Alert]: 触发的告警列表
        """
        fired_alerts = []

        for anomaly in anomalies:
            if anomaly.anomaly_score > 0.2:
                alert = self.fire_alert(
                    title=f"数据异常严重告警 - {anomaly.table_name}.{anomaly.column_name}",
                    message=f"{anomaly.description} (得分: {anomaly.anomaly_score:.3f})",
                    level=AlertLevel.CRITICAL,
                    source="anomaly_detector",
                    labels={
                        "table": anomaly.table_name,
                        "column": anomaly.column_name,
                        "anomaly_type": anomaly.anomaly_type.value,
                    },
                    rule_id="anomaly_critical",
                )
                if alert:
                    fired_alerts.append(alert)
            elif anomaly.anomaly_score > 0.1:
                alert = self.fire_alert(
                    title=f"数据异常警告 - {anomaly.table_name}.{anomaly.column_name}",
                    message=f"{anomaly.description} (得分: {anomaly.anomaly_score:.3f})",
                    level=AlertLevel.WARNING,
                    source="anomaly_detector",
                    labels={
                        "table": anomaly.table_name,
                        "column": anomaly.column_name,
                        "anomaly_type": anomaly.anomaly_type.value,
                    },
                    rule_id="anomaly_warning",
                )
                if alert:
                    fired_alerts.append(alert)

        return fired_alerts
