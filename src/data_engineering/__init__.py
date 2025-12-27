#!/usr/bin/env python3
"""
V35.0 数据工程模块
==================

提供生产级数据管道能力:
- FeatureFactory: V35.0 特征工厂 (ELO + Table + Fatigue + Efficiency)
- MultiPathExtractor: 多路径 JSONB 提取器

使用示例:
    from src.data_engineering import FeatureFactory, create_feature_factory

    # 创建特征工厂
    factory = create_feature_factory()
    df_features = factory.build_all_features(df_matches)
"""

from .feature_factory import (
    FeatureFactory,
    ELOEngine,
    TableManager,
    FatigueTracker,
    EfficiencyEngine,
    create_feature_factory
)

from .multipath_extractor import (
    MultiPathExtractor,
    MatchStats,
    ExtractionStats,
    ExtractionPath,
    extract_match_stats_batch
)

__all__ = [
    # FeatureFactory (V35.0)
    'FeatureFactory',
    'ELOEngine',
    'TableManager',
    'FatigueTracker',
    'EfficiencyEngine',
    'create_feature_factory',

    # MultiPathExtractor
    'MultiPathExtractor',
    'MatchStats',
    'ExtractionStats',
    'ExtractionPath',
    'extract_match_stats_batch',
]

__version__ = '35.2.0'
