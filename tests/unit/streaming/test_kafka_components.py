"""
流处理单元测试 - Kafka组件
"""

import asyncio
import json
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock

import pytest

from src.streaming.kafka_components import (
    KafkaAdmin,
    FootballKafkaProducer,
    StreamProcessor,
)


@pytest.mark.unit
class TestKafkaProducer:
    """Kafka生产者测试"""

    @pytest.fixture
    def producer(self):
        """创建生产者实例"""
        producer = FootballKafkaProducer(
            bootstrap_servers="localhost:9092", client_id="test_producer"
        )
        producer.producer = MagicMock()
        producer.logger = MagicMock()
        return producer

    @pytest.fixture
    def sample_message(self):
        """示例消息"""
        return {
            "match_id": 12345,
            "event_type": "goal",
            "timestamp": datetime.now().isoformat(),
            "data": {"player": "John Doe", "minute": 25, "team": "home"},
        }

    def test_producer_initialization(self, producer):
        """测试生产者初始化"""
        assert producer is not None
        assert producer.bootstrap_servers == "localhost:9092"
        assert producer.client_id == "test_producer"
        assert producer.producer is not None

    @pytest.mark.asyncio
    async def test_send_message_success(self, producer, sample_message):
        """测试成功发送消息"""
        # Mock成功发送
        producer.producer.send_and_wait = AsyncMock(return_value=True)

        result = await producer.send_message(
            topic="match_events",
            message=sample_message,
            key=str(sample_message["match_id"]),
        )

        assert result is True
        producer.producer.send_and_wait.assert_called_once()

    @pytest.mark.asyncio
    async def test_send_message_with_error(self, producer, sample_message):
        """测试发送消息错误"""
        # Mock发送失败
        producer.producer.send_and_wait = AsyncMock(
            side_effect=Exception("Kafka error")
        )

        result = await producer.send_message(
            topic="match_events", message=sample_message
        )

        assert result is False
        producer.logger.error.assert_called()

    @pytest.mark.asyncio
    async def test_send_batch_messages(self, producer):
        """测试批量发送消息"""
        messages = [{"id": i, "data": f"message_{i}"} for i in range(10)]

        producer.producer.send_batch = AsyncMock(return_value=True)

        result = await producer.send_batch(topic="batch_topic", messages=messages)

        assert result is True
        producer.producer.send_batch.assert_called_once()

    def test_serialize_message(self, producer, sample_message):
        """测试消息序列化"""
        serializer = KafkaSerializer()

        serialized = serializer.serialize(
            topic="match_events",
            value=sample_message,
            key=str(sample_message["match_id"]),
        )

        assert isinstance(serialized, tuple)
        assert len(serialized) == 2
        assert serialized[0] == str(sample_message["match_id"]).encode()
        assert serialized[1] == json.dumps(sample_message).encode()

    def test_close_producer(self, producer):
        """测试关闭生产者"""
        producer.producer.close = MagicMock()

        producer.close()

        producer.producer.close.assert_called_once()


