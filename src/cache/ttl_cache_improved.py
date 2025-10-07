"""
改进的TTL缓存实现
Improved TTL Cache Implementation

提供高性能的内存缓存功能，支持：
- 自动过期
- LRU淘汰策略
- 批量操作
- 异步支持
- 统计监控

Provides high-performance in-memory cache with:
- Auto expiration
- LRU eviction
- Batch operations
- Async support
- Statistics monitoring
"""

import asyncio
import heapq
import logging
import time
from collections import OrderedDict
from typing import Any, Dict, List, Optional, Tuple, Union
from threading import RLock

logger = logging.getLogger(__name__)


class CacheEntry:
    """缓存条目"""

    __slots__ = ("key", "value", "expires_at", "access_count", "last_access")

    def __init__(
        self,
        key: str,
        value: Any,
        ttl: Optional[float] = None,
    ):
        self.key = key
        self.value = value
        self.expires_at = time.time() + ttl if ttl else None
        self.access_count = 0
        self.last_access = time.time()

    def is_expired(self) -> bool:
        """检查是否过期"""
        return self.expires_at is not None and time.time() > self.expires_at

    def access(self) -> Any:
        """访问缓存项"""
        self.access_count += 1
        self.last_access = time.time()
        return self.value

    def __lt__(self, other):
        """用于堆排序，比较过期时间"""
        if self.expires_at is None and other.expires_at is None:
            return False
        if self.expires_at is None:
            return False
        if other.expires_at is None:
            return True
        return self.expires_at < other.expires_at


