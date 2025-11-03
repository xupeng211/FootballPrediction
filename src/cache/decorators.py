"""
缓存装饰器模块
Cache Decorators Module

提供企业级缓存装饰器，支持同步和异步函数、多级缓存、智能失效等功能。
"""

import asyncio
import functools
import hashlib
import inspect
import json
import logging
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from typing import Any, TypeVar

try:
    from .consistency_manager import get_consistency_manager
except ImportError:
    # 如果一致性管理器不可用，提供备用实现
    def get_consistency_manager():
        return None


logger = logging.getLogger(__name__)

F = TypeVar("F", bound=Callable[..., Any])
AsyncF = TypeVar("AsyncF", bound=Callable[..., Awaitable[Any]])


@dataclass
class CacheConfig:
    """缓存配置"""

    ttl: int = 3600  # 生存时间（秒）
    key_prefix: str = "cache"
    version: str = "v1"
    cache_store: str = "default"
    use_consistency_manager: bool = True
    invalidate_on_update: bool = False
    key_builder: Callable | None = None
    condition: Callable[..., bool] | None = None
    unless: Callable[..., bool] | None = None
    max_size: int | None = None


class CacheKeyBuilder:
    """缓存键构建器"""

    @staticmethod
    def build_key(
        func_name: str,
        args: tuple,
        kwargs: dict,
        prefix: str = "cache",
        version: str = "v1",
    ) -> str:
        """
        构建缓存键

        Args:
            func_name: 函数名称
            args: 位置参数
            kwargs: 关键字参数
            prefix: 键前缀
            version: 版本号

        Returns:
            缓存键
        """
        # 创建参数指纹
        args_hash = CacheKeyBuilder._hash_args(args, kwargs)

        # 构建键
        key_parts = [prefix, version, func_name, args_hash]
        return ":".join(str(part) for part in key_parts)

    @staticmethod
    def _hash_args(args: tuple, kwargs: dict) -> str:
        """哈希化参数"""
        try:
            # 尝试JSON序列化
            serializable = []

            # 处理位置参数
            for arg in args:
                if CacheKeyBuilder._is_json_serializable(arg):
                    serializable.append(arg)
                else:
                    serializable.append(str(arg))

            # 处理关键字参数
            for k, v in sorted(kwargs.items()):
                if CacheKeyBuilder._is_json_serializable(v):
                    serializable.append((k, v))
                else:
                    serializable.append((k, str(v)))

            # 生成哈希
            json_str = json.dumps(serializable, sort_keys=True, default=str)
            return hashlib.md5(json_str.encode()).hexdigest()[:16]

        except Exception:
            # 备用方案：简单字符串哈希
            args_str = str(args) + str(sorted(kwargs.items()))
            return hashlib.md5(args_str.encode()).hexdigest()[:16]

    @staticmethod
    def _is_json_serializable(obj: Any) -> bool:
        """检查对象是否可以JSON序列化"""
        try:
            json.dumps(obj)
            return True
        except (TypeError, ValueError):
            return False


def cached(
    ttl: int = 3600,
    key_prefix: str = "cache",
    version: str = "v1",
    cache_store: str = "default",
    use_consistency_manager: bool = True,
    invalidate_on_update: bool = False,
    key_builder: Callable | None = None,
    condition: Callable[..., bool] | None = None,
    unless: Callable[..., bool] | None = None,
    max_size: int | None = None,
) -> Callable:
    """
    缓存装饰器 - 支持同步和异步函数

    Args:
        ttl: 生存时间（秒）
        key_prefix: 缓存键前缀
        version: 缓存版本
        cache_store: 缓存存储名称
        use_consistency_manager: 是否使用一致性管理器
        invalidate_on_update: 是否在更新时失效
        key_builder: 自定义键构建器
        condition: 缓存条件函数，返回True时缓存
        unless: 排除条件函数，返回True时不缓存
        max_size: 最大缓存大小

    Returns:
        装饰器函数
    """
    config = CacheConfig(
        ttl=ttl,
        key_prefix=key_prefix,
        version=version,
        cache_store=cache_store,
        use_consistency_manager=use_consistency_manager,
        invalidate_on_update=invalidate_on_update,
        key_builder=key_builder,
        condition=condition,
        unless=unless,
        max_size=max_size,
    )

    def decorator(func: F) -> F:
        # 获取函数信息
        is_async = inspect.iscoroutinefunction(func)
        func_name = f"{func.__module__}.{func.__qualname__}"

        if is_async:
            return _async_cached_wrapper(func, func_name, config)  # type: ignore
        else:
            return _sync_cached_wrapper(func, func_name, config)  # type: ignore

    return decorator


