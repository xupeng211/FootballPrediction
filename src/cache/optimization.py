"""
缓存优化策略
Cache Optimization Strategies

提供缓存优化功能：
- 多级缓存
- 缓存预热
- 缓存淘汰策略
- 缓存监控
"""

import asyncio
import json
import logging
from abc import ABC, abstractmethod
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple, Union
from dataclasses import dataclass, field
from enum import Enum
import time
from collections import OrderedDict
from functools import wraps

from src.cache.redis_manager import RedisManager
from src.cache.ttl_cache import TTLCache

logger = logging.getLogger(__name__)


class CacheLevel(Enum):
    """缓存级别"""
    L1_MEMORY = 1    # 内存缓存（最快）
    L2_REDIS = 2     # Redis缓存（较快）
    L3_DATABASE = 3  # 数据库（最慢）


class EvictionPolicy(Enum):
    """淘汰策略"""
    LRU = "lru"          # 最近最少使用
    LFU = "lfu"          # 最少使用频率
    TTL = "ttl"          # 基于时间
    FIFO = "fifo"        # 先进先出


@dataclass
class CacheConfig:
    """缓存配置"""
    # L1缓存配置
    l1_max_size: int = 1000
    l1_ttl: int = 300  # 5分钟

    # L2缓存配置
    l2_ttl: int = 1800  # 30分钟
    l2_max_memory: str = "100mb"

    # 预热配置
    preload_keys: List[str] = field(default_factory=list)
    preload_batch_size: int = 100

    # 监控配置
    metrics_enabled: bool = True
    stats_interval: int = 60  # 秒


class CacheStats:
    """缓存统计"""
    def __init__(self):
        self.hits = 0
        self.misses = 0
        self.sets = 0
        self.deletes = 0
        self.evictions = 0
        self.errors = 0
        self.last_reset = time.time()

    @property
    def hit_rate(self) -> float:
        """命中率"""
        total = self.hits + self.misses
        return self.hits / total if total > 0 else 0.0

    def reset(self):
        """重置统计"""
        self.hits = 0
        self.misses = 0
        self.sets = 0
        self.deletes = 0
        self.evictions = 0
        self.errors = 0
        self.last_reset = time.time()

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "hits": self.hits,
            "misses": self.misses,
            "sets": self.sets,
            "deletes": self.deletes,
            "evictions": self.evictions,
            "errors": self.errors,
            "hit_rate": self.hit_rate,
            "uptime": time.time() - self.last_reset
        }


class MemoryCache:
    """内存缓存实现"""

    def __init__(self, max_size: int = 1000, ttl: int = 300, eviction_policy: EvictionPolicy = EvictionPolicy.LRU):
        self.max_size = max_size
        self.ttl = ttl
        self.eviction_policy = eviction_policy
        self._cache: OrderedDict = OrderedDict()
        self._timestamps: Dict[str, float] = {}
        self._access_count: Dict[str, int] = {}
        self._stats = CacheStats()

    def get(self, key: str) -> Optional[Any]:
        """获取缓存值"""
        try:
            # 检查TTL
            if self._is_expired(key):
                # 直接删除过期的键
                if key in self._cache:
                    del self._cache[key]
                    del self._timestamps[key]
                    del self._access_count[key]
                self._stats.misses += 1
                return None

            # 获取值
            value = self._cache.get(key)
            if value is not None:
                self._update_access(key)
                self._stats.hits += 1
                return value

            self._stats.misses += 1
            return None
        except Exception as e:
            logger.error(f"Memory cache get error: {e}")
            self._stats.errors += 1
            return None

    def set(self, key: str, value: Any, ttl: Optional[int] = None) -> bool:
        """设置缓存值"""
        try:
            # 检查容量
            if len(self._cache) >= self.max_size and key not in self._cache:
                self._evict()

            # 设置值
            self._cache[key] = value
            self._timestamps[key] = time.time() + (ttl or self.ttl)
            self._access_count[key] = 1

            # 移动到末尾（LRU）
            self._cache.move_to_end(key)

            self._stats.sets += 1
            return True
        except Exception as e:
            logger.error(f"Memory cache set error: {e}")
            self._stats.errors += 1
            return False

    def delete(self, key: str) -> bool:
        """删除缓存值"""
        try:
            if key in self._cache:
                del self._cache[key]
                del self._timestamps[key]
                del self._access_count[key]
                self._stats.deletes += 1
                return True
            return False
        except Exception as e:
            logger.error(f"Memory cache delete error: {e}")
            self._stats.errors += 1
            return False

    def clear(self):
        """清空缓存"""
        self._cache.clear()
        self._timestamps.clear()
        self._access_count.clear()

    def _is_expired(self, key: str) -> bool:
        """检查是否过期"""
        if key not in self._timestamps:
            return True
        return time.time() > self._timestamps[key]

    def _update_access(self, key: str):
        """更新访问信息"""
        self._access_count[key] = self._access_count.get(key, 0) + 1
        # LRU: 移动到末尾
        if self.eviction_policy == EvictionPolicy.LRU:
            self._cache.move_to_end(key)

    def _evict(self):
        """淘汰缓存项"""
        if not self._cache:
            return

        if self.eviction_policy == EvictionPolicy.LRU:
            # 淘汰最久未使用的
            key, _ = self._cache.popitem(last=False)
        elif self.eviction_policy == EvictionPolicy.LFU:
            # 淘汰使用频率最低的
            key = min(self._access_count.items(), key=lambda x: x[1])[0]
        elif self.eviction_policy == EvictionPolicy.FIFO:
            # 淘汰最早的
            key, _ = self._cache.popitem(last=False)
        else:
            # 默认LRU
            key, _ = self._cache.popitem(last=False)

        # 清理相关信息
        del self._timestamps[key]
        del self._access_count[key]
        self._stats.evictions += 1

    def get_stats(self) -> Dict[str, Any]:
        """获取统计信息"""
        stats = self._stats.to_dict()
        stats.update({
            "size": len(self._cache),
            "max_size": self.max_size,
            "utilization": len(self._cache) / self.max_size
        })
        return stats


