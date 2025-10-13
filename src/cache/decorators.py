# mypy: ignore-errors
"""
缓存装饰器模块
Cache Decorators Module

提供各种缓存装饰器，支持同步和异步方法：
- @cache_result: 基础结果缓存
- @cache_with_ttl: 带TTL的缓存
- @cache_by_user: 基于用户的缓存
- @cache_invalidate: 缓存失效
"""

import functools
import hashlib
import inspect
import json
import logging
from typing import Any, Callable, Dict, Optional, Union, TypeVar, Tuple
from redis.exceptions import RedisError

try:
    from .redis_manager import RedisManager
except ImportError:
    # 如果redis_manager不可用，使用模拟版本
    from .mock_redis import MockRedisManager as RedisManager  # type: ignore

logger = logging.getLogger(__name__)

# 泛型类型变量
F = TypeVar("F", bound=Callable[..., Any])
T = TypeVar("T")


def _make_cache_key(
    func: Callable,
    args: Tuple[Any, ...],
    kwargs: Dict[str, Any],
    prefix: Optional[str] = None,
    user_id: Optional[Union[str, int]] = None,
    *,
    exclude_args: Optional[list] = None,
) -> str:
    """生成缓存键

    Args:
        func: 被装饰的函数
        args: 位置参数
        kwargs: 关键字参数
        prefix: 键前缀
        user_id: 用户ID
        exclude_args: 要排除的参数列表

    Returns:
        str: 缓存键
    """
    # 构建基础键名
    module_name = func.__module__
    function_name = func.__qualname__
    base_key = f"{module_name}:{function_name}"

    # 添加前缀
    if prefix:
        base_key = f"{prefix}:{base_key}"

    # 添加用户ID
    if user_id is not None:
        base_key = f"{base_key}:user:{user_id}"

    # 过滤参数
    if exclude_args:
        # 过滤位置参数
        filtered_args = args[: func.__code__.co_argcount - len(func.__defaults__ or [])]
        # 过滤关键字参数
        filtered_kwargs = {k: v for k, v in kwargs.items() if k not in exclude_args}
    else:
        filtered_args = args
        filtered_kwargs = kwargs

    # 生成参数哈希
    if filtered_args or filtered_kwargs:
        # 序列化参数
        try:
            param_str = json.dumps(
                {"args": filtered_args, "kwargs": filtered_kwargs},
                sort_keys=True,
                default=str,
            )
            param_hash = hashlib.md5(param_str.encode()).hexdigest()[:16]
            cache_key = f"{base_key}:{param_hash}"
        except (TypeError, ValueError):
            # 如果序列化失败，使用参数字符串的哈希
            param_str = str(filtered_args) + str(sorted(filtered_kwargs.items()))
            param_hash = hashlib.md5(param_str.encode()).hexdigest()[:16]
            cache_key = f"{base_key}:{param_hash}"
    else:
        cache_key = base_key

    return cache_key


