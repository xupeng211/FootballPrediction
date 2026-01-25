#!/usr/bin/env python3
"""
V76.100 - Async Database Dependencies
=====================================

统一异步数据库依赖注入，替代 SQLAlchemy 双轨制。

提供 FastAPI 兼容的依赖注入函数，基于 asyncpg 连接池。
"""

import logging
from typing import AsyncGenerator

from fastapi import Depends

from src.database.db_pool import DatabasePool

logger = logging.getLogger(__name__)


async def get_db_connection() -> AsyncGenerator:
    """
    FastAPI 依赖注入 - 获取异步数据库连接

    使用示例:
        @app.get("/api/endpoint")
        async def endpoint(conn = Depends(get_db_connection)):
            result = await conn.fetchrow("SELECT * FROM matches LIMIT 1")
            return result

    Yields:
        Connection: asyncpg 连接对象
    """
    pool = DatabasePool.get_instance()

    async with pool.get_connection() as conn:
        yield conn


async def get_db_legacy() -> AsyncGenerator:
    """
    兼容层 - 为旧代码提供 db 别名

    注意: 这是临时兼容层，新代码应使用 conn 作为变量名
    """
    pool = DatabasePool.get_instance()

    async with pool.get_connection() as db:
        yield db


__all__ = ["get_db_connection", "get_db_legacy"]
