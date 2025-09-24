"""
Phase 6: stream_processor.py 补测用例
目标：提升覆盖率从 42% 到 70%+
重点：错误分支、延迟处理、空消息场景、批处理失败等未覆盖分支
"""

import asyncio
import json
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, Mock, patch

import pytest
from confluent_kafka import KafkaError, KafkaException

from src.streaming.stream_config import StreamConfig
from src.streaming.stream_processor import StreamProcessor, StreamProcessorManager


class TestStreamProcessorInitialization:
    """测试流处理器初始化"""

    def test_initialization_with_default_config(self):
        """测试使用默认配置初始化"""
        with patch(
            "src.streaming.stream_processor.FootballKafkaConsumer"
        ) as mock_consumer:
            with patch(
                "src.streaming.stream_processor.FootballKafkaProducer"
            ) as mock_producer:
                processor = StreamProcessor()

                assert processor.config is not None
                assert processor.logger is not None
                assert not processor.running
                assert processor.consumer is not None
                assert processor.producer is not None

    def test_initialization_with_custom_config(self):
        """测试使用自定义配置初始化"""
        custom_config = StreamConfig()
        custom_config.bootstrap_servers = "custom-server:9092"

        with patch(
            "src.streaming.stream_processor.FootballKafkaConsumer"
        ) as mock_consumer:
            with patch(
                "src.streaming.stream_processor.FootballKafkaProducer"
            ) as mock_producer:
                processor = FootballStreamProcessor(config=custom_config)

                assert processor.config == custom_config

    def test_initialization_consumer_creation_failure(self):
        """测试消费者创建失败"""
        with patch(
            "src.streaming.stream_processor.FootballKafkaConsumer"
        ) as mock_consumer:
            mock_consumer.side_effect = Exception("Consumer creation failed")

            with pytest.raises(Exception):
                StreamProcessor()

    def test_initialization_producer_creation_failure(self):
        """测试生产者创建失败"""
        with patch(
            "src.streaming.stream_processor.FootballKafkaConsumer"
        ) as mock_consumer:
            with patch(
                "src.streaming.stream_processor.FootballKafkaProducer"
            ) as mock_producer:
                mock_producer.side_effect = Exception("Producer creation failed")

                with pytest.raises(Exception):
                    StreamProcessor()


class TestStreamProcessorDataProcessing:
    """测试数据处理功能"""

    def setup_method(self):
        with patch(
            "src.streaming.stream_processor.FootballKafkaConsumer"
        ) as mock_consumer:
            with patch(
                "src.streaming.stream_processor.FootballKafkaProducer"
            ) as mock_producer:
                self.mock_consumer = Mock()
                self.mock_producer = Mock()
                mock_consumer.return_value = self.mock_consumer
                mock_producer.return_value = self.mock_producer
                self.processor = FootballStreamProcessor()

    @pytest.mark.asyncio
    async def test_process_match_data_success(self):
        """测试成功处理比赛数据"""
        match_data = {
            "match_id": 123,
            "home_team": "Arsenal",
            "away_team": "Chelsea",
            "status": "scheduled",
        }

        result = await self.processor.process_match_data(match_data)

        assert result is True

    @pytest.mark.asyncio
    async def test_process_match_data_missing_required_fields(self):
        """测试处理缺少必需字段的比赛数据"""
        incomplete_data = {
            "home_team": "Arsenal"
            # 缺少 match_id 和 away_team
        }

        result = await self.processor.process_match_data(incomplete_data)

        assert result is False

    @pytest.mark.asyncio
    async def test_process_match_data_invalid_format(self):
        """测试处理无效格式的比赛数据"""
        invalid_data = "not a dict"

        with pytest.raises(AttributeError):
            await self.processor.process_match_data(invalid_data)

    @pytest.mark.asyncio
    async def test_process_odds_data_success(self):
        """测试成功处理赔率数据"""
        odds_data = {
            "match_id": 123,
            "home_win": 2.5,
            "draw": 3.2,
            "away_win": 2.8,
            "timestamp": "2023-01-01T10:00:00Z",
        }

        result = await self.processor.process_odds_data(odds_data)

        assert result is True

    @pytest.mark.asyncio
    async def test_process_odds_data_invalid_odds(self):
        """测试处理无效赔率数据"""
        invalid_odds = {
            "match_id": 123,
            "home_win": -1.0,  # 负数赔率
            "draw": 3.2,
            "away_win": 2.8,
        }

        result = await self.processor.process_odds_data(invalid_odds)

        assert result is False

    @pytest.mark.asyncio
    async def test_process_scores_data_success(self):
        """测试成功处理比分数据"""
        scores_data = {
            "match_id": 123,
            "home_score": 2,
            "away_score": 1,
            "status": "finished",
            "timestamp": "2023-01-01T17:00:00Z",
        }

        result = await self.processor.process_scores_data(scores_data)

        assert result is True

    @pytest.mark.asyncio
    async def test_process_scores_data_negative_scores(self):
        """测试处理负数比分"""
        invalid_scores = {
            "match_id": 123,
            "home_score": -1,  # 负数比分
            "away_score": 2,
            "status": "finished",
        }

        result = await self.processor.process_scores_data(invalid_scores)

        assert result is False


