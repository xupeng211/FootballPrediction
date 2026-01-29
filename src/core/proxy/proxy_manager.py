#!/usr/bin/env python3
"""V41.590 Proxy Manager - 代理池管理中心

This module provides intelligent proxy rotation and management for web scraping,
supporting both HTTP and SOCKS5 proxies with automatic failover.

Key Features:
    - Random proxy selection with round-robin fallback
    - Proxy health tracking and automatic failover
    - Support for environment variables and config files
    - Thread-safe proxy rotation

Author: V41.590 Stealth Team
Date: 2026-01-21
"""

from __future__ import annotations

import logging
import os
import random
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any

from pydantic import BaseModel, HttpUrl, field_validator

logger = logging.getLogger(__name__)


# ============================================================================
# Configuration Models
# ============================================================================


@dataclass
class ProxyConfig:
    """代理配置"""

    # 代理列表 (HTTP/SOCKS5 格式: http://host:port or socks5://host:port)
    proxies: list[str] = field(default_factory=list)

    # 当前使用的代理索引
    current_index: int = 0

    # 轮换策略: "random" (随机) 或 "round_robin" (轮询)
    rotation_strategy: str = "random"

    # 失败阈值: 连续失败多少次后标记为不可用
    failure_threshold: int = 3

    # 失败计数器 {proxy_url: failure_count}
    failure_counts: dict[str, int] = field(default_factory=dict)

    # 黑名单 {proxy_url: banned_until}
    blacklist: dict[str, datetime] = field(default_factory=dict)

    # 代理冷却时间 (秒)
    cooldown_seconds: int = 300

    def get_available_proxies(self) -> list[str]:
        """获取当前可用的代理列表（排除黑名单）"""
        now = datetime.now()
        available = []

        for proxy in self.proxies:
            # 检查是否在黑名单中
            if proxy in self.blacklist:
                banned_until = self.blacklist[proxy]
                if now < banned_until:
                    continue  # 仍在冷却期
                else:
                    # 冷却期已过，移出黑名单
                    del self.blacklist[proxy]
                    self.failure_counts[proxy] = 0

            # 检查失败次数
            failures = self.failure_counts.get(proxy, 0)
            if failures >= self.failure_threshold:
                continue  # 失败次数过多

            available.append(proxy)

        return available

    def mark_failure(self, proxy: str) -> None:
        """标记代理失败"""
        self.failure_counts[proxy] = self.failure_counts.get(proxy, 0) + 1

        # 如果失败次数达到阈值，加入黑名单
        if self.failure_counts[proxy] >= self.failure_threshold:
            from datetime import timedelta

            banned_until = datetime.now() + timedelta(seconds=self.cooldown_seconds)
            self.blacklist[proxy] = banned_until
            logger.warning(
                f"[ProxyManager] Proxy {proxy} banned after {self.failure_counts[proxy]} failures. "
                f"Cooldown until {banned_until}"
            )

    def mark_success(self, proxy: str) -> None:
        """标记代理成功（重置失败计数）"""
        if proxy in self.failure_counts:
            self.failure_counts[proxy] = 0
            logger.debug(f"[ProxyManager] Proxy {proxy} recovered")


# ============================================================================
# Proxy Manager
# ============================================================================


