"""
common_models.py
common_models

此文件已被拆分为多个模块以提供更好的组织结构。
This file has been split into multiple modules for better organization.

为了向后兼容，此文件重新导出所有模块中的类。
For backward compatibility, this file re-exports all classes from the modules.
"""

import warnings

# from ..api.data.models import api_models  # 已重构，移除此导入
from ..base_models import base_models as base_models_mod
from ..common import data_models
from ..common import utils

# 为了向后兼容
base_models = base_models_mod

warnings.warn(
    "直接从 common_models 导入已弃用。" "请从 src/models/common 导入相关类。",
    DeprecationWarning,
    stacklevel=2,
)

# 从新模块导入所有内容

# 导出所有类
__all__ = ["base_models", "data_models", "utils"]
