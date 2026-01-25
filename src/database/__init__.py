"""
足球预测系统 - 数据库模块

此模块提供PostgreSQL数据库连接、会话管理和基础配置。

V76.100: 移除 SQLAlchemy 双轨制，统一使用 asyncpg (DatabasePool)
"""

from .base import Base
from .db_pool import DatabasePool, get_db_pool
from .async_dependencies import get_db_connection

__all__ = [
    "Base",
    "DatabasePool",
    "get_db_pool",
    "get_db_connection",  # V76.100: FastAPI 依赖注入
]

# 配置现在通过 config_unified.py 管理
from src.config_unified import get_settings


def get_database_config():
    """获取数据库配置（兼容旧代码）"""
    settings = get_settings()
    return settings.database
