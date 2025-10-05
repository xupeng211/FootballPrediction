"""
Kafka组件模块

提供足球预测系统的Kafka流处理功能，包括：
- 生产者和消费者
- 消息序列化/反序列化
- 流处理配置
- 健康检查和监控
"""

import asyncio
import json
import logging
import time
from typing import Any, Callable, Dict, List, Optional, Union

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

from src.core.config import get_settings

logger = logging.getLogger(__name__)
_settings = get_settings()


class KafkaAdmin:
    """Kafka管理器"""

    def __init__(self, bootstrap_servers: Optional[str] = None):
        if not KAFKA_AVAILABLE:
            raise ImportError("confluent_kafka is required for KafkaAdmin")

        self.bootstrap_servers = bootstrap_servers or _settings.KAFKA_BOOTSTRAP_SERVERS
        self.admin_client = AdminClient({"bootstrap.servers": self.bootstrap_servers})

    async def create_topics(self, topics: List[Dict[str, Any]]) -> Dict[str, Any]:
        """创建主题"""
        try:
            new_topics = [
                NewTopic(
                    topic["name"],
                    num_partitions=topic.get("num_partitions", 3),
                    replication_factor=topic.get("replication_factor", 1),
                )
                for topic in topics
            ]

            result = self.admin_client.create_topics(new_topics)

            # 等待创建完成
            for topic_name, future in result.items():
                try:
                    future.result(timeout=10)
                    logger.info(f"主题 {topic_name} 创建成功")
                except Exception as e:
                    logger.error(f"主题 {topic_name} 创建失败: {e}")

            return {"status": "success", "created_topics": [t["name"] for t in topics]}
        except Exception as e:
            logger.error(f"创建Kafka主题失败: {e}")
            return {"status": "error", "error": str(e)}

    async def delete_topics(self, topic_names: List[str]) -> Dict[str, Any]:
        """删除主题"""
        try:
            result = self.admin_client.delete_topics(topic_names)

            # 等待删除完成
            for topic_name, future in result.items():
                try:
                    future.result(timeout=10)
                    logger.info(f"主题 {topic_name} 删除成功")
                except Exception as e:
                    logger.error(f"主题 {topic_name} 删除失败: {e}")

            return {"status": "success", "deleted_topics": topic_names}
        except Exception as e:
            logger.error(f"删除Kafka主题失败: {e}")
            return {"status": "error", "error": str(e)}


class StreamConfig:
    """流处理配置"""

    def __init__(
        self,
        bootstrap_servers: Optional[str] = None,
        group_id: Optional[str] = None,
        auto_offset_reset: str = "earliest",
        enable_auto_commit: bool = True,
        session_timeout_ms: int = 30000,
        heartbeat_interval_ms: int = 3000,
    ):
        """
        初始化流配置

        Args:
            bootstrap_servers: Kafka服务器地址
            group_id: 消费者组ID
            auto_offset_reset: 偏移量重置策略
            enable_auto_commit: 是否自动提交偏移量
            session_timeout_ms: 会话超时时间
            heartbeat_interval_ms: 心跳间隔
        """
        self.bootstrap_servers = bootstrap_servers or getattr(
            _settings, "kafka_bootstrap_servers", "localhost:9092"
        )
        self.group_id = group_id or getattr(_settings, "kafka_group_id", "football-prediction")
        self.auto_offset_reset = auto_offset_reset
        self.enable_auto_commit = enable_auto_commit
        self.session_timeout_ms = session_timeout_ms
        self.heartbeat_interval_ms = heartbeat_interval_ms

    def to_producer_config(self) -> Dict[str, Any]:
        """转换为生产者配置"""
        return {
            "bootstrap.servers": self.bootstrap_servers,
            "client.id": f"football-prediction-producer-{int(time.time())}",
            "acks": "all",
            "retries": 3,
            "retry.backoff.ms": 100,
            "linger.ms": 10,
            "batch.size": 16384,
            "compression.type": "snappy",
        }

    def to_consumer_config(self) -> Dict[str, Any]:
        """转换为消费者配置"""
        return {
            "bootstrap.servers": self.bootstrap_servers,
            "group.id": self.group_id,
            "auto.offset.reset": self.auto_offset_reset,
            "enable.auto.commit": self.enable_auto_commit,
            "session.timeout.ms": self.session_timeout_ms,
            "heartbeat.interval.ms": self.heartbeat_interval_ms,
        }


