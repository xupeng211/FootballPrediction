"""
 streaming_collector.py 测试文件
 测试 Kafka 流式数据收集器的异步操作和数据处理功能
"""
import pytest
from unittest.mock import Mock, patch, AsyncMock, MagicMock
import asyncio
import json
import sys
import os
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional

# 添加 src 目录到路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'src'))

# 清理Prometheus注册表以避免重复注册
try:
    from prometheus_client import REGISTRY
    # 清理所有收集器
    collectors = list(REGISTRY._collector_to_names.keys())
    for collector in collectors:
        REGISTRY.unregister(collector)
except ImportError:
    pass

# 模拟外部依赖
with patch.dict('sys.modules', {
    'aiohttp': Mock(),
    'confluent_kafka': Mock(),
    'prometheus_client': Mock(),
    'prometheus_client.registry': Mock(),
    'prometheus_client.core': Mock()
}):
    from data.collectors.streaming_collector import StreamingCollector, DataStream, StreamConfig


class TestStreamConfig:
    """测试 StreamConfig 配置类"""

    def test_stream_config_creation(self):
        """测试 StreamConfig 对象创建"""
        config = StreamConfig(
            bootstrap_servers="localhost:9092",
            topic="football_data",
            group_id="football_collector",
            auto_offset_reset="earliest",
            enable_auto_commit=True,
            session_timeout_ms=10000
        )

        assert config.bootstrap_servers == "localhost:9092"
        assert config.topic == "football_data"
        assert config.group_id == "football_collector"
        assert config.auto_offset_reset == "earliest"
        assert config.enable_auto_commit == True

    def test_stream_config_defaults(self):
        """测试 StreamConfig 默认值"""
        config = StreamConfig(
            bootstrap_servers="localhost:9092",
            topic="test_topic"
        )

        assert config.group_id == "default_consumer"
        assert config.auto_offset_reset == "latest"
        assert config.enable_auto_commit == True

    def test_stream_config_validation(self):
        """测试 StreamConfig 验证"""
        with pytest.raises(ValueError):
            StreamConfig(
                bootstrap_servers="",  # 空值
                topic="test_topic"
            )

        with pytest.raises(ValueError):
            StreamConfig(
                bootstrap_servers="localhost:9092",
                topic=""  # 空值
            )


class TestDataStream:
    """测试 DataStream 数据流类"""

    def test_data_stream_creation(self):
        """测试 DataStream 对象创建"""
        stream = DataStream(
            stream_id="stream_123",
            data_type="match_data",
            payload={"match_id": "match_456", "home_team": "Team A", "away_team": "Team B"},
            timestamp=datetime.now(),
            metadata={"source": "api", "version": "1.0"}
        )

        assert stream.stream_id == "stream_123"
        assert stream.data_type == "match_data"
        assert stream.payload["match_id"] == "match_456"
        assert stream.metadata["source"] == "api"

    def test_data_stream_serialization(self):
        """测试 DataStream 序列化"""
        stream = DataStream(
            stream_id="stream_123",
            data_type="match_data",
            payload={"match_id": "match_456"},
            timestamp=datetime.now(),
            metadata={"source": "api"}
        )

        stream_dict = stream.to_dict()
        assert stream_dict["stream_id"] == "stream_123"
        assert stream_dict["data_type"] == "match_data"
        assert "timestamp" in stream_dict

    def test_data_stream_deserialization(self):
        """测试 DataStream 反序列化"""
        stream_data = {
            "stream_id": "stream_123",
            "data_type": "match_data",
            "payload": {"match_id": "match_456"},
            "timestamp": datetime.now().isoformat(),
            "metadata": {"source": "api"}
        }

        stream = DataStream.from_dict(stream_data)
        assert stream.stream_id == "stream_123"
        assert stream.data_type == "match_data"
        assert stream.payload["match_id"] == "match_456"

    def test_data_stream_validation(self):
        """测试 DataStream 验证"""
        with pytest.raises(ValueError):
            DataStream(
                stream_id="",  # 空值
                data_type="match_data",
                payload={"match_id": "match_456"}
            )


