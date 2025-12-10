"""
代理池 (ProxyPool) 实现
Proxy Pool Implementation

该模块实现了一个高可用、可扩展的代理池系统，支持：
1. 多种代理来源（文件/API/环境变量）
2. 代理健康评分和黑名单机制
3. 多策略轮询（随机/轮询）
4. 自动剔除失效代理
5. 异步接口设计

作者: Lead Collector Engineer
创建时间: 2025-12-06
版本: 1.0.0
"""

import asyncio
import random
import time
from abc import abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, , , Optional, Protocol, runtime_checkable

import aiohttp


class ProxyProtocol(Enum):
    """代理协议类型"""

    HTTP = "http"
    HTTPS = "https"
    SOCKS4 = "socks4"
    SOCKS5 = "socks5"


class ProxyStatus(Enum):
    """代理状态"""

    ACTIVE = "active"  # 活跃可用
    BANNED = "banned"  # 已被禁用
    TESTING = "testing"  # 测试中


@dataclass
class Proxy:
    """
    代理信息数据类

    Attributes:
        url: 代理完整URL (如: http://127.0.0.1:8080)
        protocol: 代理协议类型
        host: 代理主机地址
        port: 代理端口
        username: 用户名（可选）
        password: 密码（可选）
        score: 信誉分数 (0-100)
        fail_count: 连续失败次数
        success_count: 连续成功次数
        last_used: 最后使用时间
        last_check: 最后检查时间
        status: 代理状态
        response_time: 响应时间（毫秒）
    """

    url: str
    protocol: ProxyProtocol
    host: str
    port: int
    username: Optional[str] = None
    password: Optional[str] = None
    score: float = 100.0
    fail_count: int = 0
    success_count: int = 0
    last_used: Optional[float] = field(default_factory=time.monotonic)
    last_check: Optional[float] = field(default_factory=time.monotonic)
    status: ProxyStatus = ProxyStatus.ACTIVE
    response_time: Optional[float] = None

    def __post_init__(self) -> None:
        """初始化后处理"""
        if isinstance(self.protocol, str):
            self.protocol = ProxyProtocol(self.protocol.lower())
        if isinstance(self.status, str):
            self.status = ProxyStatus(self.status.lower())

    @classmethod
    def from_url(cls, url: str, **kwargs) -> "Proxy":
        """
        从URL创建代理对象

        Args:
            url: 代理URL (如: http://127.0.0.1:8080)
            **kwargs: 其他属性

        Returns:
            Proxy: 代理对象
        """
        if not url.startswith(("http://", "https://", "socks4://", "socks5://")):
            url = f"http://{url}"

        # 解析URL
        if "://" in url:
            protocol_str, rest = url.split("://", 1)
            protocol = ProxyProtocol(protocol_str.lower())

            # 处理认证信息
            credentials = None
            if "@" in rest:
                credentials, rest = rest.split("@", 1)
                if ":" in credentials:
                    username, password = credentials.split(":", 1)
                else:
                    username, password = credentials, None
            else:
                username, password = None, None

            # 处理主机和端口
            if ":" in rest:
                host, port_str = rest.rsplit(":", 1)
                try:
                    port = int(port_str)
                except ValueError:
                    # 如果端口不是数字，可能是IPv6地址
                    if "[" in rest and "]" in rest:
                        host = rest.split("]")[0][1:]
                        port_part = rest.split("]:")
                        port = int(port_part[1]) if len(port_part) > 1 else 80
                    else:
                        raise ValueError(f"Invalid proxy URL: {url}")
            else:
                host = rest
                port = 80
        else:
            raise ValueError(f"Invalid proxy URL: {url}")

        return cls(
            url=url,
            protocol=protocol,
            host=host,
            port=port,
            username=username,
            password=password,
            **kwargs,
        )

    @property
    def is_active(self) -> bool:
        """检查代理是否活跃"""
        return self.status == ProxyStatus.ACTIVE

    @property
    def is_banned(self) -> bool:
        """检查代理是否被禁用"""
        return self.status == ProxyStatus.BANNED

    @property
    def is_healthy(self) -> bool:
        """检查代理是否健康（分数>50且未被禁用）"""
        return self.score > 50.0 and not self.is_banned

    def record_success(self, response_time: Optional[float] = None) -> None:
        """
        记录成功使用

        Args:
            response_time: 响应时间（毫秒）
        """
        self.success_count += 1
        self.fail_count = 0  # 重置失败计数
        self.last_used = time.monotonic()

        if response_time is not None:
            self.response_time = response_time

        # 增加分数，最高100
        if self.score < 100.0:
            self.score = min(100.0, self.score + 5.0)

    def record_failure(self) -> None:
        """记录失败使用"""
        self.fail_count += 1
        self.last_used = time.monotonic()

        # 减少分数，最低0
        if self.score > 0.0:
            self.score = max(0.0, self.score - 10.0)

    def ban(self) -> None:
        """禁用代理"""
        self.status = ProxyStatus.BANNED
        self.score = 0.0

    def reactivate(self) -> None:
        """重新激活代理"""
        self.status = ProxyStatus.ACTIVE
        self.fail_count = 0
        self.score = max(50.0, self.score)  # 恢复到最低50分

    def to_dict(self) -> dict[str, Any]:
        """转换为字典格式"""
        return {
            "url": self.url,
            "protocol": self.protocol.value,
            "host": self.host,
            "port": self.port,
            "username": self.username,
            "password": "***" if self.password else None,
            "score": self.score,
            "fail_count": self.fail_count,
            "success_count": self.success_count,
            "last_used": self.last_used,
            "last_check": self.last_check,
            "status": self.status.value,
            "response_time": self.response_time,
            "is_active": self.is_active,
            "is_banned": self.is_banned,
            "is_healthy": self.is_healthy,
        }

    def __str__(self) -> str:
        return f"Proxy({self.url}, score={self.score:.1f}, status={self.status.value})"

    def __repr__(self) -> str:
        return self.__str__()