class MessageSerializer:
    """消息序列化器"""

    @staticmethod
    def serialize(value: Any) -> bytes:
        """序列化消息"""
        try:
            if isinstance(value, bytes):
                return value
            elif isinstance(value, str):
                return value.encode("utf-8")
            else:
                return json.dumps(value, ensure_ascii=False).encode("utf-8")
        except Exception as e:
            logger.error(f"消息序列化失败: {e}")
            raise

    @staticmethod
    def deserialize(value: bytes) -> Any:
        """反序列化消息"""
        try:
            if not value:
                return None
            # 尝试解析为JSON
            return json.loads(value.decode("utf-8"))
        except json.JSONDecodeError:
            # 如果不是JSON，直接返回字符串
            return value.decode("utf-8")
        except Exception as e:
            logger.error(f"消息反序列化失败: {e}")
            raise


class FootballKafkaProducer:
    """足球预测系统Kafka生产者"""

    def __init__(self, config: Optional[StreamConfig] = None):
        """
        初始化生产者

        Args:
            config: 流配置
        """
        if not KAFKA_AVAILABLE:
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


class FootballKafkaConsumer:
    """足球预测系统Kafka消费者"""

    def __init__(
        self,
        topics: Union[str, List[str]],
        config: Optional[StreamConfig] = None,
        message_handler: Optional[Callable] = None,
    ):
        """
        初始化消费者

        Args:
            topics: 订阅的主题
            config: 流配置
            message_handler: 消息处理函数
        """
        if not KAFKA_AVAILABLE:
            raise ImportError("confluent_kafka 未安装，无法使用Kafka功能")

        self.config = config or StreamConfig()
        self.topics = [topics] if isinstance(topics, str) else topics
        self.message_handler = message_handler
        self.consumer = None
        self.serializer = MessageSerializer()
        self._closed = False
        self._running = False

        try:
            self.consumer = Consumer(self.config.to_consumer_config())
            self.consumer.subscribe(self.topics)
            logger.info(f"Kafka消费者初始化成功，订阅主题: {self.topics}")
        except Exception as e:
            logger.error(f"Kafka消费者初始化失败: {e}")
            raise

    async def start_consuming(self, batch_size: int = 100, timeout: float = 1.0) -> None:
        """
        开始消费消息

        Args:
            batch_size: 批处理大小
            timeout: 超时时间
        """
        if self._closed:
            raise RuntimeError("消费者已关闭")

        self._running = True
        logger.info(f"开始消费消息，主题: {self.topics}")

        try:
            while self._running:
                batch = []
                # 收集一批消息
                for _ in range(batch_size):
                    msg = self.consumer.poll(timeout)
                    if msg is None:
                        break
                    elif msg.error():
                        logger.error(f"消费消息错误: {msg.error()}")
                        continue
                    else:
                        batch.append(msg)

                # 处理消息批次
                if batch:
                    await self._process_message_batch(batch)

        except Exception as e:
            logger.error(f"消费消息异常: {e}")
            raise
        finally:
            self._running = False

    async def _process_message_batch(self, batch: List) -> None:
        """处理消息批次"""
        for msg in batch:
            try:
                # 反序列化消息
                value = self.serializer.deserialize(msg.value())
                key = self.serializer.deserialize(msg.key()) if msg.key() else None

                # 构建消息对象
                message = {
                    "topic": msg.topic(),
                    "partition": msg.partition(),
                    "offset": msg.offset(),
                    "key": key,
                    "value": value,
                    "timestamp": msg.timestamp()[1] if msg.timestamp()[0] else None,
                    "headers": dict(msg.headers()) if msg.headers() else {},
                }

                # 处理消息
                if self.message_handler:
                    if asyncio.iscoroutinefunction(self.message_handler):
                        await self.message_handler(message)
                    else:
                        self.message_handler(message)

            except Exception as e:
                logger.error(f"处理消息失败: {e}")

    def stop_consuming(self) -> None:
        """停止消费"""
        self._running = False
        logger.info("停止消费消息")

    def close(self) -> None:
        """关闭消费者"""
        if not self._closed:
            self.stop_consuming()
            if self.consumer:
                self.consumer.close()
            self._closed = True
            logger.info("Kafka消费者已关闭")

    def health_check(self) -> bool:
        """健康检查"""
        try:
            if self._closed or not self.consumer:
                return False
            # 尝试获取集群元数据
            metadata = self.consumer.list_topics(timeout=5.0)
            return len(metadata.brokers) > 0
        except Exception as e:
            logger.error(f"Kafka消费者健康检查失败: {e}")
            return False


