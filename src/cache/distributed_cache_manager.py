"""分布式缓存管理器
Distributed Cache Manager.

提供企业级分布式缓存解决方案，支持多级缓存、智能路由、负载均衡和故障转移。
"""

import asyncio
import hashlib
import json
import logging
import random
import threading
import time
from abc import ABC, abstractmethod
from collections import defaultdict
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any

from .redis_cluster_manager import RedisClusterManager, get_redis_cluster_manager

logger = logging.getLogger(__name__)


class CacheLevel(Enum):
    """缓存级别."""

    L1_MEMORY = "l1_memory"  # L1: 内存缓存（最快）
    L2_REDIS = "l2_redis"  # L2: Redis缓存（快）
    L3_DATABASE = "l3_database"  # L3: 数据库缓存（慢）
    L4_EXTERNAL = "l4_external"  # L4: 外部缓存（如CDN）


class CacheEvictionPolicy(Enum):
    """缓存淘汰策略."""

    LRU = "lru"  # 最近最少使用
    LFU = "lfu"  # 最少使用频率
    FIFO = "fifo"  # 先进先出
    TTL = "ttl"  # 基于TTL
    ADAPTIVE = "adaptive"  # 自适应策略


class DistributionStrategy(Enum):
    """分发策略."""

    CONSISTENT_HASH = "consistent_hash"  # 一致性哈希
    ROUND_ROBIN = "round_robin"  # 轮询
    WEIGHTED_RANDOM = "weighted_random"  # 加权随机
    AFFINITY_BASED = "affinity_based"  # 亲和性基于


@dataclass
class CacheConfig:
    """缓存配置."""

    max_size: int = 10000
    ttl: int | None = 3600
    eviction_policy: CacheEvictionPolicy = CacheEvictionPolicy.LRU
    enable_compression: bool = False
    enable_serialization: bool = True
    enable_metrics: bool = True


@dataclass
class CacheEntry:
    """缓存条目."""

    key: str
    value: Any
    level: CacheLevel
    ttl: int | None = None
    created_at: datetime = field(default_factory=datetime.utcnow)
    accessed_at: datetime = field(default_factory=datetime.utcnow)
    access_count: int = 0
    size: int = 0
    checksum: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        if not self.checksum:
            self.checksum = self._calculate_checksum()
        if self.size == 0:
            self.size = self._calculate_size()

    def _calculate_checksum(self) -> str:
        """计算校验和."""
        data = f"{self.key}{self.value}{self.level}{self.created_at}"
        return hashlib.md5(data.encode(), usedforsecurity=False).hexdigest()

    def _calculate_size(self) -> int:
        """计算条目大小."""
        try:
            if self.enable_serialization:
                return len(json.dumps(self.value, default=str))
            else:
                return len(str(self.value))
        except Exception:
            return len(str(self.value))

    def is_expired(self) -> bool:
        """检查是否过期."""
        if self.ttl:
            return (datetime.utcnow() - self.created_at).total_seconds() > self.ttl
        return False

    def is_valid(self) -> bool:
        """检查条目有效性."""
        return self.checksum == self._calculate_checksum() and not self.is_expired()

    def access(self) -> Any:
        """访问缓存条目."""
        self.accessed_at = datetime.utcnow()
        self.access_count += 1
        return self.value


