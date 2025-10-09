"""
kafka_producer.py
Kafka_Producer

此文件已被拆分为多个模块以提供更好的组织结构。
This file has been split into multiple modules for better organization.

为了向后兼容，此文件重新导出所有模块中的类。
For backward compatibility, this file re-exports all classes from the modules.
"""

import warnings

warnings.warn(
    "直接从 kafka_producer 导入已弃用。"
    "请从 streaming.producer 导入相关类。",
    DeprecationWarning,
    stacklevel=2
)

# 从新模块导入所有内容
from .streaming.producer.kafka_producer import *
from .streaming.producer.message_builder import *
from .streaming.producer.partitioner import *
from .streaming.producer.retry_handler import *

# 导出所有类
__all__ = [
    "KafkaProducer"
    "MessageBuilder"
    "Partitioner"
    "RetryHandler"
]
