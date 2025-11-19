from typing import Optional

"""
数据库优化功能测试
Database Optimization Tests
"""

import asyncio
from unittest.mock import MagicMock

import pytest

from src.api.optimization.connection_pool_optimizer import (
    ConnectionPoolOptimizer,
    PoolMetrics,
    PoolOptimizationConfig,
)
from src.api.optimization.database_performance_middleware import (
    DatabasePerformanceMiddleware,
    QueryOptimizationAdvisor,
    get_database_middleware,
    get_optimization_advisor,
)
from src.api.optimization.database_query_optimizer import (
    DatabasePerformanceAnalyzer,
    QueryMetrics,
    get_database_analyzer,
)
from src.api.optimization.query_execution_analyzer import (
    ExecutionPlanNode,
    QueryExecutionAnalyzer,
)


class TestDatabasePerformanceAnalyzer:
    """数据库性能分析器测试"""

    def test_analyzer_initialization(self):
        """测试分析器初始化"""
        analyzer = DatabasePerformanceAnalyzer(max_query_history=500)

        assert analyzer.max_query_history == 500
        assert len(analyzer.query_metrics) == 0
        assert len(analyzer.slow_queries) == 0
        assert analyzer.analysis_start_time is not None

    def test_query_hash_generation(self):
        """测试查询哈希生成"""
        analyzer = DatabasePerformanceAnalyzer()

        query1 = "SELECT * FROM users WHERE id = 1"
        query2 = "select * from users where id = 1"  # 不同大小写
        query3 = "SELECT * FROM users WHERE id = 2"  # 不同参数

        hash1 = analyzer.generate_query_hash(query1)
        hash2 = analyzer.generate_query_hash(query2)
        hash3 = analyzer.generate_query_hash(query3)

        # 标准化的查询应该生成相同的哈希
        assert hash1 == hash2
        # 不同的查询应该生成不同的哈希
        assert hash1 != hash3

    @pytest.mark.asyncio
    async def test_query_analysis(self):
        """测试查询分析"""
        analyzer = DatabasePerformanceAnalyzer()

        query = "SELECT * FROM users WHERE active = true"
        execution_time = 0.5
        rows_returned = 10
        rows_examined = 50

        query_hash = await analyzer.analyze_query(
            query,
            execution_time,
            rows_returned=rows_returned,
            rows_examined=rows_examined,
        )

        # 验证查询指标被正确记录
        assert query_hash in analyzer.query_metrics
        metrics = analyzer.query_metrics[query_hash]
        assert metrics.query_text == query
        assert metrics.execution_count == 1
        assert metrics.total_time == execution_time
        assert metrics.rows_returned == rows_returned
        assert metrics.rows_examined == rows_examined

    @pytest.mark.asyncio
    async def test_slow_query_detection(self):
        """测试慢查询检测"""
        analyzer = DatabasePerformanceAnalyzer()

        # 模拟慢查询
        slow_query = "SELECT * FROM large_table WHERE complex_condition"
        await analyzer.analyze_query(slow_query, 2.5)  # 超过1秒阈值

        # 验证慢查询被记录
        assert len(analyzer.slow_queries) == 1
        assert analyzer.slow_queries[0]["query_text"] == slow_query
        assert analyzer.slow_queries[0]["execution_time"] == 2.5

    @pytest.mark.asyncio
    async def test_error_rate_calculation(self):
        """测试错误率计算"""
        analyzer = DatabasePerformanceAnalyzer()

        query = "SELECT * FROM test_table"

        # 记录多次执行，包括错误
        await analyzer.analyze_query(query, 0.1, error=False)
        await analyzer.analyze_query(query, 0.1, error=False)
        await analyzer.analyze_query(query, 0.1, error=True)  # 1次错误

        metrics = analyzer.query_metrics[analyzer.generate_query_hash(query)]
        error_rate = metrics.get_error_rate()

        assert error_rate == 33.33333333333333  # 1/3 * 100

    def test_performance_summary(self):
        """测试性能摘要"""
        analyzer = DatabasePerformanceAnalyzer()

        # 添加一些模拟数据
        for i in range(3):
            query_hash = f"query_{i}"
            analyzer.query_metrics[query_hash] = QueryMetrics(query_hash, f"Query {i}")
            analyzer.query_metrics[query_hash].execution_count = 10
            analyzer.query_metrics[query_hash].total_time = 1.0
            analyzer.query_metrics[query_hash].error_count = 1

        summary = analyzer.get_performance_summary()

        assert summary["total_queries"] == 30  # 3 queries * 10 executions
        assert summary["unique_queries"] == 3
        assert summary["avg_response_time"] == 0.1  # 3.0 total time / 30 executions
        assert summary["total_errors"] == 3

    @pytest.mark.asyncio
    async def test_optimization_suggestions(self):
        """测试优化建议生成"""
        analyzer = DatabasePerformanceAnalyzer()

        # 添加慢查询
        await analyzer.analyze_query("SELECT * FROM large_table", 2.0)

        # 添加高错误率查询
        error_query_hash = analyzer.generate_query_hash("SELECT * FROM error_table")
        analyzer.query_metrics[error_query_hash] = QueryMetrics(
            error_query_hash, "Error query"
        )
        for i in range(10):
            analyzer.query_metrics[error_query_hash].record_execution(
                0.1,
                error=(i % 2 == 0),  # 50%错误率
            )

        suggestions = await analyzer.get_optimization_suggestions()

        # 应该有慢查询建议
        slow_query_suggestions = [s for s in suggestions if s["type"] == "slow_query"]
        assert len(slow_query_suggestions) > 0

        # 应该有高错误率建议
        error_suggestions = [s for s in suggestions if s["type"] == "high_error_rate"]
        assert len(error_suggestions) > 0


