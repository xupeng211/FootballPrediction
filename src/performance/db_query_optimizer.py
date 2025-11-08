#!/usr/bin/env python3
"""
数据库查询性能优化模块
提供智能查询优化、索引建议、执行计划分析等功能
"""

import asyncio
import re
import time
from dataclasses import dataclass
from typing import Any

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.logger import get_logger
from src.database.connection import DatabaseManager

logger = get_logger(__name__)


@dataclass
class QueryPerformanceMetrics:
    """查询性能指标"""

    query_hash: str
    execution_count: int = 0
    total_time: float = 0.0
    avg_time: float = 0.0
    min_time: float = float("inf")
    max_time: float = 0.0
    last_executed: float = 0.0
    result_count: int = 0
    error_count: int = 0


@dataclass
class IndexRecommendation:
    """索引推荐"""

    table_name: str
    column_names: list[str]
    index_type: str  # btree, hash, gin, gist
    estimated_improvement: float
    reason: str
    priority: str  # high, medium, low


class QueryAnalyzer:
    """SQL查询分析器"""

    def __init__(self):
        self.query_patterns = {
            "slow_patterns": [
                r"SELECT\s+.*\s+FROM\s+\w+\s+WHERE\s+.*\s+LIKE\s+",  # LIKE查询
                r"SELECT\s+.*\s+FROM\s+\w+\s+ORDER\s+BY\s+.+\s+LIMIT\s+\d+",  # ORDER BY + LIMIT
                r"SELECT\s+.*\s+FROM\s+\w+\s+WHERE\s+.+\s+IN\s+\([^)]+\)",  # IN查询
                r"SELECT\s+COUNT\(.*\)\s+FROM\s+\w+",  # COUNT查询
                r"SELECT\s+.*\s+FROM\s+\w+\s+JOIN\s+.+\s+JOIN\s+",  # 多JOIN
            ],
            "optimization_opportunities": [
                r"SELECT\s+\*\s+FROM",  # SELECT *
                r"WHERE\s+.*\s*=\s*.*\s+OR\s+.*\s*=\s*",  # OR条件
                r"WHERE\s+.*\s+NOT\s+LIKE",  # NOT LIKE
                r"ORDER\s+BY\s+.+\s+DESC",  # DESC排序
            ],
        }

    def analyze_query(self, query: str) -> dict[str, Any]:
        """
        分析SQL查询

        Args:
            query: SQL查询语句

        Returns:
            分析结果
        """
        analysis = {
            "query_type": self._detect_query_type(query),
            "complexity": self._estimate_complexity(query),
            "slow_patterns": [],
            "optimization_opportunities": [],
            "suggested_indexes": [],
            "estimated_cost": self._estimate_execution_cost(query),
        }

        # 检查慢查询模式
        for pattern_name, pattern_list in self.query_patterns.items():
            for pattern in pattern_list:
                matches = re.findall(pattern, query, re.IGNORECASE | re.MULTILINE)
                if matches:
                    if pattern_name == "slow_patterns":
                        analysis["slow_patterns"].extend(matches)
                    elif pattern_name == "optimization_opportunities":
                        analysis["optimization_opportunities"].extend(matches)

        # 生成索引建议
        analysis["suggested_indexes"] = self._suggest_indexes(query)

        return analysis

    def _detect_query_type(self, query: str) -> str:
        """检测查询类型"""
        query_upper = query.strip().upper()
        if query_upper.startswith("SELECT"):
            if "JOIN" in query_upper:
                return "SELECT_JOIN"
            elif "GROUP BY" in query_upper:
                return "SELECT_AGGREGATE"
            elif "ORDER BY" in query_upper:
                return "SELECT_ORDERED"
            else:
                return "SELECT_SIMPLE"
        elif query_upper.startswith("INSERT"):
            return "INSERT"
        elif query_upper.startswith("UPDATE"):
            return "UPDATE"
        elif query_upper.startswith("DELETE"):
            return "DELETE"
        else:
            return "OTHER"

    def _estimate_complexity(self, query: str) -> str:
        """估算查询复杂度"""
        complexity_score = 0
        query_upper = query.upper()

        # 基础分数
        if "JOIN" in query_upper:
            complexity_score += query_upper.count("JOIN") * 2
        if "SUBQUERY" in query_upper or "(" in query:
            complexity_score += 2
        if "GROUP BY" in query_upper:
            complexity_score += 1
        if "ORDER BY" in query_upper:
            complexity_score += 1
        if "UNION" in query_upper:
            complexity_score += 2
        if "HAVING" in query_upper:
            complexity_score += 1

        if complexity_score <= 2:
            return "LOW"
        elif complexity_score <= 5:
            return "MEDIUM"
        else:
            return "HIGH"

    def _estimate_execution_cost(self, query: str) -> float:
        """估算执行成本（相对值）"""
        base_cost = 1.0
        query_upper = query.upper()

        # 复杂度调整
        if "JOIN" in query_upper:
            base_cost *= 1.5 * query_upper.count("JOIN")
        if "LIKE" in query_upper:
            base_cost *= 2.0
        if "ORDER BY" in query_upper:
            base_cost *= 1.3
        if "GROUP BY" in query_upper:
            base_cost *= 1.4
        if query_upper.count("SELECT") > 1:
            base_cost *= 1.2

        return round(base_cost, 2)

    def _suggest_indexes(self, query: str) -> list[IndexRecommendation]:
        """建议索引"""
        recommendations = []

        # 提取WHERE条件中的字段
        where_match = re.search(
            r"WHERE\s+(.+?)(?:\s+GROUP\s+BY|\s+ORDER\s+BY|\s+LIMIT|$)",
            query,
            re.IGNORECASE | re.MULTILINE,
        )
        if where_match:
            where_clause = where_match.group(1)
            # 提取字段名
            column_pattern = r"(\w+)\s*(?:=|>|<|LIKE|IN)"
            columns = re.findall(column_pattern, where_clause, re.IGNORECASE)

            # 为每个字段建议索引
            for column in columns:
                if column.lower() not in ["id", "created_at", "updated_at"]:
                    recommendations.append(
                        IndexRecommendation(
                            table_name="unknown",  # 需要从FROM子句提取
                            column_names=[column],
                            index_type="btree",
                            estimated_improvement=0.7,
                            reason=f"WHERE条件中使用 {column}",
                            priority="high",
                        )
                    )

        # 提取ORDER BY字段
        order_match = re.search(
            r"ORDER\s+BY\s+(.+?)(?:\s+LIMIT|$)", query, re.IGNORECASE | re.MULTILINE
        )
        if order_match:
            order_clause = order_match.group(1)
            columns = [col.strip() for col in order_clause.split(",")]

            for column in columns:
                column = column.split()[0]  # 移除ASC/DESC
                if column.lower() not in ["id", "created_at", "updated_at"]:
                    recommendations.append(
                        IndexRecommendation(
                            table_name="unknown",
                            column_names=[column],
                            index_type="btree",
                            estimated_improvement=0.5,
                            reason=f"ORDER BY使用 {column}",
                            priority="medium",
                        )
                    )

        return recommendations


