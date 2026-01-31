from typing import Optional

"""数据收集器模块
负责从各种数据源收集足球相关数据.
"""

# 只有存在的文件才导入
from .base_collector import BaseCollector

__all__ = [
    "BaseCollector",
]
