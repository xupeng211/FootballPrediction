"""
UX优化模块 - 智能缓存管理器
实现多层缓存架构、智能预加载和自适应缓存策略
"""

import asyncio
import json
import logging
import time
from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import Enum
from typing import Any

from src.cache.unified_cache import UnifiedCacheManager

logger = logging.getLogger(__name__)


class CacheLevel(Enum):
    """缓存级别"""

    L1_MEMORY = "L1_MEMORY"  # 内存缓存(最快)
    L2_REDIS = "L2_REDIS"  # Redis缓存(快)
    L3_DATABASE = "L3_DATABASE"  # 数据库缓存(慢)


class CacheStrategy(Enum):
    """缓存策略"""

    LRU = "LRU"  # 最近最少使用
    LFU = "LFU"  # 最少使用频率
    TTL = "TTL"  # 时间到期
    ADAPTIVE = "ADAPTIVE"  # 自适应策略


@dataclass
class CacheConfig:
    """缓存配置"""

    max_memory_size: int = 100 * 1024 * 1024  # 100MB
    max_redis_size: int = 1000  # 1000个键
    default_ttl: int = 300  # 5分钟
    max_ttl: int = 3600  # 1小时
    min_ttl: int = 60  # 1分钟
    compression_threshold: int = 1024  # 1KB
    enable_compression: bool = True
    enable_warmup: bool = True
    enable_preloading: bool = True


@dataclass
class CacheStats:
    """缓存统计"""

    hits: int = 0
    misses: int = 0
    sets: int = 0
    deletes: int = 0
    evictions: int = 0
    size_bytes: int = 0
    item_count: int = 0
    last_access: datetime | None = None

    @property
    def hit_rate(self) -> float:
        """命中率"""
        total = self.hits + self.misses
        return (self.hits / total * 100) if total > 0 else 0.0


@dataclass
class CacheItem:
    """缓存项"""

    key: str
    value: Any
    ttl: int
    created_at: datetime
    last_accessed: datetime
    access_count: int = 0
    size_bytes: int = 0
    level: CacheLevel = CacheLevel.L1_MEMORY
    compressed: bool = False

    def is_expired(self) -> bool:
        """检查是否过期"""
        return (datetime.now() - self.created_at).total_seconds() > self.ttl

    def touch(self) -> None:
        """更新访问时间"""
        self.last_accessed = datetime.now()
        self.access_count += 1