class RotationStrategy(Enum):
    """轮询策略"""

    RANDOM = "random"
    ROUND_ROBIN = "round_robin"
    WEIGHTED_RANDOM = "weighted_random"
    HEALTH_FIRST = "health_first"


@runtime_checkable
class ProxyProvider(Protocol):
    """
    代理提供者协议

    定义了从不同来源获取代理的标准接口
    """

    @abstractmethod
    async def load_proxies(self) -> list[Proxy]:
        """
        加载代理列表

        Returns:
            list[Proxy]: 代理列表
        """
        ...

    @abstractmethod
    async def refresh_proxies(self) -> list[Proxy]:
        """
        刷新代理列表

        Returns:
            list[Proxy]: 更新后的代理列表
        """
        ...


class StaticProxyProvider:
    """
    静态代理提供者

    用于测试和演示，提供固定的代理列表
    """

    def __init__(self, proxies: list[str]):
        """
        初始化静态代理提供者

        Args:
            proxies: 代理URL列表
        """
        self.proxies = [Proxy.from_url(url) for url in proxies]

    async def load_proxies(self) -> list[Proxy]:
        """加载静态代理列表"""
        return self.proxies.copy()

    async def refresh_proxies(self) -> list[Proxy]:
        """刷新代理列表（静态提供者返回相同列表）"""
        return self.proxies.copy()


