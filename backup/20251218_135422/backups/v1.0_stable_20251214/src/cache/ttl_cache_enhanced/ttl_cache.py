"""TTL缓存实现
TTL Cache Implementation.

提供带有生存时间的内存缓存功能。
Provides in-memory cache with time-to-live functionality.
"""

import logging
import threading
import time
from typing import Any

logger = logging.getLogger(__name__)


class CacheEntry:
    """缓存条目."""

    def __init__(self, value: Any, ttl: float | None = None):
        self.value = value
        self.created_at = time.time()
        self.ttl = ttl
        self.access_count = 0
        self.last_accessed = self.created_at

    def is_expired(self) -> bool:
        """检查是否过期."""
        if self.ttl is None:
            return False
        return time.time() - self.created_at > self.ttl

    def get_ttl_remaining(self) -> float | None:
        """获取剩余TTL."""
        if self.ttl is None:
            return None
        elapsed = time.time() - self.created_at
        remaining = self.ttl - elapsed
        return max(0, remaining)


class TTLCache:
    """带TTL的缓存."""

    def __init__(
        self,
        max_size: int = 1000,
        default_ttl: float | None = None,
        cleanup_interval: float = 60.0,
    ):
        """初始化TTL缓存.

        Args:
            max_size: 最大缓存大小
            default_ttl: 默认TTL（秒）
            cleanup_interval: 清理间隔（秒）
        """
        self.max_size = max_size
        self.default_ttl = default_ttl
        self.cleanup_interval = cleanup_interval
        self._cache: dict[str, CacheEntry] = {}
        self._lock = threading.RLock()
        self._cleanup_thread = None
        self._running = False

        # 统计信息
        self._hits = 0
        self._misses = 0
        self._sets = 0
        self._deletes = 0

        # 启动自动清理
        self.start_auto_cleanup()

    def get(self, key: str, default: Any = None) -> Any:
        """获取缓存值.

        Args:
            key: 缓存键
            default: 默认值

        Returns:
            缓存值或默认值
        """
        with self._lock:
            entry = self._cache.get(key)

            if entry is None:
                self._misses += 1
                return default

            if entry.is_expired():
                del self._cache[key]
                self._misses += 1
                return default

            entry.access_count += 1
            entry.last_accessed = time.time()
            self._hits += 1
            return entry.value

    def set(self, key: str, value: Any, ttl: float | None = None) -> None:
        """设置缓存值.

        Args:
            key: 缓存键
            value: 缓存值
            ttl: 生存时间（秒）
        """
        with self._lock:
            # 检查容量限制
            if len(self._cache) >= self.max_size and key not in self._cache:
                self._evict_lru()

            ttl = ttl or self.default_ttl
            entry = CacheEntry(value, ttl)
            self._cache[key] = entry
            self._sets += 1

    def delete(self, key: str) -> bool:
        """删除缓存项.

        Args:
            key: 缓存键

        Returns:
            是否删除成功
        """
        with self._lock:
            if key in self._cache:
                del self._cache[key]
                self._deletes += 1
                return True
            return False

    def clear(self) -> None:
        """清空缓存."""
        with self._lock:
            self._cache.clear()

    def pop(self, key: str, default: Any = None) -> Any:
        """弹出并删除缓存项.

        Args:
            key: 缓存键
            default: 默认值

        Returns:
            缓存值或默认值
        """
        with self._lock:
            value = self.get(key, default)
            self.delete(key)
            return value

    def keys(self) -> list[str]:
        """获取所有键."""
        with self._lock:
            return list(self._cache.keys())

    def values(self) -> list[Any]:
        """获取所有值."""
        with self._lock:
            return [entry.value for entry in self._cache.values()]

    def items(self) -> list[tuple[str, Any]]:
        """获取所有键值对."""
        with self._lock:
            return [(key, entry.value) for key, entry in self._cache.items()]

    def get_many(self, keys: list[str]) -> dict[str, Any]:
        """批量获取.

        Args:
            keys: 键列表

        Returns:
            键值对字典
        """
        result = {}
        for key in keys:
            value = self.get(key)
            if value is not None:
                result[key] = value
        return result

    def set_many(self, mapping: dict[str, Any], ttl: float | None = None) -> None:
        """批量设置.

        Args:
            mapping: 键值对字典
            ttl: 生存时间（秒）
        """
        for key, value in mapping.items():
            self.set(key, value, ttl)

    def delete_many(self, keys: list[str]) -> int:
        """批量删除.

        Args:
            keys: 键列表

        Returns:
            删除的数量
        """
        count = 0
        for key in keys:
            if self.delete(key):
                count += 1
        return count

    def increment(self, key: str, delta: int = 1, default: int = 0) -> int:
        """递增数值.

        Args:
            key: 缓存键
            delta: 递增量
            default: 默认值

        Returns:
            递增后的值
        """
        current = self.get(key, default)
        if not isinstance(current, int):
            current = default
        new_value = current + delta
        self.set(key, new_value)
        return new_value

    def touch(self, key: str, ttl: float | None = None) -> bool:
        """更新缓存项的TTL.

        Args:
            key: 缓存键
            ttl: 新的TTL（秒）

        Returns:
            是否更新成功
        """
        with self._lock:
            entry = self._cache.get(key)
            if entry is None:
                return False

            if ttl is not None:
                entry.ttl = ttl
            entry.created_at = time.time()
            return True

    def ttl(self, key: str) -> int | None:
        """获取剩余TTL.

        Args:
            key: 缓存键

        Returns:
            剩余TTL（秒）
        """
        with self._lock:
            entry = self._cache.get(key)
            if entry is None:
                return None

            remaining = entry.get_ttl_remaining()
            return int(remaining) if remaining is not None else None

    def size(self) -> int:
        """获取缓存大小."""
        with self._lock:
            return len(self._cache)

    def is_empty(self) -> bool:
        """检查缓存是否为空."""
        with self._lock:
            return len(self._cache) == 0

    def cleanup_expired(self) -> int:
        """清理过期项.

        Returns:
            清理的数量
        """
        with self._lock:
            expired_keys = [
                key for key, entry in self._cache.items() if entry.is_expired()
            ]

            for key in expired_keys:
                del self._cache[key]

            return len(expired_keys)

    def get_stats(self) -> dict[str, Any]:
        """获取统计信息."""
        with self._lock:
            total_requests = self._hits + self._misses
            hit_rate = self._hits / total_requests if total_requests > 0 else 0

            return {
                "hits": self._hits,
                "misses": self._misses,
                "sets": self._sets,
                "deletes": self._deletes,
                "hit_rate": hit_rate,
                "size": len(self._cache),
                "max_size": self.max_size,
            }

    def reset_stats(self) -> None:
        """重置统计信息."""
        with self._lock:
            self._hits = 0
            self._misses = 0
            self._sets = 0
            self._deletes = 0

    def _evict_lru(self) -> None:
        """淘汰最近最少使用的项."""
        if not self._cache:
            return

        lru_key = min(self._cache.keys(), key=lambda k: self._cache[k].last_accessed)
        del self._cache[lru_key]

    def _cleanup_worker(self) -> None:
        """清理工作线程."""
        while self._running:
            try:
                self.cleanup_expired()
                time.sleep(self.cleanup_interval)
            except Exception as e:
                logger.error(f"缓存清理错误: {e}")

    def start_auto_cleanup(self) -> None:
        """启动自动清理."""
        if self._cleanup_thread is None or not self._cleanup_thread.is_alive():
            self._running = True
            self._cleanup_thread = threading.Thread(
                target=self._cleanup_worker, daemon=True
            )
            self._cleanup_thread.start()

    def stop_auto_cleanup(self) -> None:
        """停止自动清理."""
        self._running = False
        if self._cleanup_thread and self._cleanup_thread.is_alive():
            self._cleanup_thread.join(timeout=1.0)

    def __len__(self) -> int:
        return self.size()

    def __contains__(self, key: str) -> bool:
        return self.get(key) is not None

    def __repr__(self) -> str:
        stats = self.get_stats()
        return f"TTLCache(size={stats['size']}, max_size={self.max_size}, hit_rate={stats['hit_rate']:.2f})"


# 向后兼容别名
Ttl_Cache = TTLCache