class TTLCache:
    """
    带TTL的LRU缓存
    TTL Cache with LRU Eviction

    提供线程安全的缓存实现，支持自动过期和LRU淘汰策略。
    Provides thread-safe cache with auto expiration and LRU eviction.
    """

    def __init__(
        self,
        max_size: int = 1000,
        default_ttl: Optional[float] = None,
        cleanup_interval: float = 60.0,
    ):
        """
        初始化缓存

        Args:
            max_size: 最大缓存项数
            default_ttl: 默认TTL（秒）
            cleanup_interval: 清理间隔（秒）
        """
        self.max_size = max_size
        self.default_ttl = default_ttl
        self.cleanup_interval = cleanup_interval

        # 存储结构
        self._cache: OrderedDict[str, CacheEntry] = OrderedDict()
        self._expiration_heap: List[CacheEntry] = []
        self._lock = RLock()

        # 统计信息
        self._stats = {
            "hits": 0,
            "misses": 0,
            "sets": 0,
            "deletes": 0,
            "evictions": 0,
            "expirations": 0,
        }

        # 清理任务
        self._cleanup_task: Optional[asyncio.Task] = None
        self._running = False

    def get(self, key: str, default: Any = None) -> Any:
        """
        获取缓存值

        Args:
            key: 缓存键
            default: 默认值

        Returns:
            Any: 缓存值或默认值
        """
        with self._lock:
            entry = self._cache.get(key)

            if entry is None:
                self._stats["misses"] += 1
                return default

            if entry.is_expired():
                self._remove_entry(key)
                self._stats["expirations"] += 1
                self._stats["misses"] += 1
                return default

            # 移到末尾（LRU）
            self._cache.move_to_end(key)
            self._stats["hits"] += 1
            return entry.access()

    def set(
        self,
        key: str,
        value: Any,
        ttl: Optional[float] = None,
    ) -> None:
        """
        设置缓存值

        Args:
            key: 缓存键
            value: 缓存值
            ttl: 生存时间（秒）
        """
        with self._lock:
            # 如果键已存在，更新值
            if key in self._cache:
                entry = self._cache[key]
                entry.value = value
                entry.expires_at = time.time() + ttl if ttl else self.default_ttl
                entry.access()
                self._cache.move_to_end(key)
                self._stats["sets"] += 1
                return

            # 检查容量限制
            if len(self._cache) >= self.max_size:
                self._evict_lru()

            # 创建新条目
            entry_ttl = ttl if ttl is not None else self.default_ttl
            entry = CacheEntry(key, value, entry_ttl)
            self._cache[key] = entry

            # 添加到过期堆
            if entry.expires_at is not None:
                heapq.heappush(self._expiration_heap, entry)

            self._stats["sets"] += 1

    def delete(self, key: str) -> bool:
        """
        删除缓存项

        Args:
            key: 缓存键

        Returns:
            bool: 是否删除成功
        """
        with self._lock:
            if key in self._cache:
                self._remove_entry(key)
                self._stats["deletes"] += 1
                return True
            return False

    def clear(self) -> None:
        """清空缓存"""
        with self._lock:
            self._cache.clear()
            self._expiration_heap.clear()
            logger.info("缓存已清空")

    def pop(self, key: str, default: Any = None) -> Any:
        """
        弹出并删除缓存项

        Args:
            key: 缓存键
            default: 默认值

        Returns:
            Any: 缓存值或默认值
        """
        with self._lock:
            entry = self._cache.pop(key, None)

            if entry is None:
                return default

            if entry.is_expired():
                self._stats["expirations"] += 1
                return default

            self._stats["deletes"] += 1
            return entry.value

    def keys(self) -> List[str]:
        """获取所有键"""
        with self._lock:
            self._cleanup_expired()
            return list(self._cache.keys())

    def values(self) -> List[Any]:
        """获取所有值"""
        with self._lock:
            self._cleanup_expired()
            return [entry.value for entry in self._cache.values()]

    def items(self) -> List[Tuple[str, Any]]:
        """获取所有键值对"""
        with self._lock:
            self._cleanup_expired()
            return [(key, entry.value) for key, entry in self._cache.items()]

    def get_many(self, keys: List[str]) -> Dict[str, Any]:
        """
        批量获取

        Args:
            keys: 键列表

        Returns:
            Dict[str, Any]: 键值对字典
        """
        result = {}
        for key in keys:
            value = self.get(key)
            if value is not None:
                result[key] = value
        return result

    def set_many(self, mapping: Dict[str, Any], ttl: Optional[float] = None) -> None:
        """
        批量设置

        Args:
            mapping: 键值对字典
            ttl: 生存时间（秒）
        """
        for key, value in mapping.items():
            self.set(key, value, ttl)

    def delete_many(self, keys: List[str]) -> int:
        """
        批量删除

        Args:
            keys: 键列表

        Returns:
            int: 删除的数量
        """
        count = 0
        for key in keys:
            if self.delete(key):
                count += 1
        return count

    def increment(self, key: str, delta: int = 1, default: int = 0) -> int:
        """
        递增数值

        Args:
            key: 缓存键
            delta: 递增量
            default: 默认值

        Returns:
            int: 递增后的值
        """
        with self._lock:
            value = self.get(key, default)
            if not isinstance(value, (int, float)):
                raise TypeError(f"缓存值必须是数字类型: {type(value)}")
            new_value = value + delta
            self.set(key, new_value)
            return int(new_value)

    def touch(self, key: str, ttl: Optional[float] = None) -> bool:
        """
        更新缓存项的TTL

        Args:
            key: 缓存键
            ttl: 新的TTL（秒）

        Returns:
            bool: 是否更新成功
        """
        with self._lock:
            entry = self._cache.get(key)
            if entry is None:
                return False

            if ttl is not None:
                entry.expires_at = time.time() + ttl
            else:
                entry.expires_at = time.time() + self.default_ttl if self.default_ttl else None

            entry.access()
            return True

    def ttl(self, key: str) -> Optional[int]:
        """
        获取剩余TTL

        Args:
            key: 缓存键

        Returns:
            Optional[int]: 剩余TTL（秒），None表示永不过期，-1表示不存在
        """
        with self._lock:
            entry = self._cache.get(key)
            if entry is None:
                return -1

            if entry.expires_at is None:
                return None

            remaining = int(entry.expires_at - time.time())
            return remaining if remaining > 0 else 0

    def size(self) -> int:
        """获取缓存大小"""
        with self._lock:
            self._cleanup_expired()
            return len(self._cache)

    def is_empty(self) -> bool:
        """检查缓存是否为空"""
        return self.size() == 0

    def cleanup_expired(self) -> int:
        """
        清理过期项

        Returns:
            int: 清理的数量
        """
        with self._lock:
            return self._cleanup_expired()

    def _cleanup_expired(self) -> int:
        """内部清理方法"""
        current_time = time.time()
        expired_keys = []

        # 检查过期堆
        while (
            self._expiration_heap
            and self._expiration_heap[0].expires_at is not None
            and self._expiration_heap[0].expires_at <= current_time
        ):
            entry = heapq.heappop(self._expiration_heap)
            if entry.key in self._cache:
                expired_keys.append(entry.key)

        # 删除过期项
        for key in expired_keys:
            self._cache.pop(key, None)

        self._stats["expirations"] += len(expired_keys)
        return len(expired_keys)

    def _evict_lru(self) -> None:
        """淘汰最近最少使用的项"""
        if self._cache:
            key, entry = self._cache.popitem(last=False)
            self._stats["evictions"] += 1
            logger.debug(f"淘汰LRU缓存项: {key}")

    def _remove_entry(self, key: str) -> None:
        """移除缓存项"""
        entry = self._cache.pop(key, None)
        if entry:
            # 从过期堆中移除（标记为已删除）
            entry.key = None

    def get_stats(self) -> Dict[str, Any]:
        """获取统计信息"""
        with self._lock:
            total_requests = self._stats["hits"] + self._stats["misses"]
            hit_rate = self._stats["hits"] / total_requests if total_requests > 0 else 0

            return {
                **self._stats,
                "size": len(self._cache),
                "max_size": self.max_size,
                "hit_rate": hit_rate,
                "load_factor": len(self._cache) / self.max_size,
            }

    def start_auto_cleanup(self):
        """启动自动清理任务"""
        if self._running:
            return

        self._running = True
        loop = asyncio.get_event_loop()
        self._cleanup_task = loop.create_task(self._auto_cleanup())

    def stop_auto_cleanup(self):
        """停止自动清理任务"""
        self._running = False
        if self._cleanup_task:
            self._cleanup_task.cancel()
            try:
                asyncio.get_event_loop().run_until_complete(self._cleanup_task)
            except asyncio.CancelledError:
                pass

    async def _auto_cleanup(self):
        """自动清理任务"""
        while self._running:
            try:
                self.cleanup_expired()
                await asyncio.sleep(self.cleanup_interval)
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"自动清理失败: {e}")
                await asyncio.sleep(5)

    def __len__(self) -> int:
        return self.size()

    def __contains__(self, key: str) -> bool:
        return self.get(key) is not None

    def __repr__(self) -> str:
        return f"TTLCache(size={len(self)}, max_size={self.max_size})"


