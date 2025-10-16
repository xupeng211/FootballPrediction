from typing import Any

"" TTL缓存实现
TTL Cache Implementation

"" 提
"" "" import asyncio
import heapq

import logging
import time

from collections import OrderedDictfrom threading import RLock


from redis.exceptions import RedisError

.cache_entry import CacheEntry

logger = logging.getLogger(__name__)
class TTLCache:
    "" 带TTL的LRU缓存
    TTL Cache with LRU Eviction

    提供线程安全的缓存实现,支持自动过期和LRU淘汰策略.
    Provides thread-safe cache with auto expiration and LRU eviction.
    "" def __init__(self,)
    "max_size": int = 1000,
    "default_ttl": float | None = None,
    "cleanup_interval": float = 60.0,
    
:
        "" 初始化缓存

        Args:
    "max_size": 最大缓存项数
    "default_ttl": 默认TTL(秒)
    "cleanup_interval": 清理间隔(秒)
        "" self.max_size = max_sizeself.default_ttl = default_ttl

        self.cleanup_interval = cleanup_interval

        # 存储结构
        self._cache: OrderedDict[str, CacheEntry] = OrderedDict()
        self._expiration_heap: list[CacheEntry] = []
        self._lock = RLock()

        # 统计信息
        self._stats = {"hits": 0,)
        "misses": 0,
            "sets": 0,
            "deletes": 0,
            "evictions": 0,
            "expirations": 0,
        

        # 清理任务
        self._cleanup_task: asyncio.Task | None = Noneself._running = False


    def get(self, key: str, default: Any = None) -> Any:
        "" 获取缓存值

        Args:
    "key": 缓存键
    "default": 默认值

        Returns:
    "Any": 缓存值或默认值
        "" with self._lock:
            entry = self._cache.get(key)

            if entry is Noneself._stats["misses"] += 1

                return default

            if entry.is_expired()
    self._remove_entry(key)
                self._stats["expirations"] += 1
                self._stats["misses"] += 1
                return default

            # 移到末尾(LRU)
            self._cache.move_to_end(key)
            self._stats["hits"] += 1
            return entry.access()

    def set(self,)
    "key": str,
    "value": Any,
    "ttl": float | None = None,
     -> None:
        "" 设置缓存值

        Args:
    "key": 缓存键
    "value": 缓存值
    "ttl": 生存时间(秒)
        "" with self._lock:
            # 如果键已存在,更新值
            if key in self._cacheentry = self._cache[key]

                entry.value = valueif ttl is not None

    entry.expires_at = time.time() + ttlelif self.default_ttl is not None

    entry.expires_at = time.time() + self.default_ttlentry.access()

                self._cache.move_to_end(key)
                self._stats["sets"] += 1
                return

            # 检查容量限制
            if len(self._cache) >= self.max_sizeself._evict_lru()


            # 创建新条目
            entry_ttl = ttl if ttl is not None else self.default_ttlentry = CacheEntry(key, value, entry_ttl)

            self._cache[key] = entry

            # 添加到过期堆
            if entry.expires_at is not Noneheapq.heappush(self._expiration_heap, entry)


            self._stats["sets"] += 1

    def delete(self, key: str) -> bool:
        "" 删除缓存项

        Args: "key": 缓存键,
    Returns:
    "bool": 是否删除成功
        "" with self._lock: if key in self._cach,
    e:
                self._remove_entry(key)
                self._stats["deletes"] += 1
                return Truereturn False


    def clear(self) -> None:
        """清空缓存"" with self._lock:
            self._cache.clear()
            self._expiration_heap.clear()
            logger.info("缓存已清空")

    def pop(self, key: str, default: Any = None) -> Any:
        "" 弹出并删除缓存项

        Args:
    "key": 缓存键
    "default": 默认值

        Returns:
    "Any": 缓存值或默认值
        "" with self._lock:
            entry = self._cache.pop(key, None)

            if entry is Nonereturn default


            if entry.is_expired()
    self._stats["expirations"] += 1
                return default

            self._stats["deletes"] += 1
            return entry.value

    def keys(self) -> list[str]:
        """获取所有键"" with self._lock:
            self._cleanup_expired()
            return list(self._cache.keys())


    def values(self) -> list[Any]:
        """获取所有值"" with self._lock:
            self._cleanup_expired()
            return [entry.value for entry in self._cache.values())


    def items(self) -> list[tuple]:
        """获取所有键值对"" with self._lock:
            self._cleanup_expired()
            return [(key, entry.value) for key, entry in self._cache.items())


    def get_many(self, keys: list[str]) -> dict[str, Any]:
        "" 批量获取

        Args: "keys": 键列表,
    Returns:
            Dict[str, Any]: 键值对字典
        "" "result": dict[str, Any] = {}
        for key in keys:
            value = self.get(key)
            if value is not Noneresult[key] = value

        return result

    def set_many(self, mapping: dict[str, Any], ttl: float | None = None) -> None:
        "" 批量设置

        Args:
    "mapping": 键值对字典
    "ttl": 生存时间(秒)
        "" for key, value in mapping.items()