class ProxyManager:
    """V41.590: 代理池管理器

    提供智能代理轮换和健康管理，支持 HTTP/SOCKS5 代理。

    特性:
    - 随机/轮询两种代理选择策略
    - 自动故障转移和黑名单机制
    - 线程安全的代理轮换
    - 从环境变量或配置文件加载代理列表

    Example:
        >>> manager = ProxyManager()
        >>> proxy = manager.get_random_proxy()
        >>> # 使用代理...
        >>> manager.mark_success(proxy)  # 或 manager.mark_failure(proxy)
    """

    def __init__(
        self,
        config: ProxyConfig | None = None,
        proxies_file: str | None = None,
        env_var: str = "PROXY_LIST"
    ):
        """初始化代理管理器

        Args:
            config: 代理配置对象
            proxies_file: 代理列表文件路径（每行一个代理）
            env_var: 环境变量名称（逗号分隔的代理列表）
        """
        self.config = config or ProxyConfig()

        # 从文件或环境变量加载代理
        if proxies_file:
            self._load_from_file(proxies_file)
        elif env_var:
            self._load_from_env(env_var)

        # 如果没有配置代理，使用 WSL2 自动探测
        if not self.config.proxies:
            self._enable_wsl2_autodetect()

        logger.info(
            f"[ProxyManager] 初始化完成: {len(self.config.proxies)} 个代理, "
            f"策略: {self.config.rotation_strategy}"
        )

    def _load_from_file(self, filepath: str) -> None:
        """从文件加载代理列表"""
        file_path = Path(filepath)
        if not file_path.exists():
            logger.warning(f"[ProxyManager] 代理文件不存在: {filepath}")
            return

        proxies = []
        with open(file_path) as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#"):
                    proxies.append(line)

        self.config.proxies.extend(proxies)
        logger.info(f"[ProxyManager] 从文件加载 {len(proxies)} 个代理: {filepath}")

    def _load_from_env(self, env_var: str) -> None:
        """从环境变量加载代理列表"""
        proxy_list = os.getenv(env_var, "")
        if not proxy_list:
            return

        proxies = [p.strip() for p in proxy_list.split(",") if p.strip()]
        self.config.proxies.extend(proxies)
        logger.info(f"[ProxyManager] 从环境变量加载 {len(proxies)} 个代理: {env_var}")

    def _enable_wsl2_autodetect(self) -> None:
        """启用 WSL2 自动代理探测"""
        # 从环境变量读取代理配置（V164.Sanitization 解耦）
        proxy_host = os.getenv("WSL2_PROXY_HOST", "172.25.16.1")
        proxy_ports_str = os.getenv("PROXY_PORTS", "7892,7893,7894,7895,7896,7898,7899")

        # 解析端口列表
        try:
            proxy_ports = [int(p.strip()) for p in proxy_ports_str.split(",")]
        except ValueError:
            logger.warning(f"[ProxyManager] PROXY_PORTS 格式错误: {proxy_ports_str}")
            proxy_ports = [7892, 7893, 7894]  # 默认端口

        # 构建代理列表（避免已弃用的端口）
        wsl2_proxies = [f"http://{proxy_host}:{port}" for port in proxy_ports]
        self.config.proxies.extend(wsl2_proxies)
        logger.info(f"[ProxyManager] 启用 WSL2 自动探测代理: {len(wsl2_proxies)} 个代理")

    def get_random_proxy(self) -> str | None:
        """获取随机可用代理

        Returns:
            代理 URL，如果没有可用代理则返回 None
        """
        available = self.config.get_available_proxies()
        if not available:
            logger.warning("[ProxyManager] 没有可用代理！所有代理都已失效")
            return None

        # 随机选择
        proxy = random.choice(available)
        logger.debug(f"[ProxyManager] 随机选择代理: {proxy}")
        return proxy

    def get_next_proxy(self) -> str | None:
        """获取下一个代理（轮询策略）

        Returns:
            代理 URL，如果没有可用代理则返回 None
        """
        available = self.config.get_available_proxies()
        if not available:
            logger.warning("[ProxyManager] 没有可用代理！所有代理都已失效")
            return None

        # 轮询选择
        proxy = available[self.config.current_index % len(available)]
        self.config.current_index += 1
        logger.debug(f"[ProxyManager] 轮询选择代理: {proxy}")
        return proxy

    def get_proxy(self) -> str | None:
        """根据配置策略获取代理

        Returns:
            代理 URL，如果没有可用代理则返回 None
        """
        if self.config.rotation_strategy == "random":
            return self.get_random_proxy()
        else:
            return self.get_next_proxy()

    def mark_success(self, proxy: str) -> None:
        """标记代理使用成功（重置失败计数）"""
        if proxy:
            self.config.mark_success(proxy)

    def mark_failure(self, proxy: str) -> None:
        """标记代理使用失败

        Args:
            proxy: 失败的代理 URL
        """
        if proxy:
            self.config.mark_failure(proxy)

    def get_stats(self) -> dict[str, Any]:
        """获取代理池统计信息

        Returns:
            包含代理池状态的字典
        """
        available = self.config.get_available_proxies()
        banned_count = len(self.config.blacklist)
        total_failures = sum(self.config.failure_counts.values())

        return {
            "total_proxies": len(self.config.proxies),
            "available_proxies": len(available),
            "banned_proxies": banned_count,
            "total_failures": total_failures,
            "rotation_strategy": self.config.rotation_strategy,
            "active_proxies": available,
        }


# ============================================================================
# Singleton Instance
# ============================================================================

_proxy_manager_instance: ProxyManager | None = None


def get_proxy_manager(
    config: ProxyConfig | None = None,
    proxies_file: str | None = None,
    env_var: str = "PROXY_LIST"
) -> ProxyManager:
    """获取代理管理器单例

    Args:
        config: 代理配置对象
        proxies_file: 代理列表文件路径
        env_var: 环境变量名称

    Returns:
        ProxyManager 单例实例
    """
    global _proxy_manager_instance
    if _proxy_manager_instance is None:
        _proxy_manager_instance = ProxyManager(
            config=config, proxies_file=proxies_file, env_var=env_var
        )
    return _proxy_manager_instance
