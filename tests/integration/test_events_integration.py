"""
事件系统集成测试
Event System Integration Tests

测试事件驱动架构的完整功能，包括事件发布、订阅、处理和传播机制。
"""

import pytest
import asyncio
import time
from datetime import datetime
from unittest.mock import AsyncMock, Mock, patch, MagicMock
from typing import Dict, Any, List, Callable
from dataclasses import dataclass

from src.api.events import EventBus, Event, EventHandler
from src.core.events import DomainEvent, EventStore
from src.database.models import Event as EventModel


@pytest.mark.integration
@pytest.mark.events_integration
class TestEventBusIntegration:
    """事件总线集成测试"""

    @pytest.fixture
    def event_bus(self):
        """创建事件总线"""
        return EventBus()

    @pytest.fixture
    def sample_event(self):
        """创建示例事件"""
        return Event(
            type="match_prediction_completed",
            data={
                "match_id": 123,
                "prediction": "home_win",
                "confidence": 0.85,
                "timestamp": datetime.utcnow().isoformat()
            },
            source="prediction_service"
        )

    async def test_event_publish_and_subscribe(self, event_bus, sample_event):
        """测试事件发布和订阅"""
        received_events = []

        async def event_handler(event: Event):
            received_events.append(event)

        # 订阅事件
        event_bus.subscribe("match_prediction_completed", event_handler)

        # 发布事件
        await event_bus.publish(sample_event)

        # 等待事件处理
        await asyncio.sleep(0.1)

        # 验证事件被接收
        assert len(received_events) == 1
        assert received_events[0].type == "match_prediction_completed"
        assert received_events[0].data["match_id"] == 123

    async def test_multiple_subscribers_same_event(self, event_bus, sample_event):
        """测试多个订阅者接收同一事件"""
        received_counts = {"handler1": 0, "handler2": 0, "handler3": 0}

        async def handler1(event: Event):
            received_counts["handler1"] += 1

        async def handler2(event: Event):
            received_counts["handler2"] += 1

        async def handler3(event: Event):
            received_counts["handler3"] += 1

        # 订阅同一事件
        event_bus.subscribe("match_prediction_completed", handler1)
        event_bus.subscribe("match_prediction_completed", handler2)
        event_bus.subscribe("match_prediction_completed", handler3)

        # 发布事件
        await event_bus.publish(sample_event)

        # 等待事件处理
        await asyncio.sleep(0.1)

        # 验证所有订阅者都收到事件
        assert received_counts["handler1"] == 1
        assert received_counts["handler2"] == 1
        assert received_counts["handler3"] == 1

    async def test_event_filtering(self, event_bus):
        """测试事件过滤"""
        received_events = []

        async def conditional_handler(event: Event):
            # 只处理高置信度的预测
            if event.data.get("confidence", 0) > 0.8:
                received_events.append(event)

        event_bus.subscribe("match_prediction_completed", conditional_handler)

        # 发布多个不同置信度的事件
        events = [
            Event("match_prediction_completed", {"match_id": 1, "confidence": 0.9}, "test"),
            Event("match_prediction_completed", {"match_id": 2, "confidence": 0.7}, "test"),
            Event("match_prediction_completed", {"match_id": 3, "confidence": 0.95}, "test"),
        ]

        for event in events:
            await event_bus.publish(event)

        await asyncio.sleep(0.1)

        # 验证只有高置信度事件被处理
        assert len(received_events) == 2
        assert received_events[0].data["match_id"] == 1
        assert received_events[1].data["match_id"] == 3

    async def test_event_unsubscribe(self, event_bus, sample_event):
        """测试取消订阅事件"""
        received_events = []

        async def event_handler(event: Event):
            received_events.append(event)

        # 订阅事件
        subscription_id = event_bus.subscribe("match_prediction_completed", event_handler)

        # 发布事件（应该被接收）
        await event_bus.publish(sample_event)
        await asyncio.sleep(0.1)
        assert len(received_events) == 1

        # 取消订阅
        event_bus.unsubscribe(subscription_id)

        # 再次发布事件（不应该被接收）
        await event_bus.publish(sample_event)
        await asyncio.sleep(0.1)
        assert len(received_events) == 1  # 仍然只有1个事件

    async def test_event_error_handling(self, event_bus, sample_event):
        """测试事件处理错误处理"""
        successful_events = []
        failed_events = []

        async def failing_handler(event: Event):
            if event.data.get("match_id") == 123:
                raise Exception("Simulated handler error")
            successful_events.append(event)

        async def error_logger(event: Event, error: Exception):
            failed_events.append((event, str(error)))

        # 设置错误处理
        event_bus.set_error_handler(error_logger)
        event_bus.subscribe("match_prediction_completed", failing_handler)

        # 发布会导致错误的事件
        await event_bus.publish(sample_event)
        await asyncio.sleep(0.1)

        # 验证错误被正确处理
        assert len(successful_events) == 0
        assert len(failed_events) == 1
        assert failed_events[0][0].data["match_id"] == 123

    async def test_event_bus_performance(self, event_bus):
        """测试事件总线性能"""
        processed_count = 0
        event_count = 100

        async def fast_handler(event: Event):
            nonlocal processed_count
            processed_count += 1

        event_bus.subscribe("performance_test", fast_handler)

        # 批量发布事件
        start_time = time.time()
        for i in range(event_count):
            event = Event("performance_test", {"index": i}, "performance_test")
            await event_bus.publish(event)

        # 等待所有事件处理完成
        await asyncio.sleep(1.0)
        end_time = time.time()

        # 验证性能
        processing_time = end_time - start_time
        assert processed_count == event_count
        assert processing_time < 2.0  # 应该在2秒内完成


