"""
足球预测系统Kafka生产者
"""


try:
    from confluent_kafka import Producer
    KAFKA_PRODUCER_AVAILABLE = True
except ImportError:
    KAFKA_PRODUCER_AVAILABLE = False
    Producer = None


logger = logging.getLogger(__name__)


class FootballKafkaProducer:
    """足球预测系统Kafka生产者"""

    def __init__(self, config: Optional[StreamConfig] = None):
        """
        初始化生产者

        Args:
            config: 流配置
        """
        if not KAFKA_PRODUCER_AVAILABLE:
            raise ImportError("confluent_kafka 未安装，无法使用Kafka功能")

        self.config = config or StreamConfig()
        self.producer = None
        self.serializer = MessageSerializer()
        self._closed = False

        try:
            self.producer = Producer(self.config.to_producer_config())
            logger.info(f"Kafka生产者初始化成功: {self.config.bootstrap_servers}")
        except Exception as e:
            logger.error(f"Kafka生产者初始化失败: {e}")
            raise

    def produce(
        self,
        topic: str,
        value: Any,
        key: Optional[Any] = None,
        headers: Optional[Dict[str, str]] = None,
        callback: Optional[Callable] = None,
    ) -> None:
        """
        发送消息

        Args:
            topic: 主题名称
            value: 消息值
            key: 消息键
            headers: 消息头
            callback: 发送回调函数
        """
        if self._closed:
            raise RuntimeError("生产者已关闭")

        try:
            # 序列化消息
            serialized_value = self.serializer.serialize(value)
            serialized_key = self.serializer.serialize(key) if key is not None else None

            # 准备消息头
            msg_headers = []
            if headers:
                for k, v in headers.items():
                    msg_headers.append((k, str(v).encode("utf-8")))

            # 发送消息
            self.producer.produce(
                topic=topic,
                value=serialized_value,
                key=serialized_key,
                headers=msg_headers,
                callback=callback,
            )

            # 触发轮询以确保消息发送
            self.producer.poll(0)

        except Exception as e:
            logger.error(f"发送消息到主题 {topic} 失败: {e}")
            raise

    def flush(self, timeout: float = 10.0) -> int:
        """
        刷新缓冲区

        Args:
            timeout: 超时时间

        Returns:
            int: 剩余未发送的消息数
        """
        if self.producer:
            return self.producer.flush(timeout)
        return 0

    def close(self, timeout: float = 10.0) -> None:
        """
        关闭生产者

        Args:
            timeout: 超时时间
        """
        if not self._closed and self.producer:
            self.flush(timeout)
            self._closed = True
            logger.info("Kafka生产者已关闭")

    def health_check(self) -> bool:
        """健康检查"""
        try:
            if self._closed or not self.producer:
                return False
            # 尝试获取集群元数据
            metadata = self.producer.list_topics(timeout=5.0)
            return len(metadata.brokers) > 0
        except Exception as e:
            logger.error(f"Kafka生产者健康检查失败: {e}")
            return False

    def get_producer_config(self) -> Dict[str, Any]:
        """获取生产者配置"""
        return self.config.to_producer_config()

from src.streaming.kafka.config.stream_config import StreamConfig
from src.streaming.kafka.serialization.message_serializer import MessageSerializer

