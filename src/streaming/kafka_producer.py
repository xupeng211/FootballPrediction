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
    "直接从 kafka_producer 导入已弃用。请从 streaming.producer 导入相关类。",
    DeprecationWarning,
    stacklevel=2,
)

# 导出 KafkaMessageProducer 作为 KafkaProducer 的别名以保持兼容性
try:
    from .kafka_producer_simple import KafkaMessageProducer

    # 为了向后兼容，提供 KafkaProducer 别名
    KafkaProducer = KafkaMessageProducer
    __all__ = ["KafkaProducer", "KafkaMessageProducer"]
except ImportError:
    # 如果简化版本不存在，尝试导入原始版本
    try:
        from .kafka_producer_legacy import FootballKafkaProducer

        KafkaProducer = FootballKafkaProducer
        __all__ = ["KafkaProducer", "FootballKafkaProducer"]
    except ImportError:
        # 如果都不存在，提供一个空类作为占位符
        class KafkaProducer:
            """占位符类，当真实的 KafkaProducer 不可用时使用"""

            def __init__(self, *args, **kwargs):  # type: ignore
                pass

            async def send(self, *args, **kwargs):
                return None

            async def close(self):
                pass

        __all__ = ["KafkaProducer"]