class KafkaTopicManager:
    """Kafka主题管理器"""

    def __init__(self, config: Optional[StreamConfig] = None):
        """
        初始化主题管理器

        Args:
            config: 流配置
        """
        if not KAFKA_AVAILABLE:
            raise ImportError("confluent_kafka 未安装，无法使用Kafka功能")

        self.config = config or StreamConfig()
        self.admin_client = None

        try:
            self.admin_client = AdminClient({"bootstrap.servers": self.config.bootstrap_servers})
            logger.info(f"Kafka管理器初始化成功: {self.config.bootstrap_servers}")
        except Exception as e:
            logger.error(f"Kafka管理器初始化失败: {e}")
            raise

    def create_topic(
        self,
        topic_name: str,
        num_partitions: int = 3,
        replication_factor: int = 1,
        config: Optional[Dict[str, str]] = None,
    ) -> bool:
        """
        创建主题

        Args:
            topic_name: 主题名称
            num_partitions: 分区数
            replication_factor: 副本因子
            config: 主题配置

        Returns:
            bool: 是否创建成功
        """
        try:
            topic = NewTopic(
                topic=topic_name,
                num_partitions=num_partitions,
                replication_factor=replication_factor,
                config=config or {},
            )

            future = self.admin_client.create_topics([topic])
            for topic_name, future in future.items():
                try:
                    future.result(timeout=10.0)
                    logger.info(f"主题 {topic_name} 创建成功")
                    return True
                except KafkaException as e:
                    if e.args[0].code() == KafkaError.TOPIC_ALREADY_EXISTS:
                        logger.warning(f"主题 {topic_name} 已存在")
                        return True
                    else:
                        logger.error(f"创建主题 {topic_name} 失败: {e}")
                        return False
        except Exception as e:
            logger.error(f"创建主题失败: {e}")
            return False

    def delete_topic(self, topic_name: str) -> bool:
        """
        删除主题

        Args:
            topic_name: 主题名称

        Returns:
            bool: 是否删除成功
        """
        try:
            future = self.admin_client.delete_topics([topic_name])
            for topic_name, future in future.items():
                try:
                    future.result(timeout=10.0)
                    logger.info(f"主题 {topic_name} 删除成功")
                    return True
                except KafkaException as e:
                    logger.error(f"删除主题 {topic_name} 失败: {e}")
                    return False
        except Exception as e:
            logger.error(f"删除主题失败: {e}")
            return False

    def list_topics(self) -> Dict[str, Any]:
        """
        列出所有主题

        Returns:
            Dict[str, Any]: 主题元数据
        """
        try:
            metadata = self.admin_client.list_topics(timeout=10.0)
            return {
                "topics": list(metadata.topics.keys()),
                "brokers": list(metadata.brokers.keys()),
            }
        except Exception as e:
            logger.error(f"列出主题失败: {e}")
            return {}

    def close(self) -> None:
        """关闭管理器"""
        if self.admin_client:
            # AdminClient没有close方法
            logger.info("Kafka管理器已关闭")


# 默认主题配置
DEFAULT_TOPICS = {
    "match-events": {
        "partitions": 3,
        "replication_factor": 1,
        "config": {"retention.ms": "604800000"},  # 7天
    },
    "predictions": {
        "partitions": 3,
        "replication_factor": 1,
        "config": {"retention.ms": "2592000000"},  # 30天
    },
    "odds-updates": {
        "partitions": 3,
        "replication_factor": 1,
        "config": {"retention.ms": "86400000"},  # 1天
    },
    "scores": {
        "partitions": 3,
        "replication_factor": 1,
        "config": {"retention.ms": "604800000"},  # 7天
    },
}


