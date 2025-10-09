"""
特征存储模块
Feature Store Module

基于 Feast 的特征存储实现，支持在线和离线特征查询。
"""

from .client import FootballFeatureStore
from .entities import get_entity_definitions
from .feature_views import get_feature_view_definitions
from .registry import FeatureRegistry
from .repository import FeatureRepository

__all__ = [
    "FootballFeatureStore",
    "get_entity_definitions",
    "get_feature_view_definitions",
    "FeatureRegistry",
    "FeatureRepository",
]