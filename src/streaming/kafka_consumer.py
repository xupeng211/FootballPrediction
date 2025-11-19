from typing import Optional

"""Kafka消费者模块 - 兼容性包装器.

为了保持向后兼容性,此文件重新导出新模块化结构中的类和函数。
实际的实现已经拆分到 src/streaming/consumer/ 目录下.
"""

# from .consumer import FootballKafkaConsumer  # 不存在
from .data_processor import DataProcessor
from .message_processor import MessageProcessor
from .utils import get_session

# 从新模块化结构导入所有组件

# 重新导出以保持向后兼容性
__all__ = [
    # "FootballKafkaConsumer",  # 暂时注释掉,因为模块不存在
    "MessageProcessor",
    "DataProcessor",
    "get_session",
]

# 为了兼容性保留一些别名
# KafkaConsumer = FootballKafkaConsumer  # 暂时注释掉
