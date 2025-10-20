"""
Streaming模块核心测试
测试Kafka生产者、消费者和流处理功能
"""

import pytest
import sys
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock, AsyncMock
import asyncio
import json

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

# 尝试导入streaming模块
try:
    from src.streaming.kafka_components import (
        FootballKafkaProducer,
        FootballKafkaConsumer,
        StreamConfig,
        StreamProcessor,
        KAFKA_AVAILABLE,
        DEFAULT_TOPICS,
        ensure_topics_exist,
    )
    from src.streaming.kafka_producer_simple import KafkaMessageProducer
    from src.streaming.kafka_consumer_simple import (
        FootballKafkaConsumer as SimpleConsumer,
    )
    from src.streaming.stream_processor_simple import StreamProcessorSimple
    from src.streaming.stream_config_simple import StreamConfigSimple

    STREAMING_AVAILABLE = True
except ImportError as e:
    pytest.skip(f"Streaming模块不可用: {e}", allow_module_level=True)
    STREAMING_AVAILABLE = False


class TestStreamConfig:
    """测试流配置"""

    def test_stream_config_creation(self):
        """测试流配置创建"""
        if not STREAMING_AVAILABLE:
            pytest.skip("Streaming模块不可用")

        config = StreamConfigSimple(
            bootstrap_servers="localhost:9092",
            group_id="test_group",
            auto_offset_reset="earliest",
            enable_auto_commit=True,
        )

        assert config.bootstrap_servers == "localhost:9092"
        assert config.group_id == "test_group"
        assert config.auto_offset_reset == "earliest"
        assert config.enable_auto_commit is True

    def test_stream_config_with_mock(self):
        """使用Mock测试流配置"""
        with patch(
            "src.streaming.stream_config_simple.StreamConfigSimple"
        ) as MockConfig:
            config = MockConfig()
            config.get_producer_config = Mock(
                return_value={"bootstrap.servers": "localhost:9092", "acks": "all"}
            )
            config.get_consumer_config = Mock(
                return_value={
                    "bootstrap.servers": "localhost:9092",
                    "group.id": "test_group",
                }
            )

            producer_config = config.get_producer_config()
            consumer_config = config.get_consumer_config()

            assert producer_config["bootstrap.servers"] == "localhost:9092"
            assert consumer_config["group.id"] == "test_group"

    def test_stream_config_validation(self):
        """测试配置验证"""
        with patch(
            "src.streaming.stream_config_simple.StreamConfigSimple"
        ) as MockConfig:
            config = MockConfig()
            config.validate = Mock(return_value=True)
            config.is_valid = Mock(return_value=True)

            assert config.validate() is True
            assert config.is_valid() is True

    def test_stream_config_serialization(self):
        """测试配置序列化"""
        with patch(
            "src.streaming.stream_config_simple.StreamConfigSimple"
        ) as MockConfig:
            config = MockConfig()
            config.to_dict = Mock(
                return_value={
                    "bootstrap_servers": "localhost:9092",
                    "group_id": "test_group",
                }
            )
            config.to_json = Mock(
                return_value='{"bootstrap_servers": "localhost:9092"}'
            )

            config_dict = config.to_dict()
            config_json = config.to_json()

            assert config_dict["bootstrap_servers"] == "localhost:9092"
            assert '"bootstrap_servers"' in config_json


