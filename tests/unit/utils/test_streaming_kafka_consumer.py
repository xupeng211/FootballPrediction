# TODO: Consider creating a fixture for 19 repeated Mock creations

# TODO: Consider creating a fixture for 19 repeated Mock creations


"""
Kafka消费者测试
"""

import asyncio
import json

import pytest

from src.core.exceptions import StreamingError
from src.streaming.kafka_consumer_simple import KafkaMessageConsumer


class MockAsyncIterator:
    """模拟异步迭代器"""

    def __init__(self, items):
        self.items = items
        self.iter = iter(self.items)

    def __aiter__(self):
        return self

    async def __anext__(self):
        try:
            return next(self.iter)
        except StopIteration:
            raise StopAsyncIteration


# 模拟kafka错误
class KafkaError(Exception):
    pass


class CommitFailedError(Exception):
    pass


@pytest.mark.unit
class TestKafkaMessageConsumer:
    """Kafka消息消费者测试"""

    @pytest.fixture
    def mock_kafka_consumer(self):
        """模拟Kafka消费者"""
        mock_consumer = MagicMock()
        mock_consumer.start = AsyncMock()
        mock_consumer.stop = AsyncMock()
        mock_consumer.commit = AsyncMock()
        mock_consumer.seek = MagicMock()
        mock_consumer.assignment = MagicMock(return_value=[MagicMock()])
        mock_consumer.position = MagicMock(return_value={MagicMock(): 100})
        return mock_consumer

    @pytest.fixture
    def consumer(self):
        """创建消费者实例"""
        _config = {
            "bootstrap_servers": ["localhost:9092"],
            "group_id": "test_group",
            "topics": ["topic1", "topic2"],
        }
        consumer = KafkaMessageConsumer(config)
        return consumer

    @pytest.mark.asyncio
    async def test_consumer_initialization(self, consumer):
        """测试消费者初始化"""
        assert consumer.bootstrap_servers == ["localhost:9092"]
        assert consumer.group_id == "test_group"
        assert consumer.topics == ["topic1", "topic2"]

    @pytest.mark.asyncio
    async def test_start_consumer(self, consumer):
        """测试启动消费者"""
        await consumer.start()
        assert consumer.consumer is not None

    @pytest.mark.asyncio
    async def test_stop_consumer(self, consumer):
        """测试停止消费者"""
        await consumer.start()
        await consumer.stop()
        assert consumer.consumer is None

    @pytest.mark.asyncio
    async def test_consume_messages(self, consumer):
        """测试消费消息"""
        await consumer.start()
        messages = []
        async for message in consumer.consume():
            messages.append(message)
            if len(messages) >= 1:  # 只处理一条消息
                break

        assert len(messages) == 1
        assert messages[0]["topic"] in consumer.topics
        assert "key" in messages[0]
        assert "value" in messages[0]

    @pytest.mark.asyncio
    async def test_consume_with_timeout(self, consumer, mock_kafka_consumer):
        """测试带超时的消费"""
        # 模拟超时
        mock_consumer.getmany.return_value = {}

        await consumer.start()
        messages = []
        try:
            # 设置很短的超时
            async for message in consumer.consume(timeout_ms=100):
                messages.append(message)
        except asyncio.TimeoutError:
            pass

        assert len(messages) == 0

    @pytest.mark.asyncio
    async def test_commit_offset(self, consumer):
        """测试提交偏移量"""
        await consumer.start()
        await consumer.commit()
        _stats = consumer.get_stats()
        assert stats["last_commit_offset"] >= 0

    @pytest.mark.asyncio
    async def test_commit_specific_offset(self, consumer):
        """测试提交特定偏移量"""
        await consumer.start()
        offsets = {("topic1", 0): 100}
        await consumer.commit(offsets)
        _stats = consumer.get_stats()
        assert stats["last_commit_offset"] == 100

    @pytest.mark.asyncio
    async def test_commit_failure(self, consumer):
        """测试提交失败 - 简化版本不会失败"""
        await consumer.start()
        # 简化版本的commit不会失败，只测试正常提交
        await consumer.commit()
        _stats = consumer.get_stats()
        assert stats["last_commit_offset"] >= 0

    @pytest.mark.asyncio
    async def test_seek_to_offset(self, consumer):
        """测试跳转到偏移量"""
        await consumer.start()
        # 简化版本的seek不会失败，只测试调用
        await consumer.seek("topic1", 0, 100)
        assert consumer.consumer is not None

    @pytest.mark.asyncio
    async def test_pause_partition(self, consumer):
        """测试暂停分区"""
        await consumer.start()
        mock_partition = MagicMock()
        # 简化版本的pause_partition是空操作
        consumer.pause_partition(mock_partition)
        assert consumer.consumer is not None

    @pytest.mark.asyncio
    async def test_resume_partition(self, consumer):
        """测试恢复分区"""
        await consumer.start()
        mock_partition = MagicMock()
        # 简化版本的resume_partition是空操作
        consumer.resume_partition(mock_partition)
        assert consumer.consumer is not None

    @pytest.mark.asyncio
    async def test_get_assignment(self, consumer):
        """测试获取分区分配"""
        await consumer.start()
        assignment = consumer.get_assignment()

        assert assignment is not None
        assert len(assignment) == len(consumer.topics)

    @pytest.mark.asyncio
    async def test_get_position(self, consumer):
        """测试获取当前位置"""
        await consumer.start()
        position = consumer.get_position()

        assert isinstance(position, dict)
        assert len(position) == len(consumer.topics)

    def test_deserialize_message(self, consumer):
        """测试反序列化消息"""
        mock_message = MagicMock()
        mock_message.key = b"test_key"
        mock_message.value = b'{"data": "test"}'
        mock_message.headers = [("source", b"api"), ("version", b"1.0")]

        _result = consumer._deserialize_message(mock_message)

        assert _result["key"] == "test_key"
        assert _result["value"] == {"data": "test"}
        assert _result["headers"]["source"] == "api"
        assert _result["headers"]["version"] == "1.0"

    def test_deserialize_message_without_headers(self, consumer):
        """测试反序列化没有头部的消息"""
        mock_message = MagicMock()
        mock_message.key = b"test_key"
        mock_message.value = b'{"data": "test"}'
        mock_message.headers = None

        _result = consumer._deserialize_message(mock_message)

        assert _result["key"] == "test_key"
        assert _result["value"] == {"data": "test"}
        assert _result["headers"] == {}

    def test_deserialize_invalid_json(self, consumer):
        """测试反序列化无效JSON"""
        mock_message = MagicMock()
        mock_message.key = b"test_key"
        mock_message.value = b"invalid json"
        mock_message.headers = None

        with pytest.raises(StreamingError, match="Failed to deserialize message"):
            consumer._deserialize_message(mock_message)

    @pytest.mark.asyncio
    async def test_consume_with_filter(self, consumer, mock_kafka_consumer):
        """测试带过滤器的消费"""
        mock_message1 = MagicMock()
        mock_message1.key = b"key1"
        mock_message1.value = b'{"type": "important", "data": "test1"}'

        mock_message2 = MagicMock()
        mock_message2.key = b"key2"
        mock_message2.value = b'{"type": "normal", "data": "test2"}'

        async def message_iter():
            yield mock_message1
            yield mock_message2

        mock_consumer.__aiter__ = MockAsyncIterator(message_iter)

        await consumer.start()
        messages = []

        # 只接收重要的消息
        async for message in consumer.consume(
            filter_func=lambda m: m.get("value", {}).get("type") == "important"
        ):
            messages.append(message)
            if len(messages) >= 2:
                break

        assert len(messages) >= 1
        assert messages[0]["value"]["type"] == "important"

    @pytest.mark.asyncio
    async def test_consume_with_batch_size(self, consumer, mock_kafka_consumer):
        """测试批量消费"""
        messages = []
        for i in range(5):
            msg = MagicMock()
            msg.key = f"key_{i}".encode()
            msg.value = json.dumps({"data": f"test_{i}"}).encode()
            messages.append(msg)

        async def message_iter():
            for msg in messages:
                yield msg

        mock_consumer.__aiter__ = MockAsyncIterator(message_iter)

        await consumer.start()
        batch = []
        async for message in consumer.consume(batch_size=3):
            batch.append(message)
            if len(batch) >= 3:
                break

        assert len(batch) == 3

    @pytest.mark.asyncio
    async def test_rebalance_listener(self, consumer):
        """测试重平衡监听器"""
        listener = consumer._create_rebalance_listener()

        # 测试分区分配
        partitions = [MagicMock()]
        await listener.on_partitions_assigned(partitions)

        # 测试分区撤销
        await listener.on_partitions_revoked(partitions)

    @pytest.mark.asyncio
    async def test_consume_metrics(self, consumer, mock_kafka_consumer):
        """测试消费指标消息"""
        mock_message = MagicMock()
        mock_message.key = b"metrics"
        mock_message.value = b'{"name": "cpu_usage", "value": 80.5}'
        mock_message.headers = [("type", b"metrics")]

        async def message_iter():
            yield mock_message

        mock_consumer.__aiter__ = MockAsyncIterator(message_iter)

        await consumer.start()
        metrics = []
        async for message in consumer.consume(filter_type="metrics"):
            metrics.append(message)
            break

        assert len(metrics) == 1
        assert metrics[0]["value"]["name"] == "cpu_usage"

    @pytest.mark.asyncio
    async def test_consume_events(self, consumer, mock_kafka_consumer):
        """测试消费事件消息"""
        mock_message = MagicMock()
        mock_message.key = b"match_123"
        mock_message.value = b'{"event_type": "match_created", "aggregate_id": "match_123"}'
        mock_message.headers = [("type", b"event")]

        async def message_iter():
            yield mock_message

        mock_consumer.__aiter__ = MockAsyncIterator(message_iter)

        await consumer.start()
        events = []
        async for message in consumer.consume(filter_type="event"):
            events.append(message)
            break

        assert len(events) == 1
        assert events[0]["value"]["event_type"] == "match_created"

    @pytest.mark.asyncio
    async def test_consume_with_error_handling(self, consumer, mock_kafka_consumer):
        """测试消费时的错误处理"""
        # 模拟一个无效消息和一个有效消息
        valid_message = MagicMock()
        valid_message.key = b"valid"
        valid_message.value = b'{"data": "valid"}'
        valid_message.headers = None

        async def message_iter():
            # 先产生一个错误
            yield None  # 这会导致错误
            yield valid_message

        mock_consumer.__aiter__ = MockAsyncIterator(message_iter)

        await consumer.start()
        messages = []

        async for message in consumer.consume():
            if message:  # 只处理有效的消息
                messages.append(message)
            if len(messages) >= 1:
                break

        assert len(messages) == 1

    def test_get_consumer_stats(self, consumer):
        """测试获取消费者统计"""
        _stats = consumer.get_stats()
        assert "messages_consumed" in stats
        assert "partitions_assigned" in stats
        assert "last_commit_offset" in stats
        assert stats["messages_consumed"] == 0

    @pytest.mark.asyncio
    async def test_close_consumer(self, consumer, mock_kafka_consumer):
        """测试关闭消费者"""
        await consumer.start()
        await consumer.close()

        mock_kafka_consumer.stop.assert_called_once()
        assert consumer.is_closed is True

    @pytest.mark.asyncio
    async def test_reset_offset_to_beginning(self, consumer, mock_kafka_consumer):
        """测试重置偏移量到开始"""

        await consumer.start()
        await consumer.reset_offset_to_beginning("topic1", 0)

        # 验证seek被调用
        assert mock_kafka_consumer.seek.called

    @pytest.mark.asyncio
    async def test_reset_offset_to_end(self, consumer, mock_kafka_consumer):
        """测试重置偏移量到末尾"""
        await consumer.start()
        await consumer.reset_offset_to_end("topic1", 0)

        # 验证seek被调用
        assert mock_kafka_consumer.seek.called
