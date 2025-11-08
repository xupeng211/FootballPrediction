#!/usr/bin/env python3
"""
性能服务测试
"""

from unittest.mock import AsyncMock, Mock, patch

import pytest

try:
    from src.database.connection import DatabaseManager
    from src.services.performance_service import (
        PerformanceReport,
        PerformanceService,
        get_performance_service,
        initialize_performance_service,
    )
except ImportError as e:
    print(f"Warning: Could not import performance service modules: {e}")
    pytest.skip("性能服务模块不可用", allow_module_level=True)


@pytest.mark.performance
@pytest.mark.asyncio
class TestPerformanceService:
    """性能服务测试"""

    @pytest.fixture
    def mock_db_manager(self):
        """模拟数据库管理器"""
        manager = Mock(spec=DatabaseManager)
        manager.initialized = False
        return manager

    @pytest.fixture
    def performance_service(self, mock_db_manager):
        """性能服务实例"""
        return PerformanceService(mock_db_manager)

    async def test_service_initialization(self, performance_service, mock_db_manager):
        """测试服务初始化"""
        await performance_service.initialize()

        # 验证数据库管理器被初始化
        assert mock_db_manager.initialize.called

    async def test_optimize_database_queries(self, performance_service):
        """测试数据库查询优化"""
        queries = [
            {"query": "SELECT 1 as test", "params": None},
            {"query": "SELECT 2 as test", "params": None},
        ]

        # 模拟查询优化器
        performance_service.query_optimizer.execute_batch_with_optimization = AsyncMock(
            return_value=[{"result": 1}, {"result": 2}]
        )

        results = await performance_service.optimize_database_queries(queries)

        assert len(results) == 2
        performance_service.query_optimizer.execute_batch_with_optimization.assert_called_once_with(
            queries, max_concurrent=10
        )

    async def test_analyze_database_performance(self, performance_service):
        """测试数据库性能分析"""
        # 模拟数据库优化器
        mock_analysis = {
            "users": {
                "table_stats": {"inserts": 100, "updates": 50},
                "indexes": [],
                "recommendations": [],
            }
        }
        mock_query_report = {
            "summary": {"total_queries": 10, "avg_query_time": 0.5},
            "slow_queries_count": 2,
        }

        performance_service.db_optimizer.analyze_table_performance = AsyncMock(
            return_value=mock_analysis
        )
        performance_service.query_optimizer.get_performance_report = Mock(
            return_value=mock_query_report
        )

        result = await performance_service.analyze_database_performance(["users"])

        assert "tables" in result
        assert "queries" in result
        assert "timestamp" in result
        assert result["tables"] == mock_analysis
        assert result["queries"] == mock_query_report

    async def test_optimize_batch_processing(self, performance_service):
        """测试批量处理优化"""
        test_data = list(range(100))

        async def mock_processor(batch):
            return [item * 2 for item in batch]

        # 模拟批量处理器
        performance_service.batch_processor.process_batch = AsyncMock(
            return_value=[[0, 2, 4], [6, 8, 10]]
        )

        results = await performance_service.optimize_batch_processing(
            test_data, mock_processor, batch_size=50
        )

        assert results == [[0, 2, 4], [6, 8, 10]]
        performance_service.batch_processor.process_batch.assert_called_once()

    async def test_optimize_file_operations(self, performance_service):
        """测试文件操作优化"""
        # 模拟文件操作
        with patch("aiofiles.os.stat") as mock_stat:
            mock_stat.return_value.st_size = 1024

            result = await performance_service.optimize_file_operations(
                "/test/file.txt", "read"
            )

            assert result["file_size"] == 1024
            assert result["optimized"] is True

    def test_get_connection_pool_status(self, performance_service):
        """测试连接池状态获取"""
        # 模拟连接池统计
        performance_service.connection_pool.get_pool_stats = Mock(
            return_value={"active_connections": 3, "utilization": 0.6}
        )

        status = performance_service.get_connection_pool_status()

        assert "pool_stats" in status
        assert "baseline" in status
        assert "status" in status
        assert status["status"] == "healthy"

    def test_is_pool_healthy(self, performance_service):
        """测试连接池健康检查"""
        # 健康状态
        performance_service.connection_pool.get_pool_stats = Mock(
            return_value={"utilization": 0.7}
        )
        assert performance_service._is_pool_healthy() is True

        # 不健康状态
        performance_service.connection_pool.get_pool_stats = Mock(
            return_value={"utilization": 0.9}
        )
        assert performance_service._is_pool_healthy() is False

    async def test_generate_performance_report(self, performance_service):
        """测试生成性能报告"""
        # 模拟所有组件的性能数据
        performance_service.analyze_database_performance = AsyncMock(
            return_value={"tables": {}, "queries": {}}
        )
        performance_service.query_optimizer.get_performance_report = Mock(
            return_value={"summary": {"avg_query_time": 0.3, "error_rate": 1}}
        )
        performance_service.batch_processor.metrics = Mock(
            __dict__={"operation_count": 10, "avg_time": 0.2, "errors_count": 0}
        )
        performance_service.file_optimizer.get_performance_stats = Mock(
            return_value={"operation_count": 5, "error_rate": 0}
        )
        performance_service.connection_pool.get_pool_stats = Mock(
            return_value={"utilization": 0.6}
        )

        report = await performance_service.generate_performance_report()

        assert isinstance(report, PerformanceReport)
        assert report.timestamp > 0
        assert "database_metrics" in report.__dict__
        assert "async_metrics" in report.__dict__
        assert "query_metrics" in report.__dict__
        assert "connection_pool_metrics" in report.__dict__
        assert "recommendations" in report.__dict__
        assert "overall_score" in report.__dict__

        # 验证性能分数在合理范围内
        assert 0 <= report.overall_score <= 100

    async def test_generate_recommendations(self, performance_service):
        """测试生成优化建议"""
        # 测试慢查询场景
        db_metrics = {
            "queries": {"summary": {"error_rate": 0}, "slow_queries_count": 5}
        }
        async_metrics = {"batch_processor": {"avg_time": 0.5}}
        query_metrics = {"summary": {"error_rate": 0}}
        pool_metrics = {"status": "healthy"}

        recommendations = await performance_service._generate_recommendations(
            db_metrics, async_metrics, query_metrics, pool_metrics
        )

        assert isinstance(recommendations, list)
        assert any("慢查询" in rec for rec in recommendations)

        # 测试健康场景
        db_metrics = {
            "queries": {"summary": {"error_rate": 0}, "slow_queries_count": 0}
        }

        recommendations = await performance_service._generate_recommendations(
            db_metrics, async_metrics, query_metrics, pool_metrics
        )

        assert any("性能指标良好" in rec for rec in recommendations)

    def test_calculate_performance_score(self, performance_service):
        """测试性能分数计算"""
        # 理想情况
        db_metrics = {"queries": {"summary": {"avg_query_time": 0.3, "error_rate": 0}}}
        async_metrics = {"batch_processor": {"errors_count": 0, "operation_count": 10}}
        query_metrics = {"summary": {"error_rate": 0}}
        pool_metrics = {"pool_stats": {"utilization": 0.7}}

        score = performance_service._calculate_performance_score(
            db_metrics, async_metrics, query_metrics, pool_metrics
        )

        assert 0 <= score <= 100
        assert score > 80  # 理想情况应该有较高分数

        # 不理想情况
        db_metrics = {"queries": {"summary": {"avg_query_time": 2.0, "error_rate": 10}}}
        async_metrics = {"batch_processor": {"errors_count": 5, "operation_count": 10}}
        pool_metrics = {"pool_stats": {"utilization": 0.9}}

        score = performance_service._calculate_performance_score(
            db_metrics, async_metrics, query_metrics, pool_metrics
        )

        assert 0 <= score <= 100
        assert score < 70  # 不理想情况应该有较低分数

    async def test_auto_tune_performance(self, performance_service):
        """测试自动性能调优"""
        # 模拟性能报告
        mock_report = Mock()
        mock_report.overall_score = 75.0
        mock_report.recommendations = [
            "发现 2 个慢查询，建议添加索引或优化SQL",
            "连接池利用率过高，建议增加连接池大小",
        ]

        performance_service.generate_performance_report = AsyncMock(
            return_value=mock_report
        )

        result = await performance_service.auto_tune_performance()

        assert "actions_performed" in result
        assert "performance_score_before" in result
        assert "recommendations_applied" in result
        assert result["performance_score_before"] == 75.0

        # 验证调优操作被执行
        actions = result["actions_performed"]
        assert len(actions) > 0

    async def test_benchmark_performance(self, performance_service):
        """测试性能基准测试"""
        # 模拟查询执行
        performance_service.query_optimizer.execute_optimized_query = AsyncMock(
            return_value=[{"test": 1}]
        )

        # 运行短时间基准测试
        results = await performance_service.benchmark_performance(duration_seconds=2)

        assert "duration" in results
        assert "queries_per_second" in results
        assert "avg_response_time" in results
        assert "error_rate" in results
        assert "total_queries" in results
        assert "total_errors" in results

        assert results["duration"] >= 2.0
        assert results["queries_per_second"] > 0
        assert results["avg_response_time"] >= 0
        assert 0 <= results["error_rate"] <= 1

    async def test_cleanup(self, performance_service):
        """测试清理功能"""
        # 模拟清理操作
        performance_service.query_optimizer.clear_cache = Mock()
        performance_service.batch_processor.metrics = Mock()
        performance_service.batch_processor.metrics = type("MockMetrics", (), {})()

        await performance_service.cleanup()

        # 验证清理操作被调用
        performance_service.query_optimizer.clear_cache.assert_called_once()