class AsyncTTLCache:
    """
    异步TTL缓存包装器
    Async TTL Cache Wrapper

    为TTLCache提供异步接口。
    Provides async interface for TTLCache.
    """

    def __init__(
        self,
        max_size: int = 1000,
        default_ttl: Optional[float] = None,
        cleanup_interval: float = 60.0,
    ):
        self._cache = TTLCache(max_size, default_ttl, cleanup_interval)

    async def get(self, key: str, default: Any = None) -> Any:
        """异步获取缓存值"""
        return self._cache.get(key, default)

    async def set(
        self,
        key: str,
        value: Any,
        ttl: Optional[float] = None,
    ) -> None:
        """异步设置缓存值"""
        self._cache.set(key, value, ttl)

    async def delete(self, key: str) -> bool:
        """异步删除缓存项"""
        return self._cache.delete(key)

    async def clear(self) -> None:
        """异步清空缓存"""
        self._cache.clear()

    async def get_many(self, keys: List[str]) -> Dict[str, Any]:
        """异步批量获取"""
        return self._cache.get_many(keys)

    async def set_many(
        self,
        mapping: Dict[str, Any],
        ttl: Optional[float] = None,
    ) -> None:
        """异步批量设置"""
        self._cache.set_many(mapping, ttl)

    async def delete_many(self, keys: List[str]) -> int:
        """异步批量删除"""
        return self._cache.delete_many(keys)

    async def size(self) -> int:
        """异步获取缓存大小"""
        return self._cache.size()

    async def get_stats(self) -> Dict[str, Any]:
        """异步获取统计信息"""
        return self._cache.get_stats()

    def start_auto_cleanup(self):
        """启动自动清理"""
        self._cache.start_auto_cleanup()

    def stop_auto_cleanup(self):
        """停止自动清理"""
        self._cache.stop_auto_cleanup()


class CacheFactory:
    """缓存工厂类"""

    @staticmethod
    def create_cache(
        cache_type: str = "sync",
        max_size: int = 1000,
        default_ttl: Optional[float] = None,
        cleanup_interval: float = 60.0,
    ) -> Union[TTLCache, AsyncTTLCache]:
        """
        创建缓存实例

        Args:
            cache_type: 缓存类型 ('sync' 或 'async')
            max_size: 最大缓存项数
            default_ttl: 默认TTL（秒）
            cleanup_interval: 清理间隔（秒）

        Returns:
            Union[TTLCache, AsyncTTLCache]: 缓存实例
        """
        if cache_type == "async":
            return AsyncTTLCache(max_size, default_ttl, cleanup_interval)
        else:
            return TTLCache(max_size, default_ttl, cleanup_interval)

    @staticmethod
    def create_lru_cache(max_size: int = 128) -> TTLCache:
        """创建LRU缓存"""
        return TTLCache(max_size=max_size)

    @staticmethod
    def create_ttl_cache(
        max_size: int = 1000,
        default_ttl: float = 3600,
    ) -> TTLCache:
        """创建TTL缓存"""
        return TTLCache(max_size=max_size, default_ttl=default_ttl)


# 预定义的缓存实例
prediction_cache = TTLCache(max_size=10000, default_ttl=1800)  # 30分钟
feature_cache = TTLCache(max_size=5000, default_ttl=3600)  # 1小时
odds_cache = TTLCache(max_size=20000, default_ttl=300)  # 5分钟

# 启动自动清理
for cache in [prediction_cache, feature_cache, odds_cache]:
    cache.start_auto_cleanup()