"""
智能缓存系统
Smart Cache System

提供多层缓存、智能预热、自动失效和性能优化的缓存系统。
"""

import asyncio
import hashlib
import json
import logging
import time
from datetime import datetime, timedelta
from typing import Any, Callable, Dict, List, Optional, Union

from src.cache.redis_enhanced import EnhancedRedisClient

logger = logging.getLogger(__name__)


class CacheEntry:
    """缓存条目"""

    def __init__(self, key: str, value: Any, ttl: int = 3600, metadata: Optional[Dict[str, Any]] = None):
        self.key = key
        self.value = value
        self.ttl = ttl
        self.created_at = time.time()
        self.expires_at = self.created_at + ttl
        self.access_count = 0
        self.last_accessed = self.created_at
        self.metadata = metadata or {}
        self.size = self._calculate_size()

    def _calculate_size(self) -> int:
        """计算条目大小"""
        try:
            return len(json.dumps(self.value, default=str))
        except:
            return len(str(self.value))

    def is_expired(self) -> bool:
        """检查是否过期"""
        return time.time() > self.expires_at

    def access(self) -> Any:
        """访问缓存条目"""
        self.access_count += 1
        self.last_accessed = time.time()
        return self.value

    def extend_ttl(self, additional_ttl: int):
        """延长TTL"""
        self.expires_at += additional_ttl
        self.ttl = self.expires_at - time.time()


