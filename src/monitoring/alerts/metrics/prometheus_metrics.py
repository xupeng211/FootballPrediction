"""
Prometheus指标管理

管理告警相关的Prometheus指标。
"""





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

    def update_alert_metrics(self, alert: Alert, rule_id: Optional[str]) -> None:
        """
        更新告警指标

        Args:
            alert: 告警对象
            rule_id: 规则ID
        """
        # 增加告警计数
        self.alerts_fired_total.labels(
            level=alert.level.value,
            source=alert.source,
            rule_id=rule_id or "manual",
        ).inc()

        # 更新活跃告警计数
        self._update_active_alerts()

    def _update_active_alerts(self) -> None:
        """更新活跃告警指标（需要外部提供告警列表）"""
        # 这个方法需要访问当前的告警列表
        # 在实际使用中，会通过 AlertManager 提供
        pass

    def update_quality_metrics(self, quality_data: Dict) -> None:
        """
        更新数据质量指标

        Args:
            quality_data: 质量数据
        """
        table_name = quality_data.get("table_name", "unknown")

        # 更新数据新鲜度
        freshness_hours = quality_data.get("freshness_hours", 0)
        self.data_freshness_hours.labels(table_name=table_name).set(freshness_hours)

        # 更新数据完整性
        completeness_ratio = quality_data.get("completeness_ratio", 0)
        self.data_completeness_ratio.labels(table_name=table_name).set(completeness_ratio)

        # 更新质量评分
        quality_score = quality_data.get("quality_score", 0)
        self.data_quality_score.labels(table_name=table_name).set(quality_score)

    def update_anomaly_metrics(self, anomalies: list) -> None:
        """
        更新异常指标

        Args:
            anomalies: 异常列表
        """
        for anomaly in anomalies:
            self.anomalies_detected_total.labels(
                table_name=anomaly.table_name,
                column_name=anomaly.column_name,
                anomaly_type=anomaly.anomaly_type.value,
                severity="high" if anomaly.anomaly_score > 0.2 else "medium",
            ).inc()

            # 更新异常分数
            self.anomaly_score.labels(
                table_name=anomaly.table_name,
                column_name=anomaly.column_name,
            ).set(anomaly.anomaly_score)

    def record_check_duration(self, check_type: str, duration_seconds: float) -> None:
        """
        记录检查持续时间

        Args:
            check_type: 检查类型
            duration_seconds: 持续时间（秒）
        """
        self.monitoring_check_duration_seconds.labels(check_type=check_type).observe(duration_seconds)

    def record_error(self, error_type: str) -> None:
        """
        记录监控错误

        Args:
            error_type: 错误类型
        """
        self.monitoring_errors_total.labels(error_type=error_type).inc()

from prometheus_client import REGISTRY, Counter, Gauge, Histogram