class FileProxyProvider:
    """
    文件代理提供者

    从文件中读取代理列表，支持多种格式
    """

    def __init__(self, file_path: str, encoding: str = "utf-8"):
        """
        初始化文件代理提供者

        Args:
            file_path: 代理文件路径
            encoding: 文件编码
        """
        self.file_path = Path(file_path)
        self.encoding = encoding
        self._cached_proxies: Optional[list[Proxy]] = None
        self._last_modified: Optional[float] = None

    async def load_proxies(self) -> list[Proxy]:
        """加载代理文件"""
        if not self.file_path.exists():
            raise FileNotFoundError(f"Proxy file not found: {self.file_path}")

        # 检查文件是否已修改
        current_mtime = self.file_path.stat().st_mtime

        if (
            self._cached_proxies is None
            or self._last_modified is None
            or current_mtime > self._last_modified
        ):

            proxies = []
            with open(self.file_path, encoding=self.encoding) as f:
                for line_num, line in enumerate(f, 1):
                    line = line.strip()
                    if not line or line.startswith("#"):
                        continue

                    try:
                        proxy = Proxy.from_url(line)
                        proxies.append(proxy)
                    except ValueError as e:
                        print(
                            f"Warning: Invalid proxy format at line {line_num}: {line} - {e}"
                        )
                        continue

            self._cached_proxies = proxies
            self._last_modified = current_mtime

        return self._cached_proxies.copy() if self._cached_proxies else []

    async def refresh_proxies(self) -> list[Proxy]:
        """刷新代理列表（强制重新加载文件）"""
        self._cached_proxies = None
        self._last_modified = None
        return await self.load_proxies()


