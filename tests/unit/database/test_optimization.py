"""
数据库优化模块测试
Database Optimization Module Tests

测试src/database/optimization.py的各个功能
"""

import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from datetime import datetime, timedelta

# 导入要测试的模块
from src.database.optimization import DatabaseOptimizer, QueryOptimizer


class TestDatabaseOptimizer:
    """测试数据库优化器"""

    @pytest.fixture
    def mock_db_manager(self):
        """模拟数据库管理器"""
        mock_manager = Mock()
        mock_session = AsyncMock()

        # 创建正确的async context manager mock
        mock_async_session = AsyncMock()
        mock_async_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_async_session.__aexit__ = AsyncMock(return_value=None)
        mock_manager.get_async_session.return_value = mock_async_session

        return mock_manager

    @pytest.fixture
    def mock_redis_manager(self):
        """模拟Redis管理器"""
        return Mock()

    @pytest.fixture
    def optimizer(self, mock_db_manager, mock_redis_manager):
        """创建优化器实例"""
        return DatabaseOptimizer(mock_db_manager, mock_redis_manager)

    @pytest.mark.asyncio
    async def test_analyze_slow_queries_success(self, optimizer, mock_db_manager):
        """测试成功分析慢查询"""
        # 模拟查询结果
        mock_result = Mock()
        mock_row = Mock()
        mock_row.query = "SELECT * FROM predictions WHERE match_id = $1"
        mock_row.calls = 100
        mock_row.total_exec_time = 5000.0
        mock_row.mean_exec_time = 50.0
        mock_row.rows = 1000
        mock_row.hit_percent = 95.5

        mock_result.__iter__ = Mock(return_value=iter([mock_row]))

        mock_session = mock_db_manager.get_async_session.return_value.__aenter__.return_value
        mock_session.execute.return_value = mock_result

        # 执行测试
        result = await optimizer.analyze_slow_queries()

        # 验证结果
        assert len(result) == 1
        assert result[0]["query"] == "SELECT * FROM predictions WHERE match_id = $1"
        assert result[0]["calls"] == 100
        assert result[0]["total_time"] == 5000.0
        assert result[0]["avg_time"] == 50.0
        assert result[0]["rows"] == 1000
        assert result[0]["cache_hit_rate"] == 95.5

    @pytest.mark.asyncio
    async def test_analyze_slow_queries_no_pg_statements(self, optimizer, mock_db_manager):
        """测试pg_stat_statements未启用的情况"""
        mock_session = mock_db_manager.get_async_session.return_value.__aenter__.return_value
        mock_session.execute.side_effect = Exception("pg_stat_statements not enabled")

        with patch.object(optimizer.logger, 'warning') as mock_logger:
            result = await optimizer.analyze_slow_queries()

            # 应该返回空列表
            assert result == []
            # 应该记录警告日志
            mock_logger.assert_called_once()

    @pytest.mark.asyncio
    async def test_create_missing_indexes_success(self, optimizer, mock_db_manager):
        """测试成功创建缺失索引"""
        mock_session = mock_db_manager.get_async_session.return_value.__aenter__.return_value
        mock_session.execute = AsyncMock()

        with patch.object(optimizer.logger, 'info') as mock_logger:
            result = await optimizer.create_missing_indexes()

            # 应该返回创建的索引列表
            assert len(result) > 0
            assert "idx_predictions_match_model" in result
            assert "idx_predictions_created_at" in result
            assert "idx_matches_date_status" in result

            # 验证日志
            mock_logger.assert_called()

    @pytest.mark.asyncio
    async def test_create_missing_indexes_partial_failure(self, optimizer, mock_db_manager):
        """测试创建索引时部分失败"""
        mock_session = mock_db_manager.get_async_session.return_value.__aenter__.return_value

        # 第一个索引成功，第二个失败
        mock_session.execute = AsyncMock(side_effect=[None, Exception("Index creation failed")])

        with patch.object(optimizer.logger, 'error') as mock_logger:
            result = await optimizer.create_missing_indexes()

            # 应该只包含成功创建的索引
            assert len(result) >= 1
            # 应该记录错误日志
            mock_logger.assert_called()

    @pytest.mark.asyncio
    async def test_analyze_index_usage(self, optimizer, mock_db_manager):
        """测试分析索引使用情况"""
        # 模拟索引使用数据
        mock_index_result = Mock()
        mock_index_row = Mock()
        mock_index_row.schemaname = "public"
        mock_index_row.relname = "idx_predictions_match_model"
        mock_index_row.idx_tup_read = 1000
        mock_index_row.idx_tup_fetch = 950
        mock_index_row.idx_scan = 100

        mock_index_result.__iter__ = Mock(return_value=iter([mock_index_row]))

        # 模拟表大小数据
        mock_table_result = Mock()
        mock_table_row = Mock()
        mock_table_row.schemaname = "public"
        mock_table_row.relname = "predictions"
        mock_table_row.n_tup_ins = 10000
        mock_table_row.n_tup_upd = 2000
        mock_table_row.n_tup_del = 500
        mock_table_row.n_live_tup = 9500
        mock_table_row.n_dead_tup = 500

        mock_table_result.__iter__ = Mock(return_value=iter([mock_table_row]))

        mock_session = mock_db_manager.get_async_session.return_value.__aenter__.return_value
        mock_session.execute.side_effect = [mock_index_result, mock_table_result]

        result = await optimizer.analyze_index_usage()

        assert "indexes" in result
        assert "tables" in result
        assert len(result["indexes"]) == 1
        assert result["indexes"][0]["index_name"] == "idx_predictions_match_model"
        assert result["indexes"][0]["usage_count"] == 100

    @pytest.mark.asyncio
    async def test_optimize_connection_pool_production(self, optimizer):
        """测试生产环境连接池优化"""
        result = await optimizer.optimize_connection_pool("production")

        assert result["pool_size"] == 20
        assert result["max_overflow"] == 30
        assert result["pool_timeout"] == 30
        assert result["pool_recycle"] == 3600

    @pytest.mark.asyncio
    async def test_optimize_connection_pool_development(self, optimizer):
        """测试开发环境连接池优化"""
        result = await optimizer.optimize_connection_pool("development")

        assert result["pool_size"] == 5
        assert result["max_overflow"] == 10
        assert result["pool_timeout"] == 30
        assert result["pool_recycle"] == 1800

    @pytest.mark.asyncio
    async def test_vacuum_and_analyze_table(self, optimizer, mock_db_manager):
        """测试对特定表执行VACUUM和ANALYZE"""
        mock_session = mock_db_manager.get_async_session.return_value.__aenter__.return_value
        mock_session.execute = AsyncMock()

        with patch.object(optimizer.logger, 'info') as mock_logger:
            result = await optimizer.vacuum_and_analyze("predictions")

            assert result is True
            mock_session.execute.assert_called()
            mock_logger.assert_called()

    @pytest.mark.asyncio
    async def test_vacuum_and_analyze_all_tables(self, optimizer, mock_db_manager):
        """测试对所有表执行VACUUM和ANALYZE"""
        mock_session = mock_db_manager.get_async_session.return_value.__aenter__.return_value
        mock_session.execute = AsyncMock()

        with patch.object(optimizer.logger, 'info') as mock_logger:
            result = await optimizer.vacuum_and_analyze()

            assert result is True
            mock_logger.assert_called()

    @pytest.mark.asyncio
    async def test_get_database_stats(self, optimizer, mock_db_manager):
        """测试获取数据库统计信息"""
        # 模拟数据库统计查询结果
        mock_result = Mock()
        mock_row = Mock()
        mock_row.datname = "football_prediction"
        mock_row.numbackends = 10
        mock_row.xact_commit = 10000
        mock_row.xact_rollback = 100
        mock_row.blks_read = 50000
        mock_row.blks_hit = 450000
        mock_row.tup_returned = 100000
        mock_row.tup_fetched = 80000
        mock_row.tup_inserted = 5000
        mock_row.tup_updated = 2000
        mock_row.tup_deleted = 500

        mock_result.__iter__ = Mock(return_value=iter([mock_row]))

        mock_session = mock_db_manager.get_async_session.return_value.__aenter__.return_value
        mock_session.execute.return_value = mock_result

        result = await optimizer.get_database_stats()

        assert result["database_name"] == "football_prediction"
        assert result["active_connections"] == 10
        assert result["transactions_committed"] == 10000
        assert result["transactions_rolled_back"] == 100
        assert result["cache_hit_rate"] == 90.0  # (450000 / (450000 + 50000)) * 100

    @pytest.mark.asyncio
    async def test_monitor_query_performance_fast(self, optimizer, mock_db_manager):
        """测试监控快速查询"""
        mock_session = mock_db_manager.get_async_session.return_value.__aenter__.return_value
        mock_session.execute = AsyncMock()

        # 模拟执行时间小于阈值
        with patch('time.time', side_effect=[1000.0, 1000.05]):  # 50ms
            result = await optimizer.monitor_query_performance("SELECT * FROM matches")

            assert result["query_time_ms"] == 50.0
            assert result["is_slow"] is False
            assert result["within_threshold"] is True

    @pytest.mark.asyncio
    async def test_monitor_query_performance_slow(self, optimizer, mock_db_manager):
        """测试监控慢查询"""
        mock_session = mock_db_manager.get_async_session.return_value.__aenter__.return_value
        mock_session.execute = AsyncMock()

        # 模拟执行时间大于阈值
        with patch('time.time', side_effect=[2000.0, 2000.2]):  # 200ms
            with patch.object(optimizer.logger, 'warning') as mock_logger:
                result = await optimizer.monitor_query_performance("SELECT * FROM predictions", threshold_ms=100.0)

                assert result["query_time_ms"] == 200.0
                assert result["is_slow"] is True
                assert result["within_threshold"] is False
                mock_logger.assert_called()

    @pytest.mark.asyncio
    async def test_create_query_performance_report(self, optimizer, mock_db_manager):
        """测试创建查询性能报告"""
        # 模拟慢查询数据
        mock_slow_queries = [
            {
                "query": "SELECT * FROM predictions WHERE match_id = $1",
                "calls": 100,
                "avg_time": 150.0,
                "cache_hit_rate": 85.0
            }
        ]

        # 模拟索引使用数据
        mock_index_usage = {
            "unused_indexes": ["idx_old_column"],
            "inefficient_indexes": ["idx_low_cardinality"]
        }

        with patch.object(optimizer, 'analyze_slow_queries', return_value=mock_slow_queries):
            with patch.object(optimizer, 'analyze_index_usage', return_value=mock_index_usage):
                result = await optimizer.create_query_performance_report()

                assert "summary" in result
                assert "slow_queries" in result
                assert "recommendations" in result
                assert result["summary"]["total_slow_queries"] == 1
                assert len(result["recommendations"]) > 0