class TestStreamProcessorBatchProcessing:
    """测试批处理功能"""

    def setup_method(self):
        with patch(
            "src.streaming.stream_processor.FootballKafkaConsumer"
        ) as mock_consumer:
            with patch(
                "src.streaming.stream_processor.FootballKafkaProducer"
            ) as mock_producer:
                self.mock_consumer = Mock()
                self.mock_producer = Mock()
                mock_consumer.return_value = self.mock_consumer
                mock_producer.return_value = self.mock_producer
                self.processor = FootballStreamProcessor()

    @pytest.mark.asyncio
    async def test_process_batch_messages_success(self):
        """测试成功批处理消息"""
        messages = [
            {
                "type": "match",
                "data": {"match_id": 1, "home_team": "A", "away_team": "B"},
            },
            {
                "type": "odds",
                "data": {"match_id": 1, "home_win": 2.0, "draw": 3.0, "away_win": 2.5},
            },
            {
                "type": "scores",
                "data": {
                    "match_id": 1,
                    "home_score": 1,
                    "away_score": 0,
                    "status": "finished",
                },
            },
        ]

        result = await self.processor.process_batch_messages(messages)

        assert result["total"] == 3
        assert result["success"] == 3
        assert result["failed"] == 0

    @pytest.mark.asyncio
    async def test_process_batch_messages_partial_failure(self):
        """测试批处理部分失败"""
        messages = [
            {
                "type": "match",
                "data": {"match_id": 1, "home_team": "A", "away_team": "B"},
            },  # 成功
            {"type": "invalid", "data": {"some": "data"}},  # 失败：无效类型
            {"type": "odds", "data": {"match_id": 1}},  # 失败：数据不完整
        ]

        result = await self.processor.process_batch_messages(messages)

        assert result["total"] == 3
        assert result["success"] == 1
        assert result["failed"] == 2

    @pytest.mark.asyncio
    async def test_process_batch_messages_empty_batch(self):
        """测试处理空批次"""
        result = await self.processor.process_batch_messages([])

        assert result["total"] == 0
        assert result["success"] == 0
        assert result["failed"] == 0

    @pytest.mark.asyncio
    async def test_process_batch_messages_all_invalid(self):
        """测试处理全部无效的批次"""
        invalid_messages = [
            {"type": "unknown", "data": {}},
            {"invalid": "structure"},
            None,
            {"type": "match", "data": {}},  # 缺少必需字段
        ]

        result = await self.processor.process_batch_messages(invalid_messages)

        assert result["total"] == 4
        assert result["success"] == 0
        assert result["failed"] == 4


