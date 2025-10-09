"""
足球预测系统Kafka消费者
"""

import asyncio
import logging
from typing import Any, Callable, List, Optional, Union

try:
    from confluent_kafka import Consumer
    KAFKA_CONSUMER_AVAILABLE = True
except ImportError:
    KAFKA_CONSUMER_AVAILABLE = False
    Consumer = None

from src.streaming.kafka.config.stream_config import StreamConfig
from src.streaming.kafka.serialization.message_serializer import MessageSerializer

logger = logging.getLogger(__name__)


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
        if not KAFKA_CONSUMER_AVAILABLE:
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

    async def start_consuming(
        self, batch_size: int = 100, timeout: float = 1.0
    ) -> None:
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