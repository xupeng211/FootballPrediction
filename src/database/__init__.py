"""
足球预测系统 - 数据库模块

此模块提供PostgreSQL数据库连接、会话管理和基础配置。
"""

from .base import Base
from .connection import DatabaseManager, get_async_db_session, get_db_session
from .db_pool import DatabasePool, get_db_pool

__all__ = [
    "DatabaseManager",
    "get_db_session",
    "get_async_db_session",
    "Base",
    "DatabasePool",
    "get_db_pool",
]

# 配置现在通过 config_unified.py 管理
from src.config_unified import get_settings


def get_database_config():
    """获取数据库配置（兼容旧代码）"""
    settings = get_settings()
    return settings.database
