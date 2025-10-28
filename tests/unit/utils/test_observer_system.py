from unittest.mock import AsyncMock, MagicMock

"""
观察者系统单元测试
Observer System Unit Tests

测试观察者模式的核心功能。
Tests core functionality of the observer pattern.
"""

import asyncio
from datetime import datetime, timedelta

import pytest
import pytest_asyncio

from src.observers.base import ObservableEvent, ObservableEventType, Observer, Subject
from src.observers.manager import ObserverManager, get_observer_manager
from src.observers.observers import (
    AlertingObserver,
    LoggingObserver,
    MetricsObserver,
    PerformanceObserver,
)
from src.observers.subjects import (
    AlertSubject,
    CacheSubject,
    PredictionMetricsSubject,
    SystemMetricsSubject,
)


@pytest.mark.unit
class TestObserver(Observer):
    """测试用的观察者"""

    def __init__(self):
        super().__init__("TestObserver")
        self.handled_events = []

    async def update(self, event: ObservableEvent) -> None:
        """处理事件"""
        self.handled_events.append(event)

    def get_observed_event_types(self) -> list:
        """返回观察的事件类型"""
        return [ObservableEventType.METRIC_UPDATE, ObservableEventType.ERROR_OCCURRED]


@pytest_asyncio.fixture
async def observer_manager():
    """创建观察者管理器"""
    manager = ObserverManager()
    await manager.initialize()
    return manager


@pytest.fixture
def test_observer():
    """创建测试观察者"""
    return TestObserver()


@pytest.fixture
def metrics_observer():
    """创建指标观察者"""
    return MetricsObserver()


@pytest.fixture
def alerting_observer():
    """创建告警观察者"""
    return AlertingObserver()


@pytest.fixture
def system_subject():
    """创建系统指标被观察者"""
    return SystemMetricsSubject()


@pytest.fixture
def prediction_subject():
    """创建预测指标被观察者"""
    return PredictionMetricsSubject()


@pytest.mark.asyncio
async def test_observer_subscription(test_observer, system_subject):
    """测试观察者订阅"""
    # 订阅观察者
    await system_subject.attach(test_observer)
    assert system_subject.get_observers_count() == 1

    # 创建事件
    event = ObservableEvent(
        event_type=ObservableEventType.METRIC_UPDATE,
        source="test",
        _data={"metric_name": "cpu", "metric_value": 80},
    )

    # 通知观察者
    await system_subject.notify(event)

    # 等待处理
    await asyncio.sleep(0.1)

    # 验证事件被处理
    assert len(test_observer.handled_events) == 1
    assert (
        test_observer.handled_events[0].event_type == ObservableEventType.METRIC_UPDATE
    )


@pytest.mark.asyncio
async def test_observer_unsubscription(test_observer, system_subject):
    """测试取消订阅"""
    # 订阅
    await system_subject.attach(test_observer)
    assert system_subject.get_observers_count() == 1

    # 取消订阅
    await system_subject.detach(test_observer)
    assert system_subject.get_observers_count() == 0


@pytest.mark.asyncio
async def test_metrics_observer():
    """测试指标观察者"""
    observer = MetricsObserver(aggregation_window=60)

    # 创建指标更新事件
    event = ObservableEvent(
        event_type=ObservableEventType.METRIC_UPDATE,
        source="test",
        _data={
            "metric_name": "cpu_usage",
            "metric_value": 75.5,
            "metric_type": "gauge",
        },
    )

    # 处理事件
    await observer.update(event)

    # 获取指标
    metrics = observer.get_metrics()
    assert "gauges" in metrics
    assert metrics["gauges"]["cpu_usage"] == 75.5


@pytest.mark.asyncio
async def test_alerting_observer(alerting_observer):
    """测试告警观察者"""
    # 添加告警规则
    alerting_observer.add_alert_rule(
        name="high_error",
        condition=lambda e: (
            e.event_type == ObservableEventType.ERROR_OCCURRED
            and e.data.get("error_count", 0) > 5
        ),
        severity="warning",
        message_template="错误数量过高: {error_count}",
    )

    # 创建错误事件
    event = ObservableEvent(
        event_type=ObservableEventType.ERROR_OCCURRED,
        source="test",
        _data={"error_count": 10},
    )

    # 处理事件
    await alerting_observer.update(event)

    # 获取告警历史
    alerts = alerting_observer.get_alert_history()
    assert len(alerts) == 1
    assert alerts[0]["rule_name"] == "high_error"


@pytest.mark.asyncio
async def test_system_metrics_subject(system_subject, metrics_observer):
    """测试系统指标被观察者"""
    # 订阅观察者
    await system_subject.attach(metrics_observer)

    # 设置阈值
    system_subject.set_threshold("cpu_usage", warning=70, critical=90)

    # 设置指标值（超过警告阈值）
    system_subject.set_metric("cpu_usage", 85)

    # 等待异步处理
    await asyncio.sleep(0.1)

    # 验证指标被记录
    metrics = system_subject.get_metrics()
    assert metrics["cpu_usage"] == 85


@pytest.mark.asyncio
async def test_prediction_metrics_subject(prediction_subject):
    """测试预测指标被观察者"""
    # 记录预测
    await prediction_subject.record_prediction(
        strategy_name="test_strategy",
        response_time_ms=150,
        success=True,
        confidence=0.85,
    )

    # 获取指标
    metrics = prediction_subject.get_prediction_metrics()
    assert metrics["prediction_counts"]["test_strategy"] == 1
    assert metrics["prediction_counts"]["test_strategy_success"] == 1