class QueryOptimizer:
    """查询优化器"""

    def __init__(self, db_manager: DatabaseManager):
        self.db_manager = db_manager
        self.query_metrics: dict[str, QueryPerformanceMetrics] = {}
        self.analyzer = QueryAnalyzer()
        self._slow_query_threshold = 1.0  # 1秒

    async def execute_optimized_query(
        self,
        query: str,
        params: dict[str, Any] | None = None,
        analyze: bool = True,
        auto_explain: bool = False,
    ) -> Any:
        """
        执行优化的查询

        Args:
            query: SQL查询
            params: 查询参数
            analyze: 是否分析查询
            auto_explain: 是否自动生成执行计划

        Returns:
            查询结果
        """
        start_time = time.time()
        query_hash = self._generate_query_hash(query)

        # 获取或创建性能指标
        if query_hash not in self.query_metrics:
            self.query_metrics[query_hash] = QueryPerformanceMetrics(
                query_hash=query_hash
            )
        metrics = self.query_metrics[query_hash]

        try:
            async with self.db_manager.get_async_session() as session:
                # 查询分析
                if analyze:
                    analysis = self.analyzer.analyze_query(query)
                    if analysis["complexity"] == "HIGH":
                        logger.warning(f"复杂查询检测: {query[:100]}...")

                # 自动EXPLAIN（如果启用）
                if auto_explain and self._is_select_query(query):
                    explain_result = await self._explain_query(session, query, params)
                    logger.debug(f"执行计划: {explain_result}")

                # 执行查询
                stmt = text(query)
                result = await session.execute(stmt, params or {})

                # 获取结果
                if self._is_single_result_query(query):
                    data = result.scalar_one_or_none()
                else:
                    data = result.scalars().all()

                # 更新性能指标
                execution_time = time.time() - start_time
                self._update_metrics(
                    metrics, execution_time, len(data) if isinstance(data, list) else 1
                )

                # 慢查询警告
                if execution_time > self._slow_query_threshold:
                    logger.warning(
                        f"慢查询检测: {execution_time:.3f}秒, {query[:100]}..."
                    )

                return data

        except Exception as e:
            execution_time = time.time() - start_time
            metrics.error_count += 1
            logger.error(f"查询执行失败: {e}, 耗时: {execution_time:.3f}秒")
            raise

    async def execute_batch_with_optimization(
        self,
        queries: list[dict[str, Any]],
        max_concurrent: int = 10,
    ) -> list[Any]:
        """
        批量执行优化的查询

        Args:
            queries: 查询列表 [{"query": "...", "params": {...}}, ...]
            max_concurrent: 最大并发数

        Returns:
            查询结果列表
        """
        semaphore = asyncio.Semaphore(max_concurrent)

        async def execute_single(query_data: dict[str, Any]) -> Any:
            async with semaphore:
                return await self.execute_optimized_query(
                    query_data["query"],
                    query_data.get("params"),
                    analyze=True,
                    auto_explain=False,
                )

        # 按复杂度排序，先执行简单查询
        sorted_queries = sorted(
            queries, key=lambda q: self.analyzer._estimate_execution_cost(q["query"])
        )

        tasks = [execute_single(q) for q in sorted_queries]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # 处理异常
        processed_results = []
        for result in results:
            if isinstance(result, Exception):
                logger.error(f"批量查询异常: {result}")
                processed_results.append(None)
            else:
                processed_results.append(result)

        return processed_results

    async def _explain_query(
        self, session: AsyncSession, query: str, params: dict[str, Any] | None
    ) -> str:
        """生成查询执行计划"""
        try:
            explain_query = f"EXPLAIN (ANALYZE, BUFFERS) {query}"
            stmt = text(explain_query)
            result = await session.execute(stmt, params)
            explain_plan = result.fetchall()
            return "\n".join(str(row[0]) for row in explain_plan)
        except Exception as e:
            logger.warning(f"执行计划生成失败: {e}")
            return ""

    def _generate_query_hash(self, query: str) -> str:
        """生成查询哈希"""
        import hashlib

        normalized_query = re.sub(r"\s+", " ", query.strip().lower())
        return hashlib.md5(normalized_query.encode()).hexdigest()[:16]

    def _is_select_query(self, query: str) -> bool:
        """是否为SELECT查询"""
        return query.strip().upper().startswith("SELECT")

    def _is_single_result_query(self, query: str) -> bool:
        """是否为单结果查询"""
        query_upper = query.upper()
        return (
            "LIMIT 1" in query_upper
            or "WHERE" in query_upper
            and "id" in query_upper.lower()
        )

    def _update_metrics(
        self, metrics: QueryPerformanceMetrics, execution_time: float, result_count: int
    ):
        """更新性能指标"""
        metrics.execution_count += 1
        metrics.total_time += execution_time
        metrics.avg_time = metrics.total_time / metrics.execution_count
        metrics.min_time = min(metrics.min_time, execution_time)
        metrics.max_time = max(metrics.max_time, execution_time)
        metrics.last_executed = time.time()
        metrics.result_count = result_count

    def get_performance_report(self) -> dict[str, Any]:
        """获取性能报告"""
        if not self.query_metrics:
            return {"message": "没有查询性能数据"}

        # 统计信息
        total_queries = sum(m.execution_count for m in self.query_metrics.values())
        total_time = sum(m.total_time for m in self.query_metrics.values())
        total_errors = sum(m.error_count for m in self.query_metrics.values())

        # 慢查询
        slow_queries = [
            m
            for m in self.query_metrics.values()
            if m.avg_time > self._slow_query_threshold
        ]

        # 高频查询
        high_frequency_queries = sorted(
            self.query_metrics.values(), key=lambda m: m.execution_count, reverse=True
        )[:10]

        return {
            "summary": {
                "total_queries": total_queries,
                "total_time": round(total_time, 3),
                "avg_query_time": round(total_time / max(1, total_queries), 3),
                "error_rate": round(total_errors / max(1, total_queries) * 100, 2),
                "unique_queries": len(self.query_metrics),
                "slow_queries_count": len(slow_queries),
            },
            "slow_queries": [
                {
                    "query_hash": m.query_hash,
                    "execution_count": m.execution_count,
                    "avg_time": round(m.avg_time, 3),
                    "max_time": round(m.max_time, 3),
                }
                for m in slow_queries
            ],
            "top_queries": [
                {
                    "query_hash": m.query_hash,
                    "execution_count": m.execution_count,
                    "avg_time": round(m.avg_time, 3),
                    "total_time": round(m.total_time, 3),
                    "result_count": m.result_count,
                }
                for m in high_frequency_queries
            ],
            "recommendations": self._generate_recommendations(),
        }

    def _generate_recommendations(self) -> list[str]:
        """生成优化建议"""
        recommendations = []

        # 分析慢查询
        slow_queries = [
            m
            for m in self.query_metrics.values()
            if m.avg_time > self._slow_query_threshold
        ]

        if slow_queries:
            recommendations.append(
                f"发现 {len(slow_queries)} 个慢查询，建议优化查询或添加索引"
            )

        # 分析错误率
        total_errors = sum(m.error_count for m in self.query_metrics.values())
        total_queries = sum(m.execution_count for m in self.query_metrics.values())
        error_rate = total_errors / max(1, total_queries)

        if error_rate > 0.05:  # 5%
            recommendations.append(
                f"查询错误率过高 ({error_rate:.1%})，建议检查查询语法和数据"
            )

        # 分析高频查询
        high_freq = [m for m in self.query_metrics.values() if m.execution_count > 100]

        if high_freq:
            recommendations.append(
                f"发现 {len(high_freq)} 个高频查询，建议添加缓存或优化索引"
            )

        return recommendations

    def clear_metrics(self):
        """清空性能指标"""
        self.query_metrics.clear()
        logger.info("查询性能指标已清空")


