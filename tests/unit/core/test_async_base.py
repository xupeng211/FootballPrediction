"""
Async Base Class 测试
测试异步基础设施基类的功能

作者: Async架构负责人
创建时间: 2025-12-06
"""

import pytest
import asyncio
from unittest.mock import AsyncMock, patch
from datetime import datetime

from src.core.async_base import (
    AsyncConfig,
    RequestStats,
    AsyncBaseCollector,
    AsyncBaseService,
    AsyncBatchProcessor,
    create_async_collector,
)


class MockAsyncCollector(AsyncBaseCollector):
    """测试用的异步采集器"""

    async def _get_headers(self):
        return {"User-Agent": "test-agent"}

    async def _get_user_agent(self):
        return "test-agent"


class MockAsyncService(AsyncBaseService):
    """测试用的异步服务"""

    pass


class TestAsyncConfig:
    """测试异步配置类"""

    def test_default_config(self):
        """测试默认配置"""
        config = AsyncConfig()
        assert config.http_timeout == 30.0
        assert config.max_retries == 3
        assert config.retry_delay == 1.0
        assert config.max_connections == 100
        assert config.rate_limit_delay == 0.1
        assert config.enable_performance_monitoring is True

    def test_custom_config(self):
        """测试自定义配置"""
        config = AsyncConfig(http_timeout=60.0, max_retries=5, retry_delay=2.0)
        assert config.http_timeout == 60.0
        assert config.max_retries == 5
        assert config.retry_delay == 2.0


class TestRequestStats:
    """测试请求统计类"""

    def test_initial_stats(self):
        """测试初始统计信息"""
        stats = RequestStats()
        assert stats.total_requests == 0
        assert stats.successful_requests == 0
        assert stats.failed_requests == 0
        assert stats.success_rate == 0.0
        assert stats.average_response_time_ms == 0.0
        assert stats.last_request_time is None

    def test_success_rate_calculation(self):
        """测试成功率计算"""
        stats = RequestStats()

        # 无请求时成功率为0
        assert stats.success_rate == 0.0

        # 添加请求统计
        stats.total_requests = 10
        stats.successful_requests = 8
        assert stats.success_rate == 80.0

    def test_average_response_time(self):
        """测试平均响应时间计算"""
        stats = RequestStats()

        # 无请求时平均时间为0
        assert stats.average_response_time_ms == 0.0

        # 添加响应时间统计
        stats.total_requests = 2
        stats.total_response_time_ms = 300.0
        assert stats.average_response_time_ms == 150.0


@pytest.mark.asyncio
class TestAsyncBaseCollector:
    """测试异步采集器基类"""

    async def test_collector_initialization(self):
        """测试采集器初始化"""
        collector = MockAsyncCollector()
        assert collector.name == "MockAsyncCollector"
        assert collector.session is None
        assert collector._is_initialized is False

    async def test_context_manager(self):
        """测试上下文管理器"""
        collector = MockAsyncCollector()

        async with collector as c:
            assert c is collector
            assert c._is_initialized is True
            assert c.session is not None
            assert c.session.is_closed is False

        assert collector.session.is_closed is True

    async def test_fetch_method(self):
        """测试HTTP请求方法"""
        collector = MockAsyncCollector()

        # 模拟HTTP响应
        mock_response = AsyncMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"status": "ok"}

        with patch("httpx.AsyncClient.request", return_value=mock_response):
            async with collector:
                response = await collector.fetch("https://example.com")
                assert response.status_code == 200
                assert collector.stats.total_requests == 1
                assert collector.stats.successful_requests == 1

    async def test_fetch_with_retry(self):
        """测试带重试的HTTP请求"""
        collector = MockAsyncCollector()
        collector.config.max_retries = 2

        # 第一次失败，第二次成功
        mock_response_success = AsyncMock()
        mock_response_success.status_code = 200

        with patch("httpx.AsyncClient.request") as mock_request:
            mock_request.side_effect = [
                Exception("Network error"),
                mock_response_success,
            ]

            async with collector:
                response = await collector.fetch_with_retry("https://example.com")
                assert response.status_code == 200
                assert mock_request.call_count == 2

    async def test_fetch_json(self):
        """测试JSON获取方法"""
        collector = MockAsyncCollector()

        mock_response = AsyncMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"key": "value"}

        with patch("httpx.AsyncClient.request", return_value=mock_response):
            async with collector:
                data = await collector.fetch_json("https://example.com")
                assert data == {"key": "value"}

    async def test_get_stats(self):
        """测试统计信息获取"""
        collector = MockAsyncCollector()

        # 模拟一些请求统计
        collector.stats.total_requests = 10
        collector.stats.successful_requests = 8
        collector.stats.total_response_time_ms = 1000.0
        collector.stats.last_request_time = datetime.now()

        stats = collector.get_stats()
        assert stats["name"] == "MockAsyncCollector"
        assert stats["total_requests"] == 10
        assert stats["successful_requests"] == 8
        assert stats["success_rate"] == 80.0
        assert stats["average_response_time_ms"] == 100.0
        assert "last_request_time" in stats

    def test_reset_stats(self):
        """测试统计信息重置"""
        collector = MockAsyncCollector()

        # 设置一些统计信息
        collector.stats.total_requests = 10

        # 重置统计信息
        collector.reset_stats()

        # 验证重置结果
        assert collector.stats.total_requests == 0


