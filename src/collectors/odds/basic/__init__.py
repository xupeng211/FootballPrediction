"""
src/collectors/odds/basic 模块
统一导出接口
"""

from .collector import *  # type: ignore
from .parser import *  # type: ignore
from .validator import *  # type: ignore
from .storage import *  # type: ignore

# 导出所有类
__all__ = [  # type: ignore
    "collector",
    "parser",
    "validator",
    "storage",
]