class IntelligentCacheManager:
    """智能缓存管理器"""

    def __init__(self, cache: UnifiedCacheManager, config: CacheConfig | None = None):
        self.cache = cache
        self.config = config or CacheConfig()

        # 多级缓存存储
        self.l1_cache: dict[str, CacheItem] = {}  # 内存缓存
        self.l2_cache = cache  # Redis缓存
        self.access_patterns: dict[str, list[datetime]] = defaultdict(list)
        self.hot_keys: set[str] = set()

        # 统计信息
        self.stats = {
            CacheLevel.L1_MEMORY: CacheStats(),
            CacheLevel.L2_REDIS: CacheStats(),
            "total": CacheStats(),
        }

        # 预加载任务
        self.preload_tasks: dict[str, asyncio.Task] = {}
        self.warmup_completed = False

        # 启动后台任务
        self._start_background_tasks()

    async def get(self, key: str, default: Any = None) -> Any:
        """获取缓存值"""
        start_time = time.time()

        try:
            # L1缓存查找
            item = self.l1_cache.get(key)
            if item and not item.is_expired():
                item.touch()
                self._record_hit(CacheLevel.L1_MEMORY)
                logger.debug(f"L1 cache hit: {key}")
                return item.value

            # L2缓存查找
            cached_value = await self.cache.get(key)
            if cached_value is not None:
                # 提升到L1缓存
                await self._promote_to_l1(key, cached_value)
                self._record_hit(CacheLevel.L2_REDIS)
                logger.debug(f"L2 cache hit: {key}")
                return cached_value

            # 缓存未命中
            self._record_miss()
            logger.debug(f"Cache miss: {key}")

            # 触发预加载
            await self._trigger_preload(key)

            return default

        except Exception as e:
            logger.error(f"Cache get error for key {key}: {e}")
            self._record_miss()
            return default
        finally:
            # 记录访问模式
            await self._record_access_pattern(key)
            response_time = (time.time() - start_time) * 1000
            logger.debug(f"Cache get took {response_time:.1f}ms for key: {key}")

    async def set(self, key: str, value: Any, ttl: int | None = None) -> bool:
        """设置缓存值"""
        try:
            ttl = ttl or self.config.default_ttl
            ttl = min(max(ttl, self.config.min_ttl), self.config.max_ttl)

            # 序列化和压缩
            serialized_value = await self._serialize_value(value)
            compressed_value = await self._compress_if_needed(serialized_value)
            compressed = len(compressed_value) < len(serialized_value)

            # 创建缓存项
            item = CacheItem(
                key=key,
                value=value,
                ttl=ttl,
                created_at=datetime.now(),
                last_accessed=datetime.now(),
                size_bytes=len(compressed_value if compressed else serialized_value),
                compressed=compressed,
            )

            # L1缓存存储
            await self._store_in_l1(item)

            # L2缓存存储
            storage_value = compressed_value if compressed else serialized_value
            success = await self.cache.set(key, storage_value, ttl=ttl)

            if success:
                self._record_set()
                logger.debug(f"Cache set successful: {key} (ttl: {ttl}s)")
            else:
                logger.warning(f"Cache set failed: {key}")

            return success

        except Exception as e:
            logger.error(f"Cache set error for key {key}: {e}")
            return False

    async def delete(self, key: str) -> bool:
        """删除缓存值"""
        try:
            # 从L1缓存删除
            self.l1_cache.pop(key, None)

            # 从L2缓存删除
            success = await self.cache.delete(key)

            if success:
                self._record_delete()
                logger.debug(f"Cache delete successful: {key}")

            # 取消预加载任务
            if key in self.preload_tasks:
                self.preload_tasks[key].cancel()
                del self.preload_tasks[key]

            return success

        except Exception as e:
            logger.error(f"Cache delete error for key {key}: {e}")
            return False

    async def exists(self, key: str) -> bool:
        """检查缓存是否存在"""
        # L1缓存检查
        if key in self.l1_cache:
            item = self.l1_cache[key]
            if not item.is_expired():
                return True
            else:
                del self.l1_cache[key]

        # L2缓存检查
        try:
            return await self.cache.exists(key)
        except Exception as e:
            logger.error(f"Cache exists check error for key {key}: {e}")
            return False

    async def clear(self, pattern: str | None = None) -> int:
        """清空缓存"""
        cleared_count = 0

        try:
            if pattern:
                # 清空匹配模式的缓存
                keys_to_delete = [key for key in self.l1_cache.keys() if pattern in key]

                for key in keys_to_delete:
                    del self.l1_cache[key]
                    await self.cache.delete(key)
                    cleared_count += 1
            else:
                # 清空所有缓存
                cleared_count = len(self.l1_cache)
                self.l1_cache.clear()
                await self.cache.clear()

            logger.info(f"Cleared {cleared_count} cache items")
            return cleared_count

        except Exception as e:
            logger.error(f"Cache clear error: {e}")
            return 0

    async def _promote_to_l1(self, key: str, value: Any) -> None:
        """提升到L1缓存"""
        try:
            ttl = self.config.default_ttl
            serialized_value = await self._serialize_value(value)
            compressed_value = await self._compress_if_needed(serialized_value)
            compressed = len(compressed_value) < len(serialized_value)

            item = CacheItem(
                key=key,
                value=value,
                ttl=ttl,
                created_at=datetime.now(),
                last_accessed=datetime.now(),
                size_bytes=len(compressed_value if compressed else serialized_value),
                compressed=compressed,
            )

            await self._store_in_l1(item)

        except Exception as e:
            logger.error(f"L1 promotion error for key {key}: {e}")

    async def _store_in_l1(self, item: CacheItem) -> None:
        """存储到L1缓存"""
        # 检查容量限制
        if await self._should_evict_from_l1():
            await self._evict_from_l1()

        self.l1_cache[item.key] = item
        logger.debug(f"Stored in L1 cache: {item.key}")

    async def _should_evict_from_l1(self) -> bool:
        """检查是否需要从L1缓存淘汰"""
        total_size = sum(item.size_bytes for item in self.l1_cache.values())
        return total_size > self.config.max_memory_size or len(self.l1_cache) > 1000

    async def _evict_from_l1(self) -> None:
        """从L1缓存淘汰"""
        if not self.l1_cache:
            return

        # 使用LRU策略淘汰
        oldest_key = min(
            self.l1_cache.keys(), key=lambda k: self.l1_cache[k].last_accessed
        )

        evicted_item = self.l1_cache.pop(oldest_key)
        self.stats[CacheLevel.L1_MEMORY].evictions += 1

        logger.debug(f"Evicted from L1 cache: {oldest_key}")

        # 将被淘汰的数据存储到L2缓存
        try:
            await self.cache.set(oldest_key, evicted_item.value, ttl=evicted_item.ttl)
        except Exception as e:
            logger.warning(f"Failed to store evicted item to L2: {e}")

    async def _serialize_value(self, value: Any) -> bytes:
        """序列化值"""
        try:
            if isinstance(value, (str, int, float, bool)):
                return str(value).encode("utf-8")
            else:
                return json.dumps(value, default=str).encode("utf-8")
        except Exception as e:
            logger.error(f"Value serialization error: {e}")
            return str(value).encode("utf-8")

    async def _compress_if_needed(self, data: bytes) -> bytes:
        """根据需要压缩数据"""
        if not self.config.enable_compression:
            return data

        if len(data) < self.config.compression_threshold:
            return data

        try:
            import zlib

            compressed = zlib.compress(data)
            # 只有压缩有效时才使用压缩数据
            return compressed if len(compressed) < len(data) else data
        except Exception as e:
            logger.warning(f"Compression error: {e}")
            return data

    async def _record_access_pattern(self, key: str) -> None:
        """记录访问模式"""
        now = datetime.now()
        self.access_patterns[key].append(now)

        # 只保留最近24小时的访问记录
        cutoff = now - timedelta(hours=24)
        self.access_patterns[key] = [
            access_time
            for access_time in self.access_patterns[key]
            if access_time > cutoff
        ]

        # 更新热键集合
        if len(self.access_patterns[key]) >= 10:  # 24小时内访问10次以上
            self.hot_keys.add(key)
        elif key in self.hot_keys and len(self.access_patterns[key]) < 5:
            self.hot_keys.discard(key)

    async def _trigger_preload(self, key: str) -> None:
        """触发预加载"""
        if not self.config.enable_preloading:
            return

        # 检查是否需要预加载相关键
        related_keys = await self._get_related_keys(key)
        for related_key in related_keys:
            if related_key not in self.preload_tasks:
                task = asyncio.create_task(self._preload_key(related_key))
                self.preload_tasks[related_key] = task

    async def _get_related_keys(self, key: str) -> list[str]:
        """获取相关键"""
        related_keys = []

        # 根据键的模式推断相关键
        if ":id:" in key:
            # 如果是具体ID，预加载列表键
            base_key = key.split(":id:")[0]
            related_keys.append(f"{base_key}:list")

        if ":list" in key:
            # 如果是列表，预加载前几个具体项
            try:
                list_data = await self.cache.get(key)
                if isinstance(list_data, list) and list_data:
                    for i, item in enumerate(list_data[:5]):  # 预加载前5项
                        if hasattr(item, "id"):
                            related_keys.append(
                                f"{key.replace(':list', ':id:{item.id}')}"
                            )

            except Exception as e:
                logger.warning(f"Failed to get related keys for {key}: {e}")

        return related_keys

    async def _preload_key(self, key: str) -> None:
        """预加载键"""
        try:
            await asyncio.sleep(0.1)  # 小延迟，避免阻塞

            if not await self.exists(key):
                # 这里应该从数据源加载并缓存
                logger.debug(f"Preloading key: {key}")
                # 实际实现中应该调用相应的数据加载逻辑

        except Exception as e:
            logger.warning(f"Preload error for key {key}: {e}")
        finally:
            # 清理任务记录
            self.preload_tasks.pop(key, None)

    async def warmup_cache(self) -> None:
        """预热缓存"""
        if not self.config.enable_warmup or self.warmup_completed:
            return

        try:
            logger.info("Starting cache warmup")

            # 预加载常用数据
            warmup_keys = [
                "matches:upcoming",
                "matches:live",
                "predictions:popular",
                "teams:active",
                "leagues:current",
                "user:preferences:default",
            ]

            tasks = []
            for key in warmup_keys:
                task = asyncio.create_task(self._preload_key(key))
                tasks.append(task)

            # 等待所有预热任务完成
            await asyncio.gather(*tasks, return_exceptions=True)

            self.warmup_completed = True
            logger.info("Cache warmup completed")

        except Exception as e:
            logger.error(f"Cache warmup error: {e}")

    def _record_hit(self, level: CacheLevel) -> None:
        """记录缓存命中"""
        self.stats[level].hits += 1
        self.stats["total"].hits += 1
        self.stats["total"].last_access = datetime.now()

    def _record_miss(self) -> None:
        """记录缓存未命中"""
        self.stats[CacheLevel.L1_MEMORY].misses += 1
        self.stats[CacheLevel.L2_REDIS].misses += 1
        self.stats["total"].misses += 1

    def _record_set(self) -> None:
        """记录缓存设置"""
        self.stats[CacheLevel.L1_MEMORY].sets += 1
        self.stats[CacheLevel.L2_REDIS].sets += 1
        self.stats["total"].sets += 1

    def _record_delete(self) -> None:
        """记录缓存删除"""
        self.stats[CacheLevel.L1_MEMORY].deletes += 1
        self.stats[CacheLevel.L2_REDIS].deletes += 1
        self.stats["total"].deletes += 1

    def _start_background_tasks(self) -> None:
        """启动后台任务"""
        asyncio.create_task(self._cleanup_expired_items())
        asyncio.create_task(self._analyze_access_patterns())

    async def _cleanup_expired_items(self) -> None:
        """清理过期项"""
        while True:
            try:
                await asyncio.sleep(60)  # 每分钟清理一次

                # 清理L1缓存过期项
                expired_keys = [
                    key for key, item in self.l1_cache.items() if item.is_expired()
                ]

                for key in expired_keys:
                    del self.l1_cache[key]
                    logger.debug(f"Cleaned up expired L1 item: {key}")

                # 更新统计信息
                self.stats[CacheLevel.L1_MEMORY].item_count = len(self.l1_cache)
                self.stats[CacheLevel.L1_MEMORY].size_bytes = sum(
                    item.size_bytes for item in self.l1_cache.values()
                )

            except Exception as e:
                logger.error(f"Cleanup task error: {e}")

    async def _analyze_access_patterns(self) -> None:
        """分析访问模式"""
        while True:
            try:
                await asyncio.sleep(300)  # 每5分钟分析一次

                # 分析访问频率，调整缓存策略
                for key, access_times in self.access_patterns.items():
                    if len(access_times) >= 20:  # 高频访问键
                        # 延长TTL
                        if key in self.l1_cache:
                            self.l1_cache[key].ttl = min(
                                self.l1_cache[key].ttl * 1.5, self.config.max_ttl
                            )

            except Exception as e:
                logger.error(f"Access pattern analysis error: {e}")

    def get_cache_stats(self) -> dict[str, Any]:
        """获取缓存统计信息"""
        stats = {}

        for level, cache_stats in self.stats.items():
            if isinstance(level, CacheLevel):
                stats[level.value] = {
                    "hits": cache_stats.hits,
                    "misses": cache_stats.misses,
                    "sets": cache_stats.sets,
                    "deletes": cache_stats.deletes,
                    "evictions": cache_stats.evictions,
                    "size_bytes": cache_stats.size_bytes,
                    "item_count": cache_stats.item_count,
                    "hit_rate": cache_stats.hit_rate,
                    "last_access": (
                        cache_stats.last_access.isoformat()
                        if cache_stats.last_access
                        else None
                    ),
                }

        stats["total"] = {
            "hits": self.stats["total"].hits,
            "misses": self.stats["total"].misses,
            "hit_rate": self.stats["total"].hit_rate,
            "l1_size": len(self.l1_cache),
            "hot_keys_count": len(self.hot_keys),
            "preload_tasks_count": len(self.preload_tasks),
            "warmup_completed": self.warmup_completed,
        }

        return stats

    def get_hot_keys(self) -> list[str]:
        """获取热键列表"""
        return list(self.hot_keys)

    def get_access_patterns(self) -> dict[str, dict[str, Any]]:
        """获取访问模式"""
        patterns = {}
        for key, access_times in self.access_patterns.items():
            if access_times:
                patterns[key] = {
                    "access_count": len(access_times),
                    "last_access": access_times[-1].isoformat(),
                    "first_access": access_times[0].isoformat(),
                    "frequency": len(access_times) / 24,  # 每小时访问次数
                }

        return patterns


# 全局缓存管理器实例
_cache_manager: IntelligentCacheManager | None = None


def get_cache_manager() -> IntelligentCacheManager:
    """获取全局缓存管理器实例"""
    global _cache_manager
    if _cache_manager is None:
        raise RuntimeError("Cache manager not initialized")
    return _cache_manager


def initialize_cache_manager(
    cache: UnifiedCacheManager, config: CacheConfig | None = None
) -> IntelligentCacheManager:
    """初始化全局缓存管理器"""
    global _cache_manager
    _cache_manager = IntelligentCacheManager(cache, config)
    return _cache_manager
