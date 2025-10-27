"""
API缓存实现
生成时间: 2025-10-26 20:57:22
"""

import json
import time
from functools import wraps
from typing import Any, Dict, Optional


class APICache:
    """API缓存管理器"""

    def __init__(self, default_ttl: int = 300):
        self.cache = {}
        self.default_ttl = default_ttl

    def get(self, key: str) -> Optional[Any]:
        """获取缓存值"""
        if key in self.cache:
            item = self.cache[key]
            if time.time() < item["expires"]:
                return item["value"]
            else:
                del self.cache[key]
        return None

    def set(self, key: str, value: Any, ttl: Optional[int] = None) -> None:
        """设置缓存值"""
        if ttl is None:
            ttl = self.default_ttl

        self.cache[key] = {"value": value, "expires": time.time() + ttl}

    def delete(self, key: str) -> bool:
        """删除缓存值"""
        if key in self.cache:
            del self.cache[key]
            return True
        return False

    def clear(self):
        """清空缓存"""
        self.cache.clear()


# 全局缓存实例
api_cache = APICache()


def cache_api_response(ttl: int = 300):
    """API响应缓存装饰器"""

    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            # 生成缓存键
            cache_key = f"{func.__name__}_{str(args)}_{str(kwargs)}"

            # 尝试从缓存获取
            cached_result = api_cache.get(cache_key)
            if cached_result is not None:
                return cached_result

            # 执行函数并缓存结果
            result = func(*args, **kwargs)
            api_cache.set(cache_key, result, ttl)

            return result

        return wrapper

    return decorator