@pytest.mark.integration
@pytest.mark.events_integration
class TestDomainEventIntegration:
    """领域事件集成测试"""

    @pytest.fixture
    def event_store(self):
        """创建事件存储"""
        return EventStore()

    @pytest.fixture
    def sample_domain_event(self):
        """创建示例领域事件"""
        return DomainEvent(
            aggregate_id="team_123",
            event_type="team_name_changed",
            event_data={
                "old_name": "Old Team Name",
                "new_name": "New Team Name",
                "changed_by": "admin_user"
            },
            version=1,
            timestamp=datetime.utcnow()
        )

    async def test_domain_event_creation(self, sample_domain_event):
        """测试领域事件创建"""
        assert sample_domain_event.aggregate_id == "team_123"
        assert sample_domain_event.event_type == "team_name_changed"
        assert sample_domain_event.version == 1
        assert sample_domain_event.event_data["new_name"] == "New Team Name"

    async def test_event_store_persistence(self, event_store, sample_domain_event):
        """测试事件存储持久化"""
        # 保存事件
        event_id = await event_store.save_event(sample_domain_event)
        assert event_id is not None

        # 获取事件
        retrieved_event = await event_store.get_event(event_id)
        assert retrieved_event is not None
        assert retrieved_event.aggregate_id == sample_domain_event.aggregate_id
        assert retrieved_event.event_type == sample_domain_event.event_type

    async def test_event_aggregation_retrieval(self, event_store):
        """测试聚合事件检索"""
        aggregate_id = "match_456"

        # 创建多个事件
        events = [
            DomainEvent(aggregate_id, "match_created", {"home_team": "A", "away_team": "B"}, 1),
            DomainEvent(aggregate_id, "match_started", {"kickoff_time": "15:00"}, 2),
            DomainEvent(aggregate_id, "goal_scored", {"team": "A", "minute": 25}, 3),
            DomainEvent(aggregate_id, "match_finished", {"final_score": "2-1"}, 4),
        ]

        # 保存所有事件
        event_ids = []
        for event in events:
            event_id = await event_store.save_event(event)
            event_ids.append(event_id)

        # 获取聚合的所有事件
        aggregate_events = await event_store.get_aggregate_events(aggregate_id)
        assert len(aggregate_events) == 4
        assert aggregate_events[0].event_type == "match_created"
        assert aggregate_events[-1].event_type == "match_finished"

        # 验证事件顺序
        for i, event in enumerate(aggregate_events):
            assert event.version == i + 1

    async def test_event_snapshot_creation(self, event_store):
        """测试事件快照创建"""
        aggregate_id = "team_789"

        # 创建大量事件
        for i in range(10):
            event = DomainEvent(
                aggregate_id,
                f"event_{i}",
                {"data": f"value_{i}"},
                i + 1
            )
            await event_store.save_event(event)

        # 创建快照
        snapshot_data = {
            "team_id": aggregate_id,
            "name": "Test Team",
            "points": 25,
            "version": 10
        }

        snapshot_id = await event_store.create_snapshot(aggregate_id, snapshot_data, 10)
        assert snapshot_id is not None

        # 获取最新快照
        latest_snapshot = await event_store.get_latest_snapshot(aggregate_id)
        assert latest_snapshot is not None
        assert latest_snapshot["data"]["name"] == "Test Team"
        assert latest_snapshot["version"] == 10

    async def test_event_replay_from_snapshot(self, event_store):
        """测试从快照重放事件"""
        aggregate_id = "player_101"

        # 创建初始事件和快照
        initial_events = [
            DomainEvent(aggregate_id, "player_created", {"name": "John Doe", "age": 25}, 1),
            DomainEvent(aggregate_id, "stats_updated", {"goals": 5, "assists": 3}, 2),
        ]

        for event in initial_events:
            await event_store.save_event(event)

        # 创建快照
        snapshot_data = {"name": "John Doe", "age": 25, "goals": 5, "assists": 3, "version": 2}
        await event_store.create_snapshot(aggregate_id, snapshot_data, 2)

        # 添加更多事件
        later_events = [
            DomainEvent(aggregate_id, "goal_scored", {"match_id": 1, "minute": 45}, 3),
            DomainEvent(aggregate_id, "stats_updated", {"goals": 6, "assists": 3}, 4),
        ]

        for event in later_events:
            await event_store.save_event(event)

        # 从快照重放状态
        current_state = await event_store.replay_from_snapshot(aggregate_id)
        assert current_state["goals"] == 6  # 包含快照后的所有变化
        assert current_state["assists"] == 3


