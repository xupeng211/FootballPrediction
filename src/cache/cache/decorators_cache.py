"""
缓存装饰器
"""

# 导入
from typing import Any, Callable, TypeVar


# 常量
F = TypeVar("F", bound=Callable[..., Any])
T = TypeVar("T")


# 类定义
class CacheDecorator:
    """缓存装饰器类，提供更灵活的配置"""

    pass  # TODO: 实现类逻辑


class UserCacheDecorator:
    """用户缓存装饰器类"""

    pass  # TODO: 实现类逻辑


class InvalidateCacheDecorator:
    """缓存失效装饰器类"""

    pass  # TODO: 实现类逻辑
