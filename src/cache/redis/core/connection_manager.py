"""
Redis connection manager
"""

import asyncio
import aioredis
from typing import Optional
from src.core.config import get_config


class RedisConnectionManager:
    """管理Redis连接的类"""

    def __init__(self):
        self._pool: Optional[aioredis.ConnectionPool] = None
        self._redis: Optional[aioredis.Redis] = None

    async def connect(self) -> aioredis.Redis:
        """建立Redis连接"""
        if self._redis is None:
            config = get_config()
            self._pool = aioredis.ConnectionPool.from_url(
                config.REDIS_URL,
                encoding="utf-8",
                decode_responses=True
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
        except Exception:
            return False