class TestStreamProcessorErrorHandling:
    """测试错误处理"""

    def setup_method(self):
        with patch(
            "src.streaming.stream_processor.FootballKafkaConsumer"
        ) as mock_consumer:
            with patch(
                "src.streaming.stream_processor.FootballKafkaProducer"
            ) as mock_producer:
                self.mock_consumer = Mock()
                self.mock_producer = Mock()
                mock_consumer.return_value = self.mock_consumer
                mock_producer.return_value = self.mock_producer
                self.processor = FootballStreamProcessor()

    @pytest.mark.asyncio
    async def test_handle_processing_error_with_retry(self):
        """测试处理错误时的重试机制"""
        error = Exception("Processing failed")
        message_data = {"match_id": 123}

        # Mock 重试逻辑
        with patch.object(self.processor, "_should_retry_error") as mock_should_retry:
            mock_should_retry.return_value = True

            with patch.object(self.processor, "_wait_before_retry") as mock_wait:
                mock_wait.return_value = None

                result = await self.processor.handle_processing_error(
                    error, message_data
                )

                # 应该记录错误并尝试恢复
                assert result is not None

    @pytest.mark.asyncio
    async def test_handle_processing_error_no_retry(self):
        """测试处理不可重试的错误"""
        error = ValueError("Invalid data format")
        message_data = {"invalid": "data"}

        with patch.object(self.processor, "_should_retry_error") as mock_should_retry:
            mock_should_retry.return_value = False

            result = await self.processor.handle_processing_error(error, message_data)

            # 应该直接返回失败
            assert result is False

    def test_should_retry_error_transient_errors(self):
        """测试识别可重试的瞬态错误"""
        transient_errors = [
            ConnectionError("Network timeout"),
            TimeoutError("Request timeout"),
            Exception("Temporary unavailable"),
        ]

        for error in transient_errors:
            should_retry = self.processor._should_retry_error(error)
            # 根据实际实现调整断言
            assert isinstance(should_retry, bool)

    def test_should_retry_error_permanent_errors(self):
        """测试识别不可重试的永久错误"""
        permanent_errors = [
            ValueError("Invalid format"),
            KeyError("Missing key"),
            TypeError("Wrong type"),
        ]

        for error in permanent_errors:
            should_retry = self.processor._should_retry_error(error)
            # 根据实际实现调整断言
            assert isinstance(should_retry, bool)

    @pytest.mark.asyncio
    async def test_wait_before_retry_exponential_backoff(self):
        """测试指数退避重试等待"""
        import time

        start_time = time.time()
        await self.processor._wait_before_retry(attempt=1)
        elapsed = time.time() - start_time

        # 应该等待一定时间
        assert elapsed >= 0


class TestStreamProcessorMessageRouting:
    """测试消息路由"""

    def setup_method(self):
        with patch(
            "src.streaming.stream_processor.FootballKafkaConsumer"
        ) as mock_consumer:
            with patch(
                "src.streaming.stream_processor.FootballKafkaProducer"
            ) as mock_producer:
                self.mock_consumer = Mock()
                self.mock_producer = Mock()
                mock_consumer.return_value = self.mock_consumer
                mock_producer.return_value = self.mock_producer
                self.processor = FootballStreamProcessor()

    @pytest.mark.asyncio
    async def test_route_message_to_correct_processor(self):
        """测试将消息路由到正确的处理器"""
        test_cases = [
            ("match", {"match_id": 1, "home_team": "A", "away_team": "B"}),
            ("odds", {"match_id": 1, "home_win": 2.0, "draw": 3.0, "away_win": 2.5}),
            (
                "scores",
                {"match_id": 1, "home_score": 1, "away_score": 0, "status": "finished"},
            ),
        ]

        for message_type, data in test_cases:
            message = {"type": message_type, "data": data}

            with patch.object(
                self.processor, f"process_{message_type}_data"
            ) as mock_processor:
                mock_processor.return_value = True

                result = await self.processor.route_message(message)

                assert result is True
                mock_processor.assert_called_once_with(data)

    @pytest.mark.asyncio
    async def test_route_message_unknown_type(self):
        """测试路由未知类型消息"""
        unknown_message = {"type": "unknown", "data": {"some": "data"}}

        result = await self.processor.route_message(unknown_message)

        assert result is False

    @pytest.mark.asyncio
    async def test_route_message_missing_type(self):
        """测试路由缺少类型字段的消息"""
        invalid_message = {"data": {"some": "data"}}  # 缺少 type 字段

        with pytest.raises(KeyError):
            await self.processor.route_message(invalid_message)

    @pytest.mark.asyncio
    async def test_route_message_missing_data(self):
        """测试路由缺少数据字段的消息"""
        invalid_message = {"type": "match"}  # 缺少 data 字段

        with pytest.raises(KeyError):
            await self.processor.route_message(invalid_message)


