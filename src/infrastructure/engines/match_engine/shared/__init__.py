#!/usr/bin/env python3
"""
Shared Components - V1.0.0 [Genesis.UnifiedEngine]
====================================================

共享组件模块 - 提供所有引擎共用的基础设施。

Core Components:
- NetworkGuardian: NetworkShield 统一接口适配器
- UnifiedCircuitBreaker: 统一熔断器实现（整合 7 个碎片化版本）

Author: [Genesis.UnifiedEngine]
Version: V1.0.0
Date: 2026-02-03
"""

from .circuit_breaker import (
    CircuitBreakerConfig,
    CircuitBreakerState,
    UnifiedCircuitBreaker,
    get_circuit_breaker,
)
from .network_guardian import NetworkGuardian, get_network_guardian

__all__ = [
    "CircuitBreakerConfig",
    "CircuitBreakerState",
    "NetworkGuardian",
    "UnifiedCircuitBreaker",
    "get_circuit_breaker",
    "get_network_guardian",
]
