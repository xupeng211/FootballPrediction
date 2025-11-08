from collections.abc import Callable
from typing import Any, TypeVar

"""
函数式装饰器
"""

F = TypeVar("F", bound=Callable[..., Any])
T = TypeVar("T")


def decorator(func):
    """函数文档字符串"""
    pass  # 添加pass语句
    pass  # TODO: 实现函数逻辑
