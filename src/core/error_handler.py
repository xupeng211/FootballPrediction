"""
error_handler.py
Error_Handler

此文件已被拆分为多个模块以提供更好的组织结构。
This file has been split into multiple modules for better organization.

为了向后兼容，此文件重新导出所有模块中的类。
For backward compatibility, this file re-exports all classes from the modules.
"""

import warnings

warnings.warn(
    "直接从 error_handler 导入已弃用。" "请从 core.error_handling 导入相关类。",
    DeprecationWarning,
    stacklevel=2,
)

# 从新模块导入所有内容
# 由于模块尚未实现，使用占位符
try:
    from .error_handling.error_handler import ErrorHandler
except ImportError:
    ErrorHandler = None

try:
    from .error_handling.exceptions import ErrorTypes
except ImportError:
    ErrorTypes = None

try:
    from .error_handling.serializers import ErrorSerializers
except ImportError:
    ErrorSerializers = None

try:
    from .error_handling.middleware import ErrorMiddleware
except ImportError:
    ErrorMiddleware = None

try:
    from .error_handling.handlers import ErrorHandlers
except ImportError:
    ErrorHandlers = None

# 导出所有类
__all__ = [
    "ErrorHandler",
    "ErrorTypes",
    "ErrorSerializers",
    "ErrorMiddleware",
    "ErrorHandlers",
]
