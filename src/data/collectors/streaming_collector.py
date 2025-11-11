"""
streaming_collector.py
streaming_collector

此文件已被拆分为多个模块以提供更好的组织结构。
This file has been split into multiple modules for better organization.

为了向后兼容,此文件重新导出所有模块中的类.
For backward compatibility, this file re-exports all classes from the modules.
"""

import warnings

warnings.warn(
    "直接从 streaming_collector 导入已弃用."
    "请从 src/data/collectors/streaming 导入相关类.",
    DeprecationWarning,
    stacklevel=2,
)

# 从新模块导入所有内容
try:
    from ..streaming.websocket_collector import WebSocketCollector

    websocket_collector = WebSocketCollector  # 直接赋值
except ImportError:
    # 如果新模块不存在,创建空的占位符
    kafka_collector = None
    websocket_collector = None
    processor = None
    manager = None

# 导出所有类
__all__ = ["kafka_collector", "websocket_collector", "processor", "manager"]
