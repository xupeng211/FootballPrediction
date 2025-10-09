"""
流式处理配置管理

提供Kafka和流处理的配置管理功能，包括：
- Kafka连接配置
- Topic配置管理
- 序列化配置
- 错误处理配置
"""



@dataclass
class KafkaConfig:
    """Kafka基础配置"""

    # 连接配置
    bootstrap_servers: str = "localhost:9092"
    security_protocol: str = "PLAINTEXT"

    # 生产者配置
    producer_client_id: str = "football-prediction-producer"
    producer_acks: str = "all"  # 等待所有副本确认
    producer_retries: int = 3
    producer_retry_backoff_ms: int = 1000
    producer_linger_ms: int = 5  # 批量发送延迟
    producer_batch_size: int = 16384  # 16KB批量大小

    # 消费者配置
    consumer_group_id: str = "football-prediction-consumers"
    consumer_client_id: str = "football-prediction-consumer"
    consumer_auto_offset_reset: str = "latest"
    consumer_enable_auto_commit: bool = True
    consumer_auto_commit_interval_ms: int = 5000
    consumer_max_poll_records: int = 500

    # 序列化配置
    key_serializer: str = "string"
    value_serializer: str = "json"


@dataclass
class TopicConfig:
    """Topic配置"""

    name: str
    partitions: int = 3
    replication_factor: int = 1
    cleanup_policy: str = "delete"
    retention_ms: int = 604800000  # 7天
    segment_ms: int = 86400000  # 1天


class StreamConfig:
    """
    流式处理配置管理器

    负责管理Kafka连接、Topic、序列化等配置
    支持从环境变量和配置文件加载配置
    """

    def __init__(self):
        self.kafka_config = self._load_kafka_config()
        self.topics = self._init_topics()

    def _load_kafka_config(self) -> KafkaConfig:
        """从环境变量加载Kafka配置"""
        return KafkaConfig(
            bootstrap_servers=os.getenv("KAFKA_BOOTSTRAP_SERVERS", "localhost:9092"),
            security_protocol=os.getenv("KAFKA_SECURITY_PROTOCOL", "PLAINTEXT"),
            producer_client_id=os.getenv(
                "KAFKA_PRODUCER_CLIENT_ID", "football-prediction-producer"
            ),
            producer_acks=os.getenv("KAFKA_PRODUCER_ACKS", "all"),
            producer_retries=int(os.getenv("KAFKA_PRODUCER_RETRIES", "3")),
            consumer_group_id=os.getenv(
                "KAFKA_CONSUMER_GROUP_ID", "football-prediction-consumers"
            ),
            consumer_client_id=os.getenv(
                "KAFKA_CONSUMER_CLIENT_ID", "football-prediction-consumer"
            ),
            consumer_auto_offset_reset=os.getenv(
                "KAFKA_CONSUMER_AUTO_OFFSET_RESET", "latest"
            ),
        )

    def _init_topics(self) -> Dict[str, TopicConfig]:
        """初始化Topic配置"""
        return {
            # 比赛数据流
            "matches-stream": TopicConfig(
                name="matches-stream",
                partitions=3,
                retention_ms=86400000,  # 1天
            ),
            # 赔率数据流
            "odds-stream": TopicConfig(
                name="odds-stream",
                partitions=6,  # 赔率数据量大，更多分区
                retention_ms=43200000,  # 12小时
            ),
            # 比分数据流
            "scores-stream": TopicConfig(
                name="scores-stream",
                partitions=3,
                retention_ms=21600000,  # 6小时
            ),
            # 处理结果流
            "processed-data-stream": TopicConfig(
                name="processed-data-stream",
                partitions=3,
                retention_ms=604800000,  # 7天
            ),
        }

    def get_producer_config(self) -> Dict[str, Any]:
        """获取生产者配置"""
        return {
            "bootstrap.servers": self.kafka_config.bootstrap_servers,
            "security.protocol": self.kafka_config.security_protocol,
            "client.id": self.kafka_config.producer_client_id,
            "acks": self.kafka_config.producer_acks,
            "retries": self.kafka_config.producer_retries,
            "retry.backoff.ms": self.kafka_config.producer_retry_backoff_ms,
            "linger.ms": self.kafka_config.producer_linger_ms,
            "batch.size": self.kafka_config.producer_batch_size,
            "compression.type": "gzip",  # 使用gzip压缩
            "max.in.flight.requests.per.connection": 1,  # 保证消息顺序
        }

    def get_consumer_config(
        self, consumer_group_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """获取消费者配置"""
        group_id = consumer_group_id or self.kafka_config.consumer_group_id

        return {
            "bootstrap.servers": self.kafka_config.bootstrap_servers,
            "security.protocol": self.kafka_config.security_protocol,
            "client.id": self.kafka_config.consumer_client_id,
            "group.id": group_id,
            "auto.offset.reset": self.kafka_config.consumer_auto_offset_reset,
            "enable.auto.commit": self.kafka_config.consumer_enable_auto_commit,
            "auto.commit.interval.ms": self.kafka_config.consumer_auto_commit_interval_ms,
            # confluent-kafka不支持max.poll.records，改用max.poll.interval.ms
            "max.poll.interval.ms": 300000,  # 5分钟
            "session.timeout.ms": 30000,
            "heartbeat.interval.ms": 3000,
        }

    def get_topic_config(self, topic_name: str) -> Optional[TopicConfig]:
        """获取指定Topic配置"""
        return self.topics.get(topic_name)

    def get_all_topics(self) -> List[str]:
        """获取所有Topic名称"""
        return list(self.topics.keys())

    def is_valid_topic(self, topic_name: str) -> bool:
        """检查Topic是否有效"""
        return topic_name in self.topics
import os

