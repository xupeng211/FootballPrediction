"""高性能缓存装饰器
High-Performance Cache Decorators.

提供异步缓存装饰器，支持TTL、键生成、并发保护等功能。
Provides async cache decorators with TTL support, key generation,
concurrency protection, and other features.

Author: Claude Code
Version: 1.0.0
"""

import asyncio
import functools
import inspect
import logging
from typing import Any, Optional, Union
from collections.abc import Callable

from .cache_main import RedisCache, get_cache, cache_key_builder

logger = logging.getLogger(__name__)


class CacheStampedeProtection:
    """缓存击穿保护.

    使用asyncio.Lock防止同一键的并发请求同时执行底层函数。
    Uses asyncio.Lock to prevent concurrent requests for the same key
    from executing the underlying function simultaneously.
    """

    def __init__(self):
        self._locks: dict[str, asyncio.Lock] = {}
        self._locks_lock = asyncio.Lock()

    async def get_lock(self, key: str) -> asyncio.Lock:
        """获取指定键的锁.

        Args:
            key: 缓存键

        Returns:
            asyncio.Lock: 对应的锁
        """
        async with self._locks_lock:
            if key not in self._locks:
                self._locks[key] = asyncio.Lock()
            return self._locks[key]

    async def cleanup(self):
        """清理未使用的锁."""
        async with self._locks_lock:
            # 清理未被引用的锁
            for key in list(self._locks.keys()):
                if not self._locks[key].locked():
                    del self._locks[key]


# 全局击穿保护实例
_stampede_protection = CacheStampedeProtection()


def cached(
    ttl: int = 300,
    namespace: str = "",
    key_builder: Optional[Callable] = None,
    unless: Optional[Callable] = None,
    prefix: str = "cache",
    stampede_protection: bool = True,
    cache_instance: Optional[RedisCache] = None,
):
    """高性能异步缓存装饰器.

    Args:
        ttl: 缓存过期时间（秒），默认300秒
        namespace: 缓存命名空间，用于分组相关缓存
        key_builder: 自定义键生成函数，签名为 func(*args, **kwargs) -> str
        unless: 条件函数，返回True时跳过缓存
        prefix: 缓存键前缀
        stampede_protection: 是否启用缓存击穿保护
        cache_instance: 自定义缓存实例，默认使用全局实例

    Returns:
        装饰后的函数

    Examples:
        >>> @cached(ttl=3600, namespace="predictions")
        >>> async def get_prediction(match_id: int):
        ...     # 耗时的预测计算
        ...     return prediction_result

        >>> @cached(ttl=600, key_builder=lambda id: f"user_profile:{id}")
        >>> async def get_user_profile(user_id: int):
        ...     # 获取用户资料
        ...     return profile_data
    """

    def decorator(func: Callable) -> Callable:
        # 确保函数是异步的
        if not inspect.iscoroutinefunction(func):
            raise TypeError(f"@cached装饰器只能用于异步函数: {func}")

        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            # 检查是否跳过缓存
            if unless and unless(*args, **kwargs):
                return await func(*args, **kwargs)

            # 生成缓存键
            if key_builder:
                cache_key = key_builder(*args, **kwargs)
            else:
                cache_key = _default_key_builder(
                    func, namespace, prefix, *args, **kwargs
                )

            # 获取缓存实例
            cache = cache_instance or await get_cache()

            # 尝试从缓存获取
            try:
                cached_result = await cache.get(cache_key)
                if cached_result is not None:
                    logger.debug(f"缓存命中: {cache_key}")
                    return cached_result
            except Exception as e:
                logger.warning(f"缓存读取失败 {cache_key}: {e}")

            logger.debug(f"缓存未命中: {cache_key}")

            # 缓存击穿保护
            if stampede_protection:
                lock = await _stampede_protection.get_lock(cache_key)
                async with lock:
                    # 再次尝试从缓存获取（可能在等待期间已被其他请求设置）
                    try:
                        cached_result = await cache.get(cache_key)
                        if cached_result is not None:
                            return cached_result
                    except Exception as e:
                        logger.warning(f"缓存二次读取失败 {cache_key}: {e}")

                    # 执行原函数
                    try:
                        result = await func(*args, **kwargs)

                        # 写入缓存
                        try:
                            await cache.set(cache_key, result, ttl)
                            logger.debug(f"缓存已设置: {cache_key} (TTL: {ttl}s)")
                        except Exception as e:
                            logger.warning(f"缓存写入失败 {cache_key}: {e}")

                        return result

                    except Exception as e:
                        logger.error(f"函数执行失败 {func.__name__}: {e}")
                        raise
            else:
                # 不使用击穿保护，直接执行
                try:
                    result = await func(*args, **kwargs)

                    # 写入缓存
                    try:
                        await cache.set(cache_key, result, ttl)
                        logger.debug(f"缓存已设置: {cache_key} (TTL: {ttl}s)")
                    except Exception as e:
                        logger.warning(f"缓存写入失败 {cache_key}: {e}")

                    return result

                except Exception as e:
                    logger.error(f"函数执行失败 {func.__name__}: {e}")
                    raise

        # 添加缓存控制方法
        wrapper.cache_key = functools.partial(
            _default_key_builder, func, namespace, prefix
        )
        wrapper.invalidate = functools.partial(
            _invalidate_cache, func, namespace, prefix, cache_instance
        )

        return wrapper

    return decorator


