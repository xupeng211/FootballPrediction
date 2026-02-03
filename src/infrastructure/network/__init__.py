"""
NetworkShield - V1.0.0 [Genesis.NetworkShield]
================================================

工业级跨语言代理管理组件

This package provides unified proxy management across Python and Node.js:

    from src.infrastructure.network.python import NetworkShield, get_proxy

    # Get a healthy proxy
    assignment = get_proxy(session_id="my-session")
    if assignment:
        print(f"Using proxy: {assignment.url}")
        print(f"Health score: {assignment.health_score}")

        # Mark result
        mark_success(assignment.port)
        # or
        mark_failed(assignment.port, reason="Connection timeout")

        # Release when done
        release_session("my-session")

Core Components:
    - NetworkShield: Main proxy management class
    - RegistryManager: Manages active_registry.json state
    - ProxyNode: Represents a proxy node
    - ProxyAssignment: Represents a proxy assignment result
"""

from .python.network_shield import (
    NetworkShield,
    NodeStatus,
    ProxyAssignment,
    ProxyNode,
    get_network_shield,
    get_proxy,
    mark_failed,
    mark_success,
    release_session,
)

__all__ = [
    "NetworkShield",
    "NodeStatus",
    "ProxyAssignment",
    "ProxyNode",
    "get_network_shield",
    "get_proxy",
    "mark_failed",
    "mark_success",
    "release_session",
]

__version__ = "1.0.0"
__author__ = "[Genesis.NetworkShield]"
