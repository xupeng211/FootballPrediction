#!/usr/bin/env python3
"""
V41.156 "幽灵网络" - Proxy Manager
=====================================

功能:
- 随机轮询代理池（避免固定模式）
- "脏 IP" 自动剔除机制（403/429 禁封 30 分钟）
- 并发安全设计
- 代理健康度追踪

Author: V41.156 Infrastructure Engineer
Date: 2026-01-17
"""

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
import logging
import random
import socket
import threading
import time
from typing import Dict, List, Optional, Tuple

from pydantic import BaseModel, Field, field_validator


# ============================================================================
# 枚举定义
# ============================================================================

class ProxyStatus(str, Enum):
    """代理状态枚举"""
    ACTIVE = "active"       # 正常可用
    DIRTY = "dirty"         # 临时禁用（403/429）
    BANNED = "banned"       # 永久禁用
    UNHEALTHY = "unhealthy" # 健康检查失败


# ============================================================================
# 数据模型
# ============================================================================

@dataclass
class ProxyEndpoint:
    """代理端点信息

    Attributes:
        host: 代理主机地址
        port: 代理端口
        url: 完整代理 URL (http://host:port)
        status: 当前状态
        dirty_until: 脏 IP 解封时间
        fail_count: 连续失败次数
        success_count: 成功请求次数
        last_used: 最后使用时间
        last_error: 最后一次错误
    """

    host: str
    port: int
    status: ProxyStatus = ProxyStatus.ACTIVE
    dirty_until: Optional[datetime] = None
    fail_count: int = 0
    success_count: int = 0
    last_used: Optional[datetime] = None
    last_error: Optional[str] = None

    @property
    def url(self) -> str:
        """获取完整代理 URL"""
        return f"http://{self.host}:{self.port}"

    @property
    def is_available(self) -> bool:
        """检查代理是否可用"""
        if self.status in [ProxyStatus.BANNED, ProxyStatus.UNHEALTHY]:
            return False

        if self.status == ProxyStatus.DIRTY:
            if self.dirty_until and datetime.now() < self.dirty_until:
                return False
            # 解封时间已过，恢复为活跃状态
            self.status = ProxyStatus.ACTIVE
            self.dirty_until = None

        return True

    def mark_dirty(self, duration_seconds: int = 1800) -> None:
        """标记为脏 IP（临时禁用）

        Args:
            duration_seconds: 禁用时长（默认 30 分钟）
        """
        self.status = ProxyStatus.DIRTY
        self.dirty_until = datetime.now() + timedelta(seconds=duration_seconds)
        self.fail_count += 1

    def mark_banned(self) -> None:
        """标记为永久禁用"""
        self.status = ProxyStatus.BANNED

    def mark_unhealthy(self) -> None:
        """标记为不健康"""
        self.status = ProxyStatus.UNHEALTHY

    def record_success(self) -> None:
        """记录成功请求"""
        self.status = ProxyStatus.ACTIVE
        self.dirty_until = None
        self.success_count += 1
        self.fail_count = 0
        self.last_used = datetime.now()

    def record_failure(self, error: Optional[str] = None) -> None:
        """记录失败请求"""
        self.fail_count += 1
        self.last_used = datetime.now()
        self.last_error = error


class ProxyConfig(BaseModel):
    """代理池配置

    Attributes:
        hosts: 代理主机列表（支持多个不同主机）
        ports: 代理端口列表（单个主机的多个端口）
        ban_duration_seconds: 脏 IP 禁用时长（默认 30 分钟）
        max_failures: 最大连续失败次数后永久禁用
        enable_health_check: 是否启用健康检查
        health_check_timeout_seconds: 健康检查超时时间
        rotation_strategy: 轮换策略 (random, round_robin, weighted)
    """

    hosts: List[str] = Field(default_factory=lambda: ["172.25.16.1"])
    ports: List[int] = Field(
        default_factory=lambda: [7890, 7891, 7892, 7893, 7894, 7895, 7896, 7897, 7898, 7899]
    )
    ban_duration_seconds: int = Field(default=1800, ge=60, le=86400)  # 1分钟 - 24小时
    max_failures: int = Field(default=10, ge=3, le=100)
    enable_health_check: bool = True
    health_check_timeout_seconds: float = Field(default=5.0, ge=1.0, le=30.0)
    rotation_strategy: str = Field(default="random", pattern="^(random|round_robin|weighted)$")

    @field_validator("ports")
    @classmethod
    def validate_ports(cls, v: List[int]) -> List[int]:
        """验证代理端口"""
        if not v:
            raise ValueError("代理端口列表不能为空")
        for port in v:
            if not (1 <= port <= 65535):
                raise ValueError(f"无效的代理端口: {port}")
        return v

    @field_validator("hosts")
    @classmethod
    def validate_hosts(cls, v: List[str]) -> List[str]:
        """验证代理主机"""
        if not v:
            raise ValueError("代理主机列表不能为空")
        return v


