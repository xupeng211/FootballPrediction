"""
流数据处理器测试 - 覆盖率提升版本

针对 StreamProcessor 和 StreamProcessorManager 的详细测试，专注于提升覆盖率至 70%+
"""

import pytest
import asyncio
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, Mock, patch
from typing import Dict, Any, List

from src.streaming.stream_processor import StreamProcessor, StreamProcessorManager


class TestStreamProcessor:
    """流数据处理器测试类"""

    @pytest.fixture
    def mock_config(self):
        """模拟流配置"""
        config = Mock()
        config.get_producer_config.return_value = {"bootstrap.servers": "localhost:9092"}
        config.get_consumer_config.return_value = {
            "bootstrap.servers": "localhost:9092",
            "group.id": "test-group"
        }
        return config

    @pytest.fixture
    def mock_producer(self):
        """模拟生产者"""
        producer = Mock()
        producer.send_batch = AsyncMock(return_value={"success": 2, "failed": 0})
        producer.send_match_data = AsyncMock(return_value=True)
        producer.send_odds_data = AsyncMock(return_value=True)
        producer.send_scores_data = AsyncMock(return_value=True)
        producer.close = Mock()
        producer.producer = Mock()
        producer.producer.list_topics = Mock(return_value=Mock(topics={"test-topic": None}))
        return producer

    @pytest.fixture
    def mock_consumer(self):
        """模拟消费者"""
        consumer = Mock()
        consumer.consume_batch = AsyncMock(return_value={"processed": 3, "failed": 0})
        consumer.start_consuming = AsyncMock()
        consumer.stop_consuming = Mock()
        consumer.subscribe_topics = Mock()
        consumer.subscribe_all_topics = Mock()
        consumer.consumer = Mock()
        return consumer

    @pytest.fixture
    def processor(self, mock_config, mock_producer, mock_consumer):
        """创建StreamProcessor实例"""
        with patch("src.streaming.stream_processor.FootballKafkaProducer") as mock_producer_class, \
             patch("src.streaming.stream_processor.FootballKafkaConsumer") as mock_consumer_class:

            mock_producer_class.return_value = mock_producer
            mock_consumer_class.return_value = mock_consumer

            return StreamProcessor(mock_config)

    # ===== 初始化和基础功能测试 =====

    def test_init_with_config(self, processor, mock_config):
        """测试使用配置初始化"""
        assert processor.config == mock_config
        assert processor.producer is None
        assert processor.consumer is None
        assert processor.logger is not None
        assert "messages_produced" in processor.processing_stats
        assert "messages_consumed" in processor.processing_stats
        assert "processing_errors" in processor.processing_stats

    def test_init_without_config(self):
        """测试不使用配置初始化"""
        with patch("src.streaming.stream_processor.StreamConfig") as mock_config_class:
            mock_config = Mock()
            mock_config_class.return_value = mock_config

            processor = StreamProcessor()

            assert processor.config == mock_config

    def test_initialize_producer(self, processor, mock_producer):
        """测试初始化生产者"""
        with patch("src.streaming.stream_processor.FootballKafkaProducer") as mock_producer_class:
            mock_producer_class.return_value = mock_producer

            producer = processor._initialize_producer()

            assert producer == mock_producer
            assert processor.producer == mock_producer

    def test_initialize_producer_existing(self, processor, mock_producer):
        """测试生产者已存在的情况"""
        processor.producer = mock_producer

        producer = processor._initialize_producer()

        assert producer == mock_producer
        # 确保没有重复创建
        assert processor.producer == mock_producer

    def test_initialize_consumer(self, processor, mock_consumer):
        """测试初始化消费者"""
        with patch("src.streaming.stream_processor.FootballKafkaConsumer") as mock_consumer_class:
            mock_consumer_class.return_value = mock_consumer

            consumer = processor._initialize_consumer("test-group")

            assert consumer == mock_consumer
            assert processor.consumer == mock_consumer

    def test_initialize_consumer_existing(self, processor, mock_consumer):
        """测试消费者已存在的情况"""
        processor.consumer = mock_consumer

        consumer = processor._initialize_consumer("test-group")

        assert consumer == mock_consumer
        # 确保没有重复创建

    # ===== 数据流处理测试 =====

    @pytest.mark.asyncio
    async def test_send_data_stream_success(self, processor):
        """测试成功发送数据流"""
        data_list = [
            {"match_id": "1", "data_type": "match", "data": {"home_team": "Team A"}},
            {"match_id": "2", "data_type": "match", "data": {"home_team": "Team B"}}
        ]

        result = await processor.send_data_stream(data_list, "match")

        assert result == {"success": 2, "failed": 0}
        assert processor.processing_stats["messages_produced"] == 2
        assert processor.processing_stats["processing_errors"] == 0

    @pytest.mark.asyncio
    async def test_send_data_stream_with_failures(self, processor, mock_producer):
        """测试发送数据流部分失败"""
        # 重新设置 producer mock 返回值
        processor.producer = mock_producer
        mock_producer.send_batch.return_value = {"success": 1, "failed": 2}

        data_list = [{"match_id": "1", "data_type": "match", "data": {"home_team": "Team A"}}]

        result = await processor.send_data_stream(data_list, "match")

        assert result == {"success": 1, "failed": 2}
        assert processor.processing_stats["messages_produced"] == 1
        assert processor.processing_stats["processing_errors"] == 2

    @pytest.mark.asyncio
    async def test_consume_data_stream_success(self, processor):
        """测试成功消费数据流"""
        topics = ["matches-stream", "odds-stream"]

        result = await processor.consume_data_stream(topics, batch_size=50, timeout=10.0)

        assert result == {"processed": 3, "failed": 0}
        assert processor.processing_stats["messages_consumed"] == 3
        assert processor.processing_stats["processing_errors"] == 0
        processor.consumer.subscribe_topics.assert_called_once_with(topics)

    @pytest.mark.asyncio
    async def test_consume_data_stream_all_topics(self, processor):
        """测试消费所有Topic"""
        result = await processor.consume_data_stream(None, batch_size=100, timeout=30.0)

        assert result == {"processed": 3, "failed": 0}
        processor.consumer.subscribe_all_topics.assert_called_once()

    @pytest.mark.asyncio
    async def test_consume_data_stream_with_failures(self, processor, mock_consumer):
        """测试消费数据流部分失败"""
        mock_consumer.consume_batch.return_value = {"processed": 2, "failed": 1}

        result = await processor.consume_data_stream(["test-topic"])

        assert result == {"processed": 2, "failed": 1}
        assert processor.processing_stats["messages_consumed"] == 2
        assert processor.processing_stats["processing_errors"] == 1

    @pytest.mark.asyncio
    async def test_start_continuous_processing(self, processor):
        """测试启动持续流处理"""
        topics = ["matches-stream"]

        await processor.start_continuous_processing(topics)

        assert processor.processing_stats["start_time"] is not None
        processor.consumer.subscribe_topics.assert_called_once_with(topics)
        processor.consumer.start_consuming.assert_called_once()

    @pytest.mark.asyncio
    async def test_start_continuous_processing_all_topics(self, processor):
        """测试启动持续流处理所有Topic"""
        await processor.start_continuous_processing(None)

        processor.consumer.subscribe_all_topics.assert_called_once()
        processor.consumer.start_consuming.assert_called_once()

    # ===== 数据处理便利方法测试 =====

    @pytest.mark.asyncio
    async def test_process_match_data_stream(self, processor):
        """测试处理比赛数据流"""
        match_data = [
            {"match_id": "1", "home_team": "Team A", "away_team": "Team B"},
            {"match_id": "2", "home_team": "Team C", "away_team": "Team D"}
        ]

        result = await processor.process_match_data_stream(match_data)

        assert result == {"success": 2, "failed": 0}

    @pytest.mark.asyncio
    async def test_process_odds_data_stream(self, processor):
        """测试处理赔率数据流"""
        odds_data = [
            {"match_id": "1", "home_odds": 2.10, "draw_odds": 3.40},
            {"match_id": "2", "home_odds": 1.90, "draw_odds": 3.60}
        ]

        result = await processor.process_odds_data_stream(odds_data)

        assert result == {"success": 2, "failed": 0}

    @pytest.mark.asyncio
    async def test_process_scores_data_stream(self, processor):
        """测试处理比分数据流"""
        scores_data = [
            {"match_id": "1", "home_score": 2, "away_score": 1},
            {"match_id": "2", "home_score": 0, "away_score": 0}
        ]

        result = await processor.process_scores_data_stream(scores_data)

        assert result == {"success": 2, "failed": 0}

    # ===== 停止和清理测试 =====

    def test_stop_processing(self, processor, mock_producer, mock_consumer):
        """测试停止处理"""
        processor.producer = mock_producer
        processor.consumer = mock_consumer

        processor.stop_processing()

        processor.consumer.stop_consuming.assert_called_once()
        processor.producer.close.assert_called_once()

    def test_stop(self, processor, mock_producer, mock_consumer):
        """测试停止方法"""
        processor.producer = mock_producer
        processor.consumer = mock_consumer

        processor.stop()

        processor.consumer.stop_consuming.assert_called_once()
        processor.producer.close.assert_called_once()

    def test_stop_processing_no_components(self, processor):
        """测试停止处理时组件不存在"""
        # 不应该抛出异常
        processor.stop_processing()

    # ===== 统计信息测试 =====

    def test_get_processing_stats_no_start_time(self, processor):
        """测试获取统计信息（无开始时间）"""
        processor.processing_stats = {
            "messages_produced": 10,
            "messages_consumed": 5,
            "processing_errors": 1,
            "start_time": None
        }

        stats = processor.get_processing_stats()

        assert stats["messages_produced"] == 10
        assert stats["messages_consumed"] == 5
        assert stats["processing_errors"] == 1
        assert "elapsed_seconds" not in stats
        assert "messages_per_second" not in stats

    def test_get_processing_stats_with_start_time(self, processor):
        """测试获取统计信息（有开始时间）"""
        start_time = datetime.now(timezone.utc)
        processor.processing_stats = {
            "messages_produced": 20,
            "messages_consumed": 15,
            "processing_errors": 2,
            "start_time": start_time
        }

        stats = processor.get_processing_stats()

        assert stats["messages_produced"] == 20
        assert stats["messages_consumed"] == 15
        assert stats["processing_errors"] == 2
        assert "elapsed_seconds" in stats
        assert "messages_per_second" in stats
        assert stats["messages_per_second"] > 0

    def test_get_processing_stats_zero_elapsed(self, processor):
        """测试获取统计信息（零耗时）"""
        processor.processing_stats = {
            "messages_produced": 0,
            "messages_consumed": 0,
            "processing_errors": 0,
            "start_time": datetime.now(timezone.utc)
        }

        # 模拟零耗时情况
        with patch('src.streaming.stream_processor.datetime') as mock_datetime:
            mock_datetime.now.return_value = processor.processing_stats["start_time"]
            stats = processor.get_processing_stats()

            assert stats["messages_per_second"] == 0.0

    # ===== 健康检查测试 =====

    @pytest.mark.asyncio
    async def test_health_check_healthy(self, processor, mock_producer, mock_consumer):
        """测试健康检查 - 健康状态"""
        processor.producer = mock_producer
        processor.consumer = mock_consumer

        result = await processor.health_check()

        assert result["producer_status"] == "healthy"
        assert result["consumer_status"] == "healthy"
        assert result["kafka_connection"] is True
        assert "available_topics" in result
        assert "processing_stats" in result
        assert "timestamp" in result

    @pytest.mark.asyncio
    async def test_health_check_not_initialized(self, processor):
        """测试健康检查 - 未初始化状态"""
        result = await processor.health_check()

        assert result["producer_status"] == "not_initialized"
        assert result["consumer_status"] == "not_initialized"
        assert result["kafka_connection"] is False
        assert "error" not in result

    @pytest.mark.asyncio
    async def test_health_check_kafka_connection_error(self, processor, mock_producer):
        """测试健康检查 - Kafka连接错误"""
        processor.producer = mock_producer
        mock_producer.producer.list_topics.side_effect = Exception("Connection failed")

        result = await processor.health_check()

        assert result["producer_status"] == "healthy"
        assert result["kafka_connection"] is False
        assert "error" in result

    @pytest.mark.asyncio
    async def test_health_check_general_exception(self, processor, mock_producer):
        """测试健康检查 - 一般异常"""
        processor.producer = mock_producer
        mock_producer.producer.list_topics.side_effect = Exception("General error")

        result = await processor.health_check()

        assert "error" in result
        assert "General error" in result["error"]

    # ===== 其他方法测试 =====

    def test_start_success(self, processor):
        """测试启动成功"""
        result = processor.start()

        assert result is True
        assert processor.processing_stats["start_time"] is not None

    def test_start_failure(self, processor):
        """测试启动失败"""
        with patch.object(processor, 'logger') as mock_logger:
            # 模拟异常
            processor.processing_stats["start_time"] = None
            with patch('src.streaming.stream_processor.datetime') as mock_datetime:
                mock_datetime.now.side_effect = Exception("Start failed")

                result = processor.start()

                assert result is False
                mock_logger.error.assert_called_once()

    @pytest.mark.asyncio
    async def test_send_data_match_type(self, processor):
        """测试发送比赛类型数据"""
        data = {"match_id": "1", "home_team": "Team A"}

        result = await processor.send_data(data, "match")

        assert result is True

    @pytest.mark.asyncio
    async def test_send_data_odds_type(self, processor):
        """测试发送赔率类型数据"""
        data = {"match_id": "1", "home_odds": 2.10}

        result = await processor.send_data(data, "odds")

        assert result is True

    @pytest.mark.asyncio
    async def test_send_data_scores_type(self, processor):
        """测试发送比分类型数据"""
        data = {"match_id": "1", "home_score": 2}

        result = await processor.send_data(data, "scores")

        assert result is True

    @pytest.mark.asyncio
    async def test_send_data_invalid_type(self, processor):
        """测试发送无效类型数据"""
        data = {"match_id": "1"}

        result = await processor.send_data(data, "invalid")

        assert result is False

    @pytest.mark.asyncio
    async def test_send_data_exception(self, processor):
        """测试发送数据异常"""
        processor.producer = Mock()
        processor.producer.send_match_data = AsyncMock(side_effect=Exception("Send failed"))

        data = {"match_id": "1"}

        result = await processor.send_data(data, "match")

        assert result is False

    def test_consume_data_success(self, processor):
        """测试消费数据成功"""
        result = processor.consume_data(timeout=5.0, max_messages=10)

        assert "processed" in result
        assert "failed" in result
        processor.consumer.subscribe_all_topics.assert_called_once()

    def test_consume_data_exception(self, processor):
        """测试消费数据异常"""
        processor.consumer = Mock()
        processor.consumer.subscribe_all_topics.side_effect = Exception("Consume failed")

        result = processor.consume_data()

        assert result == {"processed": 0, "failed": 1}

    # ===== 上下文管理器测试 =====

    @pytest.mark.asyncio
    async def test_async_context_manager(self, processor):
        """测试异步上下文管理器"""
        async with processor as p:
            assert p == processor

        # 验证stop_processing被调用
        assert processor.consumer.stop_consuming.called

    # ===== 边界情况测试 =====

    @pytest.mark.asyncio
    async def test_send_data_stream_empty_list(self, processor):
        """测试发送空数据列表"""
        result = await processor.send_data_stream([], "match")

        assert result == {"success": 2, "failed": 0}

    @pytest.mark.asyncio
    async def test_consume_data_stream_empty_topics(self, processor):
        """测试消费空Topic列表"""
        result = await processor.consume_data_stream([], batch_size=10, timeout=5.0)

        assert result == {"processed": 3, "failed": 0}

    def test_get_processing_stats_empty(self, processor):
        """测试获取空统计信息"""
        processor.processing_stats = {}

        stats = processor.get_processing_stats()

        assert isinstance(stats, dict)


