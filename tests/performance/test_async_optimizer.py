#!/usr/bin/env python3
"""
异步优化器测试
"""

import asyncio
from unittest.mock import AsyncMock, Mock

import pytest

try:
    from src.database.connection import DatabaseManager
    from src.performance.async_optimizer import (
        AsyncBatchProcessor,
        AsyncConnectionPool,
        AsyncFileOptimizer,
        AsyncQueryOptimizer,
        get_batch_processor,
        get_connection_pool,
        get_file_optimizer,
        get_query_optimizer,
    )
except ImportError as e:
    print(f"Warning: Could not import async optimizer modules: {e}")
    pytest.skip("异步优化器模块不可用", allow_module_level=True)


@pytest.mark.performance
@pytest.mark.asyncio
class TestAsyncConnectionPool:
    """异步连接池测试"""

    @pytest.fixture
    def mock_db_manager(self):
        """模拟数据库管理器"""
        manager = Mock(spec=DatabaseManager)
        manager.get_async_session = AsyncMock()
        return manager

    @pytest.fixture
    def connection_pool(self, mock_db_manager):
        """连接池实例"""
        return AsyncConnectionPool(mock_db_manager, min_size=2, max_size=5, timeout=5.0)

    async def test_connection_pool_stats(self, connection_pool):
        """测试连接池统计"""
        stats = connection_pool.get_pool_stats()

        assert "active_connections" in stats
        assert "pool_size" in stats
        assert "total_requests" in stats
        assert "utilization" in stats
        assert stats["active_connections"] == 0

    async def test_connection_pool_context_manager(
        self, connection_pool, mock_db_manager
    ):
        """测试连接池上下文管理"""
        mock_session = AsyncMock()
        mock_db_manager.get_async_session.return_value.__aenter__.return_value = (
            mock_session
        )

        async with connection_pool.get_connection() as session:
            assert session == mock_session

        # 验证连接计数正确
        stats = connection_pool.get_pool_stats()
        assert stats["active_connections"] == 0  # 退出上下文后应该为0


@pytest.mark.performance
@pytest.mark.asyncio
class TestAsyncBatchProcessor:
    """异步批量处理器测试"""

    @pytest.fixture
    def batch_processor(self):
        """批量处理器实例"""
        return AsyncBatchProcessor(batch_size=10, max_concurrent_batches=3)

    async def test_batch_processing(self, batch_processor):
        """测试批量处理功能"""
        # 测试数据
        test_data = list(range(50))  # 50个项目，批次大小10，应该有5个批次

        def process_batch(batch):
            """模拟批处理函数"""
            return [item * 2 for item in batch]

        # 执行批量处理
        results = await batch_processor.process_batch(test_data, process_batch)

        # 验证结果
        assert len(results) == 5  # 5个批次
        expected_data = [item * 2 for item in test_data]
        flattened_results = [item for batch in results for item in batch]
        assert flattened_results == expected_data

    async def test_batch_processing_with_progress(self, batch_processor):
        """测试带进度回调的批量处理"""
        test_data = list(range(30))
        progress_calls = []

        def progress_callback(current, total):
            progress_calls.append((current, total))

        def process_batch(batch):
            return [item for item in batch]

        await batch_processor.process_batch(test_data, process_batch, progress_callback)

        # 验证进度回调被调用
        assert len(progress_calls) == 3  # 30个数据，批次大小10，应该有3个批次
        assert progress_calls[0] == (1, 3)
        assert progress_calls[-1] == (3, 3)

    async def test_batch_processor_metrics(self, batch_processor):
        """测试批量处理器性能指标"""
        test_data = list(range(20))

        async def process_batch(batch):
            # 模拟一些处理时间
            await asyncio.sleep(0.01)
            return [item for item in batch]

        await batch_processor.process_batch(test_data, process_batch)

        # 验证性能指标
        metrics = batch_processor.metrics
        assert metrics.operation_count > 0
        assert metrics.total_time > 0
        assert metrics.avg_time > 0
        assert metrics.errors_count == 0


