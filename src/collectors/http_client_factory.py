"""
统一 HTTP 客户端工厂
Unified HTTP Client Factory

该模块实现了一个统一的HTTP客户端工厂，用于：
1. 自动装配采集器组件（RateLimiter、TokenManager、ProxyPool）
2. 简化采集器的实例化过程
3. 提供统一的配置和监控接口
4. 支持多种数据源的客户端创建

设计模式：
- Factory Pattern: 统一创建HTTP客户端
- Dependency Injection: 组件外部注入
- Builder Pattern: 灵活的配置构建
- Observer Pattern: 监控和事件通知

作者: Lead Collector Engineer
创建时间: 2025-12-06
版本: 1.0.0
"""

import asyncio
import json
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Protocol, runtime_checkable
from pathlib import Path

import httpx

from .auth import TokenManager, create_token_manager, create_fotmob_provider
from .fotmob.collector_v2 import FotMobCollectorV2
from .interface import BaseCollectorProtocol
from .proxy_pool import ProxyPool, create_proxy_pool, RotationStrategy
from .rate_limiter import RateLimiter, create_rate_limiter


@runtime_checkable
class CollectorConfig(Protocol):
    """采集器配置协议"""

    @property
    def source_name(self) -> str:
        """数据源名称"""
        ...

    @property
    def base_url(self) -> str:
        """基础URL"""
        ...

    @property
    def rate_limit_config(self) -> dict[str, Any]:
        """速率限制配置"""
        ...

    @property
    def token_manager_config(self) -> dict[str, Any]:
        """Token管理器配置"""
        ...

    @property
    def proxy_config(self) -> Optional[dict[str, Any]]:
        """代理配置"""
        ...


@dataclass
class FotMobConfig:
    """FotMob 数据源配置"""

    source_name: str = "fotmob"
    base_url: str = "https://www.fotmob.com"

    # 速率限制配置
    rate_limit_config: dict[str, Any] = field(
        default_factory=lambda: {
            "rate": 3.0,  # 3 QPS (保守速率)
            "burst": 8,  # 突发容量
            "max_wait_time": 30.0,  # 最大等待时间
        }
    )

    # Token管理器配置
    token_manager_config: dict[str, Any] = field(
        default_factory=lambda: {
            "default_ttl": 3600.0,  # 1小时TTL
            "cache_refresh_threshold": 300.0,  # 5分钟刷新阈值
            "max_retry_attempts": 3,
            "retry_delay": 1.0,
        }
    )

    # 代理配置
    proxy_config: Optional[dict[str, Any]] = field(
        default_factory=lambda: {
            "urls": [
                "http://127.0.0.1:8080",
                "http://127.0.0.1:8081",
                "socks5://127.0.0.1:1080",
            ],
            "strategy": "weighted_random",
            "auto_health_check": True,
            "max_fail_count": 5,
            "min_score_threshold": 30.0,
        }
    )

    # HTTP客户端配置
    timeout: float = 30.0
    max_retries: int = 3
    retry_delay: float = 1.0
    user_agent: str = (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    )


class RequestEvent:
    """请求事件数据类"""

    def __init__(
        self,
        source: str,
        method: str,
        url: str,
        status_code: Optional[int] = None,
        response_time_ms: Optional[float] = None,
        error: Optional[str] = None,
        proxy_used: Optional[str] = None,
        token_refreshed: bool = False,
    ):
        self.source = source
        self.method = method
        self.url = url
        self.status_code = status_code
        self.response_time_ms = response_time_ms
        self.error = error
        self.proxy_used = proxy_used
        self.token_refreshed = token_refreshed
        self.timestamp = time.monotonic()

    def to_dict(self) -> dict[str, Any]:
        """转换为字典格式"""
        return {
            "source": self.source,
            "method": self.method,
            "url": self.url,
            "status_code": self.status_code,
            "response_time_ms": self.response_time_ms,
            "error": self.error,
            "proxy_used": self.proxy_used,
            "token_refreshed": self.token_refreshed,
            "timestamp": self.timestamp,
        }


