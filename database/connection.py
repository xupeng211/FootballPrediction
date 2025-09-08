"""
数据库连接管理模块

提供同步和异步的PostgreSQL数据库连接、会话管理和生命周期控制。
"""

import logging
from contextlib import asynccontextmanager, contextmanager
from typing import AsyncGenerator, Generator, Optional

from sqlalchemy import Engine, create_engine, text
from sqlalchemy.ext.asyncio import (AsyncEngine, AsyncSession,
                                    async_sessionmaker, create_async_engine)
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import QueuePool

from .config import DatabaseConfig, get_database_config

logger = logging.getLogger(__name__)


class DatabaseManager:
    """
    数据库连接管理器

    提供单例模式的数据库连接管理，支持同步和异步操作。
    """

    _instance: Optional["DatabaseManager"] = None
    _sync_engine: Optional[Engine] = None
    _async_engine: Optional[AsyncEngine] = None
    _session_factory: Optional[sessionmaker] = None
    _async_session_factory: Optional[async_sessionmaker] = None

    def __new__(cls) -> "DatabaseManager":
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        if not hasattr(self, "_initialized"):
            self._config: Optional[DatabaseConfig] = None
            self._initialized = True

    def initialize(self, config: Optional[DatabaseConfig] = None) -> None:
        """
        初始化数据库连接

        Args:
            config: 数据库配置，如果为None则使用默认配置
        """
        if config is None:
            config = get_database_config()

        self._config = config
        logger.info(f"初始化数据库连接到 {config.host}:{config.port}/{config.database}")

        # 创建同步引擎
        self._sync_engine = create_engine(
            config.sync_url,
            poolclass=QueuePool,
            pool_size=config.pool_size,
            max_overflow=config.max_overflow,
            pool_timeout=config.pool_timeout,
            pool_recycle=config.pool_recycle,
            echo=config.echo,
            echo_pool=config.echo_pool,
        )

        # 创建异步引擎
        self._async_engine = create_async_engine(
            config.async_url,
            pool_size=config.async_pool_size,
            max_overflow=config.async_max_overflow,
            pool_timeout=config.pool_timeout,
            pool_recycle=config.pool_recycle,
            echo=config.echo,
            echo_pool=config.echo_pool,
        )

        # 创建会话工厂
        self._session_factory = sessionmaker(
            bind=self._sync_engine,
            autocommit=False,
            autoflush=False,
            expire_on_commit=False,
        )

        self._async_session_factory = async_sessionmaker(
            bind=self._async_engine,
            class_=AsyncSession,
            autocommit=False,
            autoflush=False,
            expire_on_commit=False,
        )

        logger.info("数据库连接初始化完成")

    @property
    def sync_engine(self) -> Engine:
        """获取同步数据库引擎"""
        if self._sync_engine is None:
            raise RuntimeError("数据库连接未初始化，请先调用 initialize()")
        return self._sync_engine

    @property
    def async_engine(self) -> AsyncEngine:
        """获取异步数据库引擎"""
        if self._async_engine is None:
            raise RuntimeError("数据库连接未初始化，请先调用 initialize()")
        return self._async_engine

    def create_session(self) -> Session:
        """创建同步数据库会话"""
        if self._session_factory is None:
            raise RuntimeError("数据库连接未初始化，请先调用 initialize()")
        return self._session_factory()

    def create_async_session(self) -> AsyncSession:
        """创建异步数据库会话"""
        if self._async_session_factory is None:
            raise RuntimeError("数据库连接未初始化，请先调用 initialize()")
        return self._async_session_factory()

    @contextmanager
    def get_session(self) -> Generator[Session, None, None]:
        """
        获取同步数据库会话上下文管理器

        使用示例:
            with db_manager.get_session() as session:
                # 执行数据库操作
                result = session.query(Model).all()
        """
        session = self.create_session()
        try:
            yield session
            session.commit()
        except Exception as e:
            session.rollback()
            logger.error(f"数据库操作失败: {e}")
            raise
        finally:
            session.close()

    @asynccontextmanager
    async def get_async_session(self) -> AsyncGenerator[AsyncSession, None]:
        """
        获取异步数据库会话上下文管理器

        使用示例:
            async with db_manager.get_async_session() as session:
                # 执行异步数据库操作
                result = await session.execute(select(Model))
        """
        session = self.create_async_session()
        try:
            yield session
            await session.commit()
        except Exception as e:
            await session.rollback()
            logger.error(f"异步数据库操作失败: {e}")
            raise
        finally:
            await session.close()

    async def close(self) -> None:
        """关闭数据库连接"""
        if self._async_engine:
            await self._async_engine.dispose()
            logger.info("异步数据库连接已关闭")

        if self._sync_engine:
            self._sync_engine.dispose()
            logger.info("同步数据库连接已关闭")

    def health_check(self) -> bool:
        """
        检查数据库连接健康状态（同步版本）

        Returns:
            bool: 数据库是否健康
        """
        try:
            session = self.create_session()
            # 使用text()包装SQL字符串
            session.execute(text("SELECT 1"))
            session.close()
            return True
        except Exception:
            return False

    async def async_health_check(self) -> bool:
        """
        检查数据库连接健康状态（异步版本）

        Returns:
            bool: 数据库是否健康
        """
        try:
            session = self.create_async_session()
            # 使用text()包装SQL字符串
            await session.execute(text("SELECT 1"))
            await session.close()
            return True
        except Exception:
            return False


# 全局数据库管理器实例
_db_manager = DatabaseManager()


def get_database_manager() -> DatabaseManager:
    """获取数据库管理器实例"""
    return _db_manager


def initialize_database(config: Optional[DatabaseConfig] = None) -> None:
    """
    初始化数据库连接

    Args:
        config: 数据库配置
    """
    _db_manager.initialize(config)


def get_db_session() -> Generator[Session, None, None]:
    """
    FastAPI依赖注入使用的同步数据库会话获取器

    使用示例:
        @app.get("/items/")
        def read_items(db: Session = Depends(get_db_session)):
            return db.query(Item).all()
    """
    with _db_manager.get_session() as session:
        yield session


async def get_async_db_session() -> AsyncGenerator[AsyncSession, None]:
    """
    FastAPI依赖注入使用的异步数据库会话获取器

    使用示例:
        @app.get("/items/")
        async def read_items(db: AsyncSession = Depends(get_async_db_session)):
            result = await db.execute(select(Item))
            return result.scalars().all()
    """
    async with _db_manager.get_async_session() as session:
        yield session
