"""
基础数据采集器
提供通用的数据采集功能和接口规范
"""

import asyncio
import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime
from typing import Any

import aiohttp
import backoff

logger = logging.getLogger(__name__)


@dataclass
class CollectionResult:
    """数据采集结果"""

    success: bool
    data: Any | None = None
    error: str | None = None
    status_code: int | None = None
    response_time: float | None = None
    cached: bool = False


class BaseCollector(ABC):
    """基础数据采集器抽象类"""

    def __init__(
        self,
        api_key: str,
        base_url: str,
        timeout: int = 30,
        max_retries: int = 3,
        rate_limit: int = 10,  # requests per minute
    ):
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")
        self.timeout = aiohttp.ClientTimeout(total=timeout)
        self.max_retries = max_retries
        self.rate_limit = rate_limit
        self.session: aiohttp.ClientSession | None = None
        self._last_request_time = 0.0
        self._request_count = 0

    async def __aenter__(self):
        """异步上下文管理器入口"""
        await self._ensure_session()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """异步上下文管理器出口"""
        await self.close()

    async def _ensure_session(self):
        """确保会话存在"""
        if self.session is None or self.session.closed:
            headers = await self._get_headers()
            self.session = aiohttp.ClientSession(headers=headers, timeout=self.timeout)

    async def close(self):
        """关闭会话"""
        if self.session and not self.session.closed:
            await self.session.close()

    @abstractmethod
    async def _get_headers(self) -> dict[str, str]:
        """获取请求头"""

    @abstractmethod
    def _build_url(self, endpoint: str, **params) -> str:
        """构建请求URL"""

    async def _rate_limit_wait(self):
        """速率限制等待"""
        current_time = asyncio.get_event_loop().time()
        time_since_last_request = current_time - self._last_request_time

        # 计算最小间隔时间 (60秒 / 每分钟请求数)
        min_interval = 60.0 / self.rate_limit

        if time_since_last_request < min_interval:
            wait_time = min_interval - time_since_last_request
            logger.debug(f"Rate limiting: waiting {wait_time:.2f} seconds")
            await asyncio.sleep(wait_time)

        self._last_request_time = asyncio.get_event_loop().time()

    @backoff.on_exception(
        backoff.expo,
        (aiohttp.ClientError, asyncio.TimeoutError),
        max_tries=3,
        base=1,
        max_value=10,
    )
    async def _make_request(self, method: str, url: str, **kwargs) -> CollectionResult:
        """发起HTTP请求"""
        start_time = asyncio.get_event_loop().time()

        try:
            await self._rate_limit_wait()
            await self._ensure_session()

            logger.debug(f"Making {method} request to: {url}")

            async with self.session.request(method, url, **kwargs) as response:
                response_time = asyncio.get_event_loop().time() - start_time
                self._request_count += 1

                # 记录请求统计
                logger.debug(
                    f"Request completed: {response.status} "
                    f"in {response_time:.2f}s "
                    f"(total requests: {self._request_count})"
                )

                if response.status == 200:
                    data = await response.json()
                    return CollectionResult(
                        success=True,
                        data=data,
                        status_code=response.status,
                        response_time=response_time,
                    )
                else:
                    error_text = await response.text()
                    logger.error(
                        f"API request failed: {response.status} - {error_text}"
                    )
                    return CollectionResult(
                        success=False,
                        error=f"HTTP {response.status}: {error_text}",
                        status_code=response.status,
                        response_time=response_time,
                    )

        except TimeoutError:
            response_time = asyncio.get_event_loop().time() - start_time
            logger.error(f"Request timeout after {response_time:.2f}s")
            return CollectionResult(
                success=False, error="Request timeout", response_time=response_time
            )

        except aiohttp.ClientError as e:
            response_time = asyncio.get_event_loop().time() - start_time
            logger.error(f"Client error: {e}")
            return CollectionResult(
                success=False,
                error=f"Client error: {str(e)}",
                response_time=response_time,
            )

        except Exception as e:
            response_time = asyncio.get_event_loop().time() - start_time
            logger.error(f"Unexpected error: {e}")
            return CollectionResult(
                success=False,
                error=f"Unexpected error: {str(e)}",
                response_time=response_time,
            )

    async def get(
        self, endpoint: str, params: dict[str, Any] | None = None
    ) -> CollectionResult:
        """GET请求"""
        url = self._build_url(endpoint, **(params or {}))
        return await self._make_request("GET", url)

    async def post(
        self, endpoint: str, data: dict[str, Any] | None = None
    ) -> CollectionResult:
        """POST请求"""
        url = self._build_url(endpoint)
        return await self._make_request("POST", url, json=data)

    @abstractmethod
    async def collect_matches(
        self,
        league_id: int | None = None,
        date_from: datetime | None = None,
        date_to: datetime | None = None,
    ) -> CollectionResult:
        """采集比赛数据"""

    @abstractmethod
    async def collect_teams(self, league_id: int | None = None) -> CollectionResult:
        """采集球队数据"""

    @abstractmethod
    async def collect_players(self, team_id: int | None = None) -> CollectionResult:
        """采集球员数据"""

    @abstractmethod
    async def collect_leagues(self) -> CollectionResult:
        """采集联赛数据"""

    def get_request_stats(self) -> dict[str, Any]:
        """获取请求统计信息"""
        return {
            "total_requests": self._request_count,
            "last_request_time": self._last_request_time,
            "rate_limit": self.rate_limit,
        }

    async def health_check(self) -> bool:
        """健康检查"""
        try:
            # 使用一个轻量级的端点进行健康检查
            result = await self.get("/status")
            return result.success
        except Exception as e:
            logger.error(f"Health check failed: {e}")
            return False


class CollectorError(Exception):
    """采集器异常"""


class RateLimitError(CollectorError):
    """速率限制异常"""


class AuthenticationError(CollectorError):
    """认证异常"""


class DataValidationError(CollectorError):
    """数据验证异常"""