class RequestMonitor:
    """请求监控器"""

    def __init__(self):
        self.events: list[RequestEvent] = []
        self.stats: dict[str, Any] = {
            "total_requests": 0,
            "successful_requests": 0,
            "failed_requests": 0,
            "total_response_time_ms": 0.0,
            "token_refreshes": 0,
            "proxy_rotations": 0,
        }

    def record_event(self, event: RequestEvent) -> None:
        """记录请求事件"""
        self.events.append(event)

        # 更新统计信息
        self.stats["total_requests"] += 1

        if event.status_code and 200 <= event.status_code < 400:
            self.stats["successful_requests"] += 1
        else:
            self.stats["failed_requests"] += 1

        if event.response_time_ms:
            self.stats["total_response_time_ms"] += event.response_time_ms

        if event.token_refreshed:
            self.stats["token_refreshes"] += 1

        if event.proxy_used:
            self.stats["proxy_rotations"] += 1

    def get_stats(self) -> dict[str, Any]:
        """获取统计信息"""
        total_requests = self.stats["total_requests"]
        avg_response_time = (
            self.stats["total_response_time_ms"] / total_requests
            if total_requests > 0
            else 0.0
        )

        return {
            **self.stats,
            "avg_response_time_ms": round(avg_response_time, 2),
            "success_rate": (
                self.stats["successful_requests"] / total_requests * 100
                if total_requests > 0
                else 0.0
            ),
            "error_rate": (
                self.stats["failed_requests"] / total_requests * 100
                if total_requests > 0
                else 0.0
            ),
        }

    def get_events(
        self, source: Optional[str] = None, limit: Optional[int] = None
    ) -> list[RequestEvent]:
        """获取事件列表"""
        events = self.events
        if source:
            events = [e for e in events if e.source == source]
        if limit:
            events = events[-limit:]
        return events

    def clear(self) -> None:
        """清除所有事件和统计"""
        self.events.clear()
        self.stats = {
            "total_requests": 0,
            "successful_requests": 0,
            "failed_requests": 0,
            "total_response_time_ms": 0.0,
            "token_refreshes": 0,
            "proxy_rotations": 0,
        }


