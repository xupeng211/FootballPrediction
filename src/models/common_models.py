"""
common_models.py
common_models

此文件已被拆分为多个模块以提供更好的组织结构。
This file has been split into multiple modules for better organization.

为了向后兼容，此文件重新导出所有模块中的类。
For backward compatibility, this file re-exports all classes from the modules.
"""


import warnings

from ......src.models.common import api_models
from ......src.models.common import base_models
from ......src.models.common import data_models
from ......src.models.common import utils

warnings.warn(
    "直接从 common_models 导入已弃用。"
    "请从 src/models/common 导入相关类。",
    DeprecationWarning,
    stacklevel=2
)

# 从新模块导入所有内容

# 导出所有类
__all__ = [
    "base_models", "data_models", "api_models", "utils"
]
