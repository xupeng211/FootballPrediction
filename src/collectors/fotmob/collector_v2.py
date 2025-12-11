"""
FotMob 采集器 V2 - 生产级抗封锁实现
FotMob Collector V2 - Production-Grade Anti-Blocking Implementation

基于已建立的基础设施（接口、限流、代理、认证），重构 FotMob 采集器，
实现一个生产级、抗封锁的新版采集器。

核心特性:
1. 实现 BaseCollectorProtocol 接口
2. 依赖注入设计 (RateLimiter, ProxyPool, TokenManager)
3. 动态代理配置和Token注入
4. 智能错误处理和重试机制
5. 401/403 自动Token刷新
6. 代理健康状态管理

作者: Lead Collector Engineer
创建时间: 2025-12-06
版本: 2.0.0
"""

import asyncio
import json
import time
from typing import Any, Optional

import httpx

from ..auth import TokenManager
from ..interface import (
    CollectorError,
    AuthenticationError,
    RateLimitError,
    NetworkError,
    DataNotFoundError,
)
from ..proxy_pool import Proxy, ProxyPool
from ..rate_limiter import RateLimiter


class FotMobCollectorV2:
    """
    FotMob 采集器 V2 版本

    基于已建立的基础设施实现的生产级采集器，具备以下特性：
    - 完全符合 BaseCollectorProtocol 接口
    - 依赖注入设计，便于测试和扩展
    - 智能代理管理和Token注入
    - 健壮的错误处理和重试机制
    - 401/403 自动Token刷新
    """

    def __init__(
        self,
        rate_limiter: RateLimiter,
        proxy_pool: ProxyPool,
        token_manager: TokenManager,
        base_url: str = "https://www.fotmob.com",
        timeout: float = 30.0,
        max_retries: int = 3,
        retry_delay: float = 1.0,
    ):
        """
        初始化 FotMob 采集器

        Args:
            rate_limiter: 速率限制器实例
            proxy_pool: 代理池实例
            token_manager: Token管理器实例
            base_url: FotMob API基础URL
            timeout: HTTP请求超时时间（秒）
            max_retries: 最大重试次数
            retry_delay: 重试延迟（秒）
        """
        self.rate_limiter = rate_limiter
        self.proxy_pool = proxy_pool
        self.token_manager = token_manager
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self.max_retries = max_retries
        self.retry_delay = retry_delay

        # 内部状态
        self._error_count = 0
        self._last_error: Optional[str] = None
        self._closed = False

        # 统计信息
        self.stats = {
            "total_requests": 0,
            "successful_requests": 0,
            "failed_requests": 0,
            "token_refreshes": 0,
            "proxy_rotations": 0,
            "rate_limited_requests": 0,
        }

    async def _get_client(self, proxy: Optional[Proxy] = None) -> httpx.AsyncClient:
        """
        动态构建 HTTP 客户端

        Args:
            proxy: 可选的代理配置

        Returns:
            httpx.AsyncClient: 配置好的HTTP客户端
        """
        # 基础配置
        client_config = {
            "timeout": httpx.Timeout(self.timeout),
            "headers": {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                "Accept": "application/json, text/plain, */*",
                "Accept-Language": "en-US,en;q=0.9",
                "Accept-Encoding": "gzip, deflate, br",
                "Connection": "keep-alive",
                "Upgrade-Insecure-Requests": "1",
            },
            "follow_redirects": True,
        }

        # 配置代理
        if proxy:
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

    async def _inject_auth_headers(
        self, headers: dict[str, str], provider_name: str = "fotmob"
    ) -> dict[str, str]:
        """
        注入认证头部

        Args:
            headers: 原始请求头
            provider_name: Token提供者名称

        Returns:
            dict[str, str]: 包含认证信息的请求头
        """
        try:
            token = await self.token_manager.get_token(provider_name)
            if token.token_type.value == "custom_header":
                # FotMob使用自定义头部
                headers.update(token.headers)
            elif token.token_type.value == "bearer":
                headers["Authorization"] = f"Bearer {token.value}"
            elif token.token_type.value == "api_key":
                headers["X-API-Key"] = token.value

            return headers
        except Exception as e:
            raise AuthenticationError(f"Failed to inject authentication headers: {e}")

    async def _make_request(
        self,
        method: str,
        url: str,
        *,
        params: Optional[dict[str, Any]] = None,
        headers: Optional[dict[str, str]] = None,
        provider_name: str = "fotmob",
    ) -> httpx.Response:
        """
        发起HTTP请求，包含完整的错误处理和重试逻辑

        Args:
            method: HTTP方法
            url: 请求URL
            params: URL参数
            headers: 请求头
            provider_name: Token提供者名称

        Returns:
            httpx.Response: HTTP响应

        Raises:
            NetworkError: 网络错误
            AuthenticationError: 认证失败
            CollectorError: 其他采集错误
        """
        if self._closed:
            raise CollectorError("Collector has been closed")

        # 准备请求头
        request_headers = headers or {}
        request_headers = await self._inject_auth_headers(
            request_headers, provider_name
        )

        # 记录请求开始
        self.stats["total_requests"] += 1
        start_time = time.monotonic()

        for attempt in range(self.max_retries + 1):
            proxy = None

            try:
                # 应用速率限制
                async with self.rate_limiter.acquire("fotmob_api"):
                    self.stats["rate_limited_requests"] += 1 if attempt > 0 else 0

                    # 获取代理（如果配置了代理池）
                    if self.proxy_pool:
                        proxy = await self.proxy_pool.get_proxy()
                        if proxy:
                            self.stats["proxy_rotations"] += 1

                    # 构建客户端并发起请求
                    async with await self._get_client(proxy) as client:
                        response = await client.request(
                            method=method,
                            url=url,
                            params=params,
                            headers=request_headers,
                        )

                    # 处理认证错误
                    if response.status_code in (401, 403):
                        if attempt < self.max_retries:
                            # 强制刷新Token并重试
                            await self.token_manager.get_token(
                                provider_name, force_refresh=True
                            )
                            self.stats["token_refreshes"] += 1
                            await asyncio.sleep(self.retry_delay * (2**attempt))
                            continue
                        else:
                            raise AuthenticationError(
                                f"Authentication failed after {self.max_retries} retries"
                            )

                    # 处理其他HTTP错误
                    if response.status_code >= 400:
                        if response.status_code == 404:
                            raise DataNotFoundError(f"Resource not found: {url}")
                        elif response.status_code == 429:
                            if attempt < self.max_retries:
                                await asyncio.sleep(self.retry_delay * (2**attempt))
                                continue
                            raise RateLimitError("Rate limit exceeded")
                        elif response.status_code >= 500:
                            raise NetworkError(f"Server error: {response.status_code}")
                        else:
                            raise CollectorError(f"HTTP error: {response.status_code}")

                    # 记录成功
                    self.stats["successful_requests"] += 1
                    if proxy:
                        await self.proxy_pool.record_proxy_result(
                            proxy, True, (time.monotonic() - start_time) * 1000
                        )

                    return response

            except httpx.TimeoutException:
                error_msg = f"Request timeout after {self.timeout}s"
                if proxy:
                    await self.proxy_pool.record_proxy_result(
                        proxy, False, self.timeout * 1000
                    )
            except httpx.NetworkError as e:
                error_msg = f"Network error: {e}"
                if proxy:
                    await self.proxy_pool.record_proxy_result(
                        proxy, False, self.timeout * 1000
                    )
            except httpx.HTTPError as e:
                error_msg = f"HTTP error: {e}"
            except (AuthenticationError, RateLimitError, DataNotFoundError):
                # 这些是我们已知的业务错误，直接抛出
                self.stats["failed_requests"] += 1
                raise
            except Exception as e:
                error_msg = f"Unexpected error: {e}"
                if proxy:
                    await self.proxy_pool.record_proxy_result(
                        proxy, False, self.timeout * 1000
                    )

            # 重试逻辑
            if attempt < self.max_retries:
                await asyncio.sleep(self.retry_delay * (2**attempt))
            else:
                # 所有重试都失败了
                self.stats["failed_requests"] += 1
                self._error_count += 1
                self._last_error = error_msg
                raise NetworkError(
                    f"Request failed after {self.max_retries} retries: {error_msg}"
                )

    async def collect_fixtures(
        self, league_id: int, season_id: Optional[str] = None
    ) -> list[dict[str, Any]]:
        """
        采集联赛赛程数据

        Args:
            league_id: 联赛ID (如: 47 for Premier League)
            season_id: 赛季ID (可选，如: "2024-2025")

        Returns:
            list[dict[str, Any]]: 赛程数据列表

        Raises:
            CollectorError: 采集过程中的通用错误
            AuthenticationError: 认证失败
            RateLimitError: 速率限制
            NetworkError: 网络连接问题
        """
        url = f"{self.base_url}/api/matches"
        params = {"leagueId": league_id}
        if season_id:
            params["seasonId"] = season_id

        try:
            response = await self._make_request("GET", url, params=params)
            data = response.json()

            # 解析赛程数据
            fixtures = []
            matches = data.get("matches", [])

            for match in matches:
                fixture = {
                    "match_id": str(match.get("id", "")),
                    "home_team": match.get("home", {}).get("name", ""),
                    "away_team": match.get("away", {}).get("name", ""),
                    "kickoff_time": match.get("status", {}).get("utcTime", ""),
                    "venue": match.get("venue", {}).get("name"),
                    "status": match.get("status", {}).get("statusCode", ""),
                    "league_id": league_id,
                    "season_id": season_id,
                }
                fixtures.append(fixture)

            return fixtures

        except json.JSONDecodeError as e:
            raise CollectorError(f"Failed to parse JSON response: {e}")
        except Exception as e:
            if isinstance(e, AuthenticationError | RateLimitError | NetworkError):
                raise
            raise CollectorError(f"Failed to collect fixtures: {e}")

    async def collect_match_details(self, match_id: str) -> dict[str, Any]:
        """
        采集比赛详情数据

        Args:
            match_id: 比赛唯一标识

        Returns:
            dict[str, Any]: 比赛详情数据

        Raises:
            CollectorError: 采集过程中的通用错误
            DataNotFoundError: 比赛数据不存在
            AuthenticationError: 认证失败
            RateLimitError: 速率限制
            NetworkError: 网络连接问题
        """
        url = f"{self.base_url}/api/matchDetails"
        params = {"matchId": match_id}

        try:
            response = await self._make_request("GET", url, params=params)
            data = response.json()

            if not data:
                raise DataNotFoundError(f"No data found for match {match_id}")

            # 解析比赛详情
            match_data = data.get("match", {})
            content = data.get("content", {})

            details = {
                "match_id": match_id,
                "home_team": match_data.get("home", {}).get("name", ""),
                "away_team": match_data.get("away", {}).get("name", ""),
                "home_score": match_data.get("home", {}).get("score"),
                "away_score": match_data.get("away", {}).get("score"),
                "status": match_data.get("status", {}).get("statusCode", ""),
                "kickoff_time": match_data.get("status", {}).get("utcTime", ""),
            }

            # 添加期望进球数
            xg_data = content.get("expectedGoals", {})
            if xg_data:
                details["home_xg"] = xg_data.get("home")
                details["away_xg"] = xg_data.get("away")

            # 添加射门数据
            shot_stats = content.get("shotmap", {}).get("stats", {})
            if shot_stats:
                details["shots"] = {
                    "home": shot_stats.get("home", {}).get("total", 0),
                    "away": shot_stats.get("away", {}).get("total", 0),
                }

            # 添加控球率
            possession_stats = content.get("possession", {})
            if possession_stats:
                details["possession"] = {
                    "home": possession_stats.get("home", 0),
                    "away": possession_stats.get("away", 0),
                }

            # 添加比赛事件
            events = content.get("lineUp", {}).get("lineups", [])
            details["events"] = events

            # 添加阵容信息
            lineups = content.get("lineUp", {})
            details["lineups"] = {
                "home": lineups.get("home", []),
                "away": lineups.get("away", []),
            }

            # 添加赔率数据（如果有）
            odds_data = content.get("matchStats", {}).get("odds", {})
            if odds_data:
                details["odds"] = odds_data

            return details

        except json.JSONDecodeError as e:
            raise CollectorError(f"Failed to parse JSON response: {e}")
        except Exception as e:
            if isinstance(
                e,
                DataNotFoundError | AuthenticationError | RateLimitError | NetworkError,
            ):
                raise
            raise CollectorError(f"Failed to collect match details: {e}")

    async def collect_team_info(self, team_id: str) -> dict[str, Any]:
        """
        采集球队信息

        Args:
            team_id: 球队唯一标识

        Returns:
            dict[str, Any]: 球队信息

        Raises:
            CollectorError: 采集过程中的通用错误
            DataNotFoundError: 球队数据不存在
        """
        url = f"{self.base_url}/api/teamDetails"
        params = {"teamId": team_id}

        try:
            response = await self._make_request("GET", url, params=params)
            data = response.json()

            if not data:
                raise DataNotFoundError(f"No data found for team {team_id}")

            team_data = data.get("teamDetails", {}).get("team", {})

            info = {
                "team_id": team_id,
                "name": team_data.get("name", ""),
                "country": team_data.get("country", ""),
                "founded": team_data.get("founded"),
                "stadium": team_data.get("venue", {}).get("name"),
                "logo_url": team_data.get("logoUrl"),
            }

            return info

        except json.JSONDecodeError as e:
            raise CollectorError(f"Failed to parse JSON response: {e}")
        except Exception as e:
            if isinstance(
                e,
                DataNotFoundError | AuthenticationError | RateLimitError | NetworkError,
            ):
                raise
            raise CollectorError(f"Failed to collect team info: {e}")

    async def check_health(self) -> dict[str, Any]:
        """
        检查采集器健康状态

        Returns:
            dict[str, Any]: 健康状态信息

        Raises:
            CollectorError: 健康检查失败
        """
        start_time = time.monotonic()
        status = "healthy"
        details = {}

        try:
            # 1. 检查API连通性
            url = f"{self.base_url}/api/matches"
            await self._make_request(
                "GET", url, params={"leagueId": 47}
            )  # Test with Premier League
            details["api_connectivity"] = True
        except Exception as e:
            status = "unhealthy"
            details["api_connectivity"] = False
            details["api_error"] = str(e)

        try:
            # 2. 检查Token状态
            token_stats = await self.token_manager.get_stats()
            details["token_stats"] = token_stats
            if token_stats["valid_tokens"] == 0:
                status = "unhealthy"
        except Exception as e:
            details["token_error"] = str(e)

        try:
            # 3. 检查代理池状态
            if self.proxy_pool:
                proxy_stats = self.proxy_pool.get_stats()
                details["proxy_stats"] = proxy_stats
                if proxy_stats["active"] == 0:
                    status = "degraded"
        except Exception as e:
            details["proxy_error"] = str(e)

        # 计算响应时间
        response_time_ms = (time.monotonic() - start_time) * 1000
        if response_time_ms > 5000:  # 5秒阈值
            if status == "healthy":
                status = "degraded"

        return {
            "status": status,
            "response_time_ms": round(response_time_ms, 2),
            "last_check": time.strftime("%Y-%m-%d %H:%M:%S UTC"),
            "error_count": self._error_count,
            "last_error": self._last_error,
            "stats": self.stats.copy(),
            "details": details,
        }

    async def close(self) -> None:
        """清理资源并关闭采集器"""
        if self._closed:
            return

        self._closed = True

        # 保存最终统计信息
        final_stats = {
            "total_requests": self.stats["total_requests"],
            "successful_requests": self.stats["successful_requests"],
            "failed_requests": self.stats["failed_requests"],
            "success_rate": (
                self.stats["successful_requests"]
                / max(self.stats["total_requests"], 1)
                * 100
            ),
            "token_refreshes": self.stats["token_refreshes"],
            "proxy_rotations": self.stats["proxy_rotations"],
            "rate_limited_requests": self.stats["rate_limited_requests"],
            "error_count": self._error_count,
        }

        print(f"📊 FotMobCollectorV2 关闭统计: {final_stats}")
        self.stats = final_stats

    def __del__(self):
        """析构函数，确保资源被清理"""
        if not self._closed:
            # 注意：这里不能使用await，因为析构函数是同步的
            print("⚠️ FotMobCollectorV2 没有被正确关闭，请确保调用 close() 方法")


# 便利函数，用于创建采集器实例
def create_fotmob_collector_v2(
    rate_limiter: RateLimiter,
    proxy_pool: ProxyPool,
    token_manager: TokenManager,
    **kwargs,
) -> FotMobCollectorV2:
    """
    创建 FotMob 采集器 V2 实例的便利函数

    Args:
        rate_limiter: 速率限制器
        proxy_pool: 代理池
        token_manager: Token管理器
        **kwargs: 其他传递给采集器的参数

    Returns:
        FotMobCollectorV2: 采集器实例
    """
    return FotMobCollectorV2(rate_limiter, proxy_pool, token_manager, **kwargs)


# 导出
__all__ = [
    "FotMobCollectorV2",
    "create_fotmob_collector_v2",
]