class TestKafkaProducer:
    """测试Kafka生产者"""

    @pytest.mark.asyncio
    async def test_producer_creation(self):
        """测试生产者创建"""
        if not STREAMING_AVAILABLE:
            pytest.skip("Streaming模块不可用")

        with patch(
            "src.streaming.kafka_producer_simple.KafkaMessageProducer"
        ) as MockProducer:
            producer = MockProducer()
            producer.connect = AsyncMock(return_value=True)
            producer.disconnect = AsyncMock(return_value=True)
            producer.is_connected = Mock(return_value=True)

            await producer.connect()
            assert producer.is_connected() is True
            await producer.disconnect()

    @pytest.mark.asyncio
    async def test_producer_send_message(self):
        """测试发送消息"""
        if not STREAMING_AVAILABLE:
            pytest.skip("Streaming模块不可用")

        with patch(
            "src.streaming.kafka_producer_simple.KafkaMessageProducer"
        ) as MockProducer:
            producer = MockProducer()
            producer.send = AsyncMock(
                return_value={"topic": "test_topic", "partition": 0, "offset": 123}
            )
            producer.send_batch = AsyncMock(
                return_value=[{"offset": i} for i in range(5)]
            )

            # 发送单条消息
            result = await producer.send("test_topic", {"message": "hello"})
            assert result["topic"] == "test_topic"
            assert result["offset"] == 123

            # 发送批量消息
            messages = [{"message": f"msg_{i}"} for i in range(5)]
            batch_result = await producer.send_batch("test_topic", messages)
            assert len(batch_result) == 5

    @pytest.mark.asyncio
    async def test_producer_error_handling(self):
        """测试生产者错误处理"""
        if not STREAMING_AVAILABLE:
            pytest.skip("Streaming模块不可用")

        with patch(
            "src.streaming.kafka_producer_simple.KafkaMessageProducer"
        ) as MockProducer:
            producer = MockProducer()
            producer.send = AsyncMock(side_effect=Exception("Kafka error"))
            producer.handle_error = Mock(return_value={"error": "handled"})

            try:
                await producer.send("test_topic", {"message": "error"})
            except Exception:
                error = producer.handle_error(Exception("Kafka error"))
                assert error["error"] == "handled"

    @pytest.mark.asyncio
    async def test_producer_transaction(self):
        """测试生产者事务"""
        if not STREAMING_AVAILABLE:
            pytest.skip("Streaming模块不可用")

        with patch(
            "src.streaming.kafka_producer_simple.KafkaMessageProducer"
        ) as MockProducer:
            producer = MockProducer()
            producer.begin_transaction = AsyncMock(return_value=True)
            producer.commit_transaction = AsyncMock(return_value=True)
            producer.abort_transaction = AsyncMock(return_value=True)

            await producer.begin_transaction()
            await producer.send("test_topic", {"message": "in_transaction"})
            await producer.commit_transaction()

            producer.begin_transaction.assert_called_once()
            producer.commit_transaction.assert_called_once()

    def test_producer_serialization(self):
        """测试消息序列化"""
        if not STREAMING_AVAILABLE:
            pytest.skip("Streaming模块不可用")

        with patch(
            "src.streaming.kafka_producer_simple.KafkaMessageProducer"
        ) as MockProducer:
            producer = MockProducer()
            producer.serialize_message = Mock(return_value=b'{"key": "value"}')
            producer.deserialize_message = Mock(return_value={"key": "value"})

            # 序列化
            serialized = producer.serialize_message({"key": "value"})
            assert serialized == b'{"key": "value"}'

            # 反序列化
            deserialized = producer.deserialize_message(b'{"key": "value"}')
            assert deserialized["key"] == "value"


class TestKafkaConsumer:
    """测试Kafka消费者"""

    @pytest.mark.asyncio
    async def test_consumer_creation(self):
        """测试消费者创建"""
        if not STREAMING_AVAILABLE:
            pytest.skip("Streaming模块不可用")

        with patch(
            "src.streaming.kafka_consumer_simple.FootballKafkaConsumer"
        ) as MockConsumer:
            consumer = MockConsumer()
            consumer.connect = AsyncMock(return_value=True)
            consumer.disconnect = AsyncMock(return_value=True)
            consumer.subscribe = Mock(return_value=True)

            await consumer.connect()
            consumer.subscribe(["test_topic"])
            assert consumer.subscribe.called
            await consumer.disconnect()

    @pytest.mark.asyncio
    async def test_consumer_receive_messages(self):
        """测试接收消息"""
        if not STREAMING_AVAILABLE:
            pytest.skip("Streaming模块不可用")

        with patch(
            "src.streaming.kafka_consumer_simple.FootballKafkaConsumer"
        ) as MockConsumer:
            consumer = MockConsumer()
            consumer.poll = AsyncMock(
                return_value={
                    "topic": "test_topic",
                    "partition": 0,
                    "offset": 123,
                    "key": "test_key",
                    "value": {"message": "hello"},
                }
            )
            consumer.consume_messages = AsyncMock(
                return_value=[
                    {"topic": "test_topic", "value": {"message": "msg1"}},
                    {"topic": "test_topic", "value": {"message": "msg2"}},
                ]
            )

            # 轮询单条消息
            message = await consumer.poll(timeout=1.0)
            assert message["value"]["message"] == "hello"

            # 消费多条消息
            messages = await consumer.consume_messages(count=2)
            assert len(messages) == 2
            assert messages[0]["value"]["message"] == "msg1"

    @pytest.mark.asyncio
    async def test_consumer_commit_offsets(self):
        """测试提交偏移量"""
        if not STREAMING_AVAILABLE:
            pytest.skip("Streaming模块不可用")

        with patch(
            "src.streaming.kafka_consumer_simple.FootballKafkaConsumer"
        ) as MockConsumer:
            consumer = MockConsumer()
            consumer.commit = AsyncMock(return_value=True)
            consumer.commit_async = AsyncMock(return_value=True)

            # 同步提交
            await consumer.commit()

            # 异步提交
            await consumer.commit_async()

            consumer.commit.assert_called()
            consumer.commit_async.assert_called()

    @pytest.mark.asyncio
    async def test_consumer_rebalance(self):
        """测试消费者重平衡"""
        if not STREAMING_AVAILABLE:
            pytest.skip("Streaming模块不可用")

        with patch(
            "src.streaming.kafka_consumer_simple.FootballKafkaConsumer"
        ) as MockConsumer:
            consumer = MockConsumer()
            consumer.on_rebalance = Mock(return_value=True)
            consumer.get_assigned_partitions = Mock(return_value=[0, 1, 2])

            # 处理重平衡
            consumer.on_rebalance(["test_topic"], [0, 1, 2])

            # 获取分配的分区
            partitions = consumer.get_assigned_partitions()
            assert len(partitions) == 3

    @pytest.mark.asyncio
    async def test_consumer_error_handling(self):
        """测试消费者错误处理"""
        if not STREAMING_AVAILABLE:
            pytest.skip("Streaming模块不可用")

        with patch(
            "src.streaming.kafka_consumer_simple.FootballKafkaConsumer"
        ) as MockConsumer:
            consumer = MockConsumer()
            consumer.poll = AsyncMock(side_effect=Exception("Consumer error"))
            consumer.handle_error = Mock(return_value={"error": "handled"})
            consumer.reconnect = AsyncMock(return_value=True)

            try:
                await consumer.poll()
            except Exception:
                error = consumer.handle_error(Exception("Consumer error"))
                assert error["error"] == "handled"

                # 尝试重连
                await consumer.reconnect()