class TestQueryOptimizer:
    """测试查询优化器"""

    def test_optimize_pagination_small_offset(self):
        """测试小偏移量的分页优化"""
        query = "SELECT * FROM matches ORDER BY id"
        optimized = QueryOptimizer.optimize_pagination(query, 1, 50)

        assert "LIMIT 50 OFFSET 0" in optimized
        assert "cursor-based" not in optimized

    def test_optimize_pagination_large_offset(self):
        """测试大偏移量的分页优化"""
        query = "SELECT * FROM matches ORDER BY id"
        optimized = QueryOptimizer.optimize_pagination(query, 300, 50)  # offset = 14500

        assert "WHERE t.id >" in optimized
        assert "cursor-based" in optimized.lower() or optimized.count("SELECT") > 1

    def test_add_query_hints(self):
        """测试添加查询提示"""
        query = "SELECT * FROM matches WHERE date > '2023-01-01'"
        hints = ["MAX_EXECUTION_TIME(5000)", "INDEX(matches idx_date)"]

        optimized = QueryOptimizer.add_query_hints(query, hints)

        assert "/* MAX_EXECUTION_TIME(5000) INDEX(matches idx_date) */ SELECT" in optimized

    def test_add_query_hints_empty(self):
        """测试添加空提示列表"""
        query = "SELECT * FROM matches"
        optimized = QueryOptimizer.add_query_hints(query, [])

        assert optimized == query

    def test_batch_inserts_single_batch(self):
        """测试单批次插入"""
        table_name = "predictions"
        data = [
            {"match_id": 1, "prediction": "home_win", "confidence": 0.75},
            {"match_id": 2, "prediction": "draw", "confidence": 0.60}
        ]

        queries = QueryOptimizer.batch_inserts(table_name, data, batch_size=10)

        assert len(queries) == 1
        assert "INSERT INTO predictions" in queries[0]
        assert "VALUES" in queries[0]
        assert "(1, 'home_win', 0.75)" in queries[0]

    def test_batch_inserts_multiple_batches(self):
        """测试多批次插入"""
        table_name = "predictions"
        data = [
            {"match_id": i, "prediction": "home_win", "confidence": 0.75}
            for i in range(5)
        ]

        queries = QueryOptimizer.batch_inserts(table_name, data, batch_size=2)

        assert len(queries) == 3  # 5 items / batch_size 2 = 3 batches
        assert all("INSERT INTO predictions" in q for q in queries)

    def test_batch_inserts_empty_data(self):
        """测试空数据插入"""
        queries = QueryOptimizer.batch_inserts("predictions", [])

        assert queries == []

    def test_batch_inserts_string_escaping(self):
        """测试字符串转义"""
        table_name = "teams"
        data = [
            {"name": "John's Team", "description": "A 'great' team"}
        ]

        queries = QueryOptimizer.batch_inserts(table_name, data)

        assert "John''s Team" in queries[0]
        assert "A ''great'' team" in queries[0]