class TestStreamProcessorManager:
    """流处理器管理器测试类"""

    @pytest.fixture
    def mock_config(self):
        """模拟流配置"""
        return Mock()

    @pytest.fixture
    def manager(self, mock_config):
        """创建StreamProcessorManager实例"""
        with patch("src.streaming.stream_processor.StreamProcessor") as mock_processor_class:
            mock_processor = Mock()
            mock_processor_class.return_value = mock_processor

            return StreamProcessorManager(mock_config, num_processors=2)

    # ===== 初始化测试 =====

    def test_init(self, manager, mock_config):
        """测试初始化"""
        assert manager.config == mock_config
        assert len(manager.processors) == 2
        assert manager.logger is not None

    def test_init_default_num_processors(self, mock_config):
        """测试默认处理器数量"""
        with patch("src.streaming.stream_processor.StreamProcessor") as mock_processor_class:
            mock_processor = Mock()
            mock_processor_class.return_value = mock_processor

            manager = StreamProcessorManager(mock_config)

            assert len(manager.processors) == 1

    # ===== 批量操作测试 =====

    def test_start_all_success(self, manager):
        """测试启动所有处理器成功"""
        for processor in manager.processors:
            processor.start.return_value = True

        result = manager.start_all()

        assert result is True
        for processor in manager.processors:
            processor.start.assert_called_once()

    def test_start_all_failure(self, manager):
        """测试启动所有处理器失败"""
        for processor in manager.processors:
            processor.start.side_effect = Exception("Start failed")

        result = manager.start_all()

        assert result is False

    def test_stop_all_success(self, manager):
        """测试停止所有处理器成功"""
        result = manager.stop_all()

        assert result is True
        for processor in manager.processors:
            processor.stop_processing.assert_called_once()

    def test_stop_all_failure(self, manager):
        """测试停止所有处理器失败"""
        for processor in manager.processors:
            processor.stop_processing.side_effect = Exception("Stop failed")

        result = manager.stop_all()

        assert result is False

    @pytest.mark.asyncio
    async def test_start_all_processors(self, manager):
        """测试启动所有处理器（异步版本）"""
        topics = ["matches-stream", "odds-stream"]

        for processor in manager.processors:
            processor.consumer = Mock()
            processor.start_continuous_processing = AsyncMock()

        await manager.start_all_processors(topics)

        for processor in manager.processors:
            processor.start_continuous_processing.assert_called_once_with(topics)

    @pytest.mark.asyncio
    async def test_start_all_processors_no_topics(self, manager):
        """测试启动所有处理器（无Topic）"""
        for processor in manager.processors:
            processor.consumer = Mock()
            processor.start_continuous_processing = AsyncMock()

        await manager.start_all_processors(None)

        for processor in manager.processors:
            processor.start_continuous_processing.assert_called_once_with(None)

    @pytest.mark.asyncio
    async def test_start_all_processors_with_exceptions(self, manager):
        """测试启动所有处理器（有异常）"""
        for processor in manager.processors:
            processor.consumer = Mock()
            processor.start_continuous_processing = AsyncMock(side_effect=Exception("Processor failed"))

        # 不应该抛出异常
        await manager.start_all_processors(["test-topic"])

    def test_stop_all_processors(self, manager):
        """测试停止所有处理器"""
        manager.stop_all_processors()

        for processor in manager.processors:
            processor.stop_processing.assert_called_once()

    # ===== 统计信息测试 =====

    @pytest.mark.asyncio
    async def test_get_aggregate_stats(self, manager):
        """测试获取聚合统计信息"""
        # 设置模拟统计信息
        for i, processor in enumerate(manager.processors):
            processor.get_processing_stats.return_value = {
                "messages_produced": 10 + i,
                "messages_consumed": 5 + i,
                "processing_errors": i,
                "start_time": datetime.now(timezone.utc)
            }

        stats = await manager.get_aggregate_stats()

        assert stats["total_processors"] == 2
        assert stats["total_messages_produced"] == 21  # 10 + 11
        assert stats["total_messages_consumed"] == 11  # 5 + 6
        assert stats["total_processing_errors"] == 1  # 0 + 1
        assert len(stats["processor_stats"]) == 2
        assert stats["processor_stats"][0]["processor_id"] == 0
        assert stats["processor_stats"][1]["processor_id"] == 1

    @pytest.mark.asyncio
    async def test_get_aggregate_stats_empty(self, manager):
        """测试获取空聚合统计信息"""
        for processor in manager.processors:
            processor.get_processing_stats.return_value = {}

        stats = await manager.get_aggregate_stats()

        assert stats["total_processors"] == 2
        assert stats["total_messages_produced"] == 0
        assert stats["total_messages_consumed"] == 0
        assert stats["total_processing_errors"] == 0

    # ===== 上下文管理器测试 =====

    @pytest.mark.asyncio
    async def test_async_context_manager(self, manager):
        """测试异步上下文管理器"""
        async with manager as m:
            assert m == manager

        # 验证stop_all_processors被调用
        for processor in manager.processors:
            processor.stop_processing.assert_called_once()

    # ===== 边界情况测试 =====

    def test_manager_zero_processors(self, mock_config):
        """测试零个处理器"""
        with patch("src.streaming.stream_processor.StreamProcessor") as mock_processor_class:
            manager = StreamProcessorManager(mock_config, num_processors=0)

            assert len(manager.processors) == 0

            stats = asyncio.run(manager.get_aggregate_stats())
            assert stats["total_processors"] == 0
            assert stats["total_messages_produced"] == 0

    def test_manager_many_processors(self, mock_config):
        """测试多个处理器"""
        with patch("src.streaming.stream_processor.StreamProcessor") as mock_processor_class:
            manager = StreamProcessorManager(mock_config, num_processors=10)

            assert len(manager.processors) == 10

            # 测试启动和停止
            assert manager.start_all() is True
            assert manager.stop_all() is True


if __name__ == "__main__":
    # 运行所有测试
    pytest.main([__file__, "-v", "--tb=short"])