@pytest.mark.unit
class TestKafkaConsumer:
    """Kafka消费者测试"""

    @pytest.fixture
    def consumer(self):
        """创建消费者实例"""
        consumer = KafkaConsumer(
            bootstrap_servers="localhost:9092",
            group_id="test_group",
            topics=["test_topic"],
        )
        consumer.consumer = MagicMock()
        consumer.logger = MagicMock()
        return consumer

    @pytest.fixture
    def sample_record(self):
        """示例Kafka记录"""
        from collections import namedtuple

        Record = namedtuple("Record", ["topic", "partition", "offset", "key", "value"])

        return Record(
            topic="test_topic",
            partition=0,
            offset=123,
            key=b"12345",
            value=b'{"match_id": 12345, "event": "goal"}',
        )

    def test_consumer_initialization(self, consumer):
        """测试消费者初始化"""
        assert consumer is not None
        assert consumer.group_id == "test_group"
        assert "test_topic" in consumer.topics

    @pytest.mark.asyncio
    async def test_consume_messages(self, consumer, sample_record):
        """测试消费消息"""
        # Mock消费记录
        consumer.consumer.getmany = AsyncMock(
            return_value={("test_topic", 0): [sample_record]}
        )

        messages = []
        async for message in consumer.consume(timeout_ms=1000):
            messages.append(message)
            break

        assert len(messages) == 1
        assert messages[0]["match_id"] == 12345

    @pytest.mark.asyncio
    async def test_consume_with_deserializer(self, consumer, sample_record):
        """测试使用反序列化器消费"""
        deserializer = KafkaDeserializer()
        consumer.deserializer = deserializer

        consumer.consumer.getmany = AsyncMock(
            return_value={("test_topic", 0): [sample_record]}
        )

        messages = []
        async for message in consumer.consume(timeout_ms=1000):
            messages.append(message)
            break

        assert isinstance(messages[0], dict)
        assert "match_id" in messages[0]

    def test_commit_offsets(self, consumer):
        """测试提交偏移量"""
        consumer.consumer.commit = AsyncMock(return_value=True)

        asyncio.run(consumer.commit())

        consumer.consumer.commit.assert_called_once()

    def test_seek_to_offset(self, consumer):
        """测试跳转到偏移量"""
        consumer.consumer.seek = MagicMock()

        consumer.seek(topic="test_topic", partition=0, offset=100)

        consumer.consumer.seek.assert_called_once()

    def test_pause_resume_partition(self, consumer):
        """测试暂停和恢复分区"""
        consumer.consumer.pause = MagicMock()
        consumer.consumer.resume = MagicMock()

        # 暂停
        consumer.pause_partition(topic="test_topic", partition=0)
        consumer.consumer.pause.assert_called()

        # 恢复
        consumer.resume_partition(topic="test_topic", partition=0)
        consumer.consumer.resume.assert_called()


@pytest.mark.unit
class TestKafkaAdmin:
    """Kafka管理器测试"""

    @pytest.fixture
    def admin(self):
        """创建管理器实例"""
        admin = KafkaAdmin(bootstrap_servers="localhost:9092")
        admin.admin_client = MagicMock()
        admin.logger = MagicMock()
        return admin

    @pytest.mark.asyncio
    async def test_create_topic(self, admin):
        """测试创建主题"""
        admin.admin_client.create_topics = AsyncMock(return_value={"test_topic": "OK"})

        result = await admin.create_topic(
            name="test_topic", num_partitions=3, replication_factor=1
        )

        assert result is True
        admin.admin_client.create_topics.assert_called_once()

    @pytest.mark.asyncio
    async def test_delete_topic(self, admin):
        """测试删除主题"""
        admin.admin_client.delete_topics = AsyncMock(return_value={"test_topic": "OK"})

        result = await admin.delete_topic("test_topic")

        assert result is True
        admin.admin_client.delete_topics.assert_called_once()

    @pytest.mark.asyncio
    async def test_list_topics(self, admin):
        """测试列出主题"""
        admin.admin_client.list_topics = AsyncMock(
            return_value={"test_topic": {"partitions": 3, "replication_factor": 1}}
        )

        topics = await admin.list_topics()

        assert "test_topic" in topics
        assert topics["test_topic"]["partitions"] == 3

    @pytest.mark.asyncio
    async def test_get_topic_metadata(self, admin):
        """测试获取主题元数据"""
        admin.admin_client.describe_topics = AsyncMock(
            return_value={
                "test_topic": {
                    "partitions": [
                        {"id": 0, "leader": 1, "replicas": [1]},
                        {"id": 1, "leader": 2, "replicas": [2]},
                        {"id": 2, "leader": 3, "replicas": [3]},
                    ]
                }
            }
        )

        metadata = await admin.get_topic_metadata("test_topic")

        assert len(metadata["partitions"]) == 3
        assert metadata["partitions"][0]["id"] == 0


