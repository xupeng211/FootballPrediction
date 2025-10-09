"""
足球预测系统 - 数据库模块

此模块提供PostgreSQL数据库连接、会话管理和基础配置。
"""

# 从兼容性模块导入全局函数

from typing import cast, Any, Optional, Union

from .base import Base
from .compatibility import get_async_db_session, get_db_session
from .config import DatabaseConfig, get_database_config
from .connection import DatabaseManager

__all__ = [
    "DatabaseConfig",
    "get_database_config",
    "DatabaseManager",
    "get_db_session",
    "get_async_db_session",
    "Base",
]
