"""
足球特征商店（向后兼容）
Football Feature Store (Backward Compatible)

为了保持向后兼容性，此文件重新导出新的模块化特征仓库。

Provides backward compatible exports for the modular feature store.
"""

from .feature_store_main import (
from .utils import (

# 重新导出主类和函数
    FootballFeatureStore,
    get_feature_store,
    initialize_feature_store,
)
    HAS_FEAST,
    match_entity,
    team_entity,
    match_features_view,
    team_recent_stats_view,
    odds_features_view,
    head_to_head_features_view,
)

# 保持向后兼容的原始导入
try:
    # 尝试从原始文件导入
    from .feature_store_original import (
        FootballFeatureStore as OriginalFootballFeatureStore,
        get_feature_store as get_original_feature_store,
        initialize_feature_store as initialize_original_feature_store,
    )
except ImportError:
    # 如果原始文件有问题，使用新的模块化版本
    OriginalFootballFeatureStore = FootballFeatureStore
    get_original_feature_store = get_feature_store
    initialize_original_feature_store = initialize_feature_store

# 导出所有符号
__all__ = [
    "FootballFeatureStore",
    "get_feature_store",
    "initialize_feature_store",
    "HAS_FEAST",
    "match_entity",
    "team_entity",
    "match_features_view",
    "team_recent_stats_view",
    "odds_features_view",
    "head_to_head_features_view",
    "OriginalFootballFeatureStore",
    "get_original_feature_store",
    "initialize_original_feature_store",
]