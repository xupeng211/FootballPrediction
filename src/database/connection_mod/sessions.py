"""
会话获取辅助函数
Session Retrieval Helper Functions

提供便捷的会话获取函数。
"""

from contextlib import asynccontextmanager, contextmanager
from typing import AsyncGenerator, Generator, Optional

from sqlalchemy.orm import Session

from .factory import get_database_manager, get_multi_user_database_manager
from .roles import DatabaseRole


@contextmanager
def get_db_session() -> Generator[Session, None, None]:
    """
    获取默认数据库会话 / Get Default Database Session

    Returns:
        Generator[Session, None, None]: 数据库会话 / Database session
    """
    manager = get_database_manager()
    with manager.get_session() as session:
        yield session


@contextmanager
def get_reader_session() -> Generator[Session, None, None]:
    """
    获取只读用户会话 / Get Reader User Session

    Returns:
        Generator[Session, None, None]: 只读会话 / Read-only session
    """
    manager = get_multi_user_database_manager()
    with manager.get_session(role=DatabaseRole.READER) as session:
        yield session


@contextmanager
def get_writer_session() -> Generator[Session, None, None]:
    """
    获取读写用户会话 / Get Writer User Session

    Returns:
        Generator[Session, None, None]: 读写会话 / Read-write session
    """
    manager = get_multi_user_database_manager()
    with manager.get_session(role=DatabaseRole.WRITER) as session:
        yield session


@contextmanager
def get_admin_session() -> Generator[Session, None, None]:
    """
    获取管理员用户会话 / Get Admin User Session

    Returns:
        Generator[Session, None, None]: 管理员会话 / Admin session
    """
    manager = get_multi_user_database_manager()
    with manager.get_session(role=DatabaseRole.ADMIN) as session:
        yield session


@contextmanager
def get_session(role: Optional[str] = None) -> Generator[Session, None, None]:
    """
    获取指定角色的会话 / Get Session for Specific Role

    Args:
        role (Optional[str]): 角色名称 / Role name

    Returns:
        Generator[Session, None, None]: 数据库会话 / Database session
    """
    if role is None:
        with get_db_session() as session:
            yield session
    else:
        manager = get_multi_user_database_manager()
        with manager.get_session(role=role) as session:
            yield session


@asynccontextmanager
async def get_async_db_session() -> AsyncGenerator[Session, None]:
    """
    获取默认异步数据库会话 / Get Default Async Database Session

    Returns:
        AsyncGenerator[Session, None]: 异步数据库会话 / Async database session
    """
    manager = get_database_manager()
    async with manager.get_async_session() as session:
        yield session  # type: ignore


@asynccontextmanager
async def get_async_reader_session() -> AsyncGenerator[Session, None]:
    """
    获取只读用户异步会话 / Get Reader User Async Session

    Returns:
        AsyncGenerator[Session, None]: 只读异步会话 / Read-only async session
    """
    manager = get_multi_user_database_manager()
    async with manager.get_async_session(role=DatabaseRole.READER) as session:
        yield session  # type: ignore


@asynccontextmanager
async def get_async_writer_session() -> AsyncGenerator[Session, None]:
    """
    获取读写用户异步会话 / Get Writer User Async Session

    Returns:
        AsyncGenerator[Session, None]: 读写异步会话 / Read-write async session
    """
    manager = get_multi_user_database_manager()
    async with manager.get_async_session(role=DatabaseRole.WRITER) as session:
        yield session  # type: ignore


@asynccontextmanager
async def get_async_admin_session() -> AsyncGenerator[Session, None]:
    """
    获取管理员用户异步会话 / Get Admin User Async Session

    Returns:
        AsyncGenerator[Session, None]: 管理员异步会话 / Admin async session
    """
    manager = get_multi_user_database_manager()
    async with manager.get_async_session(role=DatabaseRole.ADMIN) as session:
        yield session  # type: ignore


@asynccontextmanager
async def get_async_session(
    role: Optional[str] = None,
) -> AsyncGenerator[Session, None]:
    """
    获取指定角色的异步会话 / Get Async Session for Specific Role

    Args:
        role (Optional[str]): 角色名称 / Role name

    Returns:
        AsyncGenerator[Session, None]: 异步数据库会话 / Async database session
    """
    if role is None:
        manager = get_database_manager()
        async with manager.get_async_session() as session:
            yield session  # type: ignore
    else:
        manager = get_multi_user_database_manager()  # type: ignore
        async with manager.get_async_session(role=role) as session:  # type: ignore
            yield session  # type: ignore


def create_session_factory(engine, **kwargs):
    """创建会话工厂

    Args:
        engine: 数据库引擎
        **kwargs: 会话参数

    Returns:
        sessionmaker: 会话工厂
    """
    from sqlalchemy.orm import sessionmaker

    return sessionmaker(bind=engine, **kwargs)