@pytest.mark.asyncio
async def test_cache_subject():
    """测试缓存被观察者"""
    subject = CacheSubject()

    # 记录缓存命中和未命中
    await subject.record_cache_hit("test_cache", "key1")
    await subject.record_cache_hit("test_cache", "key2")
    await subject.record_cache_miss("test_cache", "key3")

    # 获取统计
    _stats = subject.get_cache_statistics()
    assert stats["stats"]["hits"] == 2
    assert stats["stats"]["misses"] == 1
    assert stats["overall_hit_rate"] == 2 / 3


@pytest.mark.asyncio
async def test_observer_manager(observer_manager):
    """测试观察者管理器"""
    # 验证观察者和被观察者已创建
    assert len(observer_manager._observers) > 0
    assert len(observer_manager._subjects) > 0

    # 验证特定观察者存在
    assert observer_manager.get_metrics_observer() is not None
    assert observer_manager.get_alerting_observer() is not None

    # 验证特定被观察者存在
    assert observer_manager.get_system_metrics_subject() is not None
    assert observer_manager.get_prediction_metrics_subject() is not None

    # 获取系统状态
    status = observer_manager.get_system_status()
    assert status["initialized"] is True
    assert "observers" in status
    assert "subjects" in status


@pytest.mark.asyncio
async def test_observer_manager_record_prediction(observer_manager):
    """测试通过管理器记录预测"""
    # 记录预测
    await observer_manager.record_prediction(
        strategy_name="test_strategy",
        response_time_ms=200,
        success=True,
        confidence=0.9,
    )

    # 获取指标
    metrics = observer_manager.get_all_metrics()
    assert "prediction_metrics" in metrics
    assert metrics["prediction_metrics"]["prediction_counts"]["test_strategy"] == 1


@pytest.mark.asyncio
async def test_observer_manager_trigger_alert(observer_manager):
    """测试通过管理器触发告警"""
    # 获取告警观察者
    alerting_observer = observer_manager.get_alerting_observer()
    initial_alerts = len(alerting_observer.get_alert_history())

    # 触发告警
    await observer_manager.trigger_alert(
        alert_type="test_alert",
        severity="warning",
        message="测试告警",
        source="test",
    )

    # 验证告警被触发
    alerts = alerting_observer.get_alert_history()
    assert len(alerts) == initial_alerts + 1


@pytest.mark.asyncio
async def test_observer_manager_cache_operations(observer_manager):
    """测试缓存操作"""
    # 记录缓存操作
    await observer_manager.record_cache_hit("test_cache", "key1")
    await observer_manager.record_cache_miss("test_cache", "key2")

    # 获取指标
    metrics = observer_manager.get_all_metrics()
    assert "cache_stats" in metrics
    assert metrics["cache_stats"]["stats"]["hits"] == 1
    assert metrics["cache_stats"]["stats"]["misses"] == 1


@pytest.mark.asyncio
async def test_event_filtering():
    """测试事件过滤"""
    observer = TestObserver()

    # 添加过滤器：只处理错误事件
    observer.add_filter(lambda e: e.event_type == ObservableEventType.ERROR_OCCURRED)

    # 创建不同类型的事件
    metric_event = ObservableEvent(
        event_type=ObservableEventType.METRIC_UPDATE,
        source="test",
    )
    error_event = ObservableEvent(
        event_type=ObservableEventType.ERROR_OCCURRED,
        source="test",
    )

    # 处理事件
    await observer.update(metric_event)
    await observer.update(error_event)

    # 验证只有错误事件被处理
    assert len(observer.handled_events) == 1
    assert observer.handled_events[0].event_type == ObservableEventType.ERROR_OCCURRED


@pytest.mark.asyncio
async def test_observer_enable_disable():
    """测试观察者启用/禁用"""
    observer = TestObserver()

    # 默认是启用的
    assert observer.is_enabled() is True

    # 禁用观察者
    observer.disable()
    assert observer.is_enabled() is False

    # 创建事件
    event = ObservableEvent(
        event_type=ObservableEventType.METRIC_UPDATE,
        source="test",
    )

    # 处理事件（应该被忽略）
    await observer.update(event)
    assert len(observer.handled_events) == 0

    # 重新启用
    observer.enable()
    await observer.update(event)
    assert len(observer.handled_events) == 1


def test_global_observer_manager():
    """测试全局观察者管理器"""
    # 获取全局实例
    manager1 = get_observer_manager()
    manager2 = get_observer_manager()

    # 应该是同一个实例
    assert manager1 is manager2


@pytest.mark.asyncio
async def test_performance_observer():
    """测试性能观察者"""
    observer = PerformanceObserver(window_size=10)

    # 记录多个预测完成事件
    for i in range(5):
        event = ObservableEvent(
            event_type=ObservableEventType.PREDICTION_COMPLETED,
            source="test",
            _data={"response_time_ms": 100 + i * 10},
        )
        await observer.update(event)

    # 获取性能指标
    metrics = observer.get_performance_metrics()
    assert "response_time" in metrics
    assert metrics["response_time"]["count"] == 5
    assert metrics["response_time"]["avg"] == 120  # (100+110+120+130+140)/5
