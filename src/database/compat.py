"""
数据库兼容适配器（临时过渡用）
Database Compatibility Adapter (Temporary Migration Helper)

⚠️ 注意：这是临时适配器，用于逐步迁移到异步接口
⚠️ WARNING: This is a temporary adapter for gradual migration to async interfaces

使用方法：
1. 短期：直接替换 import 语句
   from src.database.compat import fetch_all_sync, fetch_one_sync, execute_sync

2. 中期：逐步将函数改为 async
   async def my_function():
       result = await fetch_all(query, params)

3. 长期：完全迁移到 async_manager.py
   from src.database.async_manager import fetch_all
"""

import asyncio
import logging
from typing import Any, Optional, , 
from sqlalchemy import text

from .async_manager import fetch_all, fetch_one, execute

logger = logging.getLogger(__name__)


def fetch_all_sync(query, params: Optional[dict[str, Any]] = None) -> list[dict[str, Any]]:
    """
    同步版本的 fetch_all（适配器）

    Args:
        query: SQL查询语句或SQLAlchemy对象
        params: 查询参数字典

    Returns:
        查询结果列表

    Warning:
        此函数使用 asyncio.run()，不适用于已有事件循环的环境
        仅用于临时迁移，尽快改为异步版本
    """
    logger.warning(
        "⚠️ 使用同步适配器 fetch_all_sync，建议改为异步版本。"
        "文件位置需要重构以支持异步操作。"
    )
    try:
        # 尝试在现有事件循环中运行
        asyncio.get_running_loop()
        # 如果已有事件循环，创建任务
        import concurrent.futures
        with concurrent.futures.ThreadPoolExecutor() as executor:
            future = executor.submit(asyncio.run, fetch_all(query, params))
            return future.result()
    except RuntimeError:
        # 没有事件循环，使用 asyncio.run
        return asyncio.run(fetch_all(query, params))


def fetch_one_sync(query, params: Optional[dict[str, Any]] = None) -> Optional[dict[str, Any]]:
    """
    同步版本的 fetch_one（适配器）

    Args:
        query: SQL查询语句或SQLAlchemy对象
        params: 查询参数字典

    Returns:
        单个查询结果字典或None

    Warning:
        此函数使用 asyncio.run()，不适用于已有事件循环的环境
        仅用于临时迁移，尽快改为异步版本
    """
    logger.warning(
        "⚠️ 使用同步适配器 fetch_one_sync，建议改为异步版本。"
        "文件位置需要重构以支持异步操作。"
    )
    try:
        # 尝试在现有事件循环中运行
        asyncio.get_running_loop()
        # 如果已有事件循环，创建任务
        import concurrent.futures
        with concurrent.futures.ThreadPoolExecutor() as executor:
            future = executor.submit(asyncio.run, fetch_one(query, params))
            return future.result()
    except RuntimeError:
        # 没有事件循环，使用 asyncio.run
        return asyncio.run(fetch_one(query, params))


def execute_sync(query, params: Optional[dict[str, Any]] = None) -> Any:
    """
    同步版本的 execute（适配器）

    Args:
        query: SQL语句或SQLAlchemy对象
        params: 查询参数字典

    Returns:
        执行结果

    Warning:
        此函数使用 asyncio.run()，不适用于已有事件循环的环境
        仅用于临时迁移，尽快改为异步版本
    """
    logger.warning(
        "⚠️ 使用同步适配器 execute_sync，建议改为异步版本。"
        "文件位置需要重构以支持异步操作。"
    )
    try:
        # 尝试在现有事件循环中运行
        asyncio.get_running_loop()
        # 如果已有事件循环，创建任务
        import concurrent.futures
        with concurrent.futures.ThreadPoolExecutor() as executor:
            future = executor.submit(asyncio.run, execute(query, params))
            return future.result()
    except RuntimeError:
        # 没有事件循环，使用 asyncio.run
        return asyncio.run(execute(query, params))


# ============================================================================
# 向后兼容的包装函数（用于最常见的场景）
# ============================================================================

class DatabaseCompatManager:
    """
    数据库兼容管理器

    提供与旧 DatabaseManager 类似的接口，但内部使用新的异步实现
    临时用于减少迁移风险
    """

    def __init__(self):
        """初始化兼容管理器"""
        logger.warning("⚠️ 使用 DatabaseCompatManager，建议迁移到 AsyncDatabaseManager")

    def get_session(self):
        """获取数据库会话（同步接口 - 临时兼容）"""
        logger.warning("⚠️ get_session() 同步接口已弃用，请改为异步实现")
        # 返回一个兼容的会话包装器
        return SyncSessionWrapper()


class SyncSessionWrapper:
    """
    同步会话包装器（临时兼容用）

    提供类似旧版同步会话的接口，但内部使用异步实现
    """

    def __init__(self):
        self._closed = False

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()

    def execute(self, query, params=None):
        """执行查询（同步包装）"""
        if isinstance(query, str):
            query = text(query)
        return execute_sync(query, params)

    def fetchall(self, query, params=None):
        """获取所有结果（同步包装）"""
        return fetch_all_sync(query, params)

    def fetchone(self, query, params=None):
        """获取单个结果（同步包装）"""
        return fetch_one_sync(query, params)

    def close(self):
        """关闭会话"""
        self._closed = True
        logger.debug("SyncSessionWrapper 已关闭")

    def commit(self):
        """提交事务（兼容方法）"""
        logger.debug("SyncSessionWrapper commit (兼容方法)")

    def rollback(self):
        """回滚事务（兼容方法）"""
        logger.debug("SyncSessionWrapper rollback (兼容方法)")


# 导出接口
__all__ = [
    # 主要适配器函数
    "fetch_all_sync",
    "fetch_one_sync",
    "execute_sync",
    # 兼容管理器类
    "DatabaseCompatManager",
    "SyncSessionWrapper",
]