def _sync_cached_wrapper(func: F, func_name: str, config: CacheConfig) -> F:
    """同步函数缓存包装器"""

    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        # 检查条件
        if config.condition and not config.condition(*args, **kwargs):
            return func(*args, **kwargs)

        if config.unless and config.unless(*args, **kwargs):
            return func(*args, **kwargs)

        # 构建缓存键
        if config.key_builder:
            cache_key = config.key_builder(*args, **kwargs)
        else:
            cache_key = CacheKeyBuilder.build_key(
                func_name, args, kwargs, config.key_prefix, config.version
            )

        try:
            # 尝试从缓存获取
            if config.use_consistency_manager:
                manager = get_consistency_manager()
                entry = asyncio.run(
                    manager.get_cache_entry(cache_key, config.cache_store)
                )
                if entry and entry.value is not None:
                    logger.debug(f"缓存命中: {cache_key}")
                    return entry.value

            # 缓存未命中，执行函数
            logger.debug(f"缓存未命中: {cache_key}")
            result = func(*args, **kwargs)

            # 存储到缓存
            if config.use_consistency_manager:
                asyncio.run(
                    manager.set_cache_entry(
                        cache_key, result, config.ttl, config.cache_store
                    )
                )

            logger.debug(f"缓存存储: {cache_key}")
            return result

        except Exception as e:
            logger.error(f"缓存装饰器错误: {cache_key}, 错误: {e}")
            # 缓存错误时直接执行函数
            return func(*args, **kwargs)

    return wrapper  # type: ignore


def _async_cached_wrapper(func: AsyncF, func_name: str, config: CacheConfig) -> AsyncF:
    """异步函数缓存包装器"""

    @functools.wraps(func)
    async def wrapper(*args, **kwargs):
        # 检查条件
        if config.condition and not config.condition(*args, **kwargs):
            return await func(*args, **kwargs)

        if config.unless and config.unless(*args, **kwargs):
            return await func(*args, **kwargs)

        # 构建缓存键
        if config.key_builder:
            cache_key = config.key_builder(*args, **kwargs)
        else:
            cache_key = CacheKeyBuilder.build_key(
                func_name, args, kwargs, config.key_prefix, config.version
            )

        try:
            # 尝试从缓存获取
            if config.use_consistency_manager:
                manager = get_consistency_manager()
                entry = await manager.get_cache_entry(cache_key, config.cache_store)
                if entry and entry.value is not None:
                    logger.debug(f"缓存命中: {cache_key}")
                    return entry.value

            # 缓存未命中，执行函数
            logger.debug(f"缓存未命中: {cache_key}")
            result = await func(*args, **kwargs)

            # 存储到缓存
            if config.use_consistency_manager:
                await manager.set_cache_entry(
                    cache_key, result, config.ttl, config.cache_store
                )

            logger.debug(f"缓存存储: {cache_key}")
            return result

        except Exception as e:
            logger.error(f"缓存装饰器错误: {cache_key}, 错误: {e}")
            # 缓存错误时直接执行函数
            return await func(*args, **kwargs)

    return wrapper  # type: ignore


