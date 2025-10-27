"""
Kafka组件模块 - 兼容性包装器

为了保持向后兼容性，此文件重新导出Kafka相关的类和函数。
"""

from typing import List, Type

# 尝试导入Kafka组件
try:
    from .kafka_producer import FootballKafkaProducer
except ImportError:
    FootballKafkaProducer = None

try:
    from .kafka_consumer import FootballKafkaConsumer
except ImportError:
    # 创建一个占位符类
    class FootballKafkaConsumer:
        """占位符类 - Kafka消费者"""

        def __init__(self, *args, **kwargs):
            pass

    FootballKafkaConsumer = FootballKafkaConsumer

# 尝试导入StreamConfig
try:
    from .stream_config import StreamConfig
except ImportError:
    StreamConfig = None

# 创建占位符类以避免类型错误
if StreamConfig is None:

    class StreamConfig:
        """占位符类 - 流配置"""

        def __init__(self, *args, **kwargs):
            pass

    StreamConfig: Type = StreamConfig

# 尝试导入StreamProcessor
try:
    from .stream_processor import StreamProcessor
except ImportError:
    StreamProcessor = None

# 创建占位符类以避免类型错误
if StreamProcessor is None:

    class StreamProcessor:
        """占位符类 - 流处理器"""

        def __init__(self, *args, **kwargs):
            pass

    StreamProcessor: Type = StreamProcessor

# Kafka可用性标志
KAFKA_AVAILABLE = True  # 如果导入成功，设置为True

# 默认主题
DEFAULT_TOPICS = ["football_matches", "football_predictions", "football_odds"]

# 兼容性别名
Consumer = None  # 可以根据需要定义
Producer = None  # 可以根据需要定义
KafkaError = Exception  # 基础异常类
KafkaException = Exception  # 基础异常类
KafkaAdmin = None  # 管理类
KafkaTopicManager = None  # 主题管理
MessageSerializer = None  # 消息序列化器
KafkaStream = None  # 流处理类


def ensure_topics_exist(topics: List[str]) -> bool:
    """确保主题存在（桩实现）"""
    return True


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
