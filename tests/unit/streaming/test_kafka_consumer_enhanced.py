"""
Kafka消费者增强测试 - 覆盖率提升版本

针对 FootballKafkaConsumer 的详细测试，专注于提升覆盖率至 70%+
"""

import pytest
import json
import asyncio
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, Mock, patch, call
from typing import Dict, Any, List

from src.streaming.kafka_consumer import FootballKafkaConsumer


class TestFootballKafkaConsumerEnhanced:
    """Kafka消费者增强测试类"""

    @pytest.fixture
    def mock_stream_config(self):
        """模拟流配置"""
        config = Mock()
        config.get_consumer_config.return_value = {
            "bootstrap.servers": "localhost:9092",
            "group.id": "football-consumers",
            "auto.offset.reset": "earliest",
            "enable.auto.commit": False,
            "max.poll.records": 500,
            "session.timeout.ms": 10000,
            "heartbeat.interval.ms": 3000
        }
        return config

    @pytest.fixture
    def mock_database_manager(self):
        """模拟数据库管理器"""
        db_manager = Mock()
        db_manager.get_async_session.return_value.__aenter__.return_value = Mock()
        return db_manager

    @pytest.fixture
    def mock_consumer(self):
        """模拟Kafka消费者"""
        consumer = Mock()
        consumer.subscribe = Mock()
        consumer.unsubscribe = Mock()
        consumer.poll = Mock()
        consumer.commit = Mock()
        consumer.assignment = Mock(return_value=[])
        consumer.committed = Mock(return_value=None)
        consumer.position = Mock(return_value=None)
        consumer.seek = Mock()
        consumer.get_watermark_offsets = Mock(return_value=(0, 100))
        return consumer

    @pytest.fixture
    def football_consumer(self, mock_stream_config, mock_database_manager, mock_consumer):
        """创建FootballKafkaConsumer实例"""
        with patch("src.streaming.kafka_consumer.Consumer", return_value=mock_consumer):
            return FootballKafkaConsumer(mock_stream_config, mock_database_manager)

    # ===== 初始化和基础功能测试 =====

    def test_init_with_configs(self, football_consumer, mock_stream_config, mock_database_manager):
        """测试使用配置初始化"""
        assert football_consumer.config == mock_stream_config
        assert football_consumer.db_manager == mock_database_manager
        assert football_consumer.consumer is not None
        assert football_consumer.running is False
        assert football_consumer.logger is not None

    def test_init_without_configs(self):
        """测试不使用配置初始化"""
        with patch("src.streaming.kafka_consumer.StreamConfig") as mock_config_class, \
             patch("src.streaming.kafka_consumer.DatabaseManager") as mock_db_manager_class, \
             patch("src.streaming.kafka_consumer.Consumer") as mock_consumer_class:

            mock_config = Mock()
            mock_config.get_consumer_config.return_value = {"bootstrap.servers": "localhost:9092"}
            mock_config_class.return_value = mock_config

            mock_db_manager = Mock()
            mock_db_manager_class.return_value = mock_db_manager

            mock_consumer = Mock()
            mock_consumer_class.return_value = mock_consumer

            consumer = FootballKafkaConsumer()

            assert consumer.config == mock_config
            assert consumer.db_manager == mock_db_manager
            assert consumer.consumer == mock_consumer

    def test_create_consumer_success(self, football_consumer, mock_consumer):
        """测试成功创建消费者"""
        football_consumer.consumer = None

        with patch("src.streaming.kafka_consumer.Consumer", return_value=mock_consumer):
            football_consumer._create_consumer()
            assert football_consumer.consumer == mock_consumer

    def test_create_consumer_failure(self, football_consumer):
        """测试创建消费者失败"""
        football_consumer.consumer = None

        with patch("src.streaming.kafka_consumer.Consumer") as mock_consumer_class:
            mock_consumer_class.side_effect = Exception("Connection failed")

            football_consumer._create_consumer()
            assert football_consumer.consumer is None

    # ===== 订阅功能测试 =====

    def test_subscribe_topics_success(self, football_consumer):
        """测试成功订阅主题"""
        topics = ["matches-stream", "odds-stream", "scores-stream"]

        football_consumer.subscribe_topics(topics)

        football_consumer.consumer.subscribe.assert_called_once_with(topics)

    def test_subscribe_topics_empty_list(self, football_consumer):
        """测试订阅空主题列表"""
        football_consumer.subscribe_topics([])
        football_consumer.consumer.subscribe.assert_not_called()

    def test_subscribe_topics_consumer_not_initialized(self, football_consumer):
        """测试消费者未初始化时订阅主题"""
        football_consumer.consumer = None

        topics = ["matches-stream"]
        # 不应该抛出异常
        football_consumer.subscribe_topics(topics)

    def test_unsubscribe_topics(self, football_consumer):
        """测试取消订阅主题"""
        football_consumer.unsubscribe_topics()
        football_consumer.consumer.unsubscribe.assert_called_once()

    def test_unsubscribe_topics_consumer_not_initialized(self, football_consumer):
        """测试消费者未初始化时取消订阅"""
        football_consumer.consumer = None
        # 不应该抛出异常
        football_consumer.unsubscribe_topics()

    # ===== 消费功能测试 =====

    @pytest.mark.asyncio
    async def test_consume_messages_success(self, football_consumer):
        """测试成功消费消息"""
        # 模拟消息
        mock_message = Mock()
        mock_message.value.return_value = json.dumps({
            "data_type": "match",
            "match_id": "12345",
            "data": {
                "home_team": "Team A",
                "away_team": "Team B",
                "home_score": 2,
                "away_score": 1
            }
        }).encode('utf-8')
        mock_message.error.return_value = None
        mock_message.topic.return_value = "matches-stream"
        mock_message.key.return_value = b"12345"
        mock_message.offset.return_value = 123
        mock_message.partition.return_value = 0
        mock_message.timestamp.return_value = (1234567890, 1234567890000)

        # 设置poll返回
        football_consumer.consumer.poll.side_effect = [mock_message, None]

        with patch.object(football_consumer, '_process_message') as mock_process:
            mock_process.return_value = True

            result = await football_consumer.consume_messages(timeout=1.0)

            assert result is True
            assert football_consumer.consumer.poll.call_count == 2
            mock_process.assert_called_once()

    @pytest.mark.asyncio
    async def test_consume_messages_no_messages(self, football_consumer):
        """测试无消息可消费"""
        football_consumer.consumer.poll.return_value = None

        result = await football_consumer.consume_messages(timeout=1.0)

        assert result is True

    @pytest.mark.asyncio
    async def test_consume_messages_error_message(self, football_consumer):
        """测试消费错误消息"""
        mock_message = Mock()
        mock_message.error.return_value = Exception("Message error")
        mock_message.value.return_value = b'{"data": "test"}'

        football_consumer.consumer.poll.return_value = mock_message

        result = await football_consumer.consume_messages(timeout=1.0)

        assert result is True  # 错误消息也被认为是成功消费

    @pytest.mark.asyncio
    async def test_consume_messages_consumer_not_initialized(self, football_consumer):
        """测试消费者未初始化时消费消息"""
        football_consumer.consumer = None

        result = await football_consumer.consume_messages()
        assert result is False

    # ===== 消息处理测试 =====

    @pytest.mark.asyncio
    async def test_process_match_message_success(self, football_consumer):
        """测试成功处理比赛消息"""
        message_data = {
            "data_type": "match",
            "match_id": "12345",
            "data": {
                "home_team": "Team A",
                "away_team": "Team B",
                "home_score": 2,
                "away_score": 1,
                "match_date": "2024-01-15T15:00:00Z",
                "competition": "Premier League",
                "status": "FINISHED"
            }
        }

        result = await football_consumer._process_message(message_data)

        assert result is True

    @pytest.mark.asyncio
    async def test_process_odds_message_success(self, football_consumer):
        """测试成功处理赔率消息"""
        message_data = {
            "data_type": "odds",
            "match_id": "12345",
            "data": {
                "home_odds": 2.10,
                "draw_odds": 3.40,
                "away_odds": 3.80,
                "bookmaker": "Bet365",
                "timestamp": "2024-01-15T14:55:00Z"
            }
        }

        result = await football_consumer._process_message(message_data)

        assert result is True

    @pytest.mark.asyncio
    async def test_process_scores_message_success(self, football_consumer):
        """测试成功处理比分消息"""
        message_data = {
            "data_type": "scores",
            "match_id": "12345",
            "data": {
                "home_score": 2,
                "away_score": 1,
                "minute": 90,
                "status": "FINISHED",
                "timestamp": "2024-01-15T17:00:00Z"
            }
        }

        result = await football_consumer._process_message(message_data)

        assert result is True

    @pytest.mark.asyncio
    async def test_process_message_unknown_type(self, football_consumer):
        """测试处理未知类型消息"""
        message_data = {
            "data_type": "unknown",
            "match_id": "12345",
            "data": {"some": "data"}
        }

        result = await football_consumer._process_message(message_data)

        assert result is False

    @pytest.mark.asyncio
    async def test_process_message_invalid_data(self, football_consumer):
        """测试处理无效数据"""
        message_data = {"invalid": "data"}

        result = await football_consumer._process_message(message_data)

        assert result is False

    @pytest.mark.asyncio
    async def test_process_message_database_error(self, football_consumer):
        """测试处理消息时数据库错误"""
        message_data = {
            "data_type": "match",
            "match_id": "12345",
            "data": {"home_team": "Team A", "away_team": "Team B"}
        }

        # 模拟数据库错误
        football_consumer.db_manager.get_async_session.side_effect = Exception("DB error")

        result = await football_consumer._process_message(message_data)

        assert result is False

    # ===== 反序列化功能测试 =====

    def test_deserialize_message_success(self, football_consumer):
        """测试成功反序列化消息"""
        message_value = json.dumps({"test": "data"}).encode('utf-8')
        mock_message = Mock()
        mock_message.value.return_value = message_value

        result = football_consumer._deserialize_message(mock_message)

        assert result == {"test": "data"}

    def test_deserialize_message_invalid_json(self, football_consumer):
        """测试反序列化无效JSON"""
        mock_message = Mock()
        mock_message.value.return_value = b'invalid json'

        result = football_consumer._deserialize_message(mock_message)

        assert result is None

    def test_deserialize_message_none_value(self, football_consumer):
        """测试反序列化None值"""
        mock_message = Mock()
        mock_message.value.return_value = None

        result = football_consumer._deserialize_message(mock_message)

        assert result is None

    # ===== 启动和停止测试 =====

    @pytest.mark.asyncio
    async def test_start_consuming_success(self, football_consumer):
        """测试成功启动消费"""
        football_consumer.consumer.poll.return_value = None  # 无消息

        with patch.object(football_consumer, 'consume_messages') as mock_consume:
            mock_consume.return_value = True

            result = await football_consumer.start_consuming()

            assert result is True
            assert football_consumer.running is True
            mock_consume.assert_called_once()

    @pytest.mark.asyncio
    async def test_start_consuming_already_running(self, football_consumer):
        """测试启动已运行的消费者"""
        football_consumer.running = True

        result = await football_consumer.start_consuming()

        assert result is False

    @pytest.mark.asyncio
    async def test_start_consuming_consumer_not_initialized(self, football_consumer):
        """测试启动未初始化的消费者"""
        football_consumer.consumer = None

        result = await football_consumer.start_consuming()

        assert result is False

    @pytest.mark.asyncio
    async def test_stop_consuming(self, football_consumer):
        """测试停止消费"""
        football_consumer.running = True

        await football_consumer.stop_consuming()

        assert football_consumer.running is False

    # ===== 偏移管理测试 =====

    def test_commit_offset_success(self, football_consumer):
        """测试成功提交偏移"""
        football_consumer.consumer.assignment.return_value = [Mock()]

        football_consumer.commit_offset()

        football_consumer.consumer.commit.assert_called_once()

    def test_commit_offset_no_assignment(self, football_consumer):
        """测试提交偏移无分配"""
        football_consumer.consumer.assignment.return_value = []

        football_consumer.commit_offset()
        football_consumer.consumer.commit.assert_not_called()

    def test_commit_offset_consumer_not_initialized(self, football_consumer):
        """测试消费者未初始化时提交偏移"""
        football_consumer.consumer = None

        football_consumer.commit_offset()  # 不应该抛出异常

    def test_seek_to_beginning(self, football_consumer):
        """测试重置到开始位置"""
        mock_partition = Mock()
        football_consumer.consumer.assignment.return_value = [mock_partition]

        football_consumer.seek_to_beginning("test-topic")

        football_consumer.consumer.seek.assert_called_once()

    def test_seek_to_beginning_consumer_not_initialized(self, football_consumer):
        """测试消费者未初始化时重置位置"""
        football_consumer.consumer = None

        football_consumer.seek_to_beginning("test-topic")  # 不应该抛出异常

    # ===== 健康检查和统计测试 =====

    def test_health_check_healthy(self, football_consumer):
        """测试健康检查-健康状态"""
        football_consumer.consumer.poll.return_value = None

        result = football_consumer.health_check()

        assert result is True
        football_consumer.consumer.poll.assert_called_once_with(0)

    def test_health_check_unhealthy(self, football_consumer):
        """测试健康检查-不健康状态"""
        football_consumer.consumer.poll.side_effect = Exception("Connection error")

        result = football_consumer.health_check()

        assert result is False

    def test_health_check_consumer_not_initialized(self, football_consumer):
        """测试消费者未初始化时健康检查"""
        football_consumer.consumer = None

        result = football_consumer.health_check()

        assert result is False

    def test_get_consumer_stats(self, football_consumer):
        """测试获取消费者统计信息"""
        mock_partition = Mock()
        mock_partition.partition = 0
        mock_partition.topic = "test-topic"
        football_consumer.consumer.assignment.return_value = [mock_partition]
        football_consumer.consumer.committed.return_value = 50
        football_consumer.consumer.position.return_value = 60
        football_consumer.consumer.get_watermark_offsets.return_value = (0, 100)

        stats = football_consumer.get_consumer_stats()

        assert isinstance(stats, dict)
        assert "assigned_partitions" in stats
        assert "lag" in stats
        assert "current_offsets" in stats

    def test_get_consumer_stats_consumer_not_initialized(self, football_consumer):
        """测试消费者未初始化时获取统计信息"""
        football_consumer.consumer = None

        stats = football_consumer.get_consumer_stats()

        assert isinstance(stats, dict)
        assert stats["assigned_partitions"] == 0

    # ===== 重平衡处理测试 =====

    def test_on_rebalance_assign(self, football_consumer):
        """测试重平衡分配处理"""
        mock_partitions = [Mock(topic="test-topic", partition=0)]

        football_consumer._on_rebalance_assign(mock_partitions)

        # 应该能处理重平衡分配而不抛出异常

    def test_on_rebalance_revoke(self, football_consumer):
        """测试重平衡撤销处理"""
        mock_partitions = [Mock(topic="test-topic", partition=0)]

        football_consumer._on_rebalance_revoke(mock_partitions)

        # 应该能处理重平衡撤销而不抛出异常

    # ===== 错误处理测试 =====

    @pytest.mark.asyncio
    async def test_consume_with_retry_success(self, football_consumer):
        """测试带重试的消费成功"""
        mock_message = Mock()
        mock_message.value.return_value = b'{"data_type": "match", "data": {"test": "data"}}'
        mock_message.error.return_value = None

        # 前两次poll返回None，第三次返回消息
        football_consumer.consumer.poll.side_effect = [None, None, mock_message]

        with patch.object(football_consumer, '_process_message') as mock_process:
            mock_process.return_value = True

            result = await football_consumer.consume_with_retry(timeout=5.0, max_retries=3)

            assert result is True
            assert football_consumer.consumer.poll.call_count == 3

    @pytest.mark.asyncio
    async def test_consume_with_retry_failure(self, football_consumer):
        """测试带重试的消费失败"""
        football_consumer.consumer.poll.return_value = None  # 始终无消息

        result = await football_consumer.consume_with_retry(timeout=1.0, max_retries=3)

        assert result is False

    @pytest.mark.asyncio
    async def test_consume_with_retry_processing_failure(self, football_consumer):
        """测试处理消息失败的重试"""
        mock_message = Mock()
        mock_message.value.return_value = b'{"data_type": "match", "data": {"test": "data"}}'
        mock_message.error.return_value = None

        football_consumer.consumer.poll.return_value = mock_message

        with patch.object(football_consumer, '_process_message') as mock_process:
            mock_process.return_value = False  # 处理失败

            result = await football_consumer.consume_with_retry(timeout=1.0, max_retries=3)

            assert result is False

    # ===== 清理功能测试 =====

    def test_cleanup(self, football_consumer):
        """测试清理资源"""
        football_consumer.running = True

        football_consumer.cleanup()

        assert football_consumer.running is False

    def test_cleanup_consumer_not_initialized(self, football_consumer):
        """测试消费者未初始化时清理"""
        football_consumer.consumer = None

        football_consumer.cleanup()  # 不应该抛出异常

    # ===== 批量消费测试 =====

    @pytest.mark.asyncio
    async def test_consume_batch_success(self, football_consumer):
        """测试批量消费成功"""
        mock_messages = []
        for i in range(3):
            mock_msg = Mock()
            mock_msg.value.return_value = json.dumps({
                "data_type": "match",
                "match_id": f"123{i}",
                "data": {"home_team": f"Team {i}"}
            }).encode('utf-8')
            mock_msg.error.return_value = None
            mock_messages.append(mock_msg)

        football_consumer.consumer.poll.side_effect = mock_messages + [None]

        results = await football_consumer.consume_batch(batch_size=3, timeout=1.0)

        assert len(results) == 3
        assert all(result is True for result in results)

    @pytest.mark.asyncio
    async def test_consume_batch_partial_failure(self, football_consumer):
        """测试批量消费部分失败"""
        mock_messages = []
        for i in range(3):
            mock_msg = Mock()
            mock_msg.value.return_value = json.dumps({
                "data_type": "match",
                "match_id": f"123{i}",
                "data": {"home_team": f"Team {i}"}
            }).encode('utf-8')
            mock_msg.error.return_value = None
            mock_messages.append(mock_msg)

        football_consumer.consumer.poll.side_effect = mock_messages + [None]

        # 使第二条消息处理失败
        with patch.object(football_consumer, '_process_message') as mock_process:
            mock_process.side_effect = [True, False, True]

            results = await football_consumer.consume_batch(batch_size=3, timeout=1.0)

            assert len(results) == 3
            assert results[0] is True
            assert results[1] is False
            assert results[2] is True

    # ===== 上下文管理器测试 =====

    def test_context_manager(self, mock_stream_config, mock_database_manager, mock_consumer):
        """测试上下文管理器"""
        with patch("src.streaming.kafka_consumer.Consumer", return_value=mock_consumer):
            with FootballKafkaConsumer(mock_stream_config, mock_database_manager) as consumer:
                assert consumer is not None
                assert consumer.running is False  # 初始状态

            # 退出后应该保持停止状态
            assert consumer.running is False

    # ===== 边界情况测试 =====

    @pytest.mark.asyncio
    async def test_process_message_none_data(self, football_consumer):
        """测试处理None数据"""
        result = await football_consumer._process_message(None)
        assert result is False

    @pytest.mark.asyncio
    async def test_process_message_empty_data(self, football_consumer):
        """测试处理空数据"""
        result = await football_consumer._process_message({})
        assert result is False

    def test_deserialize_message_none_message(self, football_consumer):
        """测试反序列化None消息"""
        result = football_consumer._deserialize_message(None)
        assert result is None


if __name__ == "__main__":
    # 运行所有测试
    pytest.main([__file__, "-v", "--tb=short"])