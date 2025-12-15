"""
Feature Engineering Module - 特征工程模块

Phase 2: AI Modeling - 特征工程核心组件

提供标准化的特征生成框架，支持滚动窗口特征、统计特征、衍生特征等。
"""

from .base import BaseFeatureTransformer
from .rolling import RollingAverageTransformer, RollingSumTransformer

__all__ = [
    'BaseFeatureTransformer',
    'RollingAverageTransformer',
    'RollingSumTransformer',
]