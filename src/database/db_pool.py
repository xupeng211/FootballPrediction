#!/usr/bin/env python3
"""
V30.0 数据库连接池实现 (同步 + 异步双模支持)

提供企业级的PostgreSQL连接池管理，支持同步和异步两种模式。
采用单例模式确保全局唯一实例，支持连接池监控、自动重连、配置管理等功能。

主要特性:
- 同步连接池 (psycopg2.pool) - 高并发保护
- 异步连接池 (asyncpg) - 高性能异步
- 单例模式确保全局唯一连接池
- 环境变量配置加载
- 连接池健康检查
- 自动重连机制
- 连接泄漏检测
- 详细的性能监控和日志

使用示例 (同步):
    # 获取同步连接池实例
    pool = SyncDatabasePool.get_instance()
    pool.init_pool()

    # 执行SQL查询
    with pool.get_connection() as conn:
        rows = pool.fetch_all(conn, "SELECT * FROM matches WHERE id = %s", (match_id,))

使用示例 (异步):
    pool = await DatabasePool.get_instance()
    await pool.init_pool()
    result = await pool.execute("SELECT * FROM matches WHERE id = $1", match_id)
"""

import asyncio
from collections.abc import AsyncIterator
from contextlib import AbstractAsyncContextManager, asynccontextmanager, suppress
import logging
import ssl
import time
from types import TracebackType
from typing import Any, Optional, cast

import asyncpg
from asyncpg import Connection, Pool

from src.database.db_pool_config import ConfigError, DatabasePoolConfig
from src.database.sync_db_pool import (
    SyncDatabasePool,
    execute_sync_query,
    fetch_sync_all,
    fetch_sync_one,
    get_sync_db_pool,
    init_global_sync_db_pool,
)

logger = logging.getLogger(__name__)

__all__ = [
    "ConfigError",
    "DatabasePool",
    "DatabasePoolConfig",
    "SyncDatabasePool",
    "execute_query",
    "execute_sync_query",
    "fetch_query",
    "fetch_sync_all",
    "fetch_sync_one",
    "fetchrow_query",
    "fetchval_query",
    "get_db_pool",
    "get_sync_db_pool",
    "init_global_db_pool",
    "init_global_sync_db_pool",
]


