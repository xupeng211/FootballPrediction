#!/usr/bin/env python3
"""
异步数据库连接池实现

提供企业级的异步PostgreSQL连接池管理，采用单例模式确保全局唯一实例。
支持连接池监控、自动重连、配置管理等功能。

主要特性:
- 单例模式确保全局唯一连接池
- 异步连接池管理 (基于asyncpg)
- 环境变量配置加载
- 连接池健康检查
- 自动重连机制
- 详细的性能监控和日志

使用示例:
    # 获取连接池实例
    pool = DatabasePool.get_instance()

    # 初始化连接池
    await pool.init_pool()

    # 执行SQL查询
    result = await pool.execute("SELECT * FROM matches WHERE id = $1", match_id)

    # 或者使用上下文管理器
    async with pool.acquire() as conn:
        rows = await conn.fetch("SELECT * FROM teams")
"""

import asyncio
import os
import logging
import time
import urllib.parse
from typing import Optional, Dict, Any, List, AsyncContextManager
from contextlib import asynccontextmanager
from dataclasses import dataclass, field
import asyncpg
from asyncpg import Connection, Pool

logger = logging.getLogger(__name__)


@dataclass
class DatabasePoolConfig:
    """数据库连接池配置类

    所有配置项都支持从环境变量加载，提供合理的默认值
    """

    # 基本连接配置
    host: str = field(default_factory=lambda: os.getenv("DB_HOST", "localhost"))
    port: int = field(default_factory=lambda: int(os.getenv("DB_PORT", "5432")))
    user: str = field(default_factory=lambda: os.getenv("DB_USER", "postgres"))
    password: str = field(default_factory=lambda: os.getenv("DB_PASSWORD", "postgres"))
    database: str = field(
        default_factory=lambda: os.getenv("DB_NAME", "football_prediction")
    )

    # 连接池配置
    min_size: int = field(
        default_factory=lambda: int(os.getenv("DB_POOL_MIN_SIZE", "5"))
    )
    max_size: int = field(
        default_factory=lambda: int(os.getenv("DB_POOL_MAX_SIZE", "20"))
    )
    max_queries: int = field(
        default_factory=lambda: int(os.getenv("DB_POOL_MAX_QUERIES", "50000"))
    )
    max_inactive_connection_lifetime: float = field(
        default_factory=lambda: float(
            os.getenv("DB_POOL_MAX_INACTIVE_LIFETIME", "300.0")
        )
    )

    # 超时配置
    timeout: float = field(
        default_factory=lambda: float(os.getenv("DB_TIMEOUT", "60.0"))
    )
    command_timeout: float = field(
        default_factory=lambda: float(os.getenv("DB_COMMAND_TIMEOUT", "30.0"))
    )

    # 健康检查配置
    health_check_interval: float = field(
        default_factory=lambda: float(os.getenv("DB_HEALTH_CHECK_INTERVAL", "30.0"))
    )
    health_check_timeout: float = field(
        default_factory=lambda: float(os.getenv("DB_HEALTH_CHECK_TIMEOUT", "5.0"))
    )

    # 重连配置
    max_retries: int = field(
        default_factory=lambda: int(os.getenv("DB_MAX_RETRIES", "3"))
    )
    retry_delay: float = field(
        default_factory=lambda: float(os.getenv("DB_RETRY_DELAY", "1.0"))
    )

    @classmethod
    def from_url(cls, db_url: Optional[str] = None) -> "DatabasePoolConfig":
        """从数据库URL创建配置对象

        Args:
            db_url: 数据库连接URL，如果为None则从环境变量获取

        Returns:
            DatabasePoolConfig: 配置对象
        """
        if db_url is None:
            db_url = os.getenv(
                "DATABASE_URL",
                "postgresql+asyncpg://football_user:football_pass@db:5432/football_prediction_dev",
            )

        # 解析数据库URL
        parsed = urllib.parse.urlparse(
            db_url.replace("postgresql+asyncpg://", "postgresql://")
        )

        return cls(
            host=parsed.hostname or "localhost",
            port=parsed.port or 5432,
            user=parsed.username or "postgres",
            password=parsed.password or "postgres",
            database=parsed.path.lstrip("/") or "football_prediction",
        )


