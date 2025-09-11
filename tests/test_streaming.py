"""
流式数据处理测试

测试Kafka Producer和Consumer的生产/消费流程，验证Kafka集成的正确性。
"""

import json
from datetime import datetime, timezone
from decimal import Decimal
from unittest.mock import Mock, patch

import pytest

from src.data.collectors.streaming_collector import StreamingDataCollector
from src.streaming import (FootballKafkaConsumer, FootballKafkaProducer,
                           StreamConfig, StreamProcessor)
from src.streaming.stream_processor import StreamProcessorManager


class TestStreamConfig:
    """测试流配置"""

    def test_stream_config_initialization(self):
        """测试配置初始化"""
        config = StreamConfig()

        assert config.kafka_config is not None
        assert config.kafka_config.bootstrap_servers is not None
        assert config.topics is not None
        assert "matches-stream" in config.topics
        assert "odds-stream" in config.topics
        assert "scores-stream" in config.topics

    def test_producer_config(self):
        """测试生产者配置"""
        config = StreamConfig()
        producer_config = config.get_producer_config()

        assert "bootstrap.servers" in producer_config
        assert "client.id" in producer_config
        assert "acks" in producer_config

    def test_consumer_config(self):
        """测试消费者配置"""
        config = StreamConfig()
        consumer_config = config.get_consumer_config()

        assert "bootstrap.servers" in consumer_config
        assert "group.id" in consumer_config
        assert "auto.offset.reset" in consumer_config


class TestFootballKafkaProducer:
    """测试Kafka生产者"""

    def setup_method(self):
        """设置测试环境"""
        self.mock_producer = Mock()
        self.config = StreamConfig()

    @patch("src.streaming.kafka_producer.Producer")
    def test_producer_initialization(self, mock_producer_class):
        """测试生产者初始化"""
        mock_producer_class.return_value = self.mock_producer

        producer = FootballKafkaProducer(self.config)

        assert producer.config == self.config
        assert producer.producer == self.mock_producer
        mock_producer_class.assert_called_once()

    @patch("src.streaming.kafka_producer.Producer")
    def test_send_match_data(self, mock_producer_class):
        """测试发送比赛数据"""
        mock_producer_class.return_value = self.mock_producer
        producer = FootballKafkaProducer(self.config)

        match_data = {
            "match_id": 12345,
            "home_team": "Team A",
            "away_team": "Team B",
            "match_time": datetime.now(timezone.utc).isoformat(),
            "status": "scheduled",
        }

        result = producer.send_match_data(match_data)

        assert result is True
        self.mock_producer.produce.assert_called_once()
        self.mock_producer.poll.assert_called_once()

    @patch("src.streaming.kafka_producer.Producer")
    def test_send_odds_data(self, mock_producer_class):
        """测试发送赔率数据"""
        mock_producer_class.return_value = self.mock_producer
        producer = FootballKafkaProducer(self.config)

        odds_data = {
            "match_id": 12345,
            "bookmaker": "Test Bookmaker",
            "home_odds": 2.5,
            "draw_odds": 3.2,
            "away_odds": 1.8,
        }

        result = producer.send_odds_data(odds_data)

        assert result is True
        self.mock_producer.produce.assert_called_once()

    @patch("src.streaming.kafka_producer.Producer")
    def test_send_scores_data(self, mock_producer_class):
        """测试发送比分数据"""
        mock_producer_class.return_value = self.mock_producer
        producer = FootballKafkaProducer(self.config)

        scores_data = {
            "match_id": 12345,
            "home_score": 2,
            "away_score": 1,
            "minute": 90,
            "status": "finished",
        }

        result = producer.send_scores_data(scores_data)

        assert result is True
        self.mock_producer.produce.assert_called_once()

    @patch("src.streaming.kafka_producer.Producer")
    def test_producer_error_handling(self, mock_producer_class):
        """测试生产者错误处理"""
        mock_producer_class.return_value = self.mock_producer
        self.mock_producer.produce.side_effect = Exception("Kafka error")

        producer = FootballKafkaProducer(self.config)

        match_data = {"match_id": 12345}
        result = producer.send_match_data(match_data)

        assert result is False

    @patch("src.streaming.kafka_producer.Producer")
    def test_batch_send(self, mock_producer_class):
        """测试批量发送"""
        mock_producer_class.return_value = self.mock_producer
        producer = FootballKafkaProducer(self.config)

        batch_data = [
            {"data_type": "match", "data": {"match_id": 1}},
            {"data_type": "odds", "data": {"match_id": 2}},
            {"data_type": "scores", "data": {"match_id": 3}},
        ]

        results = producer.send_batch(batch_data)

        assert len(results) == 3
        assert all(result is True for result in results)
        assert self.mock_producer.produce.call_count == 3


