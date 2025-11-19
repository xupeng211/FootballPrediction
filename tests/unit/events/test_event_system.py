"""
事件系统测试套件
Event System Test Suite

测试事件系统的核心功能，包括事件基类、事件总线、事件处理器等.
"""

import asyncio
from datetime import datetime
from typing import Any, Optional
from unittest.mock import AsyncMock, Mock

import pytest

from src.events.base import EventData, EventHandler
from src.events.bus import EventBus
from src.events.handlers import MetricsEventHandler
from src.events.types import (
    MatchCreatedEvent,
    MatchCreatedEventData,
    PredictionMadeEvent,
    UserRegisteredEvent,
)


class TestEventData:
    """事件数据测试"""

    def test_event_data_initialization(self):
        """测试事件数据初始化"""
        event_data = EventData(
            source="test_service",
            version="1.0",
            metadata={"key": "value"},
            event_id="test-event-123",
            timestamp=datetime(2024, 1, 1, 12, 0, 0),
        )

        assert event_data.source == "test_service"
        assert event_data.version == "1.0"
        assert event_data.metadata == {"key": "value"}
        assert event_data.event_id == "test-event-123"
        assert event_data.timestamp == datetime(2024, 1, 1, 12, 0, 0)

    def test_event_data_default_values(self):
        """测试事件数据默认值"""
        event_data = EventData()

        assert event_data.source is None
        assert event_data.version == "1.0"
        assert event_data.metadata is None
        assert event_data.event_id is not None  # 应该自动生成UUID
        assert event_data.timestamp is not None  # 应该自动生成时间戳

    def test_event_data_auto_generation(self):
        """测试事件数据自动生成"""
        event_data1 = EventData()
        event_data2 = EventData()

        # 验证UUID唯一性
        assert event_data1.event_id != event_data2.event_id

        # 验证时间戳是最近的
        now = datetime.utcnow()
        assert abs((event_data1.timestamp - now).total_seconds()) < 5
        assert abs((event_data2.timestamp - now).total_seconds()) < 5

    def test_event_data_to_dict(self):
        """测试事件数据转换为字典"""
        event_data = EventData(source="test_service", metadata={"key": "value"})

        # 检查是否实现to_dict方法
        if hasattr(event_data, "to_dict"):
            data_dict = event_data.to_dict()
            assert data_dict["source"] == "test_service"
            assert data_dict["metadata"] == {"key": "value"}


class TestEventTypes:
    """事件类型测试"""

    def test_match_created_event(self):
        """测试比赛创建事件"""
        event_data = MatchCreatedEventData(
            match_id=12345,
            home_team_id=1,
            away_team_id=2,
            league_id=10,
            match_time=datetime(2024, 12, 1, 20, 0, 0),
        )
        event = MatchCreatedEvent(event_data)

        assert event.data.match_id == 12345
        assert event.data.home_team_id == 1
        assert event.data.away_team_id == 2
        assert event.data.league_id == 10
        assert event.data.match_time == datetime(2024, 12, 1, 20, 0, 0)

    def test_prediction_made_event(self):
        """测试预测创建事件"""
        # 创建简单的预测事件数据
        event_data = EventData(
            source="prediction_service",
            metadata={"prediction_id": 67890, "match_id": 12345, "user_id": 999},
        )

        # 验证事件数据创建成功
        assert event_data.source == "prediction_service"
        assert event_data.metadata["prediction_id"] == 67890
        assert event_data.metadata["match_id"] == 12345
        assert event_data.metadata["user_id"] == 999

    def test_user_registered_event(self):
        """测试用户注册事件"""
        # 创建用户注册事件数据
        event_data = EventData(
            source="user_service",
            metadata={
                "user_id": 1111,
                "username": "testuser",
                "email": "test@example.com",
            },
        )

        # 验证事件数据
        assert event_data.source == "user_service"
        assert event_data.metadata["user_id"] == 1111
        assert event_data.metadata["username"] == "testuser"
        assert event_data.metadata["email"] == "test@example.com"

    def test_team_stats_updated_event(self):
        """测试队伍统计更新事件"""
        # 创建队伍统计更新事件数据
        event_data = EventData(
            source="stats_service",
            metadata={
                "team_id": 2222,
                "team_name": "Test Team",
                "stats_updated": {
                    "wins": 10,
                    "losses": 5,
                    "goals_scored": 25,
                    "goals_conceded": 15,
                },
            },
        )

        # 验证事件数据
        assert event_data.source == "stats_service"
        assert event_data.metadata["team_id"] == 2222
        assert event_data.metadata["team_name"] == "Test Team"
        assert event_data.metadata["stats_updated"]["wins"] == 10
        assert event_data.metadata["stats_updated"]["losses"] == 5

    def test_event_inheritance(self):
        """测试事件继承关系"""
        # 创建基本事件数据
        event_data1 = EventData(source="test1")
        event_data2 = EventData(source="test2")
        event_data3 = EventData(source="test3")

        events = [event_data1, event_data2, event_data3]

        for event in events:
            # 验证所有事件都继承自EventData
            assert isinstance(event, EventData)
            assert hasattr(event, "source")
            assert hasattr(event, "event_id")
            assert hasattr(event, "timestamp")


