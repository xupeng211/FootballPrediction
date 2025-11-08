from .feature_definitions import (
    match_entity,
    match_features_view,
    odds_features_view,
    team_entity,
    team_recent_stats_view,
)
from .feature_store import FeatureStore as FootballFeatureStore

"""
特征仓库模块

提供基于Feast的特征存储,管理和服务功能。
支持在线和离线特征服务,用于机器学习模型训练和预测。

主要组件:
- FeatureStore: 特征仓库管理器
- feature_definitions: 特征和实体定义
- feature_service: 特征服务接口

基于 DATA_DESIGN.md 第6.1节特征仓库设计.
"""

__all__ = [
    "FootballFeatureStore",
    "match_entity",
    "team_entity",
    "match_features_view",
    "team_recent_stats_view",
    "odds_features_view",
]
