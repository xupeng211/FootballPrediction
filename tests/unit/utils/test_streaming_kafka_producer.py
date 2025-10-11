"""
Kafka生产者测试
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch, mock_open
import asyncio
import json
from typing import Any, Dict, Optional
from src.streaming.kafka_producer_simple import KafkaMessageProducer
from src.core.exceptions import StreamingError


# 模拟kafka错误
class KafkaError(Exception):
    pass


class KafkaTimeoutError(Exception):
    pass


class TestKafkaMessageProducer:
    """Kafka消息生产者测试"""

    @pytest.fixture
    def mock_kafka_producer(self):
        """模拟Kafka生产者"""
        mock_producer = MagicMock()
        mock_producer.send = AsyncMock(return_value=MagicMock())
        mock_producer.flush = AsyncMock(return_value=None)
        mock_producer.start = AsyncMock()
        mock_producer.stop = AsyncMock()
        return mock_producer

    @pytest.fixture
    def producer(self):
        """创建生产者实例"""
        config = {"bootstrap_servers": ["localhost:9092"], "topic": "test_topic"}
        producer = KafkaMessageProducer(config)
        return producer

    @pytest.mark.asyncio
    async def test_producer_initialization(self, producer):
        """测试生产者初始化"""
        assert producer.bootstrap_servers == ["localhost:9092"]
        assert producer.topic == "test_topic"
        # producer在初始化时是None，需要在start后设置
        assert producer.producer is None

    @pytest.mark.asyncio
    async def test_start_producer(self, producer):
        """测试启动生产者"""
        await producer.start()
        assert producer.producer is not None

    @pytest.mark.asyncio
    async def test_stop_producer(self, producer):
        """测试停止生产者"""
        await producer.start()
        await producer.stop()
        assert producer.producer is None

    @pytest.mark.asyncio
    async def test_send_message(self, producer, mock_kafka_producer):
        """测试发送消息"""
        # 启动生产者
        await producer.start()

        # 发送消息
        message = {"key": "test_key", "value": {"data": "test"}}
        result = await producer.send_message(message)

        # 验证调用
        mock_kafka_producer.send.assert_called_once_with(
            topic="test_topic", key=b"test_key", value=b'{"data": "test"}'
        )
        assert result is not None

    @pytest.mark.asyncio
    async def test_send_message_without_key(self, producer, mock_kafka_producer):
        """测试发送不带键的消息"""
        await producer.start()

        message = {"value": {"data": "test"}}
        await producer.send_message(message)

        mock_kafka_producer.send.assert_called_once_with(
            topic="test_topic", key=None, value=b'{"data": "test"}'
        )

    @pytest.mark.asyncio
    async def test_send_message_with_headers(self, producer, mock_kafka_producer):
        """测试发送带头部的消息"""
        await producer.start()

        message = {
            "key": "test_key",
            "value": {"data": "test"},
            "headers": {"source": "api", "version": "1.0"},
        }
        await producer.send_message(message)

        # 验证头部被正确处理
        call_args = mock_kafka_producer.send.call_args
        assert call_args.kwargs["topic"] == "test_topic"
        assert call_args.kwargs["key"] == b"test_key"
        assert call_args.kwargs["value"] == b'{"data": "test"}'
        assert "headers" in call_args.kwargs

    @pytest.mark.asyncio
    async def test_send_message_error(self, producer, mock_kafka_producer):
        """测试发送消息错误"""
        await producer.start()

        # 模拟发送失败
        mock_kafka_producer.send.side_effect = KafkaError("Connection failed")

        message = {"value": {"data": "test"}}
        with pytest.raises(StreamingError, match="Failed to send message"):
            await producer.send_message(message)

    @pytest.mark.asyncio
    async def test_send_message_timeout(self, producer, mock_kafka_producer):
        """测试发送消息超时"""
        await producer.start()

        # 模拟超时
        mock_kafka_producer.send.side_effect = KafkaTimeoutError("Timeout")

        message = {"value": {"data": "test"}}
        with pytest.raises(StreamingError, match="Timeout while sending message"):
            await producer.send_message(message)

    @pytest.mark.asyncio
    async def test_send_batch_messages(self, producer, mock_kafka_producer):
        """测试批量发送消息"""
        await producer.start()

        messages = [
            {"key": "key1", "value": {"data": "message1"}},
            {"key": "key2", "value": {"data": "message2"}},
            {"value": {"data": "message3"}},
        ]

        results = await producer.send_batch(messages)

        # 验证发送了3条消息
        assert mock_kafka_producer.send.call_count == 3
        assert len(results) == 3

    @pytest.mark.asyncio
    async def test_flush_messages(self, producer, mock_kafka_producer):
        """测试刷新消息缓冲区"""
        await producer.start()
        await producer.flush()

        mock_kafka_producer.flush.assert_called_once()

    @pytest.mark.asyncio
    async def test_context_manager(self, producer, mock_kafka_producer):
        """测试上下文管理器"""
        async with producer:
            pass

        mock_kafka_producer.start.assert_called_once()
        mock_kafka_producer.stop.assert_called_once()

    def test_serialize_message(self, producer):
        """测试消息序列化"""
        message = {"key": "test", "value": {"data": "测试"}}
        serialized = producer._serialize_message(message)

        assert serialized["key"] == b"test"
        assert serialized["value"] == b'{"data": "\\u6d4b\\u8bd5"}'

    def test_serialize_none_message(self, producer):
        """测试序列化None消息"""
        with pytest.raises(StreamingError, match="Message cannot be None"):
            producer._serialize_message(None)

    def test_serialize_invalid_message(self, producer):
        """测试序列化无效消息"""
        with pytest.raises(StreamingError, match="Message must have 'value' field"):
            producer._serialize_message({"key": "test"})

    def test_prepare_headers(self, producer):
        """测试准备头部"""
        headers = {"source": "api", "version": "1.0"}
        prepared = producer._prepare_headers(headers)

        assert isinstance(prepared, list)
        assert len(prepared) == 2
        assert ("source", b"api") in prepared
        assert ("version", b"1.0") in prepared

    def test_prepare_empty_headers(self, producer):
        """测试准备空头部"""
        prepared = producer._prepare_headers(None)
        assert prepared is None

        prepared = producer._prepare_headers({})
        assert prepared == []

    @pytest.mark.asyncio
    async def test_send_with_partition(self, producer, mock_kafka_producer):
        """测试发送到指定分区"""
        await producer.start()

        message = {"key": "test", "value": {"data": "test"}, "partition": 1}
        await producer.send_message(message)

        call_args = mock_kafka_producer.send.call_args
        assert call_args.kwargs["partition"] == 1

    @pytest.mark.asyncio
    async def test_send_with_timestamp(self, producer, mock_kafka_producer):
        """测试发送带时间戳的消息"""
        await producer.start()

        import time

        timestamp = int(time.time() * 1000)
        message = {"value": {"data": "test"}, "timestamp_ms": timestamp}
        await producer.send_message(message)

        call_args = mock_kafka_producer.send.call_args
        assert call_args.kwargs["timestamp_ms"] == timestamp

    def test_validate_config(self):
        """测试配置验证"""
        # 有效配置
        valid_config = {"bootstrap_servers": ["localhost:9092"], "topic": "test_topic"}
        producer = KafkaMessageProducer(valid_config)
        assert producer.bootstrap_servers == ["localhost:9092"]

        # 无效配置（缺少必要字段）
        with pytest.raises(StreamingError, match="Missing required config"):
            KafkaMessageProducer({})

    @pytest.mark.asyncio
    async def test_send_string_value(self, producer, mock_kafka_producer):
        """测试发送字符串值"""
        await producer.start()

        message = {"value": "simple string"}
        await producer.send_message(message)

        call_args = mock_kafka_producer.send.call_args
        assert call_args.kwargs["value"] == b"simple string"

    @pytest.mark.asyncio
    async def test_send_bytes_value(self, producer, mock_kafka_producer):
        """测试发送字节值"""
        await producer.start()

        message = {"value": b"binary data"}
        await producer.send_message(message)

        call_args = mock_kafka_producer.send.call_args
        assert call_args.kwargs["value"] == b"binary data"

    @pytest.mark.asyncio
    async def test_send_compressed_message(self, producer, mock_kafka_producer):
        """测试发送压缩消息"""
        await producer.start()

        message = {"value": {"data": "large message"}, "compression_type": "gzip"}
        await producer.send_message(message)

        # 验证消息被处理
        call_args = mock_kafka_producer.send.call_args
        assert call_args.kwargs["value"] is not None

    @pytest.mark.asyncio
    async def test_retry_on_failure(self, producer, mock_kafka_producer):
        """测试失败重试"""
        await producer.start()

        # 前两次失败，第三次成功
        mock_kafka_producer.send.side_effect = [
            KafkaError("Temporary failure"),
            KafkaError("Temporary failure"),
            MagicMock(),
        ]

        message = {"value": {"data": "test"}}
        result = await producer.send_message(message, retries=3)

        assert result is not None
        assert mock_kafka_producer.send.call_count == 3

    @pytest.mark.asyncio
    async def test_send_metrics(self, producer, mock_kafka_producer):
        """测试发送指标消息"""
        await producer.start()

        metrics = {
            "name": "request_count",
            "value": 100,
            "timestamp": "2024-01-01T00:00:00Z",
            "tags": {"service": "api", "status": "200"},
        }
        await producer.send_metrics(metrics)

        call_args = mock_kafka_producer.send.call_args
        assert call_args.kwargs["topic"] == "test_topic"

    @pytest.mark.asyncio
    async def test_send_event(self, producer, mock_kafka_producer):
        """测试发送事件消息"""
        await producer.start()

        event = {
            "event_id": "evt_123",
            "event_type": "match_created",
            "aggregate_id": "match_456",
            "data": {"home_team": "Team A", "away_team": "Team B"},
            "occurred_at": "2024-01-01T12:00:00Z",
        }
        await producer.send_event(event)

        call_args = mock_kafka_producer.send.call_args
        assert call_args.kwargs["key"] == b"match_456"
        assert b"event_type" in call_args.kwargs["value"]

    def test_get_producer_stats(self, producer):
        """测试获取生产者统计"""
        stats = producer.get_stats()
        assert "messages_sent" in stats
        assert "errors" in stats
        assert stats["messages_sent"] == 0
        assert stats["errors"] == 0
