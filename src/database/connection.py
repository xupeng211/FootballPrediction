"""
数据库连接管理模块

提供异步的PostgreSQL数据库连接、会话管理和生命周期控制。
仅支持异步操作，移除同步引擎以避免psycopg2依赖。
"""

import logging
from contextlib import asynccontextmanager, contextmanager
from typing import AsyncGenerator, Generator, Optional, Any

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

logger = logging.getLogger(__name__)


def get_database_config():
    """获取数据库配置（从 config_unified.py）"""
    from src.config_unified import get_settings
    settings = get_settings()
    return settings.database


class DatabaseManager:
    """
    数据库连接管理器

    提供单例模式的数据库连接管理，支持异步操作。
    """

    _instance: Optional["DatabaseManager"] = None
    _async_engine: Optional[AsyncEngine] = None
    _async_session_factory: Optional[async_sessionmaker] = None

    def __new__(cls) -> "DatabaseManager":
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self) -> None:
        if not hasattr(self, "_initialized"):
            self._config = None
            self._initialized = True

    def initialize(self, config: Optional[Any] = None) -> None:
        """
        初始化数据库连接

        Args:
            config: 数据库配置，如果为None则使用默认配置
        """
        if config is None:
            config = get_database_config()

        self._config = config
        logger.info(f"初始化数据库连接到 {config.host}:{config.port}/{config.name}")

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

        # 创建异步会话工厂
        self._async_session_factory = async_sessionmaker(
            bind=self._async_engine,
            class_=AsyncSession,
            autocommit=False,
            autoflush=False,
            expire_on_commit=False,
        )

        logger.info("数据库连接初始化完成")

    @property
    def sync_engine(self) -> None:
        """获取同步数据库引擎 - 已禁用，仅支持异步"""
        # 已禁用同步引擎，仅支持异步操作
        return None

    @property
    def async_engine(self) -> AsyncEngine:
        """获取异步数据库引擎"""
        if self._async_engine is None:
            raise RuntimeError("数据库连接未初始化，请先调用 initialize()")
        return self._async_engine

    def create_session(self) -> None:
        """创建同步数据库会话 - 已禁用，仅支持异步"""
        # 已禁用同步会话，仅支持异步操作
        return None

    def create_async_session(self) -> AsyncSession:
        """创建异步数据库会话"""
        if self._async_session_factory is None:
            raise RuntimeError("数据库连接未初始化，请先调用 initialize()")
        return self._async_session_factory()

    @contextmanager
    def get_session(self) -> Generator[None, None, None]:
        """
        获取同步数据库会话上下文管理器 - 已禁用，仅支持异步

        使用示例:
            使用 create_async_session() 和 get_async_session() 替代
        """
        # 已禁用同步会话，仅支持异步操作
        yield None

    @asynccontextmanager
    async def get_async_session(self) -> AsyncGenerator[AsyncSession, None]:
        """
        获取异步数据库会话上下文管理器

        使用示例:
            async with db_manager.get_async_session() as session:
                # 执行异步数据库操作
                result = await session.execute(select(Model))
        """
        if self._async_session_factory is None:
            raise RuntimeError("数据库连接未初始化，请先调用 initialize()")

        async with self._async_session_factory() as session:
            try:
                yield session
            except Exception as e:
                await session.rollback()
                logger.error(f"异步数据库操作失败: {e}")
                raise
            finally:
                await session.close()

    def close(self) -> None:
        """关闭数据库连接"""
        if self._async_engine is not None:
            self._async_engine.dispose()
            logger.info("数据库连接已关闭")

    def is_initialized(self) -> bool:
        """检查数据库是否已初始化"""
        return self._async_engine is not None


# 创建全局数据库管理器实例
_db_manager = DatabaseManager()


def initialize_database(config: Optional[Any] = None) -> None:
    """
    初始化数据库连接

    Args:
        config: 数据库配置，如果为None则使用默认配置
    """
    _db_manager.initialize(config)


def get_db_manager() -> DatabaseManager:
    """
    获取数据库管理器实例

    Returns:
        DatabaseManager实例
    """
    return _db_manager


async def get_async_db_session() -> AsyncGenerator[AsyncSession, None]:
    """
    获取异步数据库会话的便捷函数

    使用示例:
        async for session in get_async_db_session():
            await session.execute(select(Model))
    """
    async with _db_manager.get_async_session() as session:
        yield session


def get_db_session() -> None:
    """
    获取同步数据库会话的便捷函数 - 已禁用

    使用示例:
        使用 get_async_db_session() 替代
    """
    # 已禁用同步会话，仅支持异步操作
    return None


def close_database() -> None:
    """关闭数据库连接"""
    _db_manager.close()
