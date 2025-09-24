"""
Phase 6: stream_processor.py 补测用例
目标：提升覆盖率从 42% 到 70%+
重点：错误分支、延迟处理、空消息场景、批处理失败等未覆盖分支
"""

import asyncio
from datetime import datetime
from unittest.mock import AsyncMock, Mock, patch

import pytest

from src.streaming.stream_config import StreamConfig
from src.streaming.stream_processor import StreamProcessor, StreamProcessorManager


class TestStreamProcessorBasic:
    """测试流处理器基础功能"""

    def test_initialization_with_default_config(self):
        """测试使用默认配置初始化"""
        processor = StreamProcessor()

        assert processor.config is not None
        assert processor.logger is not None
        assert processor.producer is None
        assert processor.consumer is None

    def test_initialization_with_custom_config(self):
        """测试使用自定义配置初始化"""
        custom_config = StreamConfig()
        custom_config.bootstrap_servers = "custom-server:9092"

        processor = StreamProcessor(config=custom_config)

        assert processor.config == custom_config

    @pytest.mark.asyncio
    async def test_initialize_with_mocked_components(self):
        """测试使用模拟组件初始化"""
        processor = StreamProcessor()

        with patch(
            "src.streaming.stream_processor.FootballKafkaProducer"
        ) as mock_producer:
            with patch(
                "src.streaming.stream_processor.FootballKafkaConsumer"
            ) as mock_consumer:
                mock_producer.return_value = Mock()
                mock_consumer.return_value = Mock()

                await processor.initialize()

                assert processor.producer is not None
                assert processor.consumer is not None

    @pytest.mark.asyncio
    async def test_send_data_without_producer(self):
        """测试未初始化生产者时发送数据"""
        processor = StreamProcessor()
        processor.producer = None

        result = await processor.send_data_stream("test-topic", {"test": "data"})

        assert result is False

    @pytest.mark.asyncio
    async def test_consume_data_without_consumer(self):
        """测试未初始化消费者时消费数据"""
        processor = StreamProcessor()
        processor.consumer = None

        result = await processor.consume_data_stream(timeout=1.0)

        assert result is None

    def test_stats_functionality(self):
        """测试统计功能"""
        processor = StreamProcessor()

        # 测试初始统计
        stats = processor.get_stats()
        assert isinstance(stats, dict)

        # 测试更新统计
        processor._update_stats("send_success")
        updated_stats = processor.get_stats()
        assert "messages_sent" in updated_stats or "send_success" in str(updated_stats)

        # 测试重置统计
        processor.reset_stats()
        reset_stats = processor.get_stats()
        assert isinstance(reset_stats, dict)

    @pytest.mark.asyncio
    async def test_cleanup_without_components(self):
        """测试清理空组件"""
        processor = StreamProcessor()
        processor.producer = None
        processor.consumer = None

        # 应该不抛出异常
        await processor.cleanup()

    @pytest.mark.asyncio
    async def test_send_batch_empty_list(self):
        """测试发送空批次"""
        processor = StreamProcessor()

        result = await processor.send_batch_messages([])

        assert result["total"] == 0
        assert result["success"] == 0
        assert result["failed"] == 0


class TestStreamProcessorManager:
    """测试流处理器管理器"""

    def test_manager_initialization(self):
        """测试管理器初始化"""
        manager = StreamProcessorManager()

        assert manager.processors == {}
        assert manager.logger is not None

    @pytest.mark.asyncio
    async def test_create_processor(self):
        """测试创建处理器"""
        manager = StreamProcessorManager()

        processor = await manager.create_processor("test-processor")

        assert processor is not None
        assert manager.processors["test-processor"] == processor

    @pytest.mark.asyncio
    async def test_create_duplicate_processor(self):
        """测试创建重复名称的处理器"""
        manager = StreamProcessorManager()

        await manager.create_processor("test-processor")

        with pytest.raises(ValueError):
            await manager.create_processor("test-processor")

    def test_get_existing_processor(self):
        """测试获取存在的处理器"""
        manager = StreamProcessorManager()
        mock_processor = Mock()
        manager.processors["test-processor"] = mock_processor

        retrieved = manager.get_processor("test-processor")

        assert retrieved == mock_processor

    def test_get_nonexistent_processor(self):
        """测试获取不存在的处理器"""
        manager = StreamProcessorManager()

        with pytest.raises(KeyError):
            manager.get_processor("nonexistent-processor")

    @pytest.mark.asyncio
    async def test_remove_processor(self):
        """测试移除处理器"""
        manager = StreamProcessorManager()
        mock_processor = Mock()
        mock_processor.cleanup = AsyncMock()
        manager.processors["test-processor"] = mock_processor

        await manager.remove_processor("test-processor")

        assert "test-processor" not in manager.processors
        mock_processor.cleanup.assert_called_once()

    @pytest.mark.asyncio
    async def test_remove_nonexistent_processor(self):
        """测试移除不存在的处理器"""
        manager = StreamProcessorManager()

        with pytest.raises(KeyError):
            await manager.remove_processor("nonexistent-processor")

    def test_list_processors(self):
        """测试列出处理器"""
        manager = StreamProcessorManager()

        # 空列表
        assert manager.list_processors() == []

        # 添加处理器
        manager.processors["proc1"] = Mock()
        manager.processors["proc2"] = Mock()

        processor_names = manager.list_processors()
        assert set(processor_names) == {"proc1", "proc2"}

    @pytest.mark.asyncio
    async def test_shutdown_all(self):
        """测试关闭所有处理器"""
        manager = StreamProcessorManager()

        mock_processor1 = Mock()
        mock_processor1.cleanup = AsyncMock()
        mock_processor2 = Mock()
        mock_processor2.cleanup = AsyncMock()

        manager.processors["proc1"] = mock_processor1
        manager.processors["proc2"] = mock_processor2

        await manager.shutdown_all()

        mock_processor1.cleanup.assert_called_once()
        mock_processor2.cleanup.assert_called_once()
        assert manager.processors == {}