class TestStreamingCollector:
    """测试 StreamingCollector 流式收集器"""

    def setup_method(self):
        """设置测试环境"""
        self.config = StreamConfig(
            bootstrap_servers="localhost:9092",
            topic="football_data",
            group_id="test_collector"
        )
        self.collector = StreamingCollector(self.config)

    @patch('data.collectors.streaming_collector.Producer')
    def test_collector_initialization(self, mock_producer):
        """测试收集器初始化"""
        mock_producer.return_value = Mock()

        collector = StreamingCollector(self.config)
        assert collector.config == self.config
        assert collector.is_running == False

    @patch('data.collectors.streaming_collector.Producer')
    def test_start_collector_success(self, mock_producer):
        """测试启动收集器成功"""
        mock_producer_instance = Mock()
        mock_producer.return_value = mock_producer_instance

        self.collector.start()
        assert self.collector.is_running == True
        mock_producer.assert_called_once()

    @patch('data.collectors.streaming_collector.Producer')
    def test_stop_collector(self, mock_producer):
        """测试停止收集器"""
        mock_producer_instance = Mock()
        mock_producer.return_value = mock_producer_instance

        self.collector.start()
        assert self.collector.is_running == True

        self.collector.stop()
        assert self.collector.is_running == False
        mock_producer_instance.flush.assert_called_once()

    @patch('data.collectors.streaming_collector.Producer')
    async def test_publish_message_success(self, mock_producer):
        """测试发布消息成功"""
        mock_producer_instance = Mock()
        mock_producer.return_value = mock_producer_instance
        mock_producer_instance.produce.return_value = None
        mock_producer_instance.flush.return_value = None

        self.collector.start()

        stream = DataStream(
            stream_id="stream_123",
            data_type="match_data",
            payload={"match_id": "match_456"},
            timestamp=datetime.now(),
            metadata={"source": "api"}
        )

        result = await self.collector.publish_message(stream)
        assert result is True
        mock_producer_instance.produce.assert_called_once()

    @patch('data.collectors.streaming_collector.Producer')
    async def test_publish_message_error(self, mock_producer):
        """测试发布消息错误"""
        mock_producer_instance = Mock()
        mock_producer.return_value = mock_producer_instance
        mock_producer_instance.produce.side_effect = KafkaException("Kafka error")

        self.collector.start()

        stream = DataStream(
            stream_id="stream_123",
            data_type="match_data",
            payload={"match_id": "match_456"},
            timestamp=datetime.now(),
            metadata={"source": "api"}
        )

        with pytest.raises(KafkaException):
            await self.collector.publish_message(stream)

    @patch('data.collectors.streaming_collector.Consumer')
    async def test_consume_messages_success(self, mock_consumer):
        """测试消费消息成功"""
        mock_consumer_instance = Mock()
        mock_consumer.return_value = mock_consumer_instance

        # 模拟消息
        mock_message = Mock()
        mock_message.value.return_value = json.dumps({
            "stream_id": "stream_123",
            "data_type": "match_data",
            "payload": {"match_id": "match_456"},
            "timestamp": datetime.now().isoformat(),
            "metadata": {"source": "api"}
        }).encode('utf-8')

        mock_consumer_instance.poll.return_value = mock_message

        self.collector.consumer = mock_consumer_instance

        messages = []
        async for message in self.collector.consume_messages(timeout=1.0):
            messages.append(message)
            break  # 只消费一条消息用于测试

        assert len(messages) == 1
        assert messages[0].stream_id == "stream_123"

    @patch('data.collectors.streaming_collector.Consumer')
    async def test_consume_messages_timeout(self, mock_consumer):
        """测试消费消息超时"""
        mock_consumer_instance = Mock()
        mock_consumer.return_value = mock_consumer_instance
        mock_consumer_instance.poll.return_value = None

        self.collector.consumer = mock_consumer_instance

        messages = []
        async for message in self.collector.consume_messages(timeout=1.0):
            messages.append(message)

        assert len(messages) == 0  # 超时应该返回空列表

    @patch('data.collectors.streaming_collector.Producer')
    def test_batch_publish_messages(self, mock_producer):
        """测试批量发布消息"""
        mock_producer_instance = Mock()
        mock_producer.return_value = mock_producer_instance

        self.collector.start()

        streams = [
            DataStream(
                stream_id=f"stream_{i}",
                data_type="match_data",
                payload={"match_id": f"match_{i}"},
                timestamp=datetime.now(),
                metadata={"source": "api"}
            )
            for i in range(5)
        ]

        async def batch_publish():
            results = []
            for stream in streams:
                result = await self.collector.publish_message(stream)
                results.append(result)
            return results

        results = asyncio.run(batch_publish())
        assert all(results) == True
        assert mock_producer_instance.produce.call_count == 5

    @patch('data.collectors.streaming_collector.Producer')
    async def test_concurrent_publishing(self, mock_producer):
        """测试并发发布"""
        mock_producer_instance = Mock()
        mock_producer.return_value = mock_producer_instance
        mock_producer_instance.produce.return_value = None

        self.collector.start()

        async def publish_concurrently():
            tasks = []
            for i in range(10):
                stream = DataStream(
                    stream_id=f"stream_{i}",
                    data_type="match_data",
                    payload={"match_id": f"match_{i}"},
                    timestamp=datetime.now(),
                    metadata={"source": "api"}
                )
                task = asyncio.create_task(self.collector.publish_message(stream))
                tasks.append(task)

            return await asyncio.gather(*tasks)

        results = await publish_concurrently()
        assert all(results) == True
        assert mock_producer_instance.produce.call_count == 10

    def test_message_validation(self):
        """测试消息验证"""
        valid_stream = DataStream(
            stream_id="stream_123",
            data_type="match_data",
            payload={"match_id": "match_456"},
            timestamp=datetime.now(),
            metadata={"source": "api"}
        )

        assert self.collector.validate_message(valid_stream) == True

        invalid_stream = DataStream(
            stream_id="",  # 无效ID
            data_type="match_data",
            payload={"match_id": "match_456"},
            timestamp=datetime.now(),
            metadata={"source": "api"}
        )

        assert self.collector.validate_message(invalid_stream) == False

    def test_error_handling(self):
        """测试错误处理"""
        # 测试Kafka连接错误
        with patch('data.collectors.streaming_collector.Producer') as mock_producer:
            mock_producer.side_effect = KafkaException("Connection failed")

            with pytest.raises(KafkaException):
                self.collector.start()

    def test_metrics_collection(self):
        """测试指标收集"""
        # 获取初始指标
        initial_metrics = self.collector.get_metrics()

        # 模拟一些操作
        self.collector.message_count = 10
        self.collector.error_count = 2

        final_metrics = self.collector.get_metrics()
        assert final_metrics["message_count"] == 10
        assert final_metrics["error_count"] == 2
        assert final_metrics["success_rate"] == 0.8  # (10-2)/10

    @patch('data.collectors.streaming_collector.Producer')
    def test_message_retry_mechanism(self, mock_producer):
        """测试消息重试机制"""
        mock_producer_instance = Mock()
        mock_producer.return_value = mock_producer_instance

        # 模拟前两次失败，第三次成功
        call_count = 0
        def mock_produce(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise KafkaException("Temporary failure")
            return None

        mock_producer_instance.produce.side_effect = mock_produce

        self.collector.start()

        stream = DataStream(
            stream_id="stream_123",
            data_type="match_data",
            payload={"match_id": "match_456"},
            timestamp=datetime.now(),
            metadata={"source": "api"}
        )

        # 设置重试次数
        self.collector.max_retries = 3

        result = asyncio.run(self.collector.publish_message_with_retry(stream))
        assert result is True
        assert call_count == 3

    @patch('data.collectors.streaming_collector.Producer')
    def test_message_batch_processing(self, mock_producer):
        """测试消息批处理"""
        mock_producer_instance = Mock()
        mock_producer.return_value = mock_producer_instance

        self.collector.start()

        # 创建批量消息
        batch_messages = [
            DataStream(
                stream_id=f"stream_{i}",
                data_type="match_data",
                payload={"match_id": f"match_{i}"},
                timestamp=datetime.now(),
                metadata={"source": "api"}
            )
            for i in range(100)
        ]

        async def process_batch():
            return await self.collector.process_batch(batch_messages)

        result = asyncio.run(process_batch())
        assert result["success_count"] == 100
        assert result["error_count"] == 0
        assert mock_producer_instance.produce.call_count == 100

    def test_stream_statistics(self):
        """测试流统计"""
        # 模拟统计数据
        self.collector.message_count = 1000
        self.collector.error_count = 50
        self.collector.bytes_sent = 1024 * 1024  # 1MB

        stats = self.collector.get_stream_statistics()
        assert stats["total_messages"] == 1000
        assert stats["total_errors"] == 50
        assert stats["total_bytes"] == 1024 * 1024
        assert stats["success_rate"] == 0.95

    @patch('data.collectors.streaming_collector.Producer')
    def test_connection_pool_management(self, mock_producer):
        """测试连接池管理"""
        mock_producer_instance = Mock()
        mock_producer.return_value = mock_producer_instance

        # 测试连接池创建
        self.collector.create_connection_pool(pool_size=5)
        assert len(self.collector.connection_pool) == 5

        # 测试连接池获取
        connection = self.collector.get_connection()
        assert connection is not None

        # 测试连接池释放
        self.collector.release_connection(connection)
        assert connection in self.collector.connection_pool

    @patch('data.collectors.streaming_collector.Producer')
    def test_health_check(self, mock_producer):
        """测试健康检查"""
        mock_producer_instance = Mock()
        mock_producer.return_value = mock_producer_instance

        self.collector.start()

        health = self.collector.health_check()
        assert health["status"] == "healthy"
        assert health["is_running"] == True
        assert "uptime" in health

    def test_configuration_validation(self):
        """测试配置验证"""
        # 测试有效配置
        valid_config = StreamConfig(
            bootstrap_servers="localhost:9092",
            topic="test_topic",
            group_id="test_group"
        )
        assert self.collector.validate_config(valid_config) == True

        # 测试无效配置
        invalid_config = StreamConfig(
            bootstrap_servers="",  # 无效
            topic="test_topic"
        )
        assert self.collector.validate_config(invalid_config) == False

    @patch('data.collectors.streaming_collector.Producer')
    def test_performance_monitoring(self, mock_producer):
        """测试性能监控"""
        mock_producer_instance = Mock()
        mock_producer.return_value = mock_producer_instance

        self.collector.start()

        # 记录性能指标
        self.collector.record_performance_metric("publish_time", 0.1)
        self.collector.record_performance_metric("consume_time", 0.05)

        metrics = self.collector.get_performance_metrics()
        assert "publish_time" in metrics
        assert "consume_time" in metrics
        assert metrics["publish_time"]["count"] >= 1


class TestStreamingCollectorIntegration:
    """测试 StreamingCollector 集成功能"""

    def setup_method(self):
        """设置测试环境"""
        self.config = StreamConfig(
            bootstrap_servers="localhost:9092",
            topic="football_data",
            group_id="test_collector"
        )
        self.collector = StreamingCollector(self.config)

    @patch('data.collectors.streaming_collector.Producer')
    @patch('data.collectors.streaming_collector.Consumer')
    async def test_end_to_end_flow(self, mock_consumer, mock_producer):
        """测试端到端流程"""
        # 设置生产者
        mock_producer_instance = Mock()
        mock_producer.return_value = mock_producer_instance
        mock_producer_instance.produce.return_value = None

        # 设置消费者
        mock_consumer_instance = Mock()
        mock_consumer.return_value = mock_consumer_instance

        # 模拟消息循环
        test_stream = DataStream(
            stream_id="stream_123",
            data_type="match_data",
            payload={"match_id": "match_456"},
            timestamp=datetime.now(),
            metadata={"source": "api"}
        )

        # 发布消息
        self.collector.start()
        await self.collector.publish_message(test_stream)

        # 消费消息
        mock_message = Mock()
        mock_message.value.return_value = json.dumps(test_stream.to_dict()).encode('utf-8')
        mock_consumer_instance.poll.return_value = mock_message
        self.collector.consumer = mock_consumer_instance

        consumed_messages = []
        async for message in self.collector.consume_messages(timeout=1.0):
            consumed_messages.append(message)
            break

        assert len(consumed_messages) == 1
        assert consumed_messages[0].stream_id == test_stream.stream_id

    def test_error_recovery_mechanism(self):
        """测试错误恢复机制"""
        # 测试连接失败恢复
        with patch('data.collectors.streaming_collector.Producer') as mock_producer:
            mock_producer.side_effect = [KafkaException("Connection failed"), Mock()]

            # 第一次尝试失败
            with pytest.raises(KafkaException):
                self.collector.start()

            # 第二次尝试成功
            self.collector.start()
            assert self.collector.is_running == True

    def test_resource_cleanup(self):
        """测试资源清理"""
        # 测试资源正确清理
        with patch('data.collectors.streaming_collector.Producer') as mock_producer:
            mock_producer_instance = Mock()
            mock_producer.return_value = mock_producer_instance

            self.collector.start()
            assert self.collector.is_running == True

            self.collector.stop()
            assert self.collector.is_running == False
            mock_producer_instance.flush.assert_called_once()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])