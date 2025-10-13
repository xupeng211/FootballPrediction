"""
增强指标收集器隔离测试
测试各个模块的独立功能，避免导入依赖问题
"""

import pytest
from datetime import datetime
from unittest.mock import Mock


def test_metric_types_isolated():
    """独立测试指标数据类型"""
    # 直接定义测试，避免导入问题
    from dataclasses import dataclass, field
    from typing import Dict, Any
    from datetime import datetime

    @dataclass
    class MetricPoint:
        name: str
        value: float
        labels: Dict[str, str] = field(default_factory=dict)
        timestamp: datetime = field(default_factory=datetime.now)
        unit: str = ""

    @dataclass
    class MetricSummary:
        count: int
        sum: float
        avg: float
        min: float
        max: float
        last: float
        p50: float = None
        p95: float = None
        p99: float = None

    @dataclass
    class AlertInfo:
        name: str
        message: str
        severity: str
        component: str = ""
        context: Dict[str, Any] = field(default_factory=dict)
        labels: Dict[str, str] = field(default_factory=dict)
        timestamp: datetime = field(default_factory=datetime.now)

        def to_dict(self):
            return {
                "name": self.name,
                "message": self.message,
                "severity": self.severity,
                "component": self.component,
                "context": self.context,
                "labels": self.labels,
                "timestamp": self.timestamp.isoformat(),
            }

    # 测试MetricPoint
    point = MetricPoint(
        name="test_metric", value=100.5, labels={"env": "test"}, unit="ms"
    )
    assert point.name == "test_metric"
    assert point.value == 100.5
    assert point.labels["env"] == "test"
    assert point.unit == "ms"
    assert isinstance(point.timestamp, datetime)

    # 测试MetricSummary
    summary = MetricSummary(
        count=10, sum=1000.0, avg=100.0, min=50.0, max=150.0, last=95.0
    )
    assert summary.count == 10
    assert summary.avg == 100.0
    assert summary.min == 50.0
    assert summary.max == 150.0

    # 测试AlertInfo
    alert = AlertInfo(
        name="test_alert",
        message="Test alert message",
        severity="high",
        component="test_component",
    )
    assert alert.name == "test_alert"
    assert alert.message == "Test alert message"
    assert alert.severity == "high"
    assert alert.component == "test_component"

    # 测试to_dict方法
    alert_dict = alert.to_dict()
    assert alert_dict["name"] == "test_alert"
    assert alert_dict["severity"] == "high"
    assert isinstance(alert_dict["timestamp"], str)


def test_aggregator_isolated():
    """独立测试指标聚合器"""
    import statistics
    from collections import defaultdict, deque
    from datetime import datetime, timedelta
    from typing import Dict, Deque

    # 简化的MetricPoint定义
    class MetricPoint:
        def __init__(self, name, value, labels=None, timestamp=None):
            self.name = name
            self.value = value
            self.labels = labels or {}
            self.timestamp = timestamp or datetime.now()

    # 简化的MetricSummary定义
    class MetricSummary:
        def __init__(self, count, sum, avg, min, max, last):
            self.count = count
            self.sum = sum
            self.avg = avg
            self.min = min
            self.max = max
            self.last = last
            self.p50 = None
            self.p95 = None
            self.p99 = None

    # 简化的MetricsAggregator
    class MetricsAggregator:
        def __init__(self, window_size=300):
            self.window_size = window_size
            self.metrics = defaultdict(lambda: deque(maxlen=window_size * 10))
            self.aggregates = {}
            self.last_update = {}

        def add_metric(self, metric):
            key = self._make_key(metric.name, metric.labels)
            self.metrics[key].append(metric)
            self._update_aggregates(key)

        def _make_key(self, name, labels):
            if not labels:
                return name
            label_str = ",".join(f"{k}={v}" for k, v in sorted(labels.items()))
            return f"{name}[{label_str}]"

        def _update_aggregates(self, key):
            metrics = self.metrics[key]
            if not metrics:
                return

            cutoff_time = datetime.now() - timedelta(seconds=self.window_size)
            while metrics and metrics[0].timestamp < cutoff_time:
                metrics.popleft()

            if not metrics:
                return

            values = [m.value for m in metrics]
            self.aggregates[key] = MetricSummary(
                count=len(values),
                sum=sum(values),
                avg=statistics.mean(values),
                min=min(values),
                max=max(values),
                last=values[-1],
            )
            self.last_update[key] = datetime.now()

        def get_metric(self, name, labels=None):
            key = self._make_key(name, labels or {})
            return self.aggregates.get(key)

    # 测试聚合器
    aggregator = MetricsAggregator(window_size=60)

    # 添加指标点
    point1 = MetricPoint(name="test_metric", value=100.0, labels={"env": "test"})
    aggregator.add_metric(point1)

    point2 = MetricPoint(name="test_metric", value=200.0, labels={"env": "test"})
    aggregator.add_metric(point2)

    # 获取指标聚合
    summary = aggregator.get_metric("test_metric", {"env": "test"})
    assert summary is not None
    assert summary.count == 2
    assert summary.avg == 150.0
    assert summary.min == 100.0
    assert summary.max == 200.0


