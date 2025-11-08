#!/usr/bin/env python3
"""
数据库查询优化器测试
"""

from unittest.mock import AsyncMock, Mock

import pytest

try:
    from src.database.connection import DatabaseManager
    from src.performance.db_query_optimizer import (
        DatabaseOptimizer,
        QueryAnalyzer,
        QueryOptimizer,
        get_database_optimizer,
        get_query_optimizer,
    )
except ImportError as e:
    print(f"Warning: Could not import db query optimizer modules: {e}")
    pytest.skip("数据库查询优化器模块不可用", allow_module_level=True)


@pytest.mark.performance
class TestQueryAnalyzer:
    """查询分析器测试"""

    @pytest.fixture
    def query_analyzer(self):
        """查询分析器实例"""
        return QueryAnalyzer()

    def test_detect_simple_select(self, query_analyzer):
        """测试检测简单SELECT查询"""
        query = "SELECT * FROM users"
        result = query_analyzer._detect_query_type(query)
        assert result == "SELECT_SIMPLE"

    def test_detect_join_query(self, query_analyzer):
        """测试检测JOIN查询"""
        query = "SELECT u.*, p.* FROM users u JOIN profiles p ON u.id = p.user_id"
        result = query_analyzer._detect_query_type(query)
        assert result == "SELECT_JOIN"

    def test_detect_aggregate_query(self, query_analyzer):
        """测试检测聚合查询"""
        query = "SELECT COUNT(*), AVG(age) FROM users GROUP BY department"
        result = query_analyzer._detect_query_type(query)
        assert result == "SELECT_AGGREGATE"

    def test_detect_ordered_query(self, query_analyzer):
        """测试检测排序查询"""
        query = "SELECT * FROM users ORDER BY created_at DESC LIMIT 10"
        result = query_analyzer._detect_query_type(query)
        assert result == "SELECT_ORDERED"

    def test_estimate_complexity(self, query_analyzer):
        """测试复杂度估算"""
        # 低复杂度
        simple_query = "SELECT * FROM users WHERE id = 1"
        assert query_analyzer._estimate_complexity(simple_query) == "LOW"

        # 中等复杂度
        medium_query = "SELECT * FROM users u JOIN profiles p ON u.id = p.user_id WHERE u.active = true"
        assert query_analyzer._estimate_complexity(medium_query) == "MEDIUM"

        # 高复杂度
        complex_query = """
        SELECT u.*, p.*, o.*
        FROM users u
        JOIN profiles p ON u.id = p.user_id
        JOIN orders o ON u.id = o.user_id
        WHERE u.active = true
        GROUP BY u.id
        HAVING COUNT(o.id) > 5
        ORDER BY u.created_at DESC
        """
        assert query_analyzer._estimate_complexity(complex_query) == "HIGH"

    def test_analyze_query_comprehensive(self, query_analyzer):
        """测试综合查询分析"""
        query = """
        SELECT u.name, COUNT(o.id) as order_count
        FROM users u
        JOIN orders o ON u.id = o.user_id
        WHERE u.active = true AND o.status = 'completed'
        GROUP BY u.id, u.name
        HAVING COUNT(o.id) > 5
        ORDER BY order_count DESC
        LIMIT 10
        """
        analysis = query_analyzer.analyze_query(query)

        # 验证分析结果
        assert "query_type" in analysis
        assert "complexity" in analysis
        assert "slow_patterns" in analysis
        assert "optimization_opportunities" in analysis
        assert "suggested_indexes" in analysis
        assert "estimated_cost" in analysis

        assert analysis["query_type"] == "SELECT_AGGREGATE"
        assert analysis["complexity"] in ["LOW", "MEDIUM", "HIGH"]

    def test_suggest_indexes_for_where_clause(self, query_analyzer):
        """测试为WHERE子句建议索引"""
        query = (
            "SELECT * FROM users WHERE email = 'test@example.com' AND status = 'active'"
        )
        analysis = query_analyzer.analyze_query(query)

        # 应该建议为email和status字段建立索引
        suggested_indexes = analysis["suggested_indexes"]
        assert len(suggested_indexes) > 0

        email_index = next(
            (idx for idx in suggested_indexes if "email" in idx.column_names), None
        )
        assert email_index is not None
        assert email_index.priority == "high"
        assert email_index.index_type == "btree"

    def test_suggest_indexes_for_order_by(self, query_analyzer):
        """测试为ORDER BY建议索引"""
        query = "SELECT * FROM users ORDER BY created_at DESC LIMIT 10"
        analysis = query_analyzer.analyze_query(query)

        suggested_indexes = analysis["suggested_indexes"]
        order_by_index = next(
            (idx for idx in suggested_indexes if "created_at" in idx.column_names), None
        )
        assert order_by_index is not None
        assert order_by_index.priority == "medium"


