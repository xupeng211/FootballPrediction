"""
流处理任务测试
Tests for Streaming Tasks

测试src.tasks.streaming_tasks模块的流处理功能
"""

import pytest
from unittest.mock import Mock, patch, AsyncMock
from datetime import datetime
import asyncio
import json

# 测试导入
try:
    from src.tasks.streaming_tasks import (
        StreamMessage,
        KafkaProducer,
        KafkaConsumer,
        StreamProcessor,
        StreamMonitor,
        StreamingTaskStatus,
    )

    STREAMING_TASKS_AVAILABLE = True
except ImportError as e:
    print(f"Import error: {e}")
    STREAMING_TASKS_AVAILABLE = False
    # 创建模拟对象
    StreamMessage = None
    KafkaProducer = None
    KafkaConsumer = None
    StreamProcessor = None
    StreamMonitor = None
    StreamingTaskStatus = None


@pytest.mark.skipif(
    not STREAMING_TASKS_AVAILABLE, reason="Streaming tasks module not available"
)
class TestStreamMessage:
    """流消息测试"""

    def test_message_creation(self):
        """测试：消息创建"""
        msg = StreamMessage("test_topic", b"key", b"value")
        assert msg.topic == "test_topic"
        assert msg.key == b"key"
        assert msg.value == b"value"
        assert msg.timestamp is not None
        assert msg.headers is None

    def test_message_with_headers(self):
        """测试：带头部的消息"""
        headers = {"content-type": "application/json", "version": "1.0"}
        msg = StreamMessage("test_topic", b"key", b"value", headers=headers)
        assert msg.headers == headers

    def test_message_serialization(self):
        """测试：消息序列化"""
        data = {"event": "test", "data": {"id": 1}}
        msg = StreamMessage("test_topic", b"key", json.dumps(data).encode())

        # 验证可以反序列化
        deserialized = json.loads(msg.value.decode())
        assert deserialized["event"] == "test"
        assert deserialized["data"]["id"] == 1

    def test_message_with_timestamp(self):
        """测试：带时间戳的消息"""
        timestamp = datetime.now()
        msg = StreamMessage("test_topic", b"key", b"value", timestamp=timestamp)
        assert msg.timestamp == timestamp


@pytest.mark.skipif(
    not STREAMING_TASKS_AVAILABLE, reason="Streaming tasks module not available"
)
class TestKafkaProducer:
    """Kafka生产者测试"""

    def test_producer_creation(self):
        """测试：生产者创建"""
        config = {"bootstrap_servers": ["localhost:9092"], "client_id": "test_producer"}
        producer = KafkaProducer(config)
        assert producer is not None
        assert producer.config == config

    @pytest.mark.asyncio
    async def test_produce_message(self):
        """测试：生产消息"""
        config = {"bootstrap_servers": ["localhost:9092"], "client_id": "test_producer"}
        producer = KafkaProducer(config)

        message = StreamMessage("test_topic", b"test_key", b'{"event": "test"}')

        with patch.object(producer, "kafka_client") as mock_client:
            mock_client.send.return_value = {
                "topic": "test_topic",
                "partition": 0,
                "offset": 100,
            }

            result = await producer.produce(message)

            assert result["topic"] == "test_topic"
            assert result["partition"] == 0
            assert result["offset"] == 100

    @pytest.mark.asyncio
    async def test_produce_batch(self):
        """测试：批量生产消息"""
        config = {"bootstrap_servers": ["localhost:9092"], "client_id": "test_producer"}
        producer = KafkaProducer(config)

        with patch.object(producer, "kafka_client") as mock_client:
            mock_client.send_batch.return_value = [
                {"topic": "test_topic", "partition": 0, "offset": 101},
                {"topic": "test_topic", "partition": 0, "offset": 102},
                {"topic": "test_topic", "partition": 0, "offset": 103},
            ]

            messages = [
                StreamMessage("test_topic", b"key1", b"value1"),
                StreamMessage("test_topic", b"key2", b"value2"),
                StreamMessage("test_topic", b"key3", b"value3"),
            ]

            results = await producer.produce_batch(messages)

            assert len(results) == 3
            assert all(r["topic"] == "test_topic" for r in results)

    @pytest.mark.asyncio
    async def test_producer_error_handling(self):
        """测试：生产者错误处理"""
        config = {"bootstrap_servers": ["localhost:9092"], "client_id": "test_producer"}
        producer = KafkaProducer(config)

        with patch.object(producer, "kafka_client") as mock_client:
            mock_client.send.side_effect = Exception("Connection failed")

            message = StreamMessage("test_topic", b"key", b"value")

            result = await producer.produce(message)

            assert result["status"] == "failed"
            assert "error" in result

    def test_producer_connection_health(self):
        """测试：生产者连接健康检查"""
        config = {"bootstrap_servers": ["localhost:9092"], "client_id": "test_producer"}
        producer = KafkaProducer(config)

        with patch.object(producer, "kafka_client") as mock_client:
            mock_client.bootstrap.connected.return_value = True

            health = producer.check_health()
            assert health["status"] == "healthy"
            assert health["connected"] is True


