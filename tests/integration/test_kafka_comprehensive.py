"""
Kafka 综合集成测试
Comprehensive Kafka Integration Tests

测试 Kafka 与系统各组件的集成，包括：
- 消息序列化/反序列化
- 分区和偏移量管理
- 错误处理和重试机制
- 批量消息处理
- 事务性消息
- 消费者组管理
"""

import pytest
import asyncio
import json
import time
from datetime import datetime, timezone, timedelta
from typing import List, Dict, Any, Optional
from unittest.mock import Mock, patch, AsyncMock
import uuid

# 测试导入
try:
    from kafka import KafkaProducer, KafkaConsumer, KafkaAdminClient
    from kafka.errors import KafkaError, CommitFailedError, KafkaTimeoutError
    from kafka.admin import NewTopic

    KAFKA_AVAILABLE = True
except ImportError:
    KAFKA_AVAILABLE = False
    KafkaProducer = None
    KafkaConsumer = None
    KafkaAdminClient = None

try:
    from src.streaming.kafka_producer import PredictionProducer
    from src.streaming.kafka_consumer import PredictionConsumer
    from src.streaming.event_handler import EventHandler
    from src.streaming.serialization import JSONSerializer, AvroSerializer

    STREAMING_AVAILABLE = True
except ImportError:
    STREAMING_AVAILABLE = False