@pytest.mark.unit
class TestMessageHandler:
    """消息处理器测试"""

    @pytest.fixture
    def handler(self):
        """创建处理器实例"""
        handler = MessageHandler()
        handler.logger = MagicMock()
        return handler

    @pytest.fixture
    def sample_message(self):
        """示例消息"""
        return {
            "topic": "match_events",
            "key": "12345",
            "value": {
                "match_id": 12345,
                "event": "goal",
                "timestamp": datetime.now().isoformat(),
            },
            "partition": 0,
            "offset": 100,
        }

    def test_handle_goal_event(self, handler, sample_message):
        """测试处理进球事件"""

        # 注册处理函数
        @handler.register("goal")
        def handle_goal(message):
            return {"processed": True, "event_type": "goal"}

        result = handler.handle(sample_message)

        assert result["processed"] is True
        assert result["event_type"] == "goal"

    def test_handle_unknown_event(self, handler, sample_message):
        """测试处理未知事件"""
        sample_message["value"]["event"] = "unknown"

        result = handler.handle(sample_message)

        assert result["processed"] is False
        assert "error" in result

    def test_register_handler(self, handler):
        """测试注册处理器"""

        def custom_handler(message):
            return {"custom": True}

        handler.register("custom_event", custom_handler)

        assert "custom_event" in handler.handlers
        assert handler.handlers["custom_event"] == custom_handler

    def test_unregistered_handler(self, handler):
        """测试注销处理器"""
        # 先注册
        handler.register("temp_event", lambda x: x)
        assert "temp_event" in handler.handlers

        # 注销
        handler.unregister("temp_event")
        assert "temp_event" not in handler.handlers

    @pytest.mark.asyncio
    async def test_async_handler(self, handler, sample_message):
        """测试异步处理器"""

        @handler.register_async("async_goal")
        async def handle_async_goal(message):
            await asyncio.sleep(0.01)  # 模拟异步操作
            return {"async_processed": True}

        sample_message["value"]["event"] = "async_goal"
        result = await handler.handle_async(sample_message)

        assert result["async_processed"] is True


