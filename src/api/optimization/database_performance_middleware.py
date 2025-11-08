"""
数据库性能监控中间件
Database Performance Monitoring Middleware

提供实时的数据库查询性能监控和自动优化建议。
"""

import asyncio
import logging
import time
from typing import Any

from sqlalchemy import event
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Session
from sqlalchemy.pool import Pool

from src.api.optimization.database_query_optimizer import get_database_analyzer

logger = logging.getLogger(__name__)


class DatabasePerformanceMiddleware:
    """数据库性能监控中间件"""

    def __init__(
        self,
        enable_query_tracking: bool = True,
        enable_slow_query_detection: bool = True,
        slow_query_threshold: float = 1.0,
        enable_connection_pool_monitoring: bool = True,
    ):
        self.enable_query_tracking = enable_query_tracking
        self.enable_slow_query_detection = enable_slow_query_detection
        self.slow_query_threshold = slow_query_threshold
        self.enable_connection_pool_monitoring = enable_connection_pool_monitoring

        self.db_analyzer = get_database_analyzer()
        self.is_monitoring = False

    async def start_monitoring(self):
        """开始监控"""
        if self.is_monitoring:
            return

        self.is_monitoring = True

        # 注册SQLAlchemy事件监听器
        if self.enable_query_tracking:
            self._register_query_listeners()

        if self.enable_connection_pool_monitoring:
            self._register_pool_listeners()

        logger.info("Database performance monitoring started")

    def stop_monitoring(self):
        """停止监控"""
        self.is_monitoring = False
        # 这里可以添加事件监听器的注销逻辑
        logger.info("Database performance monitoring stopped")

    def _register_query_listeners(self):
        """注册查询监听器"""

        @event.listens_for(AsyncSession, "before_cursor_execute")
        def before_cursor_execute_async(
            conn, cursor, statement, parameters, context, executemany
        ):
            context._query_start_time = time.time()

        @event.listens_for(AsyncSession, "after_cursor_execute")
        def after_cursor_execute_async(
            conn, cursor, statement, parameters, context, executemany
        ):
            if not self.is_monitoring:
                return

            try:
                start_time = getattr(context, "_query_start_time", None)
                if start_time:
                    execution_time = time.time() - start_time

                    # 获取行数信息（如果可用）
                    rows_returned = getattr(cursor, "rowcount", 0)
                    rows_examined = self._estimate_rows_examined(statement, parameters)

                    # 异步分析查询
                    asyncio.create_task(
                        self.db_analyzer.analyze_query(
                            statement,
                            execution_time,
                            rows_returned=rows_returned,
                            rows_examined=rows_examined,
                            error=False,
                        )
                    )

                    # 检查慢查询
                    if (
                        self.enable_slow_query_detection
                        and execution_time > self.slow_query_threshold
                    ):
                        self._handle_slow_query(statement, execution_time, parameters)

            except Exception as e:
                logger.error(f"Error in query monitoring: {e}")

        @event.listens_for(Session, "before_cursor_execute")
        def before_cursor_execute_sync(
            conn, cursor, statement, parameters, context, executemany
        ):
            context._query_start_time = time.time()

        @event.listens_for(Session, "after_cursor_execute")
        def after_cursor_execute_sync(
            conn, cursor, statement, parameters, context, executemany
        ):
            if not self.is_monitoring:
                return

            try:
                start_time = getattr(context, "_query_start_time", None)
                if start_time:
                    execution_time = time.time() - start_time

                    rows_returned = getattr(cursor, "rowcount", 0)
                    rows_examined = self._estimate_rows_examined(statement, parameters)

                    # 异步分析查询
                    asyncio.create_task(
                        self.db_analyzer.analyze_query(
                            statement,
                            execution_time,
                            rows_returned=rows_returned,
                            rows_examined=rows_examined,
                            error=False,
                        )
                    )

                    if (
                        self.enable_slow_query_detection
                        and execution_time > self.slow_query_threshold
                    ):
                        self._handle_slow_query(statement, execution_time, parameters)

            except Exception as e:
                logger.error(f"Error in sync query monitoring: {e}")

        @event.listens_for(AsyncSession, "handle_error")
        def handle_error_async(exc, context):
            if self.is_monitoring and hasattr(context, "statement"):
                asyncio.create_task(
                    self.db_analyzer.analyze_query(context.statement, 0.0, error=True)
                )

        @event.listens_for(Session, "handle_error")
        def handle_error_sync(exc, context):
            if self.is_monitoring and hasattr(context, "statement"):
                asyncio.create_task(
                    self.db_analyzer.analyze_query(context.statement, 0.0, error=True)
                )

    def _register_pool_listeners(self):
        """注册连接池监听器"""

        @event.listens_for(Pool, "connect")
        def on_connect(dbapi_connection, connection_record):
            # 记录新连接
            pass

        @event.listens_for(Pool, "checkout")
        def on_checkout(dbapi_connection, connection_record, connection_proxy):
            # 记录连接检出
            pass

        @event.listens_for(Pool, "checkin")
        def on_checkin(dbapi_connection, connection_record):
            # 记录连接检入
            pass

    def _estimate_rows_examined(self, statement: str, parameters: Any) -> int:
        """估算检查的行数"""
        # 这里可以实现更复杂的逻辑来估算检查的行数
        # 目前返回0表示无法估算
        return 0

    def _handle_slow_query(
        self, statement: str, execution_time: float, parameters: Any
    ):
        """处理慢查询"""
        logger.warning(
            f"Slow query detected: {execution_time:.4f}s - {statement[:200]}..."
        )

        # 可以在这里添加额外的慢查询处理逻辑
        # 例如：发送警报、记录到专门的慢查询日志等

    async def get_real_time_metrics(self) -> dict[str, Any]:
        """获取实时性能指标"""
        if not self.is_monitoring:
            return {"status": "monitoring_disabled"}

        performance_summary = self.db_analyzer.get_performance_summary()
        optimization_suggestions = await self.db_analyzer.get_optimization_suggestions()

        return {
            "status": "active",
            "monitoring_enabled": True,
            "slow_query_threshold": self.slow_query_threshold,
            "performance_summary": performance_summary,
            "optimization_suggestions_count": len(optimization_suggestions),
            "high_priority_suggestions": len(
                [
                    s
                    for s in optimization_suggestions
                    if s["priority"] in ["critical", "high"]
                ]
            ),
            "timestamp": time.time(),
        }

    async def analyze_current_performance(self) -> dict[str, Any]:
        """分析当前性能状况"""
        if not self.is_monitoring:
            return {"error": "Monitoring is not enabled"}

        # 获取最慢的查询
        top_slow_queries = await self.db_analyzer.get_top_slow_queries(5)

        # 获取最频繁的查询
        most_frequent = await self.db_analyzer.get_most_frequent_queries(5)

        # 获取高错误率查询
        high_error_queries = await self.db_analyzer.get_queries_with_high_error_rate(
            5.0
        )

        # 获取优化建议
        suggestions = await self.db_analyzer.get_optimization_suggestions()

        return {
            "top_slow_queries": top_slow_queries,
            "most_frequent_queries": most_frequent,
            "high_error_rate_queries": high_error_queries,
            "optimization_suggestions": suggestions,
            "performance_summary": self.db_analyzer.get_performance_summary(),
            "analysis_timestamp": time.time(),
        }