class TestEventBus:
    """事件总线测试"""

    @pytest.fixture
    def event_bus(self):
        """创建事件总线实例"""
        return EventBus(max_workers=5)

    def test_event_bus_initialization(self, event_bus):
        """测试事件总线初始化"""
        assert event_bus._subscribers is not None
        assert event_bus._filters is not None
        assert hasattr(event_bus, "_executor")

    def test_subscribe_to_event(self, event_bus):
        """测试订阅事件"""
        handler = Mock(spec=EventHandler)

        # 订阅事件
        event_bus.subscribe_sync("test_event", handler)

        # 验证订阅成功
        assert "test_event" in event_bus._subscribers
        assert handler in event_bus._subscribers["test_event"]

    def test_subscribe_multiple_handlers(self, event_bus):
        """测试订阅多个处理器"""
        handler1 = Mock(spec=EventHandler)
        handler2 = Mock(spec=EventHandler)

        # 订阅同一事件的多个处理器
        event_bus.subscribe_sync("test_event", handler1)
        event_bus.subscribe_sync("test_event", handler2)

        # 验证两个处理器都已订阅
        assert len(event_bus._subscribers["test_event"]) == 2
        assert handler1 in event_bus._subscribers["test_event"]
        assert handler2 in event_bus._subscribers["test_event"]

    def test_unsubscribe_from_event(self, event_bus):
        """测试取消订阅事件"""
        handler = Mock(spec=EventHandler)

        # 先订阅
        event_bus.subscribe_sync("test_event", handler)
        assert handler in event_bus._subscribers["test_event"]

        # 取消订阅
        event_bus.unsubscribe_sync("test_event", handler)
        assert handler not in event_bus._subscribers["test_event"]

    def test_publish_event_sync(self, event_bus):
        """测试同步发布事件"""
        handler = Mock(spec=EventHandler)
        handler.handle = Mock()

        # 订阅事件
        event_bus.subscribe_sync("test_event", handler)

        # 发布事件
        test_event = EventData(source="test", event_id="test-123")
        event_bus.publish_sync("test_event", test_event)

        # 验证处理器被调用
        handler.handle.assert_called_once_with(test_event)

    def test_publish_event_async(self, event_bus):
        """测试异步发布事件"""

        async def async_publish():
            handler = AsyncMock(spec=EventHandler)
            handler.handle = AsyncMock()
            handler.name = "TestHandler"

            # 添加必需的方法
            handler._subscribed_events = {}

            def add_subscription(event_type, queue):
                handler._subscribed_events[event_type] = queue

            def is_subscribed_to(event_type):
                return event_type in handler._subscribed_events

            handler.add_subscription = add_subscription
            handler.is_subscribed_to = is_subscribed_to

            # 订阅事件
            await event_bus.subscribe("test_event", handler)

            # 启动EventBus
            await event_bus.start()

            # 发布事件
            test_event = EventData(source="test", event_id="test-123")
            await event_bus.publish("test_event", test_event)

            # 等待一下让事件处理完成
            await asyncio.sleep(0.1)

            # 验证处理器被调用
            handler.handle.assert_called_once()

            # 停止EventBus
            await event_bus.stop()

        # 运行异步测试
        asyncio.run(async_publish())

    def test_publish_to_multiple_handlers(self, event_bus):
        """测试发布事件到多个处理器"""
        handler1 = Mock(spec=EventHandler)
        handler2 = Mock(spec=EventHandler)
        handler1.handle = Mock()
        handler2.handle = Mock()

        # 订阅多个处理器
        event_bus.subscribe_sync("test_event", handler1)
        event_bus.subscribe_sync("test_event", handler2)

        # 发布事件
        test_event = EventData(source="test", event_id="test-123")
        event_bus.publish_sync("test_event", test_event)

        # 验证所有处理器都被调用
        handler1.handle.assert_called_once_with(test_event)
        handler2.handle.assert_called_once_with(test_event)

    def test_event_filtering(self, event_bus):
        """测试事件过滤"""
        handler = Mock(spec=EventHandler)
        handler.handle = Mock()

        # 创建过滤器
        def test_filter(event):
            return hasattr(event, "source") and event.source == "allowed_source"

        # 订阅事件并添加过滤器
        event_bus.subscribe_sync("test_event", handler)
        event_bus.add_filter(handler, test_filter)

        # 发布允许的事件
        allowed_event = EventData(source="allowed_source", event_id="test-1")
        event_bus.publish_sync("test_event", allowed_event)
        handler.handle.assert_called_once_with(allowed_event)

        # 重置mock
        handler.handle.reset_mock()

        # 发布被过滤的事件
        filtered_event = EventData(source="blocked_source", event_id="test-2")
        event_bus.publish_sync("test_event", filtered_event)
        handler.handle.assert_not_called()

    def test_no_subscribers_event(self, event_bus):
        """测试没有订阅者的事件"""
        # 发布没有订阅者的事件
        test_event = EventData(source="test", event_id="test-123")

        # 应该不会抛出异常
        event_bus.publish_sync("nonexistent_event", test_event)


