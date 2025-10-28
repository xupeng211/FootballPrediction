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


def cache_by_user(user_id_param="user_id", user_param=None, ttl=None, prefix=None):
    """按用户缓存的装饰器 - 占位符实现"""
    # 支持两种参数名称以保持兼容性
    if user_param is not None:
        user_id_param = user_param  # noqa: F841  # 占位符实现中暂时未使用

    def decorator(func):
        return func

    return decorator


def _make_cache_key(
    func_or_name, args, kwargs, prefix=None, user_id=None, exclude_args=None
):
    """智能Mock兼容修复模式 - 生成缓存键的辅助函数

    Args:
        func_or_name: 函数对象或函数名字符串
        args: 位置参数元组
        kwargs: 关键字参数字典
        prefix: 键前缀
        user_id: 用户ID（兼容性参数）
        exclude_args: 要排除的参数名列表
    """
    import hashlib

    # 智能Mock兼容修复模式 - 支持函数对象和函数名两种输入
    if callable(func_or_name):
        # 如果是函数对象，提取模块和限定名
        func_name = f"{func_or_name.__module__}:{func_or_name.__qualname__}"
    else:
        # 如果是字符串，直接使用
        func_name = str(func_or_name)

    key_parts = []

    # 添加前缀（如果提供）
    if prefix:
        key_parts.append(prefix)

    # 添加函数名
    key_parts.append(func_name)

    # 添加用户ID（如果提供）
    if user_id is not None:
        key_parts.append(f"user:{user_id}")

    # 智能Mock兼容修复模式 - 处理exclude_args
    if exclude_args:
        # 过滤掉要排除的参数
        filtered_kwargs = {k: v for k, v in kwargs.items() if k not in exclude_args}
    else:
        filtered_kwargs = kwargs

    # 添加参数到键中
    if args:
        key_parts.extend(str(arg) for arg in args)
    if filtered_kwargs:
        sorted_kwargs = sorted(filtered_kwargs.items())
        key_parts.extend(f"{k}:{v}" for k, v in sorted_kwargs)

    # 智能Mock兼容修复模式 - 生成可读的键格式，包含哈希避免过长
    key_str = ":".join(key_parts)

    # 如果键太长，生成哈希版本
    if len(key_str) > 200:
        return hashlib.md5(key_str.encode(), usedforsecurity=False).hexdigest()

    return key_str


def cache_invalidate(pattern_func=None, pattern=None, key_generator=None, **kwargs):
    """缓存失效装饰器 - 占位符实现"""

    # 支持多种参数名称以保持兼容性
    def decorator(func):
        return func

    return decorator


def cache_user_predictions(ttl_seconds=None, **kwargs):
    """用户预测缓存装饰器 - 占位符实现"""

    def decorator(func):
        return func

    return decorator


def cache_match_data(ttl_seconds=None, **kwargs):
    """比赛数据缓存装饰器 - 占位符实现"""

    def decorator(func):
        return func

    return decorator


def cache_team_stats(ttl_seconds=None, **kwargs):
    """队伍统计缓存装饰器 - 占位符实现"""

    def decorator(func):
        return func

    return decorator
