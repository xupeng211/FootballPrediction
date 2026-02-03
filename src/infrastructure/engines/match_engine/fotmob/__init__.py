#!/usr/bin/env python3
"""
FotMob Engine Module - V145.0 [Genesis.UnifiedEngine]
====================================================

FotMob L2 数据收割引擎 - 迁移自 src/collectors/fotmob_core.py

迁移变更:
- 继承 BaseHarvestEngine 统一接口
- NetworkShield 代理管理（替代 ProxyManager V41.590）
- UnifiedCircuitBreaker 熔断保护（整合 7 个碎片化实现）
- 保留 Ghost Protocol 反检测能力（BaseExtractor V150.0）
- 跨语言状态同步（active_registry.json）

使用示例:
    >>> from src.infrastructure.engines.match_engine.fotmob import create_fotmob_engine
    >>>
    >>> engine = create_fotmob_engine()
    >>> await engine.initialize()
    >>>
    >>> result = await engine.harvest_match(12345678)
    >>> print(f"Success: {result.success}")
    >>>
    >>> await engine.shutdown()

Author: [Genesis.UnifiedEngine]
Version: V145.0
Date: 2026-02-03
Migration: From src/collectors/fotmob_core.py V144.5
"""

from .fotmob_engine import (
    FotMobEngine,
    FotMobEngineConfig,
    create_fotmob_engine,
    harvest_fotmob_match,
)

__all__ = [
    "FotMobEngine",
    "FotMobEngineConfig",
    "create_fotmob_engine",
    "harvest_fotmob_match",
]
