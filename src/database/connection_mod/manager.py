"""
数据库连接管理器
Database Connection Manager

提供单例模式的数据库连接管理。
"""

import asyncio
import os
from contextlib import asynccontextmanager, contextmanager
from typing import Any, AsyncGenerator, Dict, Generator, Optional

from sqlalchemy import Engine, create_engine, text
from sqlalchemy.exc import SQLAlchemyError, DatabaseError
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import QueuePool

from src.utils.retry import RetryConfig, retry
from src.core.logging import get_logger

from .config import DatabaseConfig, get_database_config

logger = get_logger(__name__)

# 数据库重试配置 / Database retry configuration
DATABASE_RETRY_CONFIG = RetryConfig(
    max_attempts=int(os.getenv("DATABASE_RETRY_MAX_ATTEMPTS", "5")),
    base_delay=float(os.getenv("DATABASE_RETRY_BASE_DELAY", "1.0")),
    max_delay=30.0,
    exponential_base=2.0,
    jitter=True,
)


class DatabaseManager:
    """
    数据库连接管理器 / Database Connection Manager

    单例模式的数据库连接管理器，负责管理数据库连接、会话创建和生命周期。
    Singleton database connection manager responsible for managing database connections,
    session creation, and lifecycle.

    Attributes:
        _instance (Optional[DatabaseManager]): 单例实例 / Singleton instance
        _initialized (bool): 是否已初始化 / Whether initialized
        config (DatabaseConfig): 数据库配置 / Database configuration
        _engine (Optional[Engine]): 同步引擎 / Synchronous engine
        _async_engine (Optional[AsyncEngine]): 异步引擎 / Asynchronous engine
        _session_factory (Optional[sessionmaker]): 同步会话工厂 / Synchronous session factory
        _async_session_factory (Optional[async_sessionmaker]): 异步会话工厂 / Asynchronous session factory

    Note:
        这是一个单例类，使用 get_instance() 方法获取实例。
        This is a singleton class, use get_instance() method to get instance.
    """

    _instance: Optional["DatabaseManager"] = None
    _initialized: bool = False

    def __new__(cls) -> "DatabaseManager":
        """
        创建或获取单例实例 / Create or get singleton instance

        Returns:
            DatabaseManager: 单例实例 / Singleton instance
        """
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        """初始化数据库管理器 / Initialize database manager"""
        if self._initialized:
            return

        self.config: Optional[DatabaseConfig] = None
        self._engine: Optional[Engine] = None
        self._async_engine: Optional[AsyncEngine] = None
        self._session_factory: Optional[sessionmaker] = None
        self._async_session_factory: Optional[async_sessionmaker] = None
        self._lock = asyncio.Lock()
        self._initialized = True

    def initialize(
        self,
        config: Optional[DatabaseConfig] = None,
        echo: bool = False,
        pool_size: int = 5,
        max_overflow: int = 10,
    ) -> None:
        """
        初始化数据库连接 / Initialize Database Connection

        Args:
            config (Optional[DatabaseConfig]): 数据库配置，如果为None则使用环境变量
                                              Database configuration, use environment variables if None
            echo (bool): 是否输出SQL语句 / Whether to output SQL statements
            pool_size (int): 连接池大小 / Connection pool size
            max_overflow (int): 连接池最大溢出 / Maximum connection pool overflow

        Raises:
            Exception: 当连接初始化失败时抛出 / Raised when connection initialization fails
        """
        if self._engine and self._async_engine:
            logger.info("数据库连接已初始化")
            return

        try:
            # 获取配置
            self.config = config or get_database_config()

            # 构建同步连接URL
            sync_url = self.config.get_sync_url()

            # 构建异步连接URL
            async_url = self.config.get_async_url()

            logger.info(f"初始化数据库连接: {self.config.database}")

            # 创建同步引擎
            self._engine = create_engine(
                sync_url,
                echo=echo,
                poolclass=QueuePool,
                pool_size=pool_size,
                max_overflow=max_overflow,
                pool_pre_ping=True,
                pool_recycle=3600,
            )

            # 创建异步引擎
            self._async_engine = create_async_engine(
                async_url,
                echo=echo,
                pool_size=pool_size,
                max_overflow=max_overflow,
                pool_pre_ping=True,
                pool_recycle=3600,
            )

            # 创建会话工厂
            self._session_factory = sessionmaker(
                bind=self._engine,
                autocommit=False,
                autoflush=False,
            )

            self._async_session_factory = async_sessionmaker(
                bind=self._async_engine,
                autocommit=False,
                autoflush=False,
            )

            # 测试连接
            self._test_connection()

            logger.info("数据库连接初始化成功")

        except (SQLAlchemyError, DatabaseError, ConnectionError, TimeoutError) as e:
            logger.error(f"数据库连接初始化失败: {e}")
            raise

    @retry(DATABASE_RETRY_CONFIG)
    def _test_connection(self) -> None:
        """
        测试数据库连接 / Test Database Connection
        """
        if not self._engine:
            raise Exception("数据库引擎未初始化")

        with self._engine.connect() as conn:
            result = conn.execute(text("SELECT 1"))
            result.fetchone()

    @property
    def engine(self) -> Engine:
        """
        获取同步引擎 / Get Synchronous Engine

        Returns:
            Engine: SQLAlchemy同步引擎 / SQLAlchemy synchronous engine

        Raises:
            Exception: 当引擎未初始化时抛出 / Raised when engine is not initialized
        """
        if not self._engine:
            raise Exception("数据库引擎未初始化，请先调用 initialize()")
        return self._engine

    @property
    def async_engine(self) -> AsyncEngine:
        """
        获取异步引擎 / Get Asynchronous Engine

        Returns:
            AsyncEngine: SQLAlchemy异步引擎 / SQLAlchemy asynchronous engine

        Raises:
            Exception: 当引擎未初始化时抛出 / Raised when engine is not initialized
        """
        if not self._async_engine:
            raise Exception("异步数据库引擎未初始化，请先调用 initialize()")
        return self._async_engine

    @contextmanager
    def get_session(self) -> Generator[Session, None, None]:
        """
        获取同步数据库会话 / Get Synchronous Database Session

        Returns:
            Generator[Session, None, None]: 数据库会话上下文管理器 / Database session context manager

        Example:
            ```python
            with db_manager.get_session() as session:
                # 执行数据库操作
                result = session.execute(text("SELECT * FROM table"))
            ```
        """
        if not self._session_factory:
            raise Exception("会话工厂未初始化，请先调用 initialize()")

        session = self._session_factory()
        try:
            yield session
            session.commit()
        except (SQLAlchemyError, DatabaseError, ConnectionError, TimeoutError) as e:
            session.rollback()
            logger.error(f"数据库会话错误: {e}")
            raise
        finally:
            session.close()

    @asynccontextmanager
    async def get_async_session(self) -> AsyncGenerator[AsyncSession, None]:
        """
        获取异步数据库会话 / Get Asynchronous Database Session

        Returns:
            AsyncGenerator[AsyncSession, None, None]: 异步数据库会话上下文管理器
                                                 / Asynchronous database session context manager

        Example:
            ```python
            async with db_manager.get_async_session() as session:
                # 执行异步数据库操作
                result = await session.execute(text("SELECT * FROM table"))
            ```
        """
        if not self._async_session_factory:
            raise Exception("异步会话工厂未初始化，请先调用 initialize()")

        session = self._async_session_factory()
        try:
            yield session
            await session.commit()
        except (SQLAlchemyError, DatabaseError, ConnectionError, TimeoutError) as e:
            await session.rollback()
            logger.error(f"异步数据库会话错误: {e}")
            raise
        finally:
            await session.close()

    def execute_query(self, query: str, params: Optional[Dict[str, Any]] = None) -> Any:
        """
        执行SQL查询 / Execute SQL Query

        Args:
            query (str): SQL查询语句 / SQL query statement
            params (Optional[Dict[str, Any]]): 查询参数 / Query parameters

        Returns:
            Any: 查询结果 / Query result
        """
        with self.get_session() as session:
            return session.execute(text(query), params or {})

    async def execute_query_async(
        self, query: str, params: Optional[Dict[str, Any]] = None
    ) -> Any:
        """
        异步执行SQL查询 / Execute SQL Query Asynchronously

        Args:
            query (str): SQL查询语句 / SQL query statement
            params (Optional[Dict[str, Any]]): 查询参数 / Query parameters

        Returns:
            Any: 查询结果 / Query result
        """
        async with self.get_async_session() as session:
            return await session.execute(text(query), params or {})

    def close(self) -> None:
        """
        关闭数据库连接 / Close Database Connection
        """
        if self._engine:
            self._engine.dispose()
            self._engine = None

        if self._async_engine:
            asyncio.create_task(self._async_engine.dispose())
            self._async_engine = None

        logger.info("数据库连接已关闭")

    async def close_async(self) -> None:
        """
        异步关闭数据库连接 / Close Database Connection Asynchronously
        """
        if self._engine:
            self._engine.dispose()
            self._engine = None

        if self._async_engine:
            await self._async_engine.dispose()
            self._async_engine = None

        logger.info("数据库连接已关闭")

    def get_connection_info(self) -> Dict[str, Any]:
        """
        获取连接信息 / Get Connection Information

        Returns:
            Dict[str, Any]: 连接信息 / Connection information
        """
        if not self.config:
            return {"error": "数据库未初始化"}

        return {
            "host": self.config.host,
            "port": self.config.port,
            "database": self.config.database,
            "username": self.config.username,
            "pool_size": self._engine.pool.size() if self._engine else 0,  # type: ignore
            "checked_in": self._engine.pool.checkedin() if self._engine else 0,  # type: ignore
            "checked_out": self._engine.pool.checkedout() if self._engine else 0,  # type: ignore
        }
