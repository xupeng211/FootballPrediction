"""Feast 特征存储集成及其测试环境替身实现。"""

from .store import (
from .store.mock_feast import (

# 为了向后兼容，从新的模块化实现重新导出所有类
    FeatureRegistry,
    FeatureRepository,
    FootballFeatureStore,
    get_entity_definitions,
    get_feature_view_definitions,
)

# 为了向后兼容，保留原有的导入
    Entity,
    FeatureStore,
    FeatureView,
    Float64,
    Int64,
    PostgreSQLSource,
    ValueType,
)

__all__ = [
    "FootballFeatureStore",
    "FeatureRegistry",
    "FeatureRepository",
    "Entity",
    "FeatureStore",
    "FeatureView",
    "PostgreSQLSource",
    "Float64",
    "Int64",
    "ValueType",
    "get_entity_definitions",
    "get_feature_view_definitions",
]