def _default_key_builder(
    func: Callable, namespace: str, prefix: str, *args, **kwargs
) -> str:
    """默认的缓存键生成器.

    Args:
        func: 被装饰的函数
        namespace: 命名空间
        prefix: 键前缀
        *args: 函数位置参数
        **kwargs: 函数关键字参数

    Returns:
        str: 缓存键
    """
    # 构建基础键
    parts = [prefix, func.__module__, func.__qualname__]

    if namespace:
        parts.insert(1, namespace)

    # 跳过第一个参数（通常是self或cls）
    func_args = args[1:] if args and hasattr(args[0], "__class__") else args

    # 生成参数键
    if func_args or kwargs:
        args_key = cache_key_builder("", *func_args, **kwargs)
        parts.append(args_key)

    return ":".join(parts)


async def _invalidate_cache(
    func: Callable,
    namespace: str,
    prefix: str,
    cache_instance: Optional[RedisCache],
    *args,
    **kwargs,
):
    """使缓存失效.

    Args:
        func: 被装饰的函数
        namespace: 命名空间
        prefix: 键前缀
        cache_instance: 缓存实例
        *args: 函数位置参数
        **kwargs: 函数关键字参数
    """
    try:
        cache = cache_instance or await get_cache()
        cache_key = _default_key_builder(func, namespace, prefix, *args, **kwargs)
        await cache.delete(cache_key)
        logger.info(f"缓存已失效: {cache_key}")
    except Exception as e:
        logger.error(f"缓存失效失败: {e}")


# 便捷装饰器
def cached_long(ttl: int = 3600, **kwargs):
    """长期缓存装饰器（1小时默认）.

    Args:
        ttl: 缓存时间，默认3600秒
        **kwargs: 其他缓存参数
    """
    return cached(ttl=ttl, **kwargs)


def cached_short(ttl: int = 60, **kwargs):
    """短期缓存装饰器（1分钟默认）.

    Args:
        ttl: 缓存时间，默认60秒
        **kwargs: 其他缓存参数
    """
    return cached(ttl=ttl, **kwargs)


def cached_medium(ttl: int = 300, **kwargs):
    """中期缓存装饰器（5分钟默认）.

    Args:
        ttl: 缓存时间，默认300秒
        **kwargs: 其他缓存参数
    """
    return cached(ttl=ttl, **kwargs)


