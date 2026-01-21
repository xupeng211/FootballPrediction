"""
数据库连接管理模块

提供异步的PostgreSQL数据库连接、会话管理和生命周期控制。
仅支持异步操作，移除同步引擎以避免psycopg2依赖。

V41.98 新增:
- verify_docker_environment(): 验证连接是否指向 Docker 容器
- 环境纯净性检查: 防止连接到非 Docker 数据库
"""

from collections.abc import AsyncGenerator, Generator
from contextlib import asynccontextmanager, contextmanager
import logging
from typing import Any, Optional

from sqlalchemy import text
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


async def verify_docker_environment(engine: AsyncEngine) -> bool:
    """
    V41.98: 验证数据库连接是否指向 Docker 容器

    Args:
        engine: SQLAlchemy 异步引擎

    Returns:
        True 如果连接到 Docker 容器，否则 False

    Raises:
        RuntimeError: 如果环境不纯净（连接到非 Docker 数据库）
    """
    async with engine.begin() as conn:
        # 检查 PostgreSQL 版本信息
        result = await conn.execute(text("SELECT version()"))
        version = result.scalar()

        # 检查数据库名称
        result_db = await conn.execute(text("SELECT current_database()"))
        db_name = result_db.scalar()

        # 检查容器信息（PostgreSQL 容器识别）
        try:
            result_hostname = await conn.execute(text("SELECT inet_server_addr()"))
            hostname = result_hostname.scalar()
        except Exception:
            hostname = "unknown"

    # V41.98 环境纯净性检查
    # 必须是 PostgreSQL 15 (Docker 镜像版本)
    is_postgres_15 = "PostgreSQL 15" in version

    # 必须是 football_db 数据库
    is_correct_db = db_name == "football_db"

    # 检查是否是 Docker 环境（通过 hostname 或版本判断）
    is_docker = is_postgres_15 and is_correct_db

    logger.info("V41.98 环境验证:")
    logger.info(f"  PostgreSQL 版本: {version[:50]}...")
    logger.info(f"  数据库名称: {db_name}")
    logger.info(f"  服务器地址: {hostname}")
    logger.info(f"  Docker 容器: {'✅ 是' if is_docker else '❌ 否'}")

    if not is_docker:
        error_msg = (
            f"❌ V41.98 环境验证失败!\n"
            f"   当前数据库: {db_name}\n"
            f"   PostgreSQL 版本: {version[:50]}...\n"
            f"   期望: PostgreSQL 15 + football_db (Docker 容器)\n"
            f"   请确保 Docker 服务正在运行: make ps\n"
            f"   请停止本地 PostgreSQL: sudo service postgresql stop"
        )
        logger.error(error_msg)
        raise RuntimeError(error_msg)

    return True


class DatabaseManager:
    """
    数据库连接管理器

    提供单例模式的数据库连接管理，支持异步操作。
    """

    _instance: Optional["DatabaseManager"] = None
    _async_engine: AsyncEngine | None = None
    _async_session_factory: async_sessionmaker | None = None

    def __new__(cls) -> "DatabaseManager":
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self) -> None:
        if not hasattr(self, "_initialized"):
            self._config = None
            self._initialized = True

    def initialize(self, config: Any | None = None) -> None:
        """
        初始化数据库连接（同步版本）

        Args:
            config: 数据库配置，如果为None则使用默认配置

        Warning:
            此方法不执行 Docker 环境验证。请使用 initialize_and_verify()
            或在初始化后手动调用 verify_environment_async()
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

    async def initialize_and_verify(self, config: Any | None = None) -> None:
        """
        V41.98: 初始化数据库连接并验证 Docker 环境

        Args:
            config: 数据库配置，如果为None则使用默认配置

        Raises:
            RuntimeError: 如果数据库环境不是 Docker 容器
        """
        # 先执行标准初始化
        self.initialize(config)

        # V41.98: 验证 Docker 环境
        logger.info("V41.98: 开始验证 Docker 数据库环境...")
        try:
            await verify_docker_environment(self._async_engine)
            logger.info("✅ V41.98: Docker 环境验证通过")
        except RuntimeError as e:
            logger.exception(f"❌ V41.98: Docker 环境验证失败: {e}")
            raise

    async def verify_environment_async(self) -> bool:
        """
        V41.98: 异步验证当前数据库连接是否指向 Docker 容器

        Returns:
            True 如果环境验证通过

        Raises:
            RuntimeError: 如果环境验证失败（连接到非 Docker 数据库）
        """
        if self._async_engine is None:
            raise RuntimeError("数据库连接未初始化")

        return await verify_docker_environment(self._async_engine)

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
        return

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
                logger.exception(f"异步数据库操作失败: {e}")
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


def initialize_database(config: Any | None = None) -> None:
    """
    初始化数据库连接（不验证环境）

    Args:
        config: 数据库配置，如果为None则使用默认配置

    Warning:
        此函数不执行 Docker 环境验证。推荐使用 initialize_database_and_verify()
    """
    _db_manager.initialize(config)


async def initialize_database_and_verify(config: Any | None = None) -> None:
    """
    V41.98: 初始化数据库连接并验证 Docker 环境

    Args:
        config: 数据库配置，如果为None则使用默认配置

    Raises:
        RuntimeError: 如果连接到非 Docker 数据库
    """
    await _db_manager.initialize_and_verify(config)


async def verify_database_environment() -> bool:
    """
    V41.98: 验证当前数据库连接是否指向 Docker 容器

    Returns:
        True 如果环境验证通过

    Raises:
        RuntimeError: 如果环境验证失败
    """
    return await _db_manager.verify_environment_async()


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
    return


def close_database() -> None:
    """关闭数据库连接"""
    _db_manager.close()