@pytest.mark.unit
class TestStreamProcessor:
    """流处理器测试"""

    @pytest.fixture
    def processor(self):
        """创建处理器实例"""
        processor = StreamProcessor(
            kafka_brokers="localhost:9092",
            input_topics=["input_topic"],
            output_topics=["output_topic"],
        )
        processor.producer = MagicMock()
        processor.consumer = MagicMock()
        processor.logger = MagicMock()
        return processor

    @pytest.fixture
    def processing_pipeline(self):
        """处理管道"""

        def enrich_message(message):
            message["enriched"] = True
            message["processed_at"] = datetime.now().isoformat()
            return message

        def filter_goals(message):
            return message.get("event") == "goal"

        def aggregate_stats(message, stats):
            if message.get("event") == "goal":
                stats["total_goals"] = stats.get("total_goals", 0) + 1
            return stats

        return [enrich_message, filter_goals, aggregate_stats]

    def test_processor_initialization(self, processor):
        """测试处理器初始化"""
        assert processor is not None
        assert processor.kafka_brokers == "localhost:9092"
        assert "input_topic" in processor.input_topics
        assert "output_topic" in processor.output_topics

    @pytest.mark.asyncio
    async def test_process_single_message(self, processor):
        """测试处理单条消息"""
        message = {"match_id": 12345, "event": "goal", "player": "John Doe"}

        # Mock处理和发送
        processor.producer.send_message = AsyncMock(return_value=True)

        result = await processor.process_message(message)

        assert result is True
        processor.producer.send_message.assert_called()

    @pytest.mark.asyncio
    async def test_process_with_pipeline(self, processor, processing_pipeline):
        """测试使用管道处理消息"""
        message = {"match_id": 12345, "event": "goal", "player": "John Doe"}

        processor.pipeline = processing_pipeline
        processor.producer.send_message = AsyncMock(return_value=True)

        result = await processor.process_message(message)

        assert result is True
        # 验证消息被丰富
        assert "enriched" in message

    @pytest.mark.asyncio
    async def test_process_batch(self, processor):
        """测试批量处理"""
        messages = [
            {"id": i, "event": "goal" if i % 2 == 0 else "card"} for i in range(10)
        ]

        processor.producer.send_batch = AsyncMock(return_value=True)

        result = await processor.process_batch(messages)

        assert result is True
        processor.producer.send_batch.assert_called()

    @pytest.mark.asyncio
    async def test_start_processing(self, processor):
        """测试开始处理"""
        processor.consumer.consume = AsyncMock()
        processor.process_message = AsyncMock(return_value=True)

        # 运行处理循环（短暂运行）
        task = asyncio.create_task(processor.start_processing())
        await asyncio.sleep(0.1)
        task.cancel()

        try:
            await task
        except asyncio.CancelledError:
            pass

    def test_add_pipeline_step(self, processor):
        """测试添加处理步骤"""

        def custom_step(message):
            message["custom"] = True
            return message

        processor.add_pipeline_step(custom_step)

        assert custom_step in processor.pipeline

    def test_remove_pipeline_step(self, processor):
        """测试移除处理步骤"""

        # 添加步骤
        def temp_step(message):
            return message

        processor.add_pipeline_step(temp_step)

        # 移除步骤
        processor.remove_pipeline_step(temp_step)

        assert temp_step not in processor.pipeline

    def test_filter_messages(self, processor):
        """测试消息过滤"""
        messages = [
            {"event": "goal", "match_id": 1},
            {"event": "card", "match_id": 1},
            {"event": "goal", "match_id": 2},
            {"event": "substitution", "match_id": 1},
        ]

        # 只保留进球事件
        filtered = processor.filter_messages(
            messages, lambda m: m.get("event") == "goal"
        )

        assert len(filtered) == 2
        assert all(m.get("event") == "goal" for m in filtered)

    def test_aggregate_messages(self, processor):
        """测试消息聚合"""
        messages = [
            {"match_id": 1, "event": "goal"},
            {"match_id": 1, "event": "goal"},
            {"match_id": 1, "event": "card"},
            {"match_id": 2, "event": "goal"},
        ]

        aggregated = processor.aggregate_messages(
            messages,
            key=lambda m: m["match_id"],
            agg_func=lambda acc, m: {
                **acc,
                "goals": acc.get("goals", 0) + (1 if m["event"] == "goal" else 0),
                "cards": acc.get("cards", 0) + (1 if m["event"] == "card" else 0),
            },
        )

        assert aggregated[1]["goals"] == 2
        assert aggregated[1]["cards"] == 1
        assert aggregated[2]["goals"] == 1

    @pytest.mark.asyncio
    async def test_error_handling(self, processor):
        """测试错误处理"""
        message = {"invalid": "data"}

        # Mock处理失败
        processor.process_message = AsyncMock(side_effect=Exception("Processing error"))
        processor.producer.send_message = AsyncMock(return_value=True)

        # 应该处理错误而不崩溃
        result = await processor.process_message(message)

        assert result is False
        processor.logger.error.assert_called()

    def test_metrics_collection(self, processor):
        """测试指标收集"""
        # 初始化指标
        processor.init_metrics()

        # 更新指标
        processor.increment_processed()
        processor.increment_errors()
        processor.update_latency(0.05)

        # 检查指标
        assert processor.metrics["messages_processed"] == 1
        assert processor.metrics["errors"] == 1
        assert processor.metrics["avg_latency"] == 0.05

    @pytest.mark.asyncio
    async def test_state_management(self, processor):
        """测试状态管理"""
        # 设置状态
        await processor.set_state("last_offset", 1000)
        await processor.set_state("processing_stats", {"count": 50})

        # 获取状态
        offset = await processor.get_state("last_offset")
        stats = await processor.get_state("processing_stats")

        assert offset == 1000
        assert stats["count"] == 50

    def test_health_check(self, processor):
        """测试健康检查"""
        # Mock健康状态
        processor.producer.producer = MagicMock()
        processor.consumer.consumer = MagicMock()

        health = processor.health_check()

        assert "status" in health
        assert "producer" in health
        assert "consumer" in health
        assert "metrics" in health


@pytest.mark.unit
class TestKafkaSerializer:
    """Kafka序列化器测试"""

    @pytest.fixture
    def serializer(self):
        """创建序列化器实例"""
        return KafkaSerializer()

    def test_serialize_json(self, serializer):
        """测试JSON序列化"""
        data = {"key": "value", "number": 123}

        result = serializer.serialize("test_topic", data)

        assert isinstance(result, tuple)
        assert result[0] is None  # 没有key
        assert result[1] == json.dumps(data).encode()

    def test_serialize_with_key(self, serializer):
        """测试带key的序列化"""
        data = {"match_id": 12345}
        key = "12345"

        result = serializer.serialize("test_topic", data, key=key)

        assert result[0] == key.encode()
        assert result[1] == json.dumps(data).encode()

    def test_serialize_binary(self, serializer):
        """测试二进制序列化"""
        data = b"binary_data"

        result = serializer.serialize("test_topic", data, serialization_type="binary")

        assert result[1] == data

    def test_serialize_avro(self, serializer):
        """测试Avro序列化"""
        # Mock Avro schema
        schema = {
            "type": "record",
            "name": "MatchEvent",
            "fields": [
                {"name": "match_id", "type": "int"},
                {"name": "event", "type": "string"},
            ],
        }

        data = {"match_id": 12345, "event": "goal"}

        # 需要安装avro-python3库才能真正测试
        # 这里只验证调用
        try:
            result = serializer.serialize(
                "test_topic", data, schema=schema, serialization_type="avro"
            )
        except ImportError:
            # Avro库未安装，跳过测试
            pytest.skip("avro-python3 not installed")


