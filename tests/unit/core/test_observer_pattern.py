"""
观察者模式单元测试
Unit Tests for Observer Pattern

测试观察者模式的核心功能，包括观察者、被观察者、管理器的完整业务逻辑。
Tests core functionality of the observer pattern including observers, subjects, and manager.
"""

import asyncio
from datetime import datetime, timedelta
from typing import Any, Dict, List
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.observers.base import (
    CompositeObserver,
    ObservableEvent,
    ObservableEventType,
    Observer,
    Subject,
)
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


@pytest.fixture
def sample_events():
    """创建各种类型的示例事件"""
    return {
        "metric": ObservableEvent(
            event_type=ObservableEventType.METRIC_UPDATE,
            source="test_source",
            severity="info",
            data={"metric_name": "cpu_usage", "metric_value": 75.5},
        ),
        "error": ObservableEvent(
            event_type=ObservableEventType.ERROR_OCCURRED,
            source="test_service",
            severity="error",
            data={"error_message": "Test error", "error_count": 1},
        ),
        "prediction": ObservableEvent(
            event_type=ObservableEventType.PREDICTION_COMPLETED,
            data={"response_time_ms": 150.0, "confidence": 0.85},
        ),
        "cache_hit": ObservableEvent(
            event_type=ObservableEventType.CACHE_HIT,
            data={"cache_key": "test_key"},
        ),
        "cache_miss": ObservableEvent(
            event_type=ObservableEventType.CACHE_MISS,
            data={"cache_key": "test_key"},
        ),
    }


# ==================== 基础类测试 ====================


@pytest.mark.unit
class TestObserver:
    """测试观察者基类核心功能"""

    class ConcreteObserver(Observer):
        def __init__(self, name: str = "TestObserver"):
            super().__init__(name)
            self.events: List[ObservableEvent] = []

        async def update(self, event: ObservableEvent) -> None:
            self.events.append(event)

        def get_observed_event_types(self) -> List[ObservableEventType]:
            return [
                ObservableEventType.METRIC_UPDATE,
                ObservableEventType.ERROR_OCCURRED,
            ]

    @pytest.fixture
    def observer(self):
        return self.ConcreteObserver()

    def test_observer_lifecycle(self, observer):
        """测试观察者生命周期"""
        # 初始状态
        assert observer.name == "TestObserver"
        assert observer.is_enabled() is True
        assert len(observer._subscription_filters) == 0

        # 禁用/启用
        observer.disable()
        assert observer.is_enabled() is False
        observer.enable()
        assert observer.is_enabled() is True

    def test_event_filtering(self, observer):
        """测试事件过滤机制"""

        def filter_func(event):
            return event.data.get("metric_value", 0) > 50

        observer.add_filter(filter_func)

        # 符合条件的事件
        event1 = ObservableEvent(
            event_type=ObservableEventType.METRIC_UPDATE,
            data={"metric_value": 75},
        )
        assert observer.should_handle_event(event1) is True

        # 不符合条件的事件
        event2 = ObservableEvent(
            event_type=ObservableEventType.METRIC_UPDATE,
            data={"metric_value": 25},
        )
        assert observer.should_handle_event(event2) is False

    @pytest.mark.asyncio
    async def test_observer_update_and_stats(self, observer, sample_events):
        """测试观察者更新和统计信息"""
        await observer.update(sample_events["metric"])

        # 验证事件接收
        assert len(observer.events) == 1
        assert observer.events[0] == sample_events["metric"]

        # 验证统计信息
        stats = observer.get_stats()
        assert stats["name"] == "TestObserver"
        assert stats["enabled"] is True
        assert stats["filters_count"] == 0


