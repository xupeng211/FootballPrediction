"""
features.py
features

此文件已被拆分为多个模块以提供更好的组织结构。
This file has been split into multiple modules for better organization.

为了向后兼容，此文件重新导出所有模块中的类。
For backward compatibility, this file re-exports all classes from the modules.
"""

import warnings

warnings.warn(
    "直接从 features 导入已弃用。"
    "请从 src/database/models/feature_mod 导入相关类。",
    DeprecationWarning,
    stacklevel=2
)

# 从新模块导入所有内容
from .........src.database.models.feature_mod import feature_entity
from .........src.database.models.feature_mod import feature_types
from .........src.database.models.feature_mod import feature_metadata
from .........src.database.models.feature_mod import models

# 导出所有类
__all__ = [
    "feature_entity", "feature_types", "feature_metadata", "models"
]