@pytest.mark.performance
@pytest.mark.asyncio
class TestQueryOptimizer:
    """查询优化器测试"""

    @pytest.fixture
    def mock_db_manager(self):
        """模拟数据库管理器"""
        manager = Mock(spec=DatabaseManager)
        mock_session = AsyncMock()
        mock_result = AsyncMock()
        mock_result.scalars.return_value.all.return_value = [{"id": 1, "name": "test"}]
        mock_session.execute.return_value = mock_result
        manager.get_async_session.return_value.__aenter__.return_value = mock_session
        return manager

    @pytest.fixture
    def query_optimizer(self, mock_db_manager):
        """查询优化器实例"""
        return QueryOptimizer(mock_db_manager)

    async def test_query_hash_generation(self, query_optimizer):
        """测试查询哈希生成"""
        query1 = "SELECT * FROM users WHERE id = 1"
        query2 = "SELECT * FROM users WHERE id = 2"
        query3 = "SELECT * FROM users WHERE id = 1"

        hash1 = query_optimizer._generate_query_hash(query1)
        hash2 = query_optimizer._generate_query_hash(query2)
        hash3 = query_optimizer._generate_query_hash(query3)

        # 相同查询应该有相同哈希
        assert hash1 == hash3
        # 不同查询应该有不同哈希
        assert hash1 != hash2

    async def test_simple_query_execution(self, query_optimizer):
        """测试简单查询执行"""
        query = "SELECT * FROM users LIMIT 1"
        result = await query_optimizer.execute_optimized_query(query)

        assert result == [{"id": 1, "name": "test"}]

        # 验证性能指标被记录
        metrics = query_optimizer.query_metrics
        assert len(metrics) > 0

    async def test_parameterized_query_execution(self, query_optimizer):
        """测试参数化查询执行"""
        query = "SELECT * FROM users WHERE id = :id"
        params = {"id": 123}

        result = await query_optimizer.execute_optimized_query(query, params)

        assert result == [{"id": 1, "name": "test"}]

    async def test_batch_query_execution(self, query_optimizer):
        """测试批量查询执行"""
        queries = [
            {"query": "SELECT 1 as test", "params": None},
            {"query": "SELECT 2 as test", "params": None},
            {"query": "SELECT COUNT(*) FROM (SELECT 1) as subq", "params": None},
        ]

        results = await query_optimizer.execute_batch_with_optimization(queries)

        assert len(results) == 3

    async def test_slow_query_detection(self, query_optimizer):
        """测试慢查询检测"""
        # 降低慢查询阈值用于测试
        query_optimizer._slow_query_threshold = 0.001

        query = "SELECT * FROM users"
        result = await query_optimizer.execute_optimized_query(query)

        # 即使查询很快，也应该记录指标
        assert result is not None

    def test_performance_report_empty(self, query_optimizer):
        """测试空性能报告"""
        report = query_optimizer.get_performance_report()
        assert "message" in report

    def test_performance_report_with_metrics(self, query_optimizer):
        """测试带指标的性能报告"""
        # 手动添加一些指标
        from src.performance.db_query_optimizer import QueryPerformanceMetrics

        test_metric = QueryPerformanceMetrics(query_hash="test")
        test_metric.execution_count = 10
        test_metric.total_time = 2.5
        test_metric.avg_time = 0.25
        test_metric.min_time = 0.1
        test_metric.max_time = 0.5
        test_metric.error_count = 1

        query_optimizer.query_metrics["test"] = test_metric

        report = query_optimizer.get_performance_report()

        assert "summary" in report
        assert "slow_queries" in report
        assert "top_queries" in report
        assert "recommendations" in report

        assert report["summary"]["total_queries"] == 10
        assert report["summary"]["avg_query_time"] == 0.25
        assert report["summary"]["error_rate"] == 10.0  # 1/10 * 100

    def test_generate_recommendations(self, query_optimizer):
        """测试生成优化建议"""
        # 添加慢查询指标
        from src.performance.db_query_optimizer import QueryPerformanceMetrics

        slow_metric = QueryPerformanceMetrics(query_hash="slow")
        slow_metric.execution_count = 5
        slow_metric.total_time = 10.0  # 平均2秒，超过1秒阈值
        slow_metric.avg_time = 2.0

        # 添加高频查询指标
        high_freq_metric = QueryPerformanceMetrics(query_hash="high_freq")
        high_freq_metric.execution_count = 150  # 超过100次阈值

        query_optimizer.query_metrics["slow"] = slow_metric
        query_optimizer.query_metrics["high_freq"] = high_freq_metric

        recommendations = query_optimizer._generate_recommendations()

        assert len(recommendations) > 0
        assert any("慢查询" in rec for rec in recommendations)
        assert any("高频查询" in rec for rec in recommendations)


