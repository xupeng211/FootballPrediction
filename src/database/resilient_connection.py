#!/usr/bin/env python3
"""V144.8 Resilient Database Connection Module.

Provides connection resilience with:
- Automatic retry mechanism (3 attempts, 5s delay)
- Heartbeat check before operations
- Connection pool management
- WSL2 bridge support

Author: V144.8 SRE Team
Version: 1.0.0
Date: 2026-01-06
"""

import asyncio
import logging
import time
from typing import Any, Callable

import psycopg2
from psycopg2 import OperationalError
from psycopg2.extensions import connection

from src.config_unified import get_settings

logger = logging.getLogger(__name__)


# ============================================================================
# V144.8: Database Connection Resilience
# ============================================================================

class ResilientConnection:
    """V144.8: Resilient database connection with retry and heartbeat.

    Features:
        - Automatic retry on connection failure (3 attempts, 5s delay)
        - Heartbeat check before operations
        - Connection pool support
        - WSL2 bridge support (172.25.16.1)

    Example:
        >>> resilient = ResilientConnection()
        >>> conn = resilient.get_connection()
        >>> # Use connection...
        >>> resilient.release_connection(conn)
    """

    def __init__(
        self,
        max_retries: int = 3,
        retry_delay: int = 5,
        enable_heartbeat: bool = True,
    ) -> None:
        """Initialize resilient connection manager.

        Args:
            max_retries: Maximum retry attempts (default: 3)
            retry_delay: Delay between retries in seconds (default: 5)
            enable_heartbeat: Enable heartbeat check (default: True)
        """
        self.settings = get_settings()
        self.max_retries = max_retries
        self.retry_delay = retry_delay
        self.enable_heartbeat = enable_heartbeat
        self._conn_pool: list[connection] = []
        self._pool_lock = asyncio.Lock()

    def _create_connection(self) -> connection:
        """Create a new database connection.

        Returns:
            psycopg2 connection

        Raises:
            OperationalError: If all retries fail
        """
        last_error = None

        for attempt in range(1, self.max_retries + 1):
            try:
                logger.info(
                    f"[V144.8] 🔗 数据库连接尝试 #{attempt}/{self.max_retries}: "
                    f"{self.settings.database.host}:{self.settings.database.port}"
                )

                conn = psycopg2.connect(
                    host=self.settings.database.host,
                    port=self.settings.database.port,
                    database=self.settings.database.name,
                    user=self.settings.database.user,
                    password=self.settings.database.password.get_secret_value(),
                )

                # Heartbeat check
                if self.enable_heartbeat:
                    cur = conn.cursor()
                    cur.execute("SELECT 1")
                    cur.close()
                    logger.info("[V144.8] ✅ Heartbeat 检查通过")

                logger.info("[V144.8] ✅ 数据库连接成功")
                return conn

            except OperationalError as e:
                last_error = e
                logger.warning(
                    f"[V144.8] ⚠️ 连接失败 (尝试 {attempt}/{self.max_retries}): {e}"
                )

                if attempt < self.max_retries:
                    logger.info(f"[V144.8] ⏳ 等待 {self.retry_delay} 秒后重试...")
                    time.sleep(self.retry_delay)

        # All retries exhausted
        logger.error(f"[V144.8] ❌ 所有连接尝试均失败")
        raise OperationalError(
            f"Failed to connect after {self.max_retries} attempts: {last_error}"
        ) from last_error

    def heartbeat_check(self, conn: connection | None = None) -> bool:
        """V144.8: Perform heartbeat check.

        Tests if the database connection is alive by executing a simple query.

        Args:
            conn: Connection to check (creates new one if None)

        Returns:
            True if heartbeat successful, False otherwise
        """
        target_conn = conn

        try:
            if target_conn is None:
                target_conn = self._create_connection()

            cur = target_conn.cursor()
            cur.execute("SELECT 1")
            cur.close()

            logger.info("[V144.8] 💓 Heartbeat 检查成功")
            return True

        except Exception as e:
            logger.error(f"[V144.8] 💔 Heartbeat 检查失败: {e}")
            return False

        finally:
            # If we created a temporary connection, close it
            if conn is None and target_conn:
                try:
                    target_conn.close()
                except Exception:
                    pass

    async def get_connection_async(self) -> connection:
        """Get a database connection from pool or create new one.

        Returns:
            psycopg2 connection

        Note:
            This is an async wrapper for compatibility with async codebases.
        """
        async with self._pool_lock:
            if self._conn_pool:
                conn = self._conn_pool.pop()
                # Verify connection is still alive
                try:
                    cur = conn.cursor()
                    cur.execute("SELECT 1")
                    cur.close()
                    return conn
                except Exception:
                    # Connection is dead, create new one
                    pass

        # Create new connection with retry
        return self._create_connection()

    def get_connection(self) -> connection:
        """Synchronous version of get_connection_async.

        Returns:
            psycopg2 connection
        """
        if self._conn_pool:
            conn = self._conn_pool.pop()
            # Verify connection is still alive
            try:
                cur = conn.cursor()
                cur.execute("SELECT 1")
                cur.close()
                return conn
            except Exception:
                # Connection is dead, create new one
                pass

        # Create new connection with retry
        return self._create_connection()

    def release_connection(self, conn: connection) -> None:
        """Release a connection back to the pool.

        Args:
            conn: Database connection to release
        """
        if len(self._conn_pool) < 5:
            self._conn_pool.append(conn)
        else:
            conn.close()

    async def execute_with_retry(
        self,
        query: str,
        params: tuple[Any, ...] | None = None,
        fetch: bool = False,
    ) -> list[tuple] | int:
        """V144.8: Execute SQL query with automatic retry on connection failure.

        Args:
            query: SQL query to execute
            params: Query parameters (optional)
            fetch: Whether to fetch results (default: False)

        Returns:
            Query results if fetch=True, row count otherwise

        Raises:
            Exception: If all retry attempts fail
        """
        last_error = None

        for attempt in range(1, self.max_retries + 1):
            try:
                conn = self.get_connection()
                cur = conn.cursor()

                try:
                    if params:
                        cur.execute(query, params)
                    else:
                        cur.execute(query)

                    if fetch:
                        rows = cur.fetchall()
                        conn.commit()
                        return rows
                    else:
                        row_count = cur.rowcount
                        conn.commit()
                        return row_count

                finally:
                    cur.close()
                    self.release_connection(conn)

            except Exception as e:
                last_error = e
                logger.warning(
                    f"[V144.8] ⚠️ 查询执行失败 (尝试 {attempt}/{self.max_retries}): {e}"
                )

                if attempt < self.max_retries:
                    logger.info(f"[V144.8] ⏳ 等待 {self.retry_delay} 秒后重试...")
                    await asyncio.sleep(self.retry_delay)

        # All retries exhausted
        logger.error(f"[V144.8] ❌ 所有查询尝试均失败: {query[:100]}")
        raise last_error or Exception("Unknown error in execute_with_retry")

    def cleanup(self) -> None:
        """Clean up connection pool."""
        for conn in self._conn_pool:
            try:
                conn.close()
            except Exception:
                pass
        self._conn_pool.clear()


# ============================================================================
# Convenience Functions
# ============================================================================

def get_resilient_connection() -> ResilientConnection:
    """Get a resilient connection manager instance.

    Returns:
        ResilientConnection instance

    Example:
        >>> conn_mgr = get_resilient_connection()
        >>> conn = conn_mgr.get_connection()
    """
    return ResilientConnection()


async def execute_query_with_retry(
    query: str,
    params: tuple[Any, ...] | None = None,
    fetch: bool = False,
) -> list[tuple] | int:
    """Convenience function to execute query with retry.

    Args:
        query: SQL query to execute
        params: Query parameters (optional)
        fetch: Whether to fetch results (default: False)

    Returns:
        Query results if fetch=True, row count otherwise

    Example:
        >>> rows = await execute_query_with_retry(
        ...     "SELECT * FROM matches LIMIT 10",
        ...     fetch=True
        ... )
    """
    resilient = get_resilient_connection()
    return await resilient.execute_with_retry(query, params, fetch)