class MemoryCache:
    """内存缓存实现."""

    def __init__(self, config: CacheConfig):
        self.config = config
        self.cache: dict[str, CacheEntry] = {}
        self.access_order: list[str] = []  # LRU使用
        self.frequency: dict[str, int] = defaultdict(int)  # LFU使用
        self.lock = threading.RLock()
        self.metrics = {
            "hits": 0,
            "misses": 0,
            "sets": 0,
            "evictions": 0,
            "size": 0,
            "memory_usage": 0,
        }

    def get(self, key: str) -> Any | None:
        """获取缓存值."""
        with self.lock:
            if key in self.cache:
                entry = self.cache[key]
                if entry.is_valid():
                    self._update_access_info(key)
                    self.metrics["hits"] += 1
                    return entry.access()
                else:
                    self._remove_entry(key)
                    self.metrics["misses"] += 1
            else:
                self.metrics["misses"] += 1
            return None

    def set(self, key: str, value: Any, ttl: int | None = None) -> bool:
        """设置缓存值."""
        with self.lock:
            try:
                # 检查大小限制
                if len(self.cache) >= self.config.max_size:
                    self._evict_entries()

                entry = CacheEntry(
                    key=key,
                    value=value,
                    level=CacheLevel.L1_MEMORY,
                    ttl=ttl or self.config.ttl,
                )

                self.cache[key] = entry
                self._update_access_info(key)
                self.metrics["sets"] += 1
                self.metrics["size"] = len(self.cache)
                self.metrics["memory_usage"] = sum(
                    entry.size for entry in self.cache.values()
                )
                return True

            except Exception as e:
                logger.error(f"Error setting cache entry: {e}")
                return False

    def delete(self, key: str) -> bool:
        """删除缓存值."""
        with self.lock:
            if key in self.cache:
                self._remove_entry(key)
                return True
            return False

    def clear(self):
        """清空缓存."""
        with self.lock:
            self.cache.clear()
            self.access_order.clear()
            self.frequency.clear()
            self.metrics["size"] = 0
            self.metrics["memory_usage"] = 0

    def _update_access_info(self, key: str):
        """更新访问信息."""
        # 更新LRU顺序
        if key in self.access_order:
            self.access_order.remove(key)
        self.access_order.append(key)

        # 更新LFU频率
        self.frequency[key] += 1

    def _remove_entry(self, key: str):
        """移除缓存条目."""
        if key in self.cache:
            del self.cache[key]
            if key in self.access_order:
                self.access_order.remove(key)
            if key in self.frequency:
                del self.frequency[key]

            self.metrics["size"] = len(self.cache)
            self.metrics["memory_usage"] = sum(
                entry.size for entry in self.cache.values()
            )

    def _evict_entries(self, count: int = 1):
        """淘汰缓存条目."""
        evicted = 0
        while evicted < count and self.cache:
            if self.config.eviction_policy == CacheEvictionPolicy.LRU:
                key = (
                    self.access_order[0]
                    if self.access_order
                    else next(iter(self.cache))
                )
            elif self.config.eviction_policy == CacheEvictionPolicy.LFU:
                key = min(self.frequency.keys(), key=lambda k: self.frequency[k])
            elif self.config.eviction_policy == CacheEvictionPolicy.FIFO:
                key = next(iter(self.cache))
            else:  # TTL or Adaptive
                # 找到最早的条目
                key = min(self.cache.keys(), key=lambda k: self.cache[k].created_at)

            self._remove_entry(key)
            evicted += 1
            self.metrics["evictions"] += 1

    def get_metrics(self) -> dict[str, Any]:
        """获取缓存指标."""
        total_requests = self.metrics["hits"] + self.metrics["misses"]
        hit_rate = (
            (self.metrics["hits"] / total_requests * 100) if total_requests > 0 else 0
        )

        return {
            **self.metrics,
            "hit_rate": round(hit_rate, 2),
            "capacity_usage": round(len(self.cache) / self.config.max_size * 100, 2),
        }


class CacheBackend(ABC):
    """缓存后端抽象类."""

    @abstractmethod
    async def get(self, key: str) -> Any | None:
        """获取缓存值."""
        pass

    @abstractmethod
    async def set(self, key: str, value: Any, ttl: int | None = None) -> bool:
        """设置缓存值."""
        pass

    @abstractmethod
    async def delete(self, key: str) -> bool:
        """删除缓存值."""
        pass

    @abstractmethod
    async def health_check(self) -> bool:
        """健康检查."""
        pass


