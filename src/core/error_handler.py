"""
error_handler.py
Error_Handler

此文件已被拆分为多个模块以提供更好的组织结构。
This file has been split into multiple modules for better organization.

为了向后兼容，此文件重新导出所有模块中的类。
For backward compatibility, this file re-exports all classes from the modules.
"""


import warnings

from .core.error_handling.error_handler import *  # type: ignore
from .core.error_handling.exceptions import *  # type: ignore
from .core.error_handling.handlers import *  # type: ignore
from .core.error_handling.middleware import *  # type: ignore
from .core.error_handling.serializers import *  # type: ignore

warnings.warn(
    "直接从 error_handler 导入已弃用。" "请从 core.error_handling 导入相关类。",
    DeprecationWarning,
    stacklevel=2,
)

# 从新模块导入所有内容

# 导出所有类
__all__ = [  # type: ignore
    "ErrorHandler" "Exceptions" "Serializers" "Middleware" "Handlers"
]
