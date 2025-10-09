"""
向后兼容性模块

为了保持向后兼容性，从confluent_kafka重新导出所需的类和常量。
"""

# 导入检查
try:
    from confluent_kafka import Consumer, KafkaError, KafkaException, Producer
    from confluent_kafka.admin import AdminClient, NewTopic

    KAFKA_AVAILABLE = True
except ImportError:
    KAFKA_AVAILABLE = False
    Producer = None
    Consumer = None
    AdminClient = None
    NewTopic = None
    KafkaError = None
    KafkaException = None

# 导出向后兼容的符号
__all__ = [
    "KAFKA_AVAILABLE",
    "Producer",
    "Consumer",
    "AdminClient",
    "NewTopic",
    "KafkaError",
    "KafkaException",
]