@pytest.mark.asyncio
class TestAsyncBaseService:
    """测试异步服务基类"""

    async def test_service_initialization(self):
        """测试服务初始化"""
        service = MockAsyncService()
        assert service.name == "MockAsyncService"
        assert service.logger is not None

    async def test_get_db_session_context_manager(self):
        """测试数据库会话上下文管理器"""
        service = MockAsyncService()

        mock_session = AsyncMock()

        with patch("src.core.async_base.get_db_session") as mock_get_session:
            mock_get_session.return_value.__aenter__.return_value = mock_session
            mock_get_session.return_value.__aexit__.return_value = None

            async with service.get_db_session() as session:
                assert session is mock_session

            mock_get_session.assert_called_once()

    async def test_log_performance(self):
        """测试性能日志记录"""
        service = MockAsyncService()

        with patch.object(service.logger, "info") as mock_info:
            await service.log_performance("test_operation", 150.5)
            mock_info.assert_called_with(
                "Performance: test_operation completed in 150.50ms"
            )


@pytest.mark.asyncio
class TestAsyncBatchProcessor:
    """测试异步批处理器"""

    async def test_batch_processing(self):
        """测试批量处理"""
        processor = AsyncBatchProcessor(batch_size=2, name="TestProcessor")

        # 模拟处理函数
        async def mock_process_func(item):
            await asyncio.sleep(0.01)  # 模拟处理时间
            return item * 2

        # 测试数据
        items = [1, 2, 3, 4, 5]

        results = await processor.process_batch(
            items, mock_process_func, max_concurrent=3
        )

        assert results == [2, 4, 6, 8, 10]

    async def test_batch_processing_with_exceptions(self):
        """测试批量处理中的异常处理"""
        processor = AsyncBatchProcessor(batch_size=2, name="TestProcessor")

        # 模拟处理函数，包含异常
        async def mock_process_func(item):
            if item == 3:
                raise ValueError("Test error")
            return item * 2

        items = [1, 2, 3, 4]

        with patch.object(processor.logger, "error") as mock_error:
            results = await processor.process_batch(
                items, mock_process_func, max_concurrent=2
            )

            # 验证成功的项目被处理
            assert results == [2, 4, 8]  # 失败的项目(3)被跳过

            # 验证错误被记录
            mock_error.assert_called()

    def test_processor_initialization(self):
        """测试处理器初始化"""
        processor = AsyncBatchProcessor(batch_size=5, name="CustomProcessor")
        assert processor.batch_size == 5
        assert processor.name == "CustomProcessor"


@pytest.mark.asyncio
class TestUtilityFunctions:
    """测试工具函数"""

    async def test_create_async_collector(self):
        """测试创建异步采集器"""
        collector = await create_async_collector(MockAsyncCollector)

        try:
            assert isinstance(collector, MockAsyncCollector)
            assert collector._is_initialized is True
            assert collector.session is not None
        finally:
            await collector._cleanup()


class TestEdgeCases:
    """测试边界情况"""

    def test_collector_not_initialized_error(self):
        """测试未初始化采集器的错误处理"""
        collector = MockAsyncCollector()

        with pytest.raises(RuntimeError, match="Async collector not initialized"):
            asyncio.run(collector.fetch("https://example.com"))

    @pytest.mark.asyncio
    async def test_rate_limiting(self):
        """测试速率限制功能"""
        collector = MockAsyncCollector()
        collector.config.rate_limit_delay = 0.01  # 10ms延迟

        with patch("asyncio.sleep", new_callable=AsyncMock) as mock_sleep:
            async with collector:
                # 第一次调用应该应用速率限制
                await collector._apply_rate_limit()
                mock_sleep.assert_called_once_with(0.01)

    @pytest.mark.asyncio
    async def test_session_recreation(self):
        """测试会话重新创建"""
        collector = MockAsyncCollector()

        async with collector as c:
            first_session = c.session
            await c._ensure_session()  # 重新创建会话
            second_session = c.session

            # 应该使用相同的会话（未关闭）
            assert first_session is second_session

        # 关闭后重新创建
        await collector._ensure_session()
        assert collector.session is not None
        await collector._cleanup()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