class RedisCacheBackend(CacheBackend):
    """Redis缓存后端."""

    def __init__(self, redis_manager: RedisClusterManager | None = None):
        self.redis_manager = redis_manager or get_redis_cluster_manager()
        self.metrics = {"hits": 0, "misses": 0, "sets": 0, "errors": 0}

    async def get(self, key: str) -> Any | None:
        """获取缓存值."""
        try:
            if not self.redis_manager:
                return None

            value = await self.redis_manager.get(key)
            if value is not None:
                self.metrics["hits"] += 1
                return value
            else:
                self.metrics["misses"] += 1
                return None

        except Exception as e:
            logger.error(f"Redis get error: {e}")
            self.metrics["errors"] += 1
            return None

    async def set(self, key: str, value: Any, ttl: int | None = None) -> bool:
        """设置缓存值."""
        try:
            if not self.redis_manager:
                return False

            result = await self.redis_manager.set(key, value, ttl)
            if result:
                self.metrics["sets"] += 1
            return result

        except Exception as e:
            logger.error(f"Redis set error: {e}")
            self.metrics["errors"] += 1
            return False

    async def delete(self, key: str) -> bool:
        """删除缓存值."""
        try:
            if not self.redis_manager:
                return False

            return await self.redis_manager.delete(key)

        except Exception as e:
            logger.error(f"Redis delete error: {e}")
            self.metrics["errors"] += 1
            return False

    async def health_check(self) -> bool:
        """健康检查."""
        try:
            if not self.redis_manager:
                return False

            status = await self.redis_manager.get_cluster_status()
            return status["cluster_info"]["healthy_nodes"] > 0

        except Exception as e:
            logger.error(f"Redis health check error: {e}")
            return False


