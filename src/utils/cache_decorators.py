"""
缓存装饰器
Cache Decorators

提供简单易用的缓存装饰器。
"""

import functools
import json
import hashlib
from typing import Any, Callable, Optional, Union
import time

# 简单的内存缓存实现
_memory_cache = {}

def memory_cache(ttl: int = 3600, max_size: int = 1000):
    """
    内存缓存装饰器

    Args:
        ttl: 生存时间（秒）
        max_size: 最大缓存条目数
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            # 生成缓存键
            cache_key = _generate_cache_key(func.__name__, args, kwargs)

            # 检查缓存
            if cache_key in _memory_cache:
                data, timestamp = _memory_cache[cache_key]
                if time.time() - timestamp < ttl:
                    return data
                else:
                    del _memory_cache[cache_key]

            # 清理过期缓存
            _cleanup_expired_cache(ttl)

            # 如果缓存过大，删除最旧的条目
            if len(_memory_cache) >= max_size:
                oldest_key = min(_memory_cache.keys(),
                               key=lambda k: _memory_cache[k][1])
                del _memory_cache[oldest_key]

            # 执行函数并缓存结果
            result = func(*args, **kwargs)
            _memory_cache[cache_key] = (result, time.time())

            return result

        return wrapper
    return decorator

def _generate_cache_key(func_name: str, args: tuple, kwargs: dict) -> str:
    """生成缓存键"""
    # 将参数序列化为字符串
    key_data = {
        'args': args,
        'kwargs': sorted(kwargs.items())
    }
    key_str = json.dumps(key_data, sort_keys=True, default=str)
    # 使用MD5哈希生成固定长度的键
    hash_key = hashlib.md5(key_str.encode()).hexdigest()
    return f"{func_name}:{hash_key}"

def _cleanup_expired_cache(ttl: int):
    """清理过期的缓存条目"""
    current_time = time.time()
    expired_keys = [
        key for key, (_, timestamp) in _memory_cache.items()
        if current_time - timestamp >= ttl
    ]
    for key in expired_keys:
        del _memory_cache[key]

def clear_cache():
    """清空所有缓存"""
    global _memory_cache
    _memory_cache.clear()

def get_cache_info() -> dict:
    """获取缓存信息"""
    return {
        'size': len(_memory_cache),
        'keys': list(_memory_cache.keys())
    }

# Redis缓存装饰器（简化版，不需要实际的Redis）
def redis_cache(key_prefix: str = "", ttl: int = 3600):
    """
    Redis缓存装饰器（模拟实现）

    Args:
        key_prefix: 键前缀
        ttl: 生存时间（秒）
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            # 这里使用内存缓存模拟Redis
            # 在生产环境中，应该连接真实的Redis
            return memory_cache(ttl=ttl)(func)(*args, **kwargs)
        return wrapper
    return decorator

# 批量缓存装饰器
def batch_cache(ttl: int = 3600):
    """
    批量操作缓存装饰器
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            # 对于批量操作，缓存整个结果
            return memory_cache(ttl=ttl)(func)(*args, **kwargs)
        return wrapper
    return decorator

# 缓存失效装饰器
def cache_invalidate(pattern: str = ""):
    """
    缓存失效装饰器
    当函数执行成功后，清除匹配模式的缓存

    Args:
        pattern: 要清除的缓存键模式
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            result = func(*args, **kwargs)

            # 清除匹配的缓存
            if pattern:
                keys_to_delete = [
                    key for key in _memory_cache.keys()
                    if pattern in key
                ]
                for key in keys_to_delete:
                    del _memory_cache[key]

            return result
        return wrapper
    return decorator

# 条件缓存装饰器
def conditional_cache(condition: Callable[[Any], bool], ttl: int = 3600):
    """
    条件缓存装饰器
    只有满足条件时才缓存结果

    Args:
        condition: 判断函数，接收结果，返回是否缓存
        ttl: 生存时间
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            result = func(*args, **kwargs)

            if condition(result):
                cache_key = _generate_cache_key(func.__name__, args, kwargs)
                _memory_cache[cache_key] = (result, time.time())

            return result
        return wrapper
    return decorator

# 示例使用
if __name__ == "__main__":
    # 使用内存缓存
    @memory_cache(ttl=60)
    def expensive_operation(x: int, y: int) -> int:
        print(f"执行计算: {x} + {y}")
        time.sleep(1)  # 模拟耗时操作
        return x + y

    # 使用Redis缓存
    @redis_cache(key_prefix="calc", ttl=300)
    def multiply(a: int, b: int) -> int:
        print(f"执行乘法: {a} * {b}")
        return a * b

    # 测试
    print("第一次调用:", expensive_operation(1, 2))
    print("第二次调用:", expensive_operation(1, 2))  # 从缓存获取
    print("缓存信息:", get_cache_info())