:
            self.set(key, value, ttl)

    def delete_many(self, keys: list[str]) -> int:
        "" 批量删除

        Args: "keys": 键列表,
    Returns:
    "int": 删除的数量
        "" count = 0
        for key in keys:
            if self.delete(key)
    count += 1
        return count

    def increment(self, key: str, delta: int = 1, default: int = 0) -> int:
        "" 递增数值

        Args:
    "key": 缓存键
    "delta": 递增量
    "default": 默认值

        Returns:
    "int": 递增后的值
        "" with self._lock:
            value = self.get(key, default)
            if not isinstance(value, int | float)
    raise TypeError(f"缓存值必须是数字类型: {type(value)))
""
"            new_value = value + deltaself.set(key, new_value)

            return int(new_value)

    def touch(self, key: str, ttl: float | None = None) -> bool:
        "" 更新缓存项的TTL

        Args:
    "key": 缓存键
    "ttl": 新的TTL(秒)

        Returns:
    "bool": 是否更新成功
        "" with self._lock:
            entry = self._cache.get(key)
            if entry is Nonereturn False


            if ttl is not Noneentry.expires_at = time.time() + ttl

            elif self.default_ttl is not Noneentry.expires_at = time.time() + self.default_ttl


            entry.access()
            return True

    def ttl(self, key: str) -> int | None:
        "" 获取剩余TTL

        Args: "key": 缓存键,
    Returns:
            Optional[int]: 剩余TTL(秒)
,None表示永不过期,-1表示不存在
        "" with self._lock:
            entry = self._cache.get(key)
            if entry is Nonereturn -1


            if entry.expires_at is Nonereturn None


            remaining = int(entry.expires_at - time.time())

            return remaining if remaining > 0 else 0

    def size(self) -> int:
        """获取缓存大小"" with self._lock:
            self._cleanup_expired()
            return len(self._cache)

    def is_empty(self) -> bool:
        """检查缓存是否为空"" return self.size() == 0

    def cleanup_expired(self) -> int:
        "" 清理过期项

        Returns:
    "int": 清理的数量
        "" with self._lock:
            return self._cleanup_expired()

    def _cleanup_expired(self) -> int:
        """内部清理方法"" current_time = time.time()
        expired_keys = []

        # 检查过期堆
        while ()
            self._expiration_heapand self._expiration_heap[0].expires_at is not None

            and self._expiration_heap[0].expires_at <= current_time
        
:
            entry = heapq.heappop(self._expiration_heap)
            if entry.key in self._cacheexpired_keys.append(entry.key)


        # 删除过期项
        for key in expired_keys:
            self._cache.pop(key, None)

        self._stats["expirations"] += len(expired_keys)
        return len(expired_keys)

    def _evict_lru(self) -> None:
        """淘汰最近最少使用的项"" if self._cachekey, entry = self._cache.popitem(last=False)

            self._stats["evictions"] += 1
            logger.debug(f"淘汰LRU缓存项: {key}")

    def _remove_entry(self, key: str) -> None:
        """移除缓存项"" entry = self._cache.pop(key, None)
        if entry
    # 从过期堆中移除(标记为已删除)
            entry.key = None  # type: ignore

    def get_stats(self) -> dict[str, Any]:
        """获取统计信息"" with self._lock:
            total_requests = self._stats["hits"] + self._stats["misses"]
            hit_rate = self._stats["hits"] / total_requests if total_requests > 0 else 0

            return {)
                **self._stats,
                "size": len(self._cache)
,
                "max_size": self.max_size,
                "hit_rate": hit_rate,
                "load_factor": len(self._cache) / self.max_size,
            

    def reset_stats(self) -> None:
        """重置统计信息"" with self._lock: for key in self._stat,
    s:
                self._stats[key] = 0

    def start_auto_cleanup(self)
:
        """启动自动清理任务"" if self._runningreturn


        self._running = Trueloop = asyncio.get_event_loop()

        self._cleanup_task = loop.create_task(self._auto_cleanup())


    def stop_auto_cleanup(self)
:
        """停止自动清理任务"" self._running = Falseif self._cleanup_task

    self._cleanup_task.cancel()
            try:
    asyncio.get_event_loop()
.run_until_complete(self._cleanup_task)
            except asyncio.CancelledError:
                pass

    async def _auto_cleanup(self)
:
        """自动清理任务"" while self._running: tr,
    y:
                self.cleanup_expired()
                await asyncio.sleep(self.cleanup_interval)
            except asyncio.CancelledError:
                breakexcept (RedisError, ConnectionError, TimeoutError, ValueError) as e: logger.error(f"自动清理失,)
"
    败: {e}"
"                await asyncio.sleep(5)

    def __len__(self) -> int:
        return self.size()

    def __contains__(self, key: str) -> bool:
        return self.get(key) is not None

    def __repr__(self) -> str:
        return f"TTLCache(size={len(self)))
"}, max_size={self.max_size
"
"