class DatabaseOptimizer:
    """数据库优化器"""

    def __init__(self, db_manager: DatabaseManager):
        self.db_manager = db_manager
        self.query_optimizer = QueryOptimizer(db_manager)

    async def analyze_table_performance(self, table_names: list[str]) -> dict[str, Any]:
        """分析表性能"""
        async with self.db_manager.get_async_session() as session:
            analysis = {}

            for table_name in table_names:
                try:
                    # 获取表统计信息
                    stats_query = """
                    SELECT
                        schemaname,
                        tablename,
                        n_tup_ins as inserts,
                        n_tup_upd as updates,
                        n_tup_del as deletes,
                        n_live_tup as live_rows,
                        n_dead_tup as dead_rows,
                        last_vacuum,
                        last_autovacuum,
                        last_analyze,
                        last_autoanalyze
                    FROM pg_stat_user_tables
                    WHERE tablename = :table_name
                    """
                    stmt = text(stats_query)
                    result = await session.execute(stmt, {"table_name": table_name})
                    stats = result.fetchone()

                    # 获取索引信息
                    index_query = """
                    SELECT
                        indexname,
                        indexdef
                    FROM pg_indexes
                    WHERE tablename = :table_name
                    """
                    stmt = text(index_query)
                    index_result = await session.execute(
                        stmt, {"table_name": table_name}
                    )
                    indexes = index_result.fetchall()

                    analysis[table_name] = {
                        "table_stats": dict(stats._mapping) if stats else None,
                        "indexes": [
                            {"name": row[0], "definition": row[1]} for row in indexes
                        ],
                        "recommendations": self._generate_table_recommendations(
                            table_name, stats, indexes
                        ),
                    }

                except Exception as e:
                    logger.error(f"表 {table_name} 性能分析失败: {e}")
                    analysis[table_name] = {"error": str(e)}

            return analysis

    def _generate_table_recommendations(
        self, table_name: str, stats: Any, indexes: list
    ) -> list[str]:
        """生成表优化建议"""
        recommendations = []

        if not stats:
            return ["无法获取表统计信息"]

        # 检查死行比例
        total_rows = stats.n_live_tup + stats.n_dead_tup
        if total_rows > 0:
            dead_ratio = stats.n_dead_tup / total_rows
            if dead_ratio > 0.2:  # 20%
                recommendations.append(
                    f"死行比例过高 ({dead_ratio:.1%})，建议执行VACUUM"
                )

        # 检查索引数量
        if len(indexes) > 10:
            recommendations.append(f"索引数量过多 ({len(indexes)})，可能影响写入性能")

        # 检查最后分析时间
        if not stats.last_analyze and not stats.last_autoanalyze:
            recommendations.append("表从未被分析，建议执行ANALYZE")

        return recommendations

    async def generate_optimization_report(self) -> dict[str, Any]:
        """生成优化报告"""
        # 获取所有用户表
        async with self.db_manager.get_async_session() as session:
            tables_query = """
            SELECT tablename
            FROM pg_tables
            WHERE schemaname = 'public'
            """
            stmt = text(tables_query)
            result = await session.execute(stmt)
            table_names = [row[0] for row in result.fetchall()]

        # 分析表性能
        table_analysis = await self.analyze_table_performance(table_names)

        # 获取查询性能报告
        query_report = self.query_optimizer.get_performance_report()

        return {
            "timestamp": time.time(),
            "tables": table_analysis,
            "queries": query_report,
            "overall_recommendations": self._generate_overall_recommendations(
                table_analysis, query_report
            ),
        }

    def _generate_overall_recommendations(
        self, table_analysis: dict[str, Any], query_report: dict[str, Any]
    ) -> list[str]:
        """生成整体优化建议"""
        recommendations = []

        # 表优化建议
        vacuum_needed = [
            name
            for name, analysis in table_analysis.items()
            if analysis.get("table_stats")
            and any("VACUUM" in rec for rec in analysis.get("recommendations", []))
        ]

        if vacuum_needed:
            recommendations.append(f"建议对表 {', '.join(vacuum_needed)} 执行VACUUM")

        # 查询优化建议
        if query_report.get("summary", {}).get("slow_queries_count", 0) > 0:
            recommendations.append("发现慢查询，建议优化SQL语句或添加索引")

        # 综合建议
        recommendations.extend(
            [
                "定期执行ANALYZE更新统计信息",
                "监控数据库性能指标",
                "考虑使用连接池优化连接管理",
                "为高频查询添加适当的索引",
            ]
        )

        return recommendations


