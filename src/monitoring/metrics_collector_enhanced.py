"""
增强的指标收集器
Enhanced Metrics Collector

提供全面的业务和系统指标收集：
- 业务指标（预测数量、准确率等）
- 系统指标（延迟、吞吐量、错误率）
- 自定义指标和告警
- Prometheus集成

Provides comprehensive business and system metrics collection:
- Business metrics (prediction count, accuracy, etc.)
- System metrics (latency, throughput, error rate)
- Custom metrics and alerts
- Prometheus integration
"""

import time
from datetime import datetime, timedelta
from typing import Dict, Optional, Any
from dataclasses import dataclass, field
from collections import defaultdict, deque

from prometheus_client import Counter, Histogram, Gauge, CollectorRegistry, generate_latest
import asyncio
from src.core.logging_system import StructuredLogger, LogCategory

logger = StructuredLogger(__name__, LogCategory.PERFORMANCE)


@dataclass
class MetricPoint:
    """指标数据点"""
    name: str
    value: float
    labels: Dict[str, str] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=datetime.now)
    unit: str = ""


class MetricsAggregator:
    """指标聚合器"""

    def __init__(self, window_size: int = 60):
        self.window_size = window_size
        self.metrics: Dict[str, deque] = defaultdict(lambda: deque(maxlen=window_size))
        self.aggregates: Dict[str, Dict[str, float]] = {}

    def add_metric(self, metric: MetricPoint):
        """添加指标点"""
        key = self._make_key(metric.name, metric.labels)
        self.metrics[key].append(metric)

        # 更新聚合
        self._update_aggregates(key)

    def _make_key(self, name: str, labels: Dict[str, str]) -> str:
        """生成指标键"""
        if not labels:
            return name
        label_str = ",".join(f"{k}={v}" for k, v in sorted(labels.items()))
        return f"{name}[{label_str}]"

    def _update_aggregates(self, key: str):
        """更新聚合统计"""
        values = [m.value for m in self.metrics[key]]
        if values:
            self.aggregates[key] = {
                "count": len(values),
                "sum": sum(values),
                "avg": sum(values) / len(values),
                "min": min(values),
                "max": max(values),
                "last": values[-1],
            }

    def get_metric(self, name: str, labels: Dict[str, str] = None) -> Optional[Dict[str, float]]:
        """获取指标聚合"""
        key = self._make_key(name, labels or {})
        return self.aggregates.get(key)

    def get_all_metrics(self) -> Dict[str, Dict[str, Dict[str, float]]]:
        """获取所有指标"""
        result = {}
        for key, aggregates in self.aggregates.items():
            if "[" in key:
                name, label_str = key.split("[", 1)
                labels = {}
                for pair in label_str[:-1].split(","):
                    if "=" in pair:
                        k, v = pair.split("=", 1)
                        labels[k] = v
            else:
                name = key
                labels = {}

            if name not in result:
                result[name] = {}
            result[name][str(labels)] = aggregates

        return result


