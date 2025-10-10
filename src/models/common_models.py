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
from .base_models import base_models as base_models_mod
from ..common import api_models
# utils 模块不存在，注释掉以避免导入错误
# from ..common import utils

# 为了向后兼容
base_models = base_models_mod
data_models = api_models  # 别名以保持兼容性
utils = None  # 临时设置为 None 以避免导入错误

warnings.warn(
    "直接从 common_models 导入已弃用。" "请从 src/models/common 导入相关类。",
    DeprecationWarning,
    stacklevel=2,
)

# 从新模块导入所有内容

# 从 services.content_analysis 导入 Content, ContentType, AnalysisResult, UserProfile 和 UserRole 以保持兼容性
from ..services.content_analysis import (
    Content,
    ContentType,
    AnalysisResult,
    UserProfile,
    UserRole,
)

# 从 database.models 导入 User 以保持兼容性
from ..database.models import User

# 导出所有类
__all__ = [
    "base_models",
    "data_models",
    "Content",
    "ContentType",
    "AnalysisResult",
    "UserProfile",
    "UserRole",
    "User",
]