@pytest.mark.skipif(not KAFKA_AVAILABLE, reason="Kafka not available")
@pytest.mark.skipif(not STREAMING_AVAILABLE, reason="Streaming modules not available")
@pytest.mark.integration
@pytest.mark.kafka
class TestKafkaMessageFlow:
    """Kafka 消息流测试"""

    @pytest.fixture
    async def kafka_topics(self, test_kafka):
        """创建测试专用主题"""
        admin_client = test_kafka["admin_client"]
        test_kafka["bootstrap_servers"]

        # 创建多个测试主题
        topics = [
            NewTopic(
                name="test_predictions_flow", num_partitions=3, replication_factor=1
            ),
            NewTopic(name="test_events_flow", num_partitions=2, replication_factor=1),
            NewTopic(name="test_dead_letter", num_partitions=1, replication_factor=1),
        ]

        try:
            admin_client.create_topics(topics, validate_only=False)
        except Exception:
            pass  # 主题可能已存在

        yield {
            "predictions": "test_predictions_flow",
            "events": "test_events_flow",
            "dead_letter": "test_dead_letter",
        }

        # 清理
        try:
            admin_client.delete_topics(list(t.name for t in topics))
        except Exception:
            pass

    async def test_prediction_message_flow(self, kafka_topics, test_kafka):
        """测试预测消息的完整流程"""
        # 1. 创建生产者
        producer = KafkaProducer(
            bootstrap_servers=test_kafka["bootstrap_servers"],
            value_serializer=lambda v: json.dumps(v).encode("utf-8"),
            key_serializer=lambda k: k.encode("utf-8") if k else None,
            acks="all",  # 等待所有副本确认
            retries=3,
            batch_size=16384,
            linger_ms=10,
            buffer_memory=33554432,
        )

        # 2. 创建消费者
        consumer = KafkaConsumer(
            kafka_topics["predictions"],
            bootstrap_servers=test_kafka["bootstrap_servers"],
            group_id=f"test_group_{uuid.uuid4().hex[:8]}",
            value_deserializer=lambda m: json.loads(m.decode("utf-8")),
            key_deserializer=lambda m: m.decode("utf-8") if m else None,
            auto_offset_reset="earliest",
            enable_auto_commit=False,
        )

        try:
            # 3. 发送预测消息
            prediction_messages = [
                {
                    "id": f"pred_{i}",
                    "match_id": f"match_{i}",
                    "prediction": "HOME_WIN" if i % 2 == 0 else "AWAY_WIN",
                    "confidence": 0.75 + (i * 0.05),
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "source": "test_suite",
                }
                for i in range(5)
            ]

            # 发送消息
            for msg in prediction_messages:
                future = producer.send(
                    topic=kafka_topics["predictions"], key=msg["id"], value=msg
                )
                # 等待确认
                record_metadata = future.get(timeout=10)
                assert record_metadata.topic == kafka_topics["predictions"]

            producer.flush()

            # 4. 消费消息
            consumed_messages = []
            start_time = time.time()
            timeout = 30  # 30秒超时

            while len(consumed_messages) < 5 and (time.time() - start_time) < timeout:
                message_pack = consumer.poll(timeout_ms=1000)
                for topic_partition, messages in message_pack.items():
                    for message in messages:
                        consumed_messages.append(
                            {
                                "key": message.key,
                                "value": message.value,
                                "partition": message.partition,
                                "offset": message.offset,
                            }
                        )
                        # 手动提交偏移量
                        consumer.commit()

            # 5. 验证消息
            assert len(consumed_messages) == 5

            # 验证消息内容
            consumed_values = [msg["value"] for msg in consumed_messages]
            for original_msg in prediction_messages:
                assert original_msg in consumed_values

            # 验证分区分配
            partitions_used = set(msg["partition"] for msg in consumed_messages)
            assert len(partitions_used) >= 1  # 至少使用一个分区

        finally:
            producer.close()
            consumer.close()

    async def test_batch_message_processing(self, kafka_topics, test_kafka):
        """测试批量消息处理"""
        producer = KafkaProducer(
            bootstrap_servers=test_kafka["bootstrap_servers"],
            value_serializer=lambda v: json.dumps(v).encode("utf-8"),
            batch_size=32768,  # 更大的批次
            linger_ms=50,  # 更长的等待时间
            compression_type="gzip",
        )

        consumer = KafkaConsumer(
            kafka_topics["events"],
            bootstrap_servers=test_kafka["bootstrap_servers"],
            group_id=f"batch_test_{uuid.uuid4().hex[:8]}",
            value_deserializer=lambda m: json.loads(m.decode("utf-8")),
            max_poll_records=100,  # 每次最多拉取100条
            fetch_max_bytes=1048576,  # 1MB
        )

        try:
            # 批量发送100条消息
            batch_size = 100
            events = []

            for i in range(batch_size):
                event = {
                    "event_id": f"event_{i}",
                    "type": "match_update" if i % 2 == 0 else "prediction_update",
                    "data": {
                        "match_id": f"match_{i // 10}",
                        "update_type": "score" if i % 3 == 0 else "status",
                    },
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                }
                events.append(event)

                # 使用send_batch进行批量发送
                producer.send(kafka_topics["events"], value=event)

            producer.flush()

            # 批量消费
            consumed_events = []
            start_time = time.time()

            while len(consumed_events) < batch_size and (time.time() - start_time) < 30:
                message_pack = consumer.poll(timeout_ms=2000)

                # 批量处理消息
                for topic_partition, messages in message_pack.items():
                    consumed_events.extend([msg.value for msg in messages])

                    # 批量提交偏移量
                    consumer.commit()

            assert len(consumed_events) == batch_size

            # 验证事件类型分布
            match_updates = [e for e in consumed_events if e["type"] == "match_update"]
            prediction_updates = [
                e for e in consumed_events if e["type"] == "prediction_update"
            ]

            assert len(match_updates) == 50
            assert len(prediction_updates) == 50

        finally:
            producer.close()
            consumer.close()

    async def test_error_handling_and_retry(self, kafka_topics, test_kafka):
        """测试错误处理和重试机制"""
        # 创建一个配置了重试的生产者
        producer = KafkaProducer(
            bootstrap_servers=test_kafka["bootstrap_servers"],
            value_serializer=lambda v: json.dumps(v).encode("utf-8"),
            retries=3,
            retry_backoff_ms=100,
            request_timeout_ms=30000,
        )

        # 模拟序列化错误
        def failing_serializer(value):
            if isinstance(value, dict) and value.get("should_fail"):
                raise ValueError("Serialization failed")
            return json.dumps(value).encode("utf-8")

        producer_with_fails = KafkaProducer(
            bootstrap_servers=test_kafka["bootstrap_servers"],
            value_serializer=failing_serializer,
            retries=3,
        )

        try:
            # 1. 测试正常消息
            normal_msg = {"id": "normal", "data": "test"}
            future = producer.send(kafka_topics["predictions"], value=normal_msg)
            record_metadata = future.get(timeout=10)
            assert record_metadata is not None

            # 2. 测试失败消息（会被重试）
            failing_msg = {"id": "failing", "should_fail": True}
            with pytest.raises(ValueError):
                future = producer_with_fails.send(
                    kafka_topics["predictions"], value=failing_msg
                )
                future.get(timeout=10)

            # 3. 测试发送到不存在的主题
            with pytest.raises(KafkaTimeoutError):
                future = producer.send("nonexistent_topic", value={"test": "message"})
                future.get(timeout=5)

        finally:
            producer.close()
            producer_with_fails.close()

    async def test_consumer_group_management(self, kafka_topics, test_kafka):
        """测试消费者组管理"""
        group_id = f"test_group_mgmt_{uuid.uuid4().hex[:8]}"

        # 创建两个消费者在同一组
        consumer1 = KafkaConsumer(
            kafka_topics["events"],
            bootstrap_servers=test_kafka["bootstrap_servers"],
            group_id=group_id,
            value_deserializer=lambda m: json.loads(m.decode("utf-8")),
            session_timeout_ms=10000,
            heartbeat_interval_ms=3000,
        )

        consumer2 = KafkaConsumer(
            kafka_topics["events"],
            bootstrap_servers=test_kafka["bootstrap_servers"],
            group_id=group_id,
            value_deserializer=lambda m: json.loads(m.decode("utf-8")),
            session_timeout_ms=10000,
            heartbeat_interval_ms=3000,
        )

        # 生产者发送消息
        producer = KafkaProducer(
            bootstrap_servers=test_kafka["bootstrap_servers"],
            value_serializer=lambda v: json.dumps(v).encode("utf-8"),
        )

        try:
            # 发送消息
            test_messages = [{"id": i, "content": f"message_{i}"} for i in range(10)]

            for msg in test_messages:
                producer.send(kafka_topics["events"], value=msg)
            producer.flush()

            # 订阅主题
            consumer1.subscribe([kafka_topics["events"]])
            consumer2.subscribe([kafka_topics["events"]])

            # 等待重平衡
            time.sleep(2)

            # 验证分区分配
            assignment1 = consumer1.assignment()
            assignment2 = consumer2.assignment()

            # 两个消费者应该共享分区
            assert len(assignment1) + len(assignment2) == 2  # 总共2个分区

            # 消费消息
            consumed_by_c1 = []
            consumed_by_c2 = []

            for _ in range(50):  # 最多轮询50次
                # 消费者1
                msg_pack1 = consumer1.poll(timeout_ms=100)
                for tp, messages in msg_pack1.items():
                    consumed_by_c1.extend([msg.value for msg in messages])

                # 消费者2
                msg_pack2 = consumer2.poll(timeout_ms=100)
                for tp, messages in msg_pack2.items():
                    consumed_by_c2.extend([msg.value for msg in messages])

                if len(consumed_by_c1) + len(consumed_by_c2) >= 10:
                    break

            # 验证消息被正确分配
            total_consumed = len(consumed_by_c1) + len(consumed_by_c2)
            assert total_consumed == 10

            # 验证没有重复消费
            consumed_ids = set()
            for msg in consumed_by_c1 + consumed_by_c2:
                consumed_ids.add(msg["id"])
            assert len(consumed_ids) == 10

        finally:
            producer.close()
            consumer1.close()
            consumer2.close()


