"""
service.py
service

此文件已被拆分为多个模块以提供更好的组织结构。
This file has been split into multiple modules for better organization.

为了向后兼容，此文件重新导出所有模块中的类。
For backward compatibility, this file re-exports all classes from the modules.
"""

import warnings

warnings.warn(
    "直接从 service 导入已弃用。" "请从 src/services/data_processing/mod 导入相关类。",
    DeprecationWarning,
    stacklevel=2,
)

# 从新模块导入所有内容
from .........src.services.data_processing.mod import pipeline
from .........src.services.data_processing.mod import validator
from .........src.services.data_processing.mod import transformer
from .........src.services.data_processing.mod import service

# 导出所有类
__all__ = ["pipeline", "validator", "transformer", "service"]
