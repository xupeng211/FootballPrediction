"""
Phase 6: kafka_consumer.py 补测用例
目标：提升覆盖率从 43% 到 70%+
重点：异常处理、重试逻辑、空消息、连接失败等未覆盖分支
"""

import json
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, Mock, patch

import pytest
from confluent_kafka import Consumer, KafkaError, KafkaException

from src.streaming.kafka_consumer import FootballKafkaConsumer
from src.streaming.stream_config import StreamConfig


class TestKafkaConsumerInitialization:
    """测试 Kafka 消费者初始化"""

    def test_initialization_with_default_config(self):
        """测试使用默认配置初始化"""
        with patch("src.streaming.kafka_consumer.Consumer") as mock_consumer_class:
            mock_consumer = Mock()
            mock_consumer_class.return_value = mock_consumer

            consumer = FootballKafkaConsumer()

            assert consumer.config is not None
            assert consumer.db_manager is not None
            assert consumer.logger is not None
            assert not consumer.running
            assert consumer.consumer is not None

    def test_initialization_with_custom_config(self):
        """测试使用自定义配置初始化"""
        custom_config = StreamConfig()
        custom_config.bootstrap_servers = "custom-server:9092"

        with patch("src.streaming.kafka_consumer.Consumer") as mock_consumer_class:
            mock_consumer = Mock()
            mock_consumer_class.return_value = mock_consumer

            consumer = FootballKafkaConsumer(config=custom_config)

            assert consumer.config == custom_config

    def test_initialization_with_consumer_group_id(self):
        """测试使用自定义消费者组ID"""
        with patch("src.streaming.kafka_consumer.Consumer") as mock_consumer_class:
            mock_consumer = Mock()
            mock_consumer_class.return_value = mock_consumer

            consumer = FootballKafkaConsumer(consumer_group_id="test-group")

            assert consumer.consumer_group_id == "test-group"

    def test_initialization_consumer_creation_failure(self):
        """测试消费者创建失败"""
        with patch("src.streaming.kafka_consumer.Consumer") as mock_consumer_class:
            mock_consumer_class.side_effect = Exception("Kafka connection failed")

            with pytest.raises(Exception, match="Kafka connection failed"):
                FootballKafkaConsumer()


class TestKafkaConsumerSubscription:
    """测试订阅相关功能"""

    def setup_method(self):
        with patch("src.streaming.kafka_consumer.Consumer") as mock_consumer_class:
            self.mock_consumer = Mock()
            mock_consumer_class.return_value = self.mock_consumer
            self.consumer = FootballKafkaConsumer()

    def test_subscribe_to_topics_success(self):
        """测试成功订阅主题"""
        topics = ["football-matches", "football-odds"]

        self.consumer.subscribe_to_topics(topics)

        self.mock_consumer.subscribe.assert_called_once_with(topics)

    def test_subscribe_to_topics_failure(self):
        """测试订阅主题失败"""
        self.mock_consumer.subscribe.side_effect = KafkaException("Subscription failed")

        with pytest.raises(KafkaException):
            self.consumer.subscribe_to_topics(["invalid-topic"])

    def test_subscribe_with_empty_topics(self):
        """测试订阅空主题列表"""
        self.consumer.subscribe_to_topics([])

        self.mock_consumer.subscribe.assert_called_once_with([])

    def test_subscribe_with_none_topics(self):
        """测试订阅 None 主题"""
        with pytest.raises(TypeError):
            self.consumer.subscribe_to_topics(None)


