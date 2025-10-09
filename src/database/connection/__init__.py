"""
数据库连接管理模块 / Database Connection Management Module

提供同步和异步的PostgreSQL数据库连接、会话管理和生命周期控制。
支持多用户权限分离的数据库连接管理。
集成重试机制以提高连接可靠性。

Provides synchronous and asynchronous PostgreSQL database connection, session management,
and lifecycle control. Supports multi-user permission-separated database connection management.
Integrates retry mechanisms to improve connection reliability.
"""

# 导出核心接口以保持向后兼容
from .managers.database_manager import DatabaseManager
from .managers.multi_user_manager import MultiUserDatabaseManager
from .core import DatabaseRole, DATABASE_RETRY_CONFIG

# 创建一个全局数据库管理器实例
_database_manager = DatabaseManager()

def get_database_manager():
    """获取数据库管理器实例"""
    return _database_manager

def initialize_database():
    """初始化数据库"""
    from ..connection import initialize_database as _initialize_database
    return _initialize_database()

# 为了避免循环导入，将get_async_session的定义放在这里
async def get_async_session(role=DatabaseRole.READER):
    """获取异步数据库会话"""
    from ..connection import get_async_session as _get_async_session
    async for session in _get_async_session(role):
        yield session

__all__ = [
    "DatabaseManager",
    "MultiUserDatabaseManager",
    "DatabaseRole",
    "DATABASE_RETRY_CONFIG",
    "get_async_session",
    "get_database_manager",
    "initialize_database",
]