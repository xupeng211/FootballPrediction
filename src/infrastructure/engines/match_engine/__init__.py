#!/usr/bin/env python3
"""
Match Engine - V1.0.0 [Genesis.UnifiedEngine]
====================================================================

统一收割引擎模块 - 实现 L2 (FotMob) 和 L3 (OddsPortal) 数据采集的
统一接口和归口管理。

Core Features:
- BaseHarvestEngine: 所有引擎必须继承的抽象基类
- NetworkGuardian: NetworkShield 统一接口适配器
- HarvestResult: 统一的收割结果数据结构
- 跨语言状态同步: 与 Node.js QuantHarvester 共享 active_registry.json

Author: [Genesis.UnifiedEngine]
Version: V1.0.0
Date: 2026-02-03
"""

from .base.base_harvest_engine import BaseHarvestEngine, HarvestError, HarvestResult
from .shared.network_guardian import NetworkGuardian

__all__ = [
    "BaseHarvestEngine",
    "HarvestError",
    "HarvestResult",
    "NetworkGuardian",
]