class TestKafkaConsumerPolling:
    """测试消息轮询功能"""

    def setup_method(self):
        with patch("src.streaming.kafka_consumer.Consumer") as mock_consumer_class:
            self.mock_consumer = Mock()
            mock_consumer_class.return_value = self.mock_consumer
            self.consumer = FootballKafkaConsumer()

    def test_poll_message_success(self):
        """测试成功轮询消息"""
        mock_message = Mock()
        mock_message.error.return_value = None
        mock_message.value.return_value = b'{"match_id": 123}'
        mock_message.topic.return_value = "football-matches"

        self.mock_consumer.poll.return_value = mock_message

        message = self.consumer.poll_message(timeout=1.0)

        assert message == mock_message
        self.mock_consumer.poll.assert_called_once_with(timeout=1.0)

    def test_poll_message_timeout(self):
        """测试轮询超时"""
        self.mock_consumer.poll.return_value = None

        message = self.consumer.poll_message(timeout=1.0)

        assert message is None

    def test_poll_message_with_error(self):
        """测试轮询消息时的错误"""
        mock_message = Mock()
        mock_error = Mock()
        mock_error.code.return_value = KafkaError._PARTITION_EOF
        mock_message.error.return_value = mock_error

        self.mock_consumer.poll.return_value = mock_message

        message = self.consumer.poll_message(timeout=1.0)

        assert message == mock_message  # 应该返回带错误的消息

    def test_poll_message_kafka_exception(self):
        """测试轮询时 Kafka 异常"""
        self.mock_consumer.poll.side_effect = KafkaException("Poll failed")

        with pytest.raises(KafkaException):
            self.consumer.poll_message(timeout=1.0)


class TestKafkaConsumerMessageProcessing:
    """测试消息处理功能"""

    def setup_method(self):
        with patch("src.streaming.kafka_consumer.Consumer") as mock_consumer_class:
            self.mock_consumer = Mock()
            mock_consumer_class.return_value = self.mock_consumer
            self.consumer = FootballKafkaConsumer()

    def test_deserialize_message_success(self):
        """测试成功反序列化消息"""
        mock_message = Mock()
        mock_message.value.return_value = b'{"match_id": 123, "home_team": "Arsenal"}'

        result = self.consumer.deserialize_message(mock_message)

        expected = {"match_id": 123, "home_team": "Arsenal"}
        assert result == expected

    def test_deserialize_message_invalid_json(self):
        """测试反序列化无效 JSON"""
        mock_message = Mock()
        mock_message.value.return_value = b"invalid json"

        result = self.consumer.deserialize_message(mock_message)

        assert result is None

    def test_deserialize_message_empty_value(self):
        """测试反序列化空消息"""
        mock_message = Mock()
        mock_message.value.return_value = b""

        result = self.consumer.deserialize_message(mock_message)

        assert result is None

    def test_deserialize_message_none_value(self):
        """测试反序列化 None 值"""
        mock_message = Mock()
        mock_message.value.return_value = None

        result = self.consumer.deserialize_message(mock_message)

        assert result is None

    def test_deserialize_message_unicode_error(self):
        """测试 Unicode 解码错误"""
        mock_message = Mock()
        mock_message.value.return_value = b"\xff\xfe"  # 无效UTF-8字节

        result = self.consumer.deserialize_message(mock_message)

        assert result is None


class TestKafkaConsumerDataProcessing:
    """测试数据处理功能"""

    def setup_method(self):
        with patch("src.streaming.kafka_consumer.Consumer") as mock_consumer_class:
            self.mock_consumer = Mock()
            mock_consumer_class.return_value = self.mock_consumer
            self.consumer = FootballKafkaConsumer()

    @pytest.mark.asyncio
    async def test_process_match_message_success(self):
        """测试成功处理比赛消息"""
        mock_message = Mock()
        mock_message.topic.return_value = "football-matches"

        data = {
            "match_id": 123,
            "home_team": "Arsenal",
            "away_team": "Chelsea",
            "match_date": "2023-01-01T15:00:00",
        }

        with patch.object(self.consumer.db_manager, "execute_insert") as mock_insert:
            mock_insert.return_value = True

            result = await self.consumer.process_match_message(mock_message, data)

            assert result is True

    @pytest.mark.asyncio
    async def test_process_match_message_database_error(self):
        """测试处理比赛消息时数据库错误"""
        mock_message = Mock()
        mock_message.topic.return_value = "football-matches"

        data = {"match_id": 123}

        with patch.object(self.consumer.db_manager, "execute_insert") as mock_insert:
            mock_insert.side_effect = Exception("Database connection failed")

            result = await self.consumer.process_match_message(mock_message, data)

            assert result is False

    @pytest.mark.asyncio
    async def test_process_odds_message_success(self):
        """测试成功处理赔率消息"""
        mock_message = Mock()
        mock_message.topic.return_value = "football-odds"

        data = {"match_id": 123, "home_win": 2.5, "draw": 3.2, "away_win": 2.8}

        with patch.object(self.consumer.db_manager, "execute_insert") as mock_insert:
            mock_insert.return_value = True

            result = await self.consumer.process_odds_message(mock_message, data)

            assert result is True

    @pytest.mark.asyncio
    async def test_process_scores_message_success(self):
        """测试成功处理比分消息"""
        mock_message = Mock()
        mock_message.topic.return_value = "football-scores"

        data = {"match_id": 123, "home_score": 2, "away_score": 1, "status": "FT"}

        with patch.object(self.consumer.db_manager, "execute_insert") as mock_insert:
            mock_insert.return_value = True

            result = await self.consumer.process_scores_message(mock_message, data)

            assert result is True

    @pytest.mark.asyncio
    async def test_process_unknown_topic_message(self):
        """测试处理未知主题消息"""
        mock_message = Mock()
        mock_message.topic.return_value = "unknown-topic"

        data = {"some": "data"}

        result = await self.consumer.process_message(mock_message, data)

        assert result is False