@pytest.mark.skipif(not KAFKA_AVAILABLE, reason="Kafka not available")
@pytest.mark.skipif(not STREAMING_AVAILABLE, reason="Streaming modules not available")
@pytest.mark.integration
@pytest.mark.kafka
class TestKafkaSchemaAndSerialization:
    """Kafka 模式和序列化测试"""

    async def test_json_serialization(self, test_kafka):
        """测试JSON序列化"""
        from src.streaming.serialization import JSONSerializer

        serializer = JSONSerializer()

        # 测试各种数据类型
        test_data = {
            "string": "测试字符串",
            "number": 42,
            "float": 3.14,
            "boolean": True,
            "null": None,
            "list": [1, 2, 3],
            "nested": {
                "inner": "value",
                "timestamp": datetime.now(timezone.utc).isoformat(),
            },
        }

        # 序列化
        serialized = serializer.serialize(test_data)
        assert isinstance(serialized, bytes)

        # 反序列化
        deserialized = serializer.deserialize(serialized)
        assert deserialized == test_data

    async def test_avro_serialization(self, test_kafka):
        """测试Avro序列化（如果可用）"""
        try:
            from src.streaming.serialization import AvroSerializer

            # 定义Avro模式
            schema = {
                "type": "record",
                "name": "Prediction",
                "fields": [
                    {"name": "id", "type": "string"},
                    {"name": "match_id", "type": "string"},
                    {"name": "prediction", "type": "string"},
                    {"name": "confidence", "type": "float"},
                    {
                        "name": "timestamp",
                        "type": "string",
                        "logicalType": "timestamp-micros",
                    },
                ],
            }

            serializer = AvroSerializer(schema)

            # 测试数据
            prediction = {
                "id": "pred_001",
                "match_id": "match_123",
                "prediction": "HOME_WIN",
                "confidence": 0.75,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }

            # 序列化
            serialized = serializer.serialize(prediction)
            assert isinstance(serialized, bytes)

            # 反序列化
            deserialized = serializer.deserialize(serialized)
            assert deserialized["id"] == prediction["id"]
            assert deserialized["match_id"] == prediction["match_id"]

        except ImportError:
            pytest.skip("Avro serializer not available")

    async def test_schema_validation(self, test_kafka):
        """测试模式验证"""
        from src.streaming.validation import MessageValidator

        # 定义验证规则
        prediction_schema = {
            "type": "object",
            "required": ["id", "match_id", "prediction", "confidence"],
            "properties": {
                "id": {"type": "string"},
                "match_id": {"type": "string"},
                "prediction": {"enum": ["HOME_WIN", "AWAY_WIN", "DRAW"]},
                "confidence": {"type": "number", "minimum": 0, "maximum": 1},
                "timestamp": {"type": "string", "format": "date-time"},
            },
        }

        validator = MessageValidator(prediction_schema)

        # 有效消息
        valid_message = {
            "id": "pred_001",
            "match_id": "match_001",
            "prediction": "HOME_WIN",
            "confidence": 0.85,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

        assert validator.validate(valid_message) is True

        # 无效消息
        invalid_messages = [
            {},  # 缺少必填字段
            {
                "id": "pred",
                "match_id": "match",
                "prediction": "INVALID",
                "confidence": 0.5,
            },  # 无效枚举值
            {
                "id": "pred",
                "match_id": "match",
                "prediction": "HOME_WIN",
                "confidence": 1.5,
            },  # 超出范围
            {
                "id": "pred",
                "match_id": "match",
                "prediction": "HOME_WIN",
                "confidence": -0.1,
            },  # 负值
        ]

        for msg in invalid_messages:
            assert validator.validate(msg) is False


@pytest.mark.skipif(not KAFKA_AVAILABLE, reason="Kafka not available")
@pytest.mark.integration
@pytest.mark.kafka
@pytest.mark.performance
class TestKafkaPerformance:
    """Kafka 性能测试"""

    async def test_producer_throughput(self, test_kafka):
        """测试生产者吞吐量"""
        producer = KafkaProducer(
            bootstrap_servers=test_kafka["bootstrap_servers"],
            value_serializer=lambda v: json.dumps(v).encode("utf-8"),
            batch_size=65536,
            linger_ms=10,
            compression_type="snappy",
        )

        try:
            message_count = 1000
            message_size = 1024  # 1KB消息

            # 生成测试消息
            messages = [
                {
                    "id": i,
                    "payload": "x" * (message_size - 100),  # 填充数据
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                }
                for i in range(message_count)
            ]

            # 测量发送时间
            start_time = time.time()

            for msg in messages:
                producer.send("test_performance", value=msg)

            producer.flush()

            end_time = time.time()
            duration = end_time - start_time

            # 计算吞吐量
            throughput = message_count / duration
            mb_per_second = (message_count * message_size) / (duration * 1024 * 1024)

            # 断言性能要求
            assert throughput > 100  # 至少100条/秒
            assert mb_per_second > 1  # 至少1MB/秒

            print(f"Producer throughput: {throughput:.2f} msg/sec")
            print(f"Data rate: {mb_per_second:.2f} MB/sec")

        finally:
            producer.close()

    async def test_consumer_latency(self, test_kafka):
        """测试消费者延迟"""
        producer = KafkaProducer(
            bootstrap_servers=test_kafka["bootstrap_servers"],
            value_serializer=lambda v: json.dumps(v).encode("utf-8"),
        )

        consumer = KafkaConsumer(
            "test_performance",
            bootstrap_servers=test_kafka["bootstrap_servers"],
            group_id=f"latency_test_{uuid.uuid4().hex[:8]}",
            value_deserializer=lambda m: json.loads(m.decode("utf-8")),
            auto_offset_reset="latest",
        )

        try:
            # 发送消息
            test_message = {"id": "latency_test", "send_time": time.time()}

            producer.send("test_performance", value=test_message)
            producer.flush()

            # 测量接收延迟
            start_time = time.time()
            received_message = None

            while time.time() - start_time < 10:  # 10秒超时
                message_pack = consumer.poll(timeout_ms=100)
                for topic_partition, messages in message_pack.items():
                    for message in messages:
                        received_message = message.value
                        break
                    if received_message:
                        break

            assert received_message is not None

            # 计算延迟
            send_time = received_message["send_time"]
            receive_time = time.time()
            latency = (receive_time - send_time) * 1000  # 转换为毫秒

            # 断言延迟要求
            assert latency < 1000  # 小于1秒

            print(f"Consumer latency: {latency:.2f} ms")

        finally:
            producer.close()
            consumer.close()

    async def test_end_to_end_latency(self, test_kafka):
        """测试端到端延迟"""
        from src.streaming.kafka_producer import PredictionProducer
        from src.streaming.kafka_consumer import PredictionConsumer

        # 创建生产者和消费者
        producer_config = {
            "bootstrap_servers": test_kafka["bootstrap_servers"],
            "topic": "test_e2e",
        }

        consumer_config = {
            "bootstrap_servers": test_kafka["bootstrap_servers"],
            "topics": ["test_e2e"],
            "group_id": f"e2e_test_{uuid.uuid4().hex[:8]}",
        }

        producer = PredictionProducer(producer_config)
        consumer = PredictionConsumer(consumer_config)

        try:
            # 测试数据
            prediction = {
                "id": "e2e_test",
                "match_id": "match_e2e",
                "prediction": "HOME_WIN",
                "confidence": 0.85,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }

            # 测量端到端延迟
            start_time = time.time()

            # 发送
            await producer.send(prediction)

            # 接收
            received = None
            timeout = 10

            while time.time() - start_time < timeout:
                received = await consumer.receive(timeout=1)
                if received and received.get("id") == "e2e_test":
                    break

            end_time = time.time()
            e2e_latency = (end_time - start_time) * 1000

            assert received is not None
            assert received["id"] == "e2e_test"
            assert e2e_latency < 2000  # 小于2秒

            print(f"End-to-end latency: {e2e_latency:.2f} ms")

        finally:
            await producer.close()
            await consumer.close()


# 测试Kafka与系统的集成
@pytest.mark.skipif(not KAFKA_AVAILABLE, reason="Kafka not available")
@pytest.mark.integration
@pytest.mark.kafka
class TestKafkaSystemIntegration:
    """Kafka 与系统集成测试"""

    async def test_prediction_pipeline_integration(self, test_kafka):
        """测试预测管道集成"""
        # 模拟完整的预测流程：
        # 1. 接收比赛数据
        # 2. 生成预测
        # 3. 发布到Kafka
        # 4. 消费者处理
        # 5. 更新数据库

        producer = KafkaProducer(
            bootstrap_servers=test_kafka["bootstrap_servers"],
            value_serializer=lambda v: json.dumps(v).encode("utf-8"),
        )

        consumer = KafkaConsumer(
            "test_predictions",
            bootstrap_servers=test_kafka["bootstrap_servers"],
            group_id=f"pipeline_test_{uuid.uuid4().hex[:8]}",
            value_deserializer=lambda m: json.loads(m.decode("utf-8")),
        )

        try:
            # 1. 发送比赛数据
            match_data = {
                "event": "match_created",
                "match_id": "match_pipe_001",
                "home_team": "Team A",
                "away_team": "Team B",
                "competition": "Test League",
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }

            producer.send("test_matches", value=match_data)

            # 2. 模拟生成预测
            prediction = {
                "event": "prediction_created",
                "prediction_id": "pred_pipe_001",
                "match_id": match_data["match_id"],
                "prediction": "HOME_WIN",
                "confidence": 0.78,
                "model_version": "v2.1",
                "features": {
                    "home_form": 0.85,
                    "away_form": 0.62,
                    "h2h_home_wins": 5,
                    "h2h_away_wins": 2,
                },
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }

            producer.send("test_predictions", value=prediction)
            producer.flush()

            # 3. 消费并处理
            processed_predictions = []
            start_time = time.time()

            while len(processed_predictions) < 1 and (time.time() - start_time) < 10:
                message_pack = consumer.poll(timeout_ms=1000)
                for tp, messages in message_pack.items():
                    for message in messages:
                        # 模拟处理逻辑
                        pred = message.value
                        if pred.get("event") == "prediction_created":
                            processed_predictions.append(
                                {
                                    "prediction_id": pred["prediction_id"],
                                    "match_id": pred["match_id"],
                                    "prediction": pred["prediction"],
                                    "confidence": pred["confidence"],
                                    "processed_at": datetime.now(
                                        timezone.utc
                                    ).isoformat(),
                                }
                            )

            # 验证处理结果
            assert len(processed_predictions) == 1
            processed = processed_predictions[0]
            assert processed["prediction_id"] == "pred_pipe_001"
            assert processed["match_id"] == "match_pipe_001"
            assert "processed_at" in processed

        finally:
            producer.close()
            consumer.close()

    async def test_dead_letter_queue(self, test_kafka):
        """测试死信队列处理"""
        # 主队列生产者
        producer = KafkaProducer(
            bootstrap_servers=test_kafka["bootstrap_servers"],
            value_serializer=lambda v: json.dumps(v).encode("utf-8"),
        )

        # 死信队列消费者
        dlq_consumer = KafkaConsumer(
            "test_dead_letter",
            bootstrap_servers=test_kafka["bootstrap_servers"],
            group_id=f"dlq_test_{uuid.uuid4().hex[:8]}",
            value_deserializer=lambda m: json.loads(m.decode("utf-8")),
        )

        try:
            # 发送有效消息
            valid_messages = [
                {"id": i, "status": "valid", "data": f"message_{i}"} for i in range(5)
            ]

            # 发送无效消息（会被路由到死信队列）
            invalid_messages = [
                {"id": i, "status": "invalid", "error": "Missing required field"}
                for i in range(5, 8)
            ]

            # 发送所有消息
            for msg in valid_messages + invalid_messages:
                producer.send("test_predictions", value=msg)
            producer.flush()

            # 模拟处理器，将无效消息发送到死信队列
            dlq_producer = KafkaProducer(
                bootstrap_servers=test_kafka["bootstrap_servers"],
                value_serializer=lambda v: json.dumps(v).encode("utf-8"),
            )

            # 处理无效消息并发送到死信队列
            for invalid_msg in invalid_messages:
                dlq_message = {
                    "original_message": invalid_msg,
                    "error": invalid_msg["error"],
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "retry_count": 0,
                }
                dlq_producer.send("test_dead_letter", value=dlq_message)
            dlq_producer.flush()

            # 验证死信队列消息
            dlq_messages = []
            start_time = time.time()

            while len(dlq_messages) < 3 and (time.time() - start_time) < 10:
                message_pack = dlq_consumer.poll(timeout_ms=1000)
                for tp, messages in message_pack.items():
                    for message in messages:
                        dlq_messages.append(message.value)

            assert len(dlq_messages) == 3

            # 验证死信消息格式
            for dlq_msg in dlq_messages:
                assert "original_message" in dlq_msg
                assert "error" in dlq_msg
                assert "timestamp" in dlq_msg
                assert dlq_msg["original_message"]["status"] == "invalid"

        finally:
            producer.close()
            dlq_producer.close()
            dlq_consumer.close()
