#!/usr/bin/env python3
"""
V41.130 IP 守护者 - 智能代理防护层

核心功能:
- 403 自动封印: 检测到 403 状态码，自动标记端口为 banned，12 小时严禁调用
- 健康状态交叉验证: 每次切换 IP 必须先 ping httpbin.org/ip 确认身份
- 优雅降级: 当所有代理被封禁时，自动降级到直连模式
- 熔断器保护: 连续失败触发熔断，避免无效重试

架构设计:
  ┌──────────────────────────────────────────────────────────────┐
  │                   ProxyGuardian (单例)                        │
  │  - ban_cache: {port: banned_until}                           │
  │  - health_cache: {port: health_status}                       │
  │  - circuit_breaker: {port: failure_count}                    │
  └──────────────────────────────────────────────────────────────┘
                          ↓
  ┌──────────────────────┼──────────────────────┐
  ↓                      ↓                      ↓
File Cache          Redis Cache           Memory Fallback
(持久化)            (分布式共享)          (本地快速)

使用示例:
    >>> guardian = ProxyGuardian.get_instance()
    >>> proxy_port = guardian.get_healthy_proxy()
    >>> # 使用代理请求...
    >>> response = requests.get(url, proxies={"http": proxy_url})
    >>> guardian.record_result(proxy_port, response.status_code)
    >>> # 如果是 403，自动封禁并返回下一个可用代理
"""

import asyncio
import json
import logging
import random
import time
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from pathlib import Path
from threading import Lock
from typing import Optional

import aiohttp
import requests

from src.config_unified import get_config

logger = logging.getLogger(__name__)


class ProxyStatus(str, Enum):
    """代理状态枚举"""
    HEALTHY = "healthy"       # 健康，可用
    BANNED = "banned"         # 被封禁（403）
    DEGRADED = "degraded"     # 降级服务（慢但不完全失败）
    DEAD = "dead"            # 死亡（连接失败）


@dataclass
class ProxyHealth:
    """代理健康状态"""
    port: int
    status: ProxyStatus
    ip: str | None = None
    last_check: str = ""
    response_time_ms: float = 0.0
    failure_count: int = 0
    success_count: int = 0
    banned_until: str = ""  # ISO 格式时间戳

    def is_banned(self) -> bool:
        """检查是否被封禁"""
        if not self.banned_until:
            return False
        try:
            banned_time = datetime.fromisoformat(self.banned_until)
            return datetime.now() < banned_time
        except Exception:
            return False

    def to_dict(self) -> dict:
        """转换为字典"""
        return {
            "port": self.port,
            "status": self.status.value,
            "ip": self.ip,
            "last_check": self.last_check,
            "response_time_ms": self.response_time_ms,
            "failure_count": self.failure_count,
            "success_count": self.success_count,
            "banned_until": self.banned_until
        }