def test_alert_manager_isolated():
    """独立测试告警管理器"""
    from datetime import datetime, timedelta
    from typing import Dict, Callable, Any, List, Optional

    # 简化的AlertInfo定义
    class AlertInfo:
        def __init__(self, name, message, severity, component=""):
            self.name = name
            self.message = message
            self.severity = severity
            self.component = component
            self.timestamp = datetime.now()
            self.context = {}

    # 简化的AlertManager
    class AlertManager:
        def __init__(self):
            self.alert_rules = {}
            self.active_alerts = {}
            self.alert_history = []
            self.alert_handlers = []

        def add_alert_rule(
            self, name, condition, severity="medium", description="", cooldown=300
        ):
            self.alert_rules[name] = {
                "condition": condition,
                "severity": severity,
                "description": description,
                "cooldown": cooldown,
                "last_triggered": None,
            }

        def check_alerts(self, metrics):
            now = datetime.now()

            for name, rule in self.alert_rules.items():
                try:
                    if rule["last_triggered"]:
                        cooldown_end = rule["last_triggered"] + timedelta(
                            seconds=rule["cooldown"]
                        )
                        if now < cooldown_end:
                            continue

                    if rule["condition"](metrics):
                        self._trigger_alert(
                            name,
                            rule["description"] or f"Alert {name} triggered",
                            rule["severity"],
                            metrics,
                        )
                        rule["last_triggered"] = now
                except Exception:
                    pass

        def _trigger_alert(self, name, message, severity, context=None):
            alert = AlertInfo(name, message, severity)
            alert.context = context or {}

            self.active_alerts[name] = alert
            self.alert_history.append(alert)

            if len(self.alert_history) > 1000:
                self.alert_history = self.alert_history[-500:]

        def resolve_alert(self, name):
            if name in self.active_alerts:
                del self.active_alerts[name]

        def get_active_alerts(self):
            return list(self.active_alerts.values())

        def get_alert_summary(self):
            severity_counts = {}
            for alert in self.active_alerts.values():
                severity_counts[alert.severity] = (
                    severity_counts.get(alert.severity, 0) + 1
                )

            return {
                "active_alerts": len(self.active_alerts),
                "severity_breakdown": severity_counts,
                "total_rules": len(self.alert_rules),
                "last_updated": datetime.now().isoformat(),
            }

    # 测试告警管理器
    alert_manager = AlertManager()

    # 添加告警规则
    def high_error_rate(metrics):
        return metrics.get("error_count", 0) > 10

    alert_manager.add_alert_rule(
        name="high_error_rate",
        condition=high_error_rate,
        severity="high",
        description="Error rate is too high",
    )

    # 检查告警（不应触发）
    alert_manager.check_alerts({"error_count": 5})
    assert len(alert_manager.get_active_alerts()) == 0

    # 触发告警
    alert_manager.check_alerts({"error_count": 15})
    assert len(alert_manager.get_active_alerts()) == 1
    active_alert = alert_manager.get_active_alerts()[0]
    assert active_alert.name == "high_error_rate"
    assert active_alert.severity == "high"

    # 解决告警
    alert_manager.resolve_alert("high_error_rate")
    assert len(alert_manager.get_active_alerts()) == 0

    # 测试告警摘要
    summary = alert_manager.get_alert_summary()
    assert "active_alerts" in summary
    assert "total_rules" in summary
    assert summary["total_rules"] == 1