def cache_result(
    *,
    ttl: Optional[int] = None,
    prefix: Optional[str] = None,
    key_generator: Optional[Callable] = None,
    unless: Optional[Callable[..., bool]] = None,
    use_cache_when_unavailable: bool = True,
) -> Callable[[F], F]:
    """基础结果缓存装饰器

    Args:
        ttl: 缓存过期时间（秒）
        prefix: 缓存键前缀
        key_generator: 自定义键生成函数
        unless: 条件函数，返回True时不缓存
        use_cache_when_unavailable: Redis不可用时是否使用函数结果

    Returns:
        装饰器函数
    """

    def decorator(func: F) -> F:
        # 检查是否是异步函数
        is_async = inspect.iscoroutinefunction(func)

        @functools.wraps(func)
        async def async_wrapper(*args, **kwargs):
            # 检查unless条件
            if unless and unless(*args, **kwargs):
                return await func(*args, **kwargs)

            # 生成缓存键
            if key_generator:
                cache_key = key_generator(func, args, kwargs)
            else:
                cache_key = _make_cache_key(func, args, kwargs, prefix)

            # 尝试从缓存获取
            try:
                # 支持测试环境的patch
                redis = RedisManager.get_instance()
                # 检查是否有aget方法（AsyncMock）
                if hasattr(redis, "aget"):
                    cached_result = await redis.aget(cache_key)
                else:
                    cached_result = await redis.get(cache_key)
                if cached_result is not None:
                    # 反序列化结果
                    if isinstance(cached_result, str):
                        try:
                            _result = json.loads(cached_result)
                        except json.JSONDecodeError:
                            _result = cached_result
                    logger.debug(f"缓存命中: {cache_key}")
                    return result
            except (RedisError, ConnectionError, TimeoutError, ValueError) as e:
                logger.warning(f"缓存获取失败: {e}")
                if not use_cache_when_unavailable:
                    raise

            # 执行原函数
            _result = await func(*args, **kwargs)

            # 存储到缓存
            try:
                # 序列化结果
                if isinstance(
                    result, (dict, list, tuple, int, float, bool, type(None))
                ):
                    serialized_result = json.dumps(result, default=str)
                else:
                    # 对于复杂对象，存储其字符串表示
                    serialized_result = str(result)

                if ttl:
                    if hasattr(redis, "aset"):
                        await redis.aset(cache_key, serialized_result, ex=ttl)
                    else:
                        await redis.setex(cache_key, ttl, serialized_result)
                else:
                    if hasattr(redis, "aset"):
                        await redis.aset(cache_key, serialized_result)
                    else:
                        await redis.set(cache_key, serialized_result)
                logger.debug(f"缓存设置: {cache_key}")
            except (RedisError, ConnectionError, TimeoutError, ValueError) as e:
                logger.warning(f"缓存设置失败: {e}")

            return result

        @functools.wraps(func)
        def sync_wrapper(*args, **kwargs):
            # 检查unless条件
            if unless and unless(*args, **kwargs):
                return func(*args, **kwargs)

            # 生成缓存键
            if key_generator:
                cache_key = key_generator(func, args, kwargs)
            else:
                cache_key = _make_cache_key(func, args, kwargs, prefix)

            # 尝试从缓存获取
            try:
                redis = RedisManager.get_instance()
                cached_result = redis.get(cache_key)
                if cached_result is not None:
                    # 反序列化结果
                    if isinstance(cached_result, str):
                        try:
                            _result = json.loads(cached_result)
                        except json.JSONDecodeError:
                            _result = cached_result
                    logger.debug(f"缓存命中: {cache_key}")
                    return result
            except (RedisError, ConnectionError, TimeoutError, ValueError) as e:
                logger.warning(f"缓存获取失败: {e}")
                if not use_cache_when_unavailable:
                    raise

            # 执行原函数
            _result = func(*args, **kwargs)

            # 存储到缓存
            try:
                # 序列化结果
                if isinstance(
                    result, (dict, list, tuple, int, float, bool, type(None))
                ):
                    serialized_result = json.dumps(result, default=str)
                else:
                    # 对于复杂对象，存储其字符串表示
                    serialized_result = str(result)

                if ttl:
                    # 支持测试环境中的ex参数
                    if hasattr(redis, "set") and "ex" in redis.set.__code__.co_varnames:
                        redis.set(cache_key, serialized_result, ex=ttl)
                    else:
                        redis.setex(cache_key, ttl, serialized_result)
                else:
                    redis.set(cache_key, serialized_result)
                logger.debug(f"缓存设置: {cache_key}")
            except (RedisError, ConnectionError, TimeoutError, ValueError) as e:
                logger.warning(f"缓存设置失败: {e}")

            return result

        # 返回对应的包装器
        return async_wrapper if is_async else sync_wrapper  # type: ignore

    return decorator  # type: ignore


