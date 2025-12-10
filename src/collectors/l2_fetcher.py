#!/usr/bin/env python3
"""
L2数据获取器 (L2 Data Fetcher) - 生产版本
负责从FotMob API获取L2详情数据，包含重试机制、压缩处理和错误处理。

核心功能:
1. HTTP请求管理 (AsyncClient + tenacity重试)
2. 压缩数据处理 (Brotli检测和无压缩重试)
3. 错误处理和自定义异常
4. 认证头部管理
5. 结构化日志记录
6. 性能监控和统计

作者: L2重构团队
创建时间: 2025-12-10
版本: 1.0.0 (Production Release)
"""

import asyncio
import logging
import os
import time
from typing import Optional, Dict, Any, Tuple

import httpx
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type,
    before_sleep_log,
)

from .user_agent import UserAgentManager
from .rate_limiter import RateLimiter
from .interface import (
    AuthenticationError,
    RateLimitError,
    NetworkError,
    DataNotFoundError,
)

logger = logging.getLogger(__name__)


class L2FetchError(Exception):
    """L2数据获取自定义异常"""

    def __init__(self, message: str, match_id: str, status_code: Optional[int] = None):
        super().__init__(message)
        self.match_id = match_id
        self.status_code = status_code
        self.message = message

    def __repr__(self) -> str:
        return f"L2FetchError(match_id={self.match_id}, status_code={self.status_code}, message='{self.message}')"


