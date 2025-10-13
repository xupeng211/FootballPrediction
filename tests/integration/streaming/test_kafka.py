"""
Kafka 消息流集成测试
测试 Kafka 生产者和消费者的功能
"""

import pytest
import asyncio
import json
from datetime import datetime, timezone
from typing import List, Dict, Any


class TestKafkaIntegration:
    """Kafka 集成测试"""

    @pytest.mark.asyncio
    async def test_kafka_producer_basic(self, test_kafka):
        """测试 Kafka 生产者基本功能"""
        producer = test_kafka["producer"]
        topic = test_kafka["topics"][0]

        # 发送简单消息
        message = {"test": "basic_message", "timestamp": datetime.now().isoformat()}

        future = producer.send(topic=topic, key="test_key", value=json.dumps(message))

        # 等待发送完成
        record_metadata = future.get(timeout=10)

        # 验证发送成功
        assert record_metadata.topic == topic
        assert record_metadata.partition >= 0
        assert record_metadata.offset >= 0

    @pytest.mark.asyncio
    async def test_kafka_consumer_basic(self, test_kafka):
        """测试 Kafka 消费者基本功能"""
        from kafka import KafkaConsumer

        topic = test_kafka["topics"][1]
        bootstrap_servers = test_kafka["bootstrap_servers"]

        # 创建消费者
        consumer = KafkaConsumer(
            topic,
            bootstrap_servers=bootstrap_servers,
            auto_offset_reset="earliest",
            value_deserializer=lambda m: json.loads(m.decode("utf-8")),
            consumer_timeout_ms=5000,
            group_id="test_group_1",
        )

        # 发送测试消息
        producer = test_kafka["producer"]
        test_messages = [
            {"id": 1, "message": "Test message 1"},
            {"id": 2, "message": "Test message 2"},
            {"id": 3, "message": "Test message 3"},
        ]

        for msg in test_messages:
            producer.send(topic, key=f"key_{msg['id']}", value=json.dumps(msg))

        producer.flush()

        # 消费消息
        consumed_messages = []
        for message in consumer:
            consumed_messages.append(message.value)
            if len(consumed_messages) >= len(test_messages):
                break

        # 验证消费的消息
        assert len(consumed_messages) == 3
        assert consumed_messages[0]["message"] == "Test message 1"

        consumer.close()

    @pytest.mark.asyncio
    async def test_prediction_event_flow(
        self, test_kafka, db_session, sample_prediction_data
    ):
        """测试预测事件流"""
        from kafka import KafkaProducer, KafkaConsumer
        import uuid

        topic = f"{test_kafka['topics'][0]}"  # predictions topic
        bootstrap_servers = test_kafka["bootstrap_servers"]

        # 创建事件生产者
        event_producer = KafkaProducer(
            bootstrap_servers=bootstrap_servers,
            value_serializer=lambda v: json.dumps(v).encode("utf-8"),
            key_serializer=lambda k: k.encode("utf-8") if k else None,
        )

        # 模拟预测创建事件
        _prediction = sample_prediction_data["prediction"]
        event_data = {
            "event_id": str(uuid.uuid4()),
            "event_type": "prediction_created",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "data": {
                "prediction_id": prediction.id,
                "user_id": prediction.user_id,
                "match_id": prediction.match_id,
                "prediction": prediction.prediction,
                "confidence": prediction.confidence,
            },
        }

        # 发送事件
        event_producer.send(topic, key=event_data["event_id"], value=event_data)
        event_producer.flush()

        # 创建消费者接收事件
        consumer = KafkaConsumer(
            topic,
            bootstrap_servers=bootstrap_servers,
            auto_offset_reset="earliest",
            value_deserializer=lambda m: json.loads(m.decode("utf-8")),
            consumer_timeout_ms=5000,
            group_id="test_prediction_consumer",
        )

        # 消费并验证事件
        consumed_event = None
        for message in consumer:
            if message.value.get("event_type") == "prediction_created":
                consumed_event = message.value
                break

        # 验证事件内容
        assert consumed_event is not None
        assert consumed_event["event_type"] == "prediction_created"
        assert consumed_event["data"]["prediction_id"] == prediction.id
        assert consumed_event["data"]["prediction"] == prediction.prediction

        # 清理
        event_producer.close()
        consumer.close()

    @pytest.mark.asyncio
    async def test_match_update_events(self, test_kafka, sample_match_data):
        """测试比赛更新事件流"""
        from kafka import KafkaProducer, KafkaConsumer
        import uuid

        topic = f"{test_kafka['topics'][1]}"  # matches topic
        bootstrap_servers = test_kafka["bootstrap_servers"]

        # 创建生产者
        producer = KafkaProducer(
            bootstrap_servers=bootstrap_servers,
            value_serializer=lambda v: json.dumps(v).encode("utf-8"),
            key_serializer=lambda k: k.encode("utf-8"),
        )

        match = sample_match_data["match"]

        # 发送比赛更新事件序列
        events = [
            {
                "event_id": str(uuid.uuid4()),
                "event_type": "match_started",
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "data": {"match_id": match.id, "status": "LIVE", "minute": 1},
            },
            {
                "event_id": str(uuid.uuid4()),
                "event_type": "goal_scored",
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "data": {
                    "match_id": match.id,
                    "team": "home",
                    "scorer": "Test Player",
                    "minute": 25,
                    "score": {"home": 1, "away": 0},
                },
            },
            {
                "event_id": str(uuid.uuid4()),
                "event_type": "match_finished",
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "data": {
                    "match_id": match.id,
                    "status": "COMPLETED",
                    "final_score": {"home": 2, "away": 1},
                },
            },
        ]

        # 发送所有事件
        for event in events:
            producer.send(topic, key=str(match.id), value=event)
        producer.flush()

        # 创建消费者
        consumer = KafkaConsumer(
            topic,
            bootstrap_servers=bootstrap_servers,
            auto_offset_reset="earliest",
            value_deserializer=lambda m: json.loads(m.decode("utf-8")),
            consumer_timeout_ms=5000,
            group_id="test_match_consumer",
        )

        # 消费所有事件
        consumed_events = []
        for message in consumer:
            if message.value.get("data", {}).get("match_id") == match.id:
                consumed_events.append(message.value)
                if len(consumed_events) >= 3:
                    break

        # 验证事件序列
        assert len(consumed_events) == 3
        assert consumed_events[0]["event_type"] == "match_started"
        assert consumed_events[1]["event_type"] == "goal_scored"
        assert consumed_events[2]["event_type"] == "match_finished"

        # 验证事件顺序
        assert consumed_events[0]["timestamp"] < consumed_events[1]["timestamp"]
        assert consumed_events[1]["timestamp"] < consumed_events[2]["timestamp"]

        # 清理
        producer.close()
        consumer.close()

    @pytest.mark.asyncio
    async def test_audit_log_events(self, test_kafka):
        """测试审计日志事件"""
        from kafka import KafkaProducer, KafkaConsumer
        import uuid

        topic = f"{test_kafka['topics'][2]}"  # audit_logs topic
        bootstrap_servers = test_kafka["bootstrap_servers"]

        # 创建生产者
        producer = KafkaProducer(
            bootstrap_servers=bootstrap_servers,
            value_serializer=lambda v: json.dumps(v).encode("utf-8"),
            key_serializer=lambda k: k.encode("utf-8"),
        )

        # 模拟审计事件
        audit_events = [
            {
                "event_id": str(uuid.uuid4()),
                "event_type": "user_login",
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "user_id": "user_123",
                "ip_address": "192.168.1.100",
                "user_agent": "Mozilla/5.0...",
                "success": True,
            },
            {
                "event_id": str(uuid.uuid4()),
                "event_type": "prediction_created",
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "user_id": "user_123",
                "resource_id": "prediction_456",
                "details": {"prediction": "HOME_WIN", "confidence": 0.85},
            },
            {
                "event_id": str(uuid.uuid4()),
                "event_type": "data_export",
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "user_id": "admin_789",
                "resource_type": "predictions",
                "record_count": 1000,
                "format": "csv",
            },
        ]

        # 发送审计事件
        for event in audit_events:
            producer.send(topic, key=event["event_type"], value=event)
        producer.flush()

        # 创建消费者
        consumer = KafkaConsumer(
            topic,
            bootstrap_servers=bootstrap_servers,
            auto_offset_reset="earliest",
            value_deserializer=lambda m: json.loads(m.decode("utf-8")),
            consumer_timeout_ms=5000,
            group_id="test_audit_consumer",
        )

        # 按事件类型过滤消费
        consumed_events = {}
        for message in consumer:
            event_type = message.value.get("event_type")
            if event_type in ["user_login", "prediction_created", "data_export"]:
                consumed_events[event_type] = message.value
                if len(consumed_events) >= 3:
                    break

        # 验证审计事件
        assert len(consumed_events) == 3
        assert consumed_events["user_login"]["success"] is True
        assert consumed_events["prediction_created"]["resource_id"] == "prediction_456"
        assert consumed_events["data_export"]["record_count"] == 1000

        # 清理
        producer.close()
        consumer.close()

    @pytest.mark.asyncio
    async def test_message_serialization(self, test_kafka):
        """测试消息序列化和反序列化"""
        from kafka import KafkaProducer, KafkaConsumer

        topic = test_kafka["topics"][0]
        bootstrap_servers = test_kafka["bootstrap_servers"]

        # 创建带自定义序列化的生产者
        producer = KafkaProducer(
            bootstrap_servers=bootstrap_servers,
            value_serializer=lambda v: json.dumps(v, default=str).encode("utf-8"),
            key_serializer=lambda k: k.encode("utf-8") if k else None,
        )

        # 发送复杂对象
        complex_message = {
            "timestamp": datetime.now(timezone.utc),
            "data": {
                "numbers": [1, 2, 3.14, -5],
                "nested": {"boolean": True, "null_value": None, "unicode": "测试中文"},
                "set_data": {1, 2, 3},  # 会转换为列表
            },
        }

        producer.send(topic, key="serialization_test", value=complex_message)
        producer.flush()

        # 创建带反序列化的消费者
        consumer = KafkaConsumer(
            topic,
            bootstrap_servers=bootstrap_servers,
            auto_offset_reset="earliest",
            value_deserializer=lambda m: json.loads(m.decode("utf-8")),
            consumer_timeout_ms=5000,
            group_id="test_serialization",
        )

        # 消费并验证
        consumed_message = None
        for message in consumer:
            if message.key == b"serialization_test":
                consumed_message = message.value
                break

        # 验证序列化结果
        assert consumed_message is not None
        assert consumed_message["data"]["nested"]["boolean"] is True
        assert consumed_message["data"]["nested"]["unicode"] == "测试中文"
        assert isinstance(consumed_message["data"]["set_data"], list)

        # 清理
        producer.close()
        consumer.close()

    @pytest.mark.asyncio
    async def test_message_partitioning(self, test_kafka):
        """测试消息分区"""
        from kafka import KafkaProducer, KafkaConsumer

        topic = test_kafka["topics"][0]
        bootstrap_servers = test_kafka["bootstrap_servers"]

        # 创建生产者
        producer = KafkaProducer(
            bootstrap_servers=bootstrap_servers,
            value_serializer=lambda v: json.dumps(v).encode("utf-8"),
            key_serializer=lambda k: k.encode("utf-8") if k else None,
        )

        # 发送带不同键的消息（应该分布到不同分区）
        messages = [
            {"key": "A", "value": "Message for partition 0"},
            {"key": "B", "value": "Message for partition 1"},
            {"key": "C", "value": "Message for partition 2"},
            {"key": "A", "value": "Another message for partition 0"},
            {"key": "B", "value": "Another message for partition 1"},
        ]

        partition_info = []
        for msg in messages:
            future = producer.send(
                topic,
                key=msg["key"],
                value={"message": msg["value"], "key": msg["key"]},
            )
            _metadata = future.get(timeout=10)
            partition_info.append(
                {
                    "key": msg["key"],
                    "partition": metadata.partition,
                    "offset": metadata.offset,
                }
            )

        producer.flush()

        # 验证分区分配
        # 相同的键应该到相同的分区
        a_partitions = [p["partition"] for p in partition_info if p["key"] == "A"]
        b_partitions = [p["partition"] for p in partition_info if p["key"] == "B"]

        assert len(set(a_partitions)) == 1  # 所有 A 消息在同一分区
        assert len(set(b_partitions)) == 1  # 所有 B 消息在同一分区
        assert a_partitions[0] != b_partitions[0]  # A 和 B 在不同分区

    @pytest.mark.asyncio
    async def test_error_handling(self, test_kafka):
        """测试错误处理"""
        from kafka import KafkaProducer
        from kafka.errors import KafkaError
        import uuid

        topic = "non_existent_topic"
        bootstrap_servers = test_kafka["bootstrap_servers"]

        # 创建生产者
        producer = KafkaProducer(
            bootstrap_servers=bootstrap_servers,
            request_timeout_ms=5000,
            max_block_ms=5000,
        )

        # 尝试发送到不存在的主题
        try:
            future = producer.send(topic, key="test_error", value={"error": "test"})
            _metadata = future.get(timeout=10)
            # 如果主题不存在且设置了自动创建，这里可能成功
        except KafkaError as e:
            # 预期的错误
            assert "topic" in str(e).lower() or "broker" in str(e).lower()

        producer.close()

    @pytest.mark.asyncio
    async def test_concurrent_producers(self, test_kafka):
        """测试并发生产者"""
        from kafka import KafkaProducer

        topic = test_kafka["topics"][0]
        bootstrap_servers = test_kafka["bootstrap_servers"]

        # 创建多个生产者
        producers = []
        for i in range(3):
            producer = KafkaProducer(
                bootstrap_servers=bootstrap_servers,
                value_serializer=lambda v: json.dumps(v).encode("utf-8"),
                client_id=f"concurrent_producer_{i}",
            )
            producers.append(producer)

        # 并发发送消息
        async def send_messages(producer, producer_id):
            messages = []
            for i in range(10):
                message = {
                    "producer_id": producer_id,
                    "message_id": i,
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                }
                future = producer.send(
                    topic, key=f"producer_{producer_id}", value=message
                )
                _metadata = future.get(timeout=10)
                messages.append(metadata)
            return messages

        # 并发执行
        tasks = [
            send_messages(producers[0], 0),
            send_messages(producers[1], 1),
            send_messages(producers[2], 2),
        ]

        results = await asyncio.gather(*tasks)

        # 验证所有消息都发送成功
        total_messages = sum(len(r) for r in results)
        assert total_messages == 30

        # 清理
        for producer in producers:
            producer.close()

    @pytest.mark.asyncio
    async def test_consumer_groups(self, test_kafka):
        """测试消费者组"""
        from kafka import KafkaConsumer

        topic = test_kafka["topics"][0]
        bootstrap_servers = test_kafka["bootstrap_servers"]

        # 创建生产者发送消息
        producer = test_kafka["producer"]
        messages = [{"id": i, "data": f"Message {i}"} for i in range(10)]

        for msg in messages:
            producer.send(topic, key=str(msg["id"]), value=msg)
        producer.flush()

        # 创建两个消费者在同一组
        consumer1 = KafkaConsumer(
            topic,
            bootstrap_servers=bootstrap_servers,
            auto_offset_reset="earliest",
            value_deserializer=lambda m: json.loads(m.decode("utf-8")),
            group_id="test_group_partition",
        )

        consumer2 = KafkaConsumer(
            topic,
            bootstrap_servers=bootstrap_servers,
            auto_offset_reset="earliest",
            value_deserializer=lambda m: json.loads(m.decode("utf-8")),
            group_id="test_group_partition",
        )

        # 消费消息（每个消费者应该收到部分消息）
        consumed1 = []
        consumed2 = []

        # 简单消费（不保证精确分配）
        for _ in range(5):
            try:
                msg = next(consumer1)
                consumed1.append(msg.value)
            except StopIteration:
                break

        for _ in range(5):
            try:
                msg = next(consumer2)
                consumed2.append(msg.value)
            except StopIteration:
                break

        # 验证消息被消费
        total_consumed = len(consumed1) + len(consumed2)
        assert total_consumed > 0
        assert total_consumed <= 10

        # 清理
        consumer1.close()
        consumer2.close()
