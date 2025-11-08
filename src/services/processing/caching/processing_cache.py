"""
数据处理缓存管理 - 重写版本

提供数据处理的缓存功能，避免重复计算
Processing Cache Manager - Rewritten Version
"""

import hashlib
import json
import logging
from datetime import datetime, timedelta
from typing import Any

from redis.exceptions import RedisError


class ProcessingCache:
    """数据处理缓存管理器 - 简化版本

    提供内存和Redis缓存功能，避免重复计算
    """

    def __init__(self, redis_client=None):
        """初始化缓存管理器"""
        self.logger = logging.getLogger(f"processing.{self.__class__.__name__}")
        self.redis_client = redis_client
        self.cache_enabled = True
        self.default_ttl = 3600  # 1小时默认过期时间

        # 内存缓存作为备选方案
        self._memory_cache = {}
        self._memory_cache_timestamps = {}

    async def get(self, cache_key: str) -> Any | None:
        """获取缓存数据"""
        if not self.cache_enabled:
            return None

        try:
            # 优先从内存缓存获取
            memory_data = await self._get_from_memory(cache_key)
            if memory_data is not None:
                return memory_data

            # 尝试从Redis获取
            if self.redis_client:
                redis_data = await self._get_from_redis(cache_key)
                if redis_data is not None:
                    # 存入内存缓存
                    await self._set_memory_cache(cache_key, redis_data)
                    return redis_data

            return None

        except Exception as e:
            self.logger.warning(f"获取缓存失败 {cache_key}: {e}")
            return None

    async def set(self, cache_key: str, data: Any, ttl: int | None = None) -> bool:
        """设置缓存数据"""
        if not self.cache_enabled:
            return False

        try:
            success = True
            ttl = ttl or self.default_ttl

            # 存入内存缓存
            await self._set_memory_cache(cache_key, data, ttl)

            # 存入Redis缓存
            if self.redis_client:
                redis_success = await self._set_to_redis(cache_key, data, ttl)
                success = success and redis_success

            return success

        except Exception as e:
            self.logger.warning(f"设置缓存失败 {cache_key}: {e}")
            return False

    async def delete(self, cache_key: str) -> bool:
        """删除缓存数据"""
        try:
            success = True

            # 从内存缓存删除
            if cache_key in self._memory_cache:
                del self._memory_cache[cache_key]
            if cache_key in self._memory_cache_timestamps:
                del self._memory_cache_timestamps[cache_key]

            # 从Redis删除
            if self.redis_client:
                try:
                    await self.redis_client.delete(cache_key)
                except RedisError as e:
                    self.logger.warning(f"Redis删除失败 {cache_key}: {e}")
                    success = False

            return success

        except Exception as e:
            self.logger.warning(f"删除缓存失败 {cache_key}: {e}")
            return False

    async def clear(self, pattern: str | None = None) -> int:
        """清空缓存"""
        try:
            cleared_count = 0

            # 清空内存缓存
            if pattern:
                keys_to_delete = [
                    key for key in self._memory_cache.keys() if pattern in key
                ]
                for key in keys_to_delete:
                    del self._memory_cache[key]
                    if key in self._memory_cache_timestamps:
                        del self._memory_cache_timestamps[key]
                    cleared_count += 1
            else:
                cleared_count += len(self._memory_cache)
                self._memory_cache.clear()
                self._memory_cache_timestamps.clear()

            # 清空Redis缓存
            if self.redis_client:
                try:
                    if pattern:
                        # 使用SCAN查找匹配的键
                        cursor = 0
                        while True:
                            cursor, keys = await self.redis_client.scan(
                                cursor, match=f"*{pattern}*", count=100
                            )
                            if keys:
                                await self.redis_client.delete(*keys)
                                cleared_count += len(keys)
                            if cursor == 0:
                                break
                    else:
                        # 清空所有缓存（谨慎使用）
                        await self.redis_client.flushdb()
                        cleared_count += 100  # 估算值
                except RedisError as e:
                    self.logger.warning(f"Redis清空失败: {e}")

            return cleared_count

        except Exception as e:
            self.logger.error(f"清空缓存失败: {e}")
            return 0

    async def get_or_compute(
        self, cache_key: str, compute_func, ttl: int | None = None, *args, **kwargs
    ) -> Any:
        """获取缓存数据或计算新数据"""
        # 尝试从缓存获取
        cached_data = await self.get(cache_key)
        if cached_data is not None:
            return cached_data

        # 计算新数据
        try:
            if callable(compute_func):
                if args or kwargs:
                    new_data = await compute_func(*args, **kwargs)
                else:
                    new_data = await compute_func()
            else:
                new_data = compute_func

            # 存入缓存
            await self.set(cache_key, new_data, ttl)

            return new_data

        except Exception as e:
            self.logger.error(f"计算数据失败 {cache_key}: {e}")
            raise

    def generate_cache_key(self, prefix: str, *args, **kwargs) -> str:
        """生成缓存键"""
        try:
            # 组合所有参数
            key_parts = [prefix]
            key_parts.extend(str(arg) for arg in args)

            # 处理关键字参数
            if kwargs:
                sorted_kwargs = sorted(kwargs.items())
                key_parts.append(json.dumps(sorted_kwargs, sort_keys=True, default=str))

            # 生成MD5哈希
            key_string = ":".join(key_parts)
            hash_key = hashlib.md5(key_string.encode()).hexdigest()

            return f"{prefix}:{hash_key}"

        except Exception as e:
            self.logger.warning(f"生成缓存键失败: {e}")
            return f"{prefix}:{datetime.utcnow().timestamp()}"

    async def _get_from_memory(self, cache_key: str) -> Any | None:
        """从内存缓存获取数据"""
        try:
            # 检查是否过期
            if cache_key in self._memory_cache_timestamps:
                timestamp = self._memory_cache_timestamps[cache_key]
                if datetime.utcnow() - timestamp > timedelta(seconds=self.default_ttl):
                    del self._memory_cache[cache_key]
                    del self._memory_cache_timestamps[cache_key]
                    return None

            return self._memory_cache.get(cache_key)

        except Exception:
            return None

    async def _set_memory_cache(
        self, cache_key: str, data: Any, ttl: int | None = None
    ) -> None:
        """设置内存缓存"""
        try:
            self._memory_cache[cache_key] = data
            self._memory_cache_timestamps[cache_key] = datetime.utcnow()

            # 限制内存缓存大小
            if len(self._memory_cache) > 1000:  # 最大缓存条目数
                # 删除最旧的条目
                oldest_key = min(
                    self._memory_cache_timestamps.keys(),
                    key=lambda k: self._memory_cache_timestamps[k],
                )
                del self._memory_cache[oldest_key]
                del self._memory_cache_timestamps[oldest_key]

        except Exception as e:
            self.logger.warning(f"设置内存缓存失败: {e}")

    async def _get_from_redis(self, cache_key: str) -> Any | None:
        """从Redis获取数据"""
        try:
            data = await self.redis_client.get(cache_key)
            if data:
                return json.loads(data.decode("utf-8"))
            return None

        except (RedisError, json.JSONDecodeError, UnicodeDecodeError) as e:
            self.logger.warning(f"Redis获取失败 {cache_key}: {e}")
            return None

    async def _set_to_redis(self, cache_key: str, data: Any, ttl: int) -> bool:
        """设置Redis缓存"""
        try:
            serialized_data = json.dumps(data, default=str)
            await self.redis_client.setex(cache_key, ttl, serialized_data)
            return True

        except (RedisError, json.JSONEncodeError, TypeError) as e:
            self.logger.warning(f"Redis设置失败 {cache_key}: {e}")
            return False

    async def get_cache_stats(self) -> dict[str, Any]:
        """获取缓存统计信息"""
        try:
            stats = {
                "memory_cache_size": len(self._memory_cache),
                "cache_enabled": self.cache_enabled,
                "default_ttl": self.default_ttl,
                "has_redis_client": self.redis_client is not None,
            }

            # Redis统计
            if self.redis_client:
                try:
                    info = await self.redis_client.info()
                    stats["redis_memory_used"] = info.get("used_memory_human", "N/A")
                    stats["redis_connected_clients"] = info.get("connected_clients", 0)
                    stats["redis_keyspace_hits"] = info.get("keyspace_hits", 0)
                    stats["redis_keyspace_misses"] = info.get("keyspace_misses", 0)
                except RedisError:
                    stats["redis_status"] = "error"
                else:
                    stats["redis_status"] = "connected"
            else:
                stats["redis_status"] = "not_configured"

            return stats

        except Exception as e:
            self.logger.error(f"获取缓存统计失败: {e}")
            return {"error": str(e)}

    async def enable_cache(self) -> None:
        """启用缓存"""
        self.cache_enabled = True
        self.logger.info("缓存已启用")

    async def disable_cache(self) -> None:
        """禁用缓存"""
        self.cache_enabled = False
        self.logger.info("缓存已禁用")

    async def cleanup_expired(self) -> int:
        """清理过期的内存缓存"""
        try:
            current_time = datetime.utcnow()
            expired_keys = []

            for key, timestamp in self._memory_cache_timestamps.items():
                if current_time - timestamp > timedelta(seconds=self.default_ttl):
                    expired_keys.append(key)

            for key in expired_keys:
                if key in self._memory_cache:
                    del self._memory_cache[key]
                del self._memory_cache_timestamps[key]

            return len(expired_keys)

        except Exception as e:
            self.logger.error(f"清理过期缓存失败: {e}")
            return 0

    def __repr__(self) -> str:
        """字符串表示"""
        return (
            f"ProcessingCache(enabled={self.cache_enabled}, "
            f"memory_size={len(self._memory_cache)}, "
            f"has_redis={self.redis_client is not None})"
        )

    async def __aenter__(self):
        """异步上下文管理器入口"""
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """异步上下文管理器出口"""
        # 清理资源
        await self.cleanup_expired()


# 便利函数
async def create_processing_cache(redis_client=None) -> ProcessingCache:
    """创建处理缓存实例"""
    return ProcessingCache(redis_client=redis_client)


# 缓存装饰器
def cache_result(ttl: int = 3600, key_prefix: str = None):
    """缓存结果装饰器"""

    def decorator(func):
        async def wrapper(*args, **kwargs):
            # 获取缓存实例
            cache = getattr(wrapper, "_cache_instance", None)
            if not cache:
                return await func(*args, **kwargs)

            # 生成缓存键
            prefix = key_prefix or f"{func.__module__}.{func.__name__}"
            cache_key = cache.generate_cache_key(prefix, *args, **kwargs)

            # 尝试获取缓存
            result = await cache.get(cache_key)
            if result is not None:
                return result

            # 计算结果
            result = await func(*args, **kwargs)

            # 存入缓存
            await cache.set(cache_key, result, ttl)
            return result

        # 设置缓存实例的方法
        def set_cache_instance(cache_instance: ProcessingCache):
            wrapper._cache_instance = cache_instance

        wrapper.set_cache_instance = set_cache_instance
        wrapper.__name__ = func.__name__
        wrapper.__doc__ = func.__doc__

        return wrapper

    return decorator