class L2Fetcher:
    """
    L2数据获取器 - 生产版本

    负责从FotMob API获取L2详情数据，包含完整的重试机制、
    压缩处理、错误处理和性能监控功能。

    Attributes:
        base_url: FotMob API基础URL
        timeout: HTTP请求超时时间
        max_retries: 最大重试次数
        rate_limiter: 速率限制器
        user_agent_manager: User-Agent管理器
        stats: 统计信息
    """

    def __init__(
        self,
        base_url: str = "https://www.fotmob.com",
        timeout: float = 30.0,
        max_retries: int = 5,
        rate_limiter: Optional[RateLimiter] = None,
    ):
        """
        初始化L2数据获取器

        Args:
            base_url: FotMob API基础URL
            timeout: HTTP请求超时时间（秒）
            max_retries: 最大重试次数
            rate_limiter: 速率限制器实例
        """
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self.max_retries = max_retries
        self.rate_limiter = rate_limiter
        self.user_agent_manager = UserAgentManager()

        # HTTP客户端（延迟初始化）
        self._http_client: Optional[httpx.AsyncClient] = None

        # 统计信息
        self.stats = {
            "total_requests": 0,
            "successful_requests": 0,
            "failed_requests": 0,
            "retry_attempts": 0,
            "rate_limited_requests": 0,
            "authentication_errors": 0,
            "network_errors": 0,
            "not_found_errors": 0,
            "server_errors": 0,
            "compression_errors": 0,
            "total_response_time_ms": 0,
            "average_response_time_ms": 0.0,
        }

        logger.info(
            f"L2Fetcher initialized with base_url={base_url}, "
            f"timeout={timeout}s, max_retries={max_retries}"
        )

    async def _get_http_client(self) -> httpx.AsyncClient:
        """
        获取HTTP客户端实例（延迟初始化）

        Returns:
            httpx.AsyncClient: 配置好的HTTP客户端

        Raises:
            RuntimeError: 如果客户端初始化失败
        """
        if self._http_client is None or self._http_client.is_closed:
            timeout_config = httpx.Timeout(self.timeout)
            limits_config = httpx.Limits(
                max_connections=20,
                max_keepalive_connections=10
            )

            headers = self._build_request_headers()

            try:
                self._http_client = httpx.AsyncClient(
                    timeout=timeout_config,
                    limits=limits_config,
                    headers=headers,
                    follow_redirects=True
                )
                logger.debug("HTTP client initialized successfully")
            except Exception as initialization_error:
                logger.error(f"Failed to initialize HTTP client: {initialization_error}")
                raise RuntimeError(f"HTTP client initialization failed: {initialization_error}")

        return self._http_client

    async def _fetch_without_compression(self, match_id: str) -> httpx.Response:
        """
        发起不压缩的HTTP请求用于处理压缩响应问题

        Args:
            match_id: 比赛ID

        Returns:
            httpx.Response: HTTP响应对象
        """
        from urllib.parse import urlencode

        api_url = f"{self.base_url}/api/matchDetails"
        params = {"matchId": match_id}
        full_url = f"{api_url}?{urlencode(params)}"

        # 构建不请求压缩的头部
        headers_no_compression = self._build_request_headers()
        headers_no_compression["Accept-Encoding"] = "identity"

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.get(full_url, headers=headers_no_compression)
            logger.debug(f"Fetched uncompressed response for match {match_id}, length: {len(response.text)}")
            return response

    def _build_request_headers(self) -> Dict[str, str]:
        """
        构建HTTP请求头

        Returns:
            Dict[str, str]: 包含认证信息的请求头
        """
        headers = {
            "User-Agent": self.user_agent_manager.get_random_user_agent(),
            "Accept": "application/json, text/plain, */*",
            "Accept-Language": "en-US,en;q=0.9",
            "Accept-Encoding": "gzip, deflate, br",
            "Connection": "keep-alive",
            "Cache-Control": "no-cache",
            "Pragma": "no-cache",
            "Sec-Fetch-Dest": "empty",
            "Sec-Fetch-Mode": "cors",
            "Sec-Fetch-Site": "same-origin",
        }

        # 添加FotMob API认证头部
        x_mas_token = os.getenv("FOTMOB_X_MAS_TOKEN")
        x_foo_token = os.getenv("FOTMOB_X_FOO_TOKEN")

        if x_mas_token:
            headers["x-mas"] = x_mas_token
        if x_foo_token:
            headers["x-foo"] = x_foo_token

        return headers

    @retry(
        stop=stop_after_attempt(5),
        wait=wait_exponential(multiplier=1.5, min=2, max=60),
        retry=retry_if_exception_type(
            (httpx.RequestError, httpx.TimeoutException, httpx.NetworkError)
        ),
        before_sleep=before_sleep_log(logger, logging.WARNING),
        reraise=True
    )
    async def _make_http_request(
        self, url: str, match_id: str
    ) -> httpx.Response:
        """
        发起HTTP请求（包含重试逻辑）

        Args:
            url: 请求URL
            match_id: 比赛ID，用于日志和错误处理

        Returns:
            httpx.Response: HTTP响应对象

        Raises:
            L2FetchError: 当请求失败时
            AuthenticationError: 认证失败时
            RateLimitError: 速率限制时
            NetworkError: 网络错误时
        """
        request_start_time = time.monotonic()

        try:
            # 应用速率限制（如果配置了限流器）
            if self.rate_limiter:
                async with self.rate_limiter.acquire("fotmob.com"):
                    http_client = await self._get_http_client()
                    response = await http_client.get(url)
            else:
                http_client = await self._get_http_client()
                response = await http_client.get(url)

            # 记录请求统计
            request_time_ms = (time.monotonic() - request_start_time) * 1000
            self._update_request_stats(True, request_time_ms)

            logger.info(
                f"HTTP request completed for match {match_id}: "
                f"status={response.status_code}, time={request_time_ms:.2f}ms"
            )

            return response

        except httpx.TimeoutException as timeout_error:
            request_time_ms = (time.monotonic() - request_start_time) * 1000
            self._update_request_stats(False, request_time_ms)

            error_message = f"Request timeout for match {match_id} after {self.timeout}s"
            logger.error(error_message)
            raise NetworkError(error_message) from timeout_error

        except httpx.RequestError as request_error:
            request_time_ms = (time.monotonic() - request_start_time) * 1000
            self._update_request_stats(False, request_time_ms)

            error_message = f"Network request failed for match {match_id}: {request_error}"
            logger.error(error_message)
            raise NetworkError(error_message) from request_error

    async def fetch_match_details(self, match_id: str) -> Dict[str, Any]:
        """
        获取比赛详情数据

        Args:
            match_id: 比赛ID

        Returns:
            Dict[str, Any]: API响应的JSON数据

        Raises:
            L2FetchError: 数据获取失败时
            AuthenticationError: 认证失败时
            RateLimitError: 速率限制时
            NetworkError: 网络错误时
            DataNotFoundError: 数据不存在时
        """
        if not match_id or not isinstance(match_id, str):
            raise L2FetchError("Invalid match ID provided", match_id or "None")

        api_url = f"{self.base_url}/api/matchDetails"
        params = {"matchId": match_id}

        logger.info(f"Fetching L2 match details for match {match_id}")

        try:
            # 构建完整URL
            from urllib.parse import urlencode
            full_url = f"{api_url}?{urlencode(params)}"

            # 发起HTTP请求
            response = await self._make_http_request(full_url, match_id)

            # 处理不同的HTTP状态码
            if response.status_code == 200:
                try:
                    # 检查响应是否为空或压缩数据
                    if not response.text or response.text.startswith('��'):
                        logger.warning(f"Received compressed/empty response for match {match_id}, retrying without compression")
                        self.stats["compression_errors"] += 1
                        # 重试时不请求压缩
                        uncompressed_response = await self._fetch_without_compression(match_id)
                        json_data = uncompressed_response.json()
                    else:
                        json_data = response.json()
                    logger.info(f"Successfully fetched L2 data for match {match_id}")
                    return json_data
                except ValueError as json_error:
                    error_message = f"Invalid JSON response for match {match_id}: {json_error}"
                    logger.error(error_message)
                    raise L2FetchError(error_message, match_id, response.status_code)

            elif response.status_code == 401:
                self.stats["authentication_errors"] += 1
                error_message = f"Authentication failed for match {match_id}"
                logger.error(error_message)
                raise AuthenticationError(error_message)

            elif response.status_code == 403:
                self.stats["authentication_errors"] += 1
                error_message = f"Access forbidden for match {match_id}"
                logger.error(error_message)
                raise AuthenticationError(error_message)

            elif response.status_code == 429:
                self.stats["rate_limited_requests"] += 1
                error_message = f"Rate limit exceeded for match {match_id}"
                logger.error(error_message)
                raise RateLimitError(error_message)

            elif response.status_code == 404:
                self.stats["not_found_errors"] += 1
                error_message = f"Match data not found for match {match_id}"
                logger.warning(error_message)
                raise DataNotFoundError(error_message)

            elif 500 <= response.status_code < 600:
                self.stats["server_errors"] += 1
                error_message = f"Server error for match {match_id}: {response.status_code}"
                logger.error(error_message)
                raise L2FetchError(error_message, match_id, response.status_code)

            else:
                error_message = f"Unexpected HTTP status {response.status_code} for match {match_id}"
                logger.error(error_message)
                raise L2FetchError(error_message, match_id, response.status_code)

        except L2FetchError:
            # 重新抛出已知的L2FetchError
            raise
        except (AuthenticationError, RateLimitError, NetworkError, DataNotFoundError):
            # 重新抛出其他已知的业务异常
            raise
        except Exception as unexpected_error:
            error_message = f"Unexpected error fetching match {match_id}: {unexpected_error}"
            logger.error(error_message, exc_info=True)
            raise L2FetchError(error_message, match_id) from unexpected_error

    async def fetch_multiple_matches(
        self, match_ids: list[str], max_concurrent: int = 10
    ) -> Dict[str, Dict[str, Any]]:
        """
        并发获取多个比赛的详情数据

        Args:
            match_ids: 比赛ID列表
            max_concurrent: 最大并发数

        Returns:
            Dict[str, Dict[str, Any]]: 比赛ID到数据的映射
        """
        if not match_ids:
            return {}

        semaphore = asyncio.Semaphore(max_concurrent)

        async def fetch_single_match(match_id: str) -> Tuple[str, Optional[Dict[str, Any]]]:
            async with semaphore:
                try:
                    data = await self.fetch_match_details(match_id)
                    return match_id, data
                except Exception as fetch_error:
                    logger.error(f"Failed to fetch match {match_id}: {fetch_error}")
                    return match_id, None

        logger.info(f"Fetching {len(match_ids)} matches with max concurrency {max_concurrent}")

        # 并发获取所有比赛数据
        tasks = [fetch_single_match(match_id) for match_id in match_ids]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # 整理结果
        successful_results = {}
        failed_count = 0

        for result in results:
            if isinstance(result, Exception):
                logger.error(f"Task failed with exception: {result}")
                failed_count += 1
                continue

            match_id, match_data = result
            if match_data is not None:
                successful_results[match_id] = match_data
            else:
                failed_count += 1

        success_count = len(successful_results)
        logger.info(
            f"Batch fetch completed: {success_count} successful, "
            f"{failed_count} failed out of {len(match_ids)} total"
        )

        return successful_results

    def _update_request_stats(self, success: bool, response_time_ms: float) -> None:
        """
        更新请求统计信息

        Args:
            success: 请求是否成功
            response_time_ms: 响应时间（毫秒）
        """
        self.stats["total_requests"] += 1
        self.stats["total_response_time_ms"] += response_time_ms

        if success:
            self.stats["successful_requests"] += 1
        else:
            self.stats["failed_requests"] += 1

        # 计算平均响应时间
        if self.stats["total_requests"] > 0:
            self.stats["average_response_time_ms"] = (
                self.stats["total_response_time_ms"] / self.stats["total_requests"]
            )

    def get_stats(self) -> Dict[str, Any]:
        """
        获取统计信息

        Returns:
            Dict[str, Any]: 统计信息副本
        """
        stats_copy = self.stats.copy()

        # 添加成功率计算
        if stats_copy["total_requests"] > 0:
            stats_copy["success_rate"] = (
                stats_copy["successful_requests"] / stats_copy["total_requests"] * 100
            )
        else:
            stats_copy["success_rate"] = 0.0

        return stats_copy

    async def close(self) -> None:
        """关闭HTTP客户端和相关资源"""
        if self._http_client and not self._http_client.is_closed:
            await self._http_client.aclose()
            self._http_client = None
            logger.info("L2Fetcher closed successfully")

    async def __aenter__(self):
        """异步上下文管理器入口"""
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """异步上下文管理器出口"""
        await self.close()


# 便利函数，用于创建L2Fetcher实例
def create_l2_fetcher(
    base_url: str = "https://www.fotmob.com",
    timeout: float = 30.0,
    max_retries: int = 5,
    rate_limiter: Optional[RateLimiter] = None,
) -> L2Fetcher:
    """
    创建L2Fetcher实例的便利函数

    Args:
        base_url: FotMob API基础URL
        timeout: HTTP请求超时时间
        max_retries: 最大重试次数
        rate_limiter: 速率限制器

    Returns:
        L2Fetcher: L2数据获取器实例
    """
    return L2Fetcher(
        base_url=base_url,
        timeout=timeout,
        max_retries=max_retries,
        rate_limiter=rate_limiter,
    )


# 导出
__all__ = [
    "L2Fetcher",
    "L2FetchError",
    "create_l2_fetcher",
]