class DistributedCacheManager:
    """分布式缓存管理器."""

    def __init__(self, config: dict[str, Any] | None = None):
        self.config = config or {}
        self.cache_levels: dict[CacheLevel, Any] = {}
        self.backends: dict[CacheLevel, CacheBackend] = {}
        self.distribution_strategy = DistributionStrategy(
            self.config.get("distribution_strategy", "consistent_hash")
        )
        self.enable_write_through = self.config.get("enable_write_through", True)
        self.enable_write_back = self.config.get("enable_write_back", False)
        self.cache_coherency_enabled = self.config.get("cache_coherency", True)

        # 初始化各级缓存
        self._initialize_cache_levels()

        # 负载均衡器
        self.load_balancer = LoadBalancer(self.distribution_strategy)

        # 缓存协调器（用于多级缓存一致性）
        self.coordinator = CacheCoordinator(self)

        # 性能监控
        self.performance_monitor = CachePerformanceMonitor()

        # 事件系统
        self.event_handlers: dict[str, list[Callable]] = defaultdict(list)

    def _initialize_cache_levels(self):
        """初始化缓存级别."""
        # L1: 内存缓存
        l1_config = CacheConfig(
            max_size=self.config.get("l1_max_size", 1000),
            ttl=self.config.get("l1_ttl", 300),  # 5分钟
            eviction_policy=CacheEvictionPolicy.LRU,
        )
        self.cache_levels[CacheLevel.L1_MEMORY] = MemoryCache(l1_config)

        # L2: Redis缓存
        if self.config.get("enable_redis", True):
            self.backends[CacheLevel.L2_REDIS] = RedisCacheBackend()

        # L3: 数据库缓存（可扩展）
        # L4: 外部缓存（可扩展）

    async def get(
        self,
        key: str,
        level: CacheLevel | None = None,
        session_id: str | None = None,
    ) -> Any | None:
        """获取缓存值（多级缓存查找）."""
        start_time = time.time()

        try:
            # 指定级别查找
            if level:
                return await self._get_from_level(key, level, session_id)

            # 多级缓存查找（L1 -> L2 -> L3 -> ...）
            for cache_level in [CacheLevel.L1_MEMORY, CacheLevel.L2_REDIS]:
                value = await self._get_from_level(key, cache_level, session_id)
                if value is not None:
                    # 回填到更高级别的缓存
                    await self._populate_higher_levels(key, value, cache_level)

                    # 记录性能指标
                    response_time = time.time() - start_time
                    await self.performance_monitor.record_hit(
                        cache_level, response_time
                    )

                    return value

            # 记录未命中
            await self.performance_monitor.record_miss(time.time() - start_time)
            return None

        except Exception as e:
            logger.error(f"Error getting cache key {key}: {e}")
            await self.performance_monitor.record_error()
            return None

    async def set(
        self,
        key: str,
        value: Any,
        ttl: int | None = None,
        level: CacheLevel | None = None,
        session_id: str | None = None,
    ) -> bool:
        """设置缓存值（多级缓存写入）."""
        start_time = time.time()

        try:
            success = True

            # 指定级别写入
            if level:
                result = await self._set_to_level(key, value, ttl, level, session_id)
                await self.performance_monitor.record_write(
                    level, time.time() - start_time
                )
                return result

            # 多级缓存写入策略
            if self.enable_write_through:
                # Write-through: 同时写入所有级别
                for cache_level in [CacheLevel.L1_MEMORY, CacheLevel.L2_REDIS]:
                    result = await self._set_to_level(
                        key, value, ttl, cache_level, session_id
                    )
                    success = success and result

            elif self.enable_write_back:
                # Write-back: 只写入L1，异步写入其他级别
                await self._set_to_level(
                    key, value, ttl, CacheLevel.L1_MEMORY, session_id
                )
                asyncio.create_task(self._async_write_back(key, value, ttl, session_id))

            else:
                # Write-behind: 只写入L1
                await self._set_to_level(
                    key, value, ttl, CacheLevel.L1_MEMORY, session_id
                )

            # 缓存一致性处理
            if self.cache_coherency_enabled:
                await self.coordinator.notify_write(key, value)

            # 触发事件
            await self._trigger_event("cache_set", {"key": key, "level": level})

            await self.performance_monitor.record_write(
                level or CacheLevel.L1_MEMORY, time.time() - start_time
            )
            return success

        except Exception as e:
            logger.error(f"Error setting cache key {key}: {e}")
            await self.performance_monitor.record_error()
            return False

    async def delete(self, key: str, propagate: bool = True) -> bool:
        """删除缓存值（从所有级别删除）."""
        try:
            success = True

            # 从所有缓存级别删除
            for cache_level in [CacheLevel.L1_MEMORY, CacheLevel.L2_REDIS]:
                result = await self._delete_from_level(key, cache_level)
                success = success and result

            # 缓存一致性处理
            if propagate and self.cache_coherency_enabled:
                await self.coordinator.notify_invalidation(key)

            # 触发事件
            await self._trigger_event("cache_delete", {"key": key})

            return success

        except Exception as e:
            logger.error(f"Error deleting cache key {key}: {e}")
            return False

    async def _get_from_level(
        self, key: str, level: CacheLevel, session_id: str | None = None
    ) -> Any | None:
        """从特定缓存级别获取值."""
        if level == CacheLevel.L1_MEMORY:
            return self.cache_levels[level].get(key)
        elif level in self.backends:
            return await self.backends[level].get(key)
        return None

    async def _set_to_level(
        self,
        key: str,
        value: Any,
        ttl: int | None,
        level: CacheLevel,
        session_id: str | None = None,
    ) -> bool:
        """向特定缓存级别设置值."""
        if level == CacheLevel.L1_MEMORY:
            return self.cache_levels[level].set(key, value, ttl)
        elif level in self.backends:
            return await self.backends[level].set(key, value, ttl)
        return False

    async def _delete_from_level(self, key: str, level: CacheLevel) -> bool:
        """从特定缓存级别删除值."""
        if level == CacheLevel.L1_MEMORY:
            return self.cache_levels[level].delete(key)
        elif level in self.backends:
            return await self.backends[level].delete(key)
        return False

    async def _populate_higher_levels(
        self, key: str, value: Any, source_level: CacheLevel
    ):
        """回填到更高级别的缓存."""
        # 如果是从L2获取的，回填到L1
        if source_level == CacheLevel.L2_REDIS:
            await self._set_to_level(key, value, None, CacheLevel.L1_MEMORY)

    async def _async_write_back(
        self, key: str, value: Any, ttl: int | None, session_id: str | None = None
    ):
        """异步回写."""
        try:
            await asyncio.sleep(0.1)  # 短暂延迟
            await self._set_to_level(key, value, ttl, CacheLevel.L2_REDIS, session_id)
        except Exception as e:
            logger.error(f"Async write-back failed for key {key}: {e}")

    async def _trigger_event(self, event_name: str, data: dict[str, Any]):
        """触发缓存事件."""
        if event_name in self.event_handlers:
            for handler in self.event_handlers[event_name]:
                try:
                    if asyncio.iscoroutinefunction(handler):
                        await handler(data)
                    else:
                        handler(data)
                except Exception as e:
                    logger.error(f"Error in event handler for {event_name}: {e}")

    def add_event_handler(self, event_name: str, handler: Callable):
        """添加事件处理器."""
        self.event_handlers[event_name].append(handler)

    async def invalidate_pattern(self, pattern: str) -> int:
        """按模式失效缓存."""
        count = 0
        try:
            # L1缓存模式失效
            l1_cache = self.cache_levels[CacheLevel.L1_MEMORY]
            keys_to_remove = []
            for key in l1_cache.cache.keys():
                if pattern in key:
                    keys_to_remove.append(key)

            for key in keys_to_remove:
                if l1_cache.delete(key):
                    count += 1

            # L2缓存模式失效（如果支持）
            if CacheLevel.L2_REDIS in self.backends:
                # 这里可以实现Redis模式删除
                pass

            logger.info(
                f"Invalidated {count} cache entries matching pattern: {pattern}"
            )
            return count

        except Exception as e:
            logger.error(f"Error invalidating cache pattern {pattern}: {e}")
            return 0

    async def warm_cache(self, keys: list[str], data_loader: Callable[[str], Any]):
        """缓存预热."""
        warmed_count = 0

        for key in keys:
            try:
                # 检查是否已存在
                if await self.get(key) is not None:
                    continue

                # 加载数据
                value = await data_loader(key)
                if value is not None:
                    if await self.set(key, value):
                        warmed_count += 1

            except Exception as e:
                logger.error(f"Error warming cache key {key}: {e}")

        logger.info(f"Cache warming completed: {warmed_count}/{len(keys)} keys warmed")
        return warmed_count

    async def get_cache_status(self) -> dict[str, Any]:
        """获取缓存状态."""
        status = {
            "configuration": {
                "distribution_strategy": self.distribution_strategy.value,
                "write_through": self.enable_write_through,
                "write_back": self.enable_write_back,
                "cache_coherency": self.cache_coherency_enabled,
            },
            "levels": {},
            "performance": await self.performance_monitor.get_metrics(),
            "timestamp": datetime.utcnow().isoformat(),
        }

        # 各级别缓存状态
        for level, cache in self.cache_levels.items():
            if hasattr(cache, "get_metrics"):
                status["levels"][level.value] = cache.get_metrics()

        # 后端状态
        for level, backend in self.backends.items():
            health = await backend.health_check()
            status["levels"][level.value] = {
                "healthy": health,
                "type": "backend",
                "metrics": getattr(backend, "metrics", {}),
            }

        return status