class EnhancedMetricsCollector:
    """增强的指标收集器"""

    def __init__(self, registry: Optional[CollectorRegistry] = None):
        self.registry = registry or CollectorRegistry()
        self.aggregator = MetricsAggregator(window_size=300)  # 5分钟窗口
        self.alert_thresholds: Dict[str, Dict[str, float]] = {}
        self.last_alerts: Dict[str, datetime] = {}

        # Prometheus指标定义
        self._init_prometheus_metrics()

        # 业务指标
        self.predictions_total = 0
        self.predictions_correct = 0
        self.predictions_verified = 0
        self.model_loads = 0

        # 性能指标
        self.request_durations = deque(maxlen=1000)
        self.error_counts = defaultdict(int)

        # 定期聚合任务
        self._aggregation_task: Optional[asyncio.Task] = None

    def _init_prometheus_metrics(self):
        """初始化Prometheus指标"""
        # 业务指标
        self.prediction_counter = Counter(
            'predictions_total',
            'Total number of predictions',
            ['model_version', 'result'],
            registry=self.registry
        )

        self.prediction_accuracy = Gauge(
            'prediction_accuracy',
            'Prediction accuracy rate',
            ['model_version', 'time_window'],
            registry=self.registry
        )

        self.model_load_counter = Counter(
            'model_loads_total',
            'Total number of model loads',
            ['model_name', 'status'],
            registry=self.registry
        )

        # 性能指标
        self.request_duration = Histogram(
            'request_duration_seconds',
            'Request duration in seconds',
            ['endpoint', 'method'],
            buckets=[0.001, 0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0],
            registry=self.registry
        )

        self.cache_hit_ratio = Gauge(
            'cache_hit_ratio',
            'Cache hit ratio',
            ['cache_type'],
            registry=self.registry
        )

        # 系统指标
        self.active_connections = Gauge(
            'active_connections',
            'Number of active connections',
            ['connection_type'],
            registry=self.registry
        )

        self.error_rate = Gauge(
            'error_rate',
            'Error rate',
            ['error_type'],
            registry=self.registry
        )

        # 资源指标
        self.memory_usage = Gauge(
            'memory_usage_bytes',
            'Memory usage in bytes',
            ['component'],
            registry=self.registry
        )

        self.cpu_usage = Gauge(
            'cpu_usage_percent',
            'CPU usage percentage',
            ['component'],
            registry=self.registry
        )

        # 自定义业务指标
        self.value_bets_counter = Counter(
            'value_bets_total',
            'Total number of value bets identified',
            ['confidence_level'],
            registry=self.registry
        )

        self.data_collection_counter = Counter(
            'data_collection_operations_total',
            'Total data collection operations',
            ['source', 'status'],
            registry=self.registry
        )

    def record_prediction(
        self,
        model_version: str,
        predicted_result: str,
        confidence: float,
        duration: float,
        success: bool = True
    ):
        """记录预测指标"""
        # 更新计数器
        self.prediction_counter.labels(
            model_version=model_version,
            result=predicted_result
        ).inc()

        self.predictions_total += 1

        # 记录延迟
        metric = MetricPoint(
            name="prediction_duration",
            value=duration,
            labels={"model_version": model_version},
            unit="seconds"
        )
        self.aggregator.add_metric(metric)

        # 记录到Prometheus
        self.request_duration.labels(
            endpoint="/predict",
            method="POST"
        ).observe(duration)

        # 检查告警
        self._check_prediction_alerts(duration, confidence)

    def record_prediction_verification(
        self,
        model_version: str,
        is_correct: bool,
        time_window: str = "1h"
    ):
        """记录预测验证指标"""
        self.predictions_verified += 1
        if is_correct:
            self.predictions_correct += 1

        # 计算准确率
        if self.predictions_verified > 0:
            accuracy = self.predictions_correct / self.predictions_verified
            self.prediction_accuracy.labels(
                model_version=model_version,
                time_window=time_window
            ).set(accuracy)

            # 记录到聚合器
            metric = MetricPoint(
                name="prediction_accuracy",
                value=accuracy,
                labels={"model_version": model_version, "window": time_window},
                unit="ratio"
            )
            self.aggregator.add_metric(metric)

    def record_cache_operation(
        self,
        cache_type: str,
        operation: str,
        hit: Optional[bool] = None,
        size: Optional[int] = None
    ):
        """记录缓存操作指标"""
        if hit is not None:
            # 更新缓存命中率
            # 这里需要维护运行时统计
            pass

        if size is not None:
            metric = MetricPoint(
                name="cache_size",
                value=size,
                labels={"type": cache_type},
                unit="items"
            )
            self.aggregator.add_metric(metric)

    def record_error(
        self,
        error_type: str,
        component: str,
        severity: str = "medium"
    ):
        """记录错误指标"""
        self.error_counts[f"{component}:{error_type}"] += 1

        # 更新Prometheus
        self.error_rate.labels(error_type=error_type).inc()

        # 记录到聚合器
        metric = MetricPoint(
            name="error_count",
            value=1,
            labels={
                "error_type": error_type,
                "component": component,
                "severity": severity
            }
        )
        self.aggregator.add_metric(metric)

        # 检查错误告警
        self._check_error_alerts(error_type, component)

    def record_model_load(
        self,
        model_name: str,
        model_version: str,
        success: bool,
        load_time: float
    ):
        """记录模型加载指标"""
        status = "success" if success else "failed"
        self.model_load_counter.labels(
            model_name=model_name,
            status=status
        ).inc()

        self.model_loads += 1

        # 记录加载时间
        metric = MetricPoint(
            name="model_load_time",
            value=load_time,
            labels={
                "model_name": model_name,
                "model_version": model_version,
                "status": status
            },
            unit="seconds"
        )
        self.aggregator.add_metric(metric)

    def record_data_collection(
        self,
        source: str,
        data_type: str,
        records: int,
        success: bool,
        duration: float
    ):
        """记录数据收集指标"""
        status = "success" if success else "failed"
        self.data_collection_counter.labels(
            source=source,
            status=status
        ).inc()

        # 记录吞吐量
        if duration > 0:
            throughput = records / duration
            metric = MetricPoint(
                name="data_collection_throughput",
                value=throughput,
                labels={
                    "source": source,
                    "data_type": data_type
                },
                unit="records/sec"
            )
            self.aggregator.add_metric(metric)

    def record_value_bet(
        self,
        bookmaker: str,
        confidence_level: str,
        expected_value: float
    ):
        """记录价值投注指标"""
        self.value_bets_counter.labels(
            confidence_level=confidence_level
        ).inc()

        metric = MetricPoint(
            name="value_bet_ev",
            value=expected_value,
            labels={
                "bookmaker": bookmaker,
                "confidence_level": confidence_level
            },
            unit="ratio"
        )
        self.aggregator.add_metric(metric)

    def update_system_metrics(self):
        """更新系统指标"""
        try:
            import psutil
            import os

            process = psutil.Process(os.getpid())

            # 内存使用
            memory_info = process.memory_info()
            self.memory_usage.labels(component="app").set(memory_info.rss)
            self.memory_usage.labels(component="vms").set(memory_info.vms)

            # CPU使用
            cpu_percent = process.cpu_percent(interval=1)
            self.cpu_usage.labels(component="app").set(cpu_percent)

            # 连接数（需要根据实际情况调整）
            # self.active_connections.labels(connection_type="database").set(db_pool.size())

        except Exception as e:
            logger.error(f"Failed to update system metrics: {e}")

    def _check_prediction_alerts(self, duration: float, confidence: float):
        """检查预测告警条件"""
        # 延迟告警
        if duration > 5.0:  # 超过5秒
            self._trigger_alert(
                "prediction_latency_high",
                f"Prediction latency high: {duration:.2f}s",
                severity="high"
            )

        # 低置信度告警
        if confidence < 0.5:
            self._trigger_alert(
                "prediction_confidence_low",
                f"Prediction confidence low: {confidence:.3f}",
                severity="medium"
            )

    def _check_error_alerts(self, error_type: str, component: str):
        """检查错误告警条件"""
        error_key = f"{component}:{error_type}"
        error_count = self.error_counts[error_key]

        # 错误率告警
        if error_count > 10:  # 1分钟内超过10次错误
            self._trigger_alert(
                "error_rate_high",
                f"High error rate in {component}: {error_count} errors",
                severity="high"
            )

    def _trigger_alert(self, alert_name: str, message: str, severity: str = "medium"):
        """触发告警"""
        now = datetime.now()
        last_alert = self.last_alerts.get(alert_name)

        # 避免重复告警（5分钟内）
        if last_alert and (now - last_alert) < timedelta(minutes=5):
            return

        self.last_alerts[alert_name] = now

        # 记录告警日志
        logger.warning(
            f"ALERT: {alert_name}",
            alert_name=alert_name,
            message=message,
            severity=severity,
            timestamp=now.isoformat()
        )

        # 这里可以添加更多告警渠道：
        # - Slack通知
        # - 邮件通知
        # - PagerDuty
        # - 钉钉/企业微信

    def get_metrics_summary(self) -> Dict[str, Any]:
        """获取指标摘要"""
        return {
            "business": {
                "predictions_total": self.predictions_total,
                "predictions_correct": self.predictions_correct,
                "predictions_verified": self.predictions_verified,
                "accuracy": (
                    self.predictions_correct / self.predictions_verified
                    if self.predictions_verified > 0 else 0
                ),
                "model_loads": self.model_loads,
            },
            "performance": {
                "avg_prediction_duration": (
                    sum(self.request_durations) / len(self.request_durations)
                    if self.request_durations else 0
                ),
                "error_counts": dict(self.error_counts),
            },
            "aggregates": self.aggregator.get_all_metrics(),
            "last_updated": datetime.now().isoformat(),
        }

    def get_prometheus_metrics(self) -> str:
        """获取Prometheus格式的指标"""
        return generate_latest(self.registry).decode('utf-8')

    async def start_aggregation_task(self, interval: int = 60):
        """启动定期聚合任务"""
        if self._aggregation_task:
            return

        async def aggregation_loop():
            while True:
                try:
                    # 更新系统指标
                    self.update_system_metrics()

                    # 清理过期的告警记录
                    now = datetime.now()
                    expired_alerts = [
                        k for k, v in self.last_alerts.items()
                        if (now - v) > timedelta(hours=1)
                    ]
                    for alert in expired_alerts:
                        del self.last_alerts[alert]

                    await asyncio.sleep(interval)
                except Exception as e:
                    logger.error(f"Aggregation task error: {e}")
                    await asyncio.sleep(5)

        self._aggregation_task = asyncio.create_task(aggregation_loop())

    async def stop_aggregation_task(self):
        """停止聚合任务"""
        if self._aggregation_task:
            self._aggregation_task.cancel()
            try:
                await self._aggregation_task
            except asyncio.CancelledError:
                pass
            self._aggregation_task = None