class SmartCacheManager:
    """智能缓存管理器"""

    def __init__(self, redis_client: Optional[EnhancedRedisClient] = None,
                 max_memory_size: int = 100 * 1024 * 1024):  # 100MB
        self.redis_client = redis_client
        self.max_memory_size = max_memory_size
        self.local_cache: Dict[str, CacheEntry] = {}
        self.cache_stats = {
            'hits': 0,
            'misses': 0,
            'sets': 0,
            'deletes': 0,
            'evictions': 0
        }
        self.preload_tasks: Dict[str, Callable] = {}
        self.background_tasks: List[asyncio.Task] = []

    async def get(self, key: str, default: Any = None) -> Any:
        """获取缓存值"""
        # 首先检查本地缓存
        if key in self.local_cache:
            entry = self.local_cache[key]
            if not entry.is_expired():
                self.cache_stats['hits'] += 1
                return entry.access()
            else:
                # 本地缓存过期，删除
                del self.local_cache[key]

        # 检查Redis缓存
        if self.redis_client:
            try:
                redis_value = await self.redis_client.get(key)
                if redis_value is not None:
                    self.cache_stats['hits'] += 1
                    # 将Redis缓存同步到本地缓存
                    cache_data = json.loads(redis_value)
                    entry = CacheEntry(
                        key=key,
                        value=cache_data['value'],
                        ttl=cache_data.get('ttl', 3600),
                        metadata=cache_data.get('metadata', {})
                    )
                    self.local_cache[key] = entry
                    return entry.value
            except Exception as e:
                logger.warning(f"Redis cache get error: {e}")

        # 缓存未命中
        self.cache_stats['misses'] += 1

        # 检查是否有预加载任务
        if key in self.preload_tasks:
            # 启动后台预加载任务
            task = asyncio.create_task(self._preload_cache(key))
            self.background_tasks.append(task)

        return default

    async def set(self, key: str, value: Any, ttl: int = 3600,
                  metadata: Optional[Dict[str, Any]] = None) -> bool:
        """设置缓存值"""
        try:
            # 创建缓存条目
            entry = CacheEntry(key, value, ttl, metadata)

            # 检查内存限制
            await self._ensure_memory_limit(entry.size)

            # 设置本地缓存
            self.local_cache[key] = entry
            self.cache_stats['sets'] += 1

            # 设置Redis缓存
            if self.redis_client:
                cache_data = {
                    'value': value,
                    'ttl': ttl,
                    'metadata': metadata,
                    'created_at': entry.created_at
                }
                await self.redis_client.setex(key, ttl, json.dumps(cache_data, default=str))

            return True

        except Exception as e:
            logger.error(f"Cache set error: {e}")
            return False

    async def delete(self, key: str) -> bool:
        """删除缓存"""
        try:
            # 删除本地缓存
            if key in self.local_cache:
                del self.local_cache[key]
                self.cache_stats['deletes'] += 1

            # 删除Redis缓存
            if self.redis_client:
                await self.redis_client.delete(key)

            return True

        except Exception as e:
            logger.error(f"Cache delete error: {e}")
            return False

    async def clear(self, pattern: str = "*") -> int:
        """清理缓存"""
        cleared_count = 0

        try:
            # 清理本地缓存
            keys_to_delete = []
            for key in self.local_cache.keys():
                if pattern == "*" or pattern in key:
                    keys_to_delete.append(key)

            for key in keys_to_delete:
                del self.local_cache[key]
                cleared_count += 1

            # 清理Redis缓存
            if self.redis_client:
                if pattern == "*":
                    # 清理所有缓存（使用特定前缀）
                    await self.redis_client.delete_by_pattern("cache:*")
                else:
                    await self.redis_client.delete_by_pattern(pattern)

            self.cache_stats['deletes'] += cleared_count
            return cleared_count

        except Exception as e:
            logger.error(f"Cache clear error: {e}")
            return 0

    def register_preload_handler(self, key_pattern: str, handler: Callable):
        """注册预加载处理器"""
        self.preload_tasks[key_pattern] = handler

    async def _preload_cache(self, key: str):
        """预加载缓存"""
        try:
            # 查找匹配的预加载处理器
            for pattern, handler in self.preload_tasks.items():
                if pattern in key or key in pattern:
                    # 执行预加载
                    result = await handler(key)
                    if result is not None:
                        await self.set(key, result, ttl=1800)  # 30分钟TTL
                        logger.info(f"Preloaded cache for key: {key}")
                    break
        except Exception as e:
            logger.error(f"Preload error for key {key}: {e}")

    async def _ensure_memory_limit(self, new_entry_size: int):
        """确保内存限制"""
        current_size = sum(entry.size for entry in self.local_cache.values())

        while current_size + new_entry_size > self.max_memory_size and self.local_cache:
            # 使用LRU策略清理缓存
            oldest_key = min(self.local_cache.keys(),
                           key=lambda k: self.local_cache[k].last_accessed)
            oldest_entry = self.local_cache[oldest_key]
            del self.local_cache[oldest_key]
            current_size -= oldest_entry.size
            self.cache_stats['evictions'] += 1

            logger.debug(f"Evicted cache entry: {oldest_key}")

    async def warm_cache(self, keys: List[str], handler: Callable):
        """批量预热缓存"""
        for key in keys:
            if key not in self.local_cache:
                try:
                    result = await handler(key)
                    if result is not None:
                        await self.set(key, result, ttl=3600)
                except Exception as e:
                    logger.error(f"Cache warm error for key {key}: {e}")

    def get_cache_stats(self) -> Dict[str, Any]:
        """获取缓存统计信息"""
        total_requests = self.cache_stats['hits'] + self.cache_stats['misses']
        hit_rate = (self.cache_stats['hits'] / total_requests * 100) if total_requests > 0 else 0

        memory_usage = sum(entry.size for entry in self.local_cache.values())

        return {
            'hits': self.cache_stats['hits'],
            'misses': self.cache_stats['misses'],
            'hit_rate': hit_rate,
            'sets': self.cache_stats['sets'],
            'deletes': self.cache_stats['deletes'],
            'evictions': self.cache_stats['evictions'],
            'local_cache_size': len(self.local_cache),
            'memory_usage_bytes': memory_usage,
            'memory_usage_mb': memory_usage / (1024 * 1024),
            'background_tasks_count': len(self.background_tasks),
            'preload_handlers_count': len(self.preload_tasks)
        }

    async def cleanup_expired(self) -> int:
        """清理过期缓存"""
        expired_keys = []
        current_time = time.time()

        for key, entry in self.local_cache.items():
            if entry.is_expired():
                expired_keys.append(key)

        for key in expired_keys:
            del self.local_cache[key]

        if expired_keys:
            logger.info(f"Cleaned up {len(expired_keys)} expired cache entries")

        return len(expired_keys)

    async def optimize_cache(self) -> Dict[str, Any]:
        """优化缓存性能"""
        optimization_result = {
            'cleaned_expired': 0,
            'evicted_lru': 0,
            'recommendations': []
        }

        # 清理过期缓存
        optimization_result['cleaned_expired'] = await self.cleanup_expired()

        # 检查缓存命中率
        stats = self.get_cache_stats()
        if stats['hit_rate'] < 70:
            optimization_result['recommendations'].append(
                "缓存命中率较低，建议增加预加载策略或调整TTL设置"
            )

        # 检查内存使用率
        if stats['memory_usage_mb'] > self.max_memory_size * 0.8 / (1024 * 1024):
            optimization_result['recommendations'].append(
                "内存使用率较高，建议增加缓存大小或优化缓存策略"
            )

        # 清理低频访问的缓存
        if len(self.local_cache) > 1000:
            # 清理访问次数少于3次的缓存
            low_access_keys = [
                key for key, entry in self.local_cache.items()
                if entry.access_count < 3
            ]

            for key in low_access_keys[:100]:  # 一次清理100个
                del self.local_cache[key]
                optimization_result['evicted_lru'] += len(low_access_keys[:100])

            logger.info(f"Evicted {len(low_access_keys[:100])} low access cache entries")

        return optimization_result


