# TODO: Consider creating a fixture for 8 repeated Mock creations

# TODO: Consider creating a fixture for 8 repeated Mock creations

from unittest.mock import AsyncMock, MagicMock, patch

"""
流处理器测试
"""

import asyncio
import json
from datetime import datetime, timedelta
from typing import Any, AsyncGenerator, Callable, Dict, List, Optional

import pytest

from src.core.exceptions import StreamingError
from src.streaming.stream_processor_simple import (BatchProcessor,
                                                   MessageProcessor,
                                                   StreamProcessor)


class AsyncIterator:
    """模拟异步迭代器"""

    def __init__(self, items):
        self.items = items
        self.index = 0

    def __call__(self):
        return self

    def __aiter__(self):
        return self

    async def __anext__(self):
        if self.index >= len(self.items):
            raise StopAsyncIteration
        item = self.items[self.index]
        self.index += 1
        return item


@pytest.mark.unit
class TestStreamProcessor:
    """流处理器基础测试"""

    @pytest.fixture
    def mock_consumer(self):
        """模拟消费者"""
        consumer = AsyncMock()
        consumer.start = AsyncMock()
        consumer.stop = AsyncMock()
        consumer.commit = AsyncMock()
        return consumer

    @pytest.fixture
    def mock_producer(self):
        """模拟生产者"""
        producer = AsyncMock()
        producer.start = AsyncMock()
        producer.stop = AsyncMock()
        producer.send_message = AsyncMock()
        return producer

    @pytest.fixture
    def processor(self, mock_consumer, mock_producer):
        """创建流处理器实例"""
        return StreamProcessor(
            consumer=mock_consumer,
            producer=mock_producer,
            input_topics=["input_topic"],
            output_topics=["output_topic"],
        )

    @pytest.mark.asyncio
    async def test_processor_initialization(self, processor):
        """测试处理器初始化"""
        assert processor.input_topics == ["input_topic"]
        assert processor.output_topics == ["output_topic"]
        assert processor.consumer is not None
        assert processor.producer is not None

    @pytest.mark.asyncio
    async def test_processor_start_stop(self, processor, mock_consumer, mock_producer):
        """测试启动和停止处理器"""
        await processor.start()
        mock_consumer.start.assert_called_once()
        mock_producer.start.assert_called_once()

        await processor.stop()
        mock_consumer.stop.assert_called_once()
        mock_producer.stop.assert_called_once()

    @pytest.mark.asyncio
    async def test_process_message(self, processor):
        """测试处理消息"""
        # 模拟输入消息
        input_message = {
            "key": "test_key",
            "value": {"data": "test"},
            "topic": "input_topic",
            "partition": 0,
            "offset": 100,
        }

        # 定义处理函数
        async def process_func(msg):
            return {
                "key": msg["key"],
                "value": {"processed": True, "original": msg["value"]},
                "topic": "output_topic",
            }

        # 模拟消费和生产
        processor.consumer.consume.return_value = AsyncIterator([input_message])()
        processor.producer.send_message.return_value = True

        # 启动处理
        processed_count = 0
        async for output in processor.process(process_func, max_messages=1):
            processed_count += 1
            assert output["key"] == "test_key"
            assert output["value"]["processed"] is True

        assert processed_count == 1

    @pytest.mark.asyncio
    async def test_process_with_error_handling(self, processor):
        """测试处理时的错误处理"""
        input_message = {
            "key": "error_key",
            "value": {"data": "error"},
            "topic": "input_topic",
        }

        # 定义会抛出异常的处理函数
        async def failing_process(msg):
            if msg["key"] == "error_key":
                raise ValueError("Processing failed")
            return {"key": msg["key"], "value": {"processed": True}}

        processor.consumer.consume.return_value = AsyncIterator([input_message])()

        # 捕获错误
        errors = []
        async for output in processor.process(
            failing_process, max_messages=1, error_handler=lambda e, m: errors.append(e)
        ):
            pass

        assert len(errors) == 1
        assert isinstance(errors[0], ValueError)

    @pytest.mark.asyncio
    async def test_batch_processing(self, processor):
        """测试批量处理"""
        # 模拟多个输入消息
        messages = [
            {"key": f"key_{i}", "value": {"data": f"test_{i}"}, "topic": "input_topic"}
            for i in range(5)
        ]

        # 定义批量处理函数
        async def batch_process(batch):
            return {
                "batch_size": len(batch),
                "items": [
                    {"key": msg["key"], "value": {"batched": True}} for msg in batch
                ],
            }

        processor.consumer.consume.return_value = AsyncIterator(messages)()

        # 批量处理
        batches = []
        async for batch in processor.process_batch(batch_process, batch_size=3):
            batches.append(batch)

        assert len(batches) >= 1
        assert batches[0]["batch_size"] <= 3

    @pytest.mark.asyncio
    async def test_transform_message(self, processor):
        """测试消息转换"""
        # 定义转换规则
        transformation = {
            "mapping": {"user_id": "id", "user_name": "name"},
            "filters": ["status", "timestamp"],
        }

        input_message = {
            "key": "user_123",
            "value": {
                "id": 123,
                "name": "John Doe",
                "email": "john@example.com",
                "status": "active",
                "timestamp": "2024-01-01T00:00:00Z",
            },
        }

        # 应用转换
        output = await processor.transform_message(input_message, transformation)

        assert output["key"] == "user_123"
        assert "id" in output["value"]
        assert "name" in output["value"]
        assert "email" not in output["value"]  # 被过滤

    @pytest.mark.asyncio
    async def test_aggregation_processing(self, processor):
        """测试聚合处理"""
        # 模拟相关消息
        messages = [
            {
                "key": "match_123",
                "value": {"event": "goal", "team": "A"},
                "topic": "input_topic",
            },
            {
                "key": "match_123",
                "value": {"event": "goal", "team": "B"},
                "topic": "input_topic",
            },
            {
                "key": "match_456",
                "value": {"event": "goal", "team": "C"},
                "topic": "input_topic",
            },
        ]

        # 定义聚合函数
        async def aggregate_by_key(key, aggregated_messages):
            events = [msg["value"]["event"] for msg in aggregated_messages]
            return {
                "key": key,
                "value": {
                    "match_id": key,
                    "total_goals": len(events),
                    "events": events,
                },
            }

        processor.consumer.consume.return_value = AsyncIterator(messages)()

        # 执行聚合
        aggregations = []
        async for agg in processor.aggregate(
            aggregate_by_key,
            window_size=timedelta(seconds=10),
            key_extractor=lambda m: m["key"],
        ):
            aggregations.append(agg)

        assert len(aggregations) >= 1
        assert any(agg["value"]["match_id"] == "match_123" for agg in aggregations)

    @pytest.mark.asyncio
    async def test_filter_messages(self, processor):
        """测试消息过滤"""
        messages = [
            {"key": "1", "value": {"priority": "high", "data": "important"}},
            {"key": "2", "value": {"priority": "low", "data": "normal"}},
            {"key": "3", "value": {"priority": "high", "data": "urgent"}},
        ]

        # 定义过滤条件
        def filter_high_priority(msg):
            return msg["value"].get("priority") == "high"

        processor.consumer.consume.return_value = AsyncIterator(messages)()

        # 过滤消息
        filtered = []
        async for msg in processor.filter(filter_high_priority):
            filtered.append(msg)

        assert len(filtered) == 2
        assert all(msg["value"]["priority"] == "high" for msg in filtered)

    @pytest.mark.asyncio
    async def test_join_streams(self, processor):
        """测试流连接"""
        # 模拟两个流的输入
        stream1 = [{"key": "user_123", "value": {"name": "John"}, "topic": "stream1"}]
        stream2 = [{"key": "user_123", "value": {"age": 30}, "topic": "stream2"}]

        # 定义连接函数
        async def join_streams(msg1, msg2):
            if msg1 and msg2:
                return {
                    "key": msg1["key"],
                    "value": {
                        "name": msg1["value"]["name"],
                        "age": msg2["value"]["age"],
                    },
                }
            return None

        processor.consumer.consume.side_effect = [
            AsyncIterator(stream1)(),
            AsyncIterator(stream2)(),
        ]

        # 执行连接
        joins = []
        async for joined in processor.join(
            "stream1", "stream2", join_streams, window=timedelta(seconds=5)
        ):
            if joined:
                joins.append(joined)

        assert len(joins) >= 1
        if joins:
            assert joins[0]["value"]["name"] == "John"
            assert joins[0]["value"]["age"] == 30

    def test_processor_metrics(self, processor):
        """测试处理器指标"""
        metrics = processor.get_metrics()
        assert "messages_processed" in metrics
        assert "messages_failed" in metrics
        assert "processing_time" in metrics
        assert metrics["messages_processed"] == 0

    @pytest.mark.asyncio
    async def test_processor_with_dead_letter_queue(self, processor):
        """测试死信队列"""
        # 失败的消息
        failed_message = {
            "key": "failed",
            "value": {"data": "error"},
            "topic": "input_topic",
        }

        async def failing_process(msg):
            raise ValueError("Cannot process")

        processor.consumer.consume.return_value = AsyncIterator([failed_message])()
        processor.producer.send_message.return_value = True

        # 使用死信队列
        dlq_messages = []
        async for output in processor.process(
            failing_process, dead_letter_topic="dlq_topic", max_messages=1
        ):
            if output.get("dlq"):
                dlq_messages.append(output)

        assert len(dlq_messages) == 1
        assert dlq_messages[0]["topic"] == "dlq_topic"

    @pytest.mark.asyncio
    async def test_stateful_processing(self, processor):
        """测试有状态处理"""
        # 定义状态管理
        state = {}

        async def stateful_process(msg):
            key = msg["key"]
            count = state.get(key, 0) + 1
            state[key] = count
            return {"key": key, "value": {"count": count, "data": msg["value"]}}

        # 模拟相同key的多个消息
        messages = [
            {"key": "user_1", "value": {"action": "login"}},
            {"key": "user_1", "value": {"action": "view"}},
            {"key": "user_2", "value": {"action": "login"}},
        ]

        processor.consumer.consume.return_value = AsyncIterator(messages)()

        # 处理消息
        results = []
        async for output in processor.process(stateful_process, max_messages=3):
            results.append(output)

        # 验证状态
        user1_results = [r for r in results if r["key"] == "user_1"]
        assert len(user1_results) == 2
        assert user1_results[0]["value"]["count"] == 1
        assert user1_results[1]["value"]["count"] == 2

    @pytest.mark.asyncio
    async def test_windowed_processing(self, processor):
        """测试窗口处理"""
        messages = [
            {
                "key": "1",
                "value": {"value": 10},
                "timestamp": datetime(2024, 1, 1, 12, 0, 0),
            },
            {
                "key": "2",
                "value": {"value": 20},
                "timestamp": datetime(2024, 1, 1, 12, 0, 30),
            },
            {
                "key": "3",
                "value": {"value": 30},
                "timestamp": datetime(2024, 1, 1, 12, 2, 0),
            },
        ]

        async def window_aggregate(window):
            values = [msg["value"]["value"] for msg in window]
            return {
                "window_start": min(msg["timestamp"] for msg in window),
                "window_end": max(msg["timestamp"] for msg in window),
                "sum": sum(values),
                "count": len(values),
            }

        processor.consumer.consume.return_value = AsyncIterator(messages)()

        # 1分钟窗口
        windows = []
        async for window in processor.process_windowed(
            window_aggregate,
            window_size=timedelta(minutes=1),
            timestamp_extractor=lambda m: m["timestamp"],
        ):
            windows.append(window)

        assert len(windows) >= 1
        if windows:
            assert windows[0]["count"] >= 1


