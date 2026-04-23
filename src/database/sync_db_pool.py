#!/usr/bin/env python3
"""同步 PostgreSQL 连接池实现。"""

from __future__ import annotations

from contextlib import contextmanager
import logging
import threading
import time
from typing import TYPE_CHECKING, Any, cast

import psycopg2
from psycopg2 import pool as psycopg2_pool
from psycopg2.extras import RealDictCursor, RealDictRow

from src.database.db_pool_config import DatabasePoolConfig

if TYPE_CHECKING:
    from collections.abc import Iterator
    from types import TracebackType

logger = logging.getLogger(__name__)

_SYNC_POOL_HOLDER: dict[str, SyncDatabasePool | None] = {"pool": None}


class SyncDatabasePool:
    """
    同步数据库连接池管理器

    使用 psycopg2.pool.ThreadedConnectionPool 实现线程安全的连接池。
    适用于同步代码环境，如 data_pipeline_v25.py 等数据处理脚本。
    """

    _instance: SyncDatabasePool | None = None
    _lock = threading.Lock()

    def __init__(self, config: DatabasePoolConfig | None = None):
        """初始化同步数据库连接池。"""
        self.config = config or DatabasePoolConfig.from_url()
        self._pool: psycopg2_pool.ThreadedConnectionPool | None = None
        self._is_initialized = False
        self._stats: dict[str, Any] = {
            "total_connections_created": 0,
            "total_connections_acquired": 0,
            "total_connections_released": 0,
            "total_queries_executed": 0,
            "total_errors": 0,
            "pool_creation_time": None,
            "active_connections": 0,
        }
        self._connection_leak_threshold = 300

    @classmethod
    def get_instance(cls, config: DatabasePoolConfig | None = None) -> SyncDatabasePool:
        """获取同步数据库连接池单例实例。"""
        with cls._lock:
            if cls._instance is None:
                cls._instance = cls(config)
                logger.info("🔐 创建同步数据库连接池单例实例")
            return cls._instance

    def init_pool(self) -> None:
        """初始化连接池。"""
        if self._is_initialized and self._pool:
            return

        start_time = time.time()
        logger.info("🚀 开始初始化同步数据库连接池")
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
            sslmode = self.config.ssl_mode if self.config.ssl_mode else "require"
            logger.info("   SSL 模式: %s", sslmode)
            if sslmode.lower() == "disable":
                logger.warning("⚠️ SSL 已禁用 - 仅用于开发环境")

            self._pool = psycopg2_pool.ThreadedConnectionPool(
                minconn=self.config.min_size,
                maxconn=self.config.max_size,
                host=self.config.host,
                port=self.config.port,
                user=self.config.user,
                password=self.config.password,
                database=self.config.database,
                connect_timeout=int(self.config.timeout),
                sslmode=sslmode,
                sslcert=self.config.ssl_cert,
                sslkey=self.config.ssl_key,
                sslrootcert=self.config.ssl_root_cert,
            )

            self._is_initialized = True
            creation_time = time.time() - start_time
            self._stats["pool_creation_time"] = float(creation_time)
            logger.info("✅ 同步数据库连接池初始化成功 (耗时: %.2fs)", creation_time)
        except Exception:
            logger.exception("❌ 同步数据库连接池初始化失败")
            raise

    @contextmanager
    def get_connection(self) -> Iterator[psycopg2.extensions.connection]:
        """获取数据库连接的上下文管理器。"""
        if not self._is_initialized or not self._pool:
            raise RuntimeError("连接池未初始化，请先调用 init_pool()")

        conn = None
        try:
            conn = self._pool.getconn()
            self._stats["total_connections_acquired"] += 1
            self._stats["active_connections"] += 1

            with conn.cursor() as cursor:
                cursor.execute("SET timezone TO 'UTC'")
                cursor.execute("SET statement_timeout = '30s'")

            yield conn
        except Exception:
            self._stats["total_errors"] += 1
            logger.exception("数据库连接异常")
            raise
        finally:
            if conn:
                self._pool.putconn(conn)
                self._stats["total_connections_released"] += 1
                self._stats["active_connections"] -= 1

    @contextmanager
    def _connection_scope(
        self,
        conn: psycopg2.extensions.connection | None = None,
    ) -> Iterator[psycopg2.extensions.connection]:
        """统一管理可选外部连接，避免错误借还连接。"""
        if conn is not None:
            yield conn
            return

        with self.get_connection() as managed_conn:
            yield managed_conn

    def fetch_all(
        self,
        query: str,
        params: tuple[Any, ...] | None = None,
        conn: psycopg2.extensions.connection | None = None,
    ) -> list[RealDictRow]:
        """执行查询并返回所有结果。"""
        with self._connection_scope(conn) as active_conn:
            try:
                with active_conn.cursor(cursor_factory=RealDictCursor) as cursor:
                    cursor.execute(query, params)
                    result = cast("list[RealDictRow]", cursor.fetchall())
            except Exception:
                self._stats["total_errors"] += 1
                logger.exception("查询执行失败: %s", query)
                raise
            else:
                self._stats["total_queries_executed"] += 1
                return result

    def fetch_one(
        self,
        query: str,
        params: tuple[Any, ...] | None = None,
        conn: psycopg2.extensions.connection | None = None,
    ) -> RealDictRow | None:
        """执行查询并返回第一行结果。"""
        with self._connection_scope(conn) as active_conn:
            try:
                with active_conn.cursor(cursor_factory=RealDictCursor) as cursor:
                    cursor.execute(query, params)
                    result = cast("RealDictRow | None", cursor.fetchone())
            except Exception:
                self._stats["total_errors"] += 1
                logger.exception("查询执行失败: %s", query)
                raise
            else:
                self._stats["total_queries_executed"] += 1
                return result

    def execute(
        self,
        query: str,
        params: tuple[Any, ...] | None = None,
        conn: psycopg2.extensions.connection | None = None,
    ) -> str:
        """执行 SQL 语句（非查询）。"""
        with self._connection_scope(conn) as active_conn:
            try:
                with active_conn.cursor() as cursor:
                    cursor.execute(query, params)
                    active_conn.commit()
                    rowcount = cursor.rowcount
            except Exception:
                self._stats["total_errors"] += 1
                logger.exception("SQL执行失败: %s", query)
                active_conn.rollback()
                raise
            else:
                self._stats["total_queries_executed"] += 1
                return f"执行成功，影响 {rowcount} 行"

    def executemany(
        self,
        query: str,
        params_list: list[tuple[Any, ...]],
        conn: psycopg2.extensions.connection | None = None,
    ) -> str:
        """批量执行 SQL 语句。"""
        with self._connection_scope(conn) as active_conn:
            try:
                with active_conn.cursor() as cursor:
                    cursor.executemany(query, params_list)
                    active_conn.commit()
                    rowcount = cursor.rowcount
            except Exception:
                self._stats["total_errors"] += 1
                logger.exception("批量SQL执行失败: %s", query)
                active_conn.rollback()
                raise
            else:
                self._stats["total_queries_executed"] += len(params_list)
                return f"批量执行成功，影响 {rowcount} 行"

    def close(self) -> None:
        """关闭连接池。"""
        if self._pool:
            self._pool.closeall()
            self._is_initialized = False
            logger.info("🔒 同步数据库连接池已关闭")

    def get_stats(self) -> dict[str, Any]:
        """获取连接池统计信息。"""
        stats = self._stats.copy()
        if self._pool:
            stats.update(
                {
                    "pool_min_size": self.config.min_size,
                    "pool_max_size": self.config.max_size,
                    "estimated_active_connections": self._stats["active_connections"],
                }
            )

        return stats

    def get_pool_info(self) -> dict[str, Any]:
        """获取连接池信息。"""
        return {
            "is_initialized": self._is_initialized,
            "pool_type": "ThreadedConnectionPool",
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

    def __enter__(self) -> SyncDatabasePool:
        """上下文管理器入口。"""
        self.init_pool()
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> None:
        """上下文管理器出口。"""
        self.close()


def get_sync_db_pool(config: DatabasePoolConfig | None = None) -> SyncDatabasePool:
    """获取全局同步数据库连接池实例。"""
    pool = _SYNC_POOL_HOLDER["pool"]
    if pool is None:
        pool = SyncDatabasePool.get_instance(config)
        _SYNC_POOL_HOLDER["pool"] = pool
    return pool


def init_global_sync_db_pool(config: DatabasePoolConfig | None = None) -> SyncDatabasePool:
    """初始化全局同步数据库连接池。"""
    pool = get_sync_db_pool(config)
    pool.init_pool()
    return pool


def execute_sync_query(query: str, params: tuple[Any, ...] | None = None) -> str:
    """执行同步 SQL 语句的便捷函数。"""
    pool = get_sync_db_pool()
    return pool.execute(query, params)


def fetch_sync_all(query: str, params: tuple[Any, ...] | None = None) -> list[RealDictRow]:
    """执行同步查询的便捷函数。"""
    pool = get_sync_db_pool()
    return pool.fetch_all(query, params)


def fetch_sync_one(query: str, params: tuple[Any, ...] | None = None) -> RealDictRow | None:
    """执行同步单行查询的便捷函数。"""
    pool = get_sync_db_pool()
    return pool.fetch_one(query, params)