class TestKafkaConsumerLifecycle:
    """测试消费者生命周期管理"""

    def setup_method(self):
        with patch("src.streaming.kafka_consumer.Consumer") as mock_consumer_class:
            self.mock_consumer = Mock()
            mock_consumer_class.return_value = self.mock_consumer
            self.consumer = FootballKafkaConsumer()

    @pytest.mark.asyncio
    async def test_start_consuming_normal_flow(self):
        """测试正常消费流程"""
        # Mock 消息
        mock_message = Mock()
        mock_message.error.return_value = None
        mock_message.value.return_value = b'{"match_id": 123}'
        mock_message.topic.return_value = "football-matches"

        # Mock poll 返回一条消息后停止
        self.mock_consumer.poll.side_effect = [mock_message, None]

        with patch.object(self.consumer, "process_message") as mock_process:
            mock_process.return_value = True

            # 设置停止条件
            original_running = self.consumer.running
            self.consumer.running = True

            async def stop_after_one():
                await asyncio.sleep(0.1)
                self.consumer.running = False

            # 启动停止任务
            stop_task = asyncio.create_task(stop_after_one())

            await self.consumer.start_consuming(
                topics=["football-matches"], poll_timeout=0.1
            )

            await stop_task

    @pytest.mark.asyncio
    async def test_start_consuming_message_error(self):
        """测试消费过程中消息错误"""
        mock_message = Mock()
        mock_error = Mock()
        mock_error.code.return_value = KafkaError._PARTITION_EOF
        mock_message.error.return_value = mock_error

        self.mock_consumer.poll.side_effect = [mock_message, None]

        self.consumer.running = True

        async def stop_after_one():
            await asyncio.sleep(0.1)
            self.consumer.running = False

        stop_task = asyncio.create_task(stop_after_one())

        await self.consumer.start_consuming(
            topics=["football-matches"], poll_timeout=0.1
        )

        await stop_task

    @pytest.mark.asyncio
    async def test_start_consuming_processing_failure(self):
        """测试消息处理失败"""
        mock_message = Mock()
        mock_message.error.return_value = None
        mock_message.value.return_value = b'{"match_id": 123}'

        self.mock_consumer.poll.side_effect = [mock_message, None]

        with patch.object(self.consumer, "deserialize_message") as mock_deserialize:
            mock_deserialize.return_value = {"match_id": 123}

        with patch.object(self.consumer, "process_message") as mock_process:
            mock_process.return_value = False  # 处理失败

        self.consumer.running = True

        async def stop_after_one():
            await asyncio.sleep(0.1)
            self.consumer.running = False

        stop_task = asyncio.create_task(stop_after_one())

        await self.consumer.start_consuming(
            topics=["football-matches"], poll_timeout=0.1
        )

        await stop_task

    def test_stop_consuming(self):
        """测试停止消费"""
        self.consumer.running = True

        self.consumer.stop_consuming()

        assert not self.consumer.running

    def test_close_consumer(self):
        """测试关闭消费者"""
        self.consumer.close()

        self.mock_consumer.close.assert_called_once()

    def test_close_consumer_when_none(self):
        """测试关闭空消费者"""
        self.consumer.consumer = None

        # 应该不抛出异常
        self.consumer.close()


