#!/usr/bin/env python3
"""
Base Harvest Engine - V1.0.0 [Genesis.UnifiedEngine]
====================================================================

基础引擎抽象类 - 定义所有收割引擎必须实现的统一接口。

所有引擎 (FotMob, OddsPortal, etc.) 必须继承 BaseHarvestEngine 并实现
其抽象方法, 确保:
1. 统一的初始化流程
2. 强制的 NetworkShield 认证
3. 标准化的结果返回
4. 一致的错误处理

Author: [Genesis.UnifiedEngine]
Version: V1.0.0
Date: 2026-02-03
"""

from .base_harvest_engine import (
    BaseHarvestEngine,
    EngineConfig,
    EngineStatistics,
    HarvestError,
    HarvestResult,
)

__all__ = [
    "BaseHarvestEngine",
    "EngineConfig",
    "EngineStatistics",
    "HarvestError",
    "HarvestResult",
]
