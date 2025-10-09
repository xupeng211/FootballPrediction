"""
streaming_collector.py
streaming_collector

此文件已被拆分为多个模块以提供更好的组织结构。
This file has been split into multiple modules for better organization.

为了向后兼容，此文件重新导出所有模块中的类。
For backward compatibility, this file re-exports all classes from the modules.
"""


import warnings

from .........src.data.collectors.streaming import kafka_collector
from .........src.data.collectors.streaming import manager
from .........src.data.collectors.streaming import processor
from .........src.data.collectors.streaming import websocket_collector

warnings.warn(
    "直接从 streaming_collector 导入已弃用。"
    "请从 src/data/collectors/streaming 导入相关类。",
    DeprecationWarning,
    stacklevel=2
)

# 从新模块导入所有内容

# 导出所有类
__all__ = [
    "kafka_collector", "websocket_collector", "processor", "manager"
]