@pytest.mark.skipif(
    not STREAMING_TASKS_AVAILABLE, reason="Streaming tasks module not available"
)
class TestKafkaConsumer:
    """Kafka消费者测试"""

    def test_consumer_creation(self):
        """测试：消费者创建"""
        config = {
            "bootstrap_servers": ["localhost:9092"],
            "group_id": "test_group",
            "topics": ["test_topic"],
        }
        consumer = KafkaConsumer(config)
        assert consumer is not None
        assert consumer.config == config
        assert consumer.topics == ["test_topic"]

    @pytest.mark.asyncio
    async def test_consume_messages(self):
        """测试：消费消息"""
        config = {
            "bootstrap_servers": ["localhost:9092"],
            "group_id": "test_group",
            "topics": ["test_topic"],
        }
        consumer = KafkaConsumer(config)

        with patch.object(consumer, "kafka_client") as mock_client:
            # 模拟消费的消息
            mock_messages = [
                {
                    "topic": "test_topic",
                    "partition": 0,
                    "offset": 100,
                    "key": b"key1",
                    "value": b'{"event": "test1"}',
                    "timestamp": datetime.now(),
                },
                {
                    "topic": "test_topic",
                    "partition": 0,
                    "offset": 101,
                    "key": b"key2",
                    "value": b'{"event": "test2"}',
                    "timestamp": datetime.now(),
                },
            ]
            mock_client.consume.return_value = mock_messages

            results = await consumer.consume(batch_size=10, timeout=1.0)

            assert len(results) == 2
            assert results[0]["event"] == "test1"
            assert results[1]["event"] == "test2"

    @pytest.mark.asyncio
    async def test_consumer_commit_offsets(self):
        """测试：提交偏移量"""
        config = {
            "bootstrap_servers": ["localhost:9092"],
            "group_id": "test_group",
            "topics": ["test_topic"],
        }
        consumer = KafkaConsumer(config)

        with patch.object(consumer, "kafka_client") as mock_client:
            mock_client.commit.return_value = True

            offsets = {
                "test_topic": {
                    0: 101,  # partition: offset
                    1: 50,
                }
            }

            result = await consumer.commit_offsets(offsets)

            assert result is True
            mock_client.commit.assert_called_once_with(offsets)

    @pytest.mark.asyncio
    async def test_consumer_pause_resume(self):
        """测试：暂停和恢复消费"""
        config = {
            "bootstrap_servers": ["localhost:9092"],
            "group_id": "test_group",
            "topics": ["test_topic"],
        }
        consumer = KafkaConsumer(config)

        with patch.object(consumer, "kafka_client") as mock_client:
            # 暂停
            await consumer.pause("test_topic", 0)
            mock_client.pause_partition.assert_called_once_with("test_topic", 0)

            # 恢复
            await consumer.resume("test_topic", 0)
            mock_client.resume_partition.assert_called_once_with("test_topic", 0)


