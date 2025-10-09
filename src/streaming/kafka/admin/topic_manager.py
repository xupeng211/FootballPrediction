"""
Kafka主题管理器
"""

import logging
from typing import Any, Dict, Optional

try:
    from confluent_kafka import KafkaError, KafkaException
    from confluent_kafka.admin import AdminClient, NewTopic
    KAFKA_TOPIC_AVAILABLE = True
except ImportError:
    KAFKA_TOPIC_AVAILABLE = False
    AdminClient = None
    NewTopic = None
    KafkaError = None
    KafkaException = None

from src.streaming.kafka.config.stream_config import StreamConfig

logger = logging.getLogger(__name__)

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


class KafkaTopicManager:
    """Kafka主题管理器"""

    def __init__(self, config: Optional[StreamConfig] = None):
        """
        初始化主题管理器

        Args:
            config: 流配置
        """
        if not KAFKA_TOPIC_AVAILABLE:
            raise ImportError("confluent_kafka 未安装，无法使用Kafka功能")

        self.config = config or StreamConfig()
        self.admin_client = None

        try:
            self.admin_client = AdminClient(
                {"bootstrap.servers": self.config.bootstrap_servers}
            )
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