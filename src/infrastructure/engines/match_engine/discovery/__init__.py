#!/usr/bin/env python3
"""
DiscoveryEngine Module - V146.0 [Genesis.L1Shield]
===================================================

L1 索引引擎 - 负责扫描列表页获取 Match ID

核心功能:
- 扫描联赛列表页获取比赛 ID
- 使用 NetworkShield 统一代理管理
- 随机脉冲延迟模拟人类浏览
- 失败状态同步到 active_registry.json

使用示例:
    >>> from src.infrastructure.engines.match_engine.discovery import create_discovery_engine
    >>>
    >>> engine = create_discovery_engine()
    >>> await engine.initialize()
    >>>
    >>> # 发现联赛比赛
    >>> result = await engine.discover_league(league_id="PL", season="2023-2024")
    >>> print(f"Found {len(result.data['match_ids'])} matches")
    >>>
    >>> await engine.shutdown()

Author: [Genesis.L1Shield]
Version: V146.0
Date: 2026-02-03
Migration: From scripts/run_discovery.py V120.0
"""

from .discovery_engine import (
    DiscoveryEngine,
    DiscoveryEngineConfig,
    DiscoveryResult,
    DiscoveryStrategy,
    create_discovery_engine,
    discover_league_matches,
)

__all__ = [
    "DiscoveryEngine",
    "DiscoveryEngineConfig",
    "DiscoveryResult",
    "DiscoveryStrategy",
    "create_discovery_engine",
    "discover_league_matches",
]
