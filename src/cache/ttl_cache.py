"""Lightweight TTL cache with sync and async helpers."""

import time
from dataclasses import dataclass, field
from datetime import timedelta
from pathlib import Path
from typing import Any, Optional, Iterable, Dict, Union


@dataclass
class CacheItem:
    """Simple cache entry storing value, creation time and ttl in seconds."""

    value: Any
    ttl: Optional[float] = None
    created_at: float = field(default_factory=time.time)

    def is_expired(self, current_time: Optional[float] = None) -> bool:
        if self.ttl is None:
            return False
        if current_time is None:
            current_time = time.time()
        return current_time >= self.created_at + self.ttl

    def remaining_ttl(self, current_time: Optional[float] = None) -> Optional[float]:
        if self.ttl is None:
            return None
        if current_time is None:
            current_time = time.time()
        remaining = self.created_at + self.ttl - current_time
        return max(0.0, remaining)


# Backwards compatibility alias expected by some imports
CacheEntry = CacheItem


class TTLCache:
    """Thread-safe TTL cache with convenience async wrappers."""

    def __init__(
        self,
        max_size: int = 1000,
        ttl: Optional[float | int | timedelta] = None,
        *,
        maxsize: Optional[int] = None,
    ) -> None:
        if maxsize is not None:
            max_size = maxsize

        self._max_size = max_size
        self._default_ttl = self._normalize_ttl(ttl)
        self._cache: Dict[str, CacheItem] = {}
        self._lock = threading.Lock()
        self.hits = 0
        self.misses = 0
        self.evictions = 0

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------
    @staticmethod
    def _normalize_ttl(value: Optional[float | int | timedelta]) -> Optional[float]:
        if value is None:
            return None
        if isinstance(value, timedelta):
            return max(0.0, value.total_seconds())
        return max(0.0, float(value))

    def _purge_expired(self, now: Optional[float] = None) -> None:
        if now is None:
            now = time.time()
        expired_keys = [
            key for key, item in self._cache.items() if item.is_expired(now)
        ]
        for key in expired_keys:
            del self._cache[key]
            self.evictions += 1

    def _evict_if_needed(self) -> None:
        if len(self._cache) < self._max_size:
            return
        # 驱逐最早写入的条目
        oldest_key = min(self._cache.items(), key=lambda entry: entry[1].created_at)[0]
        del self._cache[oldest_key]
        self.evictions += 1

    # ------------------------------------------------------------------
    # Public synchronous API
    # ------------------------------------------------------------------
    def get(self, key: str, default: Any = None) -> Any:
        with self._lock:
            self._purge_expired()
            item = self._cache.get(key)
            if item and not item.is_expired():
                self.hits += 1
                return item.value
            if item:
                # expired entry met during get counts as eviction and miss
                del self._cache[key]
                self.evictions += 1
            self.misses += 1
            return default

    def set(
        self,
        key: str,
        value: Any,
        ttl: Optional[float | int | timedelta] = None,
    ) -> bool:
        ttl_seconds = self._normalize_ttl(ttl) or self._default_ttl
        with self._lock:
            self._purge_expired()
            if key not in self._cache and len(self._cache) >= self._max_size:
                self._evict_if_needed()
            self._cache[key] = CacheItem(value=value, ttl=ttl_seconds)
        return True

    def delete(self, key: str) -> bool:
        with self._lock:
            if key in self._cache:
                del self._cache[key]
                return True
        return False

    def clear(self) -> None:
        with self._lock:
            self._cache.clear()
            self.hits = self.misses = self.evictions = 0

    def size(self) -> int:
        with self._lock:
            self._purge_expired()
            return len(self._cache)

    def keys(self) -> Iterable[str]:
        with self._lock:
            self._purge_expired()
            return list(self._cache.keys())

    def values(self) -> Iterable[Any]:
        with self._lock:
            self._purge_expired()
            return [item.value for item in self._cache.values()]

    def items(self) -> Iterable[tuple[str, Any]]:
        with self._lock:
            self._purge_expired()
            return [(key, item.value) for key, item in self._cache.items()]

    def set_many(
        self,
        mapping: Dict[str, Any],
        ttl: Optional[float | int | timedelta] = None,
    ) -> bool:
        for key, value in mapping.items():
            self.set(key, value, ttl=ttl)
        return True

    def get_many(self, keys: Iterable[str], default: Any = None) -> Dict[str, Any]:
        return {key: self.get(key, default) for key in keys}

    def save_to_file(self, path: str | Path) -> None:
        data = []
        with self._lock:
            self._purge_expired()
            for key, item in self._cache.items():
                data.append(
                    {
                        "key": key,
                        "value": item.value,
                        "ttl": item.ttl,
                        "created_at": item.created_at,
                    }
                )
        Path(path).write_text(json.dumps(data, default=str, ensure_ascii=False))

    def load_from_file(self, path: str | Path, *, merge: bool = False) -> None:
        file = Path(path)
        if not file.exists():
            return
        raw = json.loads(file.read_text())
        if not merge:
            self.clear()
        for entry in raw:
            self.set(
                entry["key"],
                entry["value"],
                ttl=entry.get("ttl"),
            )

    def get_stats(self) -> Dict[str, int]:
        return {"hits": self.hits, "misses": self.misses, "evictions": self.evictions}

    # ------------------------------------------------------------------
    # Async helpers (non-blocking wrappers)
    # ------------------------------------------------------------------
    async def get_async(self, key: str, default: Any = None) -> Any:
        return await asyncio.to_thread(self.get, key, default)

    async def set_async(
        self, key: str, value: Any, ttl: Optional[float | int | timedelta] = None
    ) -> bool:
        return await asyncio.to_thread(self.set, key, value, ttl)

    async def delete_async(self, key: str) -> bool:
        return await asyncio.to_thread(self.delete, key)

    async def clear_async(self) -> None:
        await asyncio.to_thread(self.clear)

    async def set_many_async(
        self,
        mapping: Dict[str, Any],
        ttl: Optional[float | int | timedelta] = None,
    ) -> bool:
        return await asyncio.to_thread(self.set_many, mapping, ttl)

    async def get_many_async(
        self, keys: Iterable[str], default: Any = None
    ) -> Dict[str, Any]:
        return await asyncio.to_thread(self.get_many, keys, default)

    # ------------------------------------------------------------------
    # Convenience dunder methods / properties
    # ------------------------------------------------------------------
    def __contains__(self, key: str) -> bool:
        return self.get(key) is not None

    @property
    def max_size(self) -> int:
        return self._max_size

    @property
    def default_ttl(self) -> Optional[float]:
        return self._default_ttl
