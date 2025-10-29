
"""
事件系统单元测试
Event System Unit Tests

测试事件系统的核心功能。
Tests core functionality of the event system.
"""

import asyncio

import pytest
import pytest_asyncio

    Event,
    EventHandler,
    get_event_bus,
    start_event_bus,
    stop_event_bus,
)
    AnalyticsEventHandler,
    LoggingEventHandler,
    MetricsEventHandler,
)
from src.events.types import (
    MatchCreatedEvent,
    MatchCreatedEventData,
    PredictionMadeEvent,
    PredictionMadeEventData,
    UserRegisteredEvent,
    UserRegisteredEventData,
)


@pytest.mark.unit
class TestEventHandler(EventHandler):
    """测试用的事件处理器"""

    def __init__(self):
        super().__init__("TestHandler")
        self.handled_events = []

    async def handle(self, event: Event) -> None:
        """处理事件"""
        self.handled_events.append(event)

    def get_handled_events(self) -> list[str]:
        return ["prediction.made", "match.created", "user.registered"]


@pytest_asyncio.fixture
async def event_bus():
    """初始化事件总线"""
    bus = get_event_bus()
    await bus.start()
    yield bus
    await bus.stop()


@pytest.fixture
def test_handler():
    """创建测试处理器"""
    return TestEventHandler()


@pytest.fixture
def metrics_handler():
    """创建指标处理器"""
    return MetricsEventHandler()


@pytest.fixture
def analytics_handler():
    """创建分析处理器"""
    return AnalyticsEventHandler()


@pytest.mark.asyncio
async def test_event_bus_subscription(event_bus, test_handler):
    """测试事件总线订阅功能"""
    # 订阅事件
    await event_bus.subscribe("prediction.made", test_handler)

    # 验证订阅成功
    assert event_bus.get_subscribers_count("prediction.made") == 1


@pytest.mark.asyncio
async def test_event_bus_publish(event_bus, test_handler):
    """测试事件发布"""
    # 订阅事件
    await event_bus.subscribe("prediction.made", test_handler)

    # 创建并发布事件
    event_data = PredictionMadeEventData(
        prediction_id=1,
        match_id=100,
        user_id=1000,
        predicted_home=2,
        predicted_away=1,
        confidence=0.85,
    )
    event = PredictionMadeEvent(event_data)

    # 发布事件
    await event_bus.publish(event)

    # 等待事件处理
    await asyncio.sleep(0.1)

    # 验证事件被处理
    assert len(test_handler.handled_events) == 1
    assert test_handler.handled_events[0].event_id == event.event_id


@pytest.mark.asyncio
async def test_metrics_handler(event_bus, metrics_handler):
    """测试指标处理器"""
    # 订阅事件
    await event_bus.subscribe("prediction.made", metrics_handler)

    # 创建并发布多个事件
    for i in range(3):
        event_data = PredictionMadeEventData(
            prediction_id=i,
            match_id=100 + i,
            user_id=1000,
            predicted_home=2,
            predicted_away=1,
            confidence=0.85,
        )
        event = PredictionMadeEvent(event_data)
        await event_bus.publish(event)

    # 等待事件处理
    await asyncio.sleep(0.1)

    # 验证指标收集
    metrics = metrics_handler.get_metrics()
    assert metrics["events_processed"] == 3
    assert metrics["event_counts"]["prediction.made"] == 3


@pytest.mark.asyncio
async def test_analytics_handler(event_bus, analytics_handler):
    """测试分析处理器"""
    # 订阅事件
    await event_bus.subscribe("prediction.made", analytics_handler)
    await event_bus.subscribe("user.registered", analytics_handler)

    # 发布预测事件
    prediction_data = PredictionMadeEventData(
        prediction_id=1,
        match_id=100,
        user_id=1000,
        predicted_home=2,
        predicted_away=1,
        confidence=0.85,
    )
    prediction_event = PredictionMadeEvent(prediction_data)
    await event_bus.publish(prediction_event)

    # 发布用户注册事件
    user_data = UserRegisteredEventData(
        user_id=1001,
        username="testuser",
        email="test@example.com",
        registration_date=datetime.utcnow(),
    )
    user_event = UserRegisteredEvent(user_data)
    await event_bus.publish(user_event)

    # 等待事件处理
    await asyncio.sleep(0.1)

    # 验证分析数据
    analytics = analytics_handler.get_analytics_data()
    assert "user_activity" in analytics
    assert "daily_predictions" in analytics
    assert analytics["user_activity"][1000]["predictions_count"] == 1


