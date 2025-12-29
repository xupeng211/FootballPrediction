#!/usr/bin/env python3
"""
缓存策略管理器
专门为足球预测系统设计的多级缓存管理工具
"""

import asyncio
import hashlib
import json
import logging
import pickle
import time
from collections import OrderedDict
from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Any

import aioredis

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class CacheLevel(Enum):
    """缓存级别"""

    L1_MEMORY = "l1_memory"
    L2_REDIS = "l2_redis"
    L3_DATABASE = "l3_database"


class EvictionPolicy(Enum):
    """缓存淘汰策略"""

    LRU = "lru"
    LFU = "lfu"
    FIFO = "fifo"
    TTL = "ttl"


@dataclass
class CacheConfig:
    """缓存配置"""

    ttl: int = 3600  # 生存时间（秒）
    max_size: int = 1000  # 最大缓存条目数
    enable_l1: bool = True  # 启用内存缓存
    enable_l2: bool = True  # 启用Redis缓存
    eviction_policy: EvictionPolicy = EvictionPolicy.LRU
    serialize_method: str = "json"  # json, pickle, msgpack
    compression: bool = False  # 是否启用压缩
    key_prefix: str = "football"  # 键前缀


@dataclass
class CacheStats:
    """缓存统计信息"""

    l1_hits: int = 0
    l1_misses: int = 0
    l2_hits: int = 0
    l2_misses: int = 0
    l1_evictions: int = 0
    l2_evictions: int = 0
    errors: int = 0
    total_requests: int = 0
    total_bytes_cached: int = 0


class LRUCache:
    """LRU内存缓存实现"""

    def __init__(self, max_size: int = 1000, ttl: int = 3600):
        self.max_size = max_size
        self.ttl = ttl
        self.cache = OrderedDict()
        self.timestamps = {}
        self.stats = CacheStats()

    def get(self, key: str) -> Any | None:
        """获取缓存值"""
        if key not in self.cache:
            self.stats.l1_misses += 1
            return None

        # 检查TTL
        if self._is_expired(key):
            self.remove(key)
            self.stats.l1_misses += 1
            return None

        # 移到末尾（最近使用）
        value = self.cache.pop(key)
        self.cache[key] = value
        self.stats.l1_hits += 1

        return value

    def set(self, key: str, value: Any) -> None:
        """设置缓存值"""
        # 如果已存在，先删除
        if key in self.cache:
            del self.cache[key]

        # 如果达到最大容量，删除最旧的条目
        elif len(self.cache) >= self.max_size:
            oldest_key = next(iter(self.cache))
            self.remove(oldest_key)
            self.stats.l1_evictions += 1

        # 添加新条目
        self.cache[key] = value
        self.timestamps[key] = time.time()

    def remove(self, key: str) -> bool:
        """删除缓存条目"""
        if key in self.cache:
            del self.cache[key]
            if key in self.timestamps:
                del self.timestamps[key]
            return True
        return False

    def clear(self) -> None:
        """清空缓存"""
        self.cache.clear()
        self.timestamps.clear()

    def size(self) -> int:
        """获取缓存大小"""
        return len(self.cache)

    def _is_expired(self, key: str) -> bool:
        """检查条目是否过期"""
        if key not in self.timestamps:
            return True
        return time.time() - self.timestamps[key] > self.ttl

    def cleanup_expired(self) -> int:
        """清理过期条目"""
        expired_keys = [key for key in self.cache.keys() if self._is_expired(key)]

        for key in expired_keys:
            self.remove(key)
            self.stats.l1_evictions += 1

        return len(expired_keys)