class TestMessageProcessor:
    """消息处理器测试"""

    def test_message_processor_creation(self):
        """测试创建消息处理器"""
        processor = MessageProcessor(
            name="test_processor", input_topic="input", output_topic="output"
        )

        assert processor.name == "test_processor"
        assert processor.input_topic == "input"
        assert processor.output_topic == "output"

    def test_add_handler(self):
        """测试添加处理器"""
        processor = MessageProcessor(name="test")

        async def handler(msg):
            return {"processed": True}

        processor.add_handler("test_event", handler)
        assert "test_event" in processor.handlers
        assert processor.handlers["test_event"] == handler

    def test_remove_handler(self):
        """测试移除处理器"""
        processor = MessageProcessor(name="test")

        async def handler(msg):
            return {"processed": True}

        processor.add_handler("test_event", handler)
        processor.remove_handler("test_event")
        assert "test_event" not in processor.handlers

    def test_get_handler(self):
        """测试获取处理器"""
        processor = MessageProcessor(name="test")

        async def handler(msg):
            return {"processed": True}

        processor.add_handler("test_event", handler)
        retrieved = processor.get_handler("test_event")
        assert retrieved is handler

        # 测试不存在的处理器
        assert processor.get_handler("nonexistent") is None


class TestBatchProcessor:
    """批量处理器测试"""

    @pytest.fixture
    def batch_processor(self):
        """创建批量处理器"""
        return BatchProcessor(name="batch_processor", batch_size=10, batch_timeout=5.0)

    def test_batch_processor_initialization(self, batch_processor):
        """测试批量处理器初始化"""
        assert batch_processor.name == "batch_processor"
        assert batch_processor.batch_size == 10
        assert batch_processor.batch_timeout == 5.0
        assert len(batch_processor.current_batch) == 0

    def test_add_to_batch(self, batch_processor):
        """测试添加到批次"""
        message = {"key": "1", "value": {"data": "test"}}
        batch_processor.add_to_batch(message)

        assert len(batch_processor.current_batch) == 1
        assert batch_processor.current_batch[0] == message

    def test_batch_is_full(self, batch_processor):
        """测试批次是否已满"""
        # 添加9个消息
        for i in range(9):
            batch_processor.add_to_batch({"key": str(i), "value": {}})

        assert batch_processor.is_batch_ready() is False

        # 添加第10个消息
        batch_processor.add_to_batch({"key": "9", "value": {}})
        assert batch_processor.is_batch_ready() is True

    def test_clear_batch(self, batch_processor):
        """测试清空批次"""
        batch_processor.add_to_batch({"key": "1", "value": {}})
        batch_processor.add_to_batch({"key": "2", "value": {}})

        assert len(batch_processor.current_batch) == 2

        batch_processor.clear_batch()
        assert len(batch_processor.current_batch) == 0

    def test_get_batch_metrics(self, batch_processor):
        """测试获取批次指标"""
        metrics = batch_processor.get_metrics()
        assert "current_batch_size" in metrics
        assert "batches_processed" in metrics
        assert "total_messages_processed" in metrics
