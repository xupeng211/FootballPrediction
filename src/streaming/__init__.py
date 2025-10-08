from typing import cast, Any, Optional, Union

"""
流式数据处理模块

基于Apache Kafka实现的流式数据处理能力，支持：
- 实时数据采集流
- 数据消费处理
- 高可用性和容错性

模块结构：
- kafka_producer.py: Kafka生产者，发送数据到流
- kafka_consumer.py: Kafka消费者，处理流数据
- stream_config.py: 流配置管理
- stream_processor.py: 流数据处理器
"""

from .kafka_consumer import FootballKafkaConsumer
from .kafka_producer import FootballKafkaProducer
from .stream_config import StreamConfig
from .stream_processor import StreamProcessor

__all__ = [
    "FootballKafkaProducer",
    "FootballKafkaConsumer",
    "StreamConfig",
    "StreamProcessor",
]