@pytest.mark.unit
class TestSubject:
    """测试被观察者基类核心功能"""

    class ConcreteSubject(Subject):
        def __init__(self, name: str = "TestSubject"):
            super().__init__(name)

    @pytest.fixture
    def subject(self):
        return self.ConcreteSubject()

    @pytest.fixture
    def observer(self):
        class TestObserver(Observer):
            def __init__(self):
                super().__init__("TestObserver")
                self.events: List[ObservableEvent] = []

            async def update(self, event: ObservableEvent) -> None:
                self.events.append(event)

            def get_observed_event_types(self) -> List[ObservableEventType]:
                return list(ObservableEventType)

        return TestObserver()

    @pytest.mark.asyncio
    async def test_observer_attachment_and_notification(
        self, subject, observer, sample_events
    ):
        """测试观察者附加和事件通知"""
        # 附加观察者
        await subject.attach(observer)
        assert subject.get_observers_count() == 1
        assert observer in subject.get_observers()

        # 发送通知
        await subject.notify(sample_events["metric"])
        await asyncio.sleep(0.01)  # 等待异步处理

        # 验证观察者收到事件
        assert len(observer.events) == 1
        assert observer.events[0] == sample_events["metric"]

        # 验证事件历史记录
        history = subject.get_event_history()
        assert len(history) == 1
        assert history[0] == sample_events["metric"]

        # 分离观察者
        await subject.detach(observer)
        assert subject.get_observers_count() == 0

    def test_event_history_filtering(self, subject, sample_events):
        """测试事件历史过滤功能"""
        event1 = sample_events["metric"]
        event2 = sample_events["error"]

        subject._record_event(event1)
        subject._record_event(event2)

        # 按类型过滤
        metric_events = subject.get_event_history(
            event_type=ObservableEventType.METRIC_UPDATE
        )
        assert len(metric_events) == 1
        assert metric_events[0].event_type == ObservableEventType.METRIC_UPDATE

        # 按来源手动过滤
        source_events = [
            e for e in subject.get_event_history() if e.source == "test_source"
        ]
        assert len(source_events) == 1

    def test_subject_lifecycle_and_stats(self, subject):
        """测试被观察者生命周期和统计"""
        # 初始状态
        assert subject.is_enabled() is True

        # 启用/禁用
        subject.disable()
        assert subject.is_enabled() is False
        subject.enable()
        assert subject.is_enabled() is True

        # 统计信息
        stats = subject.get_stats()
        assert stats["name"] == "TestSubject"
        assert stats["observers_count"] == 0
        assert stats["events_count"] == 0
        assert stats["enabled"] is True


@pytest.mark.unit
class TestCompositeObserver:
    """测试组合观察者功能"""

    @pytest.fixture
    def observers(self):
        class MockObserver(Observer):
            def __init__(self, name):
                super().__init__(name)
                self.events = []

            async def update(self, event):
                self.events.append(event)

            def get_observed_event_types(self):
                return [ObservableEventType.METRIC_UPDATE]

        return [MockObserver("obs1"), MockObserver("obs2")]

    @pytest.fixture
    def composite(self, observers):
        composite = CompositeObserver("Composite", observers)
        return composite

    @pytest.mark.asyncio
    async def test_composite_observer_notification(
        self, composite, observers, sample_events
    ):
        """测试组合观察者通知所有子观察者"""
        await composite.update(sample_events["metric"])

        # 验证所有子观察者都收到事件
        for observer in observers:
            assert len(observer.events) == 1
            assert observer.events[0] == sample_events["metric"]

    def test_composite_observer_event_types(self, composite):
        """测试组合观察者合并事件类型"""
        event_types = composite.get_observed_event_types()
        assert ObservableEventType.METRIC_UPDATE in event_types


# ==================== 具体观察者测试 ====================


@pytest.mark.unit
class TestMetricsObserver:
    """测试指标观察者核心功能"""

    @pytest.fixture
    def observer(self):
        return MetricsObserver(aggregation_window=60)

    @pytest.mark.asyncio
    async def test_metrics_collection(self, observer, sample_events):
        """测试指标收集功能"""
        # 测试指标更新
        await observer.update(sample_events["metric"])
        metrics = observer.get_metrics()
        assert "cpu_usage" in metrics["gauges"]
        assert metrics["gauges"]["cpu_usage"] == 75.5

        # 测试预测完成计数
        await observer.update(sample_events["prediction"])
        metrics = observer.get_metrics()
        assert metrics["counters"]["predictions_completed"] == 1

    @pytest.mark.asyncio
    async def test_cache_metrics_tracking(self, observer, sample_events):
        """测试缓存指标跟踪"""
        await observer.update(sample_events["cache_hit"])
        await observer.update(sample_events["cache_miss"])

        metrics = observer.get_metrics()
        assert metrics["counters"]["cache_hits"] == 1
        assert metrics["counters"]["cache_misses"] == 1

    def test_observed_event_types(self, observer):
        """测试支持的事件类型"""
        event_types = observer.get_observed_event_types()
        expected_types = [
            ObservableEventType.METRIC_UPDATE,
            ObservableEventType.PREDICTION_COMPLETED,
            ObservableEventType.CACHE_HIT,
            ObservableEventType.CACHE_MISS,
        ]
        for event_type in expected_types:
            assert event_type in event_types


