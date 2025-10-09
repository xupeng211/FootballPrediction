"""
odds_collector.py
odds_collector

此文件已被拆分为多个模块以提供更好的组织结构。
This file has been split into multiple modules for better organization.

为了向后兼容，此文件重新导出所有模块中的类。
For backward compatibility, this file re-exports all classes from the modules.
"""

import warnings

from ......src.collectors.odds.basic import collector
from ......src.collectors.odds.basic import parser
from ......src.collectors.odds.basic import storage
from ......src.collectors.odds.basic import validator

warnings.warn(
    "直接从 odds_collector 导入已弃用。" "请从 src/collectors/odds/basic 导入相关类。",
    DeprecationWarning,
    stacklevel=2,
)

# 从新模块导入所有内容

# 导出所有类
__all__ = ["collector", "parser", "validator", "storage"]