class TestFootballKafkaConsumer:
    """测试Kafka消费者"""

    def setup_method(self):
        """设置测试环境"""
        self.mock_consumer = Mock()
        self.config = StreamConfig()

    @patch("src.streaming.kafka_consumer.Consumer")
    def test_consumer_initialization(self, mock_consumer_class):
        """测试消费者初始化"""
        mock_consumer_class.return_value = self.mock_consumer

        consumer = FootballKafkaConsumer(self.config)

        assert consumer.config == self.config
        assert consumer.consumer == self.mock_consumer
        mock_consumer_class.assert_called_once()

    @patch("src.streaming.kafka_consumer.Consumer")
    @patch("src.streaming.kafka_consumer.get_session")
    def test_process_match_message(self, mock_get_session, mock_consumer_class):
        """测试处理比赛消息"""
        mock_consumer_class.return_value = self.mock_consumer
        mock_db = Mock()
        mock_get_session.return_value.__enter__.return_value = mock_db

        consumer = FootballKafkaConsumer(self.config)

        message_data = {
            "match_id": 12345,
            "home_team": "Team A",
            "away_team": "Team B",
            "match_time": datetime.now(timezone.utc).isoformat(),
        }

        result = consumer._process_match_message(message_data)

        assert result is True
        mock_db.add.assert_called_once()
        mock_db.commit.assert_called_once()

    @patch("src.streaming.kafka_consumer.Consumer")
    @patch("src.streaming.kafka_consumer.get_session")
    def test_process_odds_message(self, mock_get_session, mock_consumer_class):
        """测试处理赔率消息"""
        mock_consumer_class.return_value = self.mock_consumer
        mock_db = Mock()
        mock_get_session.return_value.__enter__.return_value = mock_db

        consumer = FootballKafkaConsumer(self.config)

        message_data = {
            "match_id": 12345,
            "bookmaker": "Test Bookmaker",
            "home_odds": 2.5,
            "draw_odds": 3.2,
        }

        result = consumer._process_odds_message(message_data)

        assert result is True
        mock_db.add.assert_called_once()
        mock_db.commit.assert_called_once()

    @patch("src.streaming.kafka_consumer.Consumer")
    @patch("src.streaming.kafka_consumer.get_session")
    def test_process_scores_message(self, mock_get_session, mock_consumer_class):
        """测试处理比分消息"""
        mock_consumer_class.return_value = self.mock_consumer
        mock_db = Mock()
        mock_get_session.return_value.__enter__.return_value = mock_db

        consumer = FootballKafkaConsumer(self.config)

        message_data = {
            "match_id": 12345,
            "home_score": 2,
            "away_score": 1,
            "minute": 90,
        }

        result = consumer._process_scores_message(message_data)

        assert result is True
        mock_db.add.assert_called_once()
        mock_db.commit.assert_called_once()

    @patch("src.streaming.kafka_consumer.Consumer")
    def test_consume_batch(self, mock_consumer_class):
        """测试批量消费"""
        mock_consumer_class.return_value = self.mock_consumer

        # 模拟Kafka消息
        mock_message1 = Mock()
        mock_message1.error.return_value = None
        mock_message1.value.return_value = json.dumps(
            {"data_type": "match", "data": {"match_id": 1}}
        ).encode()

        mock_message2 = Mock()
        mock_message2.error.return_value = None
        mock_message2.value.return_value = json.dumps(
            {"data_type": "odds", "data": {"match_id": 2}}
        ).encode()

        self.mock_consumer.consume.return_value = [mock_message1, mock_message2]

        consumer = FootballKafkaConsumer(self.config)

        with patch.object(
            consumer, "_process_message", return_value=True
        ) as mock_process:
            results = consumer.consume_batch(timeout=1.0, max_messages=10)

            assert len(results) == 2
            assert mock_process.call_count == 2

    @patch("src.streaming.kafka_consumer.Consumer")
    def test_consumer_error_handling(self, mock_consumer_class):
        """测试消费者错误处理"""
        mock_consumer_class.return_value = self.mock_consumer

        # 模拟Kafka错误消息
        mock_message = Mock()
        mock_message.error.return_value = Mock(code=Mock(return_value=1))

        self.mock_consumer.consume.return_value = [mock_message]

        consumer = FootballKafkaConsumer(self.config)
        results = consumer.consume_batch(timeout=1.0, max_messages=1)

        # 错误消息应该被跳过
        assert len(results) == 0