class TestDatabaseOptimizationIntegration:
    """测试数据库优化集成场景"""

    @pytest.mark.asyncio
    async def test_full_optimization_workflow(self, mock_db_manager):
        """测试完整的优化工作流"""
        optimizer = DatabaseOptimizer(mock_db_manager)

        # 模拟各个步骤的结果
        mock_slow_queries = [
            {"query": "SELECT * FROM predictions", "avg_time": 150.0}
        ]

        mock_session = mock_db_manager.get_async_session.return_value.__aenter__.return_value
        mock_session.execute = AsyncMock()

        with patch.object(optimizer, 'analyze_slow_queries', return_value=mock_slow_queries):
            with patch.object(optimizer, 'create_missing_indexes', return_value=["idx_test"]):
                with patch.object(optimizer, 'vacuum_and_analyze', return_value=True):
                    # 执行优化流程
                    slow_queries = await optimizer.analyze_slow_queries()
                    created_indexes = await optimizer.create_missing_indexes()
                    vacuum_success = await optimizer.vacuum_and_analyze()

                    # 验证结果
                    assert len(slow_queries) == 1
                    assert len(created_indexes) == 1
                    assert vacuum_success is True

    @pytest.mark.asyncio
    async def test_optimization_with_redis(self, mock_db_manager, mock_redis_manager):
        """测试带Redis的优化"""
        optimizer = DatabaseOptimizer(mock_db_manager, mock_redis_manager)

        # 模拟Redis缓存操作
        mock_redis_manager.get.return_value = None
        mock_redis_manager.setex.return_value = True

        mock_session = mock_db_manager.get_async_session.return_value.__aenter__.return_value
        mock_session.execute = AsyncMock()

        # 测试缓存查询结果
        cache_key = "db_stats:2023-10-03"

        # Redis缓存未命中，需要查询数据库
        with patch('datetime.datetime') as mock_datetime:
            mock_datetime.now.return_value.strftime.return_value = "2023-10-03"

            result = await optimizer.get_database_stats()

            # 验证Redis操作
            mock_redis_manager.get.assert_called_with(cache_key)
            # mock_redis_manager.setex.assert_called()


