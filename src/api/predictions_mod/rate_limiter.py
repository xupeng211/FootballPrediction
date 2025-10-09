"""
速率限制配置 / Rate Limiting Configuration

提供API速率限制功能，支持可选的slowapi集成。
"""


try:
    from slowapi import Limiter
    from slowapi.util import get_remote_address

    limiter = Limiter(key_func=get_remote_address)
    RATE_LIMIT_AVAILABLE = True
except ImportError:
    RATE_LIMIT_AVAILABLE = False

    # 创建空的装饰器函数
    def limiter_decorator(*args, **kwargs):
        def decorator(func: Callable) -> Callable:
            return func

        return decorator

    class _LimiterStub:
        def limit(self, *args, **kwargs):
            return limiter_decorator

    limiter = _LimiterStub()


def get_rate_limiter():
    """获取速率限制器实例"""
    return limiter


def is_rate_limit_available() -> bool:
    """检查速率限制功能是否可用"""
    return RATE_LIMIT_AVAILABLE
from typing import Callable