@pytest.mark.unit
class TestLoggingObserver:
    """测试日志观察者功能"""

    @pytest.fixture
    def observer(self):
        return LoggingObserver()

    @pytest.mark.asyncio
    @patch("logging.Logger.info")
    @patch("logging.Logger.warning")
    @patch("logging.Logger.error")
    async def test_severity_based_logging(
        self, mock_error, mock_warning, mock_info, observer, sample_events
    ):
        """测试基于严重性的日志记录"""
        # Info 事件
        info_event = ObservableEvent(
            event_type=ObservableEventType.METRIC_UPDATE,
            severity="info",
            data={"message": "Test info"},
        )
        await observer.update(info_event)
        mock_info.assert_called_once()

        # Warning 事件
        warning_event = ObservableEvent(
            event_type=ObservableEventType.THRESHOLD_EXCEEDED,
            severity="warning",
            data={"message": "Test warning"},
        )
        await observer.update(warning_event)
        mock_warning.assert_called_once()

        # Error 事件
        await observer.update(sample_events["error"])
        mock_error.assert_called_once()

    def test_log_statistics(self, observer):
        """测试日志统计功能"""
        counts = observer.get_log_counts()
        assert isinstance(counts, dict)


@pytest.mark.unit
class TestAlertingObserver:
    """测试告警观察者功能"""

    @pytest.fixture
    def observer(self):
        return AlertingObserver()

    def test_alert_rule_management(self, observer):
        """测试告警规则管理"""

        def condition(event):
            return event.data.get("metric_value", 0) > 80

        observer.add_alert_rule(
            name="high_cpu",
            condition=condition,
            severity="warning",
            message_template="CPU usage is high: {metric_value}%",
        )

        rules = observer.get_alert_rules()
        assert "high_cpu" in rules
        assert rules["high_cpu"]["severity"] == "warning"

    @pytest.mark.asyncio
    async def test_alert_triggering(self, observer):
        """测试告警触发机制"""

        # 添加告警规则
        def condition(event):
            return (
                event.event_type == ObservableEventType.THRESHOLD_EXCEEDED
                and event.data.get("metric_name") == "cpu_usage"
                and event.data.get("metric_value", 0) > 80
            )

        observer.add_alert_rule(
            name="high_cpu",
            condition=condition,
            severity="warning",
            message_template="CPU usage is high: {metric_value}%",
        )

        # 触发告警
        event = ObservableEvent(
            event_type=ObservableEventType.THRESHOLD_EXCEEDED,
            data={"metric_name": "cpu_usage", "metric_value": 85.0},
        )
        await observer.update(event)

        # 验证告警历史
        alerts = observer.get_alert_history()
        assert len(alerts) > 0
        assert alerts[0]["rule_name"] == "high_cpu"
        assert "85.0" in alerts[0]["message"]

    def test_alert_cooldown_mechanism(self, observer):
        """测试告警冷却机制"""

        def condition(event):
            return True

        observer.add_alert_rule(
            name="test_alert",
            condition=condition,
            severity="info",
            cooldown_minutes=1,
        )

        # 验证冷却时间设置
        assert "test_alert" not in observer._alert_cooldown


@pytest.mark.unit
class TestPerformanceObserver:
    """测试性能观察者功能"""

    @pytest.fixture
    def observer(self):
        return PerformanceObserver(window_size=100)

    @pytest.mark.asyncio
    async def test_performance_metrics_collection(self, observer, sample_events):
        """测试性能指标收集"""
        # 测试预测完成指标
        await observer.update(sample_events["prediction"])
        metrics = observer.get_performance_metrics()
        assert "throughput" in metrics
        assert metrics["throughput"]["total_requests"] == 1

        # 测试错误率统计
        await observer.update(sample_events["error"])
        metrics = observer.get_performance_metrics()
        assert "error_rates" in metrics
        assert "test_service" in metrics["error_rates"]

    def test_performance_metrics_structure(self, observer):
        """测试性能指标结构"""
        metrics = observer.get_performance_metrics()
        assert "throughput" in metrics
        assert "error_rates" in metrics


# ==================== 具体被观察者测试 ====================