class ProxyPool:
    """
    代理池管理器

    负责代理的获取、轮询、健康评分和黑名单管理
    """

    def __init__(
        self,
        provider: ProxyProvider,
        strategy: RotationStrategy = RotationStrategy.WEIGHTED_RANDOM,
        max_fail_count: int = 5,
        min_score_threshold: float = 30.0,
        health_check_url: str = "http://httpbin.org/ip",
        health_check_timeout: float = 10.0,
        auto_health_check: bool = True,
        health_check_interval: float = 300.0,  # 5分钟
    ):
        """
        初始化代理池

        Args:
            provider: 代理提供者
            strategy: 轮询策略
            max_fail_count: 最大连续失败次数
            min_score_threshold: 最小分数阈值
            health_check_url: 健康检查URL
            health_check_timeout: 健康检查超时时间
            auto_health_check: 是否自动健康检查
            health_check_interval: 健康检查间隔
        """
        self.provider = provider
        self.strategy = strategy
        self.max_fail_count = max_fail_count
        self.min_score_threshold = min_score_threshold
        self.health_check_url = health_check_url
        self.health_check_timeout = health_check_timeout
        self.auto_health_check = auto_health_check
        self.health_check_interval = health_check_interval

        # 代理列表和状态
        self.proxies: list[Proxy] = []
        self.current_index = 0  # 用于轮询策略
        self.lock = asyncio.Lock()

        # 健康检查任务
        self._health_check_task: Optional[asyncio.Task] = None
        self._last_health_check = 0.0

    async def initialize(self) -> None:
        """初始化代理池"""
        async with self.lock:
            self.proxies = await self.provider.load_proxies()
            print(f"📋 Loaded {len(self.proxies)} proxies from provider")

            # 启动健康检查任务
            if self.auto_health_check:
                self._health_check_task = asyncio.create_task(self._health_check_loop())

    async def close(self) -> None:
        """关闭代理池"""
        if self._health_check_task:
            self._health_check_task.cancel()
            try:
                await self._health_check_task
            except asyncio.CancelledError:
                pass

    async def get_proxy(self) -> Optional[Proxy]:
        """
        获取一个可用代理

        Returns:
            Optional[Proxy]: 可用代理，如果没有则返回None
        """
        async with self.lock:
            if not self.proxies:
                return None

            # 过滤活跃且健康的代理
            available_proxies = [
                proxy for proxy in self.proxies if proxy.is_active and proxy.is_healthy
            ]

            if not available_proxies:
                # 如果没有健康的代理，尝试激活一些被禁用的代理
                await self._reactivate_banned_proxies()
                available_proxies = [
                    proxy
                    for proxy in self.proxies
                    if proxy.is_active and proxy.is_healthy
                ]

                if not available_proxies:
                    return None

            # 根据策略选择代理
            proxy = await self._select_proxy(available_proxies)
            return proxy

    async def _select_proxy(self, available_proxies: list[Proxy]) -> Proxy:
        """根据策略选择代理"""
        if self.strategy == RotationStrategy.RANDOM:
            return random.choice(available_proxies)

        elif self.strategy == RotationStrategy.ROUND_ROBIN:
            proxy = available_proxies[self.current_index % len(available_proxies)]
            self.current_index += 1
            return proxy

        elif self.strategy == RotationStrategy.WEIGHTED_RANDOM:
            # 根据分数进行加权随机选择
            total_score = sum(proxy.score for proxy in available_proxies)
            if total_score == 0:
                return random.choice(available_proxies)

            rand = random.uniform(0, total_score)
            current_score = 0.0

            for proxy in available_proxies:
                current_score += proxy.score
                if rand <= current_score:
                    return proxy

            return available_proxies[-1]  # fallback

        elif self.strategy == RotationStrategy.HEALTH_FIRST:
            # 优先选择分数最高的代理
            return max(available_proxies, key=lambda p: p.score)

        else:
            return random.choice(available_proxies)

    async def record_proxy_result(
        self, proxy: Proxy, success: bool, response_time: Optional[float] = None
    ) -> None:
        """
        记录代理使用结果

        Args:
            proxy: 使用的代理
            success: 是否成功
            response_time: 响应时间（毫秒）
        """
        async with self.lock:
            if success:
                proxy.record_success(response_time)
            else:
                proxy.record_failure()
                # 检查是否需要禁用代理
                if (
                    proxy.fail_count >= self.max_fail_count
                    or proxy.score < self.min_score_threshold
                ):
                    proxy.ban()
                    print(
                        f"🚫 Proxy banned: {proxy.url} (fail_count={proxy.fail_count}, score={proxy.score:.1f})"
                    )

    async def _reactivate_banned_proxies(self) -> None:
        """重新激活部分被禁用的代理"""
        banned_proxies = [proxy for proxy in self.proxies if proxy.is_banned]

        # 随机选择一些代理进行重新激活
        if banned_proxies:
            reactivate_count = min(3, len(banned_proxies))  # 最多重新激活3个
            selected_proxies = random.sample(banned_proxies, reactivate_count)

            for proxy in selected_proxies:
                proxy.reactivate()
                print(f"🔄 Proxy reactivated: {proxy.url}")

    async def _health_check_loop(self) -> None:
        """健康检查循环"""
        while True:
            try:
                await asyncio.sleep(self.health_check_interval)
                await self._perform_health_check()
            except asyncio.CancelledError:
                break
            except Exception as e:
                print(f"❌ Health check error: {e}")

    async def _perform_health_check(self) -> None:
        """执行健康检查"""
        current_time = time.monotonic()

        # 避免频繁检查
        if current_time - self._last_health_check < self.health_check_interval:
            return

        async with self.lock:
            self._last_health_check = current_time

            if not self.proxies:
                return

            print(f"🔍 Starting health check for {len(self.proxies)} proxies...")

            # 并发检查所有代理
            tasks = [
                self._check_single_proxy(proxy)
                for proxy in self.proxies
                if proxy.is_active
            ]

            if tasks:
                results = await asyncio.gather(*tasks, return_exceptions=True)

                # 统计结果
                healthy_count = 0
                for i, result in enumerate(results):
                    proxy = self.proxies[i]
                    if isinstance(result, Exception):
                        print(f"❌ Health check failed for {proxy.url}: {result}")
                        self.record_proxy_result(proxy, False)
                    elif result:
                        healthy_count += 1
                        print(f"✅ Health check passed for {proxy.url}")

                print(
                    f"📊 Health check completed: {healthy_count}/{len(tasks)} proxies healthy"
                )

    async def _check_single_proxy(self, proxy: Proxy) -> bool:
        """检查单个代理的健康状况"""
        try:
            proxy_url = proxy.url
            if proxy.username and proxy.password:
                # 添加认证信息
                from urllib.parse import quote

                auth_string = f"{quote(proxy.username)}:{quote(proxy.password)}"
                proxy_url = proxy_url.replace("://", f"://{auth_string}@")

            timeout = aiohttp.ClientTimeout(total=self.health_check_timeout)

            async with aiohttp.ClientSession(timeout=timeout) as session:
                async with session.get(
                    self.health_check_url, proxy=proxy_url, ssl=False  # 忽略SSL证书验证
                ) as response:
                    if response.status == 200:
                        start_time = time.monotonic()
                        await response.text()
                        end_time = time.monotonic()

                        response_time = (end_time - start_time) * 1000  # 转换为毫秒
                        proxy.record_success(response_time)
                        return True
                    else:
                        proxy.record_failure()
                        return False

        except Exception:
            proxy.record_failure()
            return False

    async def refresh_proxies(self) -> None:
        """刷新代理列表"""
        async with self.lock:
            try:
                new_proxies = await self.provider.refresh_proxies()
                old_urls = {proxy.url for proxy in self.proxies}
                new_urls = {proxy.url for proxy in new_proxies}

                # 合并代理列表，保留已有的分数和统计信息
                merged_proxies = []

                # 保留已有的代理
                for old_proxy in self.proxies:
                    if old_proxy.url in new_urls:
                        merged_proxies.append(old_proxy)

                # 添加新的代理
                for new_proxy in new_proxies:
                    if new_proxy.url not in old_urls:
                        merged_proxies.append(new_proxy)

                self.proxies = merged_proxies
                print(f"🔄 Proxies refreshed: {len(self.proxies)} total")

            except Exception as e:
                print(f"❌ Failed to refresh proxies: {e}")

    def get_stats(self) -> dict[str, Any]:
        """获取代理池统计信息"""
        if not self.proxies:
            return {
                "total": 0,
                "active": 0,
                "banned": 0,
                "healthy": 0,
                "avg_score": 0.0,
                "avg_response_time": None,
            }

        active_proxies = [p for p in self.proxies if p.is_active]
        healthy_proxies = [p for p in self.proxies if p.is_healthy]
        avg_score = sum(p.score for p in self.proxies) / len(self.proxies)

        response_times = [
            p.response_time for p in self.proxies if p.response_time is not None
        ]
        avg_response_time = (
            sum(response_times) / len(response_times) if response_times else None
        )

        return {
            "total": len(self.proxies),
            "active": len(active_proxies),
            "banned": len(self.proxies) - len(active_proxies),
            "healthy": len(healthy_proxies),
            "avg_score": round(avg_score, 2),
            "avg_response_time": (
                round(avg_response_time, 2) if avg_response_time else None
            ),
        }

    def get_proxies_info(self) -> list[dict[str, Any]]:
        """获取所有代理的详细信息"""
        return [proxy.to_dict() for proxy in self.proxies]


