"""
Core Proxy Management Module

This module provides proxy configuration, health checking, and guardian services
for network operations in the FootballPrediction system.

Components:
- proxy_manager: Proxy configuration and URL management
- proxy_guardian: Proxy protection and circuit breaking
- proxy_health_checker: Proxy health monitoring and validation
"""

from src.core.proxy.proxy_guardian import ProxyGuardian
from src.core.proxy.proxy_health_checker import ProxyHealthChecker
from src.core.proxy.proxy_manager import ProxyManager

__all__ = [
    "ProxyGuardian",
    "ProxyHealthChecker",
    "ProxyManager",
]
