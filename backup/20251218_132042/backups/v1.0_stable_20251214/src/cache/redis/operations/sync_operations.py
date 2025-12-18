import json
import logging
from typing import Any

from redis.exceptions import RedisError

"""

Redis synchronous operations
"""


logger = logging.getLogger(__name__)


class RedisSyncOperations:
    """类文档字符串."""

    pass  # 添加pass语句
    """Synchronous Redis operations"""

    def __init__(self, redis_client=None):
        """函数文档字符串."""
        # 添加pass语句
        """Initialize sync operations"""
        self.client = redis_client
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")

    def get(self, key: str) -> Any | None:
        """Get value from Redis."""
        if not self.client:
            return None
        try:
            value = self.client.get(key)
            if value:
                return json.loads(value)
            return None
        except (RedisError, ConnectionError, TimeoutError, ValueError) as e:
            self.logger.error(f"Error getting key {key}: {str(e)}")
            return None

    def set(self, key: str, value: Any, ttl: int | None = None) -> bool:
        """set value in Redis."""
        if not self.client:
            return False
        try:
            serialized = json.dumps(value, default=str)
            if ttl:
                return self.client.setex(key, ttl, serialized)
            else:
                return self.client.set(key, serialized)
        except (RedisError, ConnectionError, TimeoutError, ValueError) as e:
            self.logger.error(f"Error setting key {key}: {str(e)}")
            return False

    def delete(self, key: str) -> bool:
        """Delete key from Redis."""
        if not self.client:
            return False
        try:
            return bool(self.client.delete(key))
        except (RedisError, ConnectionError, TimeoutError, ValueError) as e:
            self.logger.error(f"Error deleting key {key}: {str(e)}")
            return False

    def exists(self, key: str) -> bool:
        """Check if key exists."""
        if not self.client:
            return False
        try:
            return bool(self.client.exists(key))
        except (RedisError, ConnectionError, TimeoutError, ValueError) as e:
            self.logger.error(f"Error checking key {key}: {str(e)}")
            return False
