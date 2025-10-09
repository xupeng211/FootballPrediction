"""
src/database/compatibility 模块
统一导出接口
"""

from .sqlite_compat import *
from .postgres_compat import *
from .dialects import *
from .compatibility import *

# 导出所有类
__all__ = [
    "sqlite_compat", "postgres_compat", "dialects", "compatibility"
]