@pytest.mark.integration
@pytest.mark.events_integration
class TestEventProcessingIntegration:
    """事件处理集成测试"""

    @pytest.fixture
    def event_processor(self):
        """创建事件处理器"""
        from src.core.events import EventProcessor
        return EventProcessor()

    @pytest.fixture
    def sample_prediction_event(self):
        """创建预测事件"""
        return Event(
            type="prediction_request",
            data={
                "match_id": 123,
                "home_team": "Team A",
                "away_team": "Team B",
                "requested_by": "user_456"
            },
            source="api_gateway"
        )

    async def test_prediction_event_processing(self, event_processor, sample_prediction_event):
        """测试预测事件处理"""
        processed_events = []

        async def prediction_handler(event: Event):
            # 模拟预测处理逻辑
            prediction_result = {
                "match_id": event.data["match_id"],
                "prediction": "home_win",
                "confidence": 0.78,
                "processed_at": datetime.utcnow().isoformat()
            }

            # 发布预测完成事件
            completion_event = Event(
                type="prediction_completed",
                data=prediction_result,
                source="prediction_service"
            )

            processed_events.append(completion_event)
            return completion_event

        # 注册处理器
        event_processor.register_handler("prediction_request", prediction_handler)

        # 处理事件
        result = await event_processor.process_event(sample_prediction_event)

        # 验证处理结果
        assert result is not None
        assert result.type == "prediction_completed"
        assert result.data["prediction"] == "home_win"
        assert len(processed_events) == 1

    async def test_batch_event_processing(self, event_processor):
        """测试批量事件处理"""
        processed_count = 0

        async def batch_handler(event: Event):
            nonlocal processed_count
            processed_count += 1
            # 模拟一些处理时间
            await asyncio.sleep(0.01)

        event_processor.register_handler("batch_test", batch_handler)

        # 创建批量事件
        events = [
            Event("batch_test", {"index": i}, "batch_test")
            for i in range(20)
        ]

        # 批量处理
        start_time = time.time()
        results = await event_processor.process_batch(events)
        processing_time = time.time() - start_time

        # 验证结果
        assert len(results) == 20
        assert processed_count == 20
        assert processing_time < 2.0  # 应该在2秒内完成

    async def test_event_dead_letter_queue(self, event_processor):
        """测试死信队列处理"""
        failed_events = []

        async def failing_handler(event: Event):
            if event.data.get("should_fail", False):
                raise Exception("Intentional failure")
            return event

        async def dead_letter_handler(event: Event, error: Exception):
            failed_events.append((event, error))

        # 设置死信队列处理器
        event_processor.set_dead_letter_handler(dead_letter_handler)
        event_processor.register_handler("dlq_test", failing_handler)

        # 测试成功事件
        success_event = Event("dlq_test", {"should_fail": False}, "test")
        await event_processor.process_event(success_event)

        # 测试失败事件
        fail_event = Event("dlq_test", {"should_fail": True}, "test")
        await event_processor.process_event(fail_event)

        # 验证失败事件进入死信队列
        assert len(failed_events) == 1
        assert failed_events[0][0].data["should_fail"] is True

    async def test_event_retry_mechanism(self, event_processor):
        """测试事件重试机制"""
        attempt_count = 0
        max_attempts = 3

        async def flaky_handler(event: Event):
            nonlocal attempt_count
            attempt_count += 1
            if attempt_count < max_attempts:
                raise Exception(f"Attempt {attempt_count} failed")
            return {"success": True, "attempts": attempt_count}

        event_processor.register_handler("retry_test", flaky_handler)

        # 处理需要重试的事件
        result = await event_processor.process_event_with_retry(
            Event("retry_test", {"data": "test"}, "test"),
            max_retries=3
        )

        # 验证重试成功
        assert result["success"] is True
        assert result["attempts"] == 3
        assert attempt_count == 3