def cache_invalidate(
    pattern: str = None, keys: list[str] = None, reason: str = "decorator_invalidation"
) -> Callable:
    """
    缓存失效装饰器

    Args:
        pattern: 失效模式
        keys: 要失效的键列表
        reason: 失效原因

    Returns:
        装饰器函数
    """

    def decorator(func: F) -> F:
        is_async = inspect.iscoroutinefunction(func)

        if is_async:

            @functools.wraps(func)
            async def async_wrapper(*args, **kwargs):
                result = await func(*args, **kwargs)

                try:
                    manager = get_consistency_manager()
                    if keys:
                        await manager.invalidate_cache(keys, reason)
                    if pattern:
                        await manager.invalidate_pattern(pattern, reason)
                    logger.debug(f"缓存失效: keys={keys}, pattern={pattern}")
                except Exception as e:
                    logger.error(f"缓存失效错误: {e}")

                return result

            return async_wrapper  # type: ignore
        else:

            @functools.wraps(func)
            def sync_wrapper(*args, **kwargs):
                result = func(*args, **kwargs)

                try:
                    manager = get_consistency_manager()
                    if keys:
                        asyncio.run(manager.invalidate_cache(keys, reason))
                    if pattern:
                        asyncio.run(manager.invalidate_pattern(pattern, reason))
                    logger.debug(f"缓存失效: keys={keys}, pattern={pattern}")
                except Exception as e:
                    logger.error(f"缓存失效错误: {e}")

                return result

            return sync_wrapper  # type: ignore

    return decorator


def multi_cached(levels: list[dict[str, Any]], fallback: bool = True) -> Callable:
    """
    多级缓存装饰器

    Args:
        levels: 缓存级别配置列表
        fallback: 是否启用降级

    Returns:
        装饰器函数
    """

    def decorator(func: F) -> F:
        is_async = inspect.iscoroutinefunction(func)
        func_name = f"{func.__module__}.{func.__qualname__}"

        if is_async:

            @functools.wraps(func)
            async def async_wrapper(*args, **kwargs):
                # 按级别尝试获取缓存
                for i, level_config in enumerate(levels):
                    try:
                        config = CacheConfig(**level_config)
                        cache_key = CacheKeyBuilder.build_key(
                            func_name, args, kwargs, config.key_prefix, config.version
                        )

                        manager = get_consistency_manager()
                        entry = await manager.get_cache_entry(
                            cache_key, config.cache_store
                        )
                        if entry and entry.value is not None:
                            logger.debug(f"L{i + 1}缓存命中: {cache_key}")
                            return entry.value
                    except Exception as e:
                        logger.warning(f"L{i + 1}缓存获取失败: {e}")
                        if not fallback:
                            break

                # 所有缓存都未命中，执行函数
                logger.debug("多级缓存全部未命中，执行函数")
                result = await func(*args, **kwargs)

                # 存储到所有缓存级别
                for i, level_config in enumerate(levels):
                    try:
                        config = CacheConfig(**level_config)
                        cache_key = CacheKeyBuilder.build_key(
                            func_name, args, kwargs, config.key_prefix, config.version
                        )

                        manager = get_consistency_manager()
                        await manager.set_cache_entry(
                            cache_key, result, config.ttl, config.cache_store
                        )
                        logger.debug(f"L{i + 1}缓存存储: {cache_key}")
                    except Exception as e:
                        logger.warning(f"L{i + 1}缓存存储失败: {e}")

                return result

            return async_wrapper  # type: ignore
        else:

            @functools.wraps(func)
            def sync_wrapper(*args, **kwargs):
                # 按级别尝试获取缓存
                for i, level_config in enumerate(levels):
                    try:
                        config = CacheConfig(**level_config)
                        cache_key = CacheKeyBuilder.build_key(
                            func_name, args, kwargs, config.key_prefix, config.version
                        )

                        manager = get_consistency_manager()
                        entry = asyncio.run(
                            manager.get_cache_entry(cache_key, config.cache_store)
                        )
                        if entry and entry.value is not None:
                            logger.debug(f"L{i + 1}缓存命中: {cache_key}")
                            return entry.value
                    except Exception as e:
                        logger.warning(f"L{i + 1}缓存获取失败: {e}")
                        if not fallback:
                            break

                # 所有缓存都未命中，执行函数
                logger.debug("多级缓存全部未命中，执行函数")
                result = func(*args, **kwargs)

                # 存储到所有缓存级别
                for i, level_config in enumerate(levels):
                    try:
                        config = CacheConfig(**level_config)
                        cache_key = CacheKeyBuilder.build_key(
                            func_name, args, kwargs, config.key_prefix, config.version
                        )

                        manager = get_consistency_manager()
                        asyncio.run(
                            manager.set_cache_entry(
                                cache_key, result, config.ttl, config.cache_store
                            )
                        )
                        logger.debug(f"L{i + 1}缓存存储: {cache_key}")
                    except Exception as e:
                        logger.warning(f"L{i + 1}缓存存储失败: {e}")

                return result

            return sync_wrapper  # type: ignore

    return decorator