@pytest.mark.performance
@pytest.mark.asyncio
class TestAsyncQueryOptimizer:
    """异步查询优化器测试"""

    @pytest.fixture
    def mock_db_manager(self):
        """模拟数据库管理器"""
        manager = Mock(spec=DatabaseManager)
        mock_session = AsyncMock()
        mock_result = AsyncMock()
        mock_result.scalars.return_value.all.return_value = [{"id": 1}, {"id": 2}]
        mock_session.execute.return_value = mock_result
        manager.get_async_session.return_value.__aenter__.return_value = mock_session
        return manager

    @pytest.fixture
    def query_optimizer(self, mock_db_manager):
        """查询优化器实例"""
        return AsyncQueryOptimizer(mock_db_manager)

    async def test_query_execution(self, query_optimizer):
        """测试查询执行"""
        query = "SELECT * FROM test_table WHERE id = :id"
        params = {"id": 1}

        result = await query_optimizer.execute_optimized_query(query, params)

        # 验证查询被执行
        assert result == [{"id": 1}, {"id": 2}]

        # 验证性能指标
        assert query_optimizer.metrics.operation_count == 1
        assert query_optimizer.metrics.total_time > 0

    async def test_query_caching(self, query_optimizer):
        """测试查询缓存"""
        query = "SELECT COUNT(*) FROM test_table"

        # 第一次执行
        result1 = await query_optimizer.execute_optimized_query(query, use_cache=True)

        # 第二次执行（应该使用缓存）
        result2 = await query_optimizer.execute_optimized_query(query, use_cache=True)

        # 验证缓存被使用
        assert result1 == result2
        assert len(query_optimizer.query_cache) > 0

    async def test_batch_query_execution(self, query_optimizer):
        """测试批量查询执行"""
        queries = [
            {"query": "SELECT 1 as test", "params": None},
            {"query": "SELECT 2 as test", "params": None},
        ]

        results = await query_optimizer.execute_batch_queries(queries)

        # 验证结果
        assert len(results) == 2
        assert query_optimizer.metrics.operation_count >= 2

    def test_cache_stats(self, query_optimizer):
        """测试缓存统计"""
        stats = query_optimizer.get_cache_stats()

        assert "cache_size" in stats
        assert "operation_count" in stats
        assert "avg_query_time" in stats
        assert "error_rate" in stats


@pytest.mark.performance
@pytest.mark.asyncio
class TestAsyncFileOptimizer:
    """异步文件优化器测试"""

    @pytest.fixture
    def file_optimizer(self):
        """文件优化器实例"""
        return AsyncFileOptimizer(chunk_size=1024)

    async def test_file_processor_metrics(self, file_optimizer):
        """测试文件处理器性能指标"""
        stats = file_optimizer.get_performance_stats()

        assert "operation_count" in stats
        assert "avg_time" in stats
        assert "peak_time" in stats
        assert "error_count" in stats
        assert "error_rate" in stats


@pytest.mark.performance
class TestGlobalOptimizerInstances:
    """全局优化器实例测试"""

    def test_get_connection_pool(self):
        """测试获取全局连接池"""
        pool1 = get_connection_pool()
        pool2 = get_connection_pool()

        # 应该返回相同的实例
        assert pool1 is pool2

    def test_get_batch_processor(self):
        """测试获取全局批量处理器"""
        processor1 = get_batch_processor()
        processor2 = get_batch_processor()

        # 应该返回相同的实例
        assert processor1 is processor2

    def test_get_query_optimizer(self):
        """测试获取全局查询优化器"""
        optimizer1 = get_query_optimizer()
        optimizer2 = get_query_optimizer()

        # 应该返回相同的实例
        assert optimizer1 is optimizer2

    def test_get_file_optimizer(self):
        """测试获取全局文件优化器"""
        optimizer1 = get_file_optimizer()
        optimizer2 = get_file_optimizer()

        # 应该返回相同的实例
        assert optimizer1 is optimizer2


@pytest.mark.performance
@pytest.mark.asyncio
class TestAsyncOptimizerIntegration:
    """异步优化器集成测试"""

    async def test_optimized_workflow(self):
        """测试优化工作流程"""
        # 获取优化器实例
        batch_processor = get_batch_processor()
        query_optimizer = get_query_optimizer()

        # 模拟数据处理工作流
        test_data = list(range(100))

        def process_batch(batch):
            """处理数据批次"""
            return [{"value": item * 2} for item in batch]

        # 批量处理数据
        processed_data = await batch_processor.process_batch(test_data, process_batch)

        # 验证处理结果
        total_processed = sum(len(batch) for batch in processed_data)
        assert total_processed == len(test_data)

        # 验证性能指标
        assert batch_processor.metrics.operation_count > 0
        assert batch_processor.metrics.errors_count == 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
