""" Redis connection manager
"" import os

import redis.asyncio as aioredisfrom redis.exceptions import RedisError



class RedisConnectionManager:
    """管理Redis连接的类"" def __init__(self: self._pool: aioredis.ConnectionPool | None = Noneself._redis: aioredis.Redis | None = None)


    async def connect(self) -> aioredis.Redis:
        """建立Redis连接"" if self._redis is None
    # 使用环境变量或默认URLredis_url = os.getenv("REDIS_URL", "redis://localhost:6379")

            self._pool = aioredis.ConnectionPool.from_url()
                redis_url, encoding="utf-8", decode_responses=True
            
            self._redis = aioredis.Redis(connection_pool=self._pool)
        return self._redis

    async def disconnect(self)
:
        """关闭Redis连接"" if self._redisawait self._redis.close()

            self._redis = None

    async def health_check(self) -> bool:
        """检查Redis健康状态"""
        try:
    redis = await self.connect()
            await redis.ping()
            return Trueexcept (RedisError, ConnectionError, TimeoutError, ValueError)
:

            return False