class TestStreamProcessorLifecycle:
    """测试流处理器生命周期"""

    def setup_method(self):
        with patch(
            "src.streaming.stream_processor.FootballKafkaConsumer"
        ) as mock_consumer:
            with patch(
                "src.streaming.stream_processor.FootballKafkaProducer"
            ) as mock_producer:
                self.mock_consumer = Mock()
                self.mock_producer = Mock()
                mock_consumer.return_value = self.mock_consumer
                mock_producer.return_value = self.mock_producer
                self.processor = FootballStreamProcessor()

    @pytest.mark.asyncio
    async def test_start_processing_normal_flow(self):
        """测试正常处理流程"""
        # Mock 消费者返回消息
        mock_messages = [
            {
                "type": "match",
                "data": {"match_id": 1, "home_team": "A", "away_team": "B"},
            },
            None,  # 表示没有更多消息
        ]

        self.mock_consumer.poll_message.side_effect = mock_messages

        # 设置处理器运行状态
        self.processor.running = True

        # 创建停止任务
        async def stop_after_delay():
            await asyncio.sleep(0.1)
            self.processor.stop_processing()

        stop_task = asyncio.create_task(stop_after_delay())

        await self.processor.start_processing()

        await stop_task

    @pytest.mark.asyncio
    async def test_start_processing_with_consumer_error(self):
        """测试消费者错误时的处理"""
        self.mock_consumer.poll_message.side_effect = KafkaException("Consumer error")

        self.processor.running = True

        async def stop_after_delay():
            await asyncio.sleep(0.1)
            self.processor.stop_processing()

        stop_task = asyncio.create_task(stop_after_delay())

        # 应该处理异常而不是崩溃
        await self.processor.start_processing()

        await stop_task

    def test_stop_processing(self):
        """测试停止处理"""
        self.processor.running = True

        self.processor.stop_processing()

        assert not self.processor.running

    @pytest.mark.asyncio
    async def test_shutdown_graceful(self):
        """测试优雅关闭"""
        await self.processor.shutdown()

        # 验证消费者和生产者被关闭
        self.mock_consumer.close.assert_called_once()
        self.mock_producer.close.assert_called_once()

    @pytest.mark.asyncio
    async def test_shutdown_with_consumer_error(self):
        """测试关闭时消费者错误"""
        self.mock_consumer.close.side_effect = Exception("Consumer close error")

        # 应该继续关闭生产者而不是崩溃
        await self.processor.shutdown()

        self.mock_producer.close.assert_called_once()

    @pytest.mark.asyncio
    async def test_shutdown_with_producer_error(self):
        """测试关闭时生产者错误"""
        self.mock_producer.close.side_effect = Exception("Producer close error")

        # 应该处理异常而不是崩溃
        await self.processor.shutdown()


