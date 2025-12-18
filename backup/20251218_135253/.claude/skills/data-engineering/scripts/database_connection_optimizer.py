#!/usr/bin/env python3
"""
数据库连接优化器
专门为足球预测系统设计的数据库连接和查询优化工具
"""

import asyncio
import time
import logging
from typing import Dict, List, Any, Optional, Union
from dataclasses import dataclass
from contextlib import asynccontextmanager
import asyncpg
import aioredis
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy import text, select, insert, update, delete
from sqlalchemy.orm import selectinload
import pandas as pd
import json
from datetime import datetime, timedelta

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@dataclass
class ConnectionStats:
    """连接统计信息"""
    total_queries: int = 0
    successful_queries: int = 0
    failed_queries: int = 0
    total_time: float = 0.0
    avg_time: float = 0.0
    slow_queries: int = 0
    connection_errors: int = 0

class DatabaseConnectionOptimizer:
    """数据库连接优化器"""

    def __init__(
        self,
        database_url: str,
        redis_url: str = "redis://localhost:6379",
        pool_size: int = 20,
        max_overflow: int = 30,
        pool_timeout: int = 30,
        pool_recycle: int = 3600
    ):
        self.database_url = database_url
        self.redis_url = redis_url
        self.pool_size = pool_size
        self.max_overflow = max_overflow
        self.pool_timeout = pool_timeout
        self.pool_recycle = pool_recycle

        self.engine = None
        self.SessionLocal = None
        self.asyncpg_pool = None
        self.redis_pool = None
        self.stats = ConnectionStats()
        self.slow_query_threshold = 1.0  # 1秒

    async def initialize(self):
        """初始化连接池"""
        logger.info("🔧 初始化数据库连接优化器...")

        # 初始化SQLAlchemy异步引擎
        await self._initialize_sqlalchemy()

        # 初始化asyncpg连接池
        await self._initialize_asyncpg()

        # 初始化Redis连接池
        await self._initialize_redis()

        logger.info("✅ 所有连接池初始化完成")

    async def _initialize_sqlalchemy(self):
        """初始化SQLAlchemy异步引擎"""
        self.engine = create_async_engine(
            self.database_url,
            pool_size=self.pool_size,
            max_overflow=self.max_overflow,
            pool_timeout=self.pool_timeout,
            pool_recycle=self.pool_recycle,
            pool_pre_ping=True,  # 连接前检查
            echo=False,          # 生产环境关闭SQL日志
            future=True
        )

        self.SessionLocal = async_sessionmaker(
            self.engine,
            class_=AsyncSession,
            expire_on_commit=False
        )

        logger.info(f"📊 SQLAlchemy引擎已配置: pool_size={self.pool_size}, max_overflow={self.max_overflow}")

    async def _initialize_asyncpg(self):
        """初始化asyncpg连接池"""
        self.asyncpg_pool = await asyncpg.create_pool(
            self.database_url,
            min_size=5,
            max_size=self.pool_size,
            command_timeout=60,
            server_settings={
                'application_name': 'football_prediction_optimizer',
                'jit': 'off'  # 关闭JIT优化，提高简单查询性能
            }
        )

        logger.info(f"🐘 asyncpg连接池已配置: max_size={self.pool_size}")

    async def _initialize_redis(self):
        """初始化Redis连接池"""
        self.redis_pool = await aioredis.from_url(
            self.redis_url,
            max_connections=20,
            retry_on_timeout=True,
            socket_keepalive=True,
            socket_keepalive_options={}
        )

        # 测试Redis连接
        await self.redis_pool.ping()
        logger.info("🔴 Redis连接池已配置")

    @asynccontextmanager
    async def get_session(self):
        """获取SQLAlchemy会话"""
        async with self.SessionLocal() as session:
            try:
                yield session
            except Exception as e:
                await session.rollback()
                self.stats.failed_queries += 1
                raise
            finally:
                await session.close()

    @asynccontextmanager
    async def get_connection(self):
        """获取asyncpg连接"""
        async with self.asyncpg_pool.acquire() as conn:
            yield conn

    async def execute_query(
        self,
        query: str,
        params: Optional[Dict] = None,
        use_cache: bool = False,
        cache_ttl: int = 300
    ) -> Any:
        """执行查询并记录性能"""
        start_time = time.time()
        cache_key = None

        try:
            self.stats.total_queries += 1

            # 尝试从缓存获取
            if use_cache and self.redis_pool:
                cache_key = f"query:{hash(query)}:{hash(str(params))}"
                cached_result = await self.redis_pool.get(cache_key)
                if cached_result:
                    logger.debug(f"缓存命中: {cache_key}")
                    return json.loads(cached_result)

            # 执行查询
            async with self.get_connection() as conn:
                if params:
                    result = await conn.fetch(query, *params.values())
                else:
                    result = await conn.fetch(query)

            # 缓存结果
            if use_cache and self.redis_pool and cache_key:
                serialized_result = json.dumps([dict(row) for row in result], default=str)
                await self.redis_pool.setex(cache_key, cache_ttl, serialized_result)

            execution_time = time.time() - start_time
            self._update_stats(execution_time, success=True)

            logger.debug(f"查询执行成功: {execution_time:.3f}s")
            return result

        except Exception as e:
            execution_time = time.time() - start_time
            self._update_stats(execution_time, success=False)
            logger.error(f"查询执行失败: {str(e)}")
            raise

    async def batch_insert(
        self,
        table: str,
        data: List[Dict],
        batch_size: int = 1000,
        on_conflict: str = "DO NOTHING"
    ) -> int:
        """批量插入优化"""
        total_inserted = 0

        async with self.get_connection() as conn:
            await conn.execute("BEGIN")

            try:
                for i in range(0, len(data), batch_size):
                    batch = data[i:i + batch_size]
                    if not batch:
                        continue

                    # 构建批量插入SQL
                    columns = batch[0].keys()
                    placeholders = ', '.join([f'${j+1}' for j in range(len(columns))])
                    values_placeholders = ', '.join([f'({placeholders})' for _ in batch])

                    sql = f"""
                    INSERT INTO {table} ({', '.join(columns)})
                    VALUES {values_placeholders}
                    {on_conflict}
                    """

                    # 准备参数
                    flat_params = []
                    for row in batch:
                        flat_params.extend(row[col] for col in columns)

                    result = await conn.execute(sql, *flat_params)
                    batch_inserted = int(result.split()[-1]) if result else len(batch)
                    total_inserted += batch_inserted

                    logger.debug(f"批量插入批次 {i//batch_size + 1}: {batch_inserted} 行")

                await conn.execute("COMMIT")
                logger.info(f"批量插入完成: {total_inserted} 行")

            except Exception as e:
                await conn.execute("ROLLBACK")
                logger.error(f"批量插入失败: {str(e)}")
                raise

        return total_inserted

    async def optimized_match_query(
        self,
        team_ids: Optional[List[int]] = None,
        date_from: Optional[datetime] = None,
        date_to: Optional[datetime] = None,
        limit: int = 100
    ) -> List[Dict]:
        """优化的比赛查询"""
        conditions = []
        params = {}
        param_index = 1

        base_query = """
        SELECT
            m.id,
            m.home_team_id,
            m.away_team_id,
            m.home_score,
            m.away_score,
            m.date,
            ht.name as home_team_name,
            at.name as away_team_name,
            l.name as league_name
        FROM matches m
        JOIN teams ht ON m.home_team_id = ht.id
        JOIN teams at ON m.away_team_id = at.id
        JOIN leagues l ON m.league_id = l.id
        """

        # 添加条件
        if team_ids:
            conditions.append(f"(m.home_team_id = ANY(${param_index}) OR m.away_team_id = ANY(${param_index}))")
            params[param_index] = team_ids
            param_index += 1

        if date_from:
            conditions.append(f"m.date >= ${param_index}")
            params[param_index] = date_from
            param_index += 1

        if date_to:
            conditions.append(f"m.date <= ${param_index}")
            params[param_index] = date_to
            param_index += 1

        if conditions:
            base_query += " WHERE " + " AND ".join(conditions)

        base_query += f" ORDER BY m.date DESC LIMIT ${param_index}"
        params[param_index] = limit

        # 使用缓存
        return await self.execute_query(base_query, params, use_cache=True, cache_ttl=600)

    async def get_team_statistics(
        self,
        team_id: int,
        last_n_matches: int = 10
    ) -> Dict[str, Any]:
        """获取球队统计信息"""
        query = """
        WITH team_matches AS (
            SELECT
                CASE WHEN home_team_id = $1 THEN home_score ELSE away_score END AS goals_for,
                CASE WHEN home_team_id = $1 THEN away_score ELSE home_score END AS goals_against,
                CASE
                    WHEN (home_team_id = $1 AND home_score > away_score) OR
                         (away_team_id = $1 AND away_score > home_score) THEN 3
                    WHEN home_score = away_score THEN 1
                    ELSE 0
                END AS points,
                date
            FROM matches
            WHERE (home_team_id = $1 OR away_team_id = $1)
            AND date >= CURRENT_DATE - INTERVAL '365 days'
            ORDER BY date DESC
            LIMIT $2
        )
        SELECT
            COUNT(*) as matches_played,
            SUM(points) as total_points,
            SUM(goals_for) as goals_for,
            SUM(goals_against) as goals_against,
            COUNT(CASE WHEN points = 3 THEN 1 END) as wins,
            COUNT(CASE WHEN points = 1 THEN 1 END) as draws,
            COUNT(CASE WHEN points = 0 THEN 1 END) as losses,
            AVG(points) as avg_points
        FROM team_matches
        """

        return await self.execute_query(query, {"team_id": team_id, "limit": last_n_matches}, use_cache=True, cache_ttl=1800)

    async def get_connection_pool_stats(self) -> Dict[str, Any]:
        """获取连接池统计信息"""
        stats = {}

        # SQLAlchemy引擎统计
        if self.engine:
            pool = self.engine.pool
            stats["sqlalchemy"] = {
                "pool_size": pool.size(),
                "checked_in": pool.checkedin(),
                "checked_out": pool.checkedout(),
                "overflow": pool.overflow(),
                "invalid": pool.invalid()
            }

        # asyncpg连接池统计
        if self.asyncpg_pool:
            stats["asyncpg"] = {
                "pool_size": self.asyncpg_pool.get_size(),
                "pool_free": self.asyncpg_pool.get_idle_size(),
                "pool_used": self.asyncpg_pool.get_size() - self.asyncpg_pool.get_idle_size()
            }

        # Redis连接统计
        if self.redis_pool:
            try:
                redis_info = await self.redis_pool.info()
                stats["redis"] = {
                    "connected_clients": redis_info.get("connected_clients"),
                    "used_memory": redis_info.get("used_memory_human"),
                    "keyspace_hits": redis_info.get("keyspace_hits", 0),
                    "keyspace_misses": redis_info.get("keyspace_misses", 0)
                }
            except Exception as e:
                stats["redis"] = {"error": str(e)}

        return stats

    async def create_performance_indexes(self):
        """创建性能索引"""
        indexes = [
            # 比赛表索引
            "CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_matches_date ON matches(date)",
            "CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_matches_home_team ON matches(home_team_id, date)",
            "CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_matches_away_team ON matches(away_team_id, date)",
            "CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_matches_league_date ON matches(league_id, date)",
            "CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_matches_teams ON matches(home_team_id, away_team_id, date)",

            # 特征表索引
            "CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_match_features_match_id ON match_features(match_id)",
            "CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_match_features_type ON match_features(feature_type, match_id)",
            "CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_match_features_created_at ON match_features(created_at)",

            # 球队表索引
            "CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_teams_league ON teams(league_id)",
            "CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_teams_name ON teams(name)",
        ]

        async with self.get_connection() as conn:
            for index_sql in indexes:
                try:
                    await conn.execute(index_sql)
                    logger.info(f"索引创建成功: {index_sql.split('idx_')[1].split(' ')[0]}")
                except Exception as e:
                    logger.warning(f"索引创建失败: {str(e)}")

    async def analyze_slow_queries(self) -> List[Dict]:
        """分析慢查询"""
        # 检查是否有pg_stat_statements扩展
        check_query = """
        SELECT COUNT(*) FROM pg_extension WHERE extname = 'pg_stat_statements'
        """

        async with self.get_connection() as conn:
            extension_exists = await conn.fetchval(check_query)

            if not extension_exists:
                logger.warning("pg_stat_statements扩展未安装，无法分析慢查询")
                return []

            # 查询慢查询
            slow_query_sql = """
            SELECT
                query,
                calls,
                total_time,
                mean_time,
                rows,
                100.0 * shared_blks_hit /
                    nullif(shared_blks_hit + shared_blks_read, 0) AS hit_percent
            FROM pg_stat_statements
            WHERE mean_time > 1000  -- 平均时间超过1秒
            ORDER BY mean_time DESC
            LIMIT 20
            """

            return await conn.fetch(slow_query_sql)

    async def update_table_statistics(self):
        """更新表统计信息"""
        tables = [
            'matches', 'teams', 'leagues', 'match_features', 'predictions'
        ]

        async with self.get_connection() as conn:
            for table in tables:
                try:
                    await conn.execute(f"ANALYZE {table}")
                    logger.debug(f"统计信息已更新: {table}")
                except Exception as e:
                    logger.warning(f"更新统计信息失败 {table}: {str(e)}")

    async def health_check(self) -> Dict[str, Any]:
        """健康检查"""
        health_status = {
            "database": {"status": "unknown", "response_time": None},
            "redis": {"status": "unknown", "response_time": None},
            "connection_pools": {},
            "query_stats": self.stats.__dict__
        }

        # 数据库健康检查
        try:
            start_time = time.time()
            async with self.get_connection() as conn:
                await conn.fetchval("SELECT 1")
            response_time = time.time() - start_time
            health_status["database"] = {
                "status": "healthy",
                "response_time": f"{response_time:.3f}s"
            }
        except Exception as e:
            health_status["database"] = {
                "status": "unhealthy",
                "error": str(e)
            }

        # Redis健康检查
        try:
            start_time = time.time()
            await self.redis_pool.ping()
            response_time = time.time() - start_time
            health_status["redis"] = {
                "status": "healthy",
                "response_time": f"{response_time:.3f}s"
            }
        except Exception as e:
            health_status["redis"] = {
                "status": "unhealthy",
                "error": str(e)
            }

        # 连接池状态
        health_status["connection_pools"] = await self.get_connection_pool_stats()

        return health_status

    def _update_stats(self, execution_time: float, success: bool):
        """更新查询统计信息"""
        self.stats.total_time += execution_time
        self.stats.avg_time = self.stats.total_time / self.stats.total_queries

        if success:
            self.stats.successful_queries += 1
        else:
            self.stats.failed_queries += 1

        if execution_time > self.slow_query_threshold:
            self.stats.slow_queries += 1

    def get_performance_report(self) -> Dict[str, Any]:
        """获取性能报告"""
        return {
            "query_statistics": self.stats.__dict__,
            "slow_query_threshold": self.slow_query_threshold,
            "success_rate": (
                self.stats.successful_queries / self.stats.total_queries
                if self.stats.total_queries > 0 else 0
            ),
            "slow_query_rate": (
                self.stats.slow_queries / self.stats.total_queries
                if self.stats.total_queries > 0 else 0
            )
        }

    async def cleanup(self):
        """清理连接池"""
        logger.info("🧹 清理连接池...")

        if self.asyncpg_pool:
            await self.asyncpg_pool.close()

        if self.redis_pool:
            await self.redis_pool.close()

        if self.engine:
            await self.engine.dispose()

        logger.info("✅ 连接池清理完成")