# 便利函数
def create_proxy_pool(
    proxies: list[str],
    strategy: RotationStrategy = RotationStrategy.WEIGHTED_RANDOM,
    **kwargs,
) -> ProxyPool:
    """
    创建代理池的便利函数

    Args:
        proxies: 代理URL列表
        strategy: 轮询策略
        **kwargs: 其他ProxyPool参数

    Returns:
        ProxyPool: 代理池实例
    """
    provider = StaticProxyProvider(proxies)
    return ProxyPool(provider, strategy, **kwargs)


def create_file_proxy_pool(
    file_path: str,
    strategy: RotationStrategy = RotationStrategy.WEIGHTED_RANDOM,
    **kwargs,
) -> ProxyPool:
    """
    创建基于文件的代理池

    Args:
        file_path: 代理文件路径
        strategy: 轮询策略
        **kwargs: 其他ProxyPool参数

    Returns:
        ProxyPool: 代理池实例
    """
    provider = FileProxyProvider(file_path)
    return ProxyPool(provider, strategy, **kwargs)


# 模块导出
__all__ = [
    "Proxy",
    "ProxyProtocol",
    "ProxyStatus",
    "RotationStrategy",
    "ProxyProvider",
    "StaticProxyProvider",
    "FileProxyProvider",
    "ProxyPool",
    "create_proxy_pool",
    "create_file_proxy_pool",
]