class DatabasePool:
    """
    异步数据库连接池管理器

    采用单例模式确保整个应用只有一个连接池实例。
    提供企业级的连接池管理功能，包括健康检查、自动重连、性能监控等。
    """

    _instance: Optional["DatabasePool"] = None
    _lock = asyncio.Lock()

    def __init__(self, config: Optional[DatabasePoolConfig] = None):
        """初始化数据库连接池

        Args:
            config: 数据库配置，如果为None则使用默认配置
        """
        self.config = config or DatabasePoolConfig.from_url()
        self._pool: Optional[Pool] = None
        self._is_initialized = False
        self._health_check_task: Optional[asyncio.Task] = None

        # 统计信息
        self._stats = {
            "total_connections_created": 0,
            "total_connections_acquired": 0,
            "total_connections_released": 0,
            "total_queries_executed": 0,
            "total_errors": 0,
            "pool_creation_time": None,
            "last_health_check": None,
            "health_check_count": 0,
        }

    @classmethod
    async def get_instance(
        cls, config: Optional[DatabasePoolConfig] = None
    ) -> "DatabasePool":
        """
        获取数据库连接池单例实例

        Args:
            config: 数据库配置，仅在首次创建时使用

        Returns:
            DatabasePool: 连接池实例
        """
        async with cls._lock:
            if cls._instance is None:
                cls._instance = cls(config)
                logger.info("🔐 创建数据库连接池单例实例")
            return cls._instance

    async def init_pool(self) -> None:
        """
        初始化连接池

        创建asyncpg连接池，设置健康检查任务。
        如果连接池已经初始化，则直接返回。

        Raises:
            asyncpg.PostgresError: 数据库连接错误
        """
        if self._is_initialized and self._pool:
            logger.debug("📦 连接池已经初始化，跳过重复初始化")
            return

        start_time = time.time()
        logger.info("🚀 开始初始化数据库连接池")
        logger.info(
            f"   数据库: {self.config.host}:{self.config.port}/{self.config.database}"
        )
        logger.info(f"   连接池大小: {self.config.min_size}-{self.config.max_size}")
        logger.info(f"   超时设置: {self.config.timeout}s")

        try:
            self._pool = await asyncpg.create_pool(
                host=self.config.host,
                port=self.config.port,
                user=self.config.user,
                password=self.config.password,
                database=self.config.database,
                min_size=self.config.min_size,
                max_size=self.config.max_size,
                max_queries=self.config.max_queries,
                max_inactive_connection_lifetime=self.config.max_inactive_connection_lifetime,
                timeout=self.config.timeout,
                command_timeout=self.config.command_timeout,
                setup=self._setup_connection,
                init=self._init_connection,
            )

            self._is_initialized = True
            creation_time = time.time() - start_time
            self._stats["pool_creation_time"] = creation_time

            logger.info(f"✅ 数据库连接池初始化成功 (耗时: {creation_time:.2f}s)")

            # 启动健康检查任务
            await self._start_health_check()

        except Exception as e:
            logger.error(f"❌ 数据库连接池初始化失败: {e}")
            raise

    async def _setup_connection(self, conn: Connection) -> None:
        """
        连接设置回调函数

        在每个连接创建时调用，用于设置连接参数

        Args:
            conn: 数据库连接对象
        """
        # 设置连接参数
        await conn.execute("SET timezone TO 'UTC'")
        await conn.execute("SET statement_timeout = '30s'")
        self._stats["total_connections_created"] += 1

    async def _init_connection(self, conn: Connection) -> None:
        """
        连接初始化回调函数

        在连接从池中获取时调用
        """
        # 可以在这里添加连接验证逻辑

    async def acquire(self) -> AsyncContextManager[Connection]:
        """
        从连接池获取连接

        Returns:
            AsyncContextManager[Connection]: 连接对象的上下文管理器
        """
        if not self._is_initialized or not self._pool:
            raise RuntimeError("连接池未初始化，请先调用 init_pool()")

        self._stats["total_connections_acquired"] += 1
        return self._pool.acquire()

    @asynccontextmanager
    async def connection(self) -> Connection:
        """
        获取数据库连接的上下文管理器

        这是最推荐的获取连接的方式，确保连接自动释放

        Yields:
            Connection: 数据库连接对象
        """
        async with self.acquire() as conn:
            try:
                yield conn
            finally:
                self._stats["total_connections_released"] += 1

    async def execute(self, query: str, *args, timeout: Optional[float] = None) -> str:
        """
        执行SQL语句（非查询）

        Args:
            query: SQL语句
            *args: SQL参数
            timeout: 执行超时时间

        Returns:
            str: 执行结果描述
        """
        async with self.connection() as conn:
            try:
                result = await conn.execute(query, *args, timeout=timeout)
                self._stats["total_queries_executed"] += 1
                return result
            except Exception as e:
                self._stats["total_errors"] += 1
                logger.error(f"SQL执行失败: {query} - {e}")
                raise

    async def executemany(
        self, query: str, args_list: List[tuple], timeout: Optional[float] = None
    ) -> str:
        """
        批量执行SQL语句

        Args:
            query: SQL语句
            args_list: 参数列表
            timeout: 执行超时时间

        Returns:
            str: 执行结果描述
        """
        async with self.connection() as conn:
            try:
                result = await conn.executemany(query, args_list, timeout=timeout)
                self._stats["total_queries_executed"] += len(args_list)
                return result
            except Exception as e:
                self._stats["total_errors"] += 1
                logger.error(f"批量SQL执行失败: {query} - {e}")
                raise

    async def fetch(
        self, query: str, *args, timeout: Optional[float] = None
    ) -> List[asyncpg.Record]:
        """
        执行查询并返回所有结果

        Args:
            query: SQL查询语句
            *args: 查询参数
            timeout: 执行超时时间

        Returns:
            List[asyncpg.Record]: 查询结果列表
        """
        async with self.connection() as conn:
            try:
                result = await conn.fetch(query, *args, timeout=timeout)
                self._stats["total_queries_executed"] += 1
                return result
            except Exception as e:
                self._stats["total_errors"] += 1
                logger.error(f"查询执行失败: {query} - {e}")
                raise

    async def fetchrow(
        self, query: str, *args, timeout: Optional[float] = None
    ) -> Optional[asyncpg.Record]:
        """
        执行查询并返回第一行结果

        Args:
            query: SQL查询语句
            *args: 查询参数
            timeout: 执行超时时间

        Returns:
            Optional[asyncpg.Record]: 查询结果的第一行，如果没有结果则返回None
        """
        async with self.connection() as conn:
            try:
                result = await conn.fetchrow(query, *args, timeout=timeout)
                self._stats["total_queries_executed"] += 1
                return result
            except Exception as e:
                self._stats["total_errors"] += 1
                logger.error(f"查询执行失败: {query} - {e}")
                raise

    async def fetchval(
        self, query: str, *args, column: int = 0, timeout: Optional[float] = None
    ) -> Any:
        """
        执行查询并返回单个值

        Args:
            query: SQL查询语句
            *args: 查询参数
            column: 要返回的列索引
            timeout: 执行超时时间

        Returns:
            Any: 查询结果的单个值
        """
        async with self.connection() as conn:
            try:
                result = await conn.fetchval(
                    query, *args, column=column, timeout=timeout
                )
                self._stats["total_queries_executed"] += 1
                return result
            except Exception as e:
                self._stats["total_errors"] += 1
                logger.error(f"查询执行失败: {query} - {e}")
                raise

    async def close(self) -> None:
        """
        关闭连接池

        优雅地关闭连接池，释放所有连接
        """
        if self._health_check_task:
            self._health_check_task.cancel()
            try:
                await self._health_check_task
            except asyncio.CancelledError:
                pass

        if self._pool:
            await self._pool.close()
            self._is_initialized = False
            logger.info("🔒 数据库连接池已关闭")

    async def _start_health_check(self) -> None:
        """启动健康检查任务"""
        if self._health_check_task:
            return

        self._health_check_task = asyncio.create_task(self._health_check_loop())
        logger.info("🏥 数据库连接池健康检查任务已启动")

    async def _health_check_loop(self) -> None:
        """健康检查循环"""
        while self._is_initialized:
            try:
                await asyncio.sleep(self.config.health_check_interval)
                await self._perform_health_check()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"健康检查异常: {e}")

    async def _perform_health_check(self) -> None:
        """执行健康检查"""
        if not self._pool:
            return

        try:
            start_time = time.time()
            await self.fetchval("SELECT 1")
            check_time = time.time() - start_time

            self._stats["last_health_check"] = time.time()
            self._stats["health_check_count"] += 1

            logger.debug(f"💓 健康检查通过 (耗时: {check_time:.3f}s)")

        except Exception as e:
            logger.error(f"💔 健康检查失败: {e}")

    def get_stats(self) -> Dict[str, Any]:
        """
        获取连接池统计信息

        Returns:
            Dict[str, Any]: 统计信息字典
        """
        stats = self._stats.copy()

        if self._pool:
            stats.update(
                {
                    "pool_size": self._pool.get_size(),
                    "pool_min_size": self._pool.get_min_size(),
                    "pool_max_size": self._pool.get_max_size(),
                    "pool_idle_connections": self._pool.get_idle_size(),
                    "pool_max_queries_per_connection": self._pool.get_max_queries(),
                    "pool_max_inactive_lifetime": self._pool.get_max_inactive_connection_lifetime(),
                }
            )

        return stats

    def get_pool_info(self) -> Dict[str, Any]:
        """
        获取连接池信息

        Returns:
            Dict[str, Any]: 连接池信息
        """
        return {
            "is_initialized": self._is_initialized,
            "config": {
                "host": self.config.host,
                "port": self.config.port,
                "database": self.config.database,
                "min_size": self.config.min_size,
                "max_size": self.config.max_size,
                "timeout": self.config.timeout,
            },
            "stats": self.get_stats(),
        }

    async def __aenter__(self) -> "DatabasePool":
        """异步上下文管理器入口"""
        await self.init_pool()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        """异步上下文管理器出口"""
        await self.close()