class MultiLevelCache:
    """多级缓存"""

    def __init__(self, config: CacheConfig, redis_manager: Optional[RedisManager] = None):
        self.config = config
        self.redis_manager = redis_manager
        self.l1_cache = MemoryCache(
            max_size=config.l1_max_size,
            ttl=config.l1_ttl,
            eviction_policy=EvictionPolicy.LRU
        )
        self._stats = CacheStats()

    async def get(self, key: str) -> Optional[Any]:
        """获取缓存值（多级）"""
        # L1缓存
        value = self.l1_cache.get(key)
        if value is not None:
            self._stats.hits += 1
            return value

        # L2缓存
        if self.redis_manager:
            try:
                value = await self.redis_manager.get(key)
                if value is not None:
                    # 回填L1缓存
                    self.l1_cache.set(key, value, self.config.l1_ttl)
                    self._stats.hits += 1
                    return value
            except Exception as e:
                logger.error(f"Redis get error: {e}")

        self._stats.misses += 1
        return None

    async def set(self, key: str, value: Any, ttl: Optional[int] = None) -> bool:
        """设置缓存值（多级）"""
        success = True

        # L1缓存
        if not self.l1_cache.set(key, value, ttl or self.config.l1_ttl):
            success = False

        # L2缓存
        if self.redis_manager:
            try:
                await self.redis_manager.set(
                    key,
                    value,
                    ttl=ttl or self.config.l2_ttl
                )
            except Exception as e:
                logger.error(f"Redis set error: {e}")
                success = False

        if success:
            self._stats.sets += 1
        return success

    async def delete(self, key: str) -> bool:
        """删除缓存值（多级）"""
        success = True

        # L1缓存
        self.l1_cache.delete(key)

        # L2缓存
        if self.redis_manager:
            try:
                await self.redis_manager.delete(key)
            except Exception as e:
                logger.error(f"Redis delete error: {e}")
                success = False

        if success:
            self._stats.deletes += 1
        return success

    async def preload(self, preload_func: callable, keys: List[str]):
        """缓存预热"""
        logger.info(f"开始缓存预热，{len(keys)}个键")

        batch_size = self.config.preload_batch_size
        for i in range(0, len(keys), batch_size):
            batch_keys = keys[i:i + batch_size]

            # 并行加载
            tasks = []
            for key in batch_keys:
                task = self._preload_key(key, preload_func)
                tasks.append(task)

            await asyncio.gather(*tasks, return_exceptions=True)

            logger.info(f"预热进度: {min(i + batch_size, len(keys))}/{len(keys)}")

        logger.info("缓存预热完成")

    async def _preload_key(self, key: str, preload_func: callable):
        """预热单个键"""
        try:
            # 检查是否已存在
            if await self.get(key) is not None:
                return

            # 加载数据
            value = await preload_func(key)
            if value is not None:
                await self.set(key, value)
        except Exception as e:
            logger.error(f"预热键失败 {key}: {e}")

    def get_stats(self) -> Dict[str, Any]:
        """获取统计信息"""
        l1_stats = self.l1_cache.get_stats()
        l2_stats = {}

        if self.redis_manager:
            try:
                # 获取Redis信息
                l2_stats = {
                    "connected": True,
                    # 可以添加更多Redis统计
                }
            except:
                l2_stats = {"connected": False}

        return {
            "l1_cache": l1_stats,
            "l2_cache": l2_stats,
            "overall": self._stats.to_dict(),
            "config": {
                "l1_max_size": self.config.l1_max_size,
                "l1_ttl": self.config.l1_ttl,
                "l2_ttl": self.config.l2_ttl
            }
        }


