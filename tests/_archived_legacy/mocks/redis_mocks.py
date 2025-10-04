"""""""
Mock Redis objects for testing.
"""""""

from typing import Any, Dict, Optional
import asyncio
import json
import time


class MockRedisManager:
    """Mock Redis manager for testing."""""""

    def __init__(self, should_fail = False):
        self.should_fail = should_fail
        self.cache = {}
        self.expirations = {}
        self.stats = {
            "get_calls[": 0,""""
            "]set_calls[": 0,""""
            "]delete_calls[": 0,""""
            "]hits[": 0,""""
            "]misses[": 0,""""
        }

    async def get(self, key: str) -> Optional[Any]:
        "]""Mock Redis GET operation."""""""
        if self.should_fail:
            raise Exception("Redis connection failed[")": self.stats["]get_calls["] += 1[": await asyncio.sleep(0.001)  # Simulate network latency["""

        # Check if key exists and hasn't expired
        if key in self.cache:
            if key in self.expirations and time.time() > self.expirations[key]:
                del self.cache[key]
                del self.expirations[key]
                self.stats["]]]misses["] += 1[": return None[": self.stats["]]]hits["] += 1[": return self.cache[key]": self.stats["]]misses["] += 1[": return None[": async def set(self, key: str, value: Any, ttl: Optional[int] = None) -> bool:""
        "]]]""Mock Redis SET operation."""""""
        if self.should_fail:
            raise Exception("Redis connection failed[")": self.stats["]set_calls["] += 1[": await asyncio.sleep(0.001)  # Simulate network latency["""

        # Store value (serialize complex objects)
        if isinstance(value, (dict, list)):
            try:
                self.cache[key] = json.dumps(value)
            except (TypeError, ValueError):
                self.cache[key] = str(value)
        else:
            self.cache[key] = value

        # Set expiration if TTL provided
        if ttl:
            self.expirations[key] = time.time() + ttl

        return True

    async def delete(self, key: str) -> bool:
        "]]]""Mock Redis DELETE operation."""""""
        if self.should_fail:
            raise Exception("Redis connection failed[")": self.stats["]delete_calls["] += 1[": await asyncio.sleep(0.001)  # Simulate network latency[": if key in self.cache:": del self.cache[key]"
            if key in self.expirations:
                del self.expirations[key]
            return True
        return False

    async def exists(self, key: str) -> bool:
        "]]]""Mock Redis EXISTS operation."""""""
        if self.should_fail:
            raise Exception("Redis connection failed[")": await asyncio.sleep(0.001)  # Simulate network latency[": return key in self.cache and (": key not in self.expirations or time.time() <= self.expirations[key]"
        )

    async def expire(self, key: str, ttl: int) -> bool:
        "]]""Mock Redis EXPIRE operation."""""""
        if self.should_fail:
            raise Exception("Redis connection failed[")": await asyncio.sleep(0.001)  # Simulate network latency[": if key in self.cache:": self.expirations[key] = time.time() + ttl"
            return True
        return False

    async def ttl(self, key: str) -> Optional[int]:
        "]]""Mock Redis TTL operation."""""""
        if self.should_fail:
            raise Exception("Redis connection failed[")": await asyncio.sleep(0.001)  # Simulate network latency[": if key not in self.cache:": return None"

        if key not in self.expirations:
            return -1  # No expiration set

        remaining = self.expirations[key] - time.time()
        return max(0, int(remaining)) if remaining > 0 else None

    async def incr(self, key: str, amount = int 1) -> int:
        "]]""Mock Redis INCR operation."""""""
        if self.should_fail:
            raise Exception("Redis connection failed[")": await asyncio.sleep(0.001)  # Simulate network latency[": current_value = await self.get(key)": if current_value is None = current_value 0"
        elif isinstance(current_value, str):
            try = current_value int(current_value)
            except ValueError = current_value 0

        new_value = current_value + amount
        await self.set(key, new_value)
        return new_value

    async def decr(self, key: str, amount = int 1) -> int:
        "]]""Mock Redis DECR operation."""""""
        return await self.incr(key, -amount)

    async def hget(self, key: str, field: str) -> Optional[Any]:
        """Mock Redis HGET operation."""""""
        if self.should_fail:
            raise Exception("Redis connection failed[")": await asyncio.sleep(0.001)  # Simulate network latency[": hash_data = await self.get(key)": if isinstance(hash_data, dict):"
            return hash_data.get(field)
        return None

    async def hset(self, key: str, field: str, value: Any) -> bool:
        "]]""Mock Redis HSET operation."""""""
        if self.should_fail:
            raise Exception("Redis connection failed[")": await asyncio.sleep(0.001)  # Simulate network latency[": hash_data = await self.get(key) or {}": if not isinstance(hash_data, dict):"
            hash_data = {}

        hash_data[field] = value
        await self.set(key, hash_data)
        return True

    async def hgetall(self, key: str) -> Dict[str, Any]:
        "]]""Mock Redis HGETALL operation."""""""
        if self.should_fail:
            raise Exception("Redis connection failed[")": await asyncio.sleep(0.001)  # Simulate network latency[": hash_data = await self.get(key)": return hash_data if isinstance(hash_data, dict) else {}"

    async def lpush(self, key: str, *values: Any) -> int:
        "]]""Mock Redis LPUSH operation."""""""
        if self.should_fail:
            raise Exception("Redis connection failed[")": await asyncio.sleep(0.001)  # Simulate network latency[": list_data = await self.get(key) or []": if not isinstance(list_data, list):"
            list_data = []

        list_data = list(values) + list_data
        await self.set(key, list_data)
        return len(list_data)

    async def rpush(self, key: str, *values: Any) -> int:
        "]]""Mock Redis RPUSH operation."""""""
        if self.should_fail:
            raise Exception("Redis connection failed[")": await asyncio.sleep(0.001)  # Simulate network latency[": list_data = await self.get(key) or []": if not isinstance(list_data, list):"
            list_data = []

        list_data.extend(values)
        await self.set(key, list_data)
        return len(list_data)

    async def llen(self, key: str) -> int:
        "]]""Mock Redis LLEN operation."""""""
        if self.should_fail:
            raise Exception("Redis connection failed[")": await asyncio.sleep(0.001)  # Simulate network latency[": list_data = await self.get(key) or []": return len(list_data) if isinstance(list_data, list) else 0"

    async def flushall(self) -> bool:
        "]]""Mock Redis FLUSHALL operation."""""""
        if self.should_fail:
            raise Exception("Redis connection failed[")": await asyncio.sleep(0.001)  # Simulate network latency[": self.cache.clear()": self.expirations.clear()"
        return True

    async def health_check(self) -> bool:
        "]]""Mock Redis health check."""""""
        if self.should_fail:
            return False
        return True

    def get_stats(self) -> Dict[str, Any]:
        """Get mock Redis statistics."""""""
        return {
            **self.stats,
            "cache_size[": len(self.cache),""""
            "]expiration_keys[": len(self.expirations),""""
            "]hit_rate[": self.stats["]hits["] / max(1, self.stats["]get_calls["]),""""
        }

    def set_cache_value(self, key: str, value: Any, ttl: Optional[int] = None):
        "]""Directly set cache value for testing."""""""
        self.cache[key] = value
        if ttl:
            self.expirations[key] = time.time() + ttl

    def simulate_expiry(self, key: str):
        """Simulate key expiration for testing."""""""
        if key in self.cache:
            del self.cache[key]
        if key in self.expirations:
            del self.expirations[key]

    def reset(self):
        """Reset mock state."""""""
        self.cache.clear()
        self.expirations.clear()
        self.stats = {
            "get_calls[": 0,""""
            "]set_calls[": 0,""""
            "]delete_calls[": 0,""""
            "]hits[": 0,""""
            "]misses[": 0,""""
        }


class MockRedisPubSub:
    "]""Mock Redis Pub/Sub for testing."""""""

    def __init__(self):
        self.subscribers = {}
        self.messages = []

    async def publish(self, channel: str, message: Any) -> int:
        """Mock Redis PUBLISH operation."""""""
        await asyncio.sleep(0.001)  # Simulate network latency

        if channel in self.subscribers:
            for callback in self.subscribers[channel]:
                try:
                    if asyncio.iscoroutinefunction(callback):
                        await callback(channel, message)
                    else:
                        callback(channel, message)
                except Exception:
                    pass  # Ignore callback errors in testing
            return len(self.subscribers[channel])
        return 0

    async def subscribe(self, channel: str, callback):
        """Mock Redis SUBSCRIBE operation."""""""
        await asyncio.sleep(0.001)  # Simulate network latency

        if channel not in self.subscribers:
            self.subscribers[channel] = []
        self.subscribers[channel].append(callback)

    async def unsubscribe(self, channel: str, callback):
        """Mock Redis UNSUBSCRIBE operation."""""""
        await asyncio.sleep(0.001)  # Simulate network latency

        if channel in self.subscribers and callback in self.subscribers[channel]:
            self.subscribers[channel].remove(callback)

    def get_channels(self) -> list:
        """Get list of active channels."""""""
        return list(self.subscribers.keys())

    def get_subscriber_count(self, channel: str) -> int:
        """Get subscriber count for a channel."""""""
        return len(self.subscribers.get(channel, []))
