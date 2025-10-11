"""
数据库引擎模块
Database Engine Module

提供数据库引擎创建和管理功能。
"""

from typing import Optional, Dict, Any
from sqlalchemy import create_engine, Engine
from sqlalchemy.ext.asyncio import AsyncEngine, create_async_engine
from sqlalchemy.pool import StaticPool
import logging

logger = logging.getLogger(__name__)


def get_engine(
    database_url: str,
    echo: bool = False,
    pool_size: int = 5,
    max_overflow: int = 10,
    **kwargs,
) -> Engine:
    """创建数据库引擎

    Args:
        database_url: 数据库URL
        echo: 是否打印SQL语句
        pool_size: 连接池大小
        max_overflow: 最大溢出连接数
        **kwargs: 其他参数

    Returns:
        Engine: 数据库引擎
    """
    engine_kwargs = {
        "echo": echo,
        "pool_size": pool_size,
        "max_overflow": max_overflow,
        **kwargs,
    }

    # SQLite特殊处理
    if database_url.startswith("sqlite"):
        engine_kwargs.update(
            {
                "poolclass": StaticPool,
                "connect_args": {
                    "check_same_thread": False,
                    "timeout": 20,
                },
            }
        )
    else:
        # PostgreSQL/MySQL配置
        engine_kwargs.update(
            {
                "pool_pre_ping": True,
                "pool_recycle": 3600,
            }
        )

    return create_engine(database_url, **engine_kwargs)


def get_engine_with_pool(
    database_url: str,
    pool_class: Optional[type] = None,
    pool_kwargs: Optional[Dict[str, Any]] = None,
    **kwargs,
) -> Engine:
    """创建带自定义连接池的数据库引擎

    Args:
        database_url: 数据库URL
        pool_class: 连接池类
        pool_kwargs: 连接池参数
        **kwargs: 其他参数

    Returns:
        Engine: 数据库引擎
    """
    engine_kwargs = kwargs.copy()

    if pool_class:
        engine_kwargs["poolclass"] = pool_class
        if pool_kwargs:
            engine_kwargs.update(pool_kwargs)

    return get_engine(database_url, **engine_kwargs)


def get_async_engine(
    database_url: str,
    echo: bool = False,
    pool_size: int = 5,
    max_overflow: int = 10,
    **kwargs,
) -> AsyncEngine:
    """创建异步数据库引擎

    Args:
        database_url: 数据库URL（asyncpg +postgresql）
        echo: 是否打印SQL语句
        pool_size: 连接池大小
        max_overflow: 最大溢出连接数
        **kwargs: 其他参数

    Returns:
        AsyncEngine: 异步数据库引擎
    """
    engine_kwargs = {
        "echo": echo,
        "pool_size": pool_size,
        "max_overflow": max_overflow,
        "pool_pre_ping": True,
        "pool_recycle": 3600,
        **kwargs,
    }

    return create_async_engine(database_url, **engine_kwargs)