# 预定义配置
CACHE_CONFIGS = {
    "short_term": {"ttl": 300, "key_prefix": "short"},  # 5分钟
    "medium_term": {"ttl": 3600, "key_prefix": "medium"},  # 1小时
    "long_term": {"ttl": 86400, "key_prefix": "long"},  # 24小时
    "prediction": {"ttl": 1800, "key_prefix": "prediction"},  # 30分钟
    "user_session": {"ttl": 7200, "key_prefix": "session"},  # 2小时
}


# 便捷装饰器
def short_cached(**kwargs):
    return cached(**{**CACHE_CONFIGS["short_term"], **kwargs})


def medium_cached(**kwargs):
    return cached(**{**CACHE_CONFIGS["medium_term"], **kwargs})


def long_cached(**kwargs):
    return cached(**{**CACHE_CONFIGS["long_term"], **kwargs})


def prediction_cached(**kwargs):
    return cached(**{**CACHE_CONFIGS["prediction"], **kwargs})


# 向后兼容装饰器类
class CacheDecorator:
    """向后兼容缓存装饰器类"""

    def __init__(self, ttl: int = 3600, key_prefix: str = "cache"):
        self.ttl = ttl
        self.key_prefix = key_prefix

    def __call__(self, func: F) -> F:
        return cached(ttl=self.ttl, key_prefix=self.key_prefix)(func)


class UserCacheDecorator:
    """用户缓存装饰器"""

    def __init__(self, ttl: int = 1800):
        self.ttl = ttl

    def __call__(self, func: F) -> F:
        def user_key_builder(*args, **kwargs):
            # 尝试从参数中提取用户ID
            user_id = None
            if args:
                user_id = args[0] if isinstance(args[0], (int, str)) else None
            if not user_id and "user_id" in kwargs:
                user_id = kwargs["user_id"]
            if not user_id:
                raise ValueError("无法从函数参数中提取用户ID")

            func_name = f"{func.__module__}.{func.__qualname__}"
            return f"user:{user_id}:{func_name}"

        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            # 检查是否有用户ID
            if not args and "user_id" not in kwargs:
                raise ValueError("用户缓存装饰器需要用户ID参数")

            # 使用缓存装饰器包装函数
            cached_func = cached(
                ttl=self.ttl, key_prefix="user_cache", key_builder=user_key_builder
            )(func)
            return cached_func(*args, **kwargs)

        return wrapper


class InvalidateCacheDecorator:
    """缓存失效装饰器"""

    def __init__(self, patterns: list[str] = None, keys: list[str] = None):
        self.patterns = patterns or []
        self.keys = keys or []

    def __call__(self, func: F) -> F:
        return cache_invalidate(
            pattern=self.patterns[0] if self.patterns else None, keys=self.keys
        )(func)


# 向后兼容装饰器函数
def cache_with_ttl(ttl: int = 3600, key_prefix: str = "cache"):
    """带TTL的缓存装饰器"""
    return cached(ttl=ttl, key_prefix=key_prefix)


def cache_result(ttl: int = 3600):
    """缓存结果装饰器"""
    return cached(ttl=ttl)


def cache_by_user(ttl: int = 1800):
    """按用户缓存装饰器"""
    return UserCacheDecorator(ttl=ttl)


def cache_user_predictions(ttl: int = 900):
    """缓存用户预测装饰器"""
    return cached(ttl=ttl, key_prefix="user_predictions")


def cache_match_data(ttl: int = 1800):
    """缓存比赛数据装饰器"""
    return cached(ttl=ttl, key_prefix="match_data")


def cache_team_stats(ttl: int = 3600):
    """缓存球队统计装饰器"""
    return cached(ttl=ttl, key_prefix="team_stats")