class CacheStrategyManager:
    """缓存策略管理器"""

    def __init__(self, redis_url: str = "redis://localhost:6379"):
        self.redis_url = redis_url
        self.redis_pool: aioredis.Redis | None = None
        self.l1_caches: dict[str, LRUCache] = {}
        self.configs: dict[str, CacheConfig] = {}
        self.global_stats = CacheStats()
        self.background_tasks: list[asyncio.Task] = []

    async def initialize(self):
        """初始化缓存管理器"""
        logger.info("🔧 初始化缓存策略管理器...")

        # 初始化Redis连接
        try:
            self.redis_pool = aioredis.from_url(
                self.redis_url, max_connections=20, retry_on_timeout=True, socket_keepalive=True
            )
            await self.redis_pool.ping()
            logger.info("🔴 Redis连接已建立")
        except Exception as e:
            logger.error(f"Redis连接失败: {e}")
            self.redis_pool = None

        # 启动后台任务
        self.background_tasks = [
            asyncio.create_task(self._cleanup_expired_task()),
            asyncio.create_task(self._stats_report_task()),
        ]

        logger.info("✅ 缓存策略管理器初始化完成")

    def register_cache_type(self, cache_type: str, config: CacheConfig):
        """注册缓存类型和配置"""
        self.configs[cache_type] = config

        if config.enable_l1 and cache_type not in self.l1_caches:
            self.l1_caches[cache_type] = LRUCache(max_size=config.max_size, ttl=config.ttl)
            logger.info(f"📝 注册L1缓存类型: {cache_type}")

        logger.info(f"⚙️  缓存配置已注册: {cache_type} - TTL: {config.ttl}s, MaxSize: {config.max_size}")

    def _generate_key(self, cache_type: str, key_data: str | dict | Any) -> str:
        """生成缓存键"""
        config = self.configs.get(cache_type, CacheConfig())
        prefix = f"{config.key_prefix}:{cache_type}"

        if isinstance(key_data, str):
            key_str = key_data
        elif isinstance(key_data, dict):
            key_str = json.dumps(key_data, sort_keys=True)
        else:
            key_str = str(key_data)

        # 生成哈希确保键的一致性和长度
        key_hash = hashlib.md5(key_str.encode()).hexdigest()
        return f"{prefix}:{key_hash}"

    async def get(
        self, cache_type: str, key_data: str | dict | Any, fallback_func: Callable | None = None, **kwargs
    ) -> Any:
        """获取缓存值"""
        cache_key = self._generate_key(cache_type, key_data)
        config = self.configs.get(cache_type, CacheConfig())

        self.global_stats.total_requests += 1

        # L1缓存（内存）
        if config.enable_l1 and cache_type in self.l1_caches:
            value = self.l1_caches[cache_type].get(cache_key)
            if value is not None:
                logger.debug(f"L1缓存命中: {cache_type}:{cache_key[:16]}...")
                return value

        # L2缓存（Redis）
        if config.enable_l2 and self.redis_pool:
            try:
                redis_value = await self.redis_pool.get(cache_key)
                if redis_value:
                    # 反序列化
                    if config.serialize_method == "json":
                        value = json.loads(redis_value)
                    elif config.serialize_method == "pickle":
                        value = pickle.loads(redis_value)
                    else:
                        value = redis_value

                    # 回填L1缓存
                    if config.enable_l1 and cache_type in self.l1_caches:
                        self.l1_caches[cache_type].set(cache_key, value)

                    self.global_stats.l2_hits += 1
                    logger.debug(f"L2缓存命中: {cache_type}:{cache_key[:16]}...")
                    return value

            except Exception as e:
                logger.error(f"Redis获取失败: {e}")
                self.global_stats.errors += 1

        self.global_stats.l2_misses += 1

        # 执行回退函数获取数据
        if fallback_func:
            try:
                value = await fallback_func(**kwargs)
                await self.set(cache_type, key_data, value)
                return value
            except Exception as e:
                logger.error(f"回退函数执行失败: {e}")
                self.global_stats.errors += 1

        return None

    async def set(self, cache_type: str, key_data: str | dict | Any, value: Any) -> bool:
        """设置缓存值"""
        cache_key = self._generate_key(cache_type, key_data)
        config = self.configs.get(cache_type, CacheConfig())

        success = True

        # L1缓存（内存）
        if config.enable_l1 and cache_type in self.l1_caches:
            self.l1_caches[cache_type].set(cache_key, value)

        # L2缓存（Redis）
        if config.enable_l2 and self.redis_pool:
            try:
                # 序列化
                if config.serialize_method == "json":
                    serialized_value = json.dumps(value, default=str)
                elif config.serialize_method == "pickle":
                    serialized_value = pickle.dumps(value)
                else:
                    serialized_value = str(value)

                # 压缩（如果启用）
                if config.compression:
                    import gzip

                    serialized_value = gzip.compress(serialized_value.encode())

                await self.redis_pool.setex(cache_key, config.ttl, serialized_value)

                # 更新统计
                value_size = len(str(serialized_value))
                self.global_stats.total_bytes_cached += value_size

            except Exception as e:
                logger.error(f"Redis设置失败: {e}")
                success = False
                self.global_stats.errors += 1

        return success

    async def delete(self, cache_type: str, key_data: str | dict | Any) -> bool:
        """删除缓存值"""
        cache_key = self._generate_key(cache_type, key_data)
        config = self.configs.get(cache_type, CacheConfig())

        success = True

        # L1缓存删除
        if config.enable_l1 and cache_type in self.l1_caches:
            self.l1_caches[cache_type].remove(cache_key)

        # L2缓存删除
        if config.enable_l2 and self.redis_pool:
            try:
                await self.redis_pool.delete(cache_key)
            except Exception as e:
                logger.error(f"Redis删除失败: {e}")
                success = False

        return success

    async def clear_cache_type(self, cache_type: str) -> int:
        """清空特定类型的缓存"""
        cleared_count = 0

        # 清空L1缓存
        if cache_type in self.l1_caches:
            old_size = self.l1_caches[cache_type].size()
            self.l1_caches[cache_type].clear()
            cleared_count += old_size

        # 清空L2缓存
        if self.redis_pool:
            try:
                config = self.configs.get(cache_type, CacheConfig())
                pattern = f"{config.key_prefix}:{cache_type}:*"
                keys = await self.redis_pool.keys(pattern)
                if keys:
                    deleted_count = await self.redis_pool.delete(*keys)
                    cleared_count += deleted_count
            except Exception as e:
                logger.error(f"清空Redis缓存失败: {e}")

        logger.info(f"清空缓存类型 {cache_type}: {cleared_count} 个条目")
        return cleared_count

    async def warm_up_cache(self, cache_type: str, warm_up_data: list[dict]):
        """缓存预热"""
        logger.info(f"🔥 开始缓存预热: {cache_type} - {len(warm_up_data)} 个条目")

        success_count = 0
        for item in warm_up_data:
            try:
                key = item.get("key")
                value = item.get("value")
                if key and value:
                    await self.set(cache_type, key, value)
                    success_count += 1
            except Exception as e:
                logger.error(f"预热条目失败: {e}")

        logger.info(f"✅ 缓存预热完成: {cache_type} - {success_count}/{len(warm_up_data)} 成功")

    def get_cache_stats(self, cache_type: str | None = None) -> dict[str, Any]:
        """获取缓存统计信息"""
        stats = {
            "global": {
                "total_requests": self.global_stats.total_requests,
                "l1_hits": self.global_stats.l1_hits,
                "l2_hits": self.global_stats.l2_hits,
                "l1_misses": self.global_stats.l1_misses,
                "l2_misses": self.global_stats.l2_misses,
                "l1_evictions": self.global_stats.l1_evictions,
                "l2_evictions": self.global_stats.l2_evictions,
                "errors": self.global_stats.errors,
                "total_bytes_cached": self.global_stats.total_bytes_cached,
                "hit_rate": 0,
                "l1_hit_rate": 0,
                "l2_hit_rate": 0,
            }
        }

        # 计算命中率
        total_requests = self.global_stats.total_requests
        if total_requests > 0:
            stats["global"]["hit_rate"] = (self.global_stats.l1_hits + self.global_stats.l2_hits) / total_requests
            stats["global"]["l1_hit_rate"] = self.global_stats.l1_hits / total_requests
            stats["global"]["l2_hit_rate"] = self.global_stats.l2_hits / total_requests

        # L1缓存统计
        if cache_type:
            if cache_type in self.l1_caches:
                l1_cache = self.l1_caches[cache_type]
                stats["l1_cache"] = {
                    "size": l1_cache.size(),
                    "max_size": l1_cache.max_size,
                    "hits": l1_cache.stats.l1_hits,
                    "misses": l1_cache.stats.l1_misses,
                    "evictions": l1_cache.stats.l1_evictions,
                    "hit_rate": l1_cache.stats.l1_hits / (l1_cache.stats.l1_hits + l1_cache.stats.l1_misses)
                    if (l1_cache.stats.l1_hits + l1_cache.stats.l1_misses) > 0
                    else 0,
                }
        else:
            stats["l1_caches"] = {}
            for ct, l1_cache in self.l1_caches.items():
                stats["l1_caches"][ct] = {
                    "size": l1_cache.size(),
                    "max_size": l1_cache.max_size,
                    "hit_rate": l1_cache.stats.l1_hits / (l1_cache.stats.l1_hits + l1_cache.stats.l1_misses)
                    if (l1_cache.stats.l1_hits + l1_cache.stats.l1_misses) > 0
                    else 0,
                }

        return stats

    async def get_redis_info(self) -> dict[str, Any]:
        """获取Redis信息"""
        if not self.redis_pool:
            return {"error": "Redis not connected"}

        try:
            info = await self.redis_pool.info()
            return {
                "version": info.get("redis_version"),
                "used_memory": info.get("used_memory_human"),
                "connected_clients": info.get("connected_clients"),
                "keyspace_hits": info.get("keyspace_hits"),
                "keyspace_misses": info.get("keyspace_misses"),
                "uptime_in_seconds": info.get("uptime_in_seconds"),
            }
        except Exception as e:
            return {"error": str(e)}

    async def health_check(self) -> dict[str, Any]:
        """健康检查"""
        health = {"status": "healthy", "components": {}, "stats": self.get_cache_stats()}

        # L1缓存健康检查
        health["components"]["l1_memory"] = {
            "status": "healthy" if self.l1_caches else "not_initialized",
            "cache_types": list(self.l1_caches.keys()),
        }

        # Redis健康检查
        if self.redis_pool:
            try:
                start_time = time.time()
                await self.redis_pool.ping()
                response_time = time.time() - start_time
                health["components"]["redis"] = {"status": "healthy", "response_time": f"{response_time:.3f}s"}
            except Exception as e:
                health["components"]["redis"] = {"status": "unhealthy", "error": str(e)}
                health["status"] = "degraded"
        else:
            health["components"]["redis"] = {"status": "not_connected"}
            health["status"] = "degraded"

        return health

    async def _cleanup_expired_task(self):
        """清理过期条目的后台任务"""
        while True:
            try:
                for cache_type, l1_cache in self.l1_caches.items():
                    cleaned_count = l1_cache.cleanup_expired()
                    if cleaned_count > 0:
                        self.global_stats.l1_evictions += cleaned_count
                        logger.debug(f"清理过期L1缓存条目: {cache_type} - {cleaned_count} 个")

                await asyncio.sleep(300)  # 每5分钟清理一次

            except Exception as e:
                logger.error(f"清理过期缓存任务错误: {e}")
                await asyncio.sleep(60)

    async def _stats_report_task(self):
        """统计报告后台任务"""
        while True:
            try:
                stats = self.get_cache_stats()
                logger.info(
                    f"缓存统计报告 - 总请求: {stats['global']['total_requests']}, "
                    f"命中率: {stats['global']['hit_rate']:.2%}, "
                    f"L1命中率: {stats['global']['l1_hit_rate']:.2%}, "
                    f"L2命中率: {stats['global']['l2_hit_rate']:.2%}"
                )

                await asyncio.sleep(3600)  # 每小时报告一次

            except Exception as e:
                logger.error(f"统计报告任务错误: {e}")
                await asyncio.sleep(300)

    async def cleanup(self):
        """清理资源"""
        logger.info("🧹 清理缓存策略管理器...")

        # 取消后台任务
        for task in self.background_tasks:
            task.cancel()

        if self.background_tasks:
            await asyncio.gather(*self.background_tasks, return_exceptions=True)

        # 关闭Redis连接
        if self.redis_pool:
            await self.redis_pool.close()

        # 清空L1缓存
        for l1_cache in self.l1_caches.values():
            l1_cache.clear()

        logger.info("✅ 缓存策略管理器清理完成")


