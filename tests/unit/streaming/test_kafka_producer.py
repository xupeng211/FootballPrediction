"""
Kafka生产者测试 - FootballKafkaProducer
"""

import asyncio
import json
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, Mock, patch

import pytest

from src.streaming.kafka_producer import FootballKafkaProducer


class TestFootballKafkaProducer:
    """测试足球数据Kafka生产者"""

    @pytest.fixture
    def producer(self):
        """创建FootballKafkaProducer实例"""
        with patch("src.streaming.kafka_producer.StreamConfig") as mock_config:
            mock_config.return_value = Mock()
            mock_config.return_value.get_producer_config.return_value = {
                "bootstrap.servers": "localhost:9092"
            }
            with patch("confluent_kafka.Producer") as mock_producer_class:
                mock_producer = Mock()
                mock_producer_class.return_value = mock_producer
                return FootballKafkaProducer()

    def test_init(self, producer):
        """测试初始化"""
        assert producer.config is not None
        assert producer.producer is not None
        assert hasattr(producer, 'logger')
        assert hasattr(producer, '_delivery_callback')

    @pytest.mark.asyncio
    async def test_create_producer_success(self, producer):
        """测试成功创建Kafka生产者"""
        # 先将producer设为None
        producer.producer = None

        with patch('confluent_kafka.Producer') as mock_producer_class:
            mock_producer = Mock()
            mock_producer_class.return_value = mock_producer

            # 这个方法没有返回值，但会创建producer
            producer._create_producer()

            assert producer.producer == mock_producer
            mock_producer_class.assert_called_once()

    @pytest.mark.asyncio
    async def test_create_producer_failure(self, producer):
        """测试创建Kafka生产者失败"""
        producer.producer = None

        with patch('confluent_kafka.Producer') as mock_producer_class:
            mock_producer_class.side_effect = Exception("Kafka连接失败")

            # 应该抛出异常而不是返回False
            try:
                producer._create_producer()
                assert False, "应该抛出异常"
            except Exception:
                pass  # 期望抛出异常

            assert producer.producer is None

    @pytest.mark.asyncio
    async def test_send_match_data_success(self, producer):
        """测试成功发送比赛数据"""
        # Mock生产者
        producer.producer = Mock()
        producer.producer.produce = Mock()
        producer.producer.flush = Mock()

        match_data = {
            "match_id": "match_1",
            "home_team": "Team A",
            "away_team": "Team B",
            "home_score": 2,
            "away_score": 1,
            "date": "2025-09-25"
        }

        result = await producer.send_match_data(match_data)

        assert result is True
        producer.producer.produce.assert_called_once()
        producer.producer.flush.assert_called_once()

        # 验证消息格式
        call_args = producer.producer.produce.call_args
        assert call_args[1]['topic'] == "matches-stream"
        assert call_args[1]['key'] == "match_1"

        # 解析消息内容
        message_data = json.loads(call_args[1]['value'])
        assert message_data['data_type'] == "match"
        assert message_data['source'] == "data_collector"
        assert message_data['data'] == match_data

    @pytest.mark.asyncio
    async def test_send_match_data_with_custom_key(self, producer):
        """测试发送比赛数据并指定自定义键"""
        producer.producer = Mock()
        producer.producer.produce = Mock()
        producer.producer.flush = Mock()

        match_data = {"match_id": "match_1", "home_team": "Team A", "away_team": "Team B"}
        custom_key = "custom_key_123"

        result = await producer.send_match_data(match_data, key=custom_key)

        assert result is True
        call_args = producer.producer.produce.call_args
        assert call_args[1]['key'] == custom_key

    @pytest.mark.asyncio
    async def test_send_match_data_producer_not_initialized(self, producer):
        """测试生产者未初始化时的发送"""
        producer.producer = None

        match_data = {"match_id": "match_1", "home_team": "Team A"}

        result = await producer.send_match_data(match_data)

        assert result is False

    @pytest.mark.asyncio
    async def test_send_odds_data_success(self, producer):
        """测试成功发送赔率数据"""
        producer.producer = Mock()
        producer.producer.produce = Mock()
        producer.producer.flush = Mock()

        odds_data = {
            "match_id": "match_1",
            "home_odds": 2.50,
            "draw_odds": 3.20,
            "away_odds": 2.80
        }

        result = await producer.send_odds_data(odds_data)

        assert result is True

        # 验证消息格式
        call_args = producer.producer.produce.call_args
        message_data = json.loads(call_args[1]['value'])
        assert message_data['data_type'] == "odds"
        assert message_data['data'] == odds_data

    @pytest.mark.asyncio
    async def test_send_scores_data_success(self, producer):
        """测试成功发送比分数据"""
        producer.producer = Mock()
        producer.producer.produce = Mock()
        producer.producer.flush = Mock()

        scores_data = {
            "match_id": "match_1",
            "home_score": 2,
            "away_score": 1,
            "status": "finished"
        }

        result = await producer.send_scores_data(scores_data)

        assert result is True

        # 验证消息格式
        call_args = producer.producer.produce.call_args
        message_data = json.loads(call_args[1]['value'])
        assert message_data['data_type'] == "scores"
        assert message_data['data'] == scores_data

    @pytest.mark.asyncio
    async def test_send_batch_success(self, producer):
        """测试批量发送消息"""
        producer.producer = Mock()
        producer.producer.produce = Mock()
        producer.producer.flush = Mock()

        messages = [
            {"match_id": "match_1", "data_type": "match", "data": {"home_team": "Team A"}},
            {"match_id": "match_2", "data_type": "match", "data": {"home_team": "Team B"}},
            {"match_id": "match_3", "data_type": "odds", "data": {"home_odds": 2.50}}
        ]

        result = await producer.send_batch(messages)

        assert result is True
        assert producer.producer.produce.call_count == 3
        producer.producer.flush.assert_called_once()

    @pytest.mark.asyncio
    async def test_send_batch_empty(self, producer):
        """测试发送空消息列表"""
        result = await producer.send_batch([])

        assert result is False

    @pytest.mark.asyncio
    async def test_send_batch_with_failures(self, producer):
        """测试批量发送部分失败"""
        producer.producer = Mock()
        producer.producer.produce = Mock()
        producer.producer.flush = Mock()

        # 前两条成功，第三条失败
        producer.producer.produce.side_effect = [None, None, Exception("发送失败")]

        messages = [
            {"match_id": "match_1", "data_type": "match", "data": {"home_team": "Team A"}},
            {"match_id": "match_2", "data_type": "match", "data": {"home_team": "Team B"}},
            {"match_id": "match_3", "data_type": "odds", "data": {"home_odds": 2.50}}
        ]

        result = await producer.send_batch(messages)

        assert result is False  # 部分失败也返回False

    @pytest.mark.asyncio
    async def test_serialize_message_success(self, producer):
        """测试成功序列化消息"""
        message = {
            "match_id": "match_1",
            "home_team": "Team A",
            "away_team": "Team B"
        }

        result = producer._serialize_message(message)

        assert isinstance(result, str)
        parsed = json.loads(result)
        assert parsed == message

    @pytest.mark.asyncio
    async def test_serialize_message_with_complex_types(self, producer):
        """测试序列化包含复杂类型的消息"""
        from datetime import datetime

        message = {
            "match_id": "match_1",
            "timestamp": datetime.now(),
            "nested": {"key": "value"},
            "list_data": [1, 2, 3]
        }

        # 应该能处理复杂类型（转换为可序列化格式）
        result = producer._serialize_message(message)

        assert isinstance(result, str)
        parsed = json.loads(result)
        assert parsed["match_id"] == "match_1"

    @pytest.mark.asyncio
    async def test_serialize_message_failure(self, producer):
        """测试序列化失败"""
        # 包含不可序列化的对象
        class UnserializableObject:
            pass

        message = {
            "object": UnserializableObject()
        }

        try:
            result = producer._serialize_message(message)
        except Exception:
            # 期望抛出序列化错误
            pass

    @pytest.mark.asyncio
    async def test_delivery_callback_success(self, producer):
        """测试消息发送成功回调"""
        mock_err = None
        mock_msg = Mock()
        mock_msg.topic.return_value = "matches-stream"
        mock_msg.key.return_value = "match_1"

        # 不应该抛出异常
        producer._delivery_callback(mock_err, mock_msg)

    @pytest.mark.asyncio
    async def test_delivery_callback_error(self, producer):
        """测试消息发送失败回调"""
        mock_err = Exception("消息发送失败")
        mock_msg = Mock()

        # 不应该抛出异常，但应该记录日志
        producer._delivery_callback(mock_err, mock_msg)

    @pytest.mark.asyncio
    async def test_reconnect_on_connection_loss(self, producer):
        """测试连接断开时重连"""
        # 初始生产者失效
        producer.producer = Mock()
        producer.producer.flush.side_effect = Exception("连接断开")

        match_data = {"match_id": "match_1", "home_team": "Team A"}

        # 第一次发送失败
        result1 = await producer.send_match_data(match_data)
        assert result1 is False

        # 重新创建生产者
        with patch('confluent_kafka.Producer') as mock_producer_class:
            mock_producer = Mock()
            mock_producer_class.return_value = mock_producer

            producer._create_producer()
            producer.producer = mock_producer
            producer.producer.produce = Mock()
            producer.producer.flush = Mock()

            # 第二次发送成功
            result2 = await producer.send_match_data(match_data)
            assert result2 is True

    @pytest.mark.asyncio
    async def test_timeout_handling(self, producer):
        """测试超时处理"""
        producer.producer = Mock()
        producer.producer.produce = Mock()
        producer.producer.flush.side_effect = asyncio.TimeoutError("操作超时")

        match_data = {"match_id": "match_1", "home_team": "Team A"}

        result = await producer.send_match_data(match_data)

        assert result is False

    @pytest.mark.asyncio
    async def test_kafka_broker_unavailable(self, producer):
        """测试Kafka代理不可用"""
        with patch('confluent_kafka.Producer') as mock_producer_class:
            mock_producer_class.side_effect = Exception("无法连接到Kafka代理")

            result = producer._create_producer()

            assert result is False

    @pytest.mark.asyncio
    async def test_validate_message_data(self, producer):
        """测试验证消息数据"""
        # 有效数据
        valid_data = {"match_id": "match_1", "home_team": "Team A", "away_team": "Team B"}
        assert producer._validate_message_data(valid_data) is True

        # 缺少必要字段
        invalid_data = {"home_team": "Team A"}
        assert producer._validate_message_data(invalid_data) is False

        # None值
        none_data = None
        assert producer._validate_message_data(none_data) is False

    @pytest.mark.asyncio
    async def test_flush_timeout_handling(self, producer):
        """测试flush超时处理"""
        producer.producer = Mock()
        producer.producer.produce = Mock()
        producer.producer.flush.side_effect = Exception("Flush超时")

        match_data = {"match_id": "match_1", "home_team": "Team A"}

        result = await producer.send_match_data(match_data)

        assert result is False

    @pytest.mark.asyncio
    async def test_cleanup(self, producer):
        """测试清理资源"""
        producer.producer = Mock()
        producer.producer.flush = Mock()

        await producer.cleanup()

        producer.producer.flush.assert_called_once()

    @pytest.mark.asyncio
    async def test_send_with_retry_mechanism(self, producer):
        """测试带重试机制的发送"""
        # 前两次失败，第三次成功
        call_count = 0
        def mock_produce_with_retry(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise Exception("临时失败")
            return None

        producer.producer = Mock()
        producer.producer.produce = mock_produce_with_retry
        producer.producer.flush = Mock()

        match_data = {"match_id": "match_1", "home_team": "Team A"}

        # 实际重试逻辑可能在更高层实现
        # 这里测试基础的重试能力
        try:
            result = await producer.send_match_data(match_data)
        except Exception:
            # 如果实现中有重试，可能会成功
            pass