class LoadBalancer:
    """负载均衡器."""

    def __init__(self, strategy: DistributionStrategy):
        self.strategy = strategy
        self.current_index = 0
        self.node_weights: dict[str, int] = {}

    def select_node(self, nodes: list[str], key: str | None = None) -> str:
        """选择节点."""
        if not nodes:
            raise ValueError("No nodes available")

        if self.strategy == DistributionStrategy.ROUND_ROBIN:
            node = nodes[self.current_index % len(nodes)]
            self.current_index += 1
            return node

        elif self.strategy == DistributionStrategy.WEIGHTED_RANDOM:
            weights = [self.node_weights.get(node, 1) for node in nodes]
            total_weight = sum(weights)
            if total_weight == 0:
                return random.choice(nodes)

            r = random.randint(1, total_weight)
            current_weight = 0
            for i, weight in enumerate(weights):
                current_weight += weight
                if r <= current_weight:
                    return nodes[i]
            return nodes[-1]

        elif self.strategy == DistributionStrategy.CONSISTENT_HASH and key:
            # 简化的一致性哈希
            hash_value = int(
                hashlib.md5(key.encode(), usedforsecurity=False).hexdigest(), 16
            )
            return nodes[hash_value % len(nodes)]

        else:  # AFFINITY_BASED or default
            return random.choice(nodes)


