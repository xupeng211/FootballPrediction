"""
性能装饰器
Performance Decorators

提供性能监控和优化的装饰器。
"""

import asyncio
import functools
import time
from datetime import datetime, timedelta
from typing import Any, Callable, Dict, List, Optional

from src.core.logging import get_logger

logger = get_logger(__name__)


def monitor_performance(
    threshold: Optional[float] = None,
    log_slow_calls: bool = True,
    track_memory: bool = False,
    collect_metrics: bool = True,
):
    """
    性能监控装饰器 / Performance Monitor Decorator

    Args:
        threshold: 性能阈值（秒）/ Performance threshold (seconds)
        log_slow_calls: 记录慢调用 / Log slow calls
        track_memory: 跟踪内存使用 / Track memory usage
        collect_metrics: 收集指标 / Collect metrics

    Returns:
        Callable: 装饰器函数 / Decorator function
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        async def async_wrapper(*args, **kwargs):
            start_time = time.time()
            start_memory = None
            result = None
            error = None

            try:
                # 跟踪内存使用
                if track_memory:
                    start_memory = _get_memory_usage()

                # 执行原函数
                result = await func(*args, **kwargs)

                return result

            except Exception as e:
                error = str(e)
                raise

            finally:
                # 计算执行时间
                execution_time = time.time() - start_time
                end_memory = _get_memory_usage() if track_memory else None

                # 记录性能数据
                await _log_performance_metrics(
                    func_name=func.__name__,
                    func_module=func.__module__,
                    execution_time=execution_time,
                    memory_usage=end_memory - start_memory if track_memory else None,
                    error=error,
                    threshold=threshold,
                    args_count=len(args) + len(kwargs),
                    result_size=_get_object_size(result) if collect_metrics else None,
                )

        @functools.wraps(func)
        def sync_wrapper(*args, **kwargs):
            start_time = time.time()
            start_memory = None
            result = None
            error = None

            try:
                # 跟踪内存使用
                if track_memory:
                    start_memory = _get_memory_usage()

                # 执行原函数
                result = func(*args, **kwargs)

                return result

            except Exception as e:
                error = str(e)
                raise

            finally:
                # 计算执行时间
                execution_time = time.time() - start_time
                end_memory = _get_memory_usage() if track_memory else None

                # 记录性能数据（同步版本）
                _log_performance_metrics_sync(
                    func_name=func.__name__,
                    func_module=func.__module__,
                    execution_time=execution_time,
                    memory_usage=end_memory - start_memory if track_memory else None,
                    error=error,
                    threshold=threshold,
                    args_count=len(args) + len(kwargs),
                    result_size=_get_object_size(result) if collect_metrics else None,
                )

        # 根据函数类型返回合适的包装器
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        else:
            return sync_wrapper

    return decorator


def cache_result(
    ttl: Optional[float] = None,
    max_size: int = 100,
    key_func: Optional[Callable] = None,
):
    """
    结果缓存装饰器 / Result Cache Decorator

    Args:
        ttl: 生存时间（秒）/ Time to live (seconds)
        max_size: 最大缓存大小 / Max cache size
        key_func: 键生成函数 / Key generation function

    Returns:
        Callable: 装饰器函数 / Decorator function
    """
    cache = {}
    cache_times = {}

    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        async def async_wrapper(*args, **kwargs):
            # 生成缓存键
            if key_func:
                cache_key = key_func(*args, **kwargs)
            else:
                cache_key = _generate_cache_key(func, args, kwargs)

            # 检查缓存
            if cache_key in cache:
                if ttl:
                    cache_time = cache_times.get(cache_key, 0)
                    if time.time() - cache_time < ttl:
                        logger.debug(f"缓存命中: {func.__name__}")
                        return cache[cache_key]
                    else:
                        # 缓存过期，删除
                        del cache[cache_key]
                        del cache_times[cache_key]
                else:
                    logger.debug(f"缓存命中: {func.__name__}")
                    return cache[cache_key]

            # 缓存未命中，执行函数
            result = await func(*args, **kwargs)

            # 存储到缓存
            if len(cache) >= max_size:
                # 删除最旧的缓存项
                oldest_key = min(cache_times.keys(), key=cache_times.get)
                del cache[oldest_key]
                del cache_times[oldest_key]

            cache[cache_key] = result
            cache_times[cache_key] = time.time()

            logger.debug(f"缓存存储: {func.__name__}")
            return result

        @functools.wraps(func)
        def sync_wrapper(*args, **kwargs):
            # 生成缓存键
            if key_func:
                cache_key = key_func(*args, **kwargs)
            else:
                cache_key = _generate_cache_key(func, args, kwargs)

            # 检查缓存
            if cache_key in cache:
                if ttl:
                    cache_time = cache_times.get(cache_key, 0)
                    if time.time() - cache_time < ttl:
                        logger.debug(f"缓存命中: {func.__name__}")
                        return cache[cache_key]
                    else:
                        # 缓存过期，删除
                        del cache[cache_key]
                        del cache_times[cache_key]
                else:
                    logger.debug(f"缓存命中: {func.__name__}")
                    return cache[cache_key]

            # 缓存未命中，执行函数
            result = func(*args, **kwargs)

            # 存储到缓存
            if len(cache) >= max_size:
                # 删除最旧的缓存项
                oldest_key = min(cache_times.keys(), key=cache_times.get)
                del cache[oldest_key]
                del cache_times[oldest_key]

            cache[cache_key] = result
            cache_times[cache_key] = time.time()

            logger.debug(f"缓存存储: {func.__name__}")
            return result

        # 根据函数类型返回合适的包装器
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        else:
            return sync_wrapper

    return decorator


def rate_limit(
    calls: int,
    period: float,
    key_func: Optional[Callable] = None,
):
    """
    速率限制装饰器 / Rate Limit Decorator

    Args:
        calls: 允许的调用次数 / Allowed calls
        period: 时间周期（秒）/ Time period (seconds)
        key_func: 键生成函数 / Key generation function

    Returns:
        Callable: 装饰器函数 / Decorator function
    """
    call_records = {}

    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        async def async_wrapper(*args, **kwargs):
            # 生成限制键
            if key_func:
                limit_key = key_func(*args, **kwargs)
            else:
                limit_key = _generate_limit_key(func, args, kwargs)

            current_time = time.time()

            # 获取调用记录
            if limit_key not in call_records:
                call_records[limit_key] = []

            # 清理过期的调用记录
            call_records[limit_key] = [
                call_time for call_time in call_records[limit_key]
                if current_time - call_time < period
            ]

            # 检查是否超过限制
            if len(call_records[limit_key]) >= calls:
                raise Exception(f"速率限制 exceeded: {calls} calls per {period} seconds")

            # 记录当前调用
            call_records[limit_key].append(current_time)

            # 执行原函数
            return await func(*args, **kwargs)

        @functools.wraps(func)
        def sync_wrapper(*args, **kwargs):
            # 生成限制键
            if key_func:
                limit_key = key_func(*args, **kwargs)
            else:
                limit_key = _generate_limit_key(func, args, kwargs)

            current_time = time.time()

            # 获取调用记录
            if limit_key not in call_records:
                call_records[limit_key] = []

            # 清理过期的调用记录
            call_records[limit_key] = [
                call_time for call_time in call_records[limit_key]
                if current_time - call_time < period
            ]

            # 检查是否超过限制
            if len(call_records[limit_key]) >= calls:
                raise Exception(f"速率限制 exceeded: {calls} calls per {period} seconds")

            # 记录当前调用
            call_records[limit_key].append(current_time)

            # 执行原函数
            return func(*args, **kwargs)

        # 根据函数类型返回合适的包装器
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        else:
            return sync_wrapper

    return decorator


def retry_on_failure(
    max_attempts: int = 3,
    delay: float = 1.0,
    backoff: float = 2.0,
    exceptions: tuple = (Exception,),
):
    """
    失败重试装饰器 / Retry on Failure Decorator

    Args:
        max_attempts: 最大尝试次数 / Max attempts
        delay: 初始延迟（秒）/ Initial delay (seconds)
        backoff: 退避倍数 / Backoff multiplier
        exceptions: 要重试的异常类型 / Exception types to retry

    Returns:
        Callable: 装饰器函数 / Decorator function
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        async def async_wrapper(*args, **kwargs):
            last_exception = None
            current_delay = delay

            for attempt in range(max_attempts):
                try:
                    return await func(*args, **kwargs)
                except exceptions as e:
                    last_exception = e
                    if attempt == max_attempts - 1:
                        # 最后一次尝试失败
                        logger.error(f"函数 {func.__name__} 在 {max_attempts} 次尝试后仍然失败")
                        raise

                    logger.warning(f"函数 {func.__name__} 第 {attempt + 1} 次尝试失败: {e}")
                    await asyncio.sleep(current_delay)
                    current_delay *= backoff

            # 理论上不会到达这里
            raise last_exception

        @functools.wraps(func)
        def sync_wrapper(*args, **kwargs):
            import time as sync_time

            last_exception = None
            current_delay = delay

            for attempt in range(max_attempts):
                try:
                    return func(*args, **kwargs)
                except exceptions as e:
                    last_exception = e
                    if attempt == max_attempts - 1:
                        # 最后一次尝试失败
                        logger.error(f"函数 {func.__name__} 在 {max_attempts} 次尝试后仍然失败")
                        raise

                    logger.warning(f"函数 {func.__name__} 第 {attempt + 1} 次尝试失败: {e}")
                    sync_time.sleep(current_delay)
                    current_delay *= backoff

            # 理论上不会到达这里
            raise last_exception

        # 根据函数类型返回合适的包装器
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        else:
            return sync_wrapper

    return decorator


