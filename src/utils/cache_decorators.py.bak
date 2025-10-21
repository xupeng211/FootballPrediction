from typing import Any, Callable, Optional
import functools
import time
import hashlib
import json

def cache_key_from_args(*args, **kwargs) -> str:
    """从参数生成缓存键"""
    key_data = str(args) + str(sorted(kwargs.items()))
    return hashlib.md5(key_data.encode()).hexdigest()

def cache_result(ttl: int = 300, cache_key_func: Callable = None):
    """缓存结果装饰器"""
    cache = {}

    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            # 生成缓存键
            if cache_key_func:
                cache_key = cache_key_func(*args, **kwargs)
            else:
                cache_key = cache_key_from_args(*args, **kwargs)

            # 检查缓存
            if cache_key in cache:
                item, timestamp = cache[cache_key]
                if time.time() - timestamp < ttl:
                    return item
                else:
                    del cache[cache_key]

            # 执行函数并缓存结果
            result = func(*args, **kwargs)
            cache[cache_key] = (result, time.time())
            return result

        return wrapper
    return decorator

def async_cache_result(ttl: int = 300, cache_key_func: Callable = None):
    """异步缓存结果装饰器"""
    cache = {}

    def decorator(func):
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            # 生成缓存键
            if cache_key_func:
                cache_key = cache_key_func(*args, **kwargs)
            else:
                cache_key = cache_key_from_args(*args, **kwargs)

            # 检查缓存
            if cache_key in cache:
                item, timestamp = cache[cache_key]
                if time.time() - timestamp < ttl:
                    return item
                else:
                    del cache[cache_key]

            # 执行异步函数并缓存结果
            result = await func(*args, **kwargs)
            cache[cache_key] = (result, time.time())
            return result

        return wrapper
    return decorator