class DatabasePool:
    """
    异步数据库连接池管理器

    采用单例模式确保整个应用只有一个连接池实例。
    提供企业级的连接池管理功能，包括健康检查、自动重连、性能监控等。
    """

    _instance: Optional["DatabasePool"] = None
    _lock = asyncio.Lock()

    def __init__(self, config: DatabasePoolConfig | None = None):
        """初始化数据库连接池

        Args:
            config: 数据库配置，如果为None则使用默认配置
        """
        self.config = config or DatabasePoolConfig.from_url()
        self._pool: Pool | None = None
        self._is_initialized = False
        self._health_check_task: asyncio.Task[None] | None = None

        # 统计信息
        self._stats: dict[str, Any] = {
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
    async def get_instance(cls, config: DatabasePoolConfig | None = None) -> "DatabasePool":
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
            return

        start_time = time.time()
        logger.info("🚀 开始初始化数据库连接池")
        logger.info(
            "   数据库: %s:%s/%s",
            self.config.host,
            self.config.port,
            self.config.database,
        )
        logger.info(
            "   连接池大小: %s-%s",
            self.config.min_size,
            self.config.max_size,
        )
        logger.info("   超时设置: %ss", self.config.timeout)

        try:
            # 构建 SSL 连接参数
            ssl_context = None
            if self.config.ssl_mode and self.config.ssl_mode.lower() != "disable":
                # V76.100: 创建 SSL 上下文 (使用 SSLContext 而不是 create_ssl_context)
                ssl_context = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
                ssl_context.check_hostname = False
                ssl_context.verify_mode = ssl.CERT_NONE

                # 如果提供了证书文件，使用它们
                if self.config.ssl_cert and self.config.ssl_key:
                    ssl_context.load_cert_chain(
                        certfile=self.config.ssl_cert,
                        keyfile=self.config.ssl_key,
                    )
                if self.config.ssl_root_cert:
                    ssl_context.load_verify_locations(cafile=self.config.ssl_root_cert)
                    ssl_context.verify_mode = ssl.CERT_REQUIRED

            # 记录 SSL 配置
            logger.info("   SSL 模式: %s", self.config.ssl_mode)
            if self.config.ssl_mode.lower() == "disable":
                logger.warning("⚠️ SSL 已禁用 - 仅用于开发环境")

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
                ssl=ssl_context,
            )

            self._is_initialized = True
            creation_time = time.time() - start_time
            self._stats["pool_creation_time"] = float(creation_time)

            logger.info("✅ 数据库连接池初始化成功 (耗时: %.2fs)", creation_time)

            # 启动健康检查任务
            await self._start_health_check()

        except Exception:
            logger.exception("❌ 数据库连接池初始化失败")
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

    def acquire(self) -> AbstractAsyncContextManager[Connection]:
        """
        从连接池获取连接

        Returns:
            AsyncContextManager[Connection]: 连接对象的上下文管理器
        """
        if not self._is_initialized or not self._pool:
            raise RuntimeError("连接池未初始化，请先调用 init_pool()")

        self._stats["total_connections_acquired"] += 1
        return cast("AbstractAsyncContextManager[Connection]", self._pool.acquire())

    @asynccontextmanager
    async def connection(self) -> AsyncIterator[Connection]:
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

    async def execute(self, query: str, *args: Any, timeout: float | None = None) -> str:
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
                result = cast("str", await conn.execute(query, *args, timeout=timeout))
            except Exception:
                self._stats["total_errors"] += 1
                logger.exception("SQL执行失败: %s", query)
                raise
            else:
                self._stats["total_queries_executed"] += 1
                return result

    async def executemany(
        self,
        query: str,
        args_list: list[tuple[Any, ...]],
        timeout: float | None = None,
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
                result = cast(
                    "str",
                    await conn.executemany(query, args_list, timeout=timeout),
                )
            except Exception:
                self._stats["total_errors"] += 1
                logger.exception("批量SQL执行失败: %s", query)
                raise
            else:
                self._stats["total_queries_executed"] += len(args_list)
                return result

    async def fetch(
        self, query: str, *args: Any, timeout: float | None = None
    ) -> list[asyncpg.Record]:
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
                result = cast(
                    "list[asyncpg.Record]",
                    await conn.fetch(query, *args, timeout=timeout),
                )
            except Exception:
                self._stats["total_errors"] += 1
                logger.exception("查询执行失败: %s", query)
                raise
            else:
                self._stats["total_queries_executed"] += 1
                return result

    async def fetchrow(
        self, query: str, *args: Any, timeout: float | None = None
    ) -> asyncpg.Record | None:
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
                result = cast(
                    "asyncpg.Record | None",
                    await conn.fetchrow(query, *args, timeout=timeout),
                )
            except Exception:
                self._stats["total_errors"] += 1
                logger.exception("查询执行失败: %s", query)
                raise
            else:
                self._stats["total_queries_executed"] += 1
                return result

    async def fetchval(
        self, query: str, *args: Any, column: int = 0, timeout: float | None = None
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
                result = await conn.fetchval(query, *args, column=column, timeout=timeout)
            except Exception:
                self._stats["total_errors"] += 1
                logger.exception("查询执行失败: %s", query)
                raise
            else:
                self._stats["total_queries_executed"] += 1
                return result

    async def close(self) -> None:
        """
        关闭连接池

        优雅地关闭连接池，释放所有连接
        """
        if self._health_check_task:
            self._health_check_task.cancel()
            with suppress(asyncio.CancelledError):
                await self._health_check_task

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
            except Exception:
                logger.exception("健康检查异常")

    async def _perform_health_check(self) -> None:
        """执行健康检查"""
        if not self._pool:
            return

        try:
            start_time = time.time()
            await self.fetchval("SELECT 1")
            time.time() - start_time

            self._stats["last_health_check"] = time.time()
            self._stats["health_check_count"] += 1

        except Exception:
            logger.exception("💔 健康检查失败")

    def get_stats(self) -> dict[str, Any]:
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

    def get_pool_info(self) -> dict[str, Any]:
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

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> None:
        """异步上下文管理器出口"""
        await self.close()


_ASYNC_POOL_HOLDER: dict[str, DatabasePool | None] = {"pool": None}


async def get_db_pool(config: DatabasePoolConfig | None = None) -> DatabasePool:
    """
    获取全局数据库连接池实例

    这是推荐的获取连接池的方式

    Args:
        config: 数据库配置，仅在首次创建时使用

    Returns:
        DatabasePool: 连接池实例
    """
    pool = _ASYNC_POOL_HOLDER["pool"]
    if pool is None:
        pool = await DatabasePool.get_instance(config)
        _ASYNC_POOL_HOLDER["pool"] = pool
    return pool


async def init_global_db_pool(
    config: DatabasePoolConfig | None = None,
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
async def execute_query(query: str, *args: Any) -> str:
    """执行SQL语句的便捷函数"""
    pool = await get_db_pool()
    return await pool.execute(query, *args)


async def fetch_query(query: str, *args: Any) -> list[asyncpg.Record]:
    """执行查询的便捷函数"""
    pool = await get_db_pool()
    return await pool.fetch(query, *args)


async def fetchrow_query(query: str, *args: Any) -> asyncpg.Record | None:
    """执行单行查询的便捷函数"""
    pool = await get_db_pool()
    return await pool.fetchrow(query, *args)


async def fetchval_query(query: str, *args: Any) -> Any:
    """执行单值查询的便捷函数"""
    pool = await get_db_pool()
    return await pool.fetchval(query, *args)