def timeout(
    timeout_seconds: float,
    exception_message: str = "Function execution timed out",
):
    """
    超时装饰器 / Timeout Decorator

    Args:
        timeout_seconds: 超时时间（秒）/ Timeout seconds
        exception_message: 异常消息 / Exception message

    Returns:
        Callable: 装饰器函数 / Decorator function
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        async def async_wrapper(*args, **kwargs):
            try:
                return await asyncio.wait_for(
                    func(*args, **kwargs),
                    timeout=timeout_seconds
                )
            except asyncio.TimeoutError:
                raise TimeoutError(exception_message)

        @functools.wraps(func)
        def sync_wrapper(*args, **kwargs):
            import signal
            import threading

            def timeout_handler(signum, frame):
                raise TimeoutError(exception_message)

            # 设置超时信号
            signal.signal(signal.SIGALRM, timeout_handler)
            signal.alarm(int(timeout_seconds))

            try:
                result = func(*args, **kwargs)
                signal.alarm(0)  # 取消超时
                return result
            except TimeoutError:
                raise
            finally:
                signal.alarm(0)  # 确保取消超时

        # 根据函数类型返回合适的包装器
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        else:
            return sync_wrapper

    return decorator


# 辅助函数

def _get_memory_usage() -> Optional[float]:
    """
    获取内存使用量 / Get Memory Usage

    Returns:
        Optional[float]: 内存使用量（MB）/ Memory usage (MB)
    """
    try:
        import psutil
        process = psutil.Process()
        return process.memory_info().rss / 1024 / 1024  # 转换为MB
    except ImportError:
        return None
    except Exception as e:
        logger.debug(f"获取内存使用量失败: {e}")
        return None


def _get_object_size(obj: Any) -> int:
    """
    获取对象大小 / Get Object Size

    Args:
        obj: 对象 / Object

    Returns:
        int: 对象大小（字节）/ Object size (bytes)
    """
    try:
        import sys
        return sys.getsizeof(obj)
    except Exception:
        return 0


async def _log_performance_metrics(
    func_name: str,
    func_module: str,
    execution_time: float,
    memory_usage: Optional[float],
    error: Optional[str],
    threshold: Optional[float],
    args_count: int,
    result_size: Optional[int],
) -> None:
    """
    记录性能指标 / Log Performance Metrics

    Args:
        func_name: 函数名 / Function name
        func_module: 函数模块 / Function module
        execution_time: 执行时间 / Execution time
        memory_usage: 内存使用量 / Memory usage
        error: 错误 / Error
        threshold: 阈值 / Threshold
        args_count: 参数数量 / Args count
        result_size: 结果大小 / Result size
    """
    try:
        metrics = {
            "function": f"{func_module}.{func_name}",
            "execution_time": execution_time,
            "memory_usage_mb": memory_usage,
            "error": error,
            "args_count": args_count,
            "result_size_bytes": result_size,
            "timestamp": datetime.now().isoformat(),
        }

        # 检查是否超过阈值
        if threshold and execution_time > threshold:
            logger.warning(f"性能警告: {func_name} 执行时间 {execution_time:.3f}s 超过阈值 {threshold}s")
            metrics["performance_warning"] = True

        # 记录性能指标
        logger.debug(f"性能指标: {metrics}")

    except Exception as e:
        logger.error(f"记录性能指标失败: {e}")


def _log_performance_metrics_sync(
    func_name: str,
    func_module: str,
    execution_time: float,
    memory_usage: Optional[float],
    error: Optional[str],
    threshold: Optional[float],
    args_count: int,
    result_size: Optional[int],
) -> None:
    """
    同步记录性能指标 / Sync Log Performance Metrics

    Args:
        func_name: 函数名 / Function name
        func_module: 函数模块 / Function module
        execution_time: 执行时间 / Execution time
        memory_usage: 内存使用量 / Memory usage
        error: 错误 / Error
        threshold: 阈值 / Threshold
        args_count: 参数数量 / Args count
        result_size: 结果大小 / Result size
    """
    try:
        asyncio.run(_log_performance_metrics(
            func_name=func_name,
            func_module=func_module,
            execution_time=execution_time,
            memory_usage=memory_usage,
            error=error,
            threshold=threshold,
            args_count=args_count,
            result_size=result_size,
        ))
    except Exception as e:
        logger.error(f"同步记录性能指标失败: {e}")


def _generate_cache_key(func: Callable, args: tuple, kwargs: dict) -> str:
    """
    生成缓存键 / Generate Cache Key

    Args:
        func: 函数 / Function
        args: 位置参数 / Positional arguments
        kwargs: 关键字参数 / Keyword arguments

    Returns:
        str: 缓存键 / Cache key
    """
    import hashlib

    # 创建键的字符串表示
    key_parts = [
        func.__module__,
        func.__name__,
        str(args),
        str(sorted(kwargs.items())),
    ]

    key_string = "|".join(key_parts)

    # 生成哈希
    return hashlib.md5(key_string.encode()).hexdigest()


def _generate_limit_key(func: Callable, args: tuple, kwargs: dict) -> str:
    """
    生成限制键 / Generate Limit Key

    Args:
        func: 函数 / Function
        args: 位置参数 / Positional arguments
        kwargs: 关键字参数 / Keyword arguments

    Returns:
        str: 限制键 / Limit key
    """
    # 尝试从参数中提取用户ID或会话ID
    if args:
        first_arg = args[0]
        if hasattr(first_arg, 'user_id'):
            return f"user:{first_arg.user_id}"
        elif hasattr(first_arg, 'session_id'):
            return f"session:{first_arg.session_id}"

    # 尝试从kwargs中提取
    for key in ['user_id', 'session_id', 'username']:
        if key in kwargs:
            return f"{key}:{kwargs[key]}"

    # 默认使用函数名
    return f"func:{func.__name__}"