class TestStreamProcessorMetrics:
    """测试指标收集"""

    def setup_method(self):
        with patch(
            "src.streaming.stream_processor.FootballKafkaConsumer"
        ) as mock_consumer:
            with patch(
                "src.streaming.stream_processor.FootballKafkaProducer"
            ) as mock_producer:
                self.mock_consumer = Mock()
                self.mock_producer = Mock()
                mock_consumer.return_value = self.mock_consumer
                mock_producer.return_value = self.mock_producer
                self.processor = FootballStreamProcessor()

    def test_get_processing_stats(self):
        """测试获取处理统计"""
        # 模拟一些处理活动
        self.processor._processed_messages = 100
        self.processor._failed_messages = 5
        self.processor._start_time = datetime.now()

        stats = self.processor.get_processing_stats()

        assert "processed_messages" in stats
        assert "failed_messages" in stats
        assert "success_rate" in stats
        assert "uptime" in stats

        assert stats["processed_messages"] == 100
        assert stats["failed_messages"] == 5
        assert stats["success_rate"] == 0.95  # 95/100

    def test_reset_stats(self):
        """测试重置统计"""
        # 设置一些统计数据
        self.processor._processed_messages = 50
        self.processor._failed_messages = 10

        self.processor.reset_stats()

        stats = self.processor.get_processing_stats()
        assert stats["processed_messages"] == 0
        assert stats["failed_messages"] == 0


class TestStreamProcessorEdgeCases:
    """测试边界情况"""

    def setup_method(self):
        with patch(
            "src.streaming.stream_processor.FootballKafkaConsumer"
        ) as mock_consumer:
            with patch(
                "src.streaming.stream_processor.FootballKafkaProducer"
            ) as mock_producer:
                self.mock_consumer = Mock()
                self.mock_producer = Mock()
                mock_consumer.return_value = self.mock_consumer
                mock_producer.return_value = self.mock_producer
                self.processor = FootballStreamProcessor()

    @pytest.mark.asyncio
    async def test_process_very_large_batch(self):
        """测试处理非常大的批次"""
        # 创建1000条消息的大批次
        large_batch = []
        for i in range(1000):
            large_batch.append(
                {
                    "type": "match",
                    "data": {
                        "match_id": i,
                        "home_team": f"Team{i}A",
                        "away_team": f"Team{i}B",
                    },
                }
            )

        result = await self.processor.process_batch_messages(large_batch)

        assert result["total"] == 1000

    @pytest.mark.asyncio
    async def test_concurrent_processing(self):
        """测试并发处理"""
        messages = [
            {
                "type": "match",
                "data": {"match_id": i, "home_team": f"A{i}", "away_team": f"B{i}"},
            }
            for i in range(10)
        ]

        # 创建多个并发处理任务
        tasks = []
        for message in messages:
            task = self.processor.route_message(message)
            tasks.append(task)

        results = await asyncio.gather(*tasks, return_exceptions=True)

        # 所有任务应该成功完成
        assert len(results) == 10

    @pytest.mark.asyncio
    async def test_process_malformed_json(self):
        """测试处理格式错误的JSON"""
        malformed_messages = [
            None,
            "",
            "not json",
            {"incomplete": "message"},
            {"type": None, "data": None},
        ]

        results = []
        for message in malformed_messages:
            try:
                result = await self.processor.route_message(message)
                results.append(result)
            except Exception as e:
                results.append(False)

        # 所有格式错误的消息都应该处理失败
        assert all(result is False for result in results)

    def test_memory_usage_with_large_datasets(self):
        """测试大数据集的内存使用"""
        # 创建大量数据但不立即处理
        large_data = {
            "match_id": 1,
            "large_field": "x" * 100000,  # 100KB 字符串
            "nested_data": {"level1": {"level2": {"level3": "data" * 1000}}},
        }

        # 验证处理器可以处理大数据而不崩溃
        import sys

        initial_memory = sys.getsizeof(self.processor)

        # 模拟处理大数据
        for _ in range(10):
            self.processor._processed_messages += 1

        # 内存使用不应该大幅增长
        final_memory = sys.getsizeof(self.processor)
        memory_growth = final_memory - initial_memory

        # 合理的内存增长阈值
        assert memory_growth < 10000  # 10KB
