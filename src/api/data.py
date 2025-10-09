"""
data.py
Data

此文件已被拆分为多个模块以提供更好的组织结构。
This file has been split into multiple modules for better organization.

为了向后兼容，此文件重新导出所有模块中的类。
For backward compatibility, this file re-exports all classes from the modules.
"""


import warnings

from .data.endpoints.dependencies import *  # type: ignore
from .data.endpoints.leagues import *  # type: ignore
from .data.endpoints.matches import *  # type: ignore
from .data.endpoints.odds import *  # type: ignore
from .data.endpoints.statistics import *  # type: ignore
from .data.endpoints.teams import *  # type: ignore

warnings.warn(
    "直接从 data 导入已弃用。" "请从 api.data.endpoints 导入相关类。",
    DeprecationWarning,
    stacklevel=2,
)

# 从新模块导入所有内容

# 导出所有类
__all__ = [  # type: ignore
    "Matches" "Teams" "Leagues" "Odds" "Statistics" "Dependencies"
]