class CacheMiddleware:
    """缓存中间件"""

    def __init__(self, cache_manager: SmartCacheManager):
        self.cache_manager = cache_manager
        self.cacheable_patterns = [
            '/api/v1/matches/',
            '/api/v1/teams/',
            '/api/v1/predictions/',
            '/api/v1/odds/',
            '/api/v1/leagues/'
        ]
        self.excluded_patterns = [
            '/api/v1/auth/',
            '/api/v1/users/',
            '/api/v1/admin/'
        ]

    def should_cache(self, method: str, path: str) -> bool:
        """判断是否应该缓存"""
        if method != 'GET':
            return False

        # 检查排除模式
        for pattern in self.excluded_patterns:
            if pattern in path:
                return False

        # 检查缓存模式
        for pattern in self.cacheable_patterns:
            if pattern in path:
                return True

        return False

    def generate_cache_key(self, method: str, path: str, query_params: Dict[str, Any]) -> str:
        """生成缓存键"""
        # 创建基础键
        base_key = f"{method}:{path}"

        # 添加查询参数
        if query_params:
            # 对查询参数排序以确保一致性
            sorted_params = sorted(query_params.items())
            query_string = "&".join(f"{k}={v}" for k, v in sorted_params)
            base_key += f"?{query_string}"

        # 生成哈希以避免键过长
        hash_key = hashlib.md5(base_key.encode()).hexdigest()

        return f"cache:{hash_key}"

    async def get_cached_response(self, method: str, path: str,
                                  query_params: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """获取缓存的响应"""
        if not self.should_cache(method, path):
            return None

        cache_key = self.generate_cache_key(method, path, query_params)
        return await self.cache_manager.get(cache_key)

    async def cache_response(self, method: str, path: str, query_params: Dict[str, Any],
                            response_data: Dict[str, Any], ttl: int = 300):
        """缓存响应数据"""
        if not self.should_cache(method, path):
            return

        cache_key = self.generate_cache_key(method, path, query_params)

        metadata = {
            'method': method,
            'path': path,
            'query_params': query_params,
            'cached_at': datetime.utcnow().isoformat()
        }

        await self.cache_manager.set(cache_key, response_data, ttl, metadata)


# 全局缓存管理器实例
_cache_manager: Optional[SmartCacheManager] = None
_cache_middleware: Optional[CacheMiddleware] = None


def get_cache_manager() -> Optional[SmartCacheManager]:
    """获取全局缓存管理器实例"""
    return _cache_manager


def get_cache_middleware() -> Optional[CacheMiddleware]:
    """获取全局缓存中间件实例"""
    return _cache_middleware


async def initialize_cache_system(redis_client: Optional[EnhancedRedisClient] = None) -> SmartCacheManager:
    """初始化缓存系统"""
    global _cache_manager, _cache_middleware

    cache_manager = SmartCacheManager(redis_client)
    cache_middleware = CacheMiddleware(cache_manager)

    _cache_manager = cache_manager
    _cache_middleware = cache_middleware

    # 注册一些预加载处理器
    cache_manager.register_preload_handler("/api/v1/matches/", _preload_matches)
    cache_manager.register_preload_handler("/api/v1/teams/", _preload_teams)

    logger.info("Smart cache system initialized")
    return cache_manager


async def _preload_matches(key: str) -> Optional[Dict[str, Any]]:
    """预加载比赛数据"""
    # 这里应该从数据库获取比赛数据
    # 暂时返回模拟数据
    return {
        "matches": [
            {"id": 1, "home_team": "Team A", "away_team": "Team B", "date": "2025-11-08"},
            {"id": 2, "home_team": "Team C", "away_team": "Team D", "date": "2025-11-09"}
        ]
    }


async def _preload_teams(key: str) -> Optional[Dict[str, Any]]:
    """预加载队伍数据"""
    # 这里应该从数据库获取队伍数据
    # 暂时返回模拟数据
    return {
        "teams": [
            {"id": 1, "name": "Team A", "league": "Premier League"},
            {"id": 2, "name": "Team B", "league": "Premier League"}
        ]
    }