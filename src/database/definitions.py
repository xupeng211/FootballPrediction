from typing import Any, Dict, List, Optional, Union
"""数据库相关的定义，用于替代connection_mod"""

from enum import Enum
import asyncio
from sqlalchemy import create_engine
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.orm import Session, sessionmaker


class DatabaseRole(Enum):
    """数据库用户角色"""

    READER = "reader"
    WRITER = "writer"
    ADMIN = "admin"


class DatabaseManager:
    """数据库管理器 - 简化版本"""

    _instance = None
    _engine = None
    _async_engine = None
    _session_factory = None
    _async_session_factory = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        if not hasattr(self, "initialized"):
            self.initialized = False

    def initialize(self, database_url: Optional[str] = None):
        """初始化数据库连接"""
        if self.initialized:
            return

        import os

        db_url = database_url or os.getenv(
            "DATABASE_URL", "postgresql://localhost/football_prediction"
        )
        if db_url is None:
            raise ValueError("Database URL is required")
        async_db_url = db_url.replace("postgresql://", "postgresql+asyncpg://")

        # 同步引擎
        self._engine = create_engine(
            db_url,
            pool_pre_ping=True,
            pool_recycle=300,
        )
        self._session_factory = sessionmaker(bind=self._engine)

        # 异步引擎
        self._async_engine = create_async_engine(
            async_db_url,
            pool_pre_ping=True,
            pool_recycle=300,
        )
        self._async_session_factory = async_sessionmaker(
            bind=self._async_engine,
            class_=AsyncSession,
        )

        self.initialized = True

    def get_session(self) -> Session:
        """获取同步会话"""
        if not self.initialized:
            self.initialize()
        return self._session_factory()

    def get_async_session(self) -> AsyncSession:
        """获取异步会话"""
        if not self.initialized:
            self.initialize()
        return self._async_session_factory()


class MultiUserDatabaseManager(DatabaseManager):
    """多用户数据库管理器 - 简化版本"""

    def __init__(self):
        super().__init__()
        self.readers = []
        self.writers = []
        self.admins = []


# 工厂函数
def get_database_manager() -> DatabaseManager:
    """获取数据库管理器单例"""
    return DatabaseManager()


def get_multi_user_database_manager() -> MultiUserDatabaseManager:
    """获取多用户数据库管理器"""
    return MultiUserDatabaseManager()


# 初始化函数
def initialize_database(database_url: Optional[str] = None):
    """初始化数据库"""
    manager = get_database_manager()
    manager.initialize(database_url)


def initialize_multi_user_database(database_url: Optional[str] = None):
    """初始化多用户数据库"""
    manager = get_multi_user_database_manager()
    manager.initialize(database_url)


def initialize_test_database():
    """初始化测试数据库"""
    # 测试数据库的特殊初始化
    pass


# 会话获取函数
def get_db_session() -> Session:
    """获取数据库会话"""
    manager = get_database_manager()
    return manager.get_session()


def get_async_session() -> AsyncSession:
    """获取异步会话"""
    manager = get_database_manager()
    return manager.get_async_session()


# 其他会话函数的简化实现
def get_reader_session() -> Session:
    return get_db_session()


def get_writer_session() -> Session:
    return get_db_session()


def get_admin_session() -> Session:
    return get_db_session()


def get_async_reader_session() -> AsyncSession:
    return get_async_session()


def get_async_writer_session() -> AsyncSession:
    return get_async_session()


def get_async_admin_session() -> AsyncSession:
    return get_async_session()


# 兼容性别名
get_session = get_db_session
