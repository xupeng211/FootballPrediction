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
def cache_result(func):
    """缓存结果装饰器 - 占位符实现"""
    return func


def cache_with_ttl(ttl_seconds):
    """带TTL的缓存装饰器 - 占位符实现"""

    def decorator(func):
        return func

    return decorator


def cache_by_user(user_id_param="user_id"):
    """按用户缓存的装饰器 - 占位符实现"""

    def decorator(func):
        return func

    return decorator


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
