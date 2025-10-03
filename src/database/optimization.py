"""
数据库优化模块
Database Optimization Module

提供数据库性能优化功能：
- 索引优化
- 查询优化
- 连接池优化
- 缓存策略
"""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Any
from sqlalchemy import text, Index, DDL
from sqlalchemy.orm import Session
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.sql import func
from src.database.connection import DatabaseManager
from src.cache.redis_manager import RedisManager

logger = logging.getLogger(__name__)


class DatabaseOptimizer:
    """数据库优化器"""

    def __init__(self, db_manager: DatabaseManager, redis_manager: Optional[RedisManager] = None):
        self.db_manager = db_manager
        self.redis_manager = redis_manager

    async def analyze_slow_queries(self, hours: int = 24) -> List[Dict[str, Any]]:
        """分析慢查询"""
        slow_queries = []

        # PostgreSQL慢查询分析
        sql = """
        SELECT
            query,
            calls,
            total_exec_time,
            mean_exec_time,
            rows,
            100.0 * shared_blks_hit / nullif(shared_blks_hit + shared_blks_read, 0) AS hit_percent
        FROM pg_stat_statements
        WHERE mean_exec_time > 100  -- 超过100ms的查询
        AND calls > 10  -- 至少调用10次
        ORDER BY mean_exec_time DESC
        LIMIT 20;
        """

        try:
            async with self.db_manager.get_async_session() as session:
                result = await session.execute(text(sql))
                for row in result:
                    slow_queries.append({
                        "query": row.query,
                        "calls": row.calls,
                        "total_time": float(row.total_exec_time),
                        "avg_time": float(row.mean_exec_time),
                        "rows": row.rows,
                        "cache_hit_rate": float(row.hit_percent) if row.hit_percent else 0
                    })
        except Exception as e:
            logger.warning(f"无法分析慢查询: {e}")
            # 可能pg_stat_statements未启用

        return slow_queries

    async def create_missing_indexes(self) -> List[str]:
        """创建缺失的索引"""
        created_indexes = []

        # 定义常用查询的索引
        indexes_to_create = [
            # 预测表索引
            {
                "name": "idx_predictions_match_model",
                "table": "predictions",
                "columns": ["match_id", "model_name"],
                "sql": "CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_predictions_match_model ON predictions(match_id, model_name)"
            },
            {
                "name": "idx_predictions_created_at",
                "table": "predictions",
                "columns": ["created_at"],
                "sql": "CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_predictions_created_at ON predictions(created_at DESC)"
            },
            {
                "name": "idx_predictions_confidence",
                "table": "predictions",
                "columns": ["confidence_score"],
                "sql": "CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_predictions_confidence ON predictions(confidence_score DESC)"
            },
            # 比赛表索引
            {
                "name": "idx_matches_date_status",
                "table": "matches",
                "columns": ["match_date", "status"],
                "sql": "CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_matches_date_status ON matches(match_date, status)"
            },
            {
                "name": "idx_matches_team_home",
                "table": "matches",
                "columns": ["home_team_id"],
                "sql": "CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_matches_team_home ON matches(home_team_id)"
            },
            {
                "name": "idx_matches_team_away",
                "table": "matches",
                "columns": ["away_team_id"],
                "sql": "CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_matches_team_away ON matches(away_team_id)"
            },
            # 审计日志索引
            {
                "name": "idx_audit_logs_timestamp_action",
                "table": "audit_logs",
                "columns": ["timestamp", "action"],
                "sql": "CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_audit_logs_timestamp_action ON audit_logs(timestamp DESC, action)"
            },
            # 特征数据索引
            {
                "name": "idx_features_match_type",
                "table": "features",
                "columns": ["match_id", "feature_type"],
                "sql": "CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_features_match_type ON features(match_id, feature_type)"
            }
        ]

        for index_info in indexes_to_create:
            try:
                async with self.db_manager.get_async_session() as session:
                    await session.execute(text(index_info["sql"]))
                    await session.commit()
                    created_indexes.append(index_info["name"])
                    logger.info(f"创建索引: {index_info['name']}")
            except Exception as e:
                logger.warning(f"创建索引失败 {index_info['name']}: {e}")

        return created_indexes

    async def analyze_index_usage(self) -> Dict[str, Any]:
        """分析索引使用情况"""
        index_stats = {}

        sql = """
        SELECT
            schemaname,
            tablename,
            indexname,
            idx_scan,
            idx_tup_read,
            idx_tup_fetch
        FROM pg_stat_user_indexes
        ORDER BY idx_scan DESC;
        """

        try:
            async with self.db_manager.get_async_session() as session:
                result = await session.execute(text(sql))
                for row in result:
                    index_name = f"{row.schemaname}.{row.tablename}.{row.indexname}"
                    index_stats[index_name] = {
                        "table": row.tablename,
                        "index": row.indexname,
                        "scans": row.idx_scan,
                        "tuples_read": row.idx_tup_read,
                        "tuples_fetched": row.idx_tup_fetch,
                        "efficiency": row.idx_tup_fetch / row.idx_tup_read if row.idx_tup_read > 0 else 0
                    }
        except Exception as e:
            logger.error(f"分析索引使用失败: {e}")

        return index_stats

    async def optimize_connection_pool(self, environment: str = "production") -> Dict[str, int]:
        """优化连接池配置"""
        if environment == "production":
            # 生产环境配置
            pool_config = {
                "pool_size": 20,  # 增加连接池大小
                "max_overflow": 30,  # 增加溢出连接
                "pool_timeout": 30,  # 获取连接超时时间
                "pool_recycle": 3600,  # 1小时回收连接
                "pool_pre_ping": True  # 连接前ping
            }
        elif environment == "development":
            # 开发环境配置
            pool_config = {
                "pool_size": 5,
                "max_overflow": 10,
                "pool_timeout": 10,
                "pool_recycle": 1800,  # 30分钟
                "pool_pre_ping": True
            }
        else:
            # 测试环境配置
            pool_config = {
                "pool_size": 1,
                "max_overflow": 0,
                "pool_timeout": 5,
                "pool_recycle": 300,
                "pool_pre_ping": True
            }

        # 重新初始化连接池
        try:
            config = self.db_manager._config
            if config:
                config.pool_size = pool_config["pool_size"]
                config.max_overflow = pool_config["max_overflow"]
                # 其他配置需要重新创建引擎
                logger.info(f"连接池配置已更新: {pool_config}")
        except Exception as e:
            logger.error(f"更新连接池配置失败: {e}")

        return pool_config

    async def cache_frequent_queries(self, ttl_seconds: int = 300) -> List[str]:
        """缓存频繁查询的结果"""
        cached_queries = []

        if not self.redis_manager:
            logger.warning("Redis管理器未初始化，跳过查询缓存")
            return cached_queries

        # 定义需要缓存的查询
        queries_to_cache = [
            {
                "key": "recent_predictions:limit_10",
                "sql": """
                SELECT p.*, m.home_team_id, m.away_team_id, m.match_date
                FROM predictions p
                JOIN matches m ON p.match_id = m.id
                ORDER BY p.created_at DESC
                LIMIT 10
                """,
                "ttl": ttl_seconds
            },
            {
                "key": "high_confidence_predictions:today",
                "sql": """
                SELECT p.*, m.home_team_id, m.away_team_id, m.match_date
                FROM predictions p
                JOIN matches m ON p.match_id = m.id
                WHERE p.confidence_score > 0.8
                AND DATE(m.match_date) = CURRENT_DATE
                ORDER BY p.confidence_score DESC
                LIMIT 20
                """,
                "ttl": ttl_seconds
            },
            {
                "key": "team_stats:home_team:7days",
                "sql": """
                SELECT
                    t.id as team_id,
                    t.name as team_name,
                    COUNT(m.id) as matches_count,
                    SUM(CASE WHEN m.home_score > m.away_score THEN 1 ELSE 0 END) as wins,
                    SUM(CASE WHEN m.home_score = m.away_score THEN 1 ELSE 0 END) as draws,
                    SUM(CASE WHEN m.home_score < m.away_score THEN 1 ELSE 0 END) as losses
                FROM teams t
                LEFT JOIN matches m ON (t.id = m.home_team_id OR t.id = m.away_team_id)
                WHERE m.match_date >= CURRENT_DATE - INTERVAL '7 days'
                AND m.status = 'completed'
                GROUP BY t.id, t.name
                """,
                "ttl": ttl_seconds * 2  # 统计数据缓存更久
            }
        ]

        for query_info in queries_to_cache:
            try:
                # 执行查询并缓存结果
                async with self.db_manager.get_async_session() as session:
                    result = await session.execute(text(query_info["sql"]))
                    data = [dict(row) for row in result]

                # 缓存到Redis
                await self.redis_manager.set_json(
                    query_info["key"],
                    data,
                    ttl=query_info["ttl"]
                )
                cached_queries.append(query_info["key"])
                logger.info(f"缓存查询: {query_info['key']}")

            except Exception as e:
                logger.error(f"缓存查询失败 {query_info['key']}: {e}")

        return cached_queries

    async def vacuum_and_analyze(self, table_name: Optional[str] = None) -> bool:
        """执行VACUUM和ANALYZE"""
        try:
            async with self.db_manager.get_async_session() as session:
                if table_name:
                    # 特定表
                    await session.execute(text(f"VACUUM ANALYZE {table_name}"))
                    logger.info(f"VACUUM ANALYZE 完成: {table_name}")
                else:
                    # 所有表
                    await session.execute(text("VACUUM ANALYZE"))
                    logger.info("VACUUM ANALYZE 完成: 所有表")
                await session.commit()
                return True
        except Exception as e:
            logger.error(f"VACUUM ANALYZE 失败: {e}")
            return False

    async def get_database_stats(self) -> Dict[str, Any]:
        """获取数据库统计信息"""
        stats = {}

        try:
            async with self.db_manager.get_async_session() as session:
                # 连接数统计
                result = await session.execute(text("""
                    SELECT count(*) as active_connections
                    FROM pg_stat_activity
                    WHERE state = 'active'
                """))
                stats["active_connections"] = result.scalar()

                # 数据库大小
                result = await session.execute(text("""
                    SELECT pg_size_pretty(pg_database_size(current_database())) as db_size
                """))
                stats["database_size"] = result.scalar()

                # 表大小统计
                result = await session.execute(text("""
                    SELECT
                        schemaname,
                        tablename,
                        pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) as size,
                        pg_total_relation_size(schemaname||'.'||tablename) as size_bytes
                    FROM pg_tables
                    WHERE schemaname = 'public'
                    ORDER BY pg_total_relation_size(schemaname||'.'||tablename) DESC
                    LIMIT 10
                """))
                stats["largest_tables"] = [
                    {
                        "schema": row.schemaname,
                        "table": row.tablename,
                        "size": row.size,
                        "size_bytes": row.size_bytes
                    }
                    for row in result
                ]

                # 缓存命中率
                result = await session.execute(text("""
                    SELECT
                        sum(heap_blks_read) as heap_read,
                        sum(heap_blks_hit) as heap_hit,
                        sum(heap_blks_hit) / nullif(sum(heap_blks_hit) + sum(heap_blks_read), 0) * 100 as cache_hit_rate
                    FROM pg_statio_user_tables
                """))
                row = result.first()
                if row:
                    stats["cache_hit_rate"] = float(row.cache_hit_rate) if row.cache_hit_rate else 0
                    stats["heap_reads"] = row.heap_read or 0
                    stats["heap_hits"] = row.heap_hit or 0

        except Exception as e:
            logger.error(f"获取数据库统计失败: {e}")

        return stats

    async def monitor_query_performance(self, query: str, threshold_ms: float = 100.0) -> Dict[str, Any]:
        """监控单个查询的性能"""
        performance_data = {}

        start_time = datetime.now()

        try:
            async with self.db_manager.get_async_session() as session:
                # 使用EXPLAIN ANALYZE分析查询
                explain_sql = f"EXPLAIN (ANALYZE, BUFFERS, FORMAT JSON) {query}"
                result = await session.execute(text(explain_sql))
                explain_data = result.scalar()

                # 解析执行计划
                if isinstance(explain_data, list) and len(explain_data) > 0:
                    plan = explain_data[0].get("Plan", {})
                    execution_time = explain_data[0].get("Execution Time", 0)
                    planning_time = explain_data[0].get("Planning Time", 0)

                    performance_data = {
                        "query": query,
                        "execution_time_ms": execution_time,
                        "planning_time_ms": planning_time,
                        "total_time_ms": execution_time + planning_time,
                        "exceeds_threshold": execution_time > threshold_ms,
                        "plan": plan,
                        "timestamp": start_time.isoformat()
                    }

                    # 记录慢查询
                    if execution_time > threshold_ms:
                        logger.warning(f"慢查询检测 ({execution_time:.2f}ms): {query[:100]}...")

        except Exception as e:
            logger.error(f"查询性能监控失败: {e}")
            performance_data = {
                "query": query,
                "error": str(e),
                "timestamp": start_time.isoformat()
            }

        return performance_data

    async def create_query_performance_report(self) -> Dict[str, Any]:
        """创建查询性能报告"""
        report = {
            "timestamp": datetime.now().isoformat(),
            "slow_queries": await self.analyze_slow_queries(),
            "database_stats": await self.get_database_stats(),
            "index_usage": await self.analyze_index_usage()
        }

        return report


class QueryOptimizer:
    """查询优化器"""

    @staticmethod
    def optimize_pagination(query: str, page: int, size: int) -> str:
        """优化分页查询"""
        offset = (page - 1) * size

        # 使用cursor-based pagination for large datasets
        if offset > 10000:
            # 对于大数据集，使用WHERE条件代替OFFSET
            optimized_query = f"""
            SELECT * FROM ({query}) t
            WHERE t.id > (SELECT id FROM ({query}) t2 ORDER BY id LIMIT 1 OFFSET {offset})
            ORDER BY id
            LIMIT {size}
            """
        else:
            optimized_query = f"{query} LIMIT {size} OFFSET {offset}"

        return optimized_query

    @staticmethod
    def add_query_hints(query: str, hints: List[str]) -> str:
        """添加查询提示"""
        if hints:
            hint_str = "/* " + " ".join(hints) + " */ "
            query = query.replace("SELECT", hint_str + "SELECT", 1)
        return query

    @staticmethod
    def batch_inserts(table_name: str, data: List[Dict], batch_size: int = 1000) -> List[str]:
        """批量插入优化"""
        queries = []

        for i in range(0, len(data), batch_size):
            batch = data[i:i + batch_size]
            columns = list(batch[0].keys())
            values_list = []

            for row in batch:
                values = []
                for col in columns:
                    val = row.get(col)
                    if isinstance(val, str):
                        escaped = val.replace("'", "''")
                        val = f"'{escaped}'"
                    elif val is None:
                        val = "NULL"
                    else:
                        val = str(val)
                    values.append(val)
                values_list.append(f"({', '.join(values)})")

            query = f"""
            INSERT INTO {table_name} ({', '.join(columns)})
            VALUES {', '.join(values_list)}
            ON CONFLICT DO NOTHING
            """
            queries.append(query)

        return queries
