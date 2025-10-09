"""
src/data/collectors/streaming 模块
统一导出接口
"""

from .kafka_collector import *  # type: ignore
from .websocket_collector import *  # type: ignore
from .processor import *  # type: ignore
from .manager import *  # type: ignore

# 导出所有类
__all__ = [  # type: ignore
    "kafka_collector",
    "websocket_collector",
    "processor",
    "manager",
]
