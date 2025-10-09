"""
src/collectors/odds/basic 模块
统一导出接口
"""

from .collector import *
from .parser import *
from .validator import *
from .storage import *

# 导出所有类
__all__ = [
    "collector", "parser", "validator", "storage"
]