@pytest.mark.integration
@pytest.mark.events_integration
class TestEventSourcingIntegration:
    """事件溯源集成测试"""

    @pytest.fixture
    def event_sourced_aggregate(self):
        """创建事件溯源聚合"""
        from src.domain.aggregates import TeamAggregate
        return TeamAggregate()

    async def test_aggregate_state_reconstruction(self, event_sourced_aggregate):
        """测试聚合状态重建"""
        # 创建领域事件序列
        events = [
            DomainEvent("team_1", "team_created", {"name": "New Team", "country": "Country"}, 1),
            DomainEvent("team_1", "team_renamed", {"old_name": "New Team", "new_name": "Renamed Team"}, 2),
            DomainEvent("team_1", "manager_changed", {"old_manager": None, "new_manager": "John Coach"}, 3),
            DomainEvent("team_1", "points_added", {"points": 3, "competition": "League"}, 4),
        ]

        # 重放事件重建状态
        for event in events:
            event_sourced_aggregate.apply(event)

        # 验证最终状态
        assert event_sourced_aggregate.name == "Renamed Team"
        assert event_sourced_aggregate.country == "Country"
        assert event_sourced_aggregate.manager == "John Coach"
        assert event_sourced_aggregate.points == 3
        assert event_sourced_aggregate.version == 4

    async def test_aggregate_event_validation(self, event_sourced_aggregate):
        """测试聚合事件验证"""
        # 测试有效事件
        valid_event = DomainEvent(
            "team_1",
            "player_signed",
            {"player_name": "New Player", "position": "forward"},
            1
        )

        # 应用有效事件应该成功
        try:
            event_sourced_aggregate.apply(valid_event)
            validation_passed = True
        except Exception:
            validation_passed = False

        assert validation_passed is True

    async def test_aggregate_snapshot_optimization(self, event_sourced_aggregate):
        """测试聚合快照优化"""
        # 生成大量事件
        for i in range(100):
            event = DomainEvent(
                "team_1",
                f"event_{i}",
                {"data": f"value_{i}", "timestamp": time.time()},
                i + 1
            )
            event_sourced_aggregate.apply(event)

        # 验证快照创建
        snapshot = event_sourced_aggregate.create_snapshot()
        assert snapshot is not None
        assert snapshot["version"] == 100
        assert snapshot["state"]["version"] == 100

        # 验证从快照恢复
        new_aggregate = type(event_sourced_aggregate)()
        new_aggregate.restore_from_snapshot(snapshot)

        assert new_aggregate.version == event_sourced_aggregate.version
        assert new_aggregate.state == event_sourced_aggregate.state


