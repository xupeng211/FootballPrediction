#!/usr/bin/env python3
"""
NetworkGuardian - V1.0.0 [Genesis.UnifiedEngine]
====================================================

NetworkShield 统一接口适配器 - 为 Python 收割引擎提供
与 Node.js QuantHarvester 相同的代理管理能力。

Core Features:
- 统一代理获取接口（get_next_healthy_proxy）
- 自动 Session 绑定（一个会话 = 一个 IP）
- 故障状态上报（mark_proxy_success / mark_proxy_failed）
- 会话管理（release_session）
- 跨语言状态同步（active_registry.json）

与 Node.js NetworkShield 的对应关系:
    Python                          Node.js
    NetworkGuardian                 NetworkShield
    get_next_healthy_proxy()        getNextHealthyProxy()
    mark_proxy_success()            markProxySuccess()
    mark_proxy_failed()             markProxyFailed()
    release_session()               releaseSession()
    get_status()                    getStatus()

Author: [Genesis.UnifiedEngine]
Version: V1.0.0
Date: 2026-02-03
"""

from __future__ import annotations

import logging
from pathlib import Path
import sys
from typing import Any, Dict, List, Optional

# 添加 NetworkShield Python 适配器路径
# 从 shared/ 目录向上 3 级到 infrastructure/，然后进入 network/python
_network_shield_path = Path(__file__).parent.parent.parent.parent / "network" / "python"
if str(_network_shield_path) not in sys.path:
    sys.path.insert(0, str(_network_shield_path))

try:
    from network_shield import NetworkShield as _NetworkShield
    from network_shield import ProxyAssignment, ProxyNode
    from network_shield import get_network_shield as _get_network_shield
except ImportError:
    # 降级：如果 NetworkShield 不可用，使用模拟实现
    _NetworkShield = None
    ProxyAssignment = None
    ProxyNode = None

# ============================================================================
# LOGGING
# ============================================================================

logger = logging.getLogger(__name__)


# ============================================================================
# DATA MODELS
# ============================================================================