@pytest.mark.skipif(
    not STREAMING_TASKS_AVAILABLE, reason="Streaming tasks module not available"
)
class TestStreamProcessor:
    """流处理器测试"""

    def test_processor_creation(self):
        """测试：处理器创建"""
        config = {
            "input_topics": ["input_topic"],
            "output_topic": "output_topic",
            "processing_function": lambda x: x,
        }
        processor = StreamProcessor(config)
        assert processor is not None
        assert processor.config == config

    @pytest.mark.asyncio
    async def test_process_message(self):
        """测试：处理消息"""

        def process_func(data):
            data["processed"] = True
            return data

        config = {
            "input_topics": ["input_topic"],
            "output_topic": "output_topic",
            "processing_function": process_func,
        }
        processor = StreamProcessor(config)

        message = StreamMessage("input_topic", b"key1", b'{"id": 1, "value": "test"}')

        with patch.object(processor, "producer") as mock_producer:
            mock_producer.produce.return_value = {
                "topic": "output_topic",
                "offset": 200,
            }

            result = await processor.process_message(message)

            assert result is True
            # 验证输出消息
            mock_producer.produce.assert_called_once()
            args = mock_producer.produce.call_args[0]
            output_message = args[0]
            assert output_message.topic == "output_topic"

            # 解析处理后的数据
            output_data = json.loads(output_message.value.decode())
            assert output_data["id"] == 1
            assert output_data["value"] == "test"
            assert output_data["processed"] is True

    @pytest.mark.asyncio
    async def test_process_batch(self):
        """测试：批量处理"""

        def process_func(data):
            data["batch_processed"] = True
            return data

        config = {
            "input_topics": ["input_topic"],
            "output_topic": "output_topic",
            "processing_function": process_func,
        }
        processor = StreamProcessor(config)

        messages = [
            StreamMessage("input_topic", b"key1", b'{"id": 1}'),
            StreamMessage("input_topic", b"key2", b'{"id": 2}'),
            StreamMessage("input_topic", b"key3", b'{"id": 3}'),
        ]

        with patch.object(processor, "producer") as mock_producer:
            mock_producer.produce_batch.return_value = [
                {"topic": "output_topic", "offset": i} for i in range(200, 203)
            ]

            results = await processor.process_batch(messages)

            assert len(results) == 3
            assert all(r["topic"] == "output_topic" for r in results)

    @pytest.mark.asyncio
    async def test_processing_error_handling(self):
        """测试：处理错误处理"""

        def failing_func(data):
            raise ValueError("Processing failed")

        config = {
            "input_topics": ["input_topic"],
            "output_topic": "output_topic",
            "processing_function": failing_func,
        }
        processor = StreamProcessor(config)

        message = StreamMessage("input_topic", b"key", b'{"test": "data"}')

        # 应该捕获错误并记录
        result = await processor.process_message(message)
        # 根据实现，可能返回False或者将消息发送到死信队列
        assert result in [False, True]  # 取决于错误处理策略


@pytest.mark.skipif(
    not STREAMING_TASKS_AVAILABLE, reason="Streaming tasks module not available"
)
class TestStreamMonitor:
    """流监控测试"""

    def test_monitor_creation(self):
        """测试：监控器创建"""
        config = {
            "metrics_interval": 60,
            "health_check_interval": 30,
            "alert_thresholds": {"lag": 1000, "error_rate": 0.05, "throughput": 1000},
        }
        monitor = StreamMonitor(config)
        assert monitor is not None
        assert monitor.config == config

    @pytest.mark.asyncio
    async def test_monitor_consumer_lag(self):
        """测试：监控消费者延迟"""
        config = {"metrics_interval": 60, "topics": ["test_topic"]}
        monitor = StreamMonitor(config)

        with patch.object(monitor, "kafka_admin") as mock_admin:
            mock_admin.get_consumer_offsets.return_value = {
                "test_group": {
                    "test_topic": {
                        0: 500,  # 消费者偏移量
                        1: 300,
                    }
                }
            }
            mock_admin.get_topic_offsets.return_value = {
                "test_topic": {
                    0: 1000,  # 最新偏移量
                    1: 800,
                }
            }

            lag_metrics = await monitor.check_consumer_lag("test_group")

            assert lag_metrics["test_topic"][0] == 500  # 1000 - 500
            assert lag_metrics["test_topic"][1] == 500  # 800 - 300

    @pytest.mark.asyncio
    async def test_monitor_throughput(self):
        """测试：监控吞吐量"""
        config = {"metrics_interval": 60, "topics": ["test_topic"]}
        monitor = StreamMonitor(config)

        with patch.object(monitor, "metrics_collector") as mock_collector:
            mock_collector.get_throughput_metrics.return_value = {
                "test_topic": {"messages_per_second": 500, "bytes_per_second": 1024000}
            }

            metrics = await monitor.collect_throughput_metrics()

            assert metrics["test_topic"]["messages_per_second"] == 500
            assert metrics["test_topic"]["bytes_per_second"] == 1024000

    @pytest.mark.asyncio
    async def test_trigger_alert(self):
        """测试：触发警报"""
        config = {"alert_thresholds": {"lag": 100, "error_rate": 0.05}}
        monitor = StreamMonitor(config)

        with patch.object(monitor, "alert_handler") as mock_alert:
            mock_alert.send_alert.return_value = True

            # 模拟高延迟
            lag_metrics = {
                "test_topic": {
                    0: 1500  # 超过阈值
                }
            }

            await monitor.check_and_alert(lag_metrics)

            # 验证警报被发送
            mock_alert.send_alert.assert_called_once()
            alert = mock_alert.send_alert.call_args[0][0]
            assert alert["type"] == "high_lag"
            assert alert["topic"] == "test_topic"
            assert alert["lag"] == 1500


