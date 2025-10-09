"""
Kafka流处理器
"""

from typing import Dict
from typing import List
from typing import Optional
from typing import Union
import logging
from typing import Any, Callable, List, Optional, Union

from src.streaming.kafka.config.stream_config import StreamConfig
from src.streaming.kafka.consumer.kafka_consumer import FootballKafkaConsumer
from src.streaming.kafka.producer.kafka_producer import FootballKafkaProducer

logger = logging.getLogger(__name__)


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
        self.input_topics = (
            [input_topics] if isinstance(input_topics, str) else input_topics
        )
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
            logger.info(
                f"启动流处理器，输入: {self.input_topics}, 输出: {self.output_topic}"
            )
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
