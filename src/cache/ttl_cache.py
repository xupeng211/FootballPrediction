"""
TTL缓存管理器 / TTL Cache Manager

提供带TTL（Time-To-Live）支持的缓存管理功能，包括自动过期和内存管理。

Provides TTL (Time-To-Live) supported cache management functionality, including automatic expiration and memory management.

主要类 / Main Classes:
    CacheEntry: 缓存条目，包含值和过期时间 / Cache entry with value and expiration time
    TTLCache: TTL缓存管理器 / TTL cache manager

主要方法 / Main Methods:
    TTLCache.get(): 获取缓存值 / Get cached value
    TTLCache.set(): 设置缓存值 / Set cached value
    TTLCache.delete(): 删除缓存值 / Delete cached value

使用示例 / Usage Example:
    ```python
    from src.cache.ttl_cache import TTLCache
    from datetime import timedelta

    # 创建缓存实例
    cache = TTLCache(max_size=100)

    # 设置缓存值（5分钟后过期）
    await cache.set("key1", "value1", ttl=timedelta(minutes=5))

    # 获取缓存值
    value = await cache.get("key1")

    # 删除缓存值
    await cache.delete("key1")
    ```

环境变量 / Environment Variables:
    CACHE_MAX_SIZE: 缓存最大条目数，默认1000 / Maximum cache entries, default 1000
    CACHE_DEFAULT_TTL_SECONDS: 默认TTL秒数，默认3600(1小时) / Default TTL seconds, default 3600 (1 hour)
"""

import asyncio
import logging
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)


@dataclass
class CacheEntry:
    """
    缓存条目 / Cache Entry

    存储缓存值和相关元数据，包括创建时间和TTL。
    Stores cache value and related metadata, including creation time and TTL.

    Attributes:
        value (Any): 缓存的值 / Cached value
        created_at (datetime): 创建时间 / Creation time
        ttl (Optional[timedelta]): 生存时间 / Time to live
    """

    value: Any
    created_at: datetime
    ttl: Optional[timedelta] = None

    def is_expired(self) -> bool:
        """
        检查缓存条目是否已过期 / Check if cache entry has expired

        Returns:
            bool: 如果缓存条目已过期则返回True，否则返回False /
                  True if cache entry has expired, False otherwise
        """
        if self.ttl is None:
            return False
        return datetime.now() > (self.created_at + self.ttl)

    def get_remaining_ttl(self) -> Optional[timedelta]:
        """
        获取缓存条目剩余的TTL / Get remaining TTL for cache entry

        Returns:
            Optional[timedelta]: 剩余的TTL，如果无TTL则返回None /
                                Remaining TTL, or None if no TTL
        """
        if self.ttl is None:
            return None
        expiration_time = self.created_at + self.ttl
        remaining = expiration_time - datetime.now()
        return remaining if remaining.total_seconds() > 0 else timedelta(0)