class QueryOptimizationAdvisor:
    """查询优化顾问"""

    def __init__(self):
        self.optimization_rules = self._initialize_optimization_rules()

    def _initialize_optimization_rules(self) -> dict[str, Any]:
        """初始化优化规则"""
        return {
            "select_star": {
                "pattern": r"SELECT\s+\*\s+FROM",
                "suggestion": "避免使用SELECT *，只查询需要的字段以减少数据传输量",
                "priority": "medium",
                "impact": "medium",
            },
            "missing_where": {
                "pattern": r"SELECT.*FROM\s+\w+(?!\s+WHERE)",
                "suggestion": "查询缺少WHERE条件，可能返回过多数据",
                "priority": "high",
                "impact": "high",
            },
            "like_leading_wildcard": {
                "pattern": r"LIKE\s+'%[^']*'",
                "suggestion": "LIKE查询以通配符开头无法使用索引，考虑全文索引或修改查询逻辑",
                "priority": "high",
                "impact": "high",
            },
            "order_without_limit": {
                "pattern": r"ORDER\s+BY.*$(?!.*LIMIT)",
                "suggestion": "ORDER BY缺少LIMIT，可能导致大量排序操作",
                "priority": "medium",
                "impact": "medium",
            },
            "too_many_joins": {
                "pattern": r"(JOIN\s+\w+){4,}",  # 4个或更多JOIN
                "suggestion": "JOIN过多，考虑拆分查询或优化表结构",
                "priority": "high",
                "impact": "high",
            },
            "subquery_in_where": {
                "pattern": r"WHERE.*\(SELECT.*\)",
                "suggestion": "WHERE子句中的子查询可能影响性能，考虑使用JOIN替代",
                "priority": "medium",
                "impact": "medium",
            },
        }

    async def analyze_query_for_optimization(self, query_text: str) -> dict[str, Any]:
        """分析查询并提供优化建议"""
        import re

        suggestions = []
        query_lower = query_text.lower()

        for rule_name, rule_info in self.optimization_rules.items():
            pattern = rule_info["pattern"]
            if re.search(pattern, query_lower, re.IGNORECASE | re.MULTILINE):
                suggestions.append(
                    {
                        "rule": rule_name,
                        "suggestion": rule_info["suggestion"],
                        "priority": rule_info["priority"],
                        "impact": rule_info["impact"],
                    }
                )

        # 检查查询复杂度
        complexity_score = self._calculate_query_complexity(query_text)

        # 检查潜在索引使用
        index_suggestions = self._suggest_indexes(query_text)

        return {
            "query_text": (
                query_text[:200] + "..." if len(query_text) > 200 else query_text
            ),
            "complexity_score": complexity_score,
            "optimization_suggestions": suggestions,
            "index_suggestions": index_suggestions,
            "overall_priority": self._determine_overall_priority(
                suggestions, complexity_score
            ),
        }

    def _calculate_query_complexity(self, query_text: str) -> int:
        """计算查询复杂度分数"""
        complexity = 0
        query_lower = query_text.lower()

        # 基础分数
        if "select" in query_lower:
            complexity += 1
        if "where" in query_lower:
            complexity += 2
        if "join" in query_lower:
            complexity += query_lower.count("join") * 3
        if "subquery" in query_lower or "(" in query_text:
            complexity += 2
        if "union" in query_lower:
            complexity += 3
        if "group by" in query_lower:
            complexity += 2
        if "order by" in query_lower:
            complexity += 1
        if "having" in query_lower:
            complexity += 2

        return complexity

    def _suggest_indexes(self, query_text: str) -> list[str]:
        """建议索引"""
        import re

        suggestions = []
        query_lower = query_text.lower()

        # 提取WHERE条件中的字段
        where_pattern = r"WHERE\s+([^;]+)"
        where_match = re.search(where_pattern, query_lower, re.IGNORECASE)

        if where_match:
            where_clause = where_match.group(1)
            # 简单的字段提取（实际应用中需要更复杂的解析）
            field_pattern = r"(\w+)\s*(?:=|>|<|>=|<=|like|in)"
            fields = re.findall(field_pattern, where_clause)

            for field in fields:
                if field not in [
                    "id",
                    "created_at",
                    "updated_at",
                ]:  # 常见已有索引的字段
                    suggestions.append(f"考虑在字段 '{field}' 上创建索引")

        # 提取ORDER BY字段
        order_pattern = r"ORDER\s+BY\s+([^;\s]+)"
        order_match = re.search(order_pattern, query_lower, re.IGNORECASE)

        if order_match:
            order_field = order_match.group(1)
            if order_field not in ["id", "created_at", "updated_at"]:
                suggestions.append(f"考虑在排序字段 '{order_field}' 上创建索引")

        return suggestions

    def _determine_overall_priority(
        self, suggestions: list, complexity_score: int
    ) -> str:
        """确定整体优先级"""
        if any(s["priority"] == "high" for s in suggestions) or complexity_score > 10:
            return "high"
        elif (
            any(s["priority"] == "medium" for s in suggestions) or complexity_score > 5
        ):
            return "medium"
        else:
            return "low"