# 全局指标收集器实例
_metrics_collector: Optional[EnhancedMetricsCollector] = None


def get_metrics_collector() -> EnhancedMetricsCollector:
    """获取全局指标收集器"""
    global _metrics_collector
    if _metrics_collector is None:
        _metrics_collector = EnhancedMetricsCollector()
    return _metrics_collector


# 便捷装饰器
def track_prediction_performance(func):
    """跟踪预测性能的装饰器"""
    async def wrapper(*args, **kwargs):
        start_time = time.time()
        success = True
        try:
            result = await func(*args, **kwargs)
            return result
        except Exception:
            success = False
            raise
        finally:
            duration = time.time() - start_time
            collector = get_metrics_collector()
            # 从参数中提取信息
            model_version = kwargs.get("model_version", "unknown")
            predicted_result = getattr(result, "predicted_result", "unknown")
            confidence = getattr(result, "confidence_score", 0.0)

            collector.record_prediction(
                model_version=model_version,
                predicted_result=predicted_result,
                confidence=confidence,
                duration=duration,
                success=success
            )
    return wrapper


def track_cache_performance(func):
    """跟踪缓存性能的装饰器"""
    def wrapper(*args, **kwargs):
        start_time = time.time()
        hit = False
        try:
            result = func(*args, **kwargs)
            # 根据返回结果判断是否命中
            hit = result is not None
            return result
        finally:
            duration = time.time() - start_time
            collector = get_metrics_collector()
            cache_type = kwargs.get("cache_type", "default")
            collector.record_cache_operation(
                cache_type=cache_type,
                operation=func.__name__,
                hit=hit
            )
    return wrapper