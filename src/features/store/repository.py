"""
repository.py
repository

此文件已被拆分为多个模块以提供更好的组织结构。
This file has been split into multiple modules for better organization.

为了向后兼容，此文件重新导出所有模块中的类。
For backward compatibility, this file re-exports all classes from the modules.
"""

import warnings

warnings.warn(
    "直接从 repository 导入已弃用。"
    "请从 src/features/store/repo 导入相关类。",
    DeprecationWarning,
    stacklevel=2
)

# 从新模块导入所有内容
from .........src.features.store.repo import cache_repository
from .........src.features.store.repo import database_repository
from .........src.features.store.repo import query_builder
from .........src.features.store.repo import repository

# 导出所有类
__all__ = [
    "cache_repository", "database_repository", "query_builder", "repository"
]
