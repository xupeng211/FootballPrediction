"""
Redis asynchronous operations
"""

import asyncio
import json
import logging
from typing import Any, Dict, List, Optional, Union

import redis.asyncio as aioredis

from src.core.logging import get_logger

logger = get_logger(__name__)


class RedisAsyncOperations:
    """Asynchronous Redis operations"""

    def __init__(self, redis_url: Optional[str] = None):
        """Initialize async operations"""
        self.redis_url = redis_url or "redis://localhost:6379"
        self.client: Optional[aioredis.Redis] = None
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")

    async def connect(self):
        """Connect to Redis"""
        if not self.client:
            self.client = aioredis.from_url(self.redis_url, decode_responses=True)

    async def disconnect(self):
        """Disconnect from Redis"""
        if self.client:
            await self.client.close()
            self.client = None

    async def get(self, key: str) -> Optional[Any]:
        """Get value from Redis"""
        if not self.client:
            await self.connect()
        try:
            value = await self.client.get(key)  # type: ignore
            if value:
                return json.loads(value)
            return None
        except Exception as e:
            self.logger.error(f"Error getting key {key}: {str(e)}")
            return None

    async def set(self, key: str, value: Any, ttl: Optional[int] = None) -> bool:
        """Set value in Redis"""
        if not self.client:
            await self.connect()
        try:
            serialized = json.dumps(value, default=str)
            if ttl:
                return await self.client.setex(key, ttl, serialized)  # type: ignore
            else:
                return await self.client.set(key, serialized)  # type: ignore
        except Exception as e:
            self.logger.error(f"Error setting key {key}: {str(e)}")
            return False

    async def delete(self, key: str) -> bool:
        """Delete key from Redis"""
        if not self.client:
            await self.connect()
        try:
            return bool(await self.client.delete(key))  # type: ignore
        except Exception as e:
            self.logger.error(f"Error deleting key {key}: {str(e)}")
            return False

    async def exists(self, key: str) -> bool:
        """Check if key exists"""
        if not self.client:
            await self.connect()
        try:
            return bool(await self.client.exists(key))  # type: ignore
        except Exception as e:
            self.logger.error(f"Error checking key {key}: {str(e)}")
            return False

    async def expire(self, key: str, ttl: int) -> bool:
        """Set TTL for key"""
        if not self.client:
            await self.connect()
        try:
            return bool(await self.client.expire(key, ttl))  # type: ignore
        except Exception as e:
            self.logger.error(f"Error setting TTL for key {key}: {str(e)}")
            return False