@pytest.mark.performance
class TestGlobalPerformanceService:
    """全局性能服务测试"""

    def test_get_performance_service(self):
        """测试获取全局性能服务实例"""
        service1 = get_performance_service()
        service2 = get_performance_service()

        # 应该返回相同的实例
        assert service1 is service2

    @pytest.mark.asyncio
    async def test_initialize_performance_service(self):
        """测试初始化全局性能服务"""
        with patch(
            "src.services.performance_service.get_performance_service"
        ) as mock_get_service:
            mock_service = Mock()
            mock_service.initialize = AsyncMock()
            mock_get_service.return_value = mock_service

            service = await initialize_performance_service()

            assert service == mock_service
            mock_service.initialize.assert_called_once()


@pytest.mark.performance
@pytest.mark.asyncio
class TestPerformanceServiceIntegration:
    """性能服务集成测试"""

    async def test_complete_performance_workflow(self):
        """测试完整性能管理工作流程"""
        service = get_performance_service()

        # 模拟初始化
        with patch.object(service.db_manager, "initialize"):
            await service.initialize()

        # 模拟性能分析
        service.analyze_database_performance = AsyncMock(
            return_value={"tables": {}, "queries": {}}
        )
        service.query_optimizer.get_performance_report = Mock(
            return_value={"summary": {"avg_query_time": 0.3}}
        )
        service.batch_processor.metrics = Mock(
            __dict__={"operation_count": 5, "avg_time": 0.2, "errors_count": 0}
        )
        service.file_optimizer.get_performance_stats = Mock(
            return_value={"operation_count": 3, "error_rate": 0}
        )
        service.connection_pool.get_pool_stats = Mock(return_value={"utilization": 0.6})

        # 生成性能报告
        report = await service.generate_performance_report()

        assert isinstance(report, PerformanceReport)
        assert report.overall_score > 0

        # 模拟基准测试
        service.query_optimizer.execute_optimized_query = AsyncMock(
            return_value=[{"test": 1}]
        )

        benchmark_results = await service.benchmark_performance(duration_seconds=1)

        assert benchmark_results["total_queries"] > 0
        assert benchmark_results["duration"] >= 1.0

        # 清理
        await service.cleanup()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
