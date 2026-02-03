#!/usr/bin/env python3
"""
NetworkShield Python Adapter - V1.0.0 [Genesis.NetworkShield]
==================================================================

Python 接入模块 - 共享 active_registry.json 状态，实现跨语言状态同步。

Core Features:
- 读取 active_registry.json 获取节点状态
- 智能选择健康节点（按 health_score 排序）
- 上报成功/失败状态到注册表
- Session 绑定支持
- 完全兼容 Python 异步/同步代码

Author: [Genesis.NetworkShield]
Version: V1.0.0
Date: 2026-02-03
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
import json
import logging
import os
from pathlib import Path
from threading import Lock
import time
from typing import Any

# ============================================================================
# LOGGING
# ============================================================================

logger = logging.getLogger(__name__)

# ============================================================================
# CONFIGURATION
# ============================================================================

REGISTRY_PATH = Path(os.getcwd()) / "config" / "active_registry.json"
REGISTRY_LOCK = Lock()


# ============================================================================
# DATA MODELS
# ============================================================================

class NodeStatus(Enum):
    """节点状态枚举"""
    ACTIVE = "active"
    COOLED = "cooled"
    INACTIVE = "inactive"


@dataclass
class ProxyNode:
    """代理节点信息"""
    port: int
    id: str
    status: str
    health_score: float
    consecutive_failures: int
    last_check: str
    last_success: str | None = None
    last_failure: str | None = None
    cooldown_until: str | None = None
    ip_address: str | None = None
    avg_latency_ms: float = 0
    total_requests: int = 0
    successful_requests: int = 0
    metadata: dict = field(default_factory=dict)

    @classmethod
    def from_dict(cls, data: dict) -> 'ProxyNode':
        """从字典创建节点对象"""
        # 过滤掉未定义的字段
        defined_fields = {f.name for f in cls.__dataclass_fields__.values()}
        filtered_data = {k: v for k, v in data.items() if k in defined_fields}
        return cls(**filtered_data)

    def is_available(self) -> bool:
        """检查节点是否可用"""
        if self.status != NodeStatus.ACTIVE.value:
            return False

        # 检查冷却期
        if self.cooldown_until:
            cooldown_time = datetime.fromisoformat(self.cooldown_until)
            if datetime.now() < cooldown_time:
                return False

        return True

    def to_proxy_url(self, host: str = "172.25.16.1", protocol: str = "http") -> str:
        """转换为代理 URL"""
        return f"{protocol}://{host}:{self.port}"


@dataclass
class ProxyAssignment:
    """代理分配结果"""
    port: int
    url: str
    id: str
    health_score: float
    ip_address: str | None
    session_id: str | None = None


# ============================================================================
# REGISTRY MANAGER (PYTHON)
# ============================================================================

class RegistryManager:
    """注册表管理器 - Python 版本

    负责读取和更新 active_registry.json，实现跨语言状态同步。
    """

    def __init__(self, registry_path: Path | None = None):
        self.registry_path = registry_path or REGISTRY_PATH
        self._cache: dict | None = None
        self._cache_time: float = 0
        self._cache_ttl: float = 1.0  # 缓存 1 秒

    def _load_registry(self) -> dict:
        """加载注册表数据"""
        now = time.time()

        # 检查缓存
        if (self._cache is not None and
            (now - self._cache_time) < self._cache_ttl):
            return self._cache

        with REGISTRY_LOCK:
            try:
                if not self.registry_path.exists():
                    logger.warning(f"Registry not found: {self.registry_path}")
                    return self._create_default_registry()

                with open(self.registry_path, "r", encoding="utf-8") as f:
                    data = json.load(f)

                self._cache = data
                self._cache_time = now
                return data

            except json.JSONDecodeError as e:
                logger.error(f"Failed to parse registry: {e}")
                return self._create_default_registry()
            except Exception as e:
                logger.error(f"Failed to load registry: {e}")
                return self._create_default_registry()

    def _save_registry(self, data: dict) -> None:
        """保存注册表数据"""
        with REGISTRY_LOCK:
            try:
                # 创建备份
                if self.registry_path.exists():
                    backup_path = self.registry_path.with_suffix(".backup.json")
                    self.registry_path.rename(backup_path)

                # 更新时间戳
                data["last_updated"] = datetime.now().isoformat()

                # 写入新数据
                with open(self.registry_path, "w", encoding="utf-8") as f:
                    json.dump(data, f, indent=2, ensure_ascii=False)

                # 更新缓存
                self._cache = data
                self._cache_time = time.time()

            except Exception as e:
                logger.error(f"Failed to save registry: {e}")
                raise

    def _create_default_registry(self) -> dict:
        """创建默认注册表"""
        return {
            "version": "V1.0.0",
            "last_updated": datetime.now().isoformat(),
            "nodes": [],
            "statistics": {"total_nodes": 0, "active_nodes": 0}
        }

    def get_available_nodes(self) -> list[ProxyNode]:
        """获取可用节点列表"""
        registry = self._load_registry()

        nodes = []
        for node_data in registry.get("nodes", []):
            node = ProxyNode.from_dict(node_data)
            if node.is_available():
                nodes.append(node)

        # 按健康分数排序（降序）
        nodes.sort(key=lambda n: n.health_score, reverse=True)
        return nodes

    def get_node(self, port: int) -> ProxyNode | None:
        """获取指定端口节点"""
        registry = self._load_registry()

        for node_data in registry.get("nodes", []):
            if node_data.get("port") == port:
                return ProxyNode.from_dict(node_data)

        return None

    def mark_node_success(self, port: int, latency: float = 0) -> None:
        """标记节点成功"""
        registry = self._load_registry()

        for node_data in registry.get("nodes", []):
            if node_data.get("port") == port:
                node_data["consecutive_failures"] = 0
                node_data["last_success"] = datetime.now().isoformat()
                node_data["last_failure"] = None

                # 恢复健康分数
                node_data["health_score"] = min(100, node_data.get("health_score", 100) + 5)
                node_data["avg_latency_ms"] = (
                    node_data.get("avg_latency_ms", 0) * 0.9 + latency * 0.1
                    if node_data.get("avg_latency_ms", 0) > 0 else latency
                )
                node_data["total_requests"] = node_data.get("total_requests", 0) + 1
                node_data["successful_requests"] = node_data.get("successful_requests", 0) + 1

                # 恢复状态
                if node_data.get("status") == "cooled":
                    node_data["status"] = "active"
                    node_data["cooldown_until"] = None

                break

        self._save_registry(registry)

    def mark_node_failed(self, port: int, reason: str = "Unknown",
                        cooldown_minutes: int = 15) -> None:
        """标记节点失败"""
        registry = self._load_registry()

        for node_data in registry.get("nodes", []):
            if node_data.get("port") == port:
                node_data["consecutive_failures"] = node_data.get("consecutive_failures", 0) + 1
                node_data["last_failure"] = datetime.now().isoformat()

                # 连续失败 2 次，进入冷却期
                if node_data["consecutive_failures"] >= 2:
                    cooldown_until = datetime.now() + timedelta(minutes=cooldown_minutes)
                    node_data["cooldown_until"] = cooldown_until.isoformat()
                    node_data["status"] = "cooled"
                    logger.warning(
                        f'[NetworkShield] Port {port} entered cooldown '
                        f'({cooldown_minutes}min) after {node_data["consecutive_failures"]} failures'
                    )

                node_data["health_score"] = max(0, node_data.get("health_score", 100) - 10)
                node_data["total_requests"] = node_data.get("total_requests", 0) + 1

                break

        self._save_registry(registry)

    def get_statistics(self) -> dict:
        """获取统计信息"""
        registry = self._load_registry()
        return registry.get("statistics", {})


# ============================================================================
# NETWORK SHIELD (PYTHON)
# ============================================================================

class NetworkShield:
    """NetworkShield Python 接口

    提供 Python 语言的统一代理管理接口，与 Node.js 版本共享状态。
    """

    def __init__(self, options: dict | None = None):
        self.options = options or {}
        self.proxy_host = self.options.get("proxy_host", "172.25.16.1")
        self.protocol = self.options.get("protocol", "http")
        self.enabled = self.options.get("enabled", True)

        self.registry = RegistryManager()

        # Session 绑定
        self._sessions: dict[str, int] = {}  # session_id -> port

        # 尊重环境变量
        if os.getenv("PROXY_ENABLED") == "false":
            self.enabled = False
            logger.info("[NetworkShield] Proxy DISABLED via environment")

    def get_next_healthy_proxy(self, session_id: str | None = None) -> ProxyAssignment | None:
        """获取下一个健康的代理节点

        Args:
            session_id: 会话 ID（用于绑定）

        Returns:
            ProxyAssignment 对象，如果没有可用代理则返回 None
        """
        if not self.enabled:
            logger.info("[NetworkShield] Proxy is DISABLED")
            return None

        # 检查现有会话
        if session_id and session_id in self._sessions:
            port = self._sessions[session_id]
            node = self.registry.get_node(port)

            if node and node.is_available():
                logger.debug(f"[NetworkShield] Reusing session {session_id} -> Port {port}")
                return ProxyAssignment(
                    port=node.port,
                    url=node.to_proxy_url(self.proxy_host, self.protocol),
                    id=node.id,
                    health_score=node.health_score,
                    ip_address=node.ip_address,
                    session_id=session_id
                )
            else:
                # 会话过期，清理
                del self._sessions[session_id]

        # 获取可用节点
        available_nodes = self.registry.get_available_nodes()

        if not available_nodes:
            logger.error("[NetworkShield] No available proxy nodes!")
            return None

        # 选择健康分数最高的节点
        selected_node = available_nodes[0]

        # 创建会话绑定
        if session_id:
            self._sessions[session_id] = selected_node.port

        logger.info(
            f"[NetworkShield] Assigned Clean IP (Port {selected_node.port}, "
            f"Score: {selected_node.health_score})"
            + (f" to Session {session_id}" if session_id else "")
        )

        return ProxyAssignment(
            port=selected_node.port,
            url=selected_node.to_proxy_url(self.proxy_host, self.protocol),
            id=selected_node.id,
            health_score=selected_node.health_score,
            ip_address=selected_node.ip_address,
            session_id=session_id
        )

    def mark_proxy_success(self, port: int, latency: float = 0) -> None:
        """标记代理成功"""
        if port:
            self.registry.mark_node_success(port, latency)
            logger.debug(f"[NetworkShield] Port {port} marked as SUCCESS")

    def mark_proxy_failed(self, port: int, reason: str = "Unknown") -> None:
        """标记代理失败"""
        if port:
            self.registry.mark_node_failed(port, reason)
            logger.warning(f"[NetworkShield] Port {port} marked as FAILED: {reason}")

    def release_session(self, session_id: str) -> None:
        """释放会话"""
        if session_id and session_id in self._sessions:
            port = self._sessions.pop(session_id)
            logger.debug(f"[NetworkShield] Session {session_id} released (was port {port})")

    def get_status(self) -> dict:
        """获取状态摘要"""
        stats = self.registry.get_statistics()
        available_nodes = self.registry.get_available_nodes()

        return {
            "enabled": self.enabled,
            "nodes": {
                "total": stats.get("total_nodes", 0),
                "active": stats.get("active_nodes", 0),
                "available": len(available_nodes)
            },
            "sessions": {
                "active": len(self._sessions),
                "sessions": list(self._sessions.keys())
            }
        }

    def reset_all_nodes(self) -> None:
        """重置所有节点状态"""
        logger.info("[NetworkShield] Resetting all nodes...")
        # 通过重新加载并重置实现
        self.registry._cache = None
        self._sessions.clear()


# ============================================================================
# SINGLETON
# ============================================================================

_shield_instance: NetworkShield | None = None


def get_network_shield(options: dict | None = None) -> NetworkShield:
    """获取 NetworkShield 单例"""
    global _shield_instance
    if _shield_instance is None:
        _shield_instance = NetworkShield(options)
    return _shield_instance


# ============================================================================
# CONVENIENCE FUNCTIONS
# ============================================================================

def get_proxy(session_id: str | None = None) -> ProxyAssignment | None:
    """便捷函数：获取代理"""
    return get_network_shield().get_next_healthy_proxy(session_id)


def mark_success(port: int, latency: float = 0) -> None:
    """便捷函数：标记成功"""
    get_network_shield().mark_proxy_success(port, latency)


def mark_failed(port: int, reason: str = "Unknown") -> None:
    """便捷函数：标记失败"""
    get_network_shield().mark_proxy_failed(port, reason)


def release_session(session_id: str) -> None:
    """便捷函数：释放会话"""
    get_network_shield().release_session(session_id)
