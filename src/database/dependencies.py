"""
FastAPI 依赖注入模块

提供数据库会话的依赖注入函数,用于替换全局会话模式。
支持同步和异步会话管理.
"""

from collections.abc import AsyncGenerator, Generator

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Session

from src.database.definitions import (
    get_async_reader_session,
    get_async_session,
    get_async_writer_session,
    get_db_session,
    get_reader_session,
    get_writer_session,
)


def get_db() -> Generator[Session, None, None]:
    """
    获取数据库会话的依赖注入函数

    用于 FastAPI 路由中,提供同步数据库会话。
    确保每个请求都有独立的数据库会话.

    Yields:
        Session: SQLAlchemy 数据库会话
    """
    session = get_db_session()
    try:
        yield session
    finally:
        session.close()


async def get_async_db() -> AsyncGenerator[AsyncSession, None]:
    """
    获取异步数据库会话的依赖注入函数

    用于 FastAPI 异步路由中,提供异步数据库会话。
    确保每个请求都有独立的异步数据库会话.

    Yields:
        AsyncSession: SQLAlchemy 异步数据库会话
    """
    session = get_async_session()
    try:
        yield session
    finally:
        await session.close()


def get_reader_db() -> Generator[Session, None, None]:
    """
    获取只读数据库会话的依赖注入函数

    用于执行只读操作的路由.

    Yields:
        Session: 只读数据库会话
    """
    session = get_reader_session()
    try:
        yield session
    finally:
        session.close()


def get_writer_db() -> Generator[Session, None, None]:
    """
    获取写入数据库会话的依赖注入函数

    用于执行写入操作的路由.

    Yields:
        Session: 写入数据库会话
    """
    session = get_writer_session()
    try:
        yield session
    finally:
        session.close()


async def get_async_reader_db() -> AsyncGenerator[AsyncSession, None]:
    """
    获取异步只读数据库会话的依赖注入函数

    用于异步只读操作的路由.

    Yields:
        AsyncSession: 异步只读数据库会话
    """
    session = get_async_reader_session()
    try:
        yield session
    finally:
        await session.close()


async def get_async_writer_db() -> AsyncGenerator[AsyncSession, None]:
    """
    获取异步写入数据库会话的依赖注入函数

    用于异步写入操作的路由.

    Yields:
        AsyncSession: 异步写入数据库会话
    """
    session = get_async_writer_session()
    try:
        yield session
    finally:
        await session.close()


# 为了向后兼容,保留原有的函数名
get_db_session_legacy = get_db  # 重命名避免重复定义
get_async_db_session_legacy = get_async_db  # 重命名避免重复定义


# 测试专用的依赖注入函数
def get_test_db() -> Generator[Session, None, None]:
    """
    测试用的数据库会话依赖注入函数

    在测试环境中使用,可以提供内存数据库或其他测试专用配置.

    Yields:
        Session: 测试数据库会话
    """
    # 这里可以在测试环境中替换为内存数据库
    session = get_db_session()
    try:
        yield session
    finally:
        session.close()


async def get_test_async_db() -> AsyncGenerator[AsyncSession, None]:
    """
    测试用的异步数据库会话依赖注入函数

    在测试环境中使用,提供异步测试数据库会话.

    Yields:
        AsyncSession: 异步测试数据库会话
    """
    # 这里可以在测试环境中替换为内存数据库
    session = get_async_session()
    try:
        yield session
    finally:
        await session.close()


# 便捷的依赖注入对象,可以直接在路由中使用
db_session = Depends(get_db)
async_db_session = Depends(get_async_db)
reader_db = Depends(get_reader_db)
writer_db = Depends(get_writer_db)
async_reader_db = Depends(get_async_reader_db)
async_writer_db = Depends(get_async_writer_db)

# 测试用的便捷依赖
test_db = Depends(get_test_db)
test_async_db = Depends(get_test_async_db)

__all__ = [
    # 同步依赖注入函数
    "get_db",
    "get_db_session",
    "get_reader_db",
    "get_writer_db",
    # 异步依赖注入函数
    "get_async_db",
    # "get_async_db_session",  # 注释以避免F822错误
    "get_async_reader_db",
    "get_async_writer_db",
    # 测试专用
    "get_test_db",
    "get_test_async_db",
    # 便捷依赖对象
    "db_session",
    "async_db_session",
    "reader_db",
    "writer_db",
    "async_reader_db",
    "async_writer_db",
    "test_db",
    "test_async_db",
]
