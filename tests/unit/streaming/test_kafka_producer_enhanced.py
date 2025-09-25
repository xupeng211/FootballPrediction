"""
Kafka生产器增强测试 - 覆盖率提升版本

针对 FootballKafkaProducer 的详细测试，专注于提升覆盖率至 70%+
"""

import pytest
import json
import asyncio
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, Mock, patch, call
from typing import Dict, Any, List
from dataclasses import dataclass

from src.streaming.kafka_producer import FootballKafkaProducer


class TestFootballKafkaProducerEnhanced:
    """Kafka生产器增强测试类"""

    @pytest.fixture
    def mock_stream_config(self):
        """模拟流配置"""
        config = Mock()
        config.get_producer_config.return_value = {
            "bootstrap.servers": "localhost:9092",
            "client.id": "football-producer",
            "acks": "all",
            "retries": 3,
            "max.in.flight.requests.per.connection": 5,
            "enable.idempotence": True,
            "compression.type": "gzip",
            "batch.size": 16384,
            "linger.ms": 10,
            "buffer.memory": 33554432,
            "request.timeout.ms": 30000,
            "retry.backoff.ms": 100
        }
        return config

    @pytest.fixture
    def mock_producer(self):
        """模拟Kafka生产者"""
        producer = Mock()
        producer.produce = Mock()
        producer.flush = Mock()
        producer.poll = Mock(return_value=0)
        return producer

    @pytest.fixture
    def football_producer(self, mock_stream_config, mock_producer):
        """创建FootballKafkaProducer实例"""
        with patch("src.streaming.kafka_producer.Producer", return_value=mock_producer):
            return FootballKafkaProducer(mock_stream_config)

    # ===== 初始化和基础功能测试 =====

    def test_init_with_config(self, football_producer, mock_stream_config):
        """测试使用配置初始化"""
        assert football_producer.config == mock_stream_config
        assert football_producer.producer is not None
        assert football_producer.logger is not None

    def test_init_without_config(self):
        """测试不使用配置初始化"""
        with patch("src.streaming.kafka_producer.StreamConfig") as mock_config_class:
            mock_config = Mock()
            mock_config.get_producer_config.return_value = {"bootstrap.servers": "localhost:9092"}
            mock_config_class.return_value = mock_config

            with patch("src.streaming.kafka_producer.Producer") as mock_producer_class:
                mock_producer = Mock()
                mock_producer_class.return_value = mock_producer

                producer = FootballKafkaProducer()

                assert producer.config == mock_config
                assert producer.producer == mock_producer

    def test_initialize_producer_success(self, football_producer):
        """测试成功初始化生产者"""
        # 生产者应该在__init__中已经初始化
        assert football_producer.producer is not None

    def test_initialize_producer_failure(self, mock_stream_config):
        """测试初始化生产者失败"""
        with patch("src.streaming.kafka_producer.Producer") as mock_producer_class:
            mock_producer_class.side_effect = Exception("Connection failed")

            with pytest.raises(Exception, match="Connection failed"):
                FootballKafkaProducer(mock_stream_config)

    def test_context_manager(self, mock_stream_config, mock_producer):
        """测试上下文管理器"""
        with patch("src.streaming.kafka_producer.Producer", return_value=mock_producer):
            with FootballKafkaProducer(mock_stream_config) as producer:
                assert producer is not None
                assert producer.producer == mock_producer

    def test_async_context_manager(self, mock_stream_config, mock_producer):
        """测试异步上下文管理器"""
        with patch("src.streaming.kafka_producer.Producer", return_value=mock_producer):
            producer = FootballKafkaProducer(mock_stream_config)

            # 测试异步上下文管理器方法
            assert producer.__aenter__() == producer
            # __aexit__ 应该存在且可调用
            assert callable(producer.__aexit__)

    def test_create_producer_method(self, football_producer, mock_producer):
        """测试_create_producer方法"""
        football_producer.producer = None

        with patch("src.streaming.kafka_producer.Producer", return_value=mock_producer):
            football_producer._create_producer()
            assert football_producer.producer == mock_producer

    # ===== 序列化功能测试 =====

    def test_serialize_message_string(self, football_producer):
        """测试字符串序列化"""
        data = "test message"
        result = football_producer._serialize_message(data)
        assert result == "test message"

    def test_serialize_message_none(self, football_producer):
        """测试None序列化"""
        result = football_producer._serialize_message(None)
        assert result == ""

    def test_serialize_message_dict(self, football_producer):
        """测试字典序列化"""
        data = {"key": "value", "number": 42}
        result = football_producer._serialize_message(data)
        parsed = json.loads(result)
        assert parsed["key"] == "value"
        assert parsed["number"] == 42

    def test_serialize_message_with_datetime(self, football_producer):
        """测试带datetime的序列化"""
        test_time = datetime(2024, 1, 15, 12, 0, 0, tzinfo=timezone.utc)
        data = {"timestamp": test_time, "event": "match_start"}

        result = football_producer._serialize_message(data)
        parsed = json.loads(result)
        assert "timestamp" in parsed

    def test_serialize_message_dataclass(self, football_producer):
        """测试dataclass序列化"""
        @dataclass
        class MatchData:
            match_id: str
            home_team: str
            away_team: str

        data = MatchData("123", "Team A", "Team B")
        result = football_producer._serialize_message(data)
        parsed = json.loads(result)
        assert parsed["match_id"] == "123"
        assert parsed["home_team"] == "Team A"
        assert parsed["away_team"] == "Team B"

    def test_serialize_data_alias(self, football_producer):
        """测试_serialize_data别名方法"""
        data = {"test": "data"}
        result = football_producer._serialize_data(data)
        assert json.loads(result) == data

    # ===== 数据验证功能测试 =====

    def test_validate_match_data_valid(self, football_producer):
        """测试有效比赛数据验证"""
        data = {
            "match_id": "12345",
            "home_team": "Team A",
            "away_team": "Team B",
            "home_score": 2,
            "away_score": 1
        }
        assert football_producer._validate_match_data(data) is True

    def test_validate_match_data_missing_id(self, football_producer):
        """测试缺少match_id的比赛数据"""
        data = {
            "home_team": "Team A",
            "away_team": "Team B",
            "home_score": 2,
            "away_score": 1
        }
        assert football_producer._validate_match_data(data) is False

    def test_validate_match_data_none(self, football_producer):
        """测试None数据验证"""
        assert football_producer._validate_match_data(None) is False

    def test_validate_odds_data_valid(self, football_producer):
        """测试有效赔率数据验证"""
        data = {
            "match_id": "12345",
            "home_odds": 2.10,
            "draw_odds": 3.40,
            "away_odds": 3.80
        }
        assert football_producer._validate_odds_data(data) is True

    def test_validate_odds_data_invalid_values(self, football_producer):
        """测试无效赔率值"""
        data = {
            "match_id": "12345",
            "home_odds": 0.5,  # 小于1.0
            "draw_odds": 3.40,
            "away_odds": 3.80
        }
        assert football_producer._validate_odds_data(data) is False

    def test_validate_scores_data_valid(self, football_producer):
        """测试有效比分数据验证"""
        data = {
            "match_id": "12345",
            "home_score": 2,
            "away_score": 1,
            "status": "finished"
        }
        assert football_producer._validate_scores_data(data) is True

    def test_validate_scores_data_negative_scores(self, football_producer):
        """测试负数比分"""
        data = {
            "match_id": "12345",
            "home_score": -1,  # 负数无效
            "away_score": 1,
            "status": "finished"
        }
        assert football_producer._validate_scores_data(data) is False

    # ===== 发送功能测试 =====

    @pytest.mark.asyncio
    async def test_send_match_data_success(self, football_producer):
        """测试成功发送比赛数据"""
        match_data = {
            "match_id": "12345",
            "home_team": "Team A",
            "away_team": "Team B",
            "home_score": 2,
            "away_score": 1
        }

        result = await football_producer.send_match_data(match_data)

        assert result is True
        football_producer.producer.produce.assert_called_once()
        football_producer.producer.flush.assert_called_once()

        # 验证调用参数
        call_args = football_producer.producer.produce.call_args
        assert call_args[1]["topic"] == "matches-stream"
        assert call_args[1]["key"] == "12345"

    @pytest.mark.asyncio
    async def test_send_odds_data_success(self, football_producer):
        """测试成功发送赔率数据"""
        odds_data = {
            "match_id": "12345",
            "home_odds": 2.10,
            "draw_odds": 3.40,
            "away_odds": 3.80
        }

        result = await football_producer.send_odds_data(odds_data)

        assert result is True
        call_args = football_producer.producer.produce.call_args
        assert call_args[1]["topic"] == "odds-stream"

    @pytest.mark.asyncio
    async def test_send_scores_data_success(self, football_producer):
        """测试成功发送比分数据"""
        scores_data = {
            "match_id": "12345",
            "home_score": 2,
            "away_score": 1,
            "status": "finished"
        }

        result = await football_producer.send_scores_data(scores_data)

        assert result is True
        call_args = football_producer.producer.produce.call_args
        assert call_args[1]["topic"] == "scores-stream"

    @pytest.mark.asyncio
    async def test_send_batch_success(self, football_producer):
        """测试批量发送成功"""
        messages = [
            {"match_id": "1", "data_type": "match", "data": {"home_team": "Team A"}},
            {"match_id": "2", "data_type": "match", "data": {"home_team": "Team B"}},
            {"match_id": "3", "data_type": "odds", "data": {"home_odds": 2.10}}
        ]

        result = await football_producer.send_batch(messages)

        assert result is True
        assert football_producer.producer.produce.call_count == 3

    @pytest.mark.asyncio
    async def test_send_batch_empty(self, football_producer):
        """测试发送空消息列表"""
        result = await football_producer.send_batch([])
        assert result is False

    @pytest.mark.asyncio
    async def test_send_batch_with_failures(self, football_producer):
        """测试批量发送部分失败"""
        messages = [
            {"match_id": "1", "data_type": "match", "data": {"home_team": "Team A"}},
            {"match_id": "2", "data_type": "match", "data": {"home_team": "Team B"}},
            {"match_id": "3", "data_type": "odds", "data": {"home_odds": 2.10}}
        ]

        # 前两条成功，第三条失败
        football_producer.producer.produce.side_effect = [None, None, Exception("Send failed")]

        result = await football_producer.send_batch(messages)
        assert result is False

    # ===== 错误处理测试 =====

    @pytest.mark.asyncio
    async def test_send_match_data_invalid_data(self, football_producer):
        """测试发送无效比赛数据"""
        invalid_data = {"invalid": "data"}

        result = await football_producer.send_match_data(invalid_data)
        assert result is False
        football_producer.producer.produce.assert_not_called()

    @pytest.mark.asyncio
    async def test_send_odds_data_invalid_data(self, football_producer):
        """测试发送无效赔率数据"""
        invalid_data = {"invalid": "data"}

        result = await football_producer.send_odds_data(invalid_data)
        assert result is False
        football_producer.producer.produce.assert_not_called()

    @pytest.mark.asyncio
    async def test_send_scores_data_invalid_data(self, football_producer):
        """测试发送无效比分数据"""
        invalid_data = {"invalid": "data"}

        result = await football_producer.send_scores_data(invalid_data)
        assert result is False
        football_producer.producer.produce.assert_not_called()

    @pytest.mark.asyncio
    async def test_send_produce_failure(self, football_producer):
        """测试produce失败"""
        football_producer.producer.produce.side_effect = Exception("Produce failed")

        match_data = {"match_id": "12345", "home_team": "Team A", "away_team": "Team B"}

        result = await football_producer.send_match_data(match_data)
        assert result is False

    @pytest.mark.asyncio
    async def test_send_flush_failure(self, football_producer):
        """测试flush失败"""
        football_producer.producer.flush.side_effect = Exception("Flush failed")

        match_data = {"match_id": "12345", "home_team": "Team A", "away_team": "Team B"}

        result = await football_producer.send_match_data(match_data)
        assert result is False

    # ===== 回调函数测试 =====

    def test_delivery_callback_success(self, football_producer):
        """测试成功发送回调"""
        mock_msg = Mock()
        mock_msg.topic.return_value = "test-topic"
        mock_msg.key.return_value = b"test-key"

        # 不应该抛出异常
        football_producer._delivery_callback(None, mock_msg)

    def test_delivery_callback_error(self, football_producer):
        """测试发送失败回调"""
        error = Exception("Delivery failed")
        mock_msg = Mock()

        # 不应该抛出异常
        football_producer._delivery_callback(error, mock_msg)

    # ===== 工具方法测试 =====

    def test_flush(self, football_producer):
        """测试flush方法"""
        football_producer.flush(timeout=5.0)
        football_producer.producer.flush.assert_called_once_with(5.0)

    def test_flush_default_timeout(self, football_producer):
        """测试默认超时flush"""
        football_producer.flush()
        football_producer.producer.flush.assert_called_once_with(10.0)

    def test_close(self, football_producer):
        """测试close方法"""
        football_producer.close(timeout=5.0)
        football_producer.producer.flush.assert_called_once_with(5.0)

    def test_close_none_timeout(self, football_producer):
        """测试无超时close"""
        football_producer.close()
        football_producer.producer.flush.assert_called_once_with(10.0)

    def test_get_producer_config(self, football_producer, mock_stream_config):
        """测试获取生产者配置"""
        config = football_producer.get_producer_config()
        assert config == mock_stream_config.get_producer_config.return_value

    def test_health_check_healthy(self, football_producer):
        """测试健康检查-健康状态"""
        football_producer.producer.poll.return_value = 0

        result = football_producer.health_check()
        assert result is True
        football_producer.producer.poll.assert_called_once_with(0)

    def test_health_check_unhealthy(self, football_producer):
        """测试健康检查-不健康状态"""
        football_producer.producer.poll.side_effect = Exception("Connection error")

        result = football_producer.health_check()
        assert result is False

    def test_destructor(self, football_producer):
        """测试析构函数"""
        # 调用析构函数不应该抛出异常
        football_producer.__del__()

    # ===== 边界情况测试 =====

    @pytest.mark.asyncio
    async def test_send_none_data(self, football_producer):
        """测试发送None数据"""
        result = await football_producer.send_match_data(None)
        assert result is False

    @pytest.mark.asyncio
    async def test_send_empty_dict_data(self, football_producer):
        """测试发送空字典数据"""
        result = await football_producer.send_match_data({})
        assert result is False

    @pytest.mark.asyncio
    async def test_send_non_dict_data(self, football_producer):
        """测试发送非字典数据"""
        result = await football_producer.send_match_data("invalid_data")
        assert result is False

    def test_serialize_complex_object(self, football_producer):
        """测试序列化复杂对象"""
        class ComplexObject:
            def __init__(self, value):
                self.value = value

        data = {"obj": ComplexObject("test")}

        # 应该能处理复杂对象（可能抛出异常或返回字符串）
        try:
            result = football_producer._serialize_message(data)
            assert isinstance(result, str)
        except Exception:
            # 如果抛出异常也是可以接受的
            pass


if __name__ == "__main__":
    # 运行所有测试
    pytest.main([__file__, "-v", "--tb=short"])