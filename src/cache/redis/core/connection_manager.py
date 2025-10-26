"""
Redis connection manager
"""

import os
import redis.asyncio as aioredis
from redis.exceptions import RedisError
from typing import Optional

class RedisConnectionManager:
    """管理Redis连接的类"""

    def __init__(self):
        self._pool: Optional[aioredis.ConnectionPool] = None
        self._redis: Optional[aioredis.Redis] = None

    async def connect(self) -> aioredis.Redis:
        """建立Redis连接"""
        if self._redis is None:
            # 使用环境变量或默认URL
            redis_url = os.getenv("REDIS_URL", "redis://localhost:6379")
            self._pool = aioredis.ConnectionPool.from_url(
                redis_url, encoding="utf-8", decode_responses=True
            )
            self._redis = aioredis.Redis(connection_pool=self._pool)
        return self._redis

    async def disconnect(self):
        """关闭Redis连接"""
        if self._redis:
            await self._redis.close()
            self._redis = None

    async def health_check(self) -> bool:
        """检查Redis健康状态"""
        try:
            redis = await self.connect()
            await redis.ping()
            return True
        except (RedisError, ConnectionError, TimeoutError, ValueError):
            return False
