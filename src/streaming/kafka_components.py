"""
Kafka组件模块 - 兼容性包装器

为了保持向后兼容性，此文件重新导出新模块化结构中的类和函数。
实际的实现已经拆分到 src/streaming/kafka/ 目录下。
"""

from .kafka import (
    # 从新模块化结构导入所有组件
    KafkaAdmin,
    FootballKafkaProducer,
    FootballKafkaConsumer,
    KafkaTopicManager,
    StreamProcessor,
    MessageSerializer,
    StreamConfig,
    KafkaStream,
    DEFAULT_TOPICS,
    ensure_topics_exist,
    KAFKA_AVAILABLE,
    Consumer,
    KafkaError,
    KafkaException,
    Producer,
)

# 重新导出以保持向后兼容性
__all__ = [
    "KafkaAdmin",
    "FootballKafkaProducer",
    "FootballKafkaConsumer",
    "KafkaTopicManager",
    "StreamProcessor",
    "MessageSerializer",
    "StreamConfig",
    "KafkaStream",
    "DEFAULT_TOPICS",
    "ensure_topics_exist",
    "KAFKA_AVAILABLE",
    "Consumer",
    "KafkaError",
    "KafkaException",
    "Producer",
]
