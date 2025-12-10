"""
统一异步数据库管理器
Unified Async Database Manager

实现 "One Way to do it" 原则，提供单一的数据库会话管理接口。
遵循 FastAPI 最佳实践，支持异步操作和依赖注入。

使用示例:
    from src.database.async_manager import get_db_session, initialize_database

    # 初始化（应用启动时调用一次）
    initialize_database()

    # 在 FastAPI 路由中使用
    @app.get("/matches/")
    async def get_matches(session: AsyncSession = Depends(get_db_session)):
        result = await session.execute(select(Match))
        return result.scalars().all()

    # 在爬虫脚本中使用
    async def crawl_fotmob():
        async with get_db_session() as session:
            # 执行数据库操作
            pass
"""

import os
import logging
from enum import Enum
from typing import Any, Optional, Union
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from sqlalchemy import create_engine, text
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.pool import NullPool
from tenacity import retry, stop_after_attempt, wait_exponential

logger = logging.getLogger(__name__)


class DatabaseRole(Enum):
    """数据库用户角色"""

    READER = "reader"
    WRITER = "writer"
    ADMIN = "admin"


class AsyncDatabaseManager:
    """
    统一异步数据库管理器（单例模式）

    职责:
    - 管理 AsyncEngine 的创建和生命周期
    - 提供 async_sessionmaker
    - 生成标准化的异步会话
    - 支持连接池配置和健康检查
    """

    _instance: "AsyncDatabaseManager | None" = None
    _initialized: bool = False

    def __new__(cls) -> "AsyncDatabaseManager":
        """实现单例模式"""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        """初始化数据库管理器"""
        if self._initialized:
            return

        self._async_engine: Optional[AsyncEngine] = None
        self._session_factory: Optional[async_sessionmaker] = None
        self._database_url: Optional[str] = None
        self._initialized = False

    def initialize(self, database_url: Optional[str] = None, **kwargs) -> None:
        """
        初始化数据库连接

        Args:
            database_url: 数据库连接URL，如果为None则从环境变量读取
            **kwargs: 额外的引擎配置参数
        """
        if self._initialized:
            logger.warning("AsyncDatabaseManager 已经初始化，跳过重复初始化")
            return

        # 获取数据库URL
        if database_url is None:
            # 优先级：ASYNC_DATABASE_URL > DATABASE_URL
            database_url = os.getenv(
                "ASYNC_DATABASE_URL",
                os.getenv(
                    "DATABASE_URL",
                    "postgresql+asyncpg://postgres:postgres@localhost:5432/football_prediction"
                ),
            )

        # 如果是同步URL，转换为异步URL
        if "postgresql://" in database_url:
            database_url = database_url.replace("postgresql://", "postgresql+asyncpg://")
        elif "sqlite://" in database_url and "+aiosqlite" not in database_url:
            database_url = database_url.replace("sqlite://", "sqlite+aiosqlite://")

        self._database_url = database_url

        # 默认连接池配置 - 根据数据库类型动态配置
        default_config = {
            "echo": kwargs.get("echo", False),
            "pool_pre_ping": kwargs.get("pool_pre_ping", True),
        }

        # 只有非SQLite数据库才使用连接池配置
        if not database_url.startswith("sqlite+aiosqlite"):
            default_config.update({
                "pool_size": kwargs.get("pool_size", 10),
                "max_overflow": kwargs.get("max_overflow", 20),
                "pool_timeout": kwargs.get("pool_timeout", 30),
                "pool_recycle": kwargs.get("pool_recycle", 3600),
            })

        # 创建异步引擎
        self._async_engine = create_async_engine(
            database_url,
            **default_config,
        )

        # 创建会话工厂
        self._session_factory = async_sessionmaker(
            bind=self._async_engine,
            class_=AsyncSession,
            expire_on_commit=False,
            autoflush=True,
            autocommit=False,
        )

        self._initialized = True

        # 构建日志信息
        log_msg = f"✅ AsyncDatabaseManager 初始化成功\n数据库URL: {self._database_url}"
        if 'pool_size' in default_config and 'max_overflow' in default_config:
            log_msg += f"\n   连接池: size={default_config['pool_size']}, overflow={default_config['max_overflow']}"

        logger.info(log_msg)

    @property
    def is_initialized(self) -> bool:
        """检查是否已初始化"""
        return self._initialized

    @property
    def engine(self) -> AsyncEngine:
        """获取异步引擎"""
        if not self._initialized or self._async_engine is None:
            raise RuntimeError(
                "AsyncDatabaseManager 未初始化！"
                "请先调用 initialize_database() 或设置 DATABASE_URL 环境变量。"
            )
        return self._async_engine

    @property
    def session_factory(self) -> async_sessionmaker:
        """获取会话工厂"""
        if not self._initialized or self._session_factory is None:
            raise RuntimeError("AsyncDatabaseManager 未初始化！")
        return self._session_factory

    async def check_connection(self) -> dict:
        """
        检查数据库连接健康状态

        Returns:
            包含连接状态信息的字典
        """
        if not self._initialized:
            return {
                "status": "error",
                "message": "数据库管理器未初始化",
                "response_time_ms": None,
            }

        try:
            import time

            start_time = time.time()

            async with self._session_factory() as session:
                # 使用 scalar() 替代 execute()，避免 server-side cursor 问题
                await session.scalar(text("SELECT 1"))
                response_time_ms = int((time.time() - start_time) * 1000)

                # scalar() 会自动处理结果，无需手动 commit

            return {
                "status": "healthy",
                "message": "连接正常",
                "response_time_ms": response_time_ms,
                "database_url": self._database_url,
            }

        except Exception as e:
            logger.error(f"❌ 数据库连接检查失败: {e}", exc_info=True)
            return {
                "status": "error",
                "message": f"连接失败: {str(e)}",
                "response_time_ms": None,
            }

    async def close(self) -> None:
        """关闭数据库连接"""
        if self._async_engine is not None:
            await self._async_engine.dispose()
            logger.info("🔌 AsyncDatabaseManager 连接已关闭")
        self._initialized = False

    def __repr__(self) -> str:
        return (
            f"AsyncDatabaseManager("
            f"initialized={self._initialized}, "
            f"database_url={self._database_url})"
        )