class TestKafkaConsumerErrorHandling:
    """测试错误处理"""

    def setup_method(self):
        with patch("src.streaming.kafka_consumer.Consumer") as mock_consumer_class:
            self.mock_consumer = Mock()
            mock_consumer_class.return_value = self.mock_consumer
            self.consumer = FootballKafkaConsumer()

    @pytest.mark.asyncio
    async def test_commit_message_success(self):
        """测试成功提交消息"""
        mock_message = Mock()

        self.consumer.commit_message(mock_message)

        self.mock_consumer.commit.assert_called_once_with(message=mock_message)

    @pytest.mark.asyncio
    async def test_commit_message_failure(self):
        """测试提交消息失败"""
        mock_message = Mock()
        self.mock_consumer.commit.side_effect = KafkaException("Commit failed")

        # 应该不抛出异常，只记录日志
        self.consumer.commit_message(mock_message)

    @pytest.mark.asyncio
    async def test_handle_message_error_partition_eof(self):
        """测试处理分区结束错误"""
        mock_message = Mock()
        mock_error = Mock()
        mock_error.code.return_value = KafkaError._PARTITION_EOF
        mock_message.error.return_value = mock_error
        mock_message.topic.return_value = "test-topic"
        mock_message.partition.return_value = 0

        # 应该不抛出异常
        self.consumer.handle_message_error(mock_message)

    @pytest.mark.asyncio
    async def test_handle_message_error_other_errors(self):
        """测试处理其他类型错误"""
        mock_message = Mock()
        mock_error = Mock()
        mock_error.code.return_value = KafkaError.UNKNOWN
        mock_message.error.return_value = mock_error

        # 应该记录错误但不抛出异常
        self.consumer.handle_message_error(mock_message)


class TestKafkaConsumerEdgeCases:
    """测试边界情况"""

    def setup_method(self):
        with patch("src.streaming.kafka_consumer.Consumer") as mock_consumer_class:
            self.mock_consumer = Mock()
            mock_consumer_class.return_value = self.mock_consumer
            self.consumer = FootballKafkaConsumer()

    def test_process_large_json_message(self):
        """测试处理大型 JSON 消息"""
        large_data = {"data": "x" * 10000}  # 大型数据
        mock_message = Mock()
        mock_message.value.return_value = json.dumps(large_data).encode()

        result = self.consumer.deserialize_message(mock_message)

        assert result == large_data

    def test_process_nested_json_message(self):
        """测试处理嵌套 JSON 消息"""
        nested_data = {
            "match": {
                "teams": {
                    "home": {"name": "Arsenal", "id": 1},
                    "away": {"name": "Chelsea", "id": 2},
                }
            }
        }
        mock_message = Mock()
        mock_message.value.return_value = json.dumps(nested_data).encode()

        result = self.consumer.deserialize_message(mock_message)

        assert result == nested_data

    @pytest.mark.asyncio
    async def test_concurrent_message_processing(self):
        """测试并发消息处理"""
        mock_messages = []
        for i in range(5):
            mock_message = Mock()
            mock_message.error.return_value = None
            mock_message.value.return_value = f'{{"match_id": {i}}}'.encode()
            mock_message.topic.return_value = "football-matches"
            mock_messages.append(mock_message)

        # 模拟并发处理
        tasks = []
        for message in mock_messages:
            data = self.consumer.deserialize_message(message)
            if data:
                task = self.consumer.process_message(message, data)
                tasks.append(task)

        results = await asyncio.gather(*tasks, return_exceptions=True)

        # 所有任务应该完成
        assert len(results) == len(mock_messages)

    def test_invalid_configuration_handling(self):
        """测试无效配置处理"""
        invalid_config = StreamConfig()
        invalid_config.bootstrap_servers = ""  # 空服务器

        with patch("src.streaming.kafka_consumer.Consumer") as mock_consumer_class:
            mock_consumer_class.side_effect = Exception("Invalid bootstrap servers")

            with pytest.raises(Exception):
                FootballKafkaConsumer(config=invalid_config)
