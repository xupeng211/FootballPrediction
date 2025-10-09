"""
Kafka消费者模块

提供模块化的Kafka消费者功能：
- 消费者核心功能
- 消息处理器
- 数据处理器
- 工具函数
"""

from .consumer import FootballKafkaConsumer
from .message_processor import MessageProcessor
from .data_processor import DataProcessor
from .utils import get_session

__all__ = [
    "FootballKafkaConsumer",
    "MessageProcessor",
    "DataProcessor",
    "get_session",
]