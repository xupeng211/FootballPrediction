"""
decorators 主模块

此文件由长文件拆分工具自动生成

拆分策略: functional_split
"""

# 导入拆分的模块
from .cache.decorators_cache import *
from .cache.decorators_functions import *

# 导出所有公共接口
__all__ = [
    "CacheDecorator",
    "UserCacheDecorator",
    "InvalidateCacheDecorator",
    "cache_result",
    "cache_with_ttl",
    "cache_by_user",
    "cache_invalidate",
    "cache_user_predictions",
    "cache_match_data",
    "cache_team_stats",
]


# 提供占位符函数以保持向后兼容
def cache_result(*args, **kwargs):
    """缓存结果装饰器 - 占位符实现"""
    if args and callable(args[0]):
        # 直接作为装饰器使用: @cache_result
        return args[0]
    else:
        # 带参数使用: @cache_result(ttl=3600)
        def decorator(func):
            return func

        return decorator


def cache_with_ttl(ttl_seconds, prefix=None):
    """带TTL的缓存装饰器 - 占位符实现"""

    def decorator(func):
        return func

    return decorator


def cache_by_user(user_id_param="user_id"):
    """按用户缓存的装饰器 - 占位符实现"""

    def decorator(func):
        return func

    return decorator


def _make_cache_key(func_name, args, kwargs, prefix=None):
    """生成缓存键的辅助函数"""
    import hashlib
    import json

    key_parts = [func_name]
    if prefix:
        key_parts.append(prefix)

    # 添加参数到键中
    if args:
        key_parts.extend(str(arg) for arg in args)
    if kwargs:
        sorted_kwargs = sorted(kwargs.items())
        key_parts.extend(f"{k}:{v}" for k, v in sorted_kwargs)

    # 生成哈希
    key_str = ":".join(key_parts)
    return hashlib.md5(key_str.encode(), usedforsecurity=False).hexdigest()


def cache_invalidate(pattern_func):
    """缓存失效装饰器 - 占位符实现"""

    def decorator(func):
        return func

    return decorator


def cache_user_predictions(func):
    """用户预测缓存装饰器 - 占位符实现"""
    return func


def cache_match_data(func):
    """比赛数据缓存装饰器 - 占位符实现"""
    return func


def cache_team_stats(func):
    """队伍统计缓存装饰器 - 占位符实现"""
    return func
