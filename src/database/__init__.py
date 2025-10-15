from typing import Any, Dict, List, Optional, Union

"""
足球预测系统 - 数据库模块

此模块提供PostgreSQL数据库连接、会话管理和基础配置。
"""

# 从兼容性模块导入全局函数

from .base import Base

# from .compatibility import get_async_db_session, get_db_session  # 暂时注释，compatibility模块不存在
from .config import DatabaseConfig, get_database_config
# from .connection import DatabaseManager  # 暂时注释，DatabaseManager未实现

__all__ = [
    "DatabaseConfig",
    "get_database_config",
    # "DatabaseManager",  # 暂时注释
    # "get_db_session",          # 暂时注释
    # "get_async_db_session",    # 暂时注释
    "Base",
]