# 全局实例
db_optimizer = None

async def get_database_optimizer() -> DatabaseConnectionOptimizer:
    """获取数据库优化器实例"""
    global db_optimizer
    if db_optimizer is None:
        db_optimizer = DatabaseConnectionOptimizer(
            database_url="postgresql://football_user:football_pass@localhost/football_prediction_dev",
            redis_url="redis://localhost:6379"
        )
        await db_optimizer.initialize()
    return db_optimizer


async def main():
    """主函数示例"""
    print("🔧 数据库连接优化器")
    print("=" * 50)

    optimizer = DatabaseConnectionOptimizer(
        database_url="postgresql://football_user:football_pass@localhost/football_prediction_dev",
        redis_url="redis://localhost:6379"
    )

    try:
        await optimizer.initialize()

        # 创建性能索引
        print("📊 创建性能索引...")
        await optimizer.create_performance_indexes()

        # 更新表统计信息
        print("📈 更新表统计信息...")
        await optimizer.update_table_statistics()

        # 执行示例查询
        print("🔍 执行优化查询...")
        matches = await optimizer.optimized_match_query(limit=5)
        print(f"查询到 {len(matches)} 场比赛")

        # 获取连接池统计
        print("📊 连接池统计:")
        pool_stats = await optimizer.get_connection_pool_stats()
        print(json.dumps(pool_stats, indent=2))

        # 健康检查
        print("💚 健康检查:")
        health = await optimizer.health_check()
        print(json.dumps(health, indent=2))

        # 性能报告
        print("📈 性能报告:")
        report = optimizer.get_performance_report()
        print(json.dumps(report, indent=2))

    finally:
        await optimizer.cleanup()


if __name__ == "__main__":
    asyncio.run(main())