"""数据库连接管理模块（向后兼容层）
Database Connection Management Module (Backward Compatibility Layer).

⚠️ 警告：此文件已被弃用！
⚠️ WARNING: This file is DEPRECATED!

新的统一接口位于: src/database/async_manager.py
New unified interface is at: src/database/async_manager.py

请使用新的接口:
- initialize_database(database_url)  # 初始化
- get_db_session()  # 获取异步会话（上下文管理器）
- get_async_db_session()  # FastAPI依赖注入

For new code, please use the new interface in src/database/async_manager.py
"""

import logging
from collections.abc import AsyncGenerator, Generator

from sqlalchemy import create_engine
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import Session, sessionmaker

from .async_manager import (
    get_db_session as _new_get_db_session,
    initialize_database as _new_initialize,
    AsyncDatabaseManager,
)

logger = logging.getLogger(__name__)

# ============================================================================
# ⚠️ 过时的接口 - 保留仅用于向后兼容
# ⚠️ DEPRECATED INTERFACES - Kept only for backward compatibility
# ============================================================================

# 这些接口已经移动到 async_manager.py
# 如需使用，请直接导入 from src.database.async_manager import

__all__ = [
    # 核心类（已移动到 async_manager.py）
    "AsyncDatabaseManager",
    # 初始化函数（已移动到 async_manager.py）
    "initialize_database",
    "get_database_manager",
    # 会话获取（已移动到 async_manager.py）
    "get_db_session",
    "get_async_db_session",
    # 向后兼容性别名（保留所有旧导出）
    "get_async_session",
    "get_session",
    "DatabaseRole",
    "MultiUserDatabaseManager",
    "get_multi_user_database_manager",
]

# ============================================================================
# 向后兼容性别名（标记为过时）
# DEPRECATED ALIASES - Marked as deprecated
# ============================================================================

# 新的初始化函数
def initialize_database(database_url=None, **kwargs):
    """⚠️ DEPRECATED: 使用 src.database.async_manager.initialize_database"""
    import warnings

    warnings.warn(
        "initialize_database() 已迁移到 src.database.async_manager 模块。\n"
        "请更新导入: from src.database.async_manager import initialize_database",
        DeprecationWarning,
        stacklevel=2,
    )
    _new_initialize(database_url, **kwargs)


# 新的会话获取函数
async def get_async_db_session() -> AsyncGenerator[AsyncSession, None]:
    """⚠️ DEPRECATED: 使用 src.database.async_manager.get_async_db_session"""
    import warnings

    warnings.warn(
        "get_async_db_session() 已迁移到 src/database/async_manager 模块。\n"
        "请更新导入: from src.database.async_manager import get_async_db_session",
        DeprecationWarning,
        stacklevel=2,
    )

    # 直接使用新的实现
    async with _new_get_db_session() as session:
        yield session


# 向后兼容性别名
get_session = get_async_db_session


# ============================================================================
# 🚨 额外的向后兼容导出（保留旧接口）
# 🚨 ADDITIONAL BACKWARD COMPATIBILITY EXPORTS (Keep old interfaces)
# ============================================================================

# 从 async_manager 导入所有需要向后兼容的符号
from .async_manager import (
    AsyncDatabaseManager as _AsyncDatabaseManager,
    DatabaseRole,
    MultiUserDatabaseManager,
    get_multi_user_database_manager,
)

# 重新导出以保持兼容性
AsyncDatabaseManager = _AsyncDatabaseManager


# 为了向后兼容，提供旧的函数别名
async def get_async_session() -> AsyncGenerator[AsyncSession, None]:
    """
    ⚠️ DEPRECATED: 使用 src.database.async_manager.get_async_db_session

    保持向后兼容的旧函数名
    """
    import warnings

    warnings.warn(
        "get_async_session() 已弃用，请使用 src.database.async_manager.get_async_db_session",
        DeprecationWarning,
        stacklevel=2,
    )

    # 直接使用新的实现
    async with get_db_session() as session:
        yield session


# 为了完全向后兼容，确保所有旧符号都可用
get_db_session = get_async_db_session
get_async_admin_session = get_async_db_session
get_async_reader_session = get_async_db_session
get_async_writer_session = get_async_db_session
get_admin_session = get_async_admin_session
get_reader_session = get_async_reader_session
get_writer_session = get_async_writer_session

# 数据库管理器别名（向后兼容）
DatabaseManager = AsyncDatabaseManager


# ============================================================================
# 🚫 完全移除的内容
# 🚫 COMPLETELY REMOVED CONTENT
# ============================================================================

"""
以下内容已完全移除，请使用新的统一接口：

❌ 旧的 DatabaseManager 单例模式 -> ✅ 使用 AsyncDatabaseManager
❌ 旧的 get_db_session() 同步会话 -> ✅ 使用 get_async_db_session()
❌ 混用同步/异步代码 -> ✅ 完全异步
❌ 多个会话获取入口 -> ✅ 单一入口：get_db_session()

新的使用方式:

1. 应用启动时初始化（通常在 main.py 中）:
   from src.database.async_manager import initialize_database

   initialize_database()

2. 在 FastAPI 路由中使用:
   from fastapi import Depends
   from src.database.async_manager import get_async_db_session

   @app.get("/matches/")
   async def get_matches(session: AsyncSession = Depends(get_async_db_session)):
       result = await session.execute(select(Match))
       return result.scalars().all()

3. 在爬虫脚本中使用:
   from src.database.async_manager import get_db_session

   async def crawl_fotmob():
       async with get_db_session() as session:
           # 执行数据库操作
           pass

4. 检查数据库健康状态:
   from src.database.async_manager import get_database_manager

   manager = get_database_manager()
   health = await manager.check_connection()
   print(health)
"""
