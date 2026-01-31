#!/usr/bin/env python3
"""
V35.0 数据工程模块
==================

提供生产级数据管道能力:
- FeatureFactory: V35.0 特征工厂 (ELO + Table + Fatigue + Efficiency)
- MultiPathExtractor: 多路径 JSONB 提取器

使用示例:
    from src.data import FeatureFactory, create_feature_factory

    # 创建特征工厂
    factory = create_feature_factory()
    df_features = factory.build_all_features(df_matches)
"""

from .feature_factory import (
    EfficiencyEngine,
    ELOEngine,
    FatigueTracker,
    FeatureFactory,
    TableManager,
    create_feature_factory,
)
from .multipath_extractor import (
    ExtractionPath,
    ExtractionStats,
    MatchStats,
    MultiPathExtractor,
    extract_match_stats_batch,
)

__all__ = [
    "ELOEngine",
    "EfficiencyEngine",
    "ExtractionPath",
    "ExtractionStats",
    "FatigueTracker",
    # FeatureFactory (V35.0)
    "FeatureFactory",
    "MatchStats",
    # MultiPathExtractor
    "MultiPathExtractor",
    "TableManager",
    "create_feature_factory",
    "extract_match_stats_batch",
]

__version__ = "35.2.0"