@pytest.mark.integration
@pytest.mark.events_integration
class TestRealWorldEventScenarios:
    """真实世界事件场景集成测试"""

    async def test_football_match_lifecycle_events(self):
        """测试足球比赛生命周期事件"""
        events_received = []

        async def match_lifecycle_handler(event: Event):
            events_received.append(event)

        event_bus = EventBus()
        event_bus.subscribe("match_*", match_lifecycle_handler)

        # 模拟比赛生命周期
        match_events = [
            Event("match_created", {"match_id": 123, "home": "A", "away": "B"}, "scheduler"),
            Event("match_started", {"match_id": 123, "kickoff": "15:00"}, "referee"),
            Event("goal_scored", {"match_id": 123, "team": "A", "scorer": "Player1", "minute": 25}, "score_tracker"),
            Event("match_finished", {"match_id": 123, "final_score": "2-1"}, "referee"),
            Event("prediction_processed", {"match_id": 123, "result": "home_win", "accuracy": "correct"}, "ai_service"),
        ]

        # 发布所有事件
        for event in match_events:
            await event_bus.publish(event)

        await asyncio.sleep(0.1)

        # 验证所有事件都被接收
        assert len(events_received) == 5
        assert events_received[0].type == "match_created"
        assert events_received[-1].type == "prediction_processed"

    async def test_prediction_pipeline_events(self):
        """测试预测流水线事件"""
        pipeline_stages = []

        async def pipeline_tracker(event: Event):
            pipeline_stages.append({
                "stage": event.type,
                "timestamp": event.timestamp,
                "data": event.data
            })

        event_bus = EventBus()
        event_bus.subscribe("prediction_*", pipeline_tracker)

        # 模拟预测流水线
        pipeline_events = [
            Event("prediction_requested", {"match_id": 456, "model": "v2.1"}, "api"),
            Event("data_collected", {"match_id": 456, "features_count": 150}, "data_service"),
            Event("model_executed", {"match_id": 456, "inference_time": 0.05}, "ml_service"),
            Event("prediction_generated", {"match_id": 456, "prediction": "draw", "confidence": 0.62}, "ml_service"),
            Event("prediction_validated", {"match_id": 456, "validation_passed": True}, "validator"),
            Event("prediction_stored", {"match_id": 456, "storage_id": "pred_789"}, "database"),
        ]

        for event in pipeline_events:
            await event_bus.publish(event)

        await asyncio.sleep(0.1)

        # 验证流水线完整性
        assert len(pipeline_stages) == 6
        assert pipeline_stages[0]["stage"] == "prediction_requested"
        assert pipeline_stages[-1]["stage"] == "prediction_stored"
        assert pipeline_stages[2]["data"]["inference_time"] == 0.05

    async def test_system_monitoring_events(self):
        """测试系统监控事件"""
        system_metrics = []

        async def metrics_collector(event: Event):
            system_metrics.append(event.data)

        event_bus = EventBus()
        event_bus.subscribe("system_*", metrics_collector)

        # 模拟系统监控事件
        monitoring_events = [
            Event("system_startup", {"service": "prediction_api", "version": "1.2.3"}, "system"),
            Event("system_health_check", {"cpu_usage": 45.2, "memory_usage": 67.8, "status": "healthy"}, "monitor"),
            Event("system_performance", {"avg_response_time": 120, "requests_per_second": 150}, "metrics"),
            Event("system_alert", {"type": "warning", "message": "High memory usage detected"}, "monitor"),
            Event("system_recovery", {"action": "memory_cleanup", "result": "success"}, "recovery"),
        ]

        for event in monitoring_events:
            await event_bus.publish(event)

        await asyncio.sleep(0.1)

        # 验证监控数据收集
        assert len(system_metrics) == 5
        assert system_metrics[1]["cpu_usage"] == 45.2
        assert system_metrics[3]["type"] == "warning"
        assert system_metrics[4]["action"] == "memory_cleanup"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])