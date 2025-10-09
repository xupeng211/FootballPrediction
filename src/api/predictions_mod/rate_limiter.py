"""

"""









    """获取速率限制器实例"""


    """检查速率限制功能是否可用"""


    from slowapi import Limiter
    from slowapi.util import get_remote_address
from typing import Callable

速率限制配置 / Rate Limiting Configuration
提供API速率限制功能，支持可选的slowapi集成。
try:
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
    return limiter
def is_rate_limit_available() -> bool:
    return RATE_LIMIT_AVAILABLE