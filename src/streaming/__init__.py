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

from typing import cast, Any, Optional, Union

# 尝试导入简化版本
try:
    from .kafka_producer_simple import KafkaMessageProducer
    from .kafka_consumer_simple import KafkaMessageConsumer
    from .stream_config_simple import (
        StreamConfig,
        KafkaConfig,
        ConsumerConfig,
        ProducerConfig,
    )
    from .stream_processor_simple import (
        StreamProcessor,
        MessageProcessor,
        BatchProcessor,
    )
    from .kafka_components_simple import (
        KafkaAdminClient,
        KafkaTopicManager,
        KafkaConsumerGroup,
        KafkaCluster,
        KafkaHealthChecker,
        KafkaMetricsCollector,
    )
except ImportError:
    # 如果简化版本不存在，使用原始版本
    try:
        from .kafka_consumer import FootballKafkaConsumer
        from .kafka_producer import FootballKafkaProducer
        from .stream_config import StreamConfig  # type: ignore
        from .stream_processor import StreamProcessor  # type: ignore
    except ImportError:
        pass

__all__ = [
    "KafkaMessageProducer",
    "KafkaMessageConsumer",
    "StreamConfig",
    "KafkaConfig",
    "ConsumerConfig",
    "ProducerConfig",
    "StreamProcessor",
    "MessageProcessor",
    "BatchProcessor",
    "KafkaAdminClient",
    "KafkaTopicManager",
    "KafkaConsumerGroup",
    "KafkaCluster",
    "KafkaHealthChecker",
    "KafkaMetricsCollector",
]
