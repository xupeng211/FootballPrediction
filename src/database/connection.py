"""
import asyncio
数据库连接管理模块

提供同步和异步的PostgreSQL数据库连接、会话管理和生命周期控制。
支持多用户权限分离的数据库连接管理。
"""

import logging
from contextlib import asynccontextmanager, contextmanager
from enum import Enum
from typing import AsyncGenerator, Dict, Generator, Optional

from sqlalchemy import Engine, create_engine, text
from sqlalchemy.ext.asyncio import (AsyncEngine, AsyncSession,
                                    async_sessionmaker, create_async_engine)
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import QueuePool

from .config import DatabaseConfig, get_database_config

logger = logging.getLogger(__name__)


class DatabaseRole(str, Enum):
    """数据库用户角色枚举"""

    READER = "reader"  # 只读用户（分析、前端）
    WRITER = "writer"  # 读写用户（数据采集）
    ADMIN = "admin"  # 管理员用户（运维、迁移）


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

    def __init__(self) -> None:
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
        # 对于SQLite，不使用连接池
        if config.database.endswith(".db") or config.database == ":memory:":
            self._sync_engine = create_engine(
                config.sync_url,
                echo=config.echo,
                echo_pool=config.echo_pool,
            )
        else:
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
        # 对于SQLite，不使用连接池参数
        if config.database.endswith(".db") or config.database == ":memory:":
            self._async_engine = create_async_engine(
                config.async_url,
                echo=config.echo,
                echo_pool=config.echo_pool,
            )
        else:
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

    def get_config(self) -> Optional[DatabaseConfig]:
        """
        获取数据库配置

        Returns:
            数据库配置对象，如果未初始化则返回None
        """
        return self._config

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
            try:
                await self._async_engine.dispose()
                logger.info("异步数据库连接已关闭")
            except Exception as e:
                logger.error(f"关闭异步数据库连接失败: {e}")

        if self._sync_engine:
            try:
                self._sync_engine.dispose()
                logger.info("同步数据库连接已关闭")
            except Exception as e:
                logger.error(f"关闭同步数据库连接失败: {e}")

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


class MultiUserDatabaseManager:
    """
    多用户数据库连接管理器

    支持按用户角色管理数据库连接，实现权限分离。
    基于 DATA_DESIGN.md 第5.3节权限控制设计。
    """

    _instance: Optional["MultiUserDatabaseManager"] = None
    _managers: Dict[DatabaseRole, DatabaseManager] = {}
    _configs: Dict[DatabaseRole, DatabaseConfig] = {}

    def __new__(cls) -> "MultiUserDatabaseManager":
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self) -> None:
        if not hasattr(self, "_initialized"):
            self._initialized = True

    def initialize(self, base_config: Optional[DatabaseConfig] = None) -> None:
        """
        初始化多用户数据库连接

        Args:
            base_config: 基础数据库配置，将为每个角色创建专用配置
        """
        if base_config is None:
            base_config = get_database_config()

        # 用户凭据映射
        user_credentials = {
            DatabaseRole.READER: {
                "username": "football_reader",
                "password": "reader_password_2025",
            },
            DatabaseRole.WRITER: {
                "username": "football_writer",
                "password": "writer_password_2025",
            },
            DatabaseRole.ADMIN: {
                "username": "football_admin",
                "password": "admin_password_2025",
            },
        }

        # 为每个角色创建专用的数据库配置和连接管理器
        for role, credentials in user_credentials.items():
            # 创建角色专用配置
            role_config = DatabaseConfig(
                host=base_config.host,
                port=base_config.port,
                database=base_config.database,
                username=credentials["username"],
                password=credentials["password"],
                pool_size=base_config.pool_size,
                max_overflow=base_config.max_overflow,
                pool_timeout=base_config.pool_timeout,
                pool_recycle=base_config.pool_recycle,
                async_pool_size=base_config.async_pool_size,
                async_max_overflow=base_config.async_max_overflow,
                echo=base_config.echo,
                echo_pool=base_config.echo_pool,
            )

            self._configs[role] = role_config

            # 为每个角色创建独立的数据库管理器
            manager = DatabaseManager()
            manager.initialize(role_config)

            self._managers[role] = manager

            logger.info(f"初始化 {role.value} 用户数据库连接: {credentials['username']}")

        logger.info("多用户数据库连接管理器初始化完成")

    def get_manager(self, role: DatabaseRole) -> DatabaseManager:
        """
        获取指定角色的数据库管理器

        Args:
            role: 数据库用户角色

        Returns:
            DatabaseManager: 角色对应的数据库管理器

        Raises:
            RuntimeError: 如果管理器未初始化或角色不存在
        """
        if role not in self._managers:
            raise RuntimeError(f"数据库角色 {role.value} 的管理器未初始化，请先调用 initialize()")
        return self._managers[role]

    @contextmanager
    def get_session(self, role: DatabaseRole) -> Generator[Session, None, None]:
        """
        获取指定角色的同步数据库会话

        Args:
            role: 数据库用户角色

        Usage:
            with multi_db_manager.get_session(DatabaseRole.READER) as session:
                # 只读操作
                results = session.query(Match).all()
        """
        manager = self.get_manager(role)
        with manager.get_session() as session:
            yield session

    @asynccontextmanager
    async def get_async_session(
        self, role: DatabaseRole
    ) -> AsyncGenerator[AsyncSession, None]:
        """
        获取指定角色的异步数据库会话

        Args:
            role: 数据库用户角色

        Usage:
            async with multi_db_manager.get_async_session(DatabaseRole.WRITER) as session:
                # 读写操作
                await session.execute(insert(RawMatchData).values(data))
        """
        manager = self.get_manager(role)
        async with manager.get_async_session() as session:
            yield session

    def health_check(self, role: Optional[DatabaseRole] = None) -> Dict[str, bool]:
        """
        检查数据库连接健康状态

        Args:
            role: 要检查的角色，如果为None则检查所有角色

        Returns:
            Dict[str, bool]: 角色名到健康状态的映射
        """
        if role:
            manager = self.get_manager(role)
            return {role.value: manager.health_check()}

        health_status = {}
        for role, manager in self._managers.items():
            health_status[role.value] = manager.health_check()

        return health_status

    async def async_health_check(
        self, role: Optional[DatabaseRole] = None
    ) -> Dict[str, bool]:
        """
        异步检查数据库连接健康状态

        Args:
            role: 要检查的角色，如果为None则检查所有角色

        Returns:
            Dict[str, bool]: 角色名到健康状态的映射
        """
        if role:
            manager = self.get_manager(role)
            return {role.value: await manager.async_health_check()}

        health_status = {}
        for role, manager in self._managers.items():
            health_status[role.value] = await manager.async_health_check()

        return health_status

    async def close(self) -> None:
        """关闭所有数据库连接"""
        for role, manager in self._managers.items():
            try:
                await manager.close()
                logger.info(f"已关闭 {role.value} 用户的数据库连接")
            except Exception as e:
                logger.error(f"关闭 {role.value} 用户数据库连接失败: {e}")

    def get_role_permissions(self, role: DatabaseRole) -> Dict[str, str]:
        """
        获取角色权限描述

        Args:
            role: 数据库用户角色

        Returns:
            Dict[str, str]: 权限描述
        """
        permissions_map = {
            DatabaseRole.READER: {
                "description": "只读用户（分析、前端）",
                "permissions": "SELECT on all tables",
                "use_cases": "数据分析、前端展示、报告生成",
            },
            DatabaseRole.WRITER: {
                "description": "读写用户（数据采集）",
                "permissions": "SELECT, INSERT, UPDATE on all tables; DELETE on raw_data tables",
                "use_cases": "数据采集、数据处理、清理任务",
            },
            DatabaseRole.ADMIN: {
                "description": "管理员用户（运维、迁移）",
                "permissions": "ALL PRIVILEGES on database",
                "use_cases": "数据库维护、架构迁移、用户管理",
            },
        }

        return permissions_map.get(role, {})


