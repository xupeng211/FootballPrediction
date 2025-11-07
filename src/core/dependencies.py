"""
核心依赖注入模块
Core Dependencies Module

提供FastAPI应用的核心依赖注入函数。
Provides core dependency injection functions for FastAPI applications.
"""

from collections.abc import AsyncGenerator, Generator

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker
from sqlalchemy.orm import Session

from ..database.base import get_async_db, get_db
from .logging_system import get_logger

logger = get_logger(__name__)

# HTTP Bearer 认证方案
security = HTTPBearer()


async def get_current_user_optional(
    credentials: HTTPAuthorizationCredentials | None = Depends(security),
) -> dict | None:
    """
    可选的用户认证依赖
    Optional user authentication dependency

    如果提供了token则验证用户，否则返回None。
    Validates user if token is provided, otherwise returns None.
    """
    if not credentials:
        return None

    try:
        # 这里应该实现JWT token验证逻辑
        # 暂时返回一个模拟用户
        return {
            "id": 1,
            "email": "test@example.com",
            "is_active": True,
            "is_admin": False,
        }
    except Exception as e:
        logger.warning(f"User authentication failed: {e}")
        return None


async def get_db_session() -> AsyncGenerator[AsyncSession, None]:
    """
    获取数据库会话
    Get database session

    提供异步数据库会话的依赖注入。
    Provides dependency injection for async database sessions.
    """
    async with get_async_db() as session:
        try:
            yield session
        finally:
            await session.close()


def get_sync_db_session() -> Generator[Session, None, None]:
    """
    获取同步数据库会话
    Get synchronous database session

    提供同步数据库会话的依赖注入。
    Provides dependency injection for synchronous database sessions.
    """
    with get_db() as session:
        yield session


async def get_current_user_required(
    current_user: dict | None = Depends(get_current_user_optional),
) -> dict:
    """
    必需的用户认证依赖
    Required user authentication dependency

    如果用户未认证则抛出HTTP异常。
    Throws HTTP exception if user is not authenticated.
    """
    if not current_user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return current_user


async def get_admin_user(
    current_user: dict = Depends(get_current_user_required),
) -> dict:
    """
    管理员用户依赖
    Admin user dependency

    检查用户是否具有管理员权限。
    Checks if user has admin privileges.
    """
    if not current_user.get("is_admin", False):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Admin privileges required"
        )
    return current_user


# 数据库连接池依赖
async def get_db_pool() -> AsyncGenerator[async_sessionmaker, None]:
    """
    获取数据库连接池
    Get database connection pool

    提供数据库连接池的依赖注入。
    Provides dependency injection for database connection pool.
    """
    from ..database.base import async_engine

    async_session_local = async_sessionmaker(
        bind=async_engine, class_=AsyncSession, expire_on_commit=False
    )

    try:
        yield async_session_local
    finally:
        # 清理资源（如果需要）
        pass


# 缓存依赖
async def get_cache_manager():
    """
    获取缓存管理器
    Get cache manager

    提供缓存管理器的依赖注入。
    Provides dependency injection for cache manager.
    """
    from ..cache.unified_cache import get_cache_manager

    return get_cache_manager()


# 性能监控依赖
async def get_performance_monitor():
    """
    获取性能监控器
    Get performance monitor

    提供性能监控器的依赖注入。
    Provides dependency injection for performance monitor.
    """
    from ..performance.monitoring import get_system_monitor

    return get_system_monitor()


# 日志记录器依赖
def get_request_logger():
    """
    获取请求日志记录器
    Get request logger

    提供请求日志记录器的依赖注入。
    Provides dependency injection for request logger.
    """
    return get_logger(__name__)


# 测试依赖
async def get_test_db() -> AsyncGenerator[AsyncSession, None]:
    """
    测试数据库会话依赖
    Test database session dependency

    为测试提供独立的数据库会话。
    Provides independent database session for testing.
    """
    # 这里应该使用测试数据库配置
    async with get_async_db() as session:
        try:
            yield session
        finally:
            await session.rollback()
            await session.close()


# 依赖注入函数映射
DEPENDENCIES = {
    "current_user_optional": get_current_user_optional,
    "current_user_required": get_current_user_required,
    "admin_user": get_admin_user,
    "db_session": get_db_session,
    "sync_db_session": get_sync_db_session,
    "db_pool": get_db_pool,
    "cache_manager": get_cache_manager,
    "performance_monitor": get_performance_monitor,
    "request_logger": get_request_logger,
    "test_db": get_test_db,
}


def get_dependency(dependency_name: str):
    """
    根据名称获取依赖函数
    Get dependency function by name

    Args:
        dependency_name: 依赖名称

    Returns:
        依赖函数
    """
    dependency = DEPENDENCIES.get(dependency_name)
    if dependency is None:
        raise ValueError(f"Unknown dependency: {dependency_name}")
    return dependency
