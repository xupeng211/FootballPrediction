from .data_processor import DataProcessor
from .message_processor import MessageProcessor
from .utils import get_session

"""
Kafka消费者模块 - 兼容性包装器

为了保持向后兼容性,此文件重新导出新模块化结构中的类和函数。
实际的实现已经拆分到 src/streaming/consumer/ 目录下.
"""

__all__ = [
    # "FootballKafkaConsumer",  # 暂时注释掉,因为模块不存在
    "MessageProcessor",
    "DataProcessor",
    "get_session",
]