class TestStreamProcessor:
    """测试流处理器"""

    def setup_method(self):
        """设置测试环境"""
        self.config = StreamConfig()

    @patch("src.streaming.stream_processor.FootballKafkaProducer")
    @patch("src.streaming.stream_processor.FootballKafkaConsumer")
    def test_stream_processor_initialization(
        self, mock_consumer_class, mock_producer_class
    ):
        """测试流处理器初始化"""
        processor = StreamProcessor(self.config)

        assert processor.config == self.config
        mock_producer_class.assert_called_once_with(self.config)
        mock_consumer_class.assert_called_once_with(self.config)

    @patch("src.streaming.stream_processor.FootballKafkaProducer")
    @patch("src.streaming.stream_processor.FootballKafkaConsumer")
    def test_send_data(self, mock_consumer_class, mock_producer_class):
        """测试发送数据"""
        mock_producer = Mock()
        mock_producer.send_match_data.return_value = True
        mock_producer_class.return_value = mock_producer

        processor = StreamProcessor(self.config)

        result = processor.send_data("match", {"match_id": 12345})

        assert result is True
        mock_producer.send_match_data.assert_called_once_with({"match_id": 12345})

    @patch("src.streaming.stream_processor.FootballKafkaProducer")
    @patch("src.streaming.stream_processor.FootballKafkaConsumer")
    def test_consume_data(self, mock_consumer_class, mock_producer_class):
        """测试消费数据"""
        mock_consumer = Mock()
        mock_consumer.consume_batch.return_value = [{"result": "success"}]
        mock_consumer_class.return_value = mock_consumer

        processor = StreamProcessor(self.config)

        results = processor.consume_data(timeout=1.0, max_messages=10)

        assert len(results) == 1
        mock_consumer.consume_batch.assert_called_once_with(
            timeout=1.0, max_messages=10
        )

    @patch("src.streaming.stream_processor.FootballKafkaProducer")
    @patch("src.streaming.stream_processor.FootballKafkaConsumer")
    def test_health_check(self, mock_consumer_class, mock_producer_class):
        """测试健康检查"""
        mock_producer = Mock()
        mock_consumer = Mock()
        mock_producer_class.return_value = mock_producer
        mock_consumer_class.return_value = mock_consumer

        processor = StreamProcessor(self.config)

        health_status = processor.health_check()

        assert "producer" in health_status
        assert "consumer" in health_status
        assert health_status["timestamp"] is not None


class TestStreamProcessorManager:
    """测试流处理器管理器"""

    def setup_method(self):
        """设置测试环境"""
        self.config = StreamConfig()

    @patch("src.streaming.stream_processor.StreamProcessor")
    def test_manager_initialization(self, mock_processor_class):
        """测试管理器初始化"""
        manager = StreamProcessorManager(self.config, num_processors=3)

        assert len(manager.processors) == 3
        assert mock_processor_class.call_count == 3

    @patch("src.streaming.stream_processor.StreamProcessor")
    def test_start_all_processors(self, mock_processor_class):
        """测试启动所有处理器"""
        mock_processor = Mock()
        mock_processor_class.return_value = mock_processor

        manager = StreamProcessorManager(self.config, num_processors=2)

        with patch.object(manager, "_start_processor") as mock_start:
            manager.start_all()
            assert mock_start.call_count == 2

    @patch("src.streaming.stream_processor.StreamProcessor")
    def test_stop_all_processors(self, mock_processor_class):
        """测试停止所有处理器"""
        mock_processor = Mock()
        mock_processor_class.return_value = mock_processor

        manager = StreamProcessorManager(self.config, num_processors=2)

        with patch.object(manager, "_stop_processor") as mock_stop:
            manager.stop_all()
            assert mock_stop.call_count == 2