class HttpClientFactory:
    """
    统一HTTP客户端工厂

    负责创建和配置不同数据源的HTTP客户端，提供：
    1. 组件自动装配（RateLimiter、TokenManager、ProxyPool）
    2. 统一的配置管理
    3. 监控和事件记录
    4. 可测试的依赖注入支持
    """

    def __init__(self):
        self._components: dict[str, Any] = {}
        self._monitor = RequestMonitor()

        # 预定义的数据源配置
        self._configs: dict[str, CollectorConfig] = {
            "fotmob": FotMobConfig(),
        }

    def register_config(self, source: str, config: CollectorConfig) -> None:
        """注册数据源配置"""
        self._configs[source] = config

    def register_component(self, name: str, component: Any) -> None:
        """注册组件（用于依赖注入）"""
        self._components[name] = component

    def get_monitor(self) -> RequestMonitor:
        """获取请求监控器"""
        return self._monitor

    async def create_rate_limiter(
        self, source: str, config: CollectorConfig
    ) -> RateLimiter:
        """创建速率限制器"""
        if f"{source}_rate_limiter" in self._components:
            return self._components[f"{source}_rate_limiter"]

        return create_rate_limiter({f"{source}_api": config.rate_limit_config})

    async def create_proxy_pool(
        self, source: str, config: CollectorConfig
    ) -> ProxyPool:
        """创建代理池"""
        if f"{source}_proxy_pool" in self._components:
            return self._components[f"{source}_proxy_pool"]

        proxy_config = config.proxy_config
        if not proxy_config:
            # 返回空的代理池
            return ProxyPool([])

        return create_proxy_pool(
            proxy_config["urls"],
            strategy=RotationStrategy(proxy_config["strategy"]),
            auto_health_check=proxy_config["auto_health_check"],
            max_fail_count=proxy_config["max_fail_count"],
            min_score_threshold=proxy_config["min_score_threshold"],
        )

    async def create_token_manager(
        self, source: str, config: CollectorConfig
    ) -> TokenManager:
        """创建Token管理器"""
        if f"{source}_token_manager" in self._components:
            return self._components[f"{source}_token_manager"]

        token_manager = create_token_manager(**config.token_manager_config)

        # 为特定数据源注册Token Provider
        if source == "fotmob":
            from .auth import create_fotmob_provider

            fotmob_provider = create_fotmob_provider()
            await token_manager.register_provider(fotmob_provider)

        return token_manager

    async def create_collector(self, source: str) -> BaseCollectorProtocol:
        """
        创建采集器实例

        Args:
            source: 数据源名称 (如: "fotmob")

        Returns:
            BaseCollectorProtocol: 配置好的采集器实例

        Raises:
            ValueError: 不支持的数据源
        """
        if source not in self._configs:
            raise ValueError(f"Unsupported data source: {source}")

        config = self._configs[source]

        print(f"🏭 创建 {source} 采集器...")

        # 创建组件
        rate_limiter = await self.create_rate_limiter(source, config)
        proxy_pool = await self.create_proxy_pool(source, config)
        token_manager = await self.create_token_manager(source, config)

        print(f"   ✅ RateLimiter: {config.rate_limit_config['rate']} QPS")
        print(f"   ✅ ProxyPool: {len(proxy_pool.proxies) if proxy_pool else 0} 个代理")
        print(f"   ✅ TokenManager: {len(token_manager.token_cache)} 个提供者")

        # 创建采集器
        if source == "fotmob":
            collector = FotMobCollectorV2(
                rate_limiter=rate_limiter,
                proxy_pool=proxy_pool,
                token_manager=token_manager,
                base_url=config.base_url,
                timeout=config.timeout,
                max_retries=config.max_retries,
                retry_delay=config.retry_delay,
            )
        else:
            raise ValueError(f"No collector implementation for source: {source}")

        # 包装采集器以添加监控
        monitored_collector = MonitoredCollector(collector, source, self._monitor)

        print(f"   ✅ {source} 采集器创建完成")
        return monitored_collector

    async def create_client(self, source: str) -> httpx.AsyncClient:
        """
        创建HTTP客户端

        注意：这个方法主要提供HTTP客户端的基础配置，
        对于完整的采集功能，建议使用 create_collector() 方法。

        Args:
            source: 数据源名称

        Returns:
            httpx.AsyncClient: 配置好的HTTP客户端
        """
        if source not in self._configs:
            raise ValueError(f"Unsupported data source: {source}")

        config = self._configs[source]

        # 创建HTTP客户端配置
        client_config = {
            "timeout": httpx.Timeout(config.timeout),
            "headers": {
                "User-Agent": config.user_agent,
                "Accept": "application/json, text/plain, */*",
                "Accept-Language": "en-US,en;q=0.9",
                "Accept-Encoding": "gzip, deflate, br",
                "Connection": "keep-alive",
                "Upgrade-Insecure-Requests": "1",
            },
            "follow_redirects": True,
        }

        # 注入Token（如果配置了TokenManager）
        if f"{source}_token_manager" in self._components:
            token_manager = self._components[f"{source}_token_manager"]
            try:
                token = await token_manager.get_token(source)
                if token.token_type.value == "custom_header":
                    client_config["headers"].update(token.headers)
                elif token.token_type.value == "bearer":
                    client_config["headers"]["Authorization"] = f"Bearer {token.value}"
                elif token.token_type.value == "api_key":
                    client_config["headers"]["X-API-Key"] = token.value
            except Exception as e:
                print(f"⚠️ Failed to inject token for {source}: {e}")

        # 配置代理（如果需要）
        if f"{source}_proxy_pool" in self._components:
            proxy_pool = self._components[f"{source}_proxy_pool"]
            if proxy_pool.proxies:
                proxy = proxy_pool.proxies[0]  # 使用第一个代理
                if proxy.protocol == "socks5":
                    client_config["proxies"] = {
                        "http://": f"socks5://{proxy.host}:{proxy.port}",
                        "https://": f"socks5://{proxy.host}:{proxy.port}",
                    }
                else:
                    proxy_url = proxy.url
                    client_config["proxies"] = {
                        "http://": proxy_url,
                        "https://": proxy_url,
                    }

                # 添加代理认证
                if proxy.username and proxy.password:
                    client_config["auth"] = (proxy.username, proxy.password)

        return httpx.AsyncClient(**client_config)

    def get_available_sources(self) -> list[str]:
        """获取可用的数据源列表"""
        return list(self._configs.keys())

    def get_config(self, source: str) -> Optional[CollectorConfig]:
        """获取数据源配置"""
        return self._configs.get(source)