# ============================================================================
# Proxy Manager - 核心类
# ============================================================================

class ProxyManager:
    """V41.156 代理池管理器

    功能:
    - 随机轮询代理池
    - 自动剔除脏 IP（403/429 禁封 30 分钟）
    - 并发安全设计
    - 代理健康度追踪

    使用方式:
        proxy_config = ProxyConfig(
            hosts=["172.25.16.1"],
            ports=[7890, 7891, 7892, 7893, 7894]
        )
        manager = ProxyManager(proxy_config)

        # 获取可用代理
        proxy = manager.get_proxy()

        # 记录成功/失败
        manager.record_success(proxy)
        manager.record_failure(proxy, 403)  # 会自动标记为脏 IP
    """

    def __init__(self, config: Optional[ProxyConfig] = None):
        """初始化代理管理器

        Args:
            config: 代理配置
        """
        self.config = config or ProxyConfig()
        self.endpoints: List[ProxyEndpoint] = []
        self._round_robin_index = 0
        self._lock = threading.Lock()
        self._logger = logging.getLogger(__name__)

        # 初始化代理端点
        self._initialize_endpoints()

        # 启动时进行健康检查
        if self.config.enable_health_check:
            self._health_check_all()

    def _initialize_endpoints(self) -> None:
        """初始化代理端点列表"""
        self.endpoints = []
        for host in self.config.hosts:
            for port in self.config.ports:
                self.endpoints.append(ProxyEndpoint(host=host, port=port))

        self._logger.info(
            f"代理池初始化完成: {len(self.endpoints)} 个端点 "
            f"({len(self.config.hosts)} 主机 x {len(self.config.ports)} 端口)"
        )

    def _health_check_all(self) -> None:
        """对所有代理进行健康检查"""
        self._logger.info("开始代理健康检查...")

        available_count = 0
        for endpoint in self.endpoints:
            if self._check_endpoint_health(endpoint):
                available_count += 1
            else:
                endpoint.mark_unhealthy()

        self._logger.info(
            f"健康检查完成: {available_count}/{len(self.endpoints)} 个端点可用"
        )

    def _check_endpoint_health(self, endpoint: ProxyEndpoint) -> bool:
        """检查单个端点健康状态

        Args:
            endpoint: 代理端点

        Returns:
            True 如果健康，False 否则
        """
        try:
            start_time = time.time()
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(self.config.health_check_timeout_seconds)
            result = sock.connect_ex((endpoint.host, endpoint.port))
            sock.close()

            if result == 0:
                latency_ms = (time.time() - start_time) * 1000
                self._logger.debug(
                    f"代理 {endpoint.url} 健康检查通过 ({latency_ms:.0f}ms)"
                )
                return True
            else:
                self._logger.warning(
                    f"代理 {endpoint.url} 健康检查失败: 连接被拒绝"
                )
                return False

        except socket.timeout:
            self._logger.warning(
                f"代理 {endpoint.url} 健康检查失败: 超时"
            )
            return False
        except Exception as e:
            self._logger.warning(
                f"代理 {endpoint.url} 健康检查失败: {e}"
            )
            return False

    def get_proxy(self) -> Optional[str]:
        """获取一个可用的代理 URL

        根据配置的轮换策略选择代理:
        - random: 随机选择（默认，推荐）
        - round_robin: 轮询选择
        - weighted: 根据成功率加权选择

        Returns:
            代理 URL，如果没有可用代理则返回 None
        """
        with self._lock:
            available_endpoints = [e for e in self.endpoints if e.is_available]

            if not available_endpoints:
                self._logger.error("没有可用的代理端点！")
                return None

            if self.config.rotation_strategy == "random":
                endpoint = random.choice(available_endpoints)

            elif self.config.rotation_strategy == "round_robin":
                endpoint = available_endpoints[
                    self._round_robin_index % len(available_endpoints)
                ]
                self._round_robin_index += 1

            elif self.config.rotation_strategy == "weighted":
                # 根据成功率加权选择
                weights = []
                for e in available_endpoints:
                    total = e.success_count + e.fail_count
                    if total > 0:
                        weight = e.success_count / total
                    else:
                        weight = 1.0  # 新代理给予默认权重
                    weights.append(max(0.1, weight))  # 最小权重 0.1

                # 归一化权重
                total_weight = sum(weights)
                weights = [w / total_weight for w in weights]

                endpoint = random.choices(available_endpoints, weights=weights, k=1)[0]

            else:
                # 默认使用随机
                endpoint = random.choice(available_endpoints)

            self._logger.debug(
                f"选择代理: {endpoint.url} "
                f"(策略: {self.config.rotation_strategy})"
            )

            return endpoint.url

    def get_proxy_with_endpoint(self) -> Optional[Tuple[str, ProxyEndpoint]]:
        """获取代理 URL 和对应的端点对象

        Returns:
            (代理 URL, ProxyEndpoint) 元组，如果没有可用代理则返回 None
        """
        with self._lock:
            available_endpoints = [e for e in self.endpoints if e.is_available]

            if not available_endpoints:
                self._logger.error("没有可用的代理端点！")
                return None

            if self.config.rotation_strategy == "random":
                endpoint = random.choice(available_endpoints)

            elif self.config.rotation_strategy == "round_robin":
                endpoint = available_endpoints[
                    self._round_robin_index % len(available_endpoints)
                ]
                self._round_robin_index += 1

            elif self.config.rotation_strategy == "weighted":
                # 根据成功率加权选择
                weights = []
                for e in available_endpoints:
                    total = e.success_count + e.fail_count
                    if total > 0:
                        weight = e.success_count / total
                    else:
                        weight = 1.0
                    weights.append(max(0.1, weight))

                total_weight = sum(weights)
                weights = [w / total_weight for w in weights]

                endpoint = random.choices(available_endpoints, weights=weights, k=1)[0]

            else:
                endpoint = random.choice(available_endpoints)

            return endpoint.url, endpoint

    def record_success(self, proxy_url: str) -> None:
        """记录代理成功请求

        Args:
            proxy_url: 代理 URL
        """
        with self._lock:
            for endpoint in self.endpoints:
                if endpoint.url == proxy_url:
                    endpoint.record_success()
                    self._logger.debug(
                        f"代理 {proxy_url} 成功 "
                        f"(成功率: {endpoint.success_count}/{endpoint.success_count + endpoint.fail_count})"
                    )
                    return

    def record_failure(
        self,
        proxy_url: str,
        status_code: Optional[int] = None,
        error: Optional[str] = None
    ) -> None:
        """记录代理失败请求

        Args:
            proxy_url: 代理 URL
            status_code: HTTP 状态码（如果适用）
            error: 错误信息

        注意:
        - 403 (Forbidden): 自动标记为脏 IP，禁封 30 分钟
        - 429 (Too Many Requests): 自动标记为脏 IP，禁封 30 分钟
        - 连续失败超过 max_failures: 永久禁用
        """
        with self._lock:
            for endpoint in self.endpoints:
                if endpoint.url == proxy_url:
                    # 检查是否需要标记为脏 IP
                    if status_code in [403, 429]:
                        endpoint.mark_dirty(self.config.ban_duration_seconds)
                        self._logger.warning(
                            f"代理 {proxy_url} 返回 {status_code}，"
                            f"已标记为脏 IP，禁封 {self.config.ban_duration_seconds} 秒"
                        )
                        return

                    # 记录失败
                    endpoint.record_failure(error)

                    # 检查是否超过最大失败次数
                    if endpoint.fail_count >= self.config.max_failures:
                        endpoint.mark_banned()
                        self._logger.error(
                            f"代理 {proxy_url} 连续失败 {endpoint.fail_count} 次，"
                            f"已永久禁用"
                        )
                    else:
                        self._logger.debug(
                            f"代理 {proxy_url} 失败 "
                            f"(失败次数: {endpoint.fail_count}/{self.config.max_failures})"
                        )
                    return

    def get_stats(self) -> Dict:
        """获取代理池统计信息

        Returns:
            统计信息字典
        """
        with self._lock:
            active_count = sum(1 for e in self.endpoints if e.status == ProxyStatus.ACTIVE)
            dirty_count = sum(1 for e in self.endpoints if e.status == ProxyStatus.DIRTY)
            banned_count = sum(1 for e in self.endpoints if e.status == ProxyStatus.BANNED)
            unhealthy_count = sum(1 for e in self.endpoints if e.status == ProxyStatus.UNHEALTHY)

            total_requests = sum(e.success_count + e.fail_count for e in self.endpoints)
            total_success = sum(e.success_count for e in self.endpoints)

            return {
                "total_endpoints": len(self.endpoints),
                "active": active_count,
                "dirty": dirty_count,
                "banned": banned_count,
                "unhealthy": unhealthy_count,
                "total_requests": total_requests,
                "total_success": total_success,
                "success_rate": round(total_success / total_requests * 100, 2) if total_requests > 0 else 0,
                "rotation_strategy": self.config.rotation_strategy,
                "ban_duration_seconds": self.config.ban_duration_seconds,
            }

    def get_detailed_stats(self) -> List[Dict]:
        """获取详细的端点统计信息

        Returns:
            端点详情列表
        """
        with self._lock:
            details = []
            for endpoint in self.endpoints:
                total = endpoint.success_count + endpoint.fail_count
                details.append({
                    "url": endpoint.url,
                    "status": endpoint.status.value,
                    "success_count": endpoint.success_count,
                    "fail_count": endpoint.fail_count,
                    "success_rate": round(endpoint.success_count / total * 100, 2) if total > 0 else 0,
                    "last_used": endpoint.last_used.isoformat() if endpoint.last_used else None,
                    "last_error": endpoint.last_error,
                    "dirty_until": endpoint.dirty_until.isoformat() if endpoint.dirty_until else None,
                })
            return details

    def recover_dirty_proxies(self) -> int:
        """手动恢复所有脏 IP（用于测试或紧急情况）

        Returns:
            恢复的端点数量
        """
        with self._lock:
            recovered_count = 0
            for endpoint in self.endpoints:
                if endpoint.status == ProxyStatus.DIRTY:
                    endpoint.status = ProxyStatus.ACTIVE
                    endpoint.dirty_until = None
                    endpoint.fail_count = 0
                    recovered_count += 1

            self._logger.info(f"手动恢复了 {recovered_count} 个脏 IP")
            return recovered_count

    def reset_all_stats(self) -> None:
        """重置所有统计信息（用于测试）"""
        with self._lock:
            for endpoint in self.endpoints:
                endpoint.status = ProxyStatus.ACTIVE
                endpoint.dirty_until = None
                endpoint.fail_count = 0
                endpoint.success_count = 0
                endpoint.last_used = None
                endpoint.last_error = None

            self._round_robin_index = 0
            self._logger.info("所有代理统计信息已重置")


# ============================================================================
# 单例实例
# ============================================================================

_global_proxy_manager: Optional[ProxyManager] = None


def get_proxy_manager(config: Optional[ProxyConfig] = None) -> ProxyManager:
    """获取全局代理管理器单例

    Args:
        config: 代理配置（仅在首次调用时使用）

    Returns:
        ProxyManager 实例
    """
    global _global_proxy_manager
    if _global_proxy_manager is None:
        _global_proxy_manager = ProxyManager(config)
    return _global_proxy_manager


# ============================================================================
# 导出
# ============================================================================

__all__ = [
    "ProxyStatus",
    "ProxyEndpoint",
    "ProxyConfig",
    "ProxyManager",
    "get_proxy_manager",
]
