"""
数据库性能优化
Database Performance Optimizations

提供数据库层面的性能优化,包括索引优化,查询优化,
连接池优化等.
"""

import asyncio
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime, timedelta
from dataclasses import dataclass

from sqlalchemy import text, Index, func
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker
from sqlalchemy.orm import selectinload, joinedload
from sqlalchemy.sql import Select

from src.database.base import get_db_session
from src.database.models import Match, Predictions, User, Tenant, Odds, Team
from src.core.config import get_settings


@dataclass
class OptimizationResult:
    """优化结果"""
    success: bool
    operation: str
    execution_time_ms: float
    affected_rows: int = 0
    details: Optional[Dict[str, Any]] = None
    error_message: Optional[str] = None


class DatabaseOptimizer:
    """
    数据库优化器

    提供数据库性能优化功能,包括索引管理,查询优化,
    数据清理等
    """

    def __init__(self, db_session: AsyncSession):
        self.db = db_session
        self.settings = get_settings()

    # ==================== 索引优化 ====================

    async def create_performance_indexes(self) -> List[OptimizationResult]:
        """创建性能优化索引"""
        results = []

        # 预测表索引
        prediction_indexes = [
            # 复合索引用于常见查询
            "CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_predictions_tenant_created ON predictions(tenant_id, created_at DESC)",
            "CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_predictions_match_created ON predictions(match_id, created_at DESC)",
            "CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_predictions_status_confidence ON predictions(status, confidence)",
            "CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_predictions_user_created ON predictions(user_id, created_at DESC)",

            # 部分索引用于活跃数据
            "CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_predictions_active ON predictions(match_id, created_at) WHERE status = 'pending'",
            "CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_predictions_high_confidence ON predictions(match_id, confidence) WHERE confidence > 0.8",
        ]

        # 比赛表索引
        match_indexes = [
            "CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_matches_tenant_status_date ON matches(tenant_id, status, match_date)",
            "CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_matches_team_status ON matches(home_team_id, status) WHERE status IN ('scheduled', 'live')",
            "CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_matches_date_range ON matches(match_date) WHERE match_date > NOW() - INTERVAL '30 days'",
            "CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_matches_league_date ON matches(league_id, match_date DESC)",
        ]

        # 用户表索引
        user_indexes = [
            "CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_users_tenant_active ON users(tenant_id, is_active)",
            "CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_users_role_created ON users(role, created_at DESC)",
            "CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_users_last_login ON users(last_login DESC) WHERE last_login IS NOT NULL",
        ]

        # 赔率表索引
        odds_indexes = [
            "CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_odds_match_bookmaker ON odds(match_id, bookmaker_id)",
            "CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_odds_market_updated ON odds(market_type, updated_at DESC)",
            "CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_odds_value ON odds(value) WHERE value > 1.0",
        ]

        # 执行索引创建
        all_indexes = prediction_indexes + match_indexes + user_indexes + odds_indexes
        for index_sql in all_indexes:
            result = await self._execute_sql(index_sql, f"创建索引: {index_sql[:50]}...")
            results.append(result)

        return results

    async def analyze_index_usage(self) -> Dict[str, Any]:
        """分析索引使用情况"""
        # 查询索引使用统计
        index_usage_query = """
        SELECT
            schemaname,
            tablename,
            indexname,
            idx_scan,
            idx_tup_read,
            idx_tup_fetch,
            pg_size_pretty(pg_relation_size(indexname::regclass)) as index_size
        FROM pg_stat_user_indexes
        WHERE schemaname = 'public'
        ORDER BY idx_scan DESC;
        """

        unused_indexes_query = """
        SELECT
            schemaname,
            tablename,
            indexname,
            pg_size_pretty(pg_relation_size(indexname::regclass)) as index_size
        FROM pg_stat_user_indexes
        WHERE idx_scan = 0
        AND schemaname = 'public'
        ORDER BY pg_relation_size(indexname::regclass) DESC;
        """

        try:
            # 执行查询
            index_usage_result = await self.db.execute(text(index_usage_query))
            unused_indexes_result = await self.db.execute(text(unused_indexes_query))

            index_usage = [dict(row._mapping) for row in index_usage_result.fetchall()]
            unused_indexes = [dict(row._mapping) for row in unused_indexes_result.fetchall()]

            return {
                "index_usage": index_usage,
                "unused_indexes": unused_indexes,
                "total_indexes": len(index_usage),
                "unused_count": len(unused_indexes)
            }

        except Exception as e:
            return {
                "error": str(e),
                "index_usage": [],
                "unused_indexes": [],
                "total_indexes": 0,
                "unused_count": 0
            }

    async def drop_unused_indexes(self) -> List[OptimizationResult]:
        """删除未使用的索引"""
        results = []

        # 获取未使用的索引
        analysis = await self.analyze_index_usage()
        unused_indexes = analysis.get("unused_indexes", [])

        for index_info in unused_indexes:
            # 只删除非主键和非唯一索引
            index_name = index_info["index_name"]
            table_name = index_info["table_name"]

            # 检查是否可以安全删除
            can_drop = await self._can_drop_index_safely(index_name, table_name)

            if can_drop:
                drop_sql = f"DROP INDEX CONCURRENTLY IF EXISTS {index_name}"
                result = await self._execute_sql(drop_sql, f"删除未使用索引: {index_name}")
                results.append(result)

        return results

    # ==================== 查询优化 ====================

    async def optimize_prediction_queries(self) -> List[OptimizationResult]:
        """优化预测相关查询"""
        results = []

        # 创建物化视图用于预测统计
        materialized_views = [
            """
            CREATE MATERIALIZED VIEW IF NOT EXISTS mv_prediction_stats AS
            SELECT
                tenant_id,
                DATE_TRUNC('day', created_at) as date,
                COUNT(*) as total_predictions,
                COUNT(CASE WHEN status = 'completed' THEN 1 END) as completed_predictions,
                COUNT(CASE WHEN status = 'pending' THEN 1 END) as pending_predictions,
                AVG(confidence) as avg_confidence,
                MAX(confidence) as max_confidence,
                MIN(confidence) as min_confidence
            FROM predictions
            WHERE created_at >= NOW() - INTERVAL '90 days'
            GROUP BY tenant_id, DATE_TRUNC('day', created_at);
            """,

            """
            CREATE MATERIALIZED VIEW IF NOT EXISTS mv_match_predictions_summary AS
            SELECT
                m.id as match_id,
                m.tenant_id,
                COUNT(p.id) as prediction_count,
                AVG(p.confidence) as avg_confidence,
                MAX(p.confidence) as max_confidence,
                COUNT(CASE WHEN p.status = 'completed' THEN 1 END) as completed_count
            FROM matches m
            LEFT JOIN predictions p ON m.id = p.match_id
            WHERE m.match_date >= NOW() - INTERVAL '30 days'
            GROUP BY m.id, m.tenant_id;
            """
        ]

        # 创建索引
        view_indexes = [
            "CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_mv_prediction_stats_tenant_date ON mv_prediction_stats(tenant_id, date)",
            "CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_mv_match_predictions_match ON mv_match_predictions_summary(match_id)",
        ]

        # 执行物化视图创建
        for view_sql in materialized_views:
            result = await self._execute_sql(view_sql, "创建物化视图")
            results.append(result)

        # 执行索引创建
        for index_sql in view_indexes:
            result = await self._execute_sql(index_sql, "创建物化视图索引")
            results.append(result)

        return results

    async def refresh_materialized_views(self) -> List[OptimizationResult]:
        """刷新物化视图"""
        views = ["mv_prediction_stats", "mv_match_predictions_summary"]
        results = []

        for view in views:
            refresh_sql = f"REFRESH MATERIALIZED VIEW CONCURRENTLY {view}"
            result = await self._execute_sql(refresh_sql, f"刷新物化视图: {view}")
            results.append(result)

        return results

    # ==================== 数据清理和归档 ====================

    async def cleanup_old_data(self, days_to_keep: int = 90) -> List[OptimizationResult]:
        """清理旧数据"""
        results = []

        # 清理旧的预测记录
        cleanup_predictions = f"""
        DELETE FROM predictions
        WHERE created_at < NOW() - INTERVAL '{days_to_keep} days'
        AND status IN ('completed', 'failed')
        RETURNING id;
        """

        # 清理旧的日志记录
        cleanup_logs = f"""
        DELETE FROM audit_logs
        WHERE created_at < NOW() - INTERVAL '{days_to_keep} days'
        RETURNING id;
        """

        # 清理旧的会话记录
        cleanup_sessions = """
        DELETE FROM user_sessions
        WHERE expires_at < NOW() - INTERVAL '7 days'
        RETURNING id;
        """

        cleanup_operations = [
            ("清理旧预测记录", cleanup_predictions),
            ("清理旧审计日志", cleanup_logs),
            ("清理过期会话", cleanup_sessions)
        ]

        for operation_name, cleanup_sql in cleanup_operations:
            result = await self._execute_sql(cleanup_sql, operation_name)
            results.append(result)

        return results

    async def archive_historical_data(self, archive_months: int = 12) -> OptimizationResult:
        """归档历史数据"""
        archive_sql = f"""
        -- 创建归档表（如果不存在）
        CREATE TABLE IF NOT EXISTS predictions_archive (
            LIKE predictions INCLUDING ALL
        );

        -- 归档旧数据
        WITH archived_data AS (
            DELETE FROM predictions
            WHERE created_at < NOW() - INTERVAL '{archive_months} months'
            RETURNING *
        )
        INSERT INTO predictions_archive
        SELECT * FROM archived_data;
        """

        return await self._execute_sql(archive_sql, f"归档{archive_months}个月的历史数据")

    # ==================== 连接池优化 ====================

    async def analyze_connection_pool(self) -> Dict[str, Any]:
        """分析连接池状态"""
        pool_stats_query = """
        SELECT
            state,
            COUNT(*) as connection_count,
            AVG(EXTRACT(EPOCH FROM (NOW() - query_start))) as avg_query_duration
        FROM pg_stat_activity
        WHERE datname = current_database()
        GROUP BY state;
        """

        active_queries_query = """
        SELECT
            query,
            EXTRACT(EPOCH FROM (NOW() - query_start)) as duration_seconds,
            usename,
            application_name
        FROM pg_stat_activity
        WHERE state = 'active'
        AND query != '<IDLE>'
        ORDER BY duration_seconds DESC
        LIMIT 10;
        """

        try:
            pool_stats_result = await self.db.execute(text(pool_stats_query))
            active_queries_result = await self.db.execute(text(active_queries_query))

            pool_stats = [dict(row._mapping) for row in pool_stats_result.fetchall()]
            active_queries = [dict(row._mapping) for row in active_queries_result.fetchall()]

            return {
                "connection_pool_stats": pool_stats,
                "active_queries": active_queries,
                "total_connections": sum(stat["connection_count"] for stat in pool_stats)
            }

        except Exception as e:
            return {
                "error": str(e),
                "connection_pool_stats": [],
                "active_queries": [],
                "total_connections": 0
            }

    async def optimize_connection_settings(self) -> Dict[str, Any]:
        """优化连接设置"""
        # 这里可以根据实际需要调整连接池参数
        # 返回建议的配置
        return {
            "recommended_settings": {
                "pool_size": 20,
                "max_overflow": 30,
                "pool_timeout": 30,
                "pool_recycle": 3600,
                "pool_pre_ping": True
            },
            "current_settings": {
                # 这里应该从配置中获取当前设置
            }
        }

    # ==================== 表空间和分区优化 ====================

    async def analyze_table_sizes(self) -> List[Dict[str, Any]]:
        """分析表大小"""
        table_sizes_query = """
        SELECT
            schemaname,
            tablename,
            pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) as total_size,
            pg_size_pretty(pg_relation_size(schemaname||'.'||tablename)) as table_size,
            pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename) - pg_relation_size(schemaname||'.'||tablename)) as index_size,
            n_tup_ins as inserts,
            n_tup_upd as updates,
            n_tup_del as deletes,
            n_live_tup as live_tuples,
            n_dead_tup as dead_tuples
        FROM pg_stat_user_tables
        WHERE schemaname = 'public'
        ORDER BY pg_total_relation_size(schemaname||'.'||tablename) DESC;
        """

        try:
            result = await self.db.execute(text(table_sizes_query))
            return [dict(row._mapping) for row in result.fetchall()]
        except Exception as e:
            return [{"error": str(e)}]

    async def optimize_large_tables(self) -> List[OptimizationResult]:
        """优化大表"""
        results = []

        # 分析表大小
        table_sizes = await self.analyze_table_sizes()
        large_tables = [
            table for table in table_sizes
            if "total_size" in table and any(
                unit in table["total_size"] for unit in ["GB", "1000MB"]
            )
        ]

        for table in large_tables:
            if "error" in table:
                continue

            table_name = table["tablename"]

            # 执行VACUUM和ANALYZE
            vacuum_result = await self._execute_sql(
                f"VACUUM ANALYZE {table_name}",
                f"清理表: {table_name}"
            )
            results.append(vacuum_result)

            # 如果死元组过多,建议执行VACUUM FULL
            live_tuples = table.get("live_tuples", 0)
            dead_tuples = table.get("dead_tuples", 0)

            if dead_tuples > live_tuples * 0.2:  # 死元组超过20%
                # 注意:VACUUM FULL会锁表,应该在维护窗口执行
                results.append(OptimizationResult(
                    success=False,
                    operation=f"建议对表 {table_name} 执行 VACUUM FULL",
                    execution_time_ms=0,
                    details={"dead_tuples": dead_tuples, "live_tuples": live_tuples}
                ))

        return results

    # ==================== 私有辅助方法 ====================

    async def _execute_sql(self, sql: str, operation_name: str) -> OptimizationResult:
        """执行SQL语句"""
        start_time = datetime.now()

        try:
            result = await self.db.execute(text(sql))
            await self.db.commit()

            execution_time = (datetime.now() - start_time).total_seconds() * 1000
            affected_rows = result.rowcount if hasattr(result, 'rowcount') else 0

            return OptimizationResult(
                success=True,
                operation=operation_name,
                execution_time_ms=execution_time,
                affected_rows=affected_rows
            )

        except Exception as e:
            await self.db.rollback()
            execution_time = (datetime.now() - start_time).total_seconds() * 1000

            return OptimizationResult(
                success=False,
                operation=operation_name,
                execution_time_ms=execution_time,
                error_message=str(e)
            )

    async def _can_drop_index_safely(self, index_name: str, table_name: str) -> bool:
        """检查是否可以安全删除索引"""
        # 检查是否是主键或唯一约束
        constraint_query = """
        SELECT conname, contype
        FROM pg_constraint
        WHERE conindid = (
            SELECT oid FROM pg_class WHERE relname = :index_name
        );
        """

        try:
            result = await self.db.execute(
                text(constraint_query),
                {"index_name": index_name}
            )
            constraints = result.fetchall()

            # 如果索引被约束使用,不能删除
            if constraints:
                return False

            # 检查索引名称模式
            unsafe_patterns = ["_pkey", "_unique", "_key"]
            for pattern in unsafe_patterns:
                if pattern in index_name.lower():
                    return False

            return True

            except Exception:
            return False