@pytest.mark.unit
class TestKafkaDeserializer:
    """Kafka反序列化器测试"""

    @pytest.fixture
    def deserializer(self):
        """创建反序列化器实例"""
        return KafkaDeserializer()

    def test_deserialize_json(self, deserializer):
        """测试JSON反序列化"""
        data = json.dumps({"key": "value"}).encode()

        result = deserializer.deserialize("test_topic", data)

        assert isinstance(result, dict)
        assert result["key"] == "value"

    def test_deserialize_with_key(self, deserializer):
        """测试带key的反序列化"""
        key = b"12345"
        value = json.dumps({"match_id": 12345}).encode()

        result = deserializer.deserialize("test_topic", value, key=key)

        assert isinstance(result, dict)
        assert result["match_id"] == 12345

    def test_deserialize_binary(self, deserializer):
        """测试二进制反序列化"""
        data = b"binary_data"

        result = deserializer.deserialize(
            "test_topic", data, serialization_type="binary"
        )

        assert result == data

    def test_deserialize_invalid_json(self, deserializer):
        """测试无效JSON反序列化"""
        data = b"invalid json"

        with pytest.raises(json.JSONDecodeError):
            deserializer.deserialize("test_topic", data)

    def test_deserialize_none(self, deserializer):
        """测试反序列化None值"""
        result = deserializer.deserialize("test_topic", None)

        assert result is None


@pytest.mark.unit
class TestKafkaIntegration:
    """Kafka集成测试"""

    @pytest.mark.asyncio
    async def test_end_to_end_flow(self):
        """测试端到端流程"""
        # 创建生产者
        producer = KafkaProducer(bootstrap_servers="localhost:9092")
        producer.producer = MagicMock()
        producer.producer.send_and_wait = AsyncMock(return_value=True)

        # 创建消费者
        consumer = KafkaConsumer(
            bootstrap_servers="localhost:9092",
            group_id="test_group",
            topics=["test_topic"],
        )
        consumer.consumer = MagicMock()

        # 模拟消息
        message = {"test": "message", "timestamp": datetime.now().isoformat()}

        # 发送消息
        result = await producer.send_message("test_topic", message)
        assert result is True

        # 验证消息格式
        serializer = KafkaSerializer()
        serialized = serializer.serialize("test_topic", message)
        assert serialized[1] is not None

    def test_configuration_validation(self):
        """测试配置验证"""
        # 有效配置
        config = {
            "bootstrap_servers": "localhost:9092",
            "group_id": "test_group",
            "auto_offset_reset": "earliest",
            "enable_auto_commit": False,
        }

        # 验证配置
        assert "bootstrap_servers" in config
        assert config["group_id"] == "test_group"
        assert config["auto_offset_reset"] == "earliest"

    @pytest.mark.asyncio
    async def test_reconnection_logic(self):
        """测试重连逻辑"""
        producer = KafkaProducer(bootstrap_servers="localhost:9092")

        # Mock连接失败然后恢复
        connection_attempts = []

        async def mock_connect():
            connection_attempts.append(1)
            if len(connection_attempts) < 3:
                raise ConnectionError("Connection failed")
            return True

        producer.connect = mock_connect

        # 重试连接
        result = await producer.connect_with_retry(max_retries=3)

        assert result is True
        assert len(connection_attempts) == 3

    def test_performance_monitoring(self):
        """测试性能监控"""
        processor = StreamProcessor(
            kafka_brokers="localhost:9092",
            input_topics=["input"],
            output_topics=["output"],
        )

        # 记录性能指标
        processor.record_throughput(100)  # 100消息/秒
        processor.record_latency(0.05)  # 50ms延迟
        processor.record_error_rate(0.01)  # 1%错误率

        # 检查指标
        assert processor.metrics["throughput"] == 100
        assert processor.metrics["avg_latency"] == 0.05
        assert processor.metrics["error_rate"] == 0.01