# 类方法缓存装饰器
def cached_method(ttl: int = 300, namespace: Optional[str] = None, **kwargs):
    """类方法缓存装饰器.

    自动处理self参数，生成基于实例的缓存键.

    Args:
        ttl: 缓存时间
        namespace: 命名空间
        **kwargs: 其他缓存参数
    """

    def decorator(func: Callable) -> Callable:
        if not inspect.iscoroutinefunction(func):
            raise TypeError(f"@cached_method装饰器只能用于异步函数: {func}")

        @functools.wraps(func)
        async def wrapper(self, *args, **kwargs):
            # 生成实例特定的命名空间
            instance_namespace = f"{namespace or func.__name__}:{id(self)}"

            # 调用原始缓存装饰器
            inner_decorator = cached(ttl=ttl, namespace=instance_namespace, **kwargs)
            inner_func = inner_decorator(func)

            return await inner_func(self, *args, **kwargs)

        # 添加缓存控制方法
        wrapper.invalidate = lambda *args, **kwargs: _invalidate_cache(
            func,
            f"{namespace or func.__name__}:{id(self)}",
            "cache",
            None,
            self,
            *args,
            **kwargs,
        )

        return wrapper

    return decorator


# 批量缓存操作
class BatchCache:
    """批量缓存操作工具.

    提供批量获取、设置和删除操作，优化Redis操作性能。
    Provides batch get, set, and delete operations to optimize Redis performance.
    """

    def __init__(self, cache_instance: Optional[RedisCache] = None):
        self.cache = cache_instance

    async def get_many(self, keys: list[str]) -> dict[str, Any]:
        """批量获取缓存值.

        Args:
            keys: 缓存键列表

        Returns:
            dict: 键值对字典
        """
        if not self.cache:
            self.cache = await get_cache()

        results = {}
        try:
            redis_client = await self.cache._get_connection()
            values = await redis_client.mget(keys)

            for key, value in zip(keys, values, strict=False):
                if value is not None:
                    try:
                        results[key] = self.cache._deserialize(value.decode("utf-8"))
                    except Exception as e:
                        logger.warning(f"反序列化失败 {key}: {e}")

        except Exception as e:
            logger.error(f"批量获取缓存失败: {e}")

        return results

    async def set_many(self, items: dict[str, Any], ttl: int = 300) -> dict[str, bool]:
        """批量设置缓存值.

        Args:
            items: 键值对字典
            ttl: 过期时间

        Returns:
            dict: 设置结果字典
        """
        if not self.cache:
            self.cache = await get_cache()

        results = {}
        try:
            redis_client = await self.cache._get_connection()

            # 使用pipeline提高性能
            pipe = redis_client.pipeline()
            for key, value in items.items():
                try:
                    serialized_value = self.cache._serialize(value)
                    pipe.setex(key, ttl, serialized_value)
                except Exception as e:
                    results[key] = False
                    logger.warning(f"序列化失败 {key}: {e}")

            if pipe:
                await pipe.execute()
                for key in items:
                    if key not in results:
                        results[key] = True

        except Exception as e:
            logger.error(f"批量设置缓存失败: {e}")
            for key in items:
                if key not in results:
                    results[key] = False

        return results

    async def delete_many(self, keys: list[str]) -> dict[str, bool]:
        """批量删除缓存值.

        Args:
            keys: 缓存键列表

        Returns:
            dict: 删除结果字典
        """
        if not self.cache:
            self.cache = await get_cache()

        results = {}
        try:
            redis_client = await self.cache._get_connection()
            await redis_client.delete(*keys)

            # 简单的删除结果估算
            for key in keys:
                results[key] = True

        except Exception as e:
            logger.error(f"批量删除缓存失败: {e}")
            for key in keys:
                results[key] = False

        return results


# 便捷函数
async def invalidate_pattern(pattern: str, cache_instance: Optional[RedisCache] = None):
    """根据模式删除缓存.

    Args:
        pattern: 匹配模式
        cache_instance: 缓存实例
    """
    try:
        cache = cache_instance or await get_cache()
        redis_client = await cache._get_connection()

        # 获取匹配的键
        keys = []
        async for key in redis_client.scan_iter(match=pattern):
            keys.append(key)

        if keys:
            deleted_count = await redis_client.delete(*keys)
            logger.info(f"删除了 {deleted_count} 个匹配的缓存键: {pattern}")

    except Exception as e:
        logger.error(f"模式删除缓存失败 {pattern}: {e}")


# 缓存装饰器的便捷别名
async_cache = cached  # 向后兼容
cache = cached  # 简化别名
