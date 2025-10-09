"""
Kafka流处理模块

提供足球预测系统的Kafka流处理功能，包括：
- 生产者和消费者
- 消息序列化/反序列化
- 流处理配置
- 健康检查和监控
"""

from .admin import KafkaAdmin, KafkaTopicManager
from .compatibility import (
from .config import StreamConfig
from .consumer import FootballKafkaConsumer
from .processor import KafkaStream, StreamProcessor, DEFAULT_TOPICS
from .producer import FootballKafkaProducer
from .serialization import MessageSerializer

# 导入各个子模块

# 向后兼容性导出
    KAFKA_AVAILABLE,
    Consumer,
    KafkaError,
    KafkaException,
    Producer,
)

# 导出所有主要类
__all__ = [
    # 管理类
    "KafkaAdmin",
    "KafkaTopicManager",

    # 配置类
    "StreamConfig",

    # 生产者和消费者
    "FootballKafkaProducer",
    "FootballKafkaConsumer",

    # 流处理
    "StreamProcessor",
    "KafkaStream",

    # 序列化
    "MessageSerializer",

    # 常量
    "DEFAULT_TOPICS",

    # 向后兼容
    "KAFKA_AVAILABLE",
    "Consumer",
    "KafkaError",
    "KafkaException",
    "Producer",
]