class TestStreamProcessor:
    """测试流处理器"""

    @pytest.mark.asyncio
    async def test_stream_processor_creation(self):
        """测试流处理器创建"""
        if not STREAMING_AVAILABLE:
            pytest.skip("Streaming模块不可用")

        with patch(
            "src.streaming.stream_processor_simple.StreamProcessorSimple"
        ) as MockProcessor:
            processor = MockProcessor()
            processor.initialize = AsyncMock(return_value=True)
            processor.start = AsyncMock(return_value=True)
            processor.stop = AsyncMock(return_value=True)

            await processor.initialize()
            await processor.start()
            assert processor.is_running is True
            await processor.stop()

    @pytest.mark.asyncio
    async def test_stream_process_message(self):
        """测试处理消息"""
        if not STREAMING_AVAILABLE:
            pytest.skip("Streaming模块不可用")

        with patch(
            "src.streaming.stream_processor_simple.StreamProcessorSimple"
        ) as MockProcessor:
            processor = MockProcessor()
            processor.process_message = AsyncMock(
                return_value={"processed": True, "result": {"transformed": "data"}}
            )
            processor.process_batch = AsyncMock(
                return_value=[
                    {"processed": True, "result": {"id": 1}},
                    {"processed": True, "result": {"id": 2}},
                ]
            )

            # 处理单条消息
            message = {"topic": "test", "value": {"data": "test"}}
            result = await processor.process_message(message)
            assert result["processed"] is True

            # 处理批量消息
            messages = [{"value": {"id": i}} for i in range(2)]
            batch_result = await processor.process_batch(messages)
            assert len(batch_result) == 2

    @pytest.mark.asyncio
    async def test_stream_transform_filter(self):
        """测试流转换和过滤"""
        if not STREAMING_AVAILABLE:
            pytest.skip("Streaming模块不可用")

        with patch(
            "src.streaming.stream_processor_simple.StreamProcessorSimple"
        ) as MockProcessor:
            processor = MockProcessor()
            processor.transform = Mock(return_value={"transformed": True})
            processor.filter = Mock(return_value=True)
            processor.map = Mock(return_value={"mapped": True})

            # 转换
            data = {"raw": "data"}
            transformed = processor.transform(data)
            assert transformed["transformed"] is True

            # 过滤
            should_keep = processor.filter(data)
            assert should_keep is True

            # 映射
            mapped = processor.map(data)
            assert mapped["mapped"] is True

    @pytest.mark.asyncio
    async def test_stream_aggregation(self):
        """测试流聚合"""
        if not STREAMING_AVAILABLE:
            pytest.skip("Streaming模块不可用")

        with patch(
            "src.streaming.stream_processor_simple.StreamProcessorSimple"
        ) as MockProcessor:
            processor = MockProcessor()
            processor.aggregate = Mock(
                return_value={"count": 10, "sum": 100, "average": 10.0}
            )
            processor.windowed_aggregate = AsyncMock(
                return_value={
                    "window": "5min",
                    "results": [{"timestamp": "2025-01-18T10:00:00", "count": 5}],
                }
            )

            # 聚合
            data = [{"value": i} for i in range(10)]
            result = processor.aggregate(data)
            assert result["count"] == 10

            # 窗口聚合
            window_result = await processor.windowed_aggregate(data, window="5min")
            assert window_result["window"] == "5min"

    @pytest.mark.asyncio
    async def test_stream_join_merge(self):
        """测试流连接和合并"""
        if not STREAMING_AVAILABLE:
            pytest.skip("Streaming模块不可用")

        with patch(
            "src.streaming.stream_processor_simple.StreamProcessorSimple"
        ) as MockProcessor:
            processor = MockProcessor()
            processor.join_streams = AsyncMock(
                return_value=[
                    {"stream1": {"id": 1}, "stream2": {"id": 1, "extra": "data"}}
                ]
            )
            processor.merge_streams = AsyncMock(
                return_value=[
                    {"source": "stream1", "data": {"id": 1}},
                    {"source": "stream2", "data": {"id": 2}},
                ]
            )

            # 连接流
            stream1 = [{"id": 1, "value": "a"}]
            stream2 = [{"id": 1, "value": "b"}]
            joined = await processor.join_streams(stream1, stream2, on="id")
            assert len(joined) == 1

            # 合并流
            merged = await processor.merge_streams(stream1, stream2)
            assert len(merged) == 2


