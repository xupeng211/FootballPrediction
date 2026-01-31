#!/usr/bin/env python3
"""
V33.0 Feature Miners Package
================================
深度特征开采模块 - 从 152 维提升到 400+ 维
"""

from .environment_miner import EnvironmentFeatures, EnvironmentMiner
from .momentum_miner import MomentumFeatures, MomentumMiner
from .shotmap_miner import ShotmapFeatures, ShotmapMiner
from .v33_unified_miner import V33UnifiedMiner, extract_v33_features

__all__ = [
    "ShotmapMiner",
    "ShotmapFeatures",
    "MomentumMiner",
    "MomentumFeatures",
    "EnvironmentMiner",
    "EnvironmentFeatures",
    "V33UnifiedMiner",
    "extract_v33_features",
]

__version__ = "33.0.0"
