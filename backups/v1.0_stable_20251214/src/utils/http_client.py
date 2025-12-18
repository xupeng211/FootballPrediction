"""
异步 HTTP 客户端模块
Async HTTP Client Module

提供高性能、可靠的异步 HTTP 请求功能，支持：
- 自动 User-Agent 轮换
- 智能重试机制（指数退避）
- 连接池管理
- 超时控制
- 错误处理

作者: Senior Python Engineer
创建时间: 2025-12-07
版本: 1.0.0
"""

import asyncio
import random
import time
from typing import Any, Optional

import httpx
from fake_useragent import UserAgent

from src.core.logging import get_logger

logger = get_logger(__name__)


class AsyncHttpClient:
    """
    异步 HTTP 客户端

    提供企业级的 HTTP 请求功能，具备智能重试、User-Agent 轮换等特性。
    专门为数据采集场景设计，避免触发反爬虫机制。
    """

    def __init__(
        self,
        timeout: float = 30.0,
        max_retries: int = 3,
        retry_delay: float = 1.0,
        max_connections: int = 20,
        enable_jitter: bool = True,
    ):
        """
        初始化异步 HTTP 客户端

        Args:
            timeout: 请求超时时间（秒）
            max_retries: 最大重试次数
            retry_delay: 初始重试延迟（秒）
            max_connections: 最大连接池大小
            enable_jitter: 是否启用重试抖动
        """
        self.timeout = timeout
        self.max_retries = max_retries
        self.retry_delay = retry_delay
        self.max_connections = max_connections
        self.enable_jitter = enable_jitter

        # User-Agent 管理器
        self.ua = UserAgent()

        # HTTP 客户端（延迟初始化）
        self._client: Optional[httpx.AsyncClient] = None

        # 统计信息
        self.stats = {
            "requests_made": 0,
            "successful_requests": 0,
            "failed_requests": 0,
            "retries_triggered": 0,
            "total_response_time": 0.0,
        }

        logger.info(
            "🌐 AsyncHttpClient 初始化完成",
            extra={
                "timeout": timeout,
                "max_retries": max_retries,
                "max_connections": max_connections,
            },
        )

    async def _get_client(self) -> httpx.AsyncClient:
        """获取或创建 HTTP 客户端"""
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(
                timeout=httpx.Timeout(self.timeout),
                limits=httpx.Limits(
                    max_connections=self.max_connections,
                    max_keepalive_connections=self.max_connections // 2,
                ),
                follow_redirects=True,
                verify=False,  # 仅用于测试，生产环境应启用
            )
        return self._client

    def _get_random_headers(
        self, additional_headers: Optional[dict[str, str]] = None
    ) -> dict[str, str]:
        """
        获取随机请求头

        Args:
            additional_headers: 额外的请求头

        Returns:
            完整的请求头字典
        """
        headers = {
            "User-Agent": self.ua.random,
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.5",
            "Accept-Encoding": "gzip, deflate, br",
            "DNT": "1",
            "Connection": "keep-alive",
            "Upgrade-Insecure-Requests": "1",
        }

        # 添加额外请求头
        if additional_headers:
            headers.update(additional_headers)

        return headers

    def _calculate_retry_delay(self, attempt: int) -> float:
        """
        计算重试延迟（指数退避 + 抖动）

        Args:
            attempt: 当前尝试次数

        Returns:
            延迟时间（秒）
        """
        base_delay = self.retry_delay * (2 ** (attempt - 1))

        if self.enable_jitter:
            # 添加 ±25% 的随机抖动
            jitter_factor = random.uniform(0.75, 1.25)
            base_delay *= jitter_factor

        # 最大延迟限制
        max_delay = min(base_delay, 60.0)

        logger.debug(
            "🔄 计算重试延迟",
            extra={
                "attempt": attempt,
                "base_delay": base_delay,
                "max_delay": max_delay,
                "jitter_enabled": self.enable_jitter,
            },
        )

        return max_delay

    async def _make_request(self, method: str, url: str, **kwargs) -> httpx.Response:
        """
        执行单次 HTTP 请求

        Args:
            method: HTTP 方法
            url: 请求 URL
            **kwargs: 其他请求参数

        Returns:
            HTTP 响应对象

        Raises:
            httpx.HTTPError: HTTP 请求失败
        """
        client = await self._get_client()

        # 设置随机请求头
        headers = self._get_random_headers(kwargs.pop("headers", None))
        kwargs["headers"] = headers

        start_time = time.time()

        try:
            response = await client.request(method, url, **kwargs)
            response_time = time.time() - start_time

            # 更新统计信息
            self.stats["requests_made"] += 1
            self.stats["total_response_time"] += response_time

            logger.debug(
                "📡 HTTP 请求完成",
                extra={
                    "method": method,
                    "url": url,
                    "status_code": response.status_code,
                    "response_time": f"{response_time:.3f}s",
                },
            )

            return response

        except Exception as e:
            response_time = time.time() - start_time
            self.stats["requests_made"] += 1
            self.stats["failed_requests"] += 1

            logger.warning(
                "❌ HTTP 请求失败",
                extra={
                    "method": method,
                    "url": url,
                    "error": str(e),
                    "response_time": f"{response_time:.3f}s",
                },
            )

            raise

    async def _retry_request(self, method: str, url: str, **kwargs) -> httpx.Response:
        """
        带重试的 HTTP 请求

        Args:
            method: HTTP 方法
            url: 请求 URL
            **kwargs: 其他请求参数

        Returns:
            HTTP 响应对象
        """
        last_exception = None

        for attempt in range(1, self.max_retries + 1):
            try:
                response = await self._make_request(method, url, **kwargs)

                # 检查是否需要重试（基于状态码）
                if response.status_code in [429, 500, 502, 503, 504]:
                    if attempt < self.max_retries:
                        self.stats["retries_triggered"] += 1
                        delay = self._calculate_retry_delay(attempt)

                        logger.warning(
                            "🔄 触发重试",
                            extra={
                                "attempt": attempt,
                                "max_retries": self.max_retries,
                                "status_code": response.status_code,
                                "delay": f"{delay:.3f}s",
                            },
                        )

                        await asyncio.sleep(delay)
                        continue

                # 请求成功
                self.stats["successful_requests"] += 1
                return response

            except (httpx.RequestError, httpx.TimeoutException) as e:
                last_exception = e

                if attempt < self.max_retries:
                    self.stats["retries_triggered"] += 1
                    delay = self._calculate_retry_delay(attempt)

                    logger.warning(
                        "🔄 网络错误重试",
                        extra={
                            "attempt": attempt,
                            "max_retries": self.max_retries,
                            "error": str(e),
                            "delay": f"{delay:.3f}s",
                        },
                    )

                    await asyncio.sleep(delay)
                    continue

                break  # 达到最大重试次数

        # 所有重试都失败了
        self.stats["failed_requests"] += 1
        raise last_exception or Exception("Request failed after all retries")

    async def get(
        self,
        url: str,
        params: Optional[dict[str, Any]] = None,
        headers: Optional[dict[str, str]] = None,
        **kwargs,
    ) -> httpx.Response:
        """
        发送 GET 请求

        Args:
            url: 请求 URL
            params: URL 参数
            headers: 额外请求头
            **kwargs: 其他请求参数

        Returns:
            HTTP 响应对象
        """
        return await self._retry_request(
            "GET", url, params=params, headers=headers, **kwargs
        )

    async def post(
        self,
        url: str,
        data: Optional[dict[str, Any]] = None,
        json: Optional[dict[str, Any]] = None,
        headers: Optional[dict[str, str]] = None,
        **kwargs,
    ) -> httpx.Response:
        """
        发送 POST 请求

        Args:
            url: 请求 URL
            data: 表单数据
            json: JSON 数据
            headers: 额外请求头
            **kwargs: 其他请求参数

        Returns:
            HTTP 响应对象
        """
        return await self._retry_request(
            "POST", url, data=data, json=json, headers=headers, **kwargs
        )

    async def get_text(self, url: str, encoding: str = "utf-8", **kwargs) -> str:
        """
        获取响应文本内容

        Args:
            url: 请求 URL
            encoding: 文本编码
            **kwargs: 其他请求参数

        Returns:
            响应文本内容
        """
        response = await self.get(url, **kwargs)
        response.encoding = encoding
        return response.text

    def get_stats(self) -> dict[str, Any]:
        """
        获取客户端统计信息

        Returns:
            统计信息字典
        """
        stats = self.stats.copy()
        if stats["requests_made"] > 0:
            stats["average_response_time"] = (
                stats["total_response_time"] / stats["requests_made"]
            )
            stats["success_rate"] = (
                stats["successful_requests"] / stats["requests_made"]
            )
        else:
            stats["average_response_time"] = 0.0
            stats["success_rate"] = 0.0

        return stats

    async def close(self):
        """关闭 HTTP 客户端"""
        if self._client and not self._client.is_closed:
            await self._client.aclose()
            logger.info("🔌 AsyncHttpClient 已关闭")

    async def __aenter__(self):
        """异步上下文管理器入口"""
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """异步上下文管理器出口"""
        await self.close()


# 便利函数
async def create_http_client(**kwargs) -> AsyncHttpClient:
    """
    创建并配置异步 HTTP 客户端

    Args:
        **kwargs: 客户端配置参数

    Returns:
        配置好的 HTTP 客户端实例
    """
    return AsyncHttpClient(**kwargs)