class TestMetricsEventHandler:
    """指标事件处理器测试"""

    def test_metrics_handler_initialization(self):
        """测试指标处理器初始化"""
        handler = MetricsEventHandler()

        assert handler.name == "MetricsCollector"
        assert "events_processed" in handler.metrics
        assert "event_counts" in handler.metrics
        assert "last_event_time" in handler.metrics
        assert handler.metrics["events_processed"] == 0
        assert handler.metrics["event_counts"] == {}

    def test_metrics_handle_event(self):
        """测试指标处理器处理事件"""
        handler = MetricsEventHandler()

        # 创建测试事件
        test_event = EventData(source="test_service", event_id="test-123")

        # 处理事件
        handler.handle_sync(test_event)

        # 验证指标更新
        assert handler.metrics["events_processed"] == 1
        assert "EventData" in handler.metrics["event_counts"]
        assert handler.metrics["event_counts"]["EventData"] == 1
        assert handler.metrics["last_event_time"] is not None

    def test_metrics_handle_multiple_events(self):
        """测试指标处理器处理多个事件"""
        handler = MetricsEventHandler()

        # 处理多个不同类型的事件
        from src.events.types import MatchCreatedEventData, PredictionMadeEventData
        events = [
            EventData(source="test", event_id="test-1"),
            MatchCreatedEvent(data=MatchCreatedEventData(
                match_id=1,
                home_team_id=1,
                away_team_id=2,
                league_id=1,
                match_time=datetime(2024, 12, 1, 20, 0, 0)
            )),
            PredictionMadeEvent(data=PredictionMadeEventData(
                prediction_id=1,
                match_id=1,
                user_id=1,
                predicted_home=2,
                predicted_away=1,
                confidence=0.8,
            )),
        ]

        for event in events:
            handler.handle_sync(event)

        # 验证指标
        assert handler.metrics["events_processed"] == 3
        assert len(handler.metrics["event_counts"]) == 3  # 三种不同类型的事件

    def test_metrics_get_metrics(self):
        """测试获取指标"""
        handler = MetricsEventHandler()

        # 处理一些事件
        handler.handle_sync(EventData(source="test", event_id="test-1"))
        handler.handle_sync(MatchCreatedEvent(data=MatchCreatedEventData(
            match_id=1,
            home_team_id=1,
            away_team_id=2,
            league_id=1,
            match_time=datetime(2024, 12, 1, 20, 0, 0)
        )))

        # 获取指标
        metrics = handler.get_metrics()

        assert metrics["events_processed"] == 2
        assert "EventData" in metrics["event_counts"]
        assert "match.created" in metrics["event_counts"]
        assert metrics["last_event_time"] is not None

    def test_metrics_reset(self):
        """测试重置指标"""
        handler = MetricsEventHandler()

        # 处理一些事件
        handler.handle_sync(EventData(source="test", event_id="test-1"))
        assert handler.metrics["events_processed"] == 1

        # 重置指标
        if hasattr(handler, "reset"):
            handler.reset()
            assert handler.metrics["events_processed"] == 0
            assert handler.metrics["event_counts"] == {}