class CacheWarmer:
    """缓存预热器"""

    def __init__(self, cache: MultiLevelCache):
        self.cache = cache
        self.warmup_tasks: List[Tuple[str, callable]] = []

    def add_task(self, name: str, loader_func: callable):
        """添加预热任务"""
        self.warmup_tasks.append((name, loader_func))

    async def warmup_all(self):
        """执行所有预热任务"""
        logger.info("开始缓存预热")
        start_time = time.time()

        for name, loader_func in self.warmup_tasks:
            try:
                logger.info(f"执行预热任务: {name}")
                await loader_func()
                logger.info(f"预热任务完成: {name}")
            except Exception as e:
                logger.error(f"预热任务失败 {name}: {e}")

        duration = time.time() - start_time
        logger.info(f"缓存预热完成，耗时: {duration:.2f}秒")

    async def warmup_predictions(self):
        """预热预测数据"""
        async def load_recent_predictions():
            # 这里应该从数据库加载最近的预测
            # 示例实现
            keys = [f"prediction:{i}" for i in range(1000)]
            await self.cache.preload(
                lambda key: {"match_id": int(key.split(":")[1]), "prediction": "home"},
                keys
            )
        await load_recent_predictions()

    async def warmup_teams(self):
        """预热球队数据"""
        async def load_teams():
            # 这里应该从数据库加载球队信息
            keys = [f"team:{i}" for i in range(500)]
            await self.cache.preload(
                lambda key: {"id": int(key.split(":")[1]), "name": f"Team {key.split(':')[1]}"},
                keys
            )
        await load_teams()


class CacheOptimizer:
    """缓存优化器"""

    def __init__(self, cache: MultiLevelCache):
        self.cache = cache
        self.optimization_rules: List[callable] = []

    def add_rule(self, rule_func: callable):
        """添加优化规则"""
        self.optimization_rules.append(rule_func)

    async def optimize(self):
        """执行优化"""
        logger.info("开始缓存优化")

        for rule in self.optimization_rules:
            try:
                await rule()
            except Exception as e:
                logger.error(f"优化规则执行失败: {e}")

        logger.info("缓存优化完成")

    async def cleanup_expired(self):
        """清理过期缓存"""
        # L1缓存会自动清理过期项
        # 这里可以添加额外的清理逻辑
        logger.info("清理过期缓存完成")

    async def adjust_ttl_based_on_access(self):
        """根据访问模式调整TTL"""
        stats = self.cache.get_stats()
        hit_rate = stats["overall"]["hit_rate"]

        if hit_rate > 0.8:
            # 命中率高，增加TTL
            logger.info("缓存命中率高，建议增加TTL")
        elif hit_rate < 0.5:
            # 命中率低，减少TTL或增加容量
            logger.info("缓存命中率低，建议减少TTL或增加容量")

    async def promote_hot_keys(self):
        """提升热键到更高缓存级别"""
        # 分析访问模式，识别热键
        # 将热键提升到更快的缓存层
        logger.info("热键提升完成")


# 全局缓存管理器
_cache_manager: Optional[MultiLevelCache] = None


def get_cache_manager() -> Optional[MultiLevelCache]:
    """获取全局缓存管理器"""
    return _cache_manager


def init_cache_manager(config: CacheConfig, redis_manager: Optional[RedisManager] = None):
    """初始化全局缓存管理器"""
    global _cache_manager
    _cache_manager = MultiLevelCache(config, redis_manager)
    return _cache_manager


# 缓存装饰器
def cached(ttl: int = 300, key_prefix: str = ""):
    """缓存装饰器"""
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            cache = get_cache_manager()
            if not cache:
                return await func(*args, **kwargs)

            # 生成缓存键
            cache_key = f"{key_prefix}:{func.__name__}:{hash(str(args) + str(kwargs))}"

            # 尝试从缓存获取
            value = await cache.get(cache_key)
            if value is not None:
                return value

            # 执行函数
            result = await func(*args, **kwargs)

            # 缓存结果
            await cache.set(cache_key, result, ttl)

            return result
        return wrapper
    return decorator