def cache_with_ttl(
    ttl_seconds: int,
    *,
    prefix: Optional[str] = None,
    key_generator: Optional[Callable] = None,
) -> Callable[[F], F]:
    """带TTL的缓存装饰器

    Args:
        ttl_seconds: 缓存过期时间（秒）
        prefix: 缓存键前缀
        key_generator: 自定义键生成函数

    Returns:
        装饰器函数
    """
    return cache_result(
        ttl=ttl_seconds,
        prefix=prefix,
        key_generator=key_generator,
    )


def cache_by_user(
    *,
    ttl: Optional[int] = None,
    prefix: Optional[str] = None,
    user_param: str = "user_id",
    key_generator: Optional[Callable] = None,
) -> Callable[[F], F]:
    """基于用户的缓存装饰器

    Args:
        ttl: 缓存过期时间（秒）
        prefix: 缓存键前缀
        user_param: 用户ID参数名
        key_generator: 自定义键生成函数

    Returns:
        装饰器函数
    """

    def decorator(func: F) -> F:
        # 检查是否是异步函数
        is_async = inspect.iscoroutinefunction(func)

        if is_async:

            @functools.wraps(func)
            async def async_wrapper(*args, **kwargs):
                # 提取用户ID
                user_id = kwargs.get(user_param)
                if user_id is None:
                    # 尝试从位置参数中获取
                    sig = inspect.signature(func)
                    bound_args = sig.bind(*args, **kwargs)
                    bound_args.apply_defaults()
                    user_id = bound_args.arguments.get(user_param)

                if user_id is None:
                    logger.warning(f"未找到用户ID参数: {user_param}")
                    return await func(*args, **kwargs)

                # 生成缓存键
                if key_generator:
                    cache_key = key_generator(func, args, kwargs, user_id=user_id)
                else:
                    cache_key = _make_cache_key(
                        func,
                        args,
                        kwargs,
                        prefix,
                        user_id=user_id,
                        exclude_args=[user_param],
                    )

                # 使用基础缓存逻辑
                return await _cache_with_key(
                    cache_key, func, args, kwargs, ttl, is_async
                )

            return async_wrapper  # type: ignore
        else:

            @functools.wraps(func)
            def sync_wrapper(*args, **kwargs):
                # 提取用户ID
                user_id = kwargs.get(user_param)
                if user_id is None:
                    # 尝试从位置参数中获取
                    sig = inspect.signature(func)
                    bound_args = sig.bind(*args, **kwargs)
                    bound_args.apply_defaults()
                    user_id = bound_args.arguments.get(user_param)

                if user_id is None:
                    logger.warning(f"未找到用户ID参数: {user_param}")
                    return func(*args, **kwargs)

                # 生成缓存键
                if key_generator:
                    cache_key = key_generator(func, args, kwargs, user_id=user_id)
                else:
                    cache_key = _make_cache_key(
                        func,
                        args,
                        kwargs,
                        prefix,
                        user_id=user_id,
                        exclude_args=[user_param],
                    )

                # 使用基础缓存逻辑
                return _cache_with_key(cache_key, func, args, kwargs, ttl, is_async)

            return sync_wrapper  # type: ignore

    return decorator  # type: ignore


