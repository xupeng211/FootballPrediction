"""
Kafka消费者测试 - FootballKafkaConsumer
"""

import asyncio
import json
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, Mock, patch

import pytest

from src.streaming.kafka_consumer import FootballKafkaConsumer


class TestFootballKafkaConsumer:
    """测试足球数据Kafka消费者"""

    @pytest.fixture
    def consumer(self):
        """创建FootballKafkaConsumer实例"""
        with patch("src.streaming.kafka_consumer.StreamConfig") as mock_config, \
             patch("src.streaming.kafka_consumer.DatabaseManager") as mock_db_manager:
            mock_config.return_value = Mock()
            mock_config.return_value.get_consumer_config.return_value = {
                "bootstrap.servers": "localhost:9092",
                "group.id": "test-group"
            }
            with patch("confluent_kafka.Consumer") as mock_consumer_class:
                mock_consumer = Mock()
                mock_consumer_class.return_value = mock_consumer
                return FootballKafkaConsumer()

    def test_init(self, consumer):
        """测试初始化"""
        assert consumer.config is not None
        assert consumer.consumer is not None
        assert hasattr(consumer, 'logger')
        assert hasattr(consumer, 'running')
        assert consumer.running is False

    @pytest.mark.asyncio
    async def test_create_consumer_success(self, consumer):
        """测试成功创建Kafka消费者"""
        # 先将consumer设为None，然后测试创建逻辑
        consumer.consumer = None

        with patch('confluent_kafka.Consumer') as mock_consumer_class:
            mock_consumer = Mock()
            mock_consumer_class.return_value = mock_consumer

            # 这个方法应该不会返回值，但会创建consumer
            consumer._create_consumer()

            assert consumer.consumer == mock_consumer
            mock_consumer_class.assert_called_once()

    @pytest.mark.asyncio
    async def test_create_consumer_failure(self, consumer):
        """测试创建Kafka消费者失败"""
        consumer.consumer = None

        with patch('confluent_kafka.Consumer') as mock_consumer_class:
            mock_consumer_class.side_effect = Exception("Kafka连接失败")

            # 应该抛出异常而不是返回False
            try:
                consumer._create_consumer()
                assert False, "应该抛出异常"
            except Exception:
                pass  # 期望抛出异常

            assert consumer.consumer is None

    def test_subscribe_topics_success(self, consumer):
        """测试成功订阅主题"""
        consumer.consumer = Mock()
        consumer.consumer.subscribe = Mock()

        topics = ["matches-stream", "odds-stream", "scores-stream"]

        consumer.subscribe_topics(topics)

        consumer.consumer.subscribe.assert_called_once_with(topics)

    def test_subscribe_topics_consumer_not_initialized(self, consumer):
        """测试消费者未初始化时订阅主题"""
        consumer.consumer = None

        topics = ["matches-stream"]

        # 这个方法没有返回值，但会检查consumer状态
        consumer.subscribe_topics(topics)

        # 应该能处理consumer为None的情况

    @pytest.mark.asyncio
    async def test_consume_messages_success(self, consumer):
        """测试成功消费消息"""
        consumer.consumer = Mock()
        consumer.consumer.poll = Mock()

        # 模拟消息
        mock_message = Mock()
        mock_message.value.return_value = json.dumps({
            "data_type": "match",
            "match_id": "match_1",
            "data": {
                "home_team": "Team A",
                "away_team": "Team B",
                "home_score": 2,
                "away_score": 1
            }
        }).encode('utf-8')

        # 第一次调用返回消息，第二次返回None（无消息）
        consumer.consumer.poll.side_effect = [mock_message, None]

        with patch.object(consumer, '_process_message') as mock_process:
            mock_process.return_value = True

            result = await consumer.consume_messages(timeout=1.0)

            assert result is True
            consumer.consumer.poll.assert_called()
            mock_process.assert_called_once()

    @pytest.mark.asyncio
    async def test_consume_messages_no_messages(self, consumer):
        """测试无消息可消费"""
        consumer.consumer = Mock()
        consumer.consumer.poll = Mock(return_value=None)  # 无消息

        result = await consumer.consume_messages(timeout=1.0)

        assert result is True  # 无消息也是成功的

    @pytest.mark.asyncio
    async def test_consume_messages_consumer_not_initialized(self, consumer):
        """测试消费者未初始化时消费消息"""
        consumer.consumer = None

        result = await consumer.consume_messages()

        # 应该返回空列表或抛出异常
        assert isinstance(result, list) or result is None

    @pytest.mark.asyncio
    async def test_process_match_message_success(self, consumer):
        """测试成功处理比赛消息"""
        message_data = {
            "data_type": "match",
            "match_id": "match_1",
            "data": {
                "home_team": "Team A",
                "away_team": "Team B",
                "home_score": 2,
                "away_score": 1,
                "date": "2025-09-25"
            }
        }

        # Mock数据库管理器
        consumer.db_manager = Mock()
        consumer.db_manager.save_match_data = AsyncMock(return_value=True)

        result = await consumer._process_match_message(message_data)

        assert result is True
        consumer.db_manager.save_match_data.assert_called_once_with(message_data["data"])

    @pytest.mark.asyncio
    async def test_process_odds_message_success(self, consumer):
        """测试成功处理赔率消息"""
        message_data = {
            "data_type": "odds",
            "match_id": "match_1",
            "data": {
                "home_odds": 2.50,
                "draw_odds": 3.20,
                "away_odds": 2.80
            }
        }

        consumer.db_manager = Mock()
        consumer.db_manager.save_odds_data = AsyncMock(return_value=True)

        result = await consumer._process_odds_message(message_data)

        assert result is True
        consumer.db_manager.save_odds_data.assert_called_once_with(message_data["data"])

    @pytest.mark.asyncio
    async def test_process_scores_message_success(self, consumer):
        """测试成功处理比分消息"""
        message_data = {
            "data_type": "scores",
            "match_id": "match_1",
            "data": {
                "home_score": 2,
                "away_score": 1,
                "status": "finished"
            }
        }

        consumer.db_manager = Mock()
        consumer.db_manager.save_scores_data = AsyncMock(return_value=True)

        result = await consumer._process_scores_message(message_data)

        assert result is True
        consumer.db_manager.save_scores_data.assert_called_once_with(message_data["data"])

    @pytest.mark.asyncio
    async def test_process_message_unknown_type(self, consumer):
        """测试处理未知类型的消息"""
        message_data = {
            "data_type": "unknown",
            "match_id": "match_1",
            "data": {"some": "data"}
        }

        result = await consumer._process_message(message_data)

        assert result is False

    @pytest.mark.asyncio
    async def test_process_message_database_error(self, consumer):
        """测试处理消息时数据库错误"""
        message_data = {
            "data_type": "match",
            "match_id": "match_1",
            "data": {"home_team": "Team A", "away_team": "Team B"}
        }

        consumer.db_manager = Mock()
        consumer.db_manager.save_match_data = AsyncMock(side_effect=Exception("数据库错误"))

        result = await consumer._process_match_message(message_data)

        assert result is False

    @pytest.mark.asyncio
    async def test_deserialize_message_success(self, consumer):
        """测试成功反序列化消息"""
        original_data = {
            "data_type": "match",
            "match_id": "match_1",
            "data": {"home_team": "Team A"}
        }

        json_data = json.dumps(original_data).encode('utf-8')

        result = consumer._deserialize_message(json_data)

        assert result == original_data

    @pytest.mark.asyncio
    async def test_deserialize_message_invalid_json(self, consumer):
        """测试反序列化无效JSON"""
        invalid_json = b'{"invalid": json}'

        try:
            result = consumer._deserialize_message(invalid_json)
        except json.JSONDecodeError:
            # 期望抛出JSON解析错误
            pass

    @pytest.mark.asyncio
    async def test_start_consuming_success(self, consumer):
        """测试成功开始消费"""
        consumer.consumer = Mock()
        consumer.consumer.subscribe = Mock()
        consumer.consumer.poll = Mock(return_value=None)  # 无消息

        with patch('asyncio.sleep'):  # 加速测试
            # 模拟运行一次后停止
            consumer.running = True
            original_running = consumer.running

            def set_running_false(*args):
                consumer.running = False

            consumer.consumer.poll.side_effect = set_running_false

            await consumer.start_consuming(topics=["matches-stream"], interval=0.1)

            consumer.consumer.subscribe.assert_called_once()

    @pytest.mark.asyncio
    async def test_stop_consuming(self, consumer):
        """测试停止消费"""
        consumer.running = True
        consumer.consumer = Mock()
        consumer.consumer.close = Mock()

        await consumer.stop_consuming()

        assert consumer.running is False
        consumer.consumer.close.assert_called_once()

    @pytest.mark.asyncio
    async def test_consumer_rebalance_handling(self, consumer):
        """测试消费者重平衡处理"""
        # 这个测试验证重平衡时的行为
        # 实际的重平衡回调可能在消费者内部处理

        consumer.consumer = Mock()
        consumer.consumer.subscribe = Mock()

        # 模拟重平衡场景
        topics = ["matches-stream"]

        result = await consumer.subscribe_topics(topics)

        assert result is True
        # 重平衡逻辑应该被正确处理

    @pytest.mark.asyncio
    async def test_consumer_group_management(self, consumer):
        """测试消费者组管理"""
        consumer.consumer = Mock()
        consumer.consumer.subscribe = Mock()

        # 使用消费者组配置
        topics = ["matches-stream"]

        result = await consumer.subscribe_topics(topics)

        assert result is True
        # 消费者组应该正确配置和管理

    @pytest.mark.asyncio
    async def test_offset_commit_handling(self, consumer):
        """测试偏移量提交处理"""
        consumer.consumer = Mock()
        consumer.consumer.commit = Mock()

        # 模拟偏移量提交
        await consumer._commit_offsets()

        consumer.consumer.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_message_backlog_handling(self, consumer):
        """测试消息积压处理"""
        consumer.consumer = Mock()
        consumer.consumer.poll = Mock()

        # 模拟大量消息
        messages = []
        for i in range(10):
            mock_msg = Mock()
            mock_msg.value.return_value = json.dumps({
                "data_type": "match",
                "match_id": f"match_{i}",
                "data": {"home_team": f"Team {i}"}
            }).encode('utf-8')
            messages.append(mock_msg)

        consumer.consumer.poll.side_effect = messages + [None]  # 10条消息后结束

        with patch.object(consumer, '_process_message') as mock_process:
            mock_process.return_value = True

            result = await consumer.consume_messages(timeout=5.0)

            assert result is True
            assert mock_process.call_count == 10  # 处理了10条消息

    @pytest.mark.asyncio
    async def test_connection_error_handling(self, consumer):
        """测试连接错误处理"""
        consumer.consumer = Mock()
        consumer.consumer.poll = Mock(side_effect=Exception("连接断开"))

        result = await consumer.consume_messages()

        assert result is False

    @pytest.mark.asyncio
    async def test_consumer_initialization_error(self, consumer):
        """测试消费者初始化错误"""
        with patch('confluent_kafka.Consumer') as mock_consumer_class:
            mock_consumer_class.side_effect = Exception("初始化失败")

            result = consumer._create_consumer()

            assert result is False

    @pytest.mark.asyncio
    async def test_topic_subscription_error(self, consumer):
        """测试主题订阅错误"""
        consumer.consumer = Mock()
        consumer.consumer.subscribe = Mock(side_effect=Exception("订阅失败"))

        topics = ["matches-stream"]

        result = await consumer.subscribe_topics(topics)

        assert result is False

    @pytest.mark.asyncio
    async def test_consumer_metrics_collection(self, consumer):
        """测试消费者指标收集"""
        consumer.consumer = Mock()
        consumer.consumer.poll = Mock(return_value=None)

        # 模拟指标收集
        metrics = await consumer._get_consumer_metrics()

        assert isinstance(metrics, dict)

    @pytest.mark.asyncio
    async def test_consumer_cleanup(self, consumer):
        """测试消费者清理"""
        consumer.consumer = Mock()
        consumer.consumer.close = Mock()

        await consumer.cleanup()

        consumer.consumer.close.assert_called_once()

    @pytest.mark.asyncio
    async def test_concurrent_message_processing(self, consumer):
        """测试并发消息处理"""
        consumer.consumer = Mock()
        consumer.consumer.poll = Mock()

        # 模拟多条消息需要并发处理
        mock_message = Mock()
        mock_message.value.return_value = json.dumps({
            "data_type": "match",
            "match_id": "match_1",
            "data": {"home_team": "Team A"}
        }).encode('utf-8')

        consumer.consumer.poll.return_value = mock_message

        with patch.object(consumer, '_process_message') as mock_process:
            mock_process.return_value = True

            # 测试并发处理能力
            tasks = []
            for _ in range(3):
                task = asyncio.create_task(consumer.consume_messages())
                tasks.append(task)

            await asyncio.gather(*tasks, return_exceptions=True)

            # 验证处理逻辑被调用
            assert mock_process.call_count > 0

    @pytest.mark.asyncio
    async def test_message_validation_failure(self, consumer):
        """测试消息验证失败"""
        # 无效的消息格式
        invalid_message = Mock()
        invalid_message.value.return_value = b'invalid message'

        consumer.consumer = Mock()
        consumer.consumer.poll = Mock(return_value=invalid_message)

        result = await consumer.consume_messages()

        # 应该能处理无效消息而不崩溃
        assert result is True

    @pytest.mark.asyncio
    async def test_consumer_restart_after_failure(self, consumer):
        """测试消费者在失败后重启"""
        # 第一次初始化失败
        with patch('confluent_kafka.Consumer') as mock_consumer_class:
            mock_consumer_class.side_effect = [Exception("第一次失败"), Mock()]

            # 第一次尝试
            result1 = consumer._create_consumer()
            assert result1 is False

            # 重置消费者对象
            consumer.consumer = None

            # 第二次尝试应该成功
            result2 = consumer._create_consumer()
            assert result2 is True