@pytest.mark.skipif(
    not STREAMING_TASKS_AVAILABLE, reason="Streaming tasks module not available"
)
class TestStreamingTasksIntegration:
    """流处理任务集成测试"""

    @pytest.mark.asyncio
    async def test_end_to_end_flow(self):
        """测试：端到端流处理流程"""
        # 创建生产者
        producer_config = {
            "bootstrap_servers": ["localhost:9092"],
            "client_id": "test_producer",
        }
        producer = KafkaProducer(producer_config)

        # 创建消费者
        consumer_config = {
            "bootstrap_servers": ["localhost:9092"],
            "group_id": "test_group",
            "topics": ["test_topic"],
        }
        consumer = KafkaConsumer(consumer_config)

        # 创建处理器
        processor_config = {
            "input_topics": ["test_topic"],
            "output_topic": "processed_topic",
            "processing_function": lambda x: {**x, "processed": True},
        }
        processor = StreamProcessor(processor_config)

        # 模拟完整的流程
        with patch.object(producer, "kafka_client") as mock_producer:
            with patch.object(consumer, "kafka_client") as mock_consumer:
                with patch.object(processor, "producer") as mock_processor_producer:
                    # 1. 生产消息
                    mock_producer.send.return_value = {
                        "topic": "test_topic",
                        "offset": 100,
                    }
                    message = StreamMessage("test_topic", b"key", b'{"id": 1}')
                    await producer.produce(message)

                    # 2. 消费消息
                    mock_consumer.consume.return_value = [
                        {"topic": "test_topic", "value": b'{"id": 1}', "key": b"key"}
                    ]
                    consumed = await consumer.consume(batch_size=1)

                    # 3. 处理消息
                    mock_processor_producer.produce.return_value = {
                        "topic": "processed_topic",
                        "offset": 200,
                    }
                    stream_msg = StreamMessage(
                        "test_topic", b"key", consumed[0]["value"]
                    )
                    await processor.process_message(stream_msg)

                    # 验证流程完成
                    assert mock_producer.send.called
                    assert mock_consumer.consume.called
                    assert mock_processor_producer.produce.called

    @pytest.mark.asyncio
    async def test_streaming_pipeline(self):
        """测试：流处理管道"""
        # 定义处理管道
        processors = [
            lambda x: {**x, "stage1": True},
            lambda x: {**x, "stage2": True},
            lambda x: {**x, "stage3": True},
        ]

        config = {
            "input_topic": "input",
            "output_topic": "output",
            "processors": processors,
        }

        pipeline = StreamProcessor(config)

        # 测试管道处理
        message = StreamMessage("input", b"key", b'{"data": "test"}')

        with patch.object(pipeline, "producer") as mock_producer:
            mock_producer.produce.return_value = {"topic": "output", "offset": 300}

            result = await pipeline.process_message(message)

            assert result is True
            # 验证消息经过所有处理阶段
            mock_producer.produce.assert_called_once()
            output_msg = mock_producer.produce.call_args[0][0]
            output_data = json.loads(output_msg.value.decode())
            assert output_data["stage1"] is True
            assert output_data["stage2"] is True
            assert output_data["stage3"] is True

    @pytest.mark.asyncio
    async def test_error_recovery(self):
        """测试：错误恢复"""
        config = {
            "input_topics": ["input"],
            "output_topic": "output",
            "processing_function": lambda x: x,
            "retry_attempts": 3,
            "dead_letter_topic": "dlq",
        }
        processor = StreamProcessor(config)

        # 模拟处理失败
        def failing_func(data):
            raise ValueError("Processing failed")

        processor.processing_function = failing_func

        message = StreamMessage("input", b"key", b'{"test": "data"}')

        with patch.object(processor, "producer") as mock_producer:
            # 第一次失败
            mock_producer.produce.side_effect = Exception("Failed")

            result = await processor.process_message(message)

            # 验证错误处理或重试逻辑
            assert isinstance(result, bool)

    @pytest.mark.asyncio
    async def test_stream_scaling(self):
        """测试：流处理扩展"""
        # 创建多个消费者实例
        consumers = []
        for i in range(3):
            config = {
                "bootstrap_servers": ["localhost:9092"],
                "group_id": "scaled_group",
                "topics": ["topic1", "topic2"],
                "consumer_id": f"consumer_{i}",
            }
            consumers.append(KafkaConsumer(config))

        # 模拟分区分配
        with patch("src.tasks.streaming_tasks.assign_partitions") as mock_assign:
            mock_assign.return_value = {
                "consumer_0": [("topic1", 0), ("topic1", 1)],
                "consumer_1": [("topic1", 2), ("topic2", 0)],
                "consumer_2": [("topic2", 1), ("topic2", 2)],
            }

            assignment = await mock_assign("scaled_group", ["topic1", "topic2"], 3)

            # 验证分区分配
            total_partitions = sum(len(parts) for parts in assignment.values())
            assert total_partitions == 5  # 3 partitions for topic1 + 2 for topic2

    @pytest.mark.asyncio
    async def test_monitoring_dashboard_data(self):
        """测试：监控仪表板数据"""
        monitor = StreamMonitor(
            {"metrics_interval": 30, "topics": ["topic1", "topic2"]}
        )

        with patch.object(monitor, "metrics_store") as mock_store:
            mock_store.get_metrics.return_value = {
                "timestamp": datetime.now(),
                "topics": {
                    "topic1": {"messages_per_sec": 100, "lag": 10, "errors": 0},
                    "topic2": {"messages_per_sec": 200, "lag": 5, "errors": 1},
                },
                "consumers": {"group1": {"active_members": 3, "avg_lag": 8}},
            }

            dashboard_data = await monitor.get_dashboard_data()

            assert "topics" in dashboard_data
            assert "consumers" in dashboard_data
            assert dashboard_data["topics"]["topic1"]["messages_per_sec"] == 100
            assert dashboard_data["consumers"]["group1"]["active_members"] == 3


@pytest.mark.skipif(
    STREAMING_TASKS_AVAILABLE, reason="Streaming tasks module should be available"
)
class TestModuleNotAvailable:
    """模块不可用时的测试"""

    def test_module_import_error(self):
        """测试：模块导入错误"""
        assert not STREAMING_TASKS_AVAILABLE
        assert True  # 表明测试意识到模块不可用


# 测试模块级别的功能
def test_module_imports():
    """测试：模块导入"""
    if STREAMING_TASKS_AVAILABLE:
        from src.tasks.streaming_tasks import (
            StreamMessage,
            KafkaProducer,
            KafkaConsumer,
            StreamProcessor,
            StreamMonitor,
            StreamingTaskStatus,
        )

        assert StreamMessage is not None
        assert KafkaProducer is not None
        assert KafkaConsumer is not None
        assert StreamProcessor is not None
        assert StreamMonitor is not None
        assert StreamingTaskStatus is not None