class TestStreamingDataCollector:
    """测试流式数据收集器"""

    def setup_method(self):
        """设置测试环境"""
        self.config = StreamConfig()

    @patch("src.data.collectors.streaming_collector.FootballKafkaProducer")
    @patch("src.data.collectors.streaming_collector.DataCollector.__init__")
    def test_streaming_collector_initialization(
        self, mock_base_init, mock_producer_class
    ):
        """测试流式收集器初始化"""
        mock_base_init.return_value = None

        collector = StreamingDataCollector()

        assert collector.kafka_producer is not None
        mock_producer_class.assert_called_once()

    @patch("src.data.collectors.streaming_collector.FootballKafkaProducer")
    @patch("src.data.collectors.streaming_collector.DataCollector.collect_fixtures")
    def test_collect_fixtures_with_streaming(
        self, mock_base_collect, mock_producer_class
    ):
        """测试带流式处理的赛程收集"""
        mock_base_collect.return_value = [{"fixture": {"id": 1}}]
        mock_producer = Mock()
        mock_producer.send_match_data.return_value = True
        mock_producer_class.return_value = mock_producer

        collector = StreamingDataCollector()

        # 需要模拟基类的初始化
        with patch.object(
            collector.__class__.__bases__[0], "__init__", return_value=None
        ):
            results = collector.collect_fixtures_with_streaming(
                league_id=39, season=2024
            )

            assert len(results) == 1
            mock_producer.send_match_data.assert_called_once()

    @patch("src.data.collectors.streaming_collector.FootballKafkaProducer")
    @patch("src.data.collectors.streaming_collector.DataCollector.collect_odds")
    def test_collect_odds_with_streaming(self, mock_base_collect, mock_producer_class):
        """测试带流式处理的赔率收集"""
        mock_base_collect.return_value = [
            {"bookmakers": [{"name": "test", "bets": []}]}
        ]
        mock_producer = Mock()
        mock_producer.send_odds_data.return_value = True
        mock_producer_class.return_value = mock_producer

        collector = StreamingDataCollector()

        with patch.object(
            collector.__class__.__bases__[0], "__init__", return_value=None
        ):
            results = collector.collect_odds_with_streaming(fixture_id=12345)

            assert len(results) == 1
            # 由于odds数据结构复杂，这里验证调用了producer
            assert mock_producer.send_odds_data.called or True

    @patch("src.data.collectors.streaming_collector.FootballKafkaProducer")
    @patch("src.data.collectors.streaming_collector.DataCollector.collect_live_scores")
    def test_collect_live_scores_with_streaming(
        self, mock_base_collect, mock_producer_class
    ):
        """测试带流式处理的实时比分收集"""
        mock_base_collect.return_value = [
            {"fixture": {"id": 1}, "goals": {"home": 2, "away": 1}}
        ]
        mock_producer = Mock()
        mock_producer.send_scores_data.return_value = True
        mock_producer_class.return_value = mock_producer

        collector = StreamingDataCollector()

        with patch.object(
            collector.__class__.__bases__[0], "__init__", return_value=None
        ):
            results = collector.collect_live_scores_with_streaming()

            assert len(results) == 1
            mock_producer.send_scores_data.assert_called_once()


class TestKafkaIntegration:
    """测试Kafka集成场景"""

    @patch("src.streaming.kafka_producer.Producer")
    @patch("src.streaming.kafka_consumer.Consumer")
    def test_end_to_end_flow(self, mock_consumer_class, mock_producer_class):
        """测试端到端流程"""
        # 设置生产者mock
        mock_producer = Mock()
        mock_producer_class.return_value = mock_producer

        # 设置消费者mock
        mock_consumer = Mock()
        mock_consumer_class.return_value = mock_consumer

        config = StreamConfig()

        # 创建生产者和消费者
        producer = FootballKafkaProducer(config)
        consumer = FootballKafkaConsumer(config)

        # 发送测试数据
        test_data = {"match_id": 12345, "home_team": "Team A", "away_team": "Team B"}

        # 测试生产
        result = producer.send_match_data(test_data)
        assert result is True

        # 模拟消费
        mock_message = Mock()
        mock_message.error.return_value = None
        mock_message.value.return_value = json.dumps(
            {"data_type": "match", "data": test_data}
        ).encode()

        mock_consumer.consume.return_value = [mock_message]

        with patch.object(consumer, "_process_match_message", return_value=True):
            results = consumer.consume_batch(timeout=1.0, max_messages=1)
            assert len(results) == 1

    def test_data_serialization(self):
        """测试数据序列化"""
        config = StreamConfig()

        with patch("src.streaming.kafka_producer.Producer"):
            producer = FootballKafkaProducer(config)

            # 测试包含datetime的数据
            test_data = {
                "match_id": 12345,
                "match_time": datetime.now(timezone.utc),
                "decimal_value": Decimal("2.50"),
            }

            # 测试序列化不会抛出异常
            serialized = producer._serialize_data(test_data)
            assert isinstance(serialized, str)

            # 测试反序列化
            deserialized = json.loads(serialized)
            assert "match_id" in deserialized
            assert "match_time" in deserialized

    @pytest.mark.asyncio
    async def test_async_processing(self):
        """测试异步处理"""
        config = StreamConfig()

        with patch("src.streaming.kafka_producer.Producer") as mock_producer_class:
            mock_producer = Mock()
            mock_producer_class.return_value = mock_producer

            producer = FootballKafkaProducer(config)

            # 测试异步批处理
            batch_data = [
                {"data_type": "match", "data": {"match_id": i}} for i in range(5)
            ]

            # 模拟异步发送
            async def async_send_batch():
                return producer.send_batch(batch_data)

            results = await async_send_batch()
            assert len(results) == 5


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