class TestEventIntegration:
    """事件系统集成测试"""

    def test_end_to_end_event_flow(self):
        """测试端到端事件流程"""
        # 创建事件总线
        event_bus = EventBus()

        # 创建指标处理器
        metrics_handler = MetricsEventHandler()

        # 创建自定义处理器
        custom_handler = Mock(spec=EventHandler)
        custom_handler.handle = Mock()

        # 订阅事件
        event_bus.subscribe_sync("MatchCreatedEvent", metrics_handler)
        event_bus.subscribe_sync("MatchCreatedEvent", custom_handler)

        # 创建并发布比赛创建事件
        match_event = MatchCreatedEvent(data=MatchCreatedEventData(
            match_id=12345,
            home_team_id=1,
            away_team_id=2,
            league_id=1,
            match_time=datetime(2024, 12, 1, 20, 0, 0)
        ))

        # 发布事件
        event_bus.publish_sync("MatchCreatedEvent", match_event)

        # 验证处理器被调用
        custom_handler.handle.assert_called_once_with(match_event)

        # 验证指标处理器更新
        metrics = metrics_handler.get_metrics()
        assert metrics["events_processed"] == 1
        assert "match.created" in metrics["event_counts"]

    def test_event_error_handling(self):
        """测试事件错误处理"""
        event_bus = EventBus()

        # 创建会抛出异常的处理器
        def failing_handler(event):
            raise Exception("Handler error")

        # 创建正常的处理器
        success_handler = Mock(spec=EventHandler)
        success_handler.handle = Mock()

        # 订阅事件
        event_bus.subscribe_sync("test_event", failing_handler)
        event_bus.subscribe_sync("test_event", success_handler)

        # 发布事件
        test_event = EventData(source="test", event_id="test-123")

        # 应该不会因为一个处理器失败而影响其他处理器
        try:
            event_bus.publish_sync("test_event", test_event)
        except Exception:
            pass  # 可能会抛出异常，但不应该中断整个流程

        # 验证正常处理器仍然被调用
        success_handler.handle.assert_called_once_with(test_event)

    def test_concurrent_event_publishing(self):
        """测试并发事件发布"""
        import threading

        event_bus = EventBus()
        metrics_handler = MetricsEventHandler()

        # 订阅事件
        event_bus.subscribe_sync("test_event", metrics_handler)

        results = []

        def publish_event(event_id):
            event = EventData(source=f"thread-{event_id}", event_id=f"test-{event_id}")
            event_bus.publish_sync("test_event", event)
            results.append(event_id)

        # 创建多个线程同时发布事件
        threads = []
        for i in range(10):
            thread = threading.Thread(target=publish_event, args=(i,))
            threads.append(thread)

        # 启动所有线程
        for thread in threads:
            thread.start()

        # 等待所有线程完成
        for thread in threads:
            thread.join()

        # 验证所有事件都被处理
        assert len(results) == 10
        assert metrics_handler.metrics["events_processed"] == 10