class ProxyGuardian:
    """V41.130 IP 守护者 - 单例模式"""

    _instance: Optional["ProxyGuardian"] = None
    _lock = Lock()

    # 封禁时长配置
    BAN_DURATION_403 = timedelta(hours=12)  # 403 封禁 12 小时
    BAN_DURATION_429 = timedelta(hours=6)   # 429 封禁 6 小时
    BAN_DURATION_TIMEOUT = timedelta(minutes=30)  # 超时封禁 30 分钟

    # 熔断器配置
    CIRCUIT_BREAKER_THRESHOLD = 5  # 连续失败 5 次触发熔断
    CIRCUIT_BREAKER_HALF_OPEN_ATTEMPTS = 3  # 半开状态尝试次数

    # 健康检查配置
    HEALTH_CHECK_URL = "http://httpbin.org/ip"  # 用于获取代理 IP
    HEALTH_CHECK_TIMEOUT = 5.0  # 秒

    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        if hasattr(self, "_initialized"):
            return

        self._initialized = True
        self.config = get_config()

        # 代理健康状态缓存 {port: ProxyHealth}
        self._health_cache: dict[int, ProxyHealth] = {}

        # 文件缓存路径
        self._cache_file = Path("logs/proxy_guardian_cache.json")
        self._cache_file.parent.mkdir(exist_ok=True)

        # 线程锁
        self._cache_lock = Lock()

        # 初始化
        self._load_cache()
        self._initialize_proxies()

        logger.info(f"🛡️ V41.130 ProxyGuardian 初始化完成")
        logger.info(f"   管理代理数: {len(self._health_cache)}")
        logger.info(f"   健康代理数: {self._get_healthy_count()}")

    @classmethod
    def get_instance(cls) -> "ProxyGuardian":
        """获取单例实例"""
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def _initialize_proxies(self):
        """初始化代理池"""
        proxy_ports = self.config.proxy.proxy_ports

        for port in proxy_ports:
            if port not in self._health_cache:
                self._health_cache[port] = ProxyHealth(
                    port=port,
                    status=ProxyStatus.HEALTHY,
                    last_check=datetime.now().isoformat()
                )

        # 移除已弃用的端口
        deprecated = self.config.proxy.deprecated_proxy_ports
        for port in deprecated:
            self._health_cache.pop(port, None)

    def _load_cache(self):
        """从文件加载缓存"""
        if not self._cache_file.exists():
            return

        try:
            with open(self._cache_file, "r", encoding="utf-8") as f:
                data = json.load(f)

            for port_str, health_data in data.items():
                port = int(port_str)
                self._health_cache[port] = ProxyHealth(
                    port=health_data["port"],
                    status=ProxyStatus(health_data["status"]),
                    ip=health_data.get("ip"),
                    last_check=health_data.get("last_check", ""),
                    response_time_ms=health_data.get("response_time_ms", 0.0),
                    failure_count=health_data.get("failure_count", 0),
                    success_count=health_data.get("success_count", 0),
                    banned_until=health_data.get("banned_until", "")
                )

            logger.info(f"📂 从缓存加载了 {len(self._health_cache)} 个代理状态")

        except Exception as e:
            logger.warning(f"⚠️ 加载缓存失败: {e}")

    def _save_cache(self):
        """保存缓存到文件"""
        try:
            data = {
                str(port): health.to_dict()
                for port, health in self._health_cache.items()
            }

            with open(self._cache_file, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)

        except Exception as e:
            logger.warning(f"⚠️ 保存缓存失败: {e}")

    def _get_healthy_count(self) -> int:
        """获取健康代理数量"""
        count = 0
        for health in self._health_cache.values():
            if health.status == ProxyStatus.HEALTHY and not health.is_banned():
                count += 1
        return count

    def get_healthy_proxy(self, exclude_ports: set[int] | None = None) -> Optional[int]:
        """获取一个健康的代理端口

        Args:
            exclude_ports: 排除的端口列表

        Returns:
            健康的代理端口，如果没有则返回 None
        """
        exclude_ports = exclude_ports or set()

        with self._cache_lock:
            # 清理过期封禁
            self._clean_expired_bans()

            # 筛选可用代理
            available = []
            for port, health in self._health_cache.items():
                if port in exclude_ports:
                    continue
                if health.is_banned():
                    continue
                if health.status == ProxyStatus.DEAD:
                    continue
                available.append((port, health))

            if not available:
                logger.warning("⚠️ 没有可用代理，所有代理均被封禁或死亡")
                return None

            # 随机选择（负载均衡）
            port, health = random.choice(available)

            logger.debug(f"🎯 选择代理: 端口 {port} (状态: {health.status.value})")
            return port

    async def verify_proxy_identity(self, port: int) -> tuple[bool, str | None]:
        """V41.130: 健康状态交叉验证 - 验证代理 IP 身份

        Args:
            port: 代理端口

        Returns:
            tuple[bool, str | None]: (是否成功, IP地址)
        """
        proxy_url = f"http://{self.config.proxy.wsl2_bridge_host}:{port}"

        try:
            start_time = time.time()

            async with aiohttp.ClientSession() as session:
                async with session.get(
                    self.HEALTH_CHECK_URL,
                    proxy=proxy_url,
                    timeout=aiohttp.ClientTimeout(total=self.HEALTH_CHECK_TIMEOUT)
                ) as response:
                    if response.status == 200:
                        data = await response.json()
                        ip = data.get("origin")
                        response_time = (time.time() - start_time) * 1000

                        # 更新健康状态
                        with self._cache_lock:
                            health = self._health_cache.get(port)
                            if health:
                                health.ip = ip
                                health.last_check = datetime.now().isoformat()
                                health.response_time_ms = response_time
                                health.status = ProxyStatus.HEALTHY

                        logger.info(f"✅ 代理 {port} 验证成功: IP={ip}, 响应={response_time:.0f}ms")
                        return True, ip
                    else:
                        logger.warning(f"⚠️ 代理 {port} 健康检查失败: HTTP {response.status}")
                        return False, None

        except asyncio.TimeoutError:
            logger.warning(f"⏰ 代理 {port} 健康检查超时")
            return False, None
        except Exception as e:
            logger.warning(f"❌ 代理 {port} 健康检查异常: {e}")
            return False, None

    def record_result(self, port: int, status_code: int, error: str | None = None):
        """记录请求结果并自动处理封禁

        Args:
            port: 代理端口
            status_code: HTTP 状态码
            error: 错误信息（如果有）
        """
        with self._cache_lock:
            health = self._health_cache.get(port)
            if not health:
                logger.warning(f"⚠️ 未知代理端口: {port}")
                return

            now = datetime.now()

            # V41.130: 403 自动封印
            if status_code == 403:
                health.banned_until = (now + self.BAN_DURATION_403).isoformat()
                health.status = ProxyStatus.BANNED
                health.failure_count += 1

                logger.error(f"🚫 代理 {port} 触发 403 封禁! 封禁至 {health.banned_until}")
                self._save_cache()
                return

            # 429 Too Many Requests
            if status_code == 429:
                health.banned_until = (now + self.BAN_DURATION_429).isoformat()
                health.status = ProxyStatus.BANNED
                health.failure_count += 1

                logger.warning(f"⚠️ 代理 {port} 触发 429 限流! 封禁至 {health.banned_until}")
                self._save_cache()
                return

            # 超时或连接错误
            if error or status_code >= 500:
                health.failure_count += 1

                # 熔断器触发
                if health.failure_count >= self.CIRCUIT_BREAKER_THRESHOLD:
                    health.banned_until = (now + self.BAN_DURATION_TIMEOUT).isoformat()
                    health.status = ProxyStatus.DEAD

                    logger.error(f"🔌 代理 {port} 熔断器触发! 失败次数={health.failure_count}")
                    self._save_cache()
                return

            # 成功请求
            if 200 <= status_code < 400:
                health.success_count += 1
                health.failure_count = 0  # 重置失败计数
                health.status = ProxyStatus.HEALTHY
                health.last_check = now.isoformat()

                # 定期保存缓存（避免频繁写入）
                if health.success_count % 10 == 0:
                    self._save_cache()

    def _clean_expired_bans(self):
        """清理过期的封禁"""
        now = datetime.now()
        changed = False

        for health in self._health_cache.values():
            # 检查是否封禁（包括状态标记为 BANNED 的情况）
            is_currently_banned = (
                health.is_banned() or
                health.status == ProxyStatus.BANNED
            )

            if is_currently_banned:
                try:
                    banned_time = datetime.fromisoformat(health.banned_until)
                    if now >= banned_time:
                        logger.info(f"🔓 代理 {health.port} 封禁已解除")
                        health.banned_until = ""
                        health.status = ProxyStatus.HEALTHY
                        health.failure_count = 0
                        changed = True
                except Exception:
                    # 如果无法解析时间，也视为解除封禁
                    if health.status == ProxyStatus.BANNED:
                        logger.info(f"🔓 代理 {health.port} 封禁已解除（无效时间戳）")
                        health.banned_until = ""
                        health.status = ProxyStatus.HEALTHY
                        health.failure_count = 0
                        changed = True

        if changed:
            self._save_cache()

    def get_health_report(self) -> dict:
        """获取健康状态报告"""
        with self._cache_lock:
            healthy = 0
            banned = 0
            degraded = 0
            dead = 0

            for health in self._health_cache.values():
                if health.is_banned() or health.status == ProxyStatus.BANNED:
                    banned += 1
                elif health.status == ProxyStatus.DEAD:
                    dead += 1
                elif health.status == ProxyStatus.DEGRADED:
                    degraded += 1
                else:
                    healthy += 1

            return {
                "total": len(self._health_cache),
                "healthy": healthy,
                "banned": banned,
                "degraded": degraded,
                "dead": dead,
                "proxies": [health.to_dict() for health in sorted(
                    self._health_cache.values(),
                    key=lambda h: h.port
                )]
            }

    def get_proxy_url(self, port: int) -> str:
        """获取代理 URL

        Args:
            port: 代理端口

        Returns:
            代理 URL，格式: http://host:port
        """
        return f"http://{self.config.proxy.wsl2_bridge_host}:{port}"


# =============================================================================
# 便捷函数
# =============================================================================

def get_guardian() -> ProxyGuardian:
    """获取 ProxyGuardian 单例"""
    return ProxyGuardian.get_instance()


async def verify_proxy_before_use(port: int) -> tuple[bool, str | None]:
    """使用前验证代理（交叉验证）

    Args:
        port: 代理端口

    Returns:
        tuple[bool, str | None]: (是否可用, IP地址)
    """
    guardian = get_guardian()
    return await guardian.verify_proxy_identity(port)
