"""
消息处理器

负责处理Kafka消息的解析、反序列化和路由。
"""

import json
import logging
from typing import Any, Dict

from .data_processor import DataProcessor


class MessageProcessor:
    """消息处理器"""

    def __init__(self, db_manager):
        """
        初始化消息处理器

        Args:
            db_manager: 数据库管理器
        """
        self.db_manager = db_manager
        self.data_processor = DataProcessor(db_manager)
        self.logger = logging.getLogger(__name__)

    def deserialize_message(self, message_value: bytes) -> Dict[str, Any]:
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

    async def process_message(self, msg) -> bool:
        """
        处理单个消息

        Args:
            msg: Kafka消息对象

        Returns:
            处理是否成功
        """
        try:
            # 反序列化消息
            message_data = self.deserialize_message(msg.value())
            data_type = message_data.get("data_type")

            # 根据数据类型路由到相应的处理器
            if data_type == "match":
                return await self.data_processor.process_match_message(message_data)
            elif data_type == "odds":
                return await self.data_processor.process_odds_message(message_data)
            elif data_type == "scores":
                return await self.data_processor.process_scores_message(message_data)
            else:
                self.logger.warning(f"未知的数据类型: {data_type}")
                return False

        except Exception as e:
            self.logger.error(f"处理消息失败: {e}")
            return False

    async def process_message_data(self, message_data: Dict[str, Any]) -> bool:
        """
        处理消息数据（测试兼容性方法）

        Args:
            message_data: 消息数据

        Returns:
            处理是否成功
        """
        try:
            topic = message_data.get("topic", "")
            data = message_data.get("data", {})

            if "matches" in topic:
                return await self.data_processor.process_match_message(data)
            elif "odds" in topic:
                return await self.data_processor.process_odds_message(data)
            elif "scores" in topic:
                return await self.data_processor.process_scores_message(data)
            else:
                self.logger.warning(f"未知的topic: {topic}")
                return False

        except Exception as e:
            self.logger.error(f"处理消息失败: {e}")
            return False