class ProxyInfo:
    """
    代理信息（与 Node.js 兼容格式）

    Attributes:
        port: 代理端口
        url: 代理 URL
        id: 节点 ID
        health_score: 健康分数 (0-100)
        ip_address: IP 地址
        session_id: 会话 ID
    """

    def __init__(
        self,
        port: int,
        url: str,
        id: str,
        health_score: float,
        ip_address: Optional[str] = None,
        session_id: Optional[str] = None
    ):
        self.port = port
        self.url = url
        self.id = id
        self.health_score = health_score
        self.ip_address = ip_address
        self.session_id = session_id

    @classmethod
    def from_assignment(cls, assignment: Any) -> 'ProxyInfo':
        """从 ProxyAssignment 转换"""
        return cls(
            port=assignment.port,
            url=assignment.url,
            id=assignment.id,
            health_score=assignment.health_score,
            ip_address=assignment.ip_address,
            session_id=assignment.session_id
        )

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式（与 Node.js 兼容）"""
        return {
            "port": self.port,
            "url": self.url,
            "id": self.id,
            "health_score": self.health_score,
            "ip_address": self.ip_address,
            "sessionId": self.session_id
        }


# ============================================================================
# NETWORK GUARDIAN CLASS
# ============================================================================


class NetworkGuardian:
    """
    NetworkGuardian - NetworkShield 统一接口适配器

    为 Python 收割引擎提供与 Node.js QuantHarvester 相同的代理管理能力。
    内部使用 NetworkShield Python 适配器，通过 active_registry.json
    实现与 Node.js 端的跨语言状态同步。

    核心功能:
    1. 统一代理获取：按健康分数排序选择最优节点
    2. Session 绑定：确保一个会话始终使用同一 IP
    3. 故障上报：成功/失败状态写入 active_registry.json
    4. 会话管理：自动释放过期会话
    5. 状态查询：获取引擎和节点状态

    使用示例:
        >>> guardian = NetworkGuardian()
        >>> await guardian.initialize()
        >>>
        >>> # 获取代理（Session 绑定）
        >>> proxy = await guardian.get_next_healthy_proxy('session-123')
        >>> print(f"Using proxy: {proxy.url}")
        >>>
        >>> # 使用代理完成请求后...
        >>> await guardian.mark_proxy_success(proxy.port, latency_ms=150)
        >>>
        >>> # 或失败时
        >>> await guardian.mark_proxy_failed(proxy.port, 'Connection timeout')
        >>>
        >>> # 释放会话
        >>> guardian.release_session('session-123')
    """

    def __init__(
        self,
        proxy_host: str = "172.25.16.1",
        protocol: str = "http",
        log_level: str = "info"
    ):
        """
        初始化 NetworkGuardian

        Args:
            proxy_host: 代理主机
            protocol: 代理协议 (http/socks5)
            log_level: 日志级别
        """
        self.proxy_host = proxy_host
        self.protocol = protocol
        self.log_level = log_level

        # NetworkShield 实例（延迟初始化）
        self._shield = None
        self._initialized = False

        # Session 追踪
        self._sessions: Dict[str, str] = {}  # session_id -> match_id

        self.logger = logging.getLogger(f"NetworkGuardian")

    async def initialize(self) -> None:
        """
        初始化 NetworkGuardian

        加载 NetworkShield Python 适配器并验证连接。

        Raises:
            RuntimeError: NetworkShield 不可用
        """
        if _NetworkShield is None:
            raise RuntimeError(
                "NetworkShield Python adapter not found. "
                "Please ensure src/infrastructure/network/python/network_shield.py exists."
            )

        try:
            # 获取 NetworkShield 单例
            self._shield = _get_network_shield({
                "proxy_host": self.proxy_host,
                "protocol": self.protocol,
                "log_level": self.log_level
            })

            # 执行初始化（如果尚未初始化）
            # 注意：Python 适配器的初始化是同步的
            status = self._shield.get_status()

            self._initialized = True

            self.logger.info(
                f"[NetworkGuardian] Initialized: {status.get('nodes', {}).get('active', 0)}/"
                f"{status.get('nodes', {}).get('total', 0)} nodes available"
            )

        except Exception as e:
            raise RuntimeError(f"Failed to initialize NetworkShield: {e}")

    async def get_next_healthy_proxy(
        self,
        session_id: Optional[str] = None
    ) -> Optional[ProxyInfo]:
        """
        获取下一个健康的代理节点

        内部逻辑:
        1. 从 active_registry.json 读取所有节点
        2. 过滤掉冷却中和失效的节点
        3. 按健康分数 (health_score) 降序排序
        4. 选择分数最高的节点
        5. 创建 Session 绑定

        Args:
            session_id: 会话 ID（可选，用于 Session 绑定）

        Returns:
            ProxyInfo: 代理信息，如果无可用代理返回 None

        Raises:
            RuntimeError: 未初始化
        """
        if not self._initialized:
            raise RuntimeError("NetworkGuardian not initialized. Call initialize() first.")

        try:
            # 调用 NetworkShield 获取代理
            assignment = self._shield.get_next_healthy_proxy(session_id)

            if not assignment:
                self.logger.warning("[NetworkGuardian] No available proxies")
                return None

            # 转换为统一格式
            proxy_info = ProxyInfo.from_assignment(assignment)

            # 追踪会话
            if session_id:
                self._sessions[session_id] = session_id

            self.logger.debug(
                f"[NetworkGuardian] Assigned proxy port {proxy_info.port} "
                f"(health: {proxy_info.health_score:.1f}, session: {session_id})"
            )

            return proxy_info

        except Exception as e:
            self.logger.error(f"[NetworkGuardian] Failed to get proxy: {e}")
            return None

    async def get_proxy(self, session_id: str) -> Optional[ProxyInfo]:
        """
        获取代理（别名方法，兼容旧接口）

        Args:
            session_id: 会话 ID

        Returns:
            ProxyInfo: 代理信息
        """
        return await self.get_next_healthy_proxy(session_id)

    async def mark_proxy_success(
        self,
        port: int,
        latency: float = 0
    ) -> None:
        """
        标记代理成功

        成功状态将被写入 active_registry.json，
        Node.js QuantHarvester 将能读取到更新后的健康分数。

        Args:
            port: 代理端口
            latency: 延迟（毫秒）

        Raises:
            RuntimeError: 未初始化
        """
        if not self._initialized:
            raise RuntimeError("NetworkGuardian not initialized. Call initialize() first.")

        try:
            self._shield.mark_proxy_success(port, latency)
            self.logger.debug(f"[NetworkGuardian] Port {port} marked as SUCCESS")
        except Exception as e:
            self.logger.error(f"[NetworkGuardian] Failed to mark success: {e}")

    async def mark_proxy_failed(
        self,
        port: int,
        reason: str = "Unknown"
    ) -> None:
        """
        标记代理失败

        失败状态将被写入 active_registry.json：
        - 节点的 consecutive_failures +1
        - 达到 2 次后自动进入 15 分钟冷却期
        - 健康分数下降 10 分

        Node.js QuantHarvester 将能即时感知该 IP 失效并避免使用。

        Args:
            port: 代理端口
            reason: 失败原因

        Raises:
            RuntimeError: 未初始化
        """
        if not self._initialized:
            raise RuntimeError("NetworkGuardian not initialized. Call initialize() first.")

        try:
            self._shield.mark_proxy_failed(port, reason)
            self.logger.warning(f"[NetworkGuardian] Port {port} marked as FAILED: {reason}")
        except Exception as e:
            self.logger.error(f"[NetworkGuardian] Failed to mark failure: {e}")

    def release_session(self, session_id: str) -> None:
        """
        释放会话

        释放后，该端口可以被其他会话使用。

        Args:
            session_id: 会话 ID
        """
        if not self._initialized:
            return

        try:
            self._shield.release_session(session_id)

            if session_id in self._sessions:
                del self._sessions[session_id]

            self.logger.debug(f"[NetworkGuardian] Session {session_id} released")
        except Exception as e:
            self.logger.error(f"[NetworkGuardian] Failed to release session: {e}")

    def get_status(self) -> Dict[str, Any]:
        """
        获取引擎状态

        Returns:
            Dict: 状态信息，包括:
                - enabled: 是否启用
                - initialized: 是否已初始化
                - nodes: 节点统计 (total, active, cooled, available)
                - sessions: 会话统计
                - requests: 请求统计
                - avg_health_score: 平均健康分数
        """
        if not self._initialized:
            return {
                "enabled": False,
                "initialized": False
            }

        return self._shield.get_status()

    def get_available_nodes(self) -> List[Dict[str, Any]]:
        """
        获取可用节点列表

        Returns:
            List[Dict]: 节点信息列表，按健康分数降序排序
        """
        if not self._initialized:
            return []

        try:
            nodes = self._shield.get_available_nodes()
            return [node.__dict__ if hasattr(node, "__dict__") else node for node in nodes]
        except Exception as e:
            self.logger.error(f"[NetworkGuardian] Failed to get available nodes: {e}")
            return []

    def get_node(self, port: int) -> Optional[Dict[str, Any]]:
        """
        获取指定端口节点信息

        Args:
            port: 节点端口

        Returns:
            Optional[Dict]: 节点信息
        """
        if not self._initialized:
            return None

        try:
            node = self._shield.get_node(port)
            return node.__dict__ if hasattr(node, "__dict__") else node
        except Exception as e:
            self.logger.error(f"[NetworkGuardian] Failed to get node {port}: {e}")
            return None

    def reset_all_nodes(self) -> Dict[str, Any]:
        """
        重置所有节点状态

        清除所有冷却期和失败计数，将所有节点恢复到 active 状态。

        Returns:
            Dict: 重置后的状态
        """
        if not self._initialized:
            raise RuntimeError("NetworkGuardian not initialized. Call initialize() first.")

        try:
            result = self._shield.reset_all_nodes()
            self.logger.info("[NetworkGuardian] All nodes reset")
            return result
        except Exception as e:
            self.logger.error(f"[NetworkGuardian] Failed to reset nodes: {e}")
            raise

    def run_health_check(self) -> Dict[str, Any]:
        """
        手动触发健康检查

        Returns:
            Dict: 健康检查结果
        """
        if not self._initialized:
            raise RuntimeError("NetworkGuardian not initialized. Call initialize() first.")

        try:
            result = self._shield.run_health_check()
            self.logger.info("[NetworkGuardian] Health check completed")
            return result
        except Exception as e:
            self.logger.error(f"[NetworkGuardian] Health check failed: {e}")
            raise

    def shutdown(self) -> None:
        """关闭 NetworkGuardian"""
        # 释放所有会话
        for session_id in list(self._sessions.keys()):
            self.release_session(session_id)

        self._initialized = False
        self.logger.info("[NetworkGuardian] Shutdown complete")


# ============================================================================
# SINGLETON & FACTORY FUNCTIONS
# ============================================================================

_guardian_instance: Optional[NetworkGuardian] = None


def get_network_guardian(
    proxy_host: str = "172.25.16.1",
    protocol: str = "http",
    log_level: str = "info",
    force_new: bool = False
) -> NetworkGuardian:
    """
    获取 NetworkGuardian 单例

    Args:
        proxy_host: 代理主机
        protocol: 代理协议
        log_level: 日志级别
        force_new: 是否强制创建新实例

    Returns:
        NetworkGuardian: 单例实例
    """
    global _guardian_instance

    if _guardian_instance is None or force_new:
        _guardian_instance = NetworkGuardian(
            proxy_host=proxy_host,
            protocol=protocol,
            log_level=log_level
        )

    return _guardian_instance


def reset_network_guardian() -> None:
    """重置 NetworkGuardian 单例（用于测试）"""
    global _guardian_instance

    if _guardian_instance:
        _guardian_instance.shutdown()
        _guardian_instance = None


# ============================================================================
# CONVENIENCE FUNCTIONS
# ============================================================================

async def get_proxy(session_id: str) -> Optional[ProxyInfo]:
    """
    便捷函数：获取代理

    Args:
        session_id: 会话 ID

    Returns:
        ProxyInfo: 代理信息
    """
    guardian = get_network_guardian()
    if not guardian._initialized:
        await guardian.initialize()
    return await guardian.get_proxy(session_id)


async def mark_success(port: int, latency: float = 0) -> None:
    """
    便捷函数：标记成功

    Args:
        port: 代理端口
        latency: 延迟（毫秒）
    """
    guardian = get_network_guardian()
    await guardian.mark_proxy_success(port, latency)


async def mark_failed(port: int, reason: str = "Unknown") -> None:
    """
    便捷函数：标记失败

    Args:
        port: 代理端口
        reason: 失败原因
    """
    guardian = get_network_guardian()
    await guardian.mark_proxy_failed(port, reason)


def release_session(session_id: str) -> None:
    """
    便捷函数：释放会话

    Args:
        session_id: 会话 ID
    """
    guardian = get_network_guardian()
    guardian.release_session(session_id)
