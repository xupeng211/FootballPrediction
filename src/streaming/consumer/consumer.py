"""
Kafka消费者核心实现

提供Kafka消费的核心功能，包括连接管理、Topic订阅和消息消费。
"""

import asyncio
import logging
from typing import Any, Dict, List, Optional

from confluent_kafka import Consumer, KafkaError, KafkaException

from src.database.connection import DatabaseManager
from .message_processor import MessageProcessor
from .utils import get_session
from ..stream_config import StreamConfig

# 为了测试兼容性添加的别名
KafkaConsumer = Consumer


class FootballKafkaConsumer:
    """
    足球数据Kafka消费者

    负责从Kafka流中消费足球数据并写入数据库，支持：
    - 多Topic订阅
    - 消息反序列化
    - 数据库写入
    - 错误处理和重试
    """

    def __init__(
        self,
        config: Optional[StreamConfig] = None,
        consumer_group_id: Optional[str] = None,
    ):
        """
        初始化Kafka消费者

        Args:
            config: 流配置，如果为None则使用默认配置
            consumer_group_id: 消费者组ID，覆盖配置中的默认值
        """
        self.config = config or StreamConfig()
        self.consumer = None
        self.db_manager = DatabaseManager()
        self.logger = logging.getLogger(__name__)
        self.running = False
        self.consumer_group_id = consumer_group_id
        self.message_processor = MessageProcessor(self.db_manager)

        # 在初始化时尝试创建consumer，如果失败则抛出异常
        self._initialize_consumer(consumer_group_id)

    def _create_consumer(self) -> None:
        """如果尚未创建，则创建Kafka Consumer"""
        if self.consumer is None:
            self._initialize_consumer(self.consumer_group_id)

    def _initialize_consumer(self, consumer_group_id: Optional[str] = None) -> None:
        """初始化Kafka Consumer"""
        try:
            consumer_config = self.config.get_consumer_config(consumer_group_id)
            self.consumer = Consumer(consumer_config)
            self.logger.info(
                f"Kafka Consumer已初始化，组ID: {consumer_config['group.id']}, "
                f"服务器: {consumer_config['bootstrap.servers']}"
            )
        except Exception as e:
            self.logger.error(f"初始化Kafka Consumer失败: {e}")
            raise

    def subscribe_topics(self, topics: List[str]) -> None:
        """
        订阅Topic列表

        Args:
            topics: Topic名称列表
        """
        self._create_consumer()
        if not self.consumer:
            self.logger.error("Consumer初始化失败")
            return

        try:
            # 验证Topic
            valid_topics = []
            for topic in topics:
                if self.config.is_valid_topic(topic):
                    valid_topics.append(topic)
                else:
                    self.logger.warning(f"无效的Topic: {topic}")

            if valid_topics:
                self.consumer.subscribe(valid_topics)
                self.logger.info(f"已订阅Topics: {valid_topics}")
            else:
                self.logger.error("没有有效的Topic可订阅")

        except Exception as e:
            self.logger.error(f"订阅Topic失败: {e}")
            raise

    async def start_consuming(self, timeout: float = 1.0) -> None:
        """
        开始消费消息

        Args:
            timeout: 轮询超时时间（秒）
        """
        self._create_consumer()
        if not self.consumer:
            self.logger.error("Consumer初始化失败")
            return

        self.running = True
        self.logger.info("开始消费Kafka消息...")

        try:
            while self.running:
                # 轮询消息
                msg = self.consumer.poll(timeout=timeout)

                if msg is None:
                    # 没有消息，继续轮询
                    await asyncio.sleep(0.1)
                    continue

                if msg.error():
                    if msg.error().code() == KafkaError._PARTITION_EOF:
                        # 分区结束，正常情况
                        self.logger.debug(
                            f"分区结束: {msg.topic()} [{msg.partition()}]"
                        )
                        continue
                    else:
                        # 其他错误
                        raise KafkaException(msg.error())

                # 处理消息
                success = await self.message_processor.process_message(msg)

                if success:
                    # 手动提交偏移量（如果启用了手动提交）
                    try:
                        self.consumer.commit(msg)
                    except Exception as e:
                        self.logger.warning(f"提交偏移量失败: {e}")
                else:
                    self.logger.warning(
                        f"消息处理失败: Topic={msg.topic()}, Partition={msg.partition()}, Offset={msg.offset()}"
                    )

        except KeyboardInterrupt:
            self.logger.info("收到中断信号，停止消费...")
        except Exception as e:
            self.logger.error(f"消费过程中出现错误: {e}")
        finally:
            self.stop_consuming()

    def stop_consuming(self) -> None:
        """停止消费"""
        self.running = False
        if self.consumer:
            self.consumer.close()
            self.logger.info("Kafka Consumer已关闭")

    async def consume_batch(
        self,
        batch_size: int = 100,
        timeout: float = 5.0,
        max_messages: Optional[int] = None,
    ) -> Dict[str, int]:
        """
        批量消费消息

        Args:
            batch_size: 批量大小
            timeout: 总超时时间（秒）
            max_messages: 最大消息数（兼容性参数，与batch_size相同）

        Returns:
            消费统计 {processed: 成功处理数, failed: 失败数}
        """
        # 兼容性处理
        if max_messages is not None:
            batch_size = max_messages

        self._create_consumer()
        if not self.consumer:
            self.logger.error("Consumer初始化失败")
            return {"processed": 0, "failed": 0}

        stats = {"processed": 0, "failed": 0}
        start_time = asyncio.get_event_loop().time()

        try:
            while stats["processed"] + stats["failed"] < batch_size:
                # 检查超时
                elapsed = asyncio.get_event_loop().time() - start_time
                if elapsed >= timeout:
                    self.logger.info(f"批量消费超时，已处理{stats['processed']}条消息")
                    break

                # 轮询消息
                msg = self.consumer.poll(timeout=1.0)

                if msg is None:
                    continue

                if msg.error():
                    if msg.error().code() != KafkaError._PARTITION_EOF:
                        stats["failed"] += 1
                        self.logger.error(f"Kafka错误: {msg.error()}")
                    continue

                # 处理消息
                success = await self.message_processor.process_message(msg)

                if success:
                    stats["processed"] += 1
                    try:
                        self.consumer.commit(msg)
                    except Exception as e:
                        self.logger.warning(f"提交偏移量失败: {e}")
                else:
                    stats["failed"] += 1

        except Exception as e:
            self.logger.error(f"批量消费失败: {e}")

        self.logger.info(
            f"批量消费完成 - 成功: {stats['processed']}, 失败: {stats['failed']}"
        )
        return stats

    async def consume_messages(
        self, batch_size: int = 100, timeout: float = 5.0
    ) -> list:
        """
        消费消息并返回消息列表（测试兼容性方法）

        Args:
            batch_size: 批量大小
            timeout: 超时时间

        Returns:
            消息列表
        """
        self._create_consumer()
        if not self.consumer:
            self.logger.error("Consumer初始化失败")
            return []

        messages = []
        start_time = asyncio.get_event_loop().time()

        try:
            while len(messages) < batch_size:
                # 检查超时
                elapsed = asyncio.get_event_loop().time() - start_time
                if elapsed >= timeout:
                    break

                # 轮询消息
                msg = self.consumer.poll(timeout=1.0)

                if msg is None:
                    continue

                if msg.error():
                    if msg.error().code() != KafkaError._PARTITION_EOF:
                        self.logger.error(f"Kafka错误: {msg.error()}")
                    continue

                # 构造消息对象
                try:
                    message_data = {
                        "topic": msg.topic(),
                        "data": self.message_processor.deserialize_message(msg.value()),
                        "partition": msg.partition(),
                        "offset": msg.offset(),
                    }
                    messages.append(message_data)
                except Exception as e:
                    self.logger.error(f"解析消息失败: {e}")

        except Exception as e:
            self.logger.error(f"消费消息失败: {e}")

        return messages

    async def process_message(self, message_data: Dict[str, Any]) -> bool:
        """
        处理单个消息（测试兼容性方法）

        Args:
            message_data: 消息数据

        Returns:
            处理是否成功
        """
        return await self.message_processor.process_message_data(message_data)

    def subscribe_all_topics(self) -> None:
        """订阅所有配置的Topic"""
        if not self.consumer:
            self.logger.error("Consumer未初始化")
            return

        topics = [
            self.config.kafka_config.topics.matches,
            self.config.kafka_config.topics.odds,
            self.config.kafka_config.topics.scores,
        ]

        try:
            self.consumer.subscribe(topics)
            self.logger.info(f"已订阅Topics: {topics}")
        except Exception as e:
            self.logger.error(f"订阅Topics失败: {e}")
            raise

    def close(self) -> None:
        """关闭消费者"""
        self.stop_consuming()

    def __del__(self):
        """析构函数，确保资源清理"""
        self.stop_consuming()

    async def __aenter__(self):
        """异步上下文管理器入口"""
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """异步上下文管理器出口"""
        self.stop_consuming()