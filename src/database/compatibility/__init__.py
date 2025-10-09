"""
src/database/compatibility 模块
统一导出接口
"""


from .compatibility import *  # type: ignore
from .dialects import *  # type: ignore
from .postgres_compat import *  # type: ignore
from .sqlite_compat import *  # type: ignore

# 导出所有类
__all__ = [  # type: ignore
    "sqlite_compat",
    "postgres_compat",
    "dialects",
    "compatibility",
]