@pytest.mark.performance
@pytest.mark.asyncio
class TestDatabaseOptimizer:
    """数据库优化器测试"""

    @pytest.fixture
    def mock_db_manager(self):
        """模拟数据库管理器"""
        manager = Mock(spec=DatabaseManager)
        mock_session = AsyncMock()

        # 模拟表查询结果
        mock_tables_result = AsyncMock()
        mock_tables_result.fetchall.return_value = [("users",), ("orders",)]

        # 模拟统计查询结果
        mock_stats_result = AsyncMock()
        mock_stats_row = Mock()
        mock_stats_row._mapping = {
            "schemaname": "public",
            "tablename": "users",
            "inserts": 100,
            "updates": 50,
            "deletes": 10,
            "live_rows": 1000,
            "dead_rows": 100,
            "last_vacuum": None,
            "last_autovacuum": "2024-01-01",
            "last_analyze": "2024-01-01",
            "last_autoanalyze": None,
        }
        mock_stats_result.fetchone.return_value = mock_stats_row

        # 模拟索引查询结果
        mock_index_result = AsyncMock()
        mock_index_result.fetchall.return_value = [
            ("users_pkey", "CREATE UNIQUE INDEX users_pkey ON users (id)"),
            ("users_email_idx", "CREATE INDEX users_email_idx ON users (email)"),
        ]

        mock_session.execute.side_effect = [
            mock_tables_result,
            mock_stats_result,
            mock_index_result,
        ]

        manager.get_async_session.return_value.__aenter__.return_value = mock_session
        return manager

    @pytest.fixture
    def db_optimizer(self, mock_db_manager):
        """数据库优化器实例"""
        return DatabaseOptimizer(mock_db_manager)

    async def test_analyze_table_performance(self, db_optimizer):
        """测试表性能分析"""
        table_names = ["users", "orders"]
        analysis = await db_optimizer.analyze_table_performance(table_names)

        assert len(analysis) == 2
        assert "users" in analysis
        assert "orders" in analysis

        users_analysis = analysis["users"]
        assert "table_stats" in users_analysis
        assert "indexes" in users_analysis
        assert "recommendations" in users_analysis

    def test_generate_table_recommendations(self, db_optimizer):
        """测试表优化建议生成"""
        # 创建模拟统计信息
        mock_stats = Mock()
        mock_stats.n_live_tup = 1000
        mock_stats.n_dead_tup = 300  # 23%死行比例，超过20%阈值
        mock_stats.last_analyze = None
        mock_stats.last_autoanalyze = None

        indexes = [
            {"name": "index1", "definition": "CREATE INDEX idx1 ON users (col1)"},
            {"name": "index2", "definition": "CREATE INDEX idx2 ON users (col2)"},
            {"name": "index3", "definition": "CREATE INDEX idx3 ON users (col3)"},
            {"name": "index4", "definition": "CREATE INDEX idx4 ON users (col4)"},
            {"name": "index5", "definition": "CREATE INDEX idx5 ON users (col5)"},
            {"name": "index6", "definition": "CREATE INDEX idx6 ON users (col6)"},
            {"name": "index7", "definition": "CREATE INDEX idx7 ON users (col7)"},
            {"name": "index8", "definition": "CREATE INDEX idx8 ON users (col8)"},
            {"name": "index9", "definition": "CREATE INDEX idx9 ON users (col9)"},
            {"name": "index10", "definition": "CREATE INDEX idx10 ON users (col10)"},
            {"name": "index11", "definition": "CREATE INDEX idx11 ON users (col11)"},
        ]

        recommendations = db_optimizer._generate_table_recommendations(
            "users", mock_stats, indexes
        )

        # 应该建议VACUUM（死行比例高）
        assert any("VACUUM" in rec for rec in recommendations)
        # 应该建议索引过多
        assert any("索引数量过多" in rec for rec in recommendations)
        # 应该建议ANALYZE（从未分析）
        assert any("ANALYZE" in rec for rec in recommendations)

    async def test_generate_optimization_report(self, db_optimizer):
        """测试生成优化报告"""
        report = await db_optimizer.generate_optimization_report()

        assert "timestamp" in report
        assert "tables" in report
        assert "queries" in report
        assert "overall_recommendations" in report


@pytest.mark.performance
class TestGlobalOptimizerInstances:
    """全局优化器实例测试"""

    def test_get_query_optimizer(self):
        """测试获取全局查询优化器"""
        optimizer1 = get_query_optimizer()
        optimizer2 = get_query_optimizer()

        # 应该返回相同的实例
        assert optimizer1 is optimizer2

    def test_get_database_optimizer(self):
        """测试获取全局数据库优化器"""
        optimizer1 = get_database_optimizer()
        optimizer2 = get_database_optimizer()

        # 应该返回相同的实例
        assert optimizer1 is optimizer2


@pytest.mark.performance
@pytest.mark.asyncio
class TestQueryOptimizerIntegration:
    """查询优化器集成测试"""

    async def test_complete_optimization_workflow(self):
        """测试完整优化工作流程"""
        # 获取优化器实例
        query_optimizer = get_query_optimizer()
        db_optimizer = get_database_optimizer()

        # 测试查询分析
        analyzer = query_optimizer.analyzer
        test_query = "SELECT u.name, COUNT(o.id) FROM users u JOIN orders o ON u.id = o.user_id GROUP BY u.id"
        analysis = analyzer.analyze_query(test_query)

        assert analysis["query_type"] == "SELECT_AGGREGATE"
        assert analysis["complexity"] in ["MEDIUM", "HIGH"]

        # 测试性能报告生成
        report = query_optimizer.get_performance_report()
        assert "summary" in report

        # 测试建议生成
        if query_optimizer.query_metrics:
            recommendations = query_optimizer._generate_recommendations()
            assert isinstance(recommendations, list)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