# 全局优化器实例
_global_query_optimizer: QueryOptimizer | None = None
_global_db_optimizer: DatabaseOptimizer | None = None


def get_query_optimizer() -> QueryOptimizer:
    """获取全局查询优化器"""
    global _global_query_optimizer
    if _global_query_optimizer is None:
        _global_query_optimizer = QueryOptimizer(DatabaseManager())
    return _global_query_optimizer


def get_database_optimizer() -> DatabaseOptimizer:
    """获取全局数据库优化器"""
    global _global_db_optimizer
    if _global_db_optimizer is None:
        _global_db_optimizer = DatabaseOptimizer(DatabaseManager())
    return _global_db_optimizer


if __name__ == "__main__":

    async def demo_database_optimization():
        """演示数据库优化功能"""
        print("🚀 演示数据库查询性能优化")

        optimizer = get_query_optimizer()
        db_optimizer = get_database_optimizer()

        # 模拟查询执行
        test_queries = [
            {"query": "SELECT 1 as test", "params": None},
            {"query": "SELECT 2 as test", "params": None},
        ]

        # 执行优化查询
        results = await optimizer.execute_batch_with_optimization(test_queries)
        print(f"✅ 执行了 {len(results)} 个优化查询")

        # 生成性能报告
        report = optimizer.get_performance_report()
        print(f"📊 查询性能报告: {report}")

        # 生成数据库优化报告
        db_report = await db_optimizer.generate_optimization_report()
        print("📈 数据库优化报告生成完成")

    asyncio.run(demo_database_optimization())
