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
    "直接从 data 导入已弃用。" "请从 api.data.endpoints 导入相关类。",
    DeprecationWarning,
    stacklevel=2,
)

# 从新模块导入所有内容
# 由于模块尚未实现，使用占位符
try:
    from .api.data.endpoints.matches import router as Matches
except ImportError:
    Matches = None

try:
    from .api.data.endpoints.teams import router as Teams
except ImportError:
    Teams = None

try:
    from .api.data.endpoints.leagues import router as Leagues
except ImportError:
    Leagues = None

try:
    from .api.data.endpoints.odds import router as Odds
except ImportError:
    Odds = None

try:
    from .api.data.endpoints.statistics import router as Statistics
except ImportError:
    Statistics = None

try:
    from .api.data.endpoints.dependencies import router as Dependencies
except ImportError:
    Dependencies = None

# 导出所有类
__all__ = [
    "Matches",
    "Teams",
    "Leagues",
    "Odds",
    "Statistics",
    "Dependencies",
]