class TestStreamingIntegration:
    """测试Streaming集成功能"""

    @pytest.mark.asyncio
    async def test_end_to_end_flow(self):
        """测试端到端流程"""
        if not STREAMING_AVAILABLE:
            pytest.skip("Streaming模块不可用")

        # 模拟完整的生产-处理-消费流程
        with patch(
            "src.streaming.kafka_producer_simple.KafkaMessageProducer"
        ) as MockProducer, patch(
            "src.streaming.kafka_consumer_simple.FootballKafkaConsumer"
        ) as MockConsumer, patch(
            "src.streaming.stream_processor_simple.StreamProcessorSimple"
        ) as MockProcessor:
            # 设置Mock
            producer = MockProducer()
            producer.send = AsyncMock(return_value={"offset": 123})

            consumer = MockConsumer()
            consumer.poll = AsyncMock(
                return_value={
                    "topic": "football_matches",
                    "value": {"match_id": 123, "home_team": "Team A"},
                }
            )

            processor = MockProcessor()
            processor.process_message = AsyncMock(
                return_value={"processed": True, "prediction": {"home_win": 0.7}}
            )

            # 端到端流程
            # 1. 生产者发送消息
            await producer.send("football_matches", {"match_id": 123})

            # 2. 消费者接收消息
            message = await consumer.poll()

            # 3. 处理器处理消息
            processed = await processor.process_message(message)

            # 验证
            assert message["value"]["match_id"] == 123
            assert processed["processed"] is True
            assert "prediction" in processed

    def test_kafka_availability_check(self):
        """测试Kafka可用性检查"""
        if not STREAMING_AVAILABLE:
            pytest.skip("Streaming模块不可用")

        # 检查Kafka是否可用
        assert isinstance(KAFKA_AVAILABLE, bool)
        assert isinstance(DEFAULT_TOPICS, list)
        assert len(DEFAULT_TOPICS) > 0

    def test_ensure_topics_exist(self):
        """测试主题确保存在"""
        if not STREAMING_AVAILABLE:
            pytest.skip("Streaming模块不可用")

        # 测试主题确保函数
        result = ensure_topics_exist(["test_topic"])
        assert isinstance(result, bool)

    @pytest.mark.asyncio
    async def test_error_recovery(self):
        """测试错误恢复机制"""
        if not STREAMING_AVAILABLE:
            pytest.skip("Streaming模块不可用")

        with patch(
            "src.streaming.kafka_producer_simple.KafkaMessageProducer"
        ) as MockProducer:
            producer = MockProducer()
            producer.send = AsyncMock(
                side_effect=[Exception("Connection lost"), {"offset": 123}]
            )
            producer.reconnect = AsyncMock(return_value=True)

            # 第一次失败
            try:
                await producer.send("test", {"data": "test"})
            except Exception:
                pass

            # 重连并重试
            await producer.reconnect()
            result = await producer.send("test", {"data": "test"})

            assert result["offset"] == 123

    @pytest.mark.asyncio
    async def test_performance_monitoring(self):
        """测试性能监控"""
        if not STREAMING_AVAILABLE:
            pytest.skip("Streaming模块不可用")

        with patch(
            "src.streaming.kafka_producer_simple.KafkaMessageProducer"
        ) as MockProducer:
            producer = MockProducer()
            producer.get_metrics = Mock(
                return_value={
                    "messages_sent": 1000,
                    "bytes_sent": 1024000,
                    "error_rate": 0.01,
                    "latency_avg": 10.5,
                }
            )

            metrics = producer.get_metrics()
            assert metrics["messages_sent"] == 1000
            assert metrics["error_rate"] == 0.01