# 全局数据库管理器实例
_db_manager = DatabaseManager()
_multi_db_manager = MultiUserDatabaseManager()


def get_database_manager() -> DatabaseManager:
    """获取数据库管理器实例"""
    return _db_manager


def get_multi_user_database_manager() -> MultiUserDatabaseManager:
    """获取多用户数据库管理器实例"""
    return _multi_db_manager


def initialize_database(config: Optional[DatabaseConfig] = None) -> None:
    """
    初始化数据库连接

    Args:
        config: 数据库配置
    """
    _db_manager.initialize(config)


def initialize_multi_user_database(config: Optional[DatabaseConfig] = None) -> None:
    """
    初始化多用户数据库连接

    Args:
        config: 基础数据库配置
    """
    _multi_db_manager.initialize(config)


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


# 多用户数据库会话依赖注入函数
def get_reader_session() -> Generator[Session, None, None]:
    """获取只读用户会话（用于数据分析、前端展示）"""
    with _multi_db_manager.get_session(DatabaseRole.READER) as session:
        yield session


def get_writer_session() -> Generator[Session, None, None]:
    """获取读写用户会话（用于数据采集、处理）"""
    with _multi_db_manager.get_session(DatabaseRole.WRITER) as session:
        yield session


def get_admin_session() -> Generator[Session, None, None]:
    """获取管理员用户会话（用于运维、迁移）"""
    with _multi_db_manager.get_session(DatabaseRole.ADMIN) as session:
        yield session


async def get_async_reader_session() -> AsyncGenerator[AsyncSession, None]:
    """获取异步只读用户会话"""
    async with _multi_db_manager.get_async_session(DatabaseRole.READER) as session:
        yield session


async def get_async_writer_session() -> AsyncGenerator[AsyncSession, None]:
    """获取异步读写用户会话"""
    async with _multi_db_manager.get_async_session(DatabaseRole.WRITER) as session:
        yield session


async def get_async_admin_session() -> AsyncGenerator[AsyncSession, None]:
    """获取异步管理员用户会话"""
    async with _multi_db_manager.get_async_session(DatabaseRole.ADMIN) as session:
        yield session


# 便捷的会话获取函数，用于直接使用
@contextmanager
def get_session(
    role: DatabaseRole = DatabaseRole.READER,
) -> Generator[Session, None, None]:
    """
    获取指定角色的数据库会话

    Args:
        role: 数据库用户角色，默认为只读用户
    """
    with _multi_db_manager.get_session(role) as session:
        yield session


@asynccontextmanager
async def get_async_session(
    role: DatabaseRole = DatabaseRole.READER,
) -> AsyncGenerator[AsyncSession, None]:
    """
    获取指定角色的异步数据库会话

    Args:
        role: 数据库用户角色，默认为只读用户
    """
    async with _multi_db_manager.get_async_session(role) as session:
        yield session
