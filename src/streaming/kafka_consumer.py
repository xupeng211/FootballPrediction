"""
Kafka消费者实现

提供足球数据的Kafka消费者功能，支持：
- 从Kafka流中消费比赛数据
- 从Kafka流中消费赔率数据
- 从Kafka流中消费比分数据
- 数据处理和数据库写入
"""

import asyncio
import json
import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

from confluent_kafka import Consumer, KafkaError, KafkaException

from src.database.connection import DatabaseManager
from src.database.models.raw_data import (RawMatchData, RawOddsData,
                                          RawScoresData)

from .stream_config import StreamConfig

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
        self._initialize_consumer(consumer_group_id)

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

    def _deserialize_message(self, message_value: bytes) -> Dict[str, Any]:
        """
        反序列化消息数据

        Args:
            message_value: 消息内容字节

        Returns:
            反序列化后的数据字典
        """
        try:
            return json.loads(message_value.decode("utf-8"))
        except (json.JSONDecodeError, UnicodeDecodeError) as e:
            self.logger.error(f"消息反序列化失败: {e}")
            raise

    async def _process_match_message(self, message_data: Dict[str, Any]) -> bool:
        """
        处理比赛数据消息

        Args:
            message_data: 消息数据

        Returns:
            处理是否成功
        """
        try:
            # 提取实际的比赛数据
            match_data = message_data.get("data", {})
            data_source = message_data.get("source", "kafka_stream")

            # 创建RawMatchData对象
            raw_match = RawMatchData(
                data_source=data_source,
                raw_data=match_data,
                collected_at=datetime.now(),
                external_match_id=str(match_data.get("match_id", "")),
                external_league_id=str(match_data.get("league_id", "")),
                match_time=(
                    datetime.fromisoformat(match_data["match_time"])
                    if match_data.get("match_time")
                    else None
                ),
            )

            # 写入数据库
            async with self.db_manager.get_async_session() as session:
                session.add(raw_match)
                await session.commit()

            self.logger.info(f"比赛数据已写入数据库 - Match ID: {match_data.get('match_id')}")
            return True

        except Exception as e:
            self.logger.error(f"处理比赛数据失败: {e}")
            return False

    async def _process_odds_message(self, message_data: Dict[str, Any]) -> bool:
        """
        处理赔率数据消息

        Args:
            message_data: 消息数据

        Returns:
            处理是否成功
        """
        try:
            # 提取实际的赔率数据
            odds_data = message_data.get("data", {})
            data_source = message_data.get("source", "kafka_stream")

            # 创建RawOddsData对象
            raw_odds = RawOddsData(
                data_source=data_source,
                raw_data=odds_data,
                collected_at=datetime.now(),
                external_match_id=str(odds_data.get("match_id", "")),
                bookmaker=odds_data.get("bookmaker"),
                market_type=odds_data.get("market_type"),
            )

            # 写入数据库
            async with self.db_manager.get_async_session() as session:
                session.add(raw_odds)
                await session.commit()

            self.logger.debug(
                f"赔率数据已写入数据库 - Match: {odds_data.get('match_id')}, "
                f"Bookmaker: {odds_data.get('bookmaker')}"
            )
            return True

        except Exception as e:
            self.logger.error(f"处理赔率数据失败: {e}")
            return False

    async def _process_scores_message(self, message_data: Dict[str, Any]) -> bool:
        """
        处理比分数据消息

        Args:
            message_data: 消息数据

        Returns:
            处理是否成功
        """
        try:
            # 提取实际的比分数据
            scores_data = message_data.get("data", {})
            data_source = message_data.get("source", "kafka_stream")

            # 创建RawScoresData对象
            raw_scores = RawScoresData(
                data_source=data_source,
                raw_data=scores_data,
                collected_at=datetime.now(),
                external_match_id=str(scores_data.get("match_id", "")),
                match_status=scores_data.get("match_status"),
                home_score=scores_data.get("home_score"),
                away_score=scores_data.get("away_score"),
                match_minute=scores_data.get("match_minute"),
            )

            # 写入数据库
            async with self.db_manager.get_async_session() as session:
                session.add(raw_scores)
                await session.commit()

            self.logger.debug(
                f"比分数据已写入数据库 - Match: {scores_data.get('match_id')}, "
                f"Status: {scores_data.get('match_status')}"
            )
            return True

        except Exception as e:
            self.logger.error(f"处理比分数据失败: {e}")
            return False

    async def _process_message(self, msg) -> bool:
        """
        处理单个消息

        Args:
            msg: Kafka消息对象

        Returns:
            处理是否成功
        """
        try:
            # 反序列化消息
            message_data = self._deserialize_message(msg.value())
            data_type = message_data.get("data_type")

            # 根据数据类型处理消息
            if data_type == "match":
                return await self._process_match_message(message_data)
            elif data_type == "odds":
                return await self._process_odds_message(message_data)
            elif data_type == "scores":
                return await self._process_scores_message(message_data)
            else:
                self.logger.warning(f"未知的数据类型: {data_type}")
                return False

        except Exception as e:
            self.logger.error(f"处理消息失败: {e}")
            return False

    def subscribe_topics(self, topics: List[str]) -> None:
        """
        订阅Topic列表

        Args:
            topics: Topic名称列表
        """
        if not self.consumer:
            self.logger.error("Consumer未初始化")
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

    def subscribe_all_topics(self) -> None:
        """订阅所有配置的Topic"""
        all_topics = self.config.get_all_topics()
        self.subscribe_topics(all_topics)

    async def start_consuming(self, timeout: float = 1.0) -> None:
        """
        开始消费消息

        Args:
            timeout: 轮询超时时间（秒）
        """
        if not self.consumer:
            self.logger.error("Consumer未初始化")
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
                        self.logger.debug(f"分区结束: {msg.topic()} [{msg.partition()}]")
                        continue
                    else:
                        # 其他错误
                        raise KafkaException(msg.error())

                # 处理消息
                success = await self._process_message(msg)

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
        if not self.consumer:
            self.logger.error("Consumer未初始化")
            return {"processed": 0, "failed": 0}

        stats = {"processed": 0, "failed": 0}
        start_time = datetime.now()

        try:
            while stats["processed"] + stats["failed"] < batch_size:
                # 检查超时
                elapsed = (datetime.now() - start_time).total_seconds()
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
                success = await self._process_message(msg)

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

        self.logger.info(f"批量消费完成 - 成功: {stats['processed']}, 失败: {stats['failed']}")
        return stats

    def __del__(self):
        """析构函数，确保资源清理"""
        self.stop_consuming()

    async def __aenter__(self):
        """异步上下文管理器入口"""
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """异步上下文管理器出口"""
        self.stop_consuming()


def get_session():
    """获取数据库会话 - 兼容测试代码"""
    db_manager = DatabaseManager()
    return db_manager.get_async_session()