# 全局中间件实例
_db_middleware: DatabasePerformanceMiddleware | None = None
_optimization_advisor: QueryOptimizationAdvisor | None = None


def get_database_middleware() -> DatabasePerformanceMiddleware:
    """获取全局数据库中间件实例"""
    global _db_middleware
    if _db_middleware is None:
        _db_middleware = DatabasePerformanceMiddleware()
    return _db_middleware


def get_optimization_advisor() -> QueryOptimizationAdvisor:
    """获取全局优化顾问实例"""
    global _optimization_advisor
    if _optimization_advisor is None:
        _optimization_advisor = QueryOptimizationAdvisor()
    return _optimization_advisor


async def initialize_database_monitoring(
    enable_query_tracking: bool = True,
    enable_slow_query_detection: bool = True,
    slow_query_threshold: float = 1.0,
) -> DatabasePerformanceMiddleware:
    """初始化数据库监控"""
    global _db_middleware

    _db_middleware = DatabasePerformanceMiddleware(
        enable_query_tracking=enable_query_tracking,
        enable_slow_query_detection=enable_slow_query_detection,
        slow_query_threshold=slow_query_threshold,
    )

    await _db_middleware.start_monitoring()
    logger.info("Database performance monitoring middleware initialized")

    return _db_middleware
