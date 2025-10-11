# mypy: ignore-errors
"""
数据库健康检查模块
Database Health Check Module

提供数据库连接健康检查功能。
"""

from typing import Dict, Any, Optional
from sqlalchemy import text
from sqlalchemy.engine import Engine
from sqlalchemy.ext.asyncio import AsyncEngine
import asyncio
import logging

logger = logging.getLogger(__name__)


async def check_database_health(
    engine: Engine | AsyncEngine, timeout: float = 5.0
) -> Dict[str, Any]:
    """检查数据库健康状态

    Args:
        engine: 数据库引擎
        timeout: 超时时间（秒）

    Returns:
        Dict[str, Any]: 健康状态信息
    """
    health_info = {
        "status": "unhealthy",
        "error": None,
        "response_time": None,
        "database_info": None,
    }

    try:
        start_time = asyncio.get_event_loop().time()

        # 执行简单查询
        if isinstance(engine, AsyncEngine):
            async with engine.connect() as conn:
                result = await conn.execute(text("SELECT 1"))
                await result.fetchone()

                # 获取数据库信息
                try:
                    result = await conn.execute(text("SELECT version()"))
                    version = (await result.fetchone())[0]
                    health_info["database_info"] = {"version": version}
                except (SQLAlchemyError, DatabaseError, ConnectionError, TimeoutError):
                    pass
        else:
            with engine.connect() as conn:
                result = conn.execute(text("SELECT 1"))
                result.fetchone()

                # 获取数据库信息
                try:
                    result = conn.execute(text("SELECT version()"))
                    version = result.fetchone()[0]
                    health_info["database_info"] = {"version": version}
                except (SQLAlchemyError, DatabaseError, ConnectionError, TimeoutError):
                    pass

        # 计算响应时间
        end_time = asyncio.get_event_loop().time()
        health_info["response_time"] = end_time - start_time
        health_info["status"] = "healthy"

        logger.info(
            f"Database health check passed in {health_info['response_time']:.3f}s"
        )

    except asyncio.TimeoutError:
        health_info["error"] = f"Database health check timed out after {timeout}s"
        health_info["status"] = "timeout"
        logger.error(health_info["error"])

    except (SQLAlchemyError, DatabaseError, ConnectionError, TimeoutError) as e:
        health_info["error"] = str(e)
        health_info["status"] = "unhealthy"
        logger.error(f"Database health check failed: {e}")

    return health_info


async def check_database_connection(
    engine: Engine | AsyncEngine, query: Optional[str] = None
) -> bool:
    """检查数据库连接

    Args:
        engine: 数据库引擎
        query: 测试查询（默认为SELECT 1）

    Returns:
        bool: 是否连接成功
    """
    if query is None:
        query = "SELECT 1"

    try:
        if isinstance(engine, AsyncEngine):
            async with engine.connect() as conn:
                await conn.execute(text(query))
        else:
            with engine.connect() as conn:
                conn.execute(text(query))
        return True
    except (SQLAlchemyError, DatabaseError, ConnectionError, TimeoutError) as e:
        logger.error(f"Database connection check failed: {e}")
        return False
