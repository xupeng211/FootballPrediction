from .base import Base
from .config import DatabaseConfig, get_database_config
from .connection import DatabaseManager

"""
足球预测系统 - 数据库模块

此模块提供PostgreSQL数据库连接,会话管理和基础配置.
"""

__all__ = [
    "DatabaseConfig",
    "get_database_config",
    "DatabaseManager",
    # "get_db_session",          # 暂时注释
    # "get_async_db_session",    # 暂时注释
    "Base",
]
