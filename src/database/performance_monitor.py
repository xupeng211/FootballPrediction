#!/usr/bin/env python3
"""
数据库性能监控工具 - Sprint 4 核心组件

专门监控50GB+大规模数据处理的数据库性能。
提供实时监控、性能分析和优化建议。

设计原则:
- Real-time Monitoring (实时监控)
- Performance Analytics (性能分析)
- Optimization Suggestions (优化建议)
- Alert System (告警系统)
"""

import asyncio
from dataclasses import dataclass, field
from datetime import datetime, timedelta
import logging
import time
from typing import Any

from .connection import get_connection

logger = logging.getLogger(__name__)


@dataclass
class DatabaseMetrics:
    """数据库性能指标"""

    timestamp: datetime
    active_connections: int
    total_connections: int
    database_size_mb: float
    table_size_mb: dict[str, float]
    index_size_mb: dict[str, float]
    query_performance: dict[str, float] = field(default_factory=dict)
    cache_hit_ratio: float = 0.0
    rows_inserted: int = 0
    rows_updated: int = 0
    rows_deleted: int = 0
    dead_tuples: int = 0
    vacuum_status: str = "unknown"


@dataclass
class QueryPerformance:
    """查询性能指标"""

    query_text: str
    execution_time_ms: float
    rows_returned: int
    plan_json: dict[str, Any] | None = None
    index_usage: list[str] = field(default_factory=list)
    recommendations: list[str] = field(default_factory=list)


@dataclass
class PerformanceAlert:
    """性能告警"""

    level: str  # INFO, WARNING, ERROR, CRITICAL
    metric_name: str
    current_value: float
    threshold_value: float
    message: str
    timestamp: datetime = field(default_factory=datetime.now)


