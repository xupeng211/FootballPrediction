#!/usr/bin/env python3
"""
Dynamic Discovery Engine - V1.1.0 [Genesis.L1Evolution]
=========================================================

L1 动态发现引擎 - 双模降级架构

Author: [Genesis.L1Evolution]
Version: V1.1.0
Date: 2026-02-03
"""

from .dynamic_discovery_engine import (
    DynamicDiscoveryEngine,
    DiscoveryConfig,
    DiscoveryMode,
    DiscoveryResult,
    DiscoveryStatus,
    DiscoveryStrategy,
    ApiDiscoveryStrategy,
    DomDiscoveryStrategy,
    CrossPlatformDiscoveryStrategy,
    MatchInfo,
    discover_championship_2025,
)
from .discovery_engine_v2 import (
    UnifiedDiscoveryEngine,
    create_unified_discovery_engine,
)

__all__ = [
    # Core Engine
    "DynamicDiscoveryEngine",
    "UnifiedDiscoveryEngine",
    # Data Models
    "DiscoveryConfig",
    "DiscoveryMode",
    "DiscoveryResult",
    "DiscoveryStatus",
    "MatchInfo",
    # Strategies
    "DiscoveryStrategy",
    "ApiDiscoveryStrategy",
    "DomDiscoveryStrategy",
    "CrossPlatformDiscoveryStrategy",
    # Factory Functions
    "discover_championship_2025",
    "create_unified_discovery_engine",
]
