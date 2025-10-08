"""
Kafka生产者实现

提供足球数据的Kafka生产者功能，支持：
- 比赛数据发送到Kafka流
- 赔率数据发送到Kafka流
- 比分数据发送到Kafka流
- 批量发送和错误处理
"""

import asyncio
import json
import logging
from dataclasses import asdict
from datetime import datetime
from typing import Any, Dict, List, Optional, cast

from confluent_kafka import Producer

from .stream_config import StreamConfig

# 为了测试兼容性添加的别名
KafkaProducer = Producer


class FootballKafkaProducer:
    """
    足球数据Kafka生产者

    负责将采集的足球数据发送到Kafka流中，支持：
    - 异步批量发送
    - 错误处理和重试
    - 消息序列化
    - 发送状态监控
    """

    def __init__(self, config: Optional[StreamConfig] = None):
        """
        初始化Kafka生产者

        Args:
            config: 流配置，如果为None则使用默认配置
        """
        self.config = config or StreamConfig()
        self.producer = None
        self.logger = logging.getLogger(__name__)
        # 在初始化时尝试创建producer，如果失败则抛出异常
        self._initialize_producer()

    def _initialize_producer(self) -> None:
        """初始化Kafka Producer"""
        try:
            producer_config = self.config.get_producer_config()
            self.producer = Producer(producer_config)
            self.logger.info(
                f"Kafka Producer已初始化，服务器: {producer_config['bootstrap.servers']}"
            )
        except Exception as e:
            self.logger.error(f"初始化Kafka Producer失败: {e}")
            raise

    def __enter__(self):
        """上下文管理器入口"""
        self._initialize_producer()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """上下文管理器出口"""
        self.close()

    def _create_producer(self) -> None:
        """创建Kafka Producer - 测试兼容性方法"""
        if self.producer is None:
            self._initialize_producer()

    def _serialize_message(self, data: Any) -> str:
        """
        序列化消息数据

        Args:
            data: 需要序列化的数据

        Returns:
            序列化后的JSON字符串
        """
        try:
            # 特殊情况处理
            if data is None:
                return ""
            if isinstance(data, str):
                return data

            # 处理dataclass对象
            if hasattr(data, "__dataclass_fields__"):
                data = asdict(data)

            # 处理datetime对象
            if isinstance(data, dict):
                for key, value in data.items():
                    if isinstance(value, datetime):
                        data[key] = value.isoformat()

            return json.dumps(data, ensure_ascii=False, default=str)
        except (TypeError, ValueError) as e:
            self.logger.error(f"消息序列化失败: {e}")
            raise

    def _delivery_callback(self, err: Optional[Exception], msg) -> None:
        """
        消息发送回调函数

        Args:
            err: 发送错误，None表示成功
            msg: 消息对象
        """
        if err is not None:
            self.logger.error(f"消息发送失败: {err}")
        else:
            self.logger.debug(
                f"消息发送成功 - Topic: {msg.topic()}, "
                f"Partition: {msg.partition()}, Offset: {msg.offset()}"
            )

    async def send_match_data(
        self, match_data: Dict[str, Any], key: Optional[str] = None
    ) -> bool:
        """
        发送比赛数据到Kafka流

        Args:
            match_data: 比赛数据字典
            key: 消息key，用于分区，默认使用match_id

        Returns:
            发送是否成功
        """
        try:
            self._create_producer()
            if not self.producer:
                self.logger.error("Kafka Producer初始化失败")
                return False

            topic = "matches-stream"
            message_key = key or str(match_data.get(str("match_id"), ""))

            # 添加元数据
            message_with_meta = {
                "timestamp": datetime.now().isoformat(),
                "data_type": "match",
                "source": "data_collector",
                "data": match_data,
            }

            self.producer.produce(
                topic=topic,
                key=message_key,
                value=self._serialize_message(message_with_meta),
                callback=self._delivery_callback,
            )

            # 异步刷新（不阻塞）
            self.producer.poll(0)

            self.logger.info(
                f"比赛数据已发送到Kafka - Match ID: {match_data.get('match_id')}"
            )
            return True

        except Exception as e:
            self.logger.error(f"发送比赛数据失败: {e}")
            return False

    async def send_odds_data(
        self, odds_data: Dict[str, Any], key: Optional[str] = None
    ) -> bool:
        """
        发送赔率数据到Kafka流

        Args:
            odds_data: 赔率数据字典
            key: 消息key，默认使用match_id

        Returns:
            发送是否成功
        """
        try:
            self._create_producer()
            if not self.producer:
                self.logger.error("Kafka Producer初始化失败")
                return False

            topic = "odds-stream"
            message_key = key or str(odds_data.get(str("match_id"), ""))

            # 添加元数据
            message_with_meta = {
                "timestamp": datetime.now().isoformat(),
                "data_type": "odds",
                "source": "data_collector",
                "bookmaker": odds_data.get("bookmaker"),
                "market_type": odds_data.get("market_type"),
                "data": odds_data,
            }

            self.producer.produce(
                topic=topic,
                key=message_key,
                value=self._serialize_message(message_with_meta),
                callback=self._delivery_callback,
            )

            self.producer.poll(0)

            self.logger.debug(
                f"赔率数据已发送到Kafka - Match: {odds_data.get('match_id')}, "
                f"Bookmaker: {odds_data.get('bookmaker')}"
            )
            return True

        except Exception as e:
            self.logger.error(f"发送赔率数据失败: {e}")
            return False

    async def send_scores_data(
        self, scores_data: Dict[str, Any], key: Optional[str] = None
    ) -> bool:
        """
        发送比分数据到Kafka流

        Args:
            scores_data: 比分数据字典
            key: 消息key，默认使用match_id

        Returns:
            发送是否成功
        """
        try:
            self._create_producer()
            if not self.producer:
                self.logger.error("Kafka Producer初始化失败")
                return False

            topic = "scores-stream"
            message_key = key or str(scores_data.get(str("match_id"), ""))

            # 添加元数据
            message_with_meta = {
                "timestamp": datetime.now().isoformat(),
                "data_type": "scores",
                "source": "data_collector",
                "match_status": scores_data.get("match_status"),
                "match_minute": scores_data.get("match_minute"),
                "data": scores_data,
            }

            self.producer.produce(
                topic=topic,
                key=message_key,
                value=self._serialize_message(message_with_meta),
                callback=self._delivery_callback,
            )

            self.producer.poll(0)

            self.logger.debug(
                f"比分数据已发送到Kafka - Match: {scores_data.get('match_id')}, "
                f"Status: {scores_data.get('match_status')}"
            )
            return True

        except Exception as e:
            self.logger.error(f"发送比分数据失败: {e}")
            return False

    async def send_batch(
        self, data_list: List[Dict[str, Any]], data_type: str
    ) -> Dict[str, int]:
        """
        批量发送数据

        Args:
            data_list: 数据列表
            data_type: 数据类型 (match/odds/scores)

        Returns:
            发送统计 {success: 成功数量, failed: 失败数量}
        """
        # 处理空数据情况
        if not data_list:
            return {"success": 0, "failed": 0}

        stats = {"success": 0, "failed": 0}

        # 根据数据类型选择发送方法
        send_method_map = {
            "match": self.send_match_data,
            "odds": self.send_odds_data,
            "scores": self.send_scores_data,
        }

        send_method = send_method_map.get(data_type)
        if not send_method:
            self.logger.error(f"不支持的数据类型: {data_type}")
            stats["failed"] = len(data_list)
            return stats

        # 批量发送
        tasks = []
        for data in data_list:
            task = send_method(data)
            tasks.append(task)

        # 等待所有发送完成
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # 统计结果
        for result in results:
            if isinstance(result, Exception):
                stats["failed"] += 1
                self.logger.error(f"批量发送异常: {result}")
            elif result:
                stats["success"] += 1
            else:
                stats["failed"] += 1

        self.logger.info(
            f"批量发送完成 - 类型: {data_type}, "
            f"成功: {stats['success']}, 失败: {stats['failed']}"
        )

        # 返回统计信息
        return stats

    def flush(self, timeout: float = 10.0) -> None:
        """
        刷新所有待发送消息

        Args:
            timeout: 超时时间（秒）
        """
        if self.producer:
            try:
                remaining = self.producer.flush(timeout)
                # 确保remaining是一个数字，处理Mock对象的情况
                if isinstance(remaining, int) and remaining > 0:
                    self.logger.warning(f"刷新超时，仍有{remaining}条消息未发送")
                else:
                    self.logger.info("所有消息已成功发送")
            except Exception as e:
                self.logger.error(f"刷新消息时出错: {e}")

    def close(self, timeout: Optional[float] = None) -> None:
        """关闭生产者"""
        if self.producer:
            if timeout is not None:
                self.producer.flush(timeout)
            else:
                self.flush()
            self.producer = None
            self.logger.info("Kafka Producer已关闭")

    def get_producer_config(self) -> Dict[str, Any]:
        """获取生产者配置"""
        return self.config.get_producer_config()

    def health_check(self) -> bool:
        """健康检查"""
        try:
            if not self.producer:
                return False
            # 尝试获取topic列表来检查连接
            self.producer.list_topics(timeout=5.0)
            return True
        except Exception as e:
            self.logger.error(f"健康检查失败: {e}")
            return False

    def _serialize_data(self, data: Any) -> str:
        """序列化数据 - 兼容测试代码"""
        return self._serialize_message(data)

    def _validate_match_data(self, data: Dict[str, Any]) -> bool:
        """
        验证比赛数据格式

        Args:
            data: 比赛数据字典

        Returns:
            bool: 数据是否有效
        """
        try:
            # 基本字段检查
            if not isinstance(data, dict):
                return False

            # 检查必要字段
            required_fields = ["match_id"]
            for field in required_fields:
                if field not in data:
                    return False

            # 验证match_id是数字
            if not isinstance(data.get(str("match_id")), (int, str)):
                return False

            return True
        except Exception as e:
            self.logger.error(f"比赛数据验证失败: {e}")
            return False

    def _validate_odds_data(self, data: Dict[str, Any]) -> bool:
        """
        验证赔率数据格式

        Args:
            data: 赔率数据字典

        Returns:
            bool: 数据是否有效
        """
        try:
            # 基本字段检查
            if not isinstance(data, dict):
                return False

            # 检查必要字段
            required_fields = ["match_id"]
            for field in required_fields:
                if field not in data:
                    return False

            # 验证match_id是数字
            if not isinstance(data.get(str("match_id")), (int, str)):
                return False

            # 验证赔率值是数字（如果存在）
            odds_fields = ["home_odds", "away_odds", "draw_odds"]
            for field in odds_fields:
                if field in data and not isinstance(data[field], (int, float)):
                    return False

            return True
        except Exception as e:
            self.logger.error(f"赔率数据验证失败: {e}")
            return False

    def _validate_scores_data(self, data: Dict[str, Any]) -> bool:
        """
        验证比分数据格式

        Args:
            data: 比分数据字典

        Returns:
            bool: 数据是否有效
        """
        try:
            # 基本字段检查
            if not isinstance(data, dict):
                return False

            # 检查必要字段
            required_fields = ["match_id"]
            for field in required_fields:
                if field not in data:
                    return False

            # 验证match_id是数字
            if not isinstance(data.get(str("match_id")), (int, str)):
                return False

            # 验证比分是数字（如果存在）
            score_fields = [
                "home_score",
                "away_score",
                "ht_home_score",
                "ht_away_score",
            ]
            for field in score_fields:
                if (
                    field in data
                    and data[field] is not None
                    and not isinstance(data[field], int)
                ):
                    return False

            return True
        except Exception as e:
            self.logger.error(f"比分数据验证失败: {e}")
            return False

    def __del__(self):
        """析构函数，确保资源清理"""
        try:
            self.close()
        except Exception:
            pass  # Ignore errors during cleanup

    async def __aenter__(self):
        """异步上下文管理器入口"""
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """异步上下文管理器出口"""
        self.close()