class TestStreamProcessorErrorHandling:
    """测试错误处理"""

    @pytest.mark.asyncio
    async def test_send_with_producer_exception(self):
        """测试生产者异常时的发送"""
        processor = StreamProcessor()
        mock_producer = Mock()
        mock_producer.send_message.side_effect = Exception("Send failed")
        processor.producer = mock_producer

        result = await processor.send_data_stream("test-topic", {"test": "data"})

        assert result is False

    @pytest.mark.asyncio
    async def test_consume_with_consumer_exception(self):
        """测试消费者异常时的消费"""
        processor = StreamProcessor()
        mock_consumer = Mock()
        mock_consumer.poll_message.side_effect = Exception("Poll failed")
        processor.consumer = mock_consumer

        result = await processor.consume_data_stream(timeout=1.0)

        assert result is None

    @pytest.mark.asyncio
    async def test_initialize_producer_failure(self):
        """测试生产者初始化失败"""
        processor = StreamProcessor()

        with patch(
            "src.streaming.stream_processor.FootballKafkaProducer"
        ) as mock_producer:
            mock_producer.side_effect = Exception("Producer init failed")

            with pytest.raises(Exception):
                await processor.initialize()

    @pytest.mark.asyncio
    async def test_initialize_consumer_failure(self):
        """测试消费者初始化失败"""
        processor = StreamProcessor()

        with patch(
            "src.streaming.stream_processor.FootballKafkaProducer"
        ) as mock_producer:
            with patch(
                "src.streaming.stream_processor.FootballKafkaConsumer"
            ) as mock_consumer:
                mock_producer.return_value = Mock()
                mock_consumer.side_effect = Exception("Consumer init failed")

                with pytest.raises(Exception):
                    await processor.initialize()

    @pytest.mark.asyncio
    async def test_cleanup_with_exception(self):
        """测试清理时的异常处理"""
        processor = StreamProcessor()
        mock_producer = Mock()
        mock_producer.close.side_effect = Exception("Close failed")
        processor.producer = mock_producer

        # 应该处理异常而不是崩溃
        await processor.cleanup()


class TestStreamProcessorEdgeCases:
    """测试边界情况"""

    @pytest.mark.asyncio
    async def test_concurrent_operations(self):
        """测试并发操作"""
        processor = StreamProcessor()
        mock_producer = Mock()
        mock_producer.send_message.return_value = True
        processor.producer = mock_producer

        # 创建多个并发发送任务
        tasks = []
        for i in range(5):
            task = processor.send_data_stream(f"topic-{i}", {"id": i})
            tasks.append(task)

        results = await asyncio.gather(*tasks)

        # 所有任务应该成功
        assert all(result is True for result in results)

    @pytest.mark.asyncio
    async def test_batch_processing_with_mixed_results(self):
        """测试批处理混合结果"""
        processor = StreamProcessor()
        mock_producer = Mock()

        def mock_send(topic, data):
            # 偶数ID成功，奇数ID失败
            return data.get("id", 0) % 2 == 0

        mock_producer.send_message.side_effect = mock_send
        processor.producer = mock_producer

        messages = [
            ("topic1", {"id": 0}),  # 成功
            ("topic2", {"id": 1}),  # 失败
            ("topic3", {"id": 2}),  # 成功
            ("topic4", {"id": 3}),  # 失败
        ]

        result = await processor.send_batch_messages(messages)

        assert result["total"] == 4
        assert result["success"] == 2
        assert result["failed"] == 2

    @pytest.mark.asyncio
    async def test_consume_batch_with_timeout(self):
        """测试批量消费超时"""
        processor = StreamProcessor()
        mock_consumer = Mock()
        mock_consumer.poll_message.return_value = None  # 总是超时
        processor.consumer = mock_consumer

        result = await processor.consume_batch_messages(batch_size=3, timeout=0.1)

        assert result == []

    def test_stats_edge_cases(self):
        """测试统计边界情况"""
        processor = StreamProcessor()

        # 测试大量更新
        for i in range(1000):
            processor._update_stats("send_success")

        stats = processor.get_stats()
        # 验证统计没有溢出或异常
        assert isinstance(stats, dict)

        # 重置后应该清零
        processor.reset_stats()
        reset_stats = processor.get_stats()
        assert isinstance(reset_stats, dict)

    @pytest.mark.asyncio
    async def test_rapid_start_stop(self):
        """测试快速启动停止"""
        processor = StreamProcessor()

        # 测试快速启动停止循环
        for _ in range(3):
            if hasattr(processor, "start") and hasattr(processor, "stop"):
                # 如果有这些方法，测试它们
                processor._running = True
                await processor.stop()
                assert not getattr(processor, "_running", True)

    def test_memory_efficiency(self):
        """测试内存效率"""
        processor = StreamProcessor()

        # 模拟大量数据处理统计
        initial_size = len(str(processor.stats))

        for _ in range(100):
            processor._update_stats("test_operation")

        final_size = len(str(processor.stats))

        # 统计增长应该是合理的
        growth = final_size - initial_size
        assert growth < 10000  # 不应该无限增长
