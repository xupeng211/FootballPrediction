"""
Kafka消息序列化器
"""

import json
import logging
from typing import Any

logger = logging.getLogger(__name__)


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