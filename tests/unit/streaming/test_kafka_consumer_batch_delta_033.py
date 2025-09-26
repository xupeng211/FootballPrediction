"""
Kafka消费者测试 - Batch-Δ-033 Phase 5.3.2.1

修复现有测试文件中的mocking问题，提升kafka_consumer.py覆盖率从30%到≥50%
覆盖所有核心功能：初始化、消息处理、订阅管理、错误处理
"""

import asyncio
import json
import pytest
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, Mock, patch, call
from typing import Dict, Any, List, Optional

from src.streaming.kafka_consumer import FootballKafkaConsumer
from src.database.models.raw_data import RawMatchData, RawOddsData, RawScoresData


class TestFootballKafkaConsumerBatchDelta033:
    """FootballKafkaConsumer 批量测试 - Phase 5.3.2.1"""

    @pytest.fixture
    def mock_stream_config(self):
        """创建模拟流配置"""
        config = Mock()
        config.get_consumer_config.return_value = {
            "bootstrap.servers": "localhost:9092",
            "group.id": "test-group",
            "auto.offset.reset": "earliest",
            "enable.auto.commit": True
        }
        config.kafka_config = Mock()
        config.kafka_config.topics = Mock()
        config.kafka_config.topics.matches = "matches-topic"
        config.kafka_config.topics.odds = "odds-topic"
        config.kafka_config.topics.scores = "scores-topic"
        config.is_valid_topic = Mock(return_value=True)
        return config

    @pytest.fixture
    def mock_consumer(self):
        """创建模拟Kafka消费者"""
        consumer = Mock()
        consumer.subscribe = Mock()
        consumer.poll = Mock(return_value=None)
        consumer.commit = Mock()
        consumer.close = Mock()
        return consumer

    @pytest.fixture
    def consumer_instance(self, mock_stream_config, mock_consumer):
        """创建FootballKafkaConsumer实例"""
        with patch("src.streaming.kafka_consumer.DatabaseManager") as mock_db_manager, \
             patch("confluent_kafka.Consumer") as mock_consumer_class:

            mock_consumer_class.return_value = mock_consumer
            mock_db_manager.return_value = Mock()

            return FootballKafkaConsumer(config=mock_stream_config)

    @pytest.fixture
    def sample_kafka_message(self):
        """创建示例Kafka消息"""
        mock_msg = Mock()
        mock_msg.topic.return_value = "matches-topic"
        mock_msg.partition.return_value = 0
        mock_msg.offset.return_value = 123
        mock_msg.value.return_value = json.dumps({
            "data_type": "match",
            "source": "test_source",
            "data": {
                "match_id": "match_123",
                "league_id": "league_1",
                "home_team": "Team A",
                "away_team": "Team B",
                "home_score": 2,
                "away_score": 1,
                "match_time": "2023-01-01T15:00:00Z"
            }
        }).encode('utf-8')
        mock_msg.error.return_value = None
        return mock_msg

    @pytest.fixture
    def mock_db_session(self):
        """创建模拟数据库会话"""
        session = AsyncMock()
        session.add = Mock()
        session.commit = AsyncMock()
        return session

    # === 初始化测试 ===

    def test_initialization_success(self, consumer_instance, mock_stream_config, mock_consumer):
        """测试成功初始化"""
    assert consumer_instance.config == mock_stream_config
    assert consumer_instance.consumer == mock_consumer
    assert consumer_instance.running is False
    assert consumer_instance.db_manager is not None

    def test_initialization_with_custom_group_id(self, mock_stream_config, mock_consumer):
        """测试使用自定义消费者组ID初始化"""
        with patch("src.streaming.kafka_consumer.DatabaseManager") as mock_db_manager, \
             patch("confluent_kafka.Consumer") as mock_consumer_class:

            mock_consumer_class.return_value = mock_consumer
            mock_db_manager.return_value = Mock()

            consumer = FootballKafkaConsumer(
                config=mock_stream_config,
                consumer_group_id="custom_group"
            )

            # 验证使用了自定义组ID
    assert consumer.consumer_group_id == "custom_group"

    def test_initialization_failure(self, mock_stream_config):
        """测试初始化失败"""
        with patch("src.streaming.kafka_consumer.DatabaseManager") as mock_db_manager, \
             patch("confluent_kafka.Consumer") as mock_consumer_class:

            mock_consumer_class.side_effect = Exception("Kafka连接失败")
            mock_db_manager.return_value = Mock()

            with pytest.raises(Exception, match="Kafka连接失败"):
                FootballKafkaConsumer(config=mock_stream_config)

    # === 消费者创建测试 ===

    def test_create_consumer_when_none(self, consumer_instance, mock_consumer):
        """测试当consumer为None时创建"""
        consumer_instance.consumer = None

        with patch("confluent_kafka.Consumer") as mock_consumer_class:
            mock_consumer_class.return_value = mock_consumer

            consumer_instance._create_consumer()

    assert consumer_instance.consumer == mock_consumer

    def test_create_consumer_when_exists(self, consumer_instance, mock_consumer):
        """测试当consumer已存在时不重新创建"""
        original_consumer = consumer_instance.consumer

        with patch("confluent_kafka.Consumer") as mock_consumer_class:
            mock_consumer_class.return_value = Mock()

            consumer_instance._create_consumer()

            # 应该保持原有的consumer
    assert consumer_instance.consumer == original_consumer
            mock_consumer_class.assert_not_called()

    def test_initialize_consumer_success(self, mock_stream_config, mock_consumer):
        """测试_initialize_consumer方法成功"""
        with patch("src.streaming.kafka_consumer.DatabaseManager") as mock_db_manager, \
             patch("confluent_kafka.Consumer") as mock_consumer_class:

            mock_consumer_class.return_value = mock_consumer
            mock_db_manager.return_value = Mock()

            consumer = FootballKafkaConsumer(config=mock_stream_config)
            consumer.consumer = None

            consumer._initialize_consumer("test_group")

            mock_consumer_class.assert_called_once_with({
                "bootstrap.servers": "localhost:9092",
                "group.id": "test_group",
                "auto.offset.reset": "earliest",
                "enable.auto.commit": True
            })

    # === 消息反序列化测试 ===

    def test_deserialize_message_success(self, consumer_instance):
        """测试成功反序列化消息"""
        original_data = {"key": "value", "number": 123}
        message_bytes = json.dumps(original_data).encode('utf-8')

        result = consumer_instance._deserialize_message(message_bytes)

    assert result == original_data

    def test_deserialize_message_invalid_json(self, consumer_instance):
        """测试反序列化无效JSON消息"""
        invalid_bytes = b'{"invalid": json}'

        with pytest.raises(json.JSONDecodeError):
            consumer_instance._deserialize_message(invalid_bytes)

    def test_deserialize_message_unicode_error(self, consumer_instance):
        """测试反序列化Unicode错误"""
        unicode_bytes = "测试中文".encode('gbk')  # 非UTF-8编码

        with pytest.raises(UnicodeDecodeError):
            consumer_instance._deserialize_message(unicode_bytes)

    # === 消息处理测试 ===

    @pytest.mark.asyncio
    async def test_process_match_message_success(self, consumer_instance, mock_db_session):
        """测试成功处理比赛消息"""
        message_data = {
            "data_type": "match",
            "source": "test_source",
            "data": {
                "match_id": "match_123",
                "league_id": "league_1",
                "home_team": "Team A",
                "away_team": "Team B",
                "home_score": 2,
                "away_score": 1,
                "match_time": "2023-01-01T15:00:00Z"
            }
        }

        # Mock数据库管理器
        consumer_instance.db_manager = Mock()
        consumer_instance.db_manager.get_async_session.return_value.__aenter__.return_value = mock_db_session
        consumer_instance.db_manager.get_async_session.return_value.__aexit__ = AsyncMock()

        result = await consumer_instance._process_match_message(message_data)

    assert result is True
        mock_db_session.add.assert_called_once()
        mock_db_session.commit.assert_called_once()

        # 验证创建的RawMatchData对象
        call_args = mock_db_session.add.call_args[0][0]
    assert isinstance(call_args, RawMatchData)
    assert call_args.data_source == "test_source"
    assert call_args.external_match_id == "match_123"

    @pytest.mark.asyncio
    async def test_process_odds_message_success(self, consumer_instance, mock_db_session):
        """测试成功处理赔率消息"""
        message_data = {
            "data_type": "odds",
            "source": "test_source",
            "data": {
                "match_id": "match_123",
                "bookmaker": "BookmakerA",
                "market_type": "1X2",
                "home_odds": 2.50,
                "draw_odds": 3.20,
                "away_odds": 2.80
            }
        }

        consumer_instance.db_manager = Mock()
        consumer_instance.db_manager.get_async_session.return_value.__aenter__.return_value = mock_db_session
        consumer_instance.db_manager.get_async_session.return_value.__aexit__ = AsyncMock()

        result = await consumer_instance._process_odds_message(message_data)

    assert result is True
        mock_db_session.add.assert_called_once()

        call_args = mock_db_session.add.call_args[0][0]
    assert isinstance(call_args, RawOddsData)
    assert call_args.bookmaker == "BookmakerA"

    @pytest.mark.asyncio
    async def test_process_scores_message_success(self, consumer_instance, mock_db_session):
        """测试成功处理比分消息"""
        message_data = {
            "data_type": "scores",
            "source": "test_source",
            "data": {
                "match_id": "match_123",
                "match_status": "in_progress",
                "home_score": 2,
                "away_score": 1,
                "match_minute": 75
            }
        }

        consumer_instance.db_manager = Mock()
        consumer_instance.db_manager.get_async_session.return_value.__aenter__.return_value = mock_db_session
        consumer_instance.db_manager.get_async_session.return_value.__aexit__ = AsyncMock()

        result = await consumer_instance._process_scores_message(message_data)

    assert result is True
        mock_db_session.add.assert_called_once()

        call_args = mock_db_session.add.call_args[0][0]
    assert isinstance(call_args, RawScoresData)
    assert call_args.match_status == "in_progress"

    @pytest.mark.asyncio
    async def test_process_message_database_error(self, consumer_instance):
        """测试处理消息时数据库错误"""
        message_data = {
            "data_type": "match",
            "source": "test_source",
            "data": {"match_id": "match_123"}
        }

        consumer_instance.db_manager = Mock()
        consumer_instance.db_manager.get_async_session.side_effect = Exception("数据库连接失败")

        result = await consumer_instance._process_match_message(message_data)

    assert result is False

    @pytest.mark.asyncio
    async def test_process_main_message_routing(self, consumer_instance):
        """测试主消息处理路由"""
        with patch.object(consumer_instance, '_process_match_message') as mock_match, \
             patch.object(consumer_instance, '_process_odds_message') as mock_odds, \
             patch.object(consumer_instance, '_process_scores_message') as mock_scores:

            mock_match.return_value = True
            mock_odds.return_value = True
            mock_scores.return_value = True

            # 测试比赛消息路由
            match_msg = Mock()
            match_msg.value.return_value = json.dumps({"data_type": "match"}).encode('utf-8')
            await consumer_instance._process_message(match_msg)
            mock_match.assert_called_once()

            # 测试赔率消息路由
            odds_msg = Mock()
            odds_msg.value.return_value = json.dumps({"data_type": "odds"}).encode('utf-8')
            await consumer_instance._process_message(odds_msg)
            mock_odds.assert_called_once()

            # 测试比分消息路由
            scores_msg = Mock()
            scores_msg.value.return_value = json.dumps({"data_type": "scores"}).encode('utf-8')
            await consumer_instance._process_message(scores_msg)
            mock_scores.assert_called_once()

    # === 订阅管理测试 ===

    def test_subscribe_topics_success(self, consumer_instance, mock_consumer):
        """测试成功订阅主题"""
        topics = ["matches-topic", "odds-topic", "scores-topic"]

        consumer_instance.subscribe_topics(topics)

        mock_consumer.subscribe.assert_called_once_with(topics)

    def test_subscribe_topics_consumer_not_initialized(self, consumer_instance):
        """测试消费者未初始化时订阅主题"""
        consumer_instance.consumer = None

        topics = ["matches-topic"]

        # 应该不抛出异常
        consumer_instance.subscribe_topics(topics)

    def test_subscribe_topics_with_validation(self, consumer_instance, mock_consumer):
        """测试订阅主题时的验证"""
        # 模拟一些主题无效
        consumer_instance.config.is_valid_topic.side_effect = lambda topic: topic != "invalid-topic"

        topics = ["valid-topic", "invalid-topic", "another-valid-topic"]

        consumer_instance.subscribe_topics(topics)

        # 应该只订阅有效主题
        mock_consumer.subscribe.assert_called_once_with(["valid-topic", "another-valid-topic"])

    def test_subscribe_topics_all_invalid(self, consumer_instance, mock_consumer):
        """测试所有主题都无效的情况"""
        consumer_instance.config.is_valid_topic.return_value = False

        topics = ["invalid-topic1", "invalid-topic2"]

        consumer_instance.subscribe_topics(topics)

        # 不应该调用订阅
        mock_consumer.subscribe.assert_not_called()

    def test_subscribe_all_topics(self, consumer_instance, mock_consumer):
        """测试订阅所有配置的主题"""
        consumer_instance.subscribe_all_topics()

        expected_topics = [
            "matches-topic",
            "odds-topic",
            "scores-topic"
        ]
        mock_consumer.subscribe.assert_called_once_with(expected_topics)

    # === 消费测试 ===

    @pytest.mark.asyncio
    async def test_start_consuming_basic(self, consumer_instance, mock_consumer):
        """测试基础消息消费"""
        mock_consumer.poll.return_value = None

        # 短时间运行然后停止
        task = asyncio.create_task(consumer_instance.start_consuming(timeout=0.1))
        await asyncio.sleep(0.05)
        consumer_instance.stop_consuming()

        try:
            await task
        except asyncio.CancelledError:
            pass

        mock_consumer.poll.assert_called()

    @pytest.mark.asyncio
    async def test_start_consuming_with_message(self, consumer_instance, sample_kafka_message):
        """测试消费消息"""
        consumer_instance.consumer.poll.return_value = sample_kafka_message

        with patch.object(consumer_instance, '_process_message') as mock_process:
            mock_process.return_value = True

            task = asyncio.create_task(consumer_instance.start_consuming(timeout=0.1))
            await asyncio.sleep(0.05)
            consumer_instance.stop_consuming()

            try:
                await task
            except asyncio.CancelledError:
                pass

            mock_process.assert_called_once()

    @pytest.mark.asyncio
    async def test_start_consuming_with_partition_eof(self, consumer_instance, mock_consumer):
        """测试处理分区结束情况"""
        from confluent_kafka import KafkaError

        eof_message = Mock()
        eof_error = Mock()
        eof_error.code.return_value = KafkaError._PARTITION_EOF
        eof_message.error.return_value = eof_error

        mock_consumer.poll.return_value = eof_message

        # 应该继续运行而不崩溃
        task = asyncio.create_task(consumer_instance.start_consuming(timeout=0.1))
        await asyncio.sleep(0.05)
        consumer_instance.stop_consuming()

        try:
            await task
        except asyncio.CancelledError:
            pass

    @pytest.mark.asyncio
    async def test_start_consuming_with_kafka_error(self, consumer_instance, mock_consumer):
        """测试处理Kafka错误"""
        from confluent_kafka import KafkaException, KafkaError

        error_message = Mock()
        error_error = Mock()
        error_error.code.return_value = KafkaError._MSG_SIZE_TOO_LARGE
        error_message.error.return_value = error_error

        mock_consumer.poll.return_value = error_message

        with pytest.raises(KafkaException):
            await consumer_instance.start_consuming(timeout=0.1)

    @pytest.mark.asyncio
    async def test_consume_batch_success(self, consumer_instance, sample_kafka_message):
        """测试批量消费成功"""
        stats = {"processed": 0, "failed": 0}
        start_time = datetime.now()

        # 模拟消息处理
        with patch.object(consumer_instance, '_process_message') as mock_process:
            mock_process.return_value = True

            # 简化测试：直接测试方法逻辑
            result = await consumer_instance.consume_batch(batch_size=1, timeout=0.1)

    assert isinstance(result, dict)
    assert "processed" in result
    assert "failed" in result

    @pytest.mark.asyncio
    async def test_consume_messages_return_type(self, consumer_instance, sample_kafka_message):
        """测试consume_messages返回类型"""
        consumer_instance.consumer.poll.return_value = sample_kafka_message

        with patch.object(consumer_instance, '_process_message') as mock_process:
            mock_process.return_value = True

            result = await consumer_instance.consume_messages(batch_size=1, timeout=0.1)

            # 应该返回列表而不是布尔值
    assert isinstance(result, list)

    # === 停止和关闭测试 ===

    def test_stop_consuming(self, consumer_instance, mock_consumer):
        """测试停止消费"""
        consumer_instance.running = True

        consumer_instance.stop_consuming()

    assert consumer_instance.running is False
        mock_consumer.close.assert_called_once()

    def test_stop_consuming_consumer_none(self, consumer_instance):
        """测试停止消费时consumer为None"""
        consumer_instance.consumer = None
        consumer_instance.running = True

        # 应该不抛出异常
        consumer_instance.stop_consuming()
    assert consumer_instance.running is False

    def test_close(self, consumer_instance, mock_consumer):
        """测试关闭消费者"""
        consumer_instance.close()

        mock_consumer.close.assert_called_once()

    # === 上下文管理器测试 ===

    @pytest.mark.asyncio
    async def test_async_context_manager(self, consumer_instance, mock_consumer):
        """测试异步上下文管理器"""
        async with consumer_instance:
            pass

        mock_consumer.close.assert_called_once()

    # === 工具函数测试 ===

    def test_get_session_function(self):
        """测试get_session工具函数"""
        from src.streaming.kafka_consumer import get_session

        with patch("src.streaming.kafka_consumer.DatabaseManager") as mock_db_manager:
            mock_db_manager.return_value = Mock()
            mock_session = AsyncMock()
            mock_db_manager.return_value.get_async_session.return_value = mock_session

            session = get_session()

    assert session is not None

    # === 错误处理测试 ===

    @pytest.mark.asyncio
    async def test_message_processing_exception_handling(self, consumer_instance):
        """测试消息处理异常处理"""
        mock_message = Mock()
        mock_message.value.return_value = json.dumps({"data_type": "match"}).encode('utf-8')

        with patch.object(consumer_instance, '_process_match_message') as mock_process:
            mock_process.side_effect = Exception("处理失败")

            result = await consumer_instance._process_message(mock_message)

    assert result is False

    def test_subscribe_topics_exception(self, consumer_instance, mock_consumer):
        """测试订阅主题异常处理"""
        mock_consumer.subscribe.side_effect = Exception("订阅失败")

        topics = ["test-topic"]

        with pytest.raises(Exception, match="订阅失败"):
            consumer_instance.subscribe_topics(topics)

    @pytest.mark.asyncio
    async def test_consume_batch_timeout(self, consumer_instance, mock_consumer):
        """测试批量消费超时"""
        mock_consumer.poll.return_value = None

        result = await consumer_instance.consume_batch(batch_size=10, timeout=0.01)

    assert isinstance(result, dict)
    assert result["processed"] == 0

    # === 边界条件测试 ===

    def test_deserialize_empty_message(self, consumer_instance):
        """测试反序列化空消息"""
        result = consumer_instance._deserialize_message(b"")
    assert result == {}

    def test_deserialize_none_message(self, consumer_instance):
        """测试反序列化None消息"""
        result = consumer_instance._deserialize_message(None)
    assert result == {}

    @pytest.mark.asyncio
    async def test_process_message_none_value(self, consumer_instance):
        """测试处理空值消息"""
        mock_message = Mock()
        mock_message.value.return_value = None
        mock_message.error.return_value = None

        result = await consumer_instance._process_message(mock_message)

    assert result is False

    # === 偏移量提交测试 ===

    @pytest.mark.asyncio
    async def test_offset_commit_success(self, consumer_instance, sample_kafka_message):
        """测试偏移量提交成功"""
        consumer_instance.consumer.poll.return_value = sample_kafka_message

        with patch.object(consumer_instance, '_process_message') as mock_process:
            mock_process.return_value = True

            task = asyncio.create_task(consumer_instance.start_consuming(timeout=0.1))
            await asyncio.sleep(0.05)
            consumer_instance.stop_consuming()

            try:
                await task
            except asyncio.CancelledError:
                pass

            # 应该尝试提交偏移量
            consumer_instance.consumer.commit.assert_called()

    @pytest.mark.asyncio
    async def test_offset_commit_failure(self, consumer_instance, sample_kafka_message):
        """测试偏移量提交失败"""
        consumer_instance.consumer.poll.return_value = sample_kafka_message
        consumer_instance.consumer.commit.side_effect = Exception("提交失败")

        with patch.object(consumer_instance, '_process_message') as mock_process:
            mock_process.return_value = True

            # 即使提交失败也应该继续运行
            task = asyncio.create_task(consumer_instance.start_consuming(timeout=0.1))
            await asyncio.sleep(0.05)
            consumer_instance.stop_consuming()

            try:
                await task
            except asyncio.CancelledError:
                pass

    # === 兼容性方法测试 ===

    @pytest.mark.asyncio
    async def test_process_message_compatibility(self, consumer_instance):
        """测试process_message兼容性方法"""
        message_data = {
            "topic": "matches-topic",
            "data": {
                "match_id": "match_123",
                "home_team": "Team A",
                "away_team": "Team B"
            }
        }

        with patch.object(consumer_instance, '_process_match_message') as mock_process:
            mock_process.return_value = True

            result = await consumer_instance.process_message(message_data)

    assert result is True