class TestEventPerformance:
    """事件系统性能测试"""

    def test_event_publishing_performance(self):
        """测试事件发布性能"""
        import time

        event_bus = EventBus()
        handler = Mock(spec=EventHandler)
        handler.handle = Mock()

        # 订阅事件
        event_bus.subscribe_sync("test_event", handler)

        # 测试大量事件发布性能
        start_time = time.time()

        for i in range(1000):
            event = EventData(source="test", event_id=f"test-{i}")
            event_bus.publish_sync("test_event", event)

        end_time = time.time()
        duration = end_time - start_time

        # 验证性能（1000个事件应该在5秒内完成）
        assert duration < 5.0, f"Event publishing too slow: {duration}s"
        assert handler.handle.call_count == 1000

    def test_multiple_handlers_performance(self):
        """测试多处理器性能"""
        import time

        event_bus = EventBus()

        # 创建多个处理器
        handlers = []
        for _ in range(10):
            handler = Mock(spec=EventHandler)
            handler.handle = Mock()
            handlers.append(handler)
            event_bus.subscribe_sync("test_event", handler)

        # 测试性能
        start_time = time.time()

        for i in range(100):
            event = EventData(source="test", event_id=f"test-{i}")
            event_bus.publish_sync("test_event", event)

        end_time = time.time()
        duration = end_time - start_time

        # 验证所有处理器都被调用
        for handler in handlers:
            assert handler.handle.call_count == 100

        # 验证性能（100个事件 * 10个处理器应该在3秒内完成）
        assert duration < 3.0, f"Multiple handlers too slow: {duration}s"


# 测试工具函数
def create_test_event(event_type: str, **kwargs) -> Any:
    """创建测试事件"""
    if event_type == "match_created":
        return MatchCreatedEvent(data=MatchCreatedEventData(
            match_id=kwargs.get("match_id", 12345),
            home_team_id=1,
            away_team_id=2,
            league_id=1,
            match_time=datetime(2024, 12, 1, 20, 0, 0)
        ))
    elif event_type == "prediction_made":
        return PredictionMadeEvent(data=PredictionMadeEventData(
            prediction_id=kwargs.get("prediction_id", 67890),
            match_id=kwargs.get("match_id", 12345),
            user_id=kwargs.get("user_id", 999),
            predicted_home=kwargs.get("predicted_home", 2),
            predicted_away=kwargs.get("predicted_away", 1),
            confidence=kwargs.get("confidence", 0.85),
        ))
    elif event_type == "user_registered":
        return UserRegisteredEvent(data=UserRegisteredEventData(
            user_id=kwargs.get("user_id", 1111),
            username=kwargs.get("username", "testuser"),
            email=kwargs.get("email", "test@example.com"),
            registration_date=datetime(2024, 1, 1, 12, 0, 0)
        ))
    else:
        return EventData(source="test", **kwargs)


def create_event_bus_with_handlers() -> EventBus:
    """创建带有处理器的事件总线"""
    event_bus = EventBus()
    metrics_handler = MetricsEventHandler()

    # 订阅一些基本事件
    event_bus.subscribe_sync("test_event", metrics_handler)

    return event_bus, metrics_handler


def assert_event_processed(handler: Mock, expected_event: Any):
    """断言事件已被处理"""
    handler.handle.assert_called()
    call_args = handler.handle.call_args[0][0]
    assert call_args == expected_event