class StreamProcessor:
    """流处理器"""

    def __init__(
        self,
        input_topics: Union[str, List[str]],
        output_topic: Optional[str] = None,
        processor_func: Optional[Callable] = None,
        config: Optional[StreamConfig] = None,
    ):
        """
        初始化流处理器

        Args:
            input_topics: 输入主题
            output_topic: 输出主题
            processor_func: 处理函数
            config: 流配置
        """
        self.input_topics = [input_topics] if isinstance(input_topics, str) else input_topics
        self.output_topic = output_topic
        self.processor_func = processor_func
        self.config = config or StreamConfig()
        self.producer = None
        self.consumer = None
        self._running = False

        # 初始化生产者（如果有输出主题）
        if self.output_topic:
            self.producer = FootballKafkaProducer(self.config)

        # 初始化消费者
        self.consumer = FootballKafkaConsumer(
            topics=self.input_topics,
            config=self.config,
            message_handler=self._handle_message,
        )

    async def _handle_message(self, message: Dict[str, Any]) -> None:
        """处理消息"""
        try:
            # 处理消息
            if self.processor_func:
                processed = self.processor_func(message)
                if processed and self.producer:
                    # 发送处理后的消息
                    self.producer.produce(
                        topic=self.output_topic,
                        value=processed,
                        key=message.get("key"),
                    )
        except Exception as e:
            logger.error(f"处理消息失败: {e}")

    async def start(self) -> None:
        """开始处理流"""
        if not self._running:
            self._running = True
            logger.info(f"启动流处理器，输入: {self.input_topics}, 输出: {self.output_topic}")
            await self.consumer.start_consuming()

    def stop(self) -> None:
        """停止处理流"""
        if self._running:
            self._running = False
            self.consumer.stop_consuming()
            logger.info("流处理器已停止")

    def close(self) -> None:
        """关闭流处理器"""
        self.stop()
        if self.consumer:
            self.consumer.close()
        if self.producer:
            self.producer.close()

    def health_check(self) -> bool:
        """健康检查"""
        consumer_healthy = self.consumer.health_check() if self.consumer else True
        producer_healthy = self.producer.health_check() if self.producer else True
        return consumer_healthy and producer_healthy


class KafkaStream:
    """Kafka流（高级封装）"""

    def __init__(
        self,
        stream_id: str,
        source_topic: str,
        sink_topic: Optional[str] = None,
        config: Optional[StreamConfig] = None,
    ):
        """
        初始化Kafka流

        Args:
            stream_id: 流ID
            source_topic: 源主题
            sink_topic: 目标主题
            config: 流配置
        """
        self.stream_id = stream_id
        self.source_topic = source_topic
        self.sink_topic = sink_topic
        self.config = config or StreamConfig()
        self.processors: List[StreamProcessor] = []

    def add_processor(
        self,
        processor_func: Callable,
        output_topic: Optional[str] = None,
    ) -> "KafkaStream":
        """
        添加处理器

         Args:
             processor_func: 处理函数
             output_topic: 输出主题

         Returns:
             KafkaStream: 返回自身以支持链式调用
        """
        processor = StreamProcessor(
            input_topics=self.source_topic,
            output_topic=output_topic or self.sink_topic,
            processor_func=processor_func,
            config=self.config,
        )
        self.processors.append(processor)
        return self

    async def start(self) -> None:
        """启动流"""
        logger.info(f"启动Kafka流: {self.stream_id}")
        tasks = []
        for processor in self.processors:
            tasks.append(processor.start())
        await asyncio.gather(*tasks)

    def stop(self) -> None:
        """停止流"""
        logger.info(f"停止Kafka流: {self.stream_id}")
        for processor in self.processors:
            processor.stop()

    def close(self) -> None:
        """关闭流"""
        self.stop()
        for processor in self.processors:
            processor.close()

    def health_check(self) -> bool:
        """健康检查"""
        return all(p.health_check() for p in self.processors)


async def ensure_topics_exist(config: Optional[StreamConfig] = None) -> None:
    """
    确保默认主题存在

    Args:
        config: 流配置
    """
    if not KAFKA_AVAILABLE:
        logger.warning("Kafka不可用，跳过主题创建")
        return

    try:
        manager = KafkaTopicManager(config)
        for topic_name, topic_config in DEFAULT_TOPICS.items():
            manager.create_topic(
                topic_name=topic_name,
                num_partitions=topic_config["partitions"],
                replication_factor=topic_config["replication_factor"],
                config=topic_config["config"],
            )
        manager.close()
    except Exception as e:
        logger.error(f"确保主题存在失败: {e}")