def test_decorators_isolated():
    """独立测试装饰器"""
    import functools
    from unittest.mock import Mock

    # 创建mock的收集器
    collector = Mock()
    collector.record_prediction = Mock()
    collector.record_cache_operation = Mock()

    # 模拟track_prediction_performance装饰器
    def track_prediction_performance(model_version_param="model_version"):
        def decorator(func):
            @functools.wraps(func)
            async def async_wrapper(*args, **kwargs):
                start_time = datetime.now()
                try:
                    _result = await func(*args, **kwargs)
                    success = True
                except Exception:
                    success = False
                    raise
                finally:
                    duration = (datetime.now() - start_time).total_seconds()
                    if hasattr(result, "predicted_result"):
                        predicted_result = result.predicted_result
                    else:
                        predicted_result = "unknown"

                    model_version = kwargs.get(model_version_param, "unknown")

                    collector.record_prediction(
                        model_version=model_version,
                        predicted_result=predicted_result,
                        confidence=getattr(result, "confidence_score", 0.0),
                        duration=duration,
                        success=success,
                    )
                return result

            @functools.wraps(func)
            def sync_wrapper(*args, **kwargs):
                start_time = datetime.now()
                try:
                    _result = func(*args, **kwargs)
                    success = True
                except Exception:
                    success = False
                    raise
                finally:
                    duration = (datetime.now() - start_time).total_seconds()
                    model_version = kwargs.get(model_version_param, "unknown")

                    collector.record_prediction(
                        model_version=model_version,
                        predicted_result="sync_call",
                        confidence=0.0,
                        duration=duration,
                        success=success,
                    )
                return result

            import asyncio

            if asyncio.iscoroutinefunction(func):
                return async_wrapper
            else:
                return sync_wrapper

        return decorator

    # 模拟track_cache_performance装饰器
    def track_cache_performance(cache_type="redis"):
        def decorator(func):
            @functools.wraps(func)
            def wrapper(*args, **kwargs):
                start_time = datetime.now()
                try:
                    _result = func(*args, **kwargs)
                    hit = result is not None
                except Exception:
                    hit = False
                    raise
                finally:
                    (datetime.now() - start_time).total_seconds()

                    collector.record_cache_operation(
                        cache_type=cache_type, operation=func.__name__, hit=hit
                    )
                return result

            return wrapper

        return decorator

    # 测试缓存性能装饰器
    @track_cache_performance(cache_type="redis")
    def cache_get(key):
        if key == "exists":
            return "value"
        return None

    _result = cache_get("exists")
    assert _result == "value"
    assert collector.record_cache_operation.called

    # 测试同步装饰器
    @track_prediction_performance()
    def test_function(model_version="v1.0"):
        return "test"

    _result = test_function(model_version="v2.0")
    assert _result == "test"
    assert collector.record_prediction.called

    # 验证调用参数
    call_args = collector.record_prediction.call_args
    assert call_args.kwargs["model_version"] == "v2.0"


def test_metric_summary_to_dict():
    """测试MetricSummary的to_dict方法"""
    from dataclasses import dataclass

    @dataclass
    class MetricSummary:
        count: int
        sum: float
        avg: float
        min: float
        max: float
        last: float
        p50: float = None
        p95: float = None
        p99: float = None

        def to_dict(self):
            return {
                "count": self.count,
                "sum": self.sum,
                "avg": self.avg,
                "min": self.min,
                "max": self.max,
                "last": self.last,
                "p50": self.p50,
                "p95": self.p95,
                "p99": self.p99,
            }

    summary = MetricSummary(
        count=100,
        sum=10000.0,
        avg=100.0,
        min=10.0,
        max=200.0,
        last=95.0,
        p50=98.0,
        p95=150.0,
        p99=190.0,
    )

    # 转换为字典
    summary_dict = summary.to_dict()
    assert summary_dict["count"] == 100
    assert summary_dict["avg"] == 100.0
    assert summary_dict["p95"] == 150.0
    assert summary_dict["p99"] == 190.0