class TestQueryMetrics:
    """查询指标测试"""

    def test_metrics_initialization(self):
        """测试指标初始化"""
        metrics = QueryMetrics("test_hash", "SELECT * FROM test")

        assert metrics.query_hash == "test_hash"
        assert metrics.query_text == "SELECT * FROM test"
        assert metrics.execution_count == 0
        assert metrics.total_time == 0.0
        assert metrics.error_count == 0

    def test_execution_recording(self):
        """测试执行记录"""
        metrics = QueryMetrics("test_hash", "SELECT * FROM test")

        # 记录多次执行
        metrics.record_execution(0.1, 10, 50, False)
        metrics.record_execution(0.2, 20, 100, False)
        metrics.record_execution(0.15, 15, 75, True)  # 错误执行

        assert metrics.execution_count == 3
        assert metrics.total_time == 0.45  # 0.1 + 0.2 + 0.15
        assert metrics.avg_time == 0.15  # 0.45 / 3
        assert metrics.min_time == 0.1
        assert metrics.max_time == 0.2
        assert metrics.error_count == 1
        assert metrics.rows_returned == 45  # 10 + 20 + 15
        assert metrics.rows_examined == 225  # 50 + 100 + 75

    def test_percentile_calculations(self):
        """测试百分位数计算"""
        metrics = QueryMetrics("test_hash", "SELECT * FROM test")

        # 添加一些执行时间
        execution_times = [0.1, 0.2, 0.15, 0.25, 0.3, 0.05, 0.18]
        for time_val in execution_times:
            metrics.record_execution(time_val)

        # 检查P50 (中位数)
        p50 = metrics.get_p50()
        sorted_times = sorted(execution_times)
        expected_p50 = sorted_times[len(sorted_times) // 2]
        assert p50 == expected_p50

        # 检查P95和P99
        p95 = metrics.get_p95()
        p99 = metrics.get_p99()
        assert p95 >= p50
        assert p99 >= p95


class TestDatabasePerformanceMiddleware:
    """数据库性能中间件测试"""

    def test_middleware_initialization(self):
        """测试中间件初始化"""
        middleware = DatabasePerformanceMiddleware(
            enable_query_tracking=True, slow_query_threshold=2.0
        )

        assert middleware.enable_query_tracking is True
        assert middleware.slow_query_threshold == 2.0
        assert middleware.db_analyzer is not None
        assert middleware.is_monitoring is False

    @pytest.mark.asyncio
    async def test_start_stop_monitoring(self):
        """测试监控启动和停止"""
        middleware = DatabasePerformanceMiddleware()

        # 启动监控
        await middleware.start_monitoring()
        assert middleware.is_monitoring is True

        # 停止监控
        middleware.stop_monitoring()
        assert middleware.is_monitoring is False

    @pytest.mark.asyncio
    async def test_real_time_metrics(self):
        """测试实时指标获取"""
        middleware = DatabasePerformanceMiddleware()

        # 未启用监控时的状态
        metrics = await middleware.get_real_time_metrics()
        assert metrics["status"] == "monitoring_disabled"

        # 启用监控后的状态
        await middleware.start_monitoring()
        metrics = await middleware.get_real_time_metrics()
        assert metrics["status"] == "active"
        assert metrics["monitoring_enabled"] is True

        middleware.stop_monitoring()

    @pytest.mark.asyncio
    async def test_current_performance_analysis(self):
        """测试当前性能分析"""
        middleware = DatabasePerformanceMiddleware()

        # 启用监控
        await middleware.start_monitoring()

        # 获取性能分析
        analysis = await middleware.analyze_current_performance()

        assert "top_slow_queries" in analysis
        assert "most_frequent_queries" in analysis
        assert "high_error_rate_queries" in analysis
        assert "optimization_suggestions" in analysis
        assert "performance_summary" in analysis

        middleware.stop_monitoring()


class TestQueryOptimizationAdvisor:
    """查询优化顾问测试"""

    def test_advisor_initialization(self):
        """测试顾问初始化"""
        advisor = QueryOptimizationAdvisor()

        assert advisor.optimimization_rules is not None
        assert "select_star" in advisor.optimization_rules
        assert "missing_where" in advisor.optimization_rules

    @pytest.mark.asyncio
    async def test_select_star_detection(self):
        """测试SELECT *检测"""
        advisor = QueryOptimizationAdvisor()

        query = "SELECT * FROM users WHERE active = true"
        analysis = await advisor.analyze_query_for_optimization(query)

        # 应该检测到SELECT *问题
        select_star_suggestions = [
            s
            for s in analysis["optimization_suggestions"]
            if s["rule"] == "select_star"
        ]
        assert len(select_star_suggestions) > 0

    @pytest.mark.asyncio
    async def test_missing_where_detection(self):
        """测试缺失WHERE条件检测"""
        advisor = QueryOptimizationAdvisor()

        query = "SELECT id, name FROM users"
        analysis = await advisor.analyze_query_for_optimization(query)

        # 应该检测到缺失WHERE条件
        missing_where_suggestions = [
            s
            for s in analysis["optimization_suggestions"]
            if s["rule"] == "missing_where"
        ]
        assert len(missing_where_suggestions) > 0

    @pytest.mark.asyncio
    async def test_like_leading_wildcard_detection(self):
        """测试LIKE前导通配符检测"""
        advisor = QueryOptimizationAdvisor()

        query = "SELECT * FROM products WHERE name LIKE '%phone%'"
        analysis = await advisor.analyze_query_for_optimization(query)

        # 应该检测到LIKE前导通配符
        like_suggestions = [
            s
            for s in analysis["optimization_suggestions"]
            if s["rule"] == "like_leading_wildcard"
        ]
        assert len(like_suggestions) > 0

    @pytest.mark.asyncio
    async def test_complexity_calculation(self):
        """�试查询复杂度计算"""
        advisor = QueryOptimizationAdvisor()

        # 简单查询
        simple_query = "SELECT id FROM users"
        simple_complexity = advisor._calculate_query_complexity(simple_query)

        # 复杂查询
        complex_query = """
        SELECT u.id, u.name, COUNT(o.id) as order_count
        FROM users u
        JOIN orders o ON u.id = o.user_id
        WHERE u.active = true
        GROUP BY u.id, u.name
        HAVING COUNT(o.id) > 5
        ORDER BY order_count DESC
        LIMIT 10
        """
        complex_complexity = advisor._calculate_query_complexity(complex_query)

        assert complex_complexity > simple_complexity

    @pytest.mark.asyncio
    async def test_index_suggestions(self):
        """测试索引建议"""
        advisor = QueryOptimizationAdvisor()

        query = "SELECT * FROM products WHERE category = 'electronics' AND price > 100"
        analysis = await advisor.analyze_query_for_optimization(query)

        # 应该有索引建议
        assert len(analysis["index_suggestions"]) > 0


class TestConnectionPoolOptimizer:
    """连接池优化器测试"""

    def test_optimizer_initialization(self):
        """测试优化器初始化"""
        config = PoolOptimizationConfig(
            min_pool_size=2, max_pool_size=10, optimization_interval=60
        )

        optimizer = ConnectionPoolOptimizer(config)

        assert optimizer.config.min_pool_size == 2
        assert optimizer.config.max_pool_size == 10
        assert optimizer.config.optimization_interval == 60
        assert len(optimizer.pools) == 0
        assert optimizer.is_monitoring is False

    def test_pool_registration(self):
        """测试连接池注册"""
        optimizer = ConnectionPoolOptimizer()

        # 模拟连接池
        mock_pool = MagicMock()
        mock_pool.size.return_value = 5
        mock_pool.checkedin.return_value = 3
        mock_pool.checkedout.return_value = 2

        optimizer.register_pool("test_pool", mock_pool)

        assert "test_pool" in optimizer.pools
        assert "test_pool" in optimizer.pool_metrics
        assert optimizer.pool_metrics["test_pool"].creation_time is not None

    @pytest.mark.asyncio
    async def test_monitoring_start_stop(self):
        """测试监控启动和停止"""
        optimizer = ConnectionPoolOptimizer()

        # 启动监控
        await optimizer.start_monitoring()
        assert optimizer.is_monitoring is True
        assert optimizer.monitoring_task is not None

        # 停止监控
        await optimizer.stop_monitoring()
        assert optimizer.is_monitoring is False

    @pytest.mark.asyncio
    async def test_pool_status_retrieval(self):
        """测试连接池状态获取"""
        optimizer = ConnectionPoolOptimizer()

        # 注册模拟连接池
        mock_pool = MagicMock()
        mock_pool.size.return_value = 5
        mock_pool.checkedin.return_value = 3
        mock_pool.checkedout.return_value = 2
        mock_pool.overflow.return_value = 0
        mock_pool.invalid.return_value = 0

        optimizer.register_pool("test_pool", mock_pool)

        # 获取状态
        status = await optimizer.get_pool_status("test_pool")

        assert status is not None
        assert status["pool_name"] == "test_pool"
        assert status["metrics"]["pool_size"] == 5
        assert status["metrics"]["checked_in"] == 3
        assert status["metrics"]["checked_out"] == 2
        assert status["health_status"]["overall"] in ["healthy", "warning", "critical"]

    def test_health_evaluation(self):
        """测试健康状态评估"""
        optimizer = ConnectionPoolOptimizer()

        # 创建健康的指标
        healthy_metrics = PoolMetrics()
        healthy_metrics.utilization_rate = 50.0
        healthy_metrics.invalid = 0

        health = optimizer._evaluate_pool_health(healthy_metrics)
        assert health["overall"] == "healthy"

        # 创建高利用率的指标
        high_util_metrics = PoolMetrics()
        high_util_metrics.utilization_rate = 95.0

        health = optimizer._evaluate_pool_health(high_util_metrics)
        assert health["overall"] in ["warning", "critical"]

    def test_recommendation_generation(self):
        """测试优化建议生成"""
        optimizer = ConnectionPoolOptimizer()

        # 高利用率指标
        high_util_metrics = PoolMetrics()
        high_util_metrics.utilization_rate = 90.0

        recommendations = optimizer._generate_pool_recommendations(high_util_metrics)
        assert any("增加连接池大小" in rec for rec in recommendations)

        # 低利用率指标
        low_util_metrics = PoolMetrics()
        low_util_metrics.utilization_rate = 10.0

        recommendations = optimizer._generate_pool_recommendations(low_util_metrics)
        assert any("减少连接池大小" in rec for rec in recommendations)


class TestQueryExecutionAnalyzer:
    """查询执行分析器测试"""

    def test_analyzer_initialization(self):
        """测试分析器初始化"""
        analyzer = QueryExecutionAnalyzer()

        assert len(analyzer.plan_cache) == 0
        assert len(analyzer.analysis_history) == 0
        assert analyzer.performance_patterns == {}

    def test_query_hash_generation(self):
        """测试查询哈希生成"""
        analyzer = QueryExecutionAnalyzer()

        query1 = "SELECT id, name FROM users WHERE active = true"
        query2 = "select id, name from users where active = true"

        hash1 = analyzer._generate_query_hash(query1)
        hash2 = analyzer._generate_query_hash(query2)

        assert hash1 == hash2  # 标准化后应该相同

    def test_execution_plan_parsing(self):
        """测试执行计划解析"""
        analyzer = QueryExecutionAnalyzer()

        # 模拟执行计划数据
        plan_data = {
            "Plan": {
                "Node Type": "Seq Scan",
                "Relation Name": "users",
                "Startup Cost": 0.0,
                "Total Cost": 15.5,
                "Plan Rows": 100,
                "Plan Width": 20,
                "Actual Total Time": 2.5,
                "Actual Rows": 150,
                "Actual Loops": 1,
            },
            "Execution Time": 3.0,
            "Planning Time": 0.1,
        }

        execution_plan = analyzer._parse_execution_plan(plan_data)

        assert len(execution_plan) == 1
        node = execution_plan[0]
        assert node.node_type == "Seq Scan"
        assert node.relation_name == "users"
        assert node.total_cost == 15.5
        assert node.actual_total_time == 2.5

    def test_used_indexes_identification(self):
        """测试使用索引识别"""
        analyzer = QueryExecutionAnalyzer()

        # 创建带索引的执行计划节点
        node_with_index = ExecutionPlanNode(
            node_type="Index Scan", relation_name="users", index_name="idx_users_email"
        )

        # 创建子节点
        child_node = ExecutionPlanNode(node_type="Seq Scan", relation_name="orders")
        node_with_index.plans.append(child_node)

        execution_plan = [node_with_index]

        used_indexes = analyzer._identify_used_indexes(execution_plan)

        assert "idx_users_email" in used_indexes

    def test_missing_indexes_detection(self):
        """测试缺失索引检测"""
        analyzer = QueryExecutionAnalyzer()

        # 创建全表扫描节点
        seq_scan_node = ExecutionPlanNode(
            node_type="Seq Scan",
            relation_name="large_table",
            rows=5000,  # 大表
        )

        execution_plan = [seq_scan_node]

        # 模拟查询
        query = "SELECT * FROM large_table WHERE category = 'electronics'"

        missing_indexes = asyncio.run(
            analyzer._detect_missing_indexes(query, execution_plan)
        )

        assert len(missing_indexes) > 0
        assert missing_indexes[0]["table"] == "large_table"

    def test_performance_issues_identification(self):
        """测试性能问题识别"""
        analyzer = QueryExecutionAnalyzer()

        # 创建慢查询节点
        slow_node = ExecutionPlanNode(
            node_type="Seq Scan",
            actual_total_time=6.0,  # 超过5秒阈值
        )

        execution_plan = [slow_node]

        issues = analyzer._identify_performance_issues(execution_plan, 6.0)

        assert len(issues) > 0
        slow_execution_issues = [i for i in issues if i["type"] == "slow_execution"]
        assert len(slow_execution_issues) > 0

    def test_analysis_statistics(self):
        """测试分析统计"""
        analyzer = QueryExecutionAnalyzer()

        # 添加一些分析历史
        analyzer.analysis_history = [
            {
                "timestamp": "2024-01-01T00:00:00",
                "execution_time": 1.5,
                "total_cost": 100.0,
                "issues_count": 2,
            },
            {
                "timestamp": "2024-01-01T01:00:00",
                "execution_time": 2.0,
                "total_cost": 150.0,
                "issues_count": 1,
            },
        ]

        stats = analyzer.get_analysis_statistics()

        assert stats["total_analyzed"] == 2
        assert stats["avg_execution_time"] == 1.75  # (1.5 + 2.0) / 2
        assert stats["avg_total_cost"] == 125.0  # (100.0 + 150.0) / 2


class TestExecutionPlanNode:
    """执行计划节点测试"""

    def test_node_creation(self):
        """测试节点创建"""
        node = ExecutionPlanNode(
            node_type="Index Scan", relation_name="users", index_name="idx_users_email"
        )

        assert node.node_type == "Index Scan"
        assert node.relation_name == "users"
        assert node.index_name == "idx_users_email"
        assert node.plans == []  # 默认空列表

    def test_node_with_children(self):
        """测试带子节点的节点"""
        parent_node = ExecutionPlanNode(node_type="Nested Loop", join_type="Inner")

        child_node = ExecutionPlanNode(node_type="Index Scan", relation_name="users")

        parent_node.plans.append(child_node)

        assert len(parent_node.plans) == 1
        assert parent_node.plans[0].node_type == "Index Scan"


class TestIntegration:
    """集成测试"""

    @pytest.mark.asyncio
    async def test_full_optimization_workflow(self):
        """测试完整优化工作流"""
        # 获取各个组件
        db_analyzer = get_database_analyzer()
        middleware = get_database_middleware()
        get_optimization_advisor()

        # 启动监控
        await middleware.start_monitoring()

        # 模拟查询执行
        queries = [
            ("SELECT * FROM users WHERE active = true", 0.5),
            ("SELECT * FROM large_table WHERE category = 'test'", 2.5),  # 慢查询
            ("SELECT id, name FROM products", 0.3),
        ]

        for query, exec_time in queries:
            await db_analyzer.analyze_query(query, exec_time)

        # 获取优化建议
        suggestions = await db_analyzer.get_optimization_suggestions()

        # 验证结果
        assert len(suggestions) > 0  # 应该有优化建议

        # 停止监控
        middleware.stop_monitoring()

    @pytest.mark.asyncio
    async def test_global_functions(self):
        """测试全局获取函数"""
        # 测试全局实例获取
        analyzer1 = get_database_analyzer()
        analyzer2 = get_database_analyzer()
        assert analyzer1 is analyzer2  # 应该是同一个实例

        middleware1 = get_database_middleware()
        middleware2 = get_database_middleware()
        assert middleware1 is middleware2  # 应该是同一个实例

        advisor1 = get_optimization_advisor()
        advisor2 = get_optimization_advisor()
        assert advisor1 is advisor2  # 应该是同一个实例

    @pytest.mark.asyncio
    async def test_error_handling(self):
        """测试错误处理"""
        analyzer = DatabasePerformanceAnalyzer()

        # 测试无效查询处理
        try:
            await analyzer.analyze_query("", 0.1)  # 空查询
            assert True  # 应该不抛出异常
        except Exception:
            pytest.fail("Empty query should not raise exception")

        # 测试负执行时间处理
        try:
            await analyzer.analyze_query("SELECT 1", -0.1)  # 负时间
            assert True  # 应该不抛出异常
        except Exception:
            pytest.fail("Negative execution time should not raise exception")


if __name__ == "__main__":
    pytest.main([__file__])