# 全局连接池实例
_global_pool: Optional[DatabasePool] = None


async def get_db_pool(config: Optional[DatabasePoolConfig] = None) -> DatabasePool:
    """
    获取全局数据库连接池实例

    这是推荐的获取连接池的方式

    Args:
        config: 数据库配置，仅在首次创建时使用

    Returns:
        DatabasePool: 连接池实例
    """
    global _global_pool
    if _global_pool is None:
        _global_pool = await DatabasePool.get_instance(config)
    return _global_pool


async def init_global_db_pool(
    config: Optional[DatabasePoolConfig] = None,
) -> DatabasePool:
    """
    初始化全局数据库连接池

    Args:
        config: 数据库配置

    Returns:
        DatabasePool: 初始化后的连接池实例
    """
    pool = await get_db_pool(config)
    await pool.init_pool()
    return pool


# 便捷函数，用于快速执行SQL
async def execute_query(query: str, *args) -> str:
    """执行SQL语句的便捷函数"""
    pool = await get_db_pool()
    return await pool.execute(query, *args)


async def fetch_query(query: str, *args) -> List[asyncpg.Record]:
    """执行查询的便捷函数"""
    pool = await get_db_pool()
    return await pool.fetch(query, *args)


async def fetchrow_query(query: str, *args) -> Optional[asyncpg.Record]:
    """执行单行查询的便捷函数"""
    pool = await get_db_pool()
    return await pool.fetchrow(query, *args)


async def fetchval_query(query: str, *args) -> Any:
    """执行单值查询的便捷函数"""
    pool = await get_db_pool()
    return await pool.fetchval(query, *args)