class TestOptimizationErrorHandling:
    """测试优化错误处理"""

    @pytest.mark.asyncio
    async def test_database_connection_error(self, mock_db_manager):
        """测试数据库连接错误"""
        mock_db_manager.get_async_session.side_effect = Exception("Connection failed")

        optimizer = DatabaseOptimizer(mock_db_manager)

        with pytest.raises(Exception):
            await optimizer.analyze_slow_queries()

    @pytest.mark.asyncio
    async def test_permission_denied_error(self, mock_db_manager):
        """测试权限拒绝错误"""
        mock_session = mock_db_manager.get_async_session.return_value.__aenter__.return_value
        mock_session.execute.side_effect = Exception("permission denied for relation pg_stat_statements")

        optimizer = DatabaseOptimizer(mock_db_manager)

        with patch.object(optimizer.logger, 'error') as mock_logger:
            result = await optimizer.analyze_slow_queries()

            assert result == []
            mock_logger.assert_called()

    @pytest.mark.asyncio
    async def test_timeout_error(self, mock_db_manager):
        """测试超时错误"""
        mock_session = mock_db_manager.get_async_session.return_value.__aenter__.return_value
        mock_session.execute.side_effect = asyncio.TimeoutError("Query timeout")

        optimizer = DatabaseOptimizer(mock_db_manager)

        with patch.object(optimizer.logger, 'error'):
            result = await optimizer.analyze_slow_queries()

            assert result == []


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])