"""
数据库查询性能优化器
Database Query Performance Optimizer

提供数据库查询性能分析、慢查询检测、索引优化建议等功能。
"""

import logging
from collections import deque
from datetime import datetime, timedelta
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.pool import QueuePool

logger = logging.getLogger(__name__)


class QueryMetrics:
    """查询指标类"""

    def __init__(self, query_hash: str, query_text: str):
        self.query_hash = query_hash
        self.query_text = query_text
        self.execution_count = 0
        self.total_time = 0.0
        self.min_time = float("inf")
        self.max_time = 0.0
        self.avg_time = 0.0
        self.recent_times = deque(maxlen=100)
        self.error_count = 0
        self.last_executed = None
        self.execution_times = []
        self.rows_examined = 0
        self.rows_returned = 0

    def record_execution(
        self,
        execution_time: float,
        rows_returned: int = 0,
        rows_examined: int = 0,
        error: bool = False,
    ):
        """记录查询执行"""
        self.execution_count += 1
        self.last_executed = datetime.utcnow()

        if error:
            self.error_count += 1
            return

        self.total_time += execution_time
        self.min_time = min(self.min_time, execution_time)
        self.max_time = max(self.max_time, execution_time)
        self.avg_time = self.total_time / self.execution_count
        self.recent_times.append(execution_time)
        self.execution_times.append(execution_time)
        self.rows_returned += rows_returned
        self.rows_examined += rows_examined

    def get_p50(self) -> float:
        """获取P50响应时间"""
        if not self.recent_times:
            return 0.0
        sorted_times = sorted(self.recent_times)
        n = len(sorted_times)
        return sorted_times[n // 2]

    def get_p95(self) -> float:
        """获取P95响应时间"""
        if not self.recent_times:
            return 0.0
        sorted_times = sorted(self.recent_times)
        n = len(sorted_times)
        return sorted_times[int(n * 0.95)]

    def get_p99(self) -> float:
        """获取P99响应时间"""
        if not self.recent_times:
            return 0.0
        sorted_times = sorted(self.recent_times)
        n = len(sorted_times)
        return sorted_times[int(n * 0.99)]

    def get_error_rate(self) -> float:
        """获取错误率"""
        if self.execution_count == 0:
            return 0.0
        return (self.error_count / self.execution_count) * 100

    def to_dict(self) -> dict[str, Any]:
        """转换为字典格式"""
        return {
            "query_hash": self.query_hash,
            "query_text": (
                self.query_text[:200] + "..."
                if len(self.query_text) > 200
                else self.query_text
            ),
            "execution_count": self.execution_count,
            "avg_time": round(self.avg_time, 4),
            "min_time": round(self.min_time, 4),
            "max_time": round(self.max_time, 4),
            "p50_time": round(self.get_p50(), 4),
            "p95_time": round(self.get_p95(), 4),
            "p99_time": round(self.get_p99(), 4),
            "error_rate": round(self.get_error_rate(), 2),
            "total_time": round(self.total_time, 4),
            "rows_returned": self.rows_returned,
            "rows_examined": self.rows_examined,
            "last_executed": (
                self.last_executed.isoformat() if self.last_executed else None
            ),
        }


class DatabasePerformanceAnalyzer:
    """数据库性能分析器"""

    def __init__(self, max_query_history: int = 1000):
        self.max_query_history = max_query_history
        self.query_metrics: dict[str, QueryMetrics] = {}
        self.slow_queries: list[dict[str, Any]] = []
        self.performance_alerts: list[dict[str, Any]] = []
        self.index_usage_stats: dict[str, dict[str, Any]] = {}
        self.table_stats: dict[str, dict[str, Any]] = {}
        self.connection_pool_stats = {}
        self.analysis_start_time = datetime.utcnow()

    def generate_query_hash(self, query_text: str) -> str:
        """生成查询哈希值"""
        import hashlib

        # 标准化查询文本（移除多余空格、统一大小写）
        normalized_query = " ".join(query_text.strip().split()).lower()
        return hashlib.sha256(normalized_query.encode()).hexdigest()

    async def analyze_query(
        self,
        query_text: str,
        execution_time: float,
        session: AsyncSession | None = None,
        rows_returned: int = 0,
        rows_examined: int = 0,
        error: bool = False,
    ) -> str:
        """分析查询性能"""
        query_hash = self.generate_query_hash(query_text)

        if query_hash not in self.query_metrics:
            self.query_metrics[query_hash] = QueryMetrics(query_hash, query_text)

        # 记录查询执行
        self.query_metrics[query_hash].record_execution(
            execution_time, rows_returned, rows_examined, error
        )

        # 检查是否为慢查询
        if execution_time > 1.0:  # 超过1秒的查询
            await self._record_slow_query(query_hash, query_text, execution_time)

        # 检查性能警告
        await self._check_performance_alerts(query_hash)

        return query_hash

    async def _record_slow_query(
        self, query_hash: str, query_text: str, execution_time: float
    ):
        """记录慢查询"""
        slow_query = {
            "query_hash": query_hash,
            "query_text": query_text,
            "execution_time": execution_time,
            "timestamp": datetime.utcnow().isoformat(),
            "suggestions": await self._generate_slow_query_suggestions(
                query_text, execution_time
            ),
        }

        self.slow_queries.append(slow_query)

        # 保持慢查询历史记录在合理范围内
        if len(self.slow_queries) > 500:
            self.slow_queries = self.slow_queries[-400:]

        logger.warning(
            f"Slow query detected: {execution_time:.4f}s - {query_text[:100]}..."
        )

    async def _generate_slow_query_suggestions(
        self, query_text: str, execution_time: float
    ) -> list[str]:
        """生成慢查询优化建议"""
        suggestions = []

        query_lower = query_text.lower()

        # 检查常见的性能问题
        if "select *" in query_lower:
            suggestions.append("避免使用SELECT *，只查询需要的字段")

        if "where" not in query_lower and "join" not in query_lower:
            suggestions.append("查询缺少WHERE条件，可能返回过多数据")

        if query_lower.count("join") > 3:
            suggestions.append("JOIN过多，考虑拆分查询或优化表结构")

        if "like" in query_lower and "%" in query_text:
            suggestions.append("LIKE查询以通配符开头无法使用索引，考虑全文索引")

        if "order by" in query_lower and "limit" not in query_lower:
            suggestions.append("ORDER BY缺少LIMIT，可能导致大量排序操作")

        if execution_time > 5.0:
            suggestions.append("查询时间过长，考虑添加适当的索引")

        return suggestions

    async def _check_performance_alerts(self, query_hash: str):
        """检查性能警告"""
        metrics = self.query_metrics[query_hash]

        # 检查错误率
        if metrics.get_error_rate() > 10 and metrics.execution_count > 10:
            alert = {
                "type": "high_error_rate",
                "query_hash": query_hash,
                "message": f"查询错误率过高: {metrics.get_error_rate():.2f}%",
                "timestamp": datetime.utcnow().isoformat(),
                "severity": "high",
            }
            self.performance_alerts.append(alert)

        # 检查平均响应时间
        if metrics.avg_time > 2.0 and metrics.execution_count > 5:
            alert = {
                "type": "high_response_time",
                "query_hash": query_hash,
                "message": f"查询平均响应时间过长: {metrics.avg_time:.4f}s",
                "timestamp": datetime.utcnow().isoformat(),
                "severity": "medium",
            }
            self.performance_alerts.append(alert)

        # 保持警告历史记录在合理范围内
        if len(self.performance_alerts) > 200:
            self.performance_alerts = self.performance_alerts[-150:]

    async def analyze_connection_pool(self, pool: QueuePool) -> dict[str, Any]:
        """分析连接池状态"""
        if not pool:
            return {}

        pool_stats = {
            "pool_size": pool.size(),
            "checked_in": pool.checkedin(),
            "checked_out": pool.checkedout(),
            "overflow": pool.overflow(),
            "invalid": pool.invalid(),
            "pool_utilization": 0.0,
            "timestamp": datetime.utcnow().isoformat(),
        }

        if pool.size() > 0:
            pool_stats["pool_utilization"] = (pool.checkedout() / pool.size()) * 100

        self.connection_pool_stats = pool_stats
        return pool_stats

    async def get_top_slow_queries(self, limit: int = 10) -> list[dict[str, Any]]:
        """获取最慢的查询"""
        sorted_queries = sorted(
            self.query_metrics.values(), key=lambda x: x.avg_time, reverse=True
        )

        return [query.to_dict() for query in sorted_queries[:limit]]

    async def get_most_frequent_queries(self, limit: int = 10) -> list[dict[str, Any]]:
        """获取执行频率最高的查询"""
        sorted_queries = sorted(
            self.query_metrics.values(), key=lambda x: x.execution_count, reverse=True
        )

        return [query.to_dict() for query in sorted_queries[:limit]]

    async def get_queries_with_high_error_rate(
        self, min_error_rate: float = 5.0
    ) -> list[dict[str, Any]]:
        """获取错误率高的查询"""
        high_error_queries = []

        for metrics in self.query_metrics.values():
            if (
                metrics.get_error_rate() >= min_error_rate
                and metrics.execution_count >= 5
            ):
                query_data = metrics.to_dict()
                high_error_queries.append(query_data)

        return sorted(high_error_queries, key=lambda x: x["error_rate"], reverse=True)

    def get_performance_summary(self) -> dict[str, Any]:
        """获取性能摘要"""
        if not self.query_metrics:
            return {
                "total_queries": 0,
                "avg_response_time": 0.0,
                "slow_queries_count": 0,
                "high_error_rate_queries": 0,
                "analysis_duration": (
                    datetime.utcnow() - self.analysis_start_time
                ).total_seconds(),
            }

        total_queries = sum(m.execution_count for m in self.query_metrics.values())
        total_time = sum(m.total_time for m in self.query_metrics.values())
        avg_response_time = total_time / total_queries if total_queries > 0 else 0.0

        slow_queries_count = len(
            [q for q in self.query_metrics.values() if q.avg_time > 1.0]
        )
        high_error_rate_queries = len(
            [q for q in self.query_metrics.values() if q.get_error_rate() > 5.0]
        )

        return {
            "total_queries": total_queries,
            "unique_queries": len(self.query_metrics),
            "avg_response_time": round(avg_response_time, 4),
            "slow_queries_count": slow_queries_count,
            "high_error_rate_queries": high_error_rate_queries,
            "total_errors": sum(m.error_count for m in self.query_metrics.values()),
            "connection_pool_stats": self.connection_pool_stats,
            "analysis_duration": (
                datetime.utcnow() - self.analysis_start_time
            ).total_seconds(),
            "timestamp": datetime.utcnow().isoformat(),
        }

    async def get_optimization_suggestions(self) -> list[dict[str, Any]]:
        """获取优化建议"""
        suggestions = []

        # 分析慢查询
        for query_hash, metrics in self.query_metrics.items():
            if metrics.avg_time > 1.0:
                suggestion = {
                    "type": "slow_query",
                    "query_hash": query_hash,
                    "priority": "high" if metrics.avg_time > 5.0 else "medium",
                    "description": f"查询平均响应时间过长: {metrics.avg_time:.4f}s",
                    "suggestions": await self._generate_slow_query_suggestions(
                        metrics.query_text, metrics.avg_time
                    ),
                    "impact": "high" if metrics.execution_count > 10 else "medium",
                }
                suggestions.append(suggestion)

        # 分析高错误率查询
        for query_hash, metrics in self.query_metrics.items():
            if metrics.get_error_rate() > 10 and metrics.execution_count > 5:
                suggestion = {
                    "type": "high_error_rate",
                    "query_hash": query_hash,
                    "priority": "critical",
                    "description": f"查询错误率过高: {metrics.get_error_rate():.2f}%",
                    "suggestions": [
                        "检查查询语法和逻辑",
                        "验证数据完整性",
                        "检查数据库连接稳定性",
                        "优化查询参数",
                    ],
                    "impact": "critical",
                }
                suggestions.append(suggestion)

        # 连接池优化建议
        if self.connection_pool_stats:
            utilization = self.connection_pool_stats.get("pool_utilization", 0)
            if utilization > 80:
                suggestions.append(
                    {
                        "type": "connection_pool",
                        "priority": "high",
                        "description": f"连接池利用率过高: {utilization:.1f}%",
                        "suggestions": [
                            "增加连接池大小",
                            "优化查询以减少连接占用时间",
                            "检查是否有连接泄漏",
                        ],
                        "impact": "high",
                    }
                )

        return sorted(
            suggestions,
            key=lambda x: (
                {"critical": 0, "high": 1, "medium": 2, "low": 3}.get(x["priority"], 4),
                {"critical": 0, "high": 1, "medium": 2, "low": 3}.get(x["impact"], 4),
            ),
        )

    async def clear_old_data(self, days_to_keep: int = 7):
        """清理旧数据"""
        cutoff_date = datetime.utcnow() - timedelta(days=days_to_keep)

        # 清理旧的慢查询记录
        self.slow_queries = [
            sq
            for sq in self.slow_queries
            if datetime.fromisoformat(sq["timestamp"]) > cutoff_date
        ]

        # 清理旧的性能警告
        self.performance_alerts = [
            alert
            for alert in self.performance_alerts
            if datetime.fromisoformat(alert["timestamp"]) > cutoff_date
        ]

        # 清理长时间未访问的查询指标
        old_queries = []
        for query_hash, metrics in self.query_metrics.items():
            if (
                metrics.last_executed
                and metrics.last_executed < cutoff_date
                and metrics.execution_count < 5
            ):
                old_queries.append(query_hash)

        for query_hash in old_queries:
            del self.query_metrics[query_hash]

        logger.info(
            f"Cleaned up old performance data: removed {len(old_queries)} old queries"
        )


# 全局数据库性能分析器实例
_db_analyzer: DatabasePerformanceAnalyzer | None = None


def get_database_analyzer() -> DatabasePerformanceAnalyzer:
    """获取全局数据库性能分析器实例"""
    global _db_analyzer
    if _db_analyzer is None:
        _db_analyzer = DatabasePerformanceAnalyzer()
    return _db_analyzer


async def initialize_database_analyzer(
    max_query_history: int = 1000,
) -> DatabasePerformanceAnalyzer:
    """初始化数据库性能分析器"""
    global _db_analyzer
    _db_analyzer = DatabasePerformanceAnalyzer(max_query_history)
    logger.info("Database performance analyzer initialized")
    return _db_analyzer
