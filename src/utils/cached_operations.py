from typing import Any, Callable, TypeVar
import functools
import time

T = TypeVar('T')

def cached(ttl: int = 300, max_size: int = 128):
    """缓存装饰器"""
    cache = {}

    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @functools.wraps(func)
        def wrapper(*args, **kwargs) -> T:
            # 创建缓存键
            cache_key = str(args) + str(sorted(kwargs.items()))

            # 检查缓存
            if cache_key in cache:
                item, timestamp = cache[cache_key]
                if time.time() - timestamp < ttl:
                    return item
                else:
                    del cache[cache_key]

            # 执行函数并缓存结果
            result = func(*args, **kwargs)

            # 添加到缓存
            if len(cache) >= max_size:
                # 删除最旧的项
                oldest_key = min(cache.keys(), key=lambda k: cache[k][1])
                del cache[oldest_key]

            cache[cache_key] = (result, time.time())
            return result

        return wrapper
    return decorator