# ==================== 性能优化工厂 ====================

class DatabaseOptimizerFactory:
    """数据库优化器工厂"""

    @staticmethod
    async def create_optimizer() -> DatabaseOptimizer:
        """创建数据库优化器实例"""
        async with get_db_session() as db:
            return DatabaseOptimizer(db)

    @staticmethod
    async def run_full_optimization() -> Dict[str, Any]:
        """运行完整的数据库优化"""
        results = {
            "index_optimization": [],
            "query_optimization": [],
            "cleanup_optimization": [],
            "table_optimization": [],
            "analysis_results": {}
        }

        async with get_db_session() as db:
            optimizer = DatabaseOptimizer(db)

            try:
                # 1. 索引优化
                results["index_optimization"] = await optimizer.create_performance_indexes()

                # 2. 查询优化
                results["query_optimization"] = await optimizer.optimize_prediction_queries()

                # 3. 数据清理
                results["cleanup_optimization"] = await optimizer.cleanup_old_data()

                # 4. 表优化
                results["table_optimization"] = await optimizer.optimize_large_tables()

                # 5. 分析结果
                results["analysis_results"] = {
                    "index_usage": await optimizer.analyze_index_usage(),
                    "connection_pool": await optimizer.analyze_connection_pool(),
                    "table_sizes": await optimizer.analyze_table_sizes()
                }

                # 6. 刷新物化视图
                await optimizer.refresh_materialized_views()

            except Exception as e:
                results["error"] = str(e)

        return results