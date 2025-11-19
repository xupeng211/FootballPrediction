from typing import Optional

"""feature_store 主模块.

此文件由长文件拆分工具自动生成

拆分策略: component_split
"""

# 导入拆分的模块
try:
    from .components.feature_store_core import (
        FootballFeatureStore,
        MockEntity,
        MockFeatureStore,
    )
except ImportError:
    FootballFeatureStore = None
    MockEntity = None
    MockFeatureStore = None

# 导出所有公共接口
__all__ = [
    "FootballFeatureStore",
    "MockEntity",
    "MockFeatureStore",
]
