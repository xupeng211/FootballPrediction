"""
数据库引擎管理器

负责创建和管理同步/异步数据库引擎
"""

import logging
from typing import Optional

from sqlalchemy import Engine
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import QueuePool

from src.database.config import DatabaseConfig
from src.database.connection.core.config import get_pool_settings

logger = logging.getLogger(__name__)


class DatabaseEngineManager:
    """
    数据库引擎管理器

    负责创建和管理同步/异步数据库引擎及会话工厂
    """

    def __init__(self):
        """初始化引擎管理器"""
        self._sync_engine: Optional[Engine] = None
        self._async_engine: Optional[AsyncEngine] = None
        self._session_factory: Optional[sessionmaker] = None
        self._async_session_factory: Optional[async_sessionmaker] = None
        self._config: Optional[DatabaseConfig] = None

    def initialize_engines(self, config: DatabaseConfig) -> None:
        """
        初始化数据库引擎

        Args:
            config: 数据库配置
        """
        self._config = config
        logger.info(f"初始化数据库引擎到 {config.host}:{config.port}/{config.database}")

        # 检查是否为SQLite
        is_sqlite = (
            config.database.endswith(".db") or
            config.database == ":memory:" or
            "sqlite" in config.sync_url
        )

        # 创建同步引擎
        self._sync_engine = self._create_sync_engine(config, is_sqlite)

        # 创建异步引擎
        self._async_engine = self._create_async_engine(config, is_sqlite)

        # 创建会话工厂
        self._create_session_factories()

        logger.info("数据库引擎初始化完成")

    def _create_sync_engine(self, config: DatabaseConfig, is_sqlite: bool) -> Engine:
        """
        创建同步数据库引擎

        Args:
            config: 数据库配置
            is_sqlite: 是否为SQLite

        Returns:
            Engine: 同步数据库引擎
        """
        if is_sqlite:
            # SQLite不使用连接池
            from sqlalchemy import create_engine
            return create_engine(
                config.sync_url,
                echo=config.echo,
                echo_pool=config.echo_pool,
            )
        else:
            from sqlalchemy import create_engine
            pool_size, max_overflow, pool_timeout, pool_recycle = get_pool_settings(
                is_async=False, is_sqlite=False
            )
            return create_engine(
                config.sync_url,
                poolclass=QueuePool,
                pool_size=pool_size,
                max_overflow=max_overflow,
                pool_timeout=pool_timeout,
                pool_recycle=pool_recycle,
                echo=config.echo,
                echo_pool=config.echo_pool,
            )

    def _create_async_engine(self, config: DatabaseConfig, is_sqlite: bool) -> AsyncEngine:
        """
        创建异步数据库引擎

        Args:
            config: 数据库配置
            is_sqlite: 是否为SQLite

        Returns:
            AsyncEngine: 异步数据库引擎
        """
        from sqlalchemy.ext.asyncio import create_async_engine

        if is_sqlite:
            # SQLite不使用连接池参数
            return create_async_engine(
                config.async_url,
                echo=config.echo,
                echo_pool=config.echo_pool,
            )
        else:
            pool_size, max_overflow, pool_timeout, pool_recycle = get_pool_settings(
                is_async=True, is_sqlite=False
            )
            return create_async_engine(
                config.async_url,
                pool_size=pool_size,
                max_overflow=max_overflow,
                pool_timeout=pool_timeout,
                pool_recycle=pool_recycle,
                echo=config.echo,
                echo_pool=config.echo_pool,
            )

    def _create_session_factories(self) -> None:
        """创建会话工厂"""
        # 同步会话工厂
        self._session_factory = sessionmaker(
            bind=self._sync_engine,
            autocommit=False,
            autoflush=False,
            expire_on_commit=False,
        )

        # 异步会话工厂
        self._async_session_factory = async_sessionmaker(
            bind=self._async_engine,
            class_=AsyncSession,
            autocommit=False,
            autoflush=False,
            expire_on_commit=False,
        )

    @property
    def sync_engine(self) -> Engine:
        """获取同步数据库引擎"""
        if self._sync_engine is None:
            raise RuntimeError("数据库引擎未初始化，请先调用 initialize_engines()")
        return self._sync_engine

    @property
    def async_engine(self) -> AsyncEngine:
        """获取异步数据库引擎"""
        if self._async_engine is None:
            raise RuntimeError("数据库引擎未初始化，请先调用 initialize_engines()")
        return self._async_engine

    @property
    def session_factory(self) -> sessionmaker:
        """获取同步会话工厂"""
        if self._session_factory is None:
            raise RuntimeError("会话工厂未初始化")
        return self._session_factory

    @property
    def async_session_factory(self) -> async_sessionmaker:
        """获取异步会话工厂"""
        if self._async_session_factory is None:
            raise RuntimeError("异步会话工厂未初始化")
        return self._async_session_factory

    def create_session(self) -> Session:
        """
        创建同步数据库会话

        Returns:
            Session: 同步数据库会话
        """
        return self.session_factory()

    def create_async_session(self):
        """
        创建异步数据库会话

        Returns:
            AsyncSession: 异步数据库会话
        """
        return self.async_session_factory()

    def get_config(self) -> Optional[DatabaseConfig]:
        """
        获取数据库配置

        Returns:
            Optional[DatabaseConfig]: 数据库配置
        """
        return self._config

    def close_engines(self) -> None:
        """关闭所有数据库引擎"""
        if self._sync_engine:
            self._sync_engine.dispose()
            logger.info("同步数据库引擎已关闭")

        if self._async_engine:
            # 对于异步引擎，需要在事件循环中关闭
            import asyncio
            try:
                loop = asyncio.get_event_loop()
                if loop.is_running():
                    # 如果事件循环正在运行，创建任务
                    loop.create_task(self._async_engine.dispose())
                else:
                    # 如果事件循环未运行，直接运行
                    asyncio.run(self._async_engine.dispose())
                logger.info("异步数据库引擎已关闭")
            except Exception as e:
                logger.warning(f"关闭异步引擎时出错: {e}")

    @property
    def is_initialized(self) -> bool:
        """
        检查引擎是否已初始化

        Returns:
            bool: 是否已初始化
        """
        return self._sync_engine is not None and self._async_engine is not None