@pytest.mark.unit
class TestSystemMetricsSubject:
    """测试系统指标被观察者"""

    @pytest.fixture
    def subject(self):
        return SystemMetricsSubject()

    @pytest.mark.asyncio
    async def test_metric_setting_and_threshold_checking(self, subject):
        """测试指标设置和阈值检查"""
        # 设置阈值
        subject.set_threshold(
            "cpu_usage", warning=70.0, critical=90.0, direction="above"
        )

        # 创建模拟观察者
        observer = AsyncMock()
        await subject.attach(observer)

        # 设置超过警告阈值的指标
        subject.set_metric("cpu_usage", 85.0)
        await asyncio.sleep(0.01)

        # 验证阈值检查触发通知
        if observer.update.called:
            event = observer.update.call_args[0][0]
            assert event.event_type == ObservableEventType.THRESHOLD_EXCEEDED
            assert event.severity == "warning"

    def test_threshold_configuration(self, subject):
        """测试阈值配置"""
        subject.set_threshold(
            "memory_usage", warning=80.0, critical=95.0, direction="above"
        )

        assert "memory_usage" in subject._thresholds
        assert subject._thresholds["memory_usage"]["warning"] == 80.0
        assert subject._thresholds["memory_usage"]["critical"] == 95.0

    @pytest.mark.asyncio
    async def test_metrics_collection(self, subject):
        """测试指标收集"""
        with patch.object(subject, "set_metric") as mock_set:
            await subject.collect_metrics()
            assert mock_set.call_count >= 1


@pytest.mark.unit
class TestPredictionMetricsSubject:
    """测试预测指标被观察者"""

    @pytest.fixture
    def subject(self):
        return PredictionMetricsSubject()

    @pytest.mark.asyncio
    async def test_prediction_recording(self, subject):
        """测试预测记录功能"""
        await subject.record_prediction(
            strategy_name="ml_model",
            response_time_ms=150.0,
            success=True,
            confidence=0.85,
        )

        metrics = subject.get_prediction_metrics()
        assert metrics["prediction_counts"]["ml_model"] == 1
        assert metrics["prediction_counts"]["ml_model_success"] == 1
        assert "response_time" in metrics
        assert "avg" in metrics["response_time"]

    @pytest.mark.asyncio
    async def test_performance_degradation_detection(self, subject):
        """测试性能下降检测"""
        # 添加慢响应时间记录
        for _ in range(100):
            await subject.record_prediction(
                strategy_name="slow_model",
                response_time_ms=1500.0,  # 超过1秒阈值
                success=True,
            )

        # 创建观察者
        observer = AsyncMock()
        await subject.attach(observer)

        # 检查性能下降
        await subject.check_performance_degradation()

        # 验证可能触发的性能下降事件
        if observer.update.called:
            event = observer.update.call_args[0][0]
            assert event.event_type == ObservableEventType.PERFORMANCE_DEGRADATION


@pytest.mark.unit
class TestAlertSubject:
    """测试告警被观察者"""

    @pytest.fixture
    def subject(self):
        return AlertSubject()

    @pytest.mark.asyncio
    async def test_alert_triggering(self, subject):
        """测试告警触发"""
        observer = AsyncMock()
        await subject.attach(observer)

        await subject.trigger_alert(
            alert_type="test_alert",
            severity="warning",
            message="Test alert message",
            source="test_source",
            data={"key": "value"},
        )

        assert observer.update.called
        event = observer.update.call_args[0][0]
        assert event.event_type == ObservableEventType.SYSTEM_ALERT
        assert event.severity == "warning"
        assert event.data["alert_type"] == "test_alert"

    def test_suppression_rule_management(self, subject):
        """测试抑制规则管理"""
        subject.add_suppression_rule(
            alert_type="test_alert",
            severity="warning",
            max_alerts=3,
            time_window=300,
        )

        stats = subject.get_alert_statistics()
        assert stats["suppression_rules"] == 1


@pytest.mark.unit
class TestCacheSubject:
    """测试缓存被观察者"""

    @pytest.fixture
    def subject(self):
        return CacheSubject()

    @pytest.mark.asyncio
    async def test_cache_operations_tracking(self, subject):
        """测试缓存操作跟踪"""
        # 记录各种缓存操作
        await subject.record_cache_hit("test_cache", "key1")
        await subject.record_cache_hit("test_cache", "key2")
        await subject.record_cache_miss("test_cache", "key3")
        await subject.record_cache_set("test_cache", "key4", ttl=300)
        await subject.record_cache_delete("test_cache", "key5")

        stats = subject.get_cache_statistics()
        assert stats["stats"]["hits"] == 2
        assert stats["stats"]["misses"] == 1
        assert stats["stats"]["sets"] == 1
        assert stats["stats"]["deletes"] == 1
        assert stats["total_requests"] == 3
        assert stats["overall_hit_rate"] == 2 / 3


# ==================== 观察者管理器测试 ====================