@pytest.mark.asyncio
async def test_multiple_handlers(event_bus):
    """测试多个处理器处理同一事件"""
    handler1 = TestEventHandler()
    handler2 = MetricsEventHandler()

    # 订阅同一事件类型
    await event_bus.subscribe("prediction.made", handler1)
    await event_bus.subscribe("prediction.made", handler2)

    # 发布事件
    event_data = PredictionMadeEventData(
        prediction_id=1,
        match_id=100,
        user_id=1000,
        predicted_home=2,
        predicted_away=1,
        confidence=0.85,
    )
    event = PredictionMadeEvent(event_data)
    await event_bus.publish(event)

    # 等待事件处理
    await asyncio.sleep(0.1)

    # 验证两个处理器都收到事件
    assert len(handler1.handled_events) == 1
    metrics = handler2.get_metrics()
    assert metrics["events_processed"] == 1


@pytest.mark.asyncio
async def test_event_unsubscription(event_bus, test_handler):
    """测试取消订阅"""
    # 订阅事件
    await event_bus.subscribe("prediction.made", test_handler)
    assert event_bus.get_subscribers_count("prediction.made") == 1

    # 取消订阅
    await event_bus.unsubscribe("prediction.made", test_handler)
    assert event_bus.get_subscribers_count("prediction.made") == 0


@pytest.mark.asyncio
async def test_sync_publish(event_bus, test_handler):
    """测试同步发布"""
    # 订阅事件
    await event_bus.subscribe("prediction.made", test_handler)

    # 创建事件
    event_data = PredictionMadeEventData(
        prediction_id=1,
        match_id=100,
        user_id=1000,
        predicted_home=2,
        predicted_away=1,
        confidence=0.85,
    )
    event = PredictionMadeEvent(event_data)

    # 同步发布
    await event_bus.publish_sync(event)

    # 验证事件被立即处理
    assert len(test_handler.handled_events) == 1


@pytest.mark.asyncio
async def test_event_bus_stats(event_bus):
    """测试事件总线统计"""
    # 添加多个订阅者
    handler1 = TestEventHandler()
    handler2 = TestEventHandler()

    await event_bus.subscribe("prediction.made", handler1)
    await event_bus.subscribe("match.created", handler1)
    await event_bus.subscribe("prediction.made", handler2)

    # 获取统计信息
    _stats = event_bus.get_stats()

    assert stats["running"] is True
    assert stats["event_types"] == 2  # prediction.made, match.created
    assert stats["total_subscribers"] == 3
    assert "prediction.made" in stats["event_types_list"]
    assert "match.created" in stats["event_types_list"]


@pytest.mark.asyncio
async def test_event_serialization():
    """测试事件序列化和反序列化"""
    # 创建事件
    event_data = PredictionMadeEventData(
        prediction_id=1,
        match_id=100,
        user_id=1000,
        predicted_home=2,
        predicted_away=1,
        confidence=0.85,
        strategy_used="ensemble_predictor",
    )
    event = PredictionMadeEvent(event_data)

    # 序列化
    event_dict = event.to_dict()

    # 验证序列化结果
    assert event_dict["event_type"] == "prediction.made"
    assert event_dict["prediction_id"] == 1
    assert event_dict["match_id"] == 100
    assert event_dict["confidence"] == 0.85

    # 反序列化
    restored_event = PredictionMadeEvent.from_dict(event_dict)

    # 验证反序列化结果
    assert restored_event.event_id == event.event_id
    assert restored_event.data.prediction_id == event.data.prediction_id
    assert restored_event.get_event_type() == event.get_event_type()


def test_event_types():
    """测试不同事件类型的创建"""
    # 测试预测事件
    pred_data = PredictionMadeEventData(
        prediction_id=1,
        match_id=100,
        user_id=1000,
        predicted_home=2,
        predicted_away=1,
        confidence=0.85,
    )
    pred_event = PredictionMadeEvent(pred_data)
    assert pred_event.get_event_type() == "prediction.made"

    # 测试比赛事件
    match_data = MatchCreatedEventData(
        match_id=100,
        home_team_id=1,
        away_team_id=2,
        league_id=10,
        match_time=datetime.utcnow(),
    )
    match_event = MatchCreatedEvent(match_data)
    assert match_event.get_event_type() == "match.created"

    # 测试用户事件
    user_data = UserRegisteredEventData(
        user_id=1000,
        username="testuser",
        email="test@example.com",
        registration_date=datetime.utcnow(),
    )
    user_event = UserRegisteredEvent(user_data)
    assert user_event.get_event_type() == "user.registered"