class CacheCoordinator:
    """缓存协调器（用于多级缓存一致性）."""

    def __init__(self, cache_manager: DistributedCacheManager):
        self.cache_manager = cache_manager
        self.invalidations: dict[str, datetime] = {}
        self.version_map: dict[str, int] = {}

    async def notify_write(self, key: str, value: Any):
        """通知写入操作."""
        # 更新版本
        self.version_map[key] = self.version_map.get(key, 0) + 1

        # 清理失效记录
        if key in self.invalidations:
            del self.invalidations[key]

    async def notify_invalidation(self, key: str):
        """通知失效操作."""
        self.invalidations[key] = datetime.utcnow()

        # 清理版本信息
        if key in self.version_map:
            del self.version_map[key]

    async def get_version(self, key: str) -> int:
        """获取键的版本."""
        return self.version_map.get(key, 0)

    async def is_invalidated(self, key: str) -> bool:
        """检查键是否已失效."""
        if key not in self.invalidations:
            return False

        # 检查失效时间是否过期（5分钟）
        if datetime.utcnow() - self.invalidations[key] > timedelta(minutes=5):
            del self.invalidations[key]
            return False

        return True


class CachePerformanceMonitor:
    """缓存性能监控器."""

    def __init__(self):
        self.metrics = {
            "hits": defaultdict(int),
            "misses": 0,
            "writes": defaultdict(int),
            "errors": 0,
            "response_times": defaultdict(list),
            "start_time": datetime.utcnow(),
        }

    async def record_hit(self, level: CacheLevel, response_time: float):
        """记录缓存命中."""
        self.metrics["hits"][level.value] += 1
        self.metrics["response_times"][level.value].append(response_time)

        # 保持最近1000个响应时间
        if len(self.metrics["response_times"][level.value]) > 1000:
            self.metrics["response_times"][level.value] = self.metrics[
                "response_times"
            ][level.value][-1000:]

    async def record_miss(self, response_time: float):
        """记录缓存未命中."""
        self.metrics["misses"] += 1

    async def record_write(self, level: CacheLevel, response_time: float):
        """记录写入操作."""
        self.metrics["writes"][level.value] += 1
        self.metrics["response_times"][f"{level.value}_write"].append(response_time)

    async def record_error(self):
        """记录错误."""
        self.metrics["errors"] += 1

    async def get_metrics(self) -> dict[str, Any]:
        """获取性能指标."""
        total_hits = sum(self.metrics["hits"].values())
        total_requests = total_hits + self.metrics["misses"]

        hit_rate = (total_hits / total_requests * 100) if total_requests > 0 else 0

        # 计算平均响应时间
        avg_response_times = {}
        for level, times in self.metrics["response_times"].items():
            if times:
                avg_response_times[level] = sum(times) / len(times)

        return {
            "hit_rate": round(hit_rate, 2),
            "total_requests": total_requests,
            "hits_by_level": dict(self.metrics["hits"]),
            "misses": self.metrics["misses"],
            "writes_by_level": dict(self.metrics["writes"]),
            "errors": self.metrics["errors"],
            "avg_response_times": {
                k: round(v, 4) for k, v in avg_response_times.items()
            },
            "uptime_seconds": (
                datetime.utcnow() - self.metrics["start_time"]
            ).total_seconds(),
        }


# 全局分布式缓存管理器实例
_distributed_cache_manager: DistributedCacheManager | None = None


def get_distributed_cache_manager() -> DistributedCacheManager | None:
    """获取全局分布式缓存管理器实例."""
    global _distributed_cache_manager
    return _distributed_cache_manager


async def initialize_distributed_cache(
    config: dict[str, Any],
) -> DistributedCacheManager:
    """初始化分布式缓存管理器."""
    global _distributed_cache_manager

    _distributed_cache_manager = DistributedCacheManager(config)
    logger.info("Distributed cache manager initialized")

    return _distributed_cache_manager