class MultiUserDatabaseManager(AsyncDatabaseManager):
    """
    多用户数据库管理器（简化版）

    为向后兼容而保留，实际功能与 AsyncDatabaseManager 相同
    """

    def __init__(self):
        """初始化多用户数据库管理器"""
        super().__init__()
        self.readers = []
        self.writers = []
        self.admins = []


def get_multi_user_database_manager() -> MultiUserDatabaseManager:
    """
    获取多用户数据库管理器（向后兼容）

    Returns:
        MultiUserDatabaseManager 实例
    """
    return MultiUserDatabaseManager()


# 全局单例实例
_db_manager = AsyncDatabaseManager()


def initialize_database(database_url: Optional[str] = None, **kwargs) -> None:
    """
    初始化数据库管理器（应用启动时调用一次）

    Args:
        database_url: 数据库连接URL
        **kwargs: 额外的引擎配置参数
    """
    _db_manager.initialize(database_url, **kwargs)


def get_database_manager() -> AsyncDatabaseManager:
    """
    获取数据库管理器单例

    Returns:
        AsyncDatabaseManager 实例
    """
    if not _db_manager.is_initialized:
        raise RuntimeError(
            "数据库管理器未初始化！请在应用启动时调用 initialize_database()"
        )
    return _db_manager


@asynccontextmanager
async def get_db_session() -> AsyncGenerator[AsyncSession, None]:
    """
    获取异步数据库会话（上下文管理器）

    这是推荐的数据库会话获取方式，遵循 FastAPI 最佳实践。

    使用示例:
        async with get_db_session() as session:
            result = await session.execute(select(Match))
            matches = result.scalars().all()

    Yields:
        AsyncSession: 异步数据库会话
    """
    manager = get_database_manager()

    async with manager.session_factory() as session:
        try:
            yield session
        except Exception as e:
            await session.rollback()
            logger.error(f"数据库会话异常，已回滚: {e}", exc_info=True)
            raise
        finally:
            await session.close()


# FastAPI 依赖注入函数
async def get_async_db_session() -> AsyncGenerator[AsyncSession, None]:
    """
    FastAPI 依赖注入函数

    使用示例:
        from fastapi import Depends

        @app.get("/matches/")
        async def get_matches(session: AsyncSession = Depends(get_async_db_session)):
            result = await session.execute(select(Match))
            return result.scalars().all()
    """
    async with get_db_session() as session:
        yield session


# 向后兼容性别名（避免破坏现有代码）
get_session = get_async_db_session


# ============================================================================
# 🔧 便捷查询方法（简化数据库操作）
# ============================================================================

async def fetch_all(query, params: Optional[dict] = None) -> list[dict]:
    """
    执行查询并返回所有结果

    Args:
        query: SQLAlchemy查询对象或SQL字符串
        params: 查询参数字典

    Returns:
        查询结果列表，每个元素为字典

    Example:
        from sqlalchemy import text
        results = await fetch_all(text("SELECT * FROM matches WHERE season = :season"), {"season": "2023"})
    """
    async with get_db_session() as session:
        if isinstance(query, str):
            query = text(query)

        result = await session.execute(query, params or {})
        return [dict(row._mapping) for row in result.fetchall()]


async def fetch_one(query, params: Optional[dict] = None) -> Optional[dict]:
    """
    执行查询并返回单个结果

    Args:
        query: SQLAlchemy查询对象或SQL字符串
        params: 查询参数字典

    Returns:
        单个查询结果字典，如果没有结果则返回None

    Example:
        from sqlalchemy import text
        result = await fetch_one(text("SELECT * FROM matches WHERE id = :match_id"), {"match_id": 123})
    """
    async with get_db_session() as session:
        if isinstance(query, str):
            query = text(query)

        result = await session.execute(query, params or {})
        row = result.fetchone()
        return dict(row._mapping) if row else None


async def execute(query, params: Optional[dict] = None) -> Any:
    """
    执行SQL语句（INSERT, UPDATE, DELETE等）

    Args:
        query: SQLAlchemy查询对象或SQL字符串
        params: 查询参数字典

    Returns:
        执行结果

    Example:
        from sqlalchemy import text
        await execute(text("INSERT INTO matches (id, name) VALUES (:id, :name)"), {"id": 1, "name": "Test Match"})
    """
    async with get_db_session() as session:
        if isinstance(query, str):
            query = text(query)

        result = await session.execute(query, params or {})
        await session.commit()
        return result


# 导出统一接口
__all__ = [
    "DatabaseRole",  # 角色枚举（向后兼容）
    "AsyncDatabaseManager",
    "MultiUserDatabaseManager",  # 向后兼容
    "initialize_database",
    "get_database_manager",
    "get_multi_user_database_manager",  # 向后兼容
    "get_db_session",
    "get_async_db_session",  # FastAPI 专用
    "get_session",  # 向后兼容
    # 新增的便捷方法
    "fetch_all",
    "fetch_one",
    "execute",
]