# 预定义的缓存配置
CACHE_CONFIGS = {
    "match_data": CacheConfig(
        ttl=1800,  # 30分钟
        max_size=500,
        serialize_method="json",
    ),
    "team_stats": CacheConfig(
        ttl=3600,  # 1小时
        max_size=200,
        serialize_method="json",
    ),
    "predictions": CacheConfig(
        ttl=86400,  # 24小时
        max_size=1000,
        serialize_method="json",
    ),
    "features": CacheConfig(
        ttl=7200,  # 2小时
        max_size=300,
        serialize_method="pickle",
        compression=True,
    ),
    "user_sessions": CacheConfig(
        ttl=1800,  # 30分钟
        max_size=1000,
        serialize_method="json",
    ),
}


async def main():
    """主函数示例"""
    print("🗄️ 缓存策略管理器")
    print("=" * 50)

    manager = CacheStrategyManager("redis://localhost:6379")

    try:
        await manager.initialize()

        # 注册缓存类型
        for cache_type, config in CACHE_CONFIGS.items():
            manager.register_cache_type(cache_type, config)

        # 示例：缓存比赛数据
        async def fetch_match_data(match_id: int):
            # 模拟数据库查询
            await asyncio.sleep(0.1)
            return {
                "match_id": match_id,
                "home_team": "Team A",
                "away_team": "Team B",
                "date": datetime.now().isoformat(),
            }

        # 获取缓存数据（首次会调用回退函数）
        match_data = await manager.get("match_data", {"match_id": 123}, fallback_func=fetch_match_data, match_id=123)
        print(f"获取比赛数据: {match_data}")

        # 再次获取（从缓存）
        match_data = await manager.get("match_data", {"match_id": 123})
        print(f"从缓存获取: {match_data}")

        # 缓存统计
        stats = manager.get_cache_stats()
        print("\n📊 缓存统计:")
        print(json.dumps(stats, indent=2))

        # 健康检查
        health = await manager.health_check()
        print("\n💚 健康检查:")
        print(json.dumps(health, indent=2))

    finally:
        await manager.cleanup()


if __name__ == "__main__":
    asyncio.run(main())
