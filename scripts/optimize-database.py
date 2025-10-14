#!/usr/bin/env python3
"""
数据库性能优化脚本
自动创建索引、优化查询和分析性能
"""

import asyncio
import logging
import time
from typing import List, Dict, Any
from pathlib import Path
import asyncpg
import sqlalchemy as sa
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

from src.core.logging import get_logger
from src.core.config import get_settings
from src.database.base import Base
from src.database.models import Match, Prediction, User, Team

logger = get_logger(__name__)


class DatabaseOptimizer:
    """数据库优化器"""

    def __init__(self):
        self.settings = get_settings()
        self.engine = None
        self.session_factory = None

    async def initialize(self):
        """初始化数据库连接"""
        self.engine = create_async_engine(
            self.settings.database_url,
            pool_size=20,
            max_overflow=30,
            pool_pre_ping=True,
            pool_recycle=3600,
            echo=False,
        )

        self.session_factory = sessionmaker(
            self.engine, class_=AsyncSession, expire_on_commit=False
        )

    async def analyze_tables(self) -> List[Dict[str, Any]]:
        """分析表统计信息"""
        logger.info("开始分析表统计信息...")

        tables = [
            "matches",
            "predictions",
            "users",
            "teams",
            "odds",
            "audit_logs",
            "data_collection_logs",
            "features",
        ]

        results = []

        async with self.session_factory() as session:
            for table in tables:
                try:
                    # 更新表统计信息
                    await session.execute(text(f"ANALYZE {table}"))

                    # 获取表统计信息
                    result = await session.execute(
                        text(
                            f"""
                            SELECT
                                schemaname,
                                tablename,
                                n_tup_ins as inserts,
                                n_tup_upd as updates,
                                n_tup_del as deletes,
                                n_live_tup as live_tuples,
                                n_dead_tup as dead_tuples,
                                last_vacuum,
                                last_autovacuum,
                                last_analyze,
                                last_autoanalyze
                            FROM pg_stat_user_tables
                            WHERE tablename = '{table}'
                        """
                        )
                    )

                    stats = result.fetchone()
                    if stats:
                        results.append(
                            {
                                "table": table,
                                "live_tuples": stats.live_tuples,
                                "dead_tuples": stats.dead_tuples,
                                "last_analyze": stats.last_autoanalyze
                                or stats.last_analyze,
                            }
                        )

                        logger.info(
                            f"表 {table} 分析完成",
                            live_tuples=stats.live_tuples,
                            dead_tuples=stats.dead_tuples,
                        )

                except Exception as e:
                    logger.error(f"分析表 {table} 失败", error=str(e))

        return results

    async def create_indexes(self) -> List[Dict[str, Any]]:
        """创建性能优化索引"""
        logger.info("开始创建优化索引...")

        index_definitions = [
            # 比赛表索引
            {
                "table": "matches",
                "name": "idx_matches_date_status",
                "sql": "CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_matches_date_status ON matches (match_date, status)",
                "description": "按日期和状态查询比赛",
            },
            {
                "table": "matches",
                "name": "idx_matches_team_competition",
                "sql": "CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_matches_team_competition ON matches (home_team_id, away_team_id, competition_id)",
                "description": "按球队和比赛查询",
            },
            {
                "table": "matches",
                "name": "idx_matches_season",
                "sql": "CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_matches_season ON matches (season, competition_id)",
                "description": "按赛季和比赛查询",
            },
            # 预测表索引
            {
                "table": "predictions",
                "name": "idx_predictions_match_user",
                "sql": "CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_predictions_match_user ON predictions (match_id, user_id)",
                "description": "按比赛和用户查询预测",
            },
            {
                "table": "predictions",
                "name": "idx_predictions_created",
                "sql": "CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_predictions_created ON predictions (created_at DESC)",
                "description": "按创建时间查询预测",
            },
            {
                "table": "predictions",
                "name": "idx_predictions_status",
                "sql": "CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_predictions_status ON predictions (status, created_at)",
                "description": "按状态和时间查询预测",
            },
            # 用户表索引
            {
                "table": "users",
                "name": "idx_users_email",
                "sql": "CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_users_email ON users (email)",
                "description": "按邮箱查询用户",
            },
            {
                "table": "users",
                "name": "idx_users_active",
                "sql": "CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_users_active ON users (is_active, created_at)",
                "description": "按活跃状态查询用户",
            },
            # 赔率表索引
            {
                "table": "odds",
                "name": "idx_odds_match_bookmaker",
                "sql": "CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_odds_match_bookmaker ON odds (match_id, bookmaker_id)",
                "description": "按比赛和博彩公司查询赔率",
            },
            {
                "table": "odds",
                "name": "idx_odds_updated",
                "sql": "CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_odds_updated ON odds (updated_at DESC)",
                "description": "按更新时间查询赔率",
            },
            # 审计日志索引
            {
                "table": "audit_logs",
                "name": "idx_audit_logs_user_action",
                "sql": "CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_audit_logs_user_action ON audit_logs (user_id, action, created_at)",
                "description": "按用户和操作查询审计日志",
            },
            {
                "table": "audit_logs",
                "name": "idx_audit_logs_timestamp",
                "sql": "CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_audit_logs_timestamp ON audit_logs (created_at DESC)",
                "description": "按时间查询审计日志",
            },
            # 特征表索引
            {
                "table": "features",
                "name": "idx_features_match",
                "sql": "CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_features_match ON features (match_id, feature_type)",
                "description": "按比赛和特征类型查询",
            },
            {
                "table": "features",
                "name": "idx_features_computed",
                "sql": "CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_features_computed ON features (computed_at DESC)",
                "description": "按计算时间查询特征",
            },
        ]

        results = []

        async with self.session_factory() as session:
            for index_def in index_definitions:
                try:
                    start_time = time.time()

                    # 检查索引是否已存在
                    check_result = await session.execute(
                        text(
                            f"""
                            SELECT indexname
                            FROM pg_indexes
                            WHERE tablename = '{index_def['table']}'
                            AND indexname = '{index_def['name']}'
                        """
                        )
                    )

                    if not check_result.fetchone():
                        # 创建索引
                        await session.execute(text(index_def["sql"]))
                        await session.commit()

                        duration = time.time() - start_time
                        results.append(
                            {
                                "table": index_def["table"],
                                "index": index_def["name"],
                                "status": "created",
                                "duration": duration,
                                "description": index_def["description"],
                            }
                        )

                        logger.info(
                            "索引创建成功",
                            table=index_def["table"],
                            index=index_def["name"],
                            duration=duration,
                        )
                    else:
                        results.append(
                            {
                                "table": index_def["table"],
                                "index": index_def["name"],
                                "status": "exists",
                                "description": index_def["description"],
                            }
                        )

                        logger.info("索引已存在", index=index_def["name"])

                except Exception as e:
                    await session.rollback()
                    logger.error(
                        "创建索引失败",
                        table=index_def["table"],
                        index=index_def["name"],
                        error=str(e),
                    )
                    results.append(
                        {
                            "table": index_def["table"],
                            "index": index_def["name"],
                            "status": "error",
                            "error": str(e),
                        }
                    )

        return results

    async def vacuum_tables(self) -> List[Dict[str, Any]]:
        """清理表（VACUUM）"""
        logger.info("开始执行VACUUM操作...")

        tables = [
            "matches",
            "predictions",
            "users",
            "teams",
            "odds",
            "audit_logs",
            "data_collection_logs",
            "features",
        ]

        results = []

        # 使用独立的连接执行VACUUM（不能在事务中）
        async with self.engine.connect() as conn:
            for table in tables:
                try:
                    start_time = time.time()

                    # 执行VACUUM ANALYZE
                    await conn.execute(text(f"VACUUM ANALYZE {table}"))

                    duration = time.time() - start_time
                    results.append(
                        {
                            "table": table,
                            "operation": "vacuum_analyze",
                            "status": "success",
                            "duration": duration,
                        }
                    )

                    logger.info("VACUUM完成", table=table, duration=duration)

                except Exception as e:
                    logger.error("VACUUM失败", table=table, error=str(e))
                    results.append(
                        {
                            "table": table,
                            "operation": "vacuum_analyze",
                            "status": "error",
                            "error": str(e),
                        }
                    )

        return results

    async def check_slow_queries(self) -> List[Dict[str, Any]]:
        """检查慢查询"""
        logger.info("检查慢查询...")

        async with self.session_factory() as session:
            # 查询慢查询统计
            result = await session.execute(
                text(
                    """
                SELECT
                    query,
                    calls,
                    total_exec_time,
                    mean_exec_time,
                    rows,
                    100.0 * shared_blks_hit / nullif(shared_blks_hit + shared_blks_read, 0) AS hit_percent
                FROM pg_stat_statements
                WHERE mean_exec_time > 100  -- 超过100ms的查询
                ORDER BY mean_exec_time DESC
                LIMIT 20
            """
                )
            )

            slow_queries = []
            for row in result.fetchall():
                slow_queries.append(
                    {
                        "query": row.query[:200] + "..."
                        if len(row.query) > 200
                        else row.query,
                        "calls": row.calls,
                        "total_time": row.total_exec_time,
                        "mean_time": row.mean_exec_time,
                        "rows": row.rows,
                        "hit_percent": row.hit_percent,
                    }
                )

            logger.info(f"发现 {len(slow_queries)} 个慢查询")
            return slow_queries

    async def optimize_table_partitions(self):
        """优化表分区（如果使用了分区）"""
        logger.info("检查表分区...")

        # 这里可以添加分区表的优化逻辑
        # 例如：创建新的分区、删除旧分区等

        async with self.session_factory() as session:
            # 检查是否有分区表
            result = await session.execute(
                text(
                    """
                SELECT
                    schemaname,
                    tablename,
                    partitioned
                FROM pg_tables
                WHERE partitioned = true
            """
                )
            )

            partitioned_tables = result.fetchall()

            if partitioned_tables:
                logger.info(f"发现 {len(partitioned_tables)} 个分区表")

                for table in partitioned_tables:
                    # 检查分区情况
                    partitions = await session.execute(
                        text(
                            f"""
                        SELECT
                            schemaname,
                            tablename,
                            pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) as size
                        FROM pg_partitions
                        WHERE tablename = '{table.tablename}'
                    """
                        )
                    )

                    logger.info(
                        f"分区表 {table.tablename} 的分区情况",
                        partitions=partitions.fetchall(),
                    )
            else:
                logger.info("未发现分区表")

    async def get_database_stats(self) -> Dict[str, Any]:
        """获取数据库统计信息"""
        logger.info("获取数据库统计信息...")

        async with self.session_factory() as session:
            # 数据库大小
            db_size = await session.execute(
                text(
                    """
                SELECT pg_size_pretty(pg_database_size(current_database()))
            """
                )
            )

            # 表大小统计
            table_sizes = await session.execute(
                text(
                    """
                SELECT
                    schemaname,
                    tablename,
                    pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) as size,
                    pg_size_pretty(pg_relation_size(schemaname||'.'||tablename)) as table_size,
                    pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename) - pg_relation_size(schemaname||'.'||tablename)) as index_size
                FROM pg_tables
                WHERE schemaname = 'public'
                ORDER BY pg_total_relation_size(schemaname||'.'||tablename) DESC
                LIMIT 10
            """
                )
            )

            # 连接统计
            connections = await session.execute(
                text(
                    """
                SELECT
                    state,
                    count(*) as connections
                FROM pg_stat_activity
                GROUP BY state
            """
                )
            )

            # 锁等待统计
            lock_waits = await session.execute(
                text(
                    """
                SELECT
                    waiting.locktype,
                    waiting.mode,
                    waiting.pid as waiting_pid,
                    other.pid as blocking_pid,
                    other.query as blocking_query
                FROM pg_locks AS waiting
                JOIN pg_stat_activity AS waiting_act ON waiting.pid = waiting_act.pid
                JOIN pg_locks AS other ON (
                    waiting.locktype = other.locktype
                    AND waiting.database IS NOT DISTINCT FROM other.database
                    AND waiting.relation IS NOT DISTINCT FROM other.relation
                    AND waiting.page IS NOT DISTINCT FROM other.page
                    AND waiting.tuple IS NOT DISTINCT FROM other.tuple
                    AND waiting.virtualxid IS NOT DISTINCT FROM other.virtualxid
                    AND waiting.transactionid IS NOT DISTINCT FROM other.transactionid
                    AND waiting.classid IS NOT DISTINCT FROM other.classid
                    AND waiting.objid IS NOT DISTINCT FROM other.objid
                    AND waiting.objsubid IS NOT DISTINCT FROM other.objsubid
                    AND waiting.pid != other.pid
                )
                JOIN pg_stat_activity AS other ON other.pid = other.pid
                WHERE NOT waiting.granted
                AND other.granted
            """
                )
            )

            return {
                "database_size": db_size.scalar(),
                "table_sizes": [dict(row) for row in table_sizes.fetchall()],
                "connections": [dict(row) for row in connections.fetchall()],
                "lock_waits": [dict(row) for row in lock_waits.fetchall()],
                "total_connections": sum(
                    row.connections for row in connections.fetchall()
                ),
            }

    async def run_full_optimization(self) -> Dict[str, Any]:
        """运行完整的数据库优化"""
        logger.info("开始数据库完整优化...")

        results = {"start_time": time.time(), "steps": {}}

        try:
            # 1. 分析表
            results["steps"]["analyze"] = await self.analyze_tables()

            # 2. 创建索引
            results["steps"]["indexes"] = await self.create_indexes()

            # 3. VACUUM操作
            results["steps"]["vacuum"] = await self.vacuum_tables()

            # 4. 检查慢查询
            results["steps"]["slow_queries"] = await self.check_slow_queries()

            # 5. 优化分区
            await self.optimize_table_partitions()

            # 6. 获取统计信息
            results["stats"] = await self.get_database_stats()

            results["end_time"] = time.time()
            results["duration"] = results["end_time"] - results["start_time"]
            results["status"] = "success"

            logger.info("数据库优化完成", duration=results["duration"])

        except Exception as e:
            logger.error("数据库优化失败", error=str(e))
            results["status"] = "error"
            results["error"] = str(e)

        return results

    async def close(self):
        """关闭数据库连接"""
        if self.engine:
            await self.engine.dispose()


async def main():
    """主函数"""
    optimizer = DatabaseOptimizer()

    try:
        await optimizer.initialize()

        # 运行优化
        results = await optimizer.run_full_optimization()

        # 打印结果
        print("\n" + "=" * 60)
        print("数据库优化报告")
        print("=" * 60)

        print(f"\n优化状态: {results['status']}")
        print(f"总耗时: {results.get('duration', 0):.2f}秒")

        if "stats" in results:
            stats = results["stats"]
            print(f"\n数据库大小: {stats['database_size']}")
            print(f"总连接数: {stats['total_connections']}")

            print("\n前10大表:")
            for table in stats["table_sizes"][:5]:
                print(
                    f"  - {table['tablename']}: {table['size']} (索引: {table['index_size']})"
                )

        if "slow_queries" in results["steps"]:
            slow_queries = results["steps"]["slow_queries"]
            if slow_queries:
                print(f"\n发现 {len(slow_queries)} 个慢查询:")
                for query in slow_queries[:5]:
                    print(f"  - 平均耗时: {query['mean_time']:.2f}ms")
                    print(f"    查询: {query['query']}")

        print("\n索引创建情况:")
        for index in results["steps"].get("indexes", []):
            status_icon = "✓" if index["status"] == "created" else "○"
            print(f"  {status_icon} {index['index']} on {index['table']}")

        print("\n" + "=" * 60)

    except Exception as e:
        logger.error("优化过程出错", error=str(e))
    finally:
        await optimizer.close()


if __name__ == "__main__":
    asyncio.run(main())