class MonitoredCollector:
    """带监控功能的采集器包装器"""

    def __init__(
        self, collector: BaseCollectorProtocol, source: str, monitor: RequestMonitor
    ):
        self.collector = collector
        self.source = source
        self.monitor = monitor

    async def collect_fixtures(
        self, league_id: int, season_id: Optional[str] = None
    ) -> list[dict[str, Any]]:
        """采集赛程数据（带监控）"""
        start_time = time.monotonic()
        try:
            result = await self.collector.collect_fixtures(league_id, season_id)

            # 记录成功事件
            event = RequestEvent(
                source=self.source,
                method="collect_fixtures",
                url=f"{self.source}://api/matches?leagueId={league_id}",
                response_time_ms=(time.monotonic() - start_time) * 1000,
            )
            self.monitor.record_event(event)

            return result

        except Exception as e:
            # 记录失败事件
            event = RequestEvent(
                source=self.source,
                method="collect_fixtures",
                url=f"{self.source}://api/matches?leagueId={league_id}",
                error=str(e),
                response_time_ms=(time.monotonic() - start_time) * 1000,
            )
            self.monitor.record_event(event)
            raise

    async def collect_match_details(self, match_id: str) -> dict[str, Any]:
        """采集比赛详情（带监控）"""
        start_time = time.monotonic()
        try:
            result = await self.collector.collect_match_details(match_id)

            # 记录成功事件
            event = RequestEvent(
                source=self.source,
                method="collect_match_details",
                url=f"{self.source}://api/matchDetails?matchId={match_id}",
                response_time_ms=(time.monotonic() - start_time) * 1000,
            )
            self.monitor.record_event(event)

            return result

        except Exception as e:
            # 记录失败事件
            event = RequestEvent(
                source=self.source,
                method="collect_match_details",
                url=f"{self.source}://api/matchDetails?matchId={match_id}",
                error=str(e),
                response_time_ms=(time.monotonic() - start_time) * 1000,
            )
            self.monitor.record_event(event)
            raise

    async def collect_team_info(self, team_id: str) -> dict[str, Any]:
        """采集球队信息（带监控）"""
        start_time = time.monotonic()
        try:
            result = await self.collector.collect_team_info(team_id)

            # 记录成功事件
            event = RequestEvent(
                source=self.source,
                method="collect_team_info",
                url=f"{self.source}://api/teamDetails?teamId={team_id}",
                response_time_ms=(time.monotonic() - start_time) * 1000,
            )
            self.monitor.record_event(event)

            return result

        except Exception as e:
            # 记录失败事件
            event = RequestEvent(
                source=self.source,
                method="collect_team_info",
                url=f"{self.source}://api/teamDetails?teamId={team_id}",
                error=str(e),
                response_time_ms=(time.monotonic() - start_time) * 1000,
            )
            self.monitor.record_event(event)
            raise

    async def check_health(self) -> dict[str, Any]:
        """健康检查（带监控）"""
        start_time = time.monotonic()
        try:
            result = await self.collector.check_health()

            # 记录成功事件
            event = RequestEvent(
                source=self.source,
                method="check_health",
                url=f"{self.source}://health",
                response_time_ms=(time.monotonic() - start_time) * 1000,
            )
            self.monitor.record_event(event)

            return result

        except Exception as e:
            # 记录失败事件
            event = RequestEvent(
                source=self.source,
                method="check_health",
                url=f"{self.source}://health",
                error=str(e),
                response_time_ms=(time.monotonic() - start_time) * 1000,
            )
            self.monitor.record_event(event)
            raise

    async def close(self) -> None:
        """关闭采集器"""
        await self.collector.close()

    def __getattr__(self, name):
        """转发其他属性调用到原始采集器"""
        return getattr(self.collector, name)


# 全局工厂实例
_global_factory: Optional[HttpClientFactory] = None


def get_http_client_factory() -> HttpClientFactory:
    """获取全局HTTP客户端工厂实例"""
    global _global_factory
    if _global_factory is None:
        _global_factory = HttpClientFactory()
    return _global_factory


async def create_collector(source: str) -> BaseCollectorProtocol:
    """创建采集器的便利函数"""
    factory = get_http_client_factory()
    return await factory.create_collector(source)


async def create_http_client(source: str) -> httpx.AsyncClient:
    """创建HTTP客户端的便利函数"""
    factory = get_http_client_factory()
    return await factory.create_client(source)


# 导出
__all__ = [
    "CollectorConfig",
    "FotMobConfig",
    "RequestEvent",
    "RequestMonitor",
    "HttpClientFactory",
    "MonitoredCollector",
    "get_http_client_factory",
    "create_collector",
    "create_http_client",
]
