"""
data.py
Data

此文件已被拆分为多个模块以提供更好的组织结构。
This file has been split into multiple modules for better organization.

为了向后兼容，此文件重新导出所有模块中的类。
For backward compatibility, this file re-exports all classes from the modules.
"""

import warnings

warnings.warn(
    "直接从 data 导入已弃用。"
    "请从 api.data.endpoints 导入相关类。",
    DeprecationWarning,
    stacklevel=2
)

# 从新模块导入所有内容
from .api.data.endpoints.matches import *
from .api.data.endpoints.teams import *
from .api.data.endpoints.leagues import *
from .api.data.endpoints.odds import *
from .api.data.endpoints.statistics import *
from .api.data.endpoints.dependencies import *

# 导出所有类
__all__ = [
    "Matches"
    "Teams"
    "Leagues"
    "Odds"
    "Statistics"
    "Dependencies"
]