class TTLCache:
    """
    TTL缓存管理器 / TTL Cache Manager

    提供带TTL支持的线程安全缓存管理功能。
    Provides thread-safe cache management functionality with TTL support.

    Attributes:
        _cache (Dict[str, CacheEntry]): 缓存存储 / Cache storage
        _max_size (int): 最大缓存条目数 / Maximum cache entries
        _lock (asyncio.Lock): 异步锁用于线程安全 / Async lock for thread safety

    Example:
        ```python
        from src.cache.ttl_cache import TTLCache
        from datetime import timedelta

        # 创建缓存实例
        cache = TTLCache(max_size=100)

        # 设置缓存值
        await cache.set("user:123", {"name": "John", "age": 30}, ttl=timedelta(minutes=10))

        # 获取缓存值
        user = await cache.get("user:123")

        # 获取缓存统计
        stats = await cache.get_stats()
        print(f"缓存条目数: {stats['active_entries']}")
        ```

    Note:
        缓存会在访问时自动清理过期条目。
        Cache automatically cleans up expired entries on access.
    """

    def __init__(self, max_size: int = 1000):
        """
        初始化TTL缓存 / Initialize TTL Cache

        Args:
            max_size (int): 最大缓存条目数 / Maximum cache entries
                Defaults to 1000
        """
        self._cache: Dict[str, CacheEntry] = {}
        self._max_size = max_size
        self._lock = asyncio.Lock()

    async def get(self, key: str) -> Optional[Any]:
        """
        从缓存获取值 / Get value from cache

        Args:
            key (str): 缓存键 / Cache key

        Returns:
            Optional[Any]: 缓存值，如果不存在或已过期则返回None /
                          Cached value, or None if not exists or expired

        Example:
            ```python
            from src.cache.ttl_cache import TTLCache

            cache = TTLCache()
            await cache.set("key1", "value1", ttl=timedelta(minutes=5))

            value = await cache.get("key1")
            if value:
                print(f"获取到缓存值: {value}")
            else:
                print("缓存未命中或已过期")
            ```
        """
        async with self._lock:
            if key in self._cache:
                entry = self._cache[key]
                if not entry.is_expired():
                    logger.debug(f"缓存命中: {key}")
                    return entry.value
                else:
                    logger.debug(f"缓存过期: {key}")
                    del self._cache[key]
            logger.debug(f"缓存未命中: {key}")
            return None

    async def set(self, key: str, value: Any, ttl: Optional[timedelta] = None) -> None:
        """
        设置缓存值 / Set cache value

        Args:
            key (str): 缓存键 / Cache key
            value (Any): 缓存值 / Cache value
            ttl (Optional[timedelta]): 生存时间，如果为None则永不过期 /
                                      Time to live, if None never expires
                Defaults to None

        Example:
            ```python
            from src.cache.ttl_cache import TTLCache
            from datetime import timedelta

            cache = TTLCache()

            # 设置5分钟后过期的缓存
            await cache.set("key1", "value1", ttl=timedelta(minutes=5))

            # 设置永不过期的缓存
            await cache.set("key2", "value2")
            ```

        Note:
            如果缓存已满，会自动清理过期条目和LRU条目。
            If cache is full, automatically cleans up expired entries and LRU entries.
        """
        async with self._lock:
            # Check if we need to evict items
            if len(self._cache) >= self._max_size:
                await self._evict_expired()
                if len(self._cache) >= self._max_size:
                    await self._evict_lru()

            self._cache[key] = CacheEntry(
                value=value, created_at=datetime.now(), ttl=ttl
            )
            logger.debug(f"缓存设置: {key} TTL: {ttl}")

    async def delete(self, key: str) -> bool:
        """
        从缓存删除值 / Delete value from cache

        Args:
            key (str): 缓存键 / Cache key

        Returns:
            bool: 如果删除成功返回True，如果键不存在返回False /
                  True if deleted successfully, False if key not exists

        Example:
            ```python
            from src.cache.ttl_cache import TTLCache

            cache = TTLCache()
            await cache.set("key1", "value1")

            # 删除缓存
            success = await cache.delete("key1")
            if success:
                print("缓存删除成功")
            else:
                print("缓存键不存在")
            ```
        """
        async with self._lock:
            if key in self._cache:
                del self._cache[key]
                logger.debug(f"缓存删除: {key}")
                return True
            return False

    async def clear(self) -> None:
        """
        清空所有缓存 / Clear all cache

        Example:
            ```python
            from src.cache.ttl_cache import TTLCache

            cache = TTLCache()
            await cache.set("key1", "value1")
            await cache.set("key2", "value2")

            # 清空所有缓存
            await cache.clear()
            print("所有缓存已清空")
            ```
        """
        async with self._lock:
            self._cache.clear()
            logger.debug("缓存已清空")

    async def _evict_expired(self) -> None:
        """Evict expired entries"""
        expired_keys = [key for key, entry in self._cache.items() if entry.is_expired()]
        for key in expired_keys:
            del self._cache[key]
        logger.debug(f"清除 {len(expired_keys)} 个过期条目")

    async def _evict_lru(self) -> None:
        """Evict least recently used entry"""
        if self._cache:
            # Find oldest entry
            oldest_key = min(
                self._cache.keys(), key=lambda k: self._cache[k].created_at
            )
            del self._cache[oldest_key]
            logger.debug(f"清除最近最少使用的条目: {oldest_key}")

    async def get_stats(self) -> Dict[str, Any]:
        """
        获取缓存统计信息 / Get cache statistics

        Returns:
            Dict[str, Any]: 缓存统计信息 / Cache statistics
                - total_entries (int): 总条目数 / Total entries
                - active_entries (int): 活跃条目数 / Active entries
                - expired_entries (int): 过期条目数 / Expired entries
                - max_size (int): 最大条目数 / Maximum entries

        Example:
            ```python
            from src.cache.ttl_cache import TTLCache

            cache = TTLCache()
            await cache.set("key1", "value1")
            await cache.set("key2", "value2")

            stats = await cache.get_stats()
            print(f"活跃条目: {stats['active_entries']}")
            print(f"总条目: {stats['total_entries']}")
            ```
        """
        async with self._lock:
            total_entries = len(self._cache)
            expired_entries = sum(
                1 for entry in self._cache.values() if entry.is_expired()
            )
            active_entries = total_entries - expired_entries

            return {
                "total_entries": total_entries,
                "active_entries": active_entries,
                "expired_entries": expired_entries,
                "max_size": self._max_size,
            }
