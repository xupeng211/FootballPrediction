"""
数据库连接管理模块
Database Connection Management Module

提供数据库连接、会话管理和权限控制功能。
"""

from .manager import DatabaseManager
from .multi_user_manager import MultiUserDatabaseManager
from .roles import DatabaseRole
from .factory import (
    get_database_manager,
    get_multi_user_database_manager,
    initialize_database,
    initialize_multi_user_database,
    initialize_test_database,
)
from .sessions import (
    get_db_session,
    get_reader_session,
    get_writer_session,
    get_admin_session,
    get_session,
    get_async_session,
    get_async_reader_session,
    get_async_writer_session,
    get_async_admin_session,
)

__all__ = [
    # 核心管理器
    "DatabaseManager",
    "MultiUserDatabaseManager",

    # 角色定义
    "DatabaseRole",

    # 工厂函数
    "get_database_manager",
    "get_multi_user_database_manager",
    "initialize_database",
    "initialize_multi_user_database",
    "initialize_test_database",

    # 会话获取
    "get_db_session",
    "get_reader_session",
    "get_writer_session",
    "get_admin_session",
    "get_session",
    "get_async_session",
    "get_async_reader_session",
    "get_async_writer_session",
    "get_async_admin_session",
]