@pytest.mark.unit
class TestObserverManager:
    """测试观察者管理器核心功能"""

    @pytest.fixture
    def manager(self):
        return ObserverManager()

    @pytest.mark.asyncio
    async def test_manager_initialization(self, manager):
        """测试管理器初始化"""
        await manager.initialize()

        # 验证观察者创建
        assert len(manager._observers) == 4
        assert "metrics" in manager._observers
        assert "logging" in manager._observers
        assert "alerting" in manager._observers
        assert "performance" in manager._observers

        # 验证被观察者创建
        assert len(manager._subjects) == 4
        assert "system_metrics" in manager._subjects
        assert "prediction_metrics" in manager._subjects
        assert "alert" in manager._subjects
        assert "cache" in manager._subjects

        assert manager._initialized is True

    @pytest.mark.asyncio
    async def test_manager_lifecycle(self, manager):
        """测试管理器生命周期"""
        await manager.initialize()

        # 启动
        await manager.start()
        assert manager._running is True

        # 停止
        await manager.stop()
        assert manager._running is False

    @pytest.mark.asyncio
    async def test_prediction_recording_via_manager(self, manager):
        """测试通过管理器记录预测"""
        await manager.initialize()

        await manager.record_prediction(
            strategy_name="ml_model",
            response_time_ms=150.0,
            success=True,
            confidence=0.85,
        )

        prediction_subject = manager.get_prediction_metrics_subject()
        metrics = prediction_subject.get_prediction_metrics()
        assert metrics["prediction_counts"]["ml_model"] == 1

    @pytest.mark.asyncio
    async def test_cache_operations_via_manager(self, manager):
        """测试通过管理器记录缓存操作"""
        await manager.initialize()

        await manager.record_cache_hit("test_cache", "key1")
        await manager.record_cache_miss("test_cache", "key2")

        cache_subject = manager.get_cache_subject()
        stats = cache_subject.get_cache_statistics()
        assert stats["stats"]["hits"] == 1
        assert stats["stats"]["misses"] == 1

    def test_system_status_reporting(self, manager):
        """测试系统状态报告"""
        status = manager.get_system_status()
        assert status["initialized"] is False
        assert status["running"] is False
        assert "observers" in status
        assert "subjects" in status
        assert "timestamp" in status

    def test_metrics_aggregation(self, manager):
        """测试指标聚合"""
        metrics = manager.get_all_metrics()
        assert isinstance(metrics, dict)


@pytest.mark.unit
class TestGlobalObserverManager:
    """测试全局观察者管理器"""

    def test_singleton_pattern(self):
        """测试单例模式"""
        manager1 = get_observer_manager()
        manager2 = get_observer_manager()
        assert manager1 is manager2

    @pytest.mark.asyncio
    async def test_system_functions(self):
        """测试系统级函数"""
        from src.observers.manager import (
            initialize_observer_system,
            start_observer_system,
            stop_observer_system,
        )

        await initialize_observer_system()
        await start_observer_system()
        await stop_observer_system()


# ==================== 集成测试 ====================


@pytest.mark.asyncio
@pytest.mark.integration
class TestObserverIntegration:
    """观察者模式集成测试"""

    async def test_end_to_end_workflow(self):
        """测试端到端工作流"""
        manager = ObserverManager()
        await manager.initialize()
        await manager.start()

        try:
            # 模拟业务操作
            await manager.record_prediction(
                strategy_name="ml_model",
                response_time_ms=150.0,
                success=True,
                confidence=0.85,
            )

            await manager.record_cache_hit("prediction_cache", "key1")
            await manager.record_cache_miss("prediction_cache", "key2")

            # 验证指标收集
            all_metrics = manager.get_all_metrics()
            assert "metrics" in all_metrics
            assert "cache_stats" in all_metrics

            # 验证系统状态
            status = manager.get_system_status()
            assert status["running"] is True
            assert status["initialized"] is True

        finally:
            await manager.stop()

    async def test_error_handling_resilience(self):
        """测试错误处理弹性"""

        # 创建会失败的观察者
        class FailingObserver(Observer):
            def __init__(self):
                super().__init__("FailingObserver")

            async def update(self, event: ObservableEvent) -> None:
                raise Exception("Test error")

            def get_observed_event_types(self) -> List[ObservableEventType]:
                return [ObservableEventType.METRIC_UPDATE]

        # 测试错误不会影响系统运行
        subject = SystemMetricsSubject()
        await subject.attach(FailingObserver())

        event = ObservableEvent(
            event_type=ObservableEventType.METRIC_UPDATE,
            data={"test": True},
        )
        await subject.notify(event)

        # 验证事件仍然被记录
        history = subject.get_event_history()
        assert len(history) == 1