class DatabasePerformanceMonitor:
    """
    数据库性能监控器

    提供：
    - 实时性能指标收集
    - 查询性能分析
    - 自动优化建议
    - 性能告警系统
    """

    def __init__(self):
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")
        self._metrics_history: list[DatabaseMetrics] = []
        self._alerts: list[PerformanceAlert] = []
        self._running = False
        self._monitor_task: asyncio.Task | None = None

        # 性能阈值配置
        self._thresholds = {
            "active_connections_warning": 80,
            "active_connections_critical": 95,
            "cache_hit_ratio_warning": 0.8,
            "dead_tuples_warning": 100000,
            "dead_tuples_critical": 1000000,
            "query_time_warning_ms": 1000,
            "query_time_critical_ms": 5000,
        }

    async def start_monitoring(self, interval_seconds: int = 60) -> None:
        """启动性能监控"""
        if self._running:
            return

        self._running = True
        self._monitor_task = asyncio.create_task(self._monitoring_loop(interval_seconds))

        self.logger.info(f"🔄 数据库性能监控已启动 (间隔: {interval_seconds}秒)")

    async def stop_monitoring(self) -> None:
        """停止性能监控"""
        self._running = False

        if self._monitor_task:
            self._monitor_task.cancel()
            try:
                await self._monitor_task
            except asyncio.CancelledError:
                pass

        self.logger.info("✅ 数据库性能监控已停止")

    async def collect_metrics(self) -> DatabaseMetrics:
        """收集性能指标"""
        try:
            conn = await get_connection()

            metrics = DatabaseMetrics(
                timestamp=datetime.now(),
                active_connections=0,
                total_connections=0,
                database_size_mb=0.0,
                table_size_mb={},
                index_size_mb={},
                cache_hit_ratio=0.0,
                rows_inserted=0,
                rows_updated=0,
                rows_deleted=0,
                dead_tuples=0,
                vacuum_status="unknown",
            )

            # 收集连接指标
            await self._collect_connection_metrics(conn, metrics)

            # 收集存储指标
            await self._collect_storage_metrics(conn, metrics)

            # 收集性能指标
            await self._collect_performance_metrics(conn, metrics)

            # 检查告警条件
            self._check_alerts(metrics)

            # 保存历史数据
            self._metrics_history.append(metrics)
            if len(self._metrics_history) > 1000:  # 保留最近1000条记录
                self._metrics_history.pop(0)

            return metrics

        except Exception as e:
            self.logger.error(f"收集性能指标失败: {e}")
            raise

    async def analyze_query_performance(self, query: str) -> QueryPerformance:
        """分析查询性能"""
        try:
            conn = await get_connection()

            start_time = time.time()

            # 执行EXPLAIN ANALYZE
            explain_query = f"EXPLAIN (ANALYZE, FORMAT JSON) {query}"
            result = await conn.fetchrow(explain_query)

            execution_time = (time.time() - start_time) * 1000
            plan_data = result["QUERY PLAN"][0]

            # 提取性能信息
            performance = QueryPerformance(
                query_text=query,
                execution_time_ms=execution_time,
                rows_returned=plan_data["Plan"].get("Actual Rows", 0),
                plan_json=plan_data,
            )

            # 分析索引使用
            performance.index_usage = self._extract_index_usage(plan_data)

            # 生成优化建议
            performance.recommendations = self._generate_query_recommendations(plan_data, execution_time)

            return performance

        except Exception as e:
            self.logger.error(f"查询性能分析失败: {e}")
            return QueryPerformance(
                query_text=query,
                execution_time_ms=0.0,
                rows_returned=0,
                recommendations=[f"分析失败: {e!s}"],
            )

    async def get_optimization_recommendations(self) -> list[str]:
        """获取优化建议"""
        recommendations = []

        # 基于最新指标生成建议
        if not self._metrics_history:
            return ["没有足够的历史数据生成建议"]

        latest_metrics = self._metrics_history[-1]

        # 连接数建议
        if latest_metrics.active_connections > self._thresholds["active_connections_warning"]:
            recommendations.append(
                f"活跃连接数过高 ({latest_metrics.active_connections})，考虑增加连接池大小或优化查询"
            )

        # 缓存命中率建议
        if latest_metrics.cache_hit_ratio < self._thresholds["cache_hit_ratio_warning"]:
            recommendations.append(
                f"缓存命中率过低 ({latest_metrics.cache_hit_ratio:.1%})，考虑增加shared_buffers或优化查询"
            )

        # 死元组建议
        if latest_metrics.dead_tuples > self._thresholds["dead_tuples_warning"]:
            recommendations.append(f"死元组过多 ({latest_metrics.dead_tuples:,})，建议执行VACUUM")

        # 表大小建议
        for table_name, table_size in latest_metrics.table_size_mb.items():
            if table_size > 5000:  # 5GB警告阈值
                recommendations.append(f"表 {table_name} 过大 ({table_size:.1f}MB)，考虑分区或归档历史数据")

        # 索引建议
        total_index_size = sum(latest_metrics.index_size_mb.values())
        total_table_size = sum(latest_metrics.table_size_mb.values())

        if total_table_size > 0:
            index_ratio = total_index_size / total_table_size
            if index_ratio > 0.5:  # 索引大小超过表大小的50%
                recommendations.append(
                    f"索引总大小过大 ({total_index_size:.1f}MB / {total_table_size:.1f}MB = {index_ratio:.1%})，"
                    "检查是否有未使用的索引"
                )

        return recommendations

    async def _monitoring_loop(self, interval_seconds: int) -> None:
        """监控循环"""
        while self._running:
            try:
                await self.collect_metrics()
                await asyncio.sleep(interval_seconds)
            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error(f"监控循环异常: {e}")
                await asyncio.sleep(5)  # 短暂等待后继续

    async def _collect_connection_metrics(self, conn, metrics: DatabaseMetrics) -> None:
        """收集连接指标"""
        try:
            # 查询活动连接数
            result = await conn.fetchrow(
                """
                SELECT count(*) as active_count
                FROM pg_stat_activity
                WHERE state = 'active'
            """
            )
            metrics.active_connections = result["active_count"]

            # 查询总连接数
            result = await conn.fetchrow(
                """
                SELECT count(*) as total_count
                FROM pg_stat_activity
            """
            )
            metrics.total_connections = result["total_count"]

        except Exception as e:
            self.logger.warning(f"收集连接指标失败: {e}")

    async def _collect_storage_metrics(self, conn, metrics: DatabaseMetrics) -> None:
        """收集存储指标"""
        try:
            # 数据库总大小
            result = await conn.fetchrow(
                """
                SELECT pg_database_size(current_database()) / 1024 / 1024 as db_size_mb
            """
            )
            metrics.database_size_mb = result["db_size_mb"]

            # 表大小统计
            table_stats = await conn.fetch(
                """
                SELECT
                    schemaname,
                    tablename,
                    pg_total_relation_size(schemaname||'.'||tablename) / 1024 / 1024 as total_size_mb,
                    pg_relation_size(schemaname||'.'||tablename) / 1024 / 1024 as table_size_mb,
                    pg_indexes_size(schemaname||'.'||tablename) / 1024 / 1024 as indexes_size_mb
                FROM pg_stat_user_tables
                ORDER BY total_size_mb DESC
            """
            )

            for row in table_stats:
                table_name = f"{row['schemaname']}.{row['tablename']}"
                metrics.table_size_mb[table_name] = row["table_size_mb"]
                metrics.index_size_mb[table_name] = row["indexes_size_mb"]

        except Exception as e:
            self.logger.warning(f"收集存储指标失败: {e}")

    async def _collect_performance_metrics(self, conn, metrics: DatabaseMetrics) -> None:
        """收集性能指标"""
        try:
            # 缓存命中率
            result = await conn.fetchrow(
                """
                SELECT
                    sum(heap_blks_read) as heap_read,
                    sum(heap_blks_hit) as heap_hit,
                    CASE
                        WHEN sum(heap_blks_read) + sum(heap_blks_hit) > 0
                        THEN sum(heap_blks_hit)::NUMERIC / (sum(heap_blks_read) + sum(heap_blks_hit))
                        ELSE 0
                    END as cache_hit_ratio
                FROM pg_stat_database
                WHERE datname = current_database()
            """
            )
            metrics.cache_hit_ratio = result["cache_hit_ratio"]

            # 统计信息
            stats = await conn.fetchrow(
                """
                SELECT
                    sum(n_tup_ins) as total_inserts,
                    sum(n_tup_upd) as total_updates,
                    sum(n_tup_del) as total_deletes,
                    sum(n_dead_tup) as total_dead_tuples
                FROM pg_stat_user_tables
            """
            )

            metrics.rows_inserted = stats["total_inserts"]
            metrics.rows_updated = stats["total_updates"]
            metrics.rows_deleted = stats["total_deletes"]
            metrics.dead_tuples = stats["total_dead_tuples"]

            # VACUUM状态
            vacuum_result = await conn.fetchrow(
                """
                SELECT count(*) as pending_vacuums
                FROM pg_stat_user_tables
                WHERE last_vacuum < NOW() - INTERVAL '7 days'
            """
            )

            if vacuum_result["pending_vacuums"] > 0:
                metrics.vacuum_status = "needed"
            else:
                metrics.vacuum_status = "good"

        except Exception as e:
            self.logger.warning(f"收集性能指标失败: {e}")

    def _extract_index_usage(self, plan_data: dict[str, Any]) -> list[str]:
        """从执行计划中提取使用的索引"""
        indexes = []

        def extract_from_node(node):
            if isinstance(node, dict):
                if "Index Name" in node:
                    indexes.append(node["Index Name"])
                if "Plans" in node:
                    for plan in node["Plans"]:
                        extract_from_node(plan)

        extract_from_node(plan_data.get("Plan", {}))
        return list(set(indexes))

    def _generate_query_recommendations(self, plan_data: dict[str, Any], execution_time: float) -> list[str]:
        """生成查询优化建议"""
        recommendations = []

        # 执行时间建议
        if execution_time > self._thresholds["query_time_critical_ms"]:
            recommendations.append("查询执行时间过长，考虑添加索引或优化查询逻辑")
        elif execution_time > self._thresholds["query_time_warning_ms"]:
            recommendations.append("查询执行时间较长，建议进一步优化")

        # 扫描类型建议
        def check_scan_types(node):
            if isinstance(node, dict):
                scan_type = node.get("Node Type", "")
                if scan_type == "Seq Scan" and node.get("Actual Rows", 0) > 1000:
                    recommendations.append(f"发现全表扫描 ({scan_type})，建议添加适当的索引")
                elif scan_type == "Bitmap Heap Scan":
                    recommendations.append("使用了位图堆扫描，考虑优化索引或查询条件")

                if "Plans" in node:
                    for plan in node["Plans"]:
                        check_scan_types(plan)

        check_scan_types(plan_data.get("Plan", {}))

        return recommendations

    def _check_alerts(self, metrics: DatabaseMetrics) -> None:
        """检查告警条件"""
        # 连接数告警
        if metrics.active_connections >= self._thresholds["active_connections_critical"]:
            self._add_alert(
                "CRITICAL",
                "active_connections",
                metrics.active_connections,
                self._thresholds["active_connections_critical"],
                f"活跃连接数达到临界值: {metrics.active_connections}",
            )
        elif metrics.active_connections >= self._thresholds["active_connections_warning"]:
            self._add_alert(
                "WARNING",
                "active_connections",
                metrics.active_connections,
                self._thresholds["active_connections_warning"],
                f"活跃连接数过高: {metrics.active_connections}",
            )

        # 缓存命中率告警
        if metrics.cache_hit_ratio < self._thresholds["cache_hit_ratio_warning"]:
            self._add_alert(
                "WARNING",
                "cache_hit_ratio",
                metrics.cache_hit_ratio,
                self._thresholds["cache_hit_ratio_warning"],
                f"缓存命中率过低: {metrics.cache_hit_ratio:.1%}",
            )

        # 死元组告警
        if metrics.dead_tuples >= self._thresholds["dead_tuples_critical"]:
            self._add_alert(
                "CRITICAL",
                "dead_tuples",
                metrics.dead_tuples,
                self._thresholds["dead_tuples_critical"],
                f"死元组过多，需要立即VACUUM: {metrics.dead_tuples:,}",
            )
        elif metrics.dead_tuples >= self._thresholds["dead_tuples_warning"]:
            self._add_alert(
                "WARNING",
                "dead_tuples",
                metrics.dead_tuples,
                self._thresholds["dead_tuples_warning"],
                f"死元组较多，建议执行VACUUM: {metrics.dead_tuples:,}",
            )

    def _add_alert(
        self,
        level: str,
        metric_name: str,
        current_value: float,
        threshold_value: float,
        message: str,
    ) -> None:
        """添加告警"""
        alert = PerformanceAlert(
            level=level,
            metric_name=metric_name,
            current_value=current_value,
            threshold_value=threshold_value,
            message=message,
        )

        self._alerts.append(alert)

        # 限制告警历史数量
        if len(self._alerts) > 1000:
            self._alerts.pop(0)

        # 记录日志
        log_level = logging.WARNING if level == "WARNING" else logging.ERROR
        self.logger.log(log_level, f"[{level}] {message}")

    def get_recent_metrics(self, count: int = 10) -> list[DatabaseMetrics]:
        """获取最近的性能指标"""
        return self._metrics_history[-count:] if self._metrics_history else []

    def get_recent_alerts(self, hours: int = 24) -> list[PerformanceAlert]:
        """获取最近的告警"""
        cutoff_time = datetime.now() - timedelta(hours=hours)
        return [alert for alert in self._alerts if alert.timestamp >= cutoff_time]

    def get_performance_summary(self) -> dict[str, Any]:
        """获取性能摘要"""
        if not self._metrics_history:
            return {"status": "no_data"}

        latest = self._metrics_history[-1]
        recent_alerts = self.get_recent_alerts(24)

        return {
            "status": "active",
            "timestamp": latest.timestamp.isoformat(),
            "active_connections": latest.active_connections,
            "database_size_mb": latest.database_size_mb,
            "cache_hit_ratio": latest.cache_hit_ratio,
            "dead_tuples": latest.dead_tuples,
            "vacuum_status": latest.vacuum_status,
            "recent_alerts_count": len(recent_alerts),
            "critical_alerts_count": len([a for a in recent_alerts if a.level == "CRITICAL"]),
            "warning_alerts_count": len([a for a in recent_alerts if a.level == "WARNING"]),
        }


# 便捷函数
async def create_performance_monitor() -> DatabasePerformanceMonitor:
    """创建性能监控器"""
    monitor = DatabasePerformanceMonitor()
    await monitor.start_monitoring()
    return monitor
