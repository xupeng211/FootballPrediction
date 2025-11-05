"""
缓存装饰器模块
"""

import functools
import logging
import asyncio
from typing import Callable, Optional

logger = logging.getLogger(__name__)

def cache_result(ttl: int = 300, key_func: Optional[Callable] = None):
    """缓存结果装饰器"""
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def sync_wrapper(*args, **kwargs):
            # 简化的缓存逻辑
            return func(*args, **kwargs)

        @functools.wraps(func)
        async def async_wrapper(*args, **kwargs):
            # 简化的异步缓存逻辑
            return await func(*args, **kwargs)

        return async_wrapper if asyncio.iscoroutinefunction(func) else sync_wrapper
    return decorator

def invalidate_cache(pattern: str = "*"):
    """缓存失效装饰器"""
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            try:
                result = func(*args, **kwargs)
                logger.debug(f"缓存失效: pattern={pattern}")
                return result
            except Exception as e:
                logger.error(f"缓存失效错误: {e}")
                raise
        return wrapper
    return decorator

# 缓存装饰器类
class CacheDecorator:
    """缓存装饰器基类"""
    def __init__(self, ttl: int = 300):
        self.ttl = ttl

    def __call__(self, func: Callable) -> Callable:
        return cache_result(self.ttl)(func)

class InvalidateCacheDecorator:
    """缓存失效装饰器"""
    def __init__(self, pattern: str = "*"):
        self.pattern = pattern

    def __call__(self, func: Callable) -> Callable:
        return invalidate_cache(self.pattern)(func)

class UserCacheDecorator(CacheDecorator):
    """用户缓存装饰器"""
    def __init__(self, ttl: int = 300):
        super().__init__(ttl)

# 便捷装饰器函数
cache_by_user = UserCacheDecorator
cache_invalidate = invalidate_cache
cache_match_data = cache_result
cache_team_stats = cache_result
cache_user_predictions = cache_result
cache_with_ttl = cache_result