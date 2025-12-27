#!/usr/bin/env python3
"""
V28.0 数据工程模块
==================

提供生产级数据管道能力:
- MultiPathExtractor: 多路径 JSONB 提取器
- V28FeaturePipeline: 特征计算流水线
- 时间对齐的滚动特征计算

使用示例:
    from src.database.db_pool import SyncDatabasePool
    from src.data_engineering import V28FeaturePipeline, run_v28_pipeline

    # 初始化连接池
    db_pool = SyncDatabasePool()
    db_pool.init_pool()

    # 运行流水线
    report = run_v28_pipeline(db_pool)
    logger.info(f"平均填充率: {report.fill_rates.values():.2f}%")
"""

from .multipath_extractor import (
    MultiPathExtractor,
    MatchStats,
    ExtractionStats,
    ExtractionPath,
    extract_match_stats_batch
)

from .feature_pipeline import (
    V28FeaturePipeline,
    PipelineConfig,
    PipelineReport,
    run_v28_pipeline
)

__all__ = [
    # MultiPathExtractor
    'MultiPathExtractor',
    'MatchStats',
    'ExtractionStats',
    'ExtractionPath',
    'extract_match_stats_batch',

    # FeaturePipeline
    'V28FeaturePipeline',
    'PipelineConfig',
    'PipelineReport',
    'run_v28_pipeline',
]

__version__ = '28.0.0'