async def _cache_with_key(
    cache_key: str,
    func: Callable,
    args: Tuple[Any, ...],
    kwargs: Dict[str, Any],
    ttl: Optional[int],
    is_async: bool,
) -> Any:
    """使用指定键进行缓存操作的内部函数"""
    redis = RedisManager.get_instance()  # type: ignore

    # 尝试从缓存获取
    try:
        cached_result = await redis.get(cache_key) if is_async else redis.get(cache_key)
        if cached_result is not None:
            if isinstance(cached_result, str):
                try:
                    _result = json.loads(cached_result)
                except json.JSONDecodeError:
                    _result = cached_result
            logger.debug(f"用户缓存命中: {cache_key}")
            return result
    except (RedisError, ConnectionError, TimeoutError, ValueError) as e:
        logger.warning(f"用户缓存获取失败: {e}")

    # 执行原函数
    if is_async:
        _result = await func(*args, **kwargs)
    else:
        _result = func(*args, **kwargs)

    # 存储到缓存
    try:
        if isinstance(result, (dict, list, tuple, int, float, bool, type(None))):
            serialized_result = json.dumps(result, default=str)
        else:
            serialized_result = str(result)

        if ttl:
            if is_async:
                await redis.setex(cache_key, ttl, serialized_result)
            else:
                redis.setex(cache_key, ttl, serialized_result)
        else:
            if is_async:
                await redis.set(cache_key, serialized_result)
            else:
                redis.set(cache_key, serialized_result)
        logger.debug(f"用户缓存设置: {cache_key}")
    except (RedisError, ConnectionError, TimeoutError, ValueError) as e:
        logger.warning(f"用户缓存设置失败: {e}")

    return result


def cache_invalidate(
    *,
    pattern: Optional[str] = None,
    keys: Optional[list] = None,
    key_generator: Optional[Callable] = None,
    prefix: Optional[str] = None,
) -> Callable[[F], F]:
    """缓存失效装饰器

    在函数执行后使指定的缓存失效。

    Args:
        pattern: 要失效的缓存键模式（支持通配符）
        keys: 要失效的具体缓存键列表
        key_generator: 根据函数参数生成失效键的函数
        prefix: 键前缀

    Returns:
        装饰器函数
    """

    def decorator(func: F) -> F:
        # 检查是否是异步函数
        is_async = inspect.iscoroutinefunction(func)

        @functools.wraps(func)
        async def async_wrapper(*args, **kwargs):
            # 执行原函数
            _result = await func(*args, **kwargs)

            # 生成要失效的键
            invalidate_keys = []

            if pattern:
                # 使用模式匹配
                if "*" in pattern:
                    # 通配符模式，需要扫描所有键
                    try:
                        redis = RedisManager.get_instance()
                        keys_found = await redis.keys(pattern)
                        invalidate_keys.extend(keys_found)
                    except (RedisError, ConnectionError, TimeoutError, ValueError) as e:
                        logger.error(f"扫描缓存键失败: {e}")
                else:
                    invalidate_keys.append(pattern)

            if keys:
                # 直接添加指定的键
                invalidate_keys.extend(keys)

            if key_generator:
                # 使用生成器生成键
                generated_keys = key_generator(func, args, kwargs, result)
                if isinstance(generated_keys, (list, tuple)):
                    invalidate_keys.extend(generated_keys)
                else:
                    invalidate_keys.append(generated_keys)

            # 失效缓存
            if invalidate_keys:
                try:
                    redis = RedisManager.get_instance()
                    # 批量删除
                    if len(invalidate_keys) == 1:
                        await redis.delete(invalidate_keys[0])
                    else:
                        await redis.delete(*invalidate_keys)
                    logger.info(f"缓存失效: {len(invalidate_keys)} 个键")
                except (RedisError, ConnectionError, TimeoutError, ValueError) as e:
                    logger.error(f"缓存失效失败: {e}")

            return result

        @functools.wraps(func)
        def sync_wrapper(*args, **kwargs):
            # 执行原函数
            _result = func(*args, **kwargs)

            # 生成要失效的键
            invalidate_keys = []

            if pattern:
                # 使用模式匹配
                if "*" in pattern:
                    # 通配符模式，需要扫描所有键
                    try:
                        redis = RedisManager.get_instance()
                        keys_found = redis.keys(pattern)
                        invalidate_keys.extend(keys_found)
                    except (RedisError, ConnectionError, TimeoutError, ValueError) as e:
                        logger.error(f"扫描缓存键失败: {e}")
                else:
                    invalidate_keys.append(pattern)

            if keys:
                # 直接添加指定的键
                invalidate_keys.extend(keys)

            if key_generator:
                # 使用生成器生成键
                generated_keys = key_generator(func, args, kwargs, result)
                if isinstance(generated_keys, (list, tuple)):
                    invalidate_keys.extend(generated_keys)
                else:
                    invalidate_keys.append(generated_keys)

            # 失效缓存
            if invalidate_keys:
                try:
                    redis = RedisManager.get_instance()
                    # 批量删除
                    if len(invalidate_keys) == 1:
                        redis.delete(invalidate_keys[0])
                    else:
                        redis.delete(*invalidate_keys)
                    logger.info(f"缓存失效: {len(invalidate_keys)} 个键")
                except (RedisError, ConnectionError, TimeoutError, ValueError) as e:
                    logger.error(f"缓存失效失败: {e}")

            return result

        return async_wrapper if is_async else sync_wrapper  # type: ignore

    return decorator  # type: ignore


# 便捷函数
def cache_user_predictions(ttl_seconds: int = 3600) -> Callable[[F], F]:
    """缓存用户预测结果的便捷装饰器

    Args:
        ttl_seconds: 缓存时间（默认1小时）

    Returns:
        装饰器函数
    """
    return cache_by_user(ttl=ttl_seconds, prefix="predictions", user_param="user_id")


def cache_match_data(ttl_seconds: int = 1800) -> Callable[[F], F]:
    """缓存比赛数据的便捷装饰器

    Args:
        ttl_seconds: 缓存时间（默认30分钟）

    Returns:
        装饰器函数
    """
    return cache_with_ttl(ttl_seconds=ttl_seconds, prefix="matches")


def cache_team_stats(ttl_seconds: int = 7200) -> Callable[[F], F]:
    """缓存球队统计数据的便捷装饰器

    Args:
        ttl_seconds: 缓存时间（默认2小时）

    Returns:
        装饰器函数
    """
    return cache_with_ttl(ttl_seconds=ttl_seconds, prefix="team_stats")


# 缓存装饰器类
class CacheDecorator:
    """缓存装饰器类，提供更灵活的配置"""

    def __init__(
        self,
        *,
        ttl: Optional[int] = None,
        prefix: Optional[str] = None,
        key_generator: Optional[Callable] = None,
        unless: Optional[Callable] = None,
        use_cache_when_unavailable: bool = True,
    ):
        self.ttl = ttl
        self.prefix = prefix
        self.key_generator = key_generator
        self.unless = unless
        self.use_cache_when_unavailable = use_cache_when_unavailable

    def __call__(self, func: F) -> F:
        return cache_result(
            ttl=self.ttl,
            prefix=self.prefix,
            key_generator=self.key_generator,
            unless=self.unless,
            use_cache_when_unavailable=self.use_cache_when_unavailable,
        )(func)


class UserCacheDecorator:
    """用户缓存装饰器类"""

    def __init__(
        self,
        *,
        ttl: Optional[int] = None,
        prefix: Optional[str] = None,
        user_param: str = "user_id",
        key_generator: Optional[Callable] = None,
    ):
        self.ttl = ttl
        self.prefix = prefix
        self.user_param = user_param
        self.key_generator = key_generator

    def __call__(self, func: F) -> F:
        return cache_by_user(
            ttl=self.ttl,
            prefix=self.prefix,
            user_param=self.user_param,
            key_generator=self.key_generator,
        )(func)


class InvalidateCacheDecorator:
    """缓存失效装饰器类"""

    def __init__(
        self,
        *,
        pattern: Optional[str] = None,
        keys: Optional[list] = None,
        key_generator: Optional[Callable] = None,
        prefix: Optional[str] = None,
    ):
        self.pattern = pattern
        self.keys = keys
        self.key_generator = key_generator
        self.prefix = prefix

    def __call__(self, func: F) -> F:
        return cache_invalidate(
            pattern=self.pattern,
            keys=self.keys,
            key_generator=self.key_generator,
            prefix=self.prefix,
        )(func)
