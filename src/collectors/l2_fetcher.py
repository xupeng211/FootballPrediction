#!/usr/bin/env python3
"""
L2数据获取器 - 生产版本
L2 Data Fetcher - Production Release

用于从FotMob API获取详细的比赛数据，支持：
- 异步HTTP请求处理
- HTTP压缩和编码处理
- 请求重试和限流
- 结构化数据提取
- 多种数据格式支持

作者: L2开发团队
创建时间: 2025-12-10
版本: 1.0.0 (Production Release)
"""

import asyncio
import logging
from typing import Any, Dict, List, Optional, Set, Tuple, Union
from datetime import datetime
from dataclasses import dataclass, field

import httpx
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

from .rate_limiter import RateLimiter


@dataclass
class L2FetchError(Exception):
    """L2数据获取错误"""
    status_code: int
    message: str
    match_id: Optional[str] = None

    def __post_init__(self):
        super().__init__(self.message)


@dataclass
class L2FetchConfig:
    """L2数据获取配置"""
    base_url: str = "https://www.fotmob.com/api"
    timeout: float = 30.0
    max_retries: int = 3
    retry_delay_base: float = 1.0
    max_retry_delay: float = 60.0

    # 请求头配置
    default_headers: Dict[str, str] = field(default_factory=lambda: {
        "Accept": "application/json, text/plain, */*",
        "Accept-Language": "en-US,en;q=0.9",
        "Cache-Control": "no-cache",
        "Pragma": "no-cache",
        "Sec-Ch-Ua": '"Google Chrome";v="131", "Chromium";v="131", "Not_A Brand";v="24"',
        "Sec-Ch-Ua-Mobile": "?0",
        "Sec-Ch-Ua-Platform": '"Linux"',
        "Sec-Fetch-Dest": "empty",
        "Sec-Fetch-Mode": "cors",
        "Sec-Fetch-Site": "same-origin",
        "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"
    })

    # 压缩支持
    enable_compression: bool = True
    compression_fallback: bool = True


class L2Fetcher:
    """
    L2数据获取器 - 生产版本

    提供高性能、可靠的FotMob API数据获取服务，支持并发请求、
    压缩处理、重试机制和错误恢复等功能。
    """

    def __init__(
        self,
        timeout: float = 30.0,
        max_retries: int = 3,
        rate_limiter: Optional[RateLimiter] = None,
        config: Optional[L2FetchConfig] = None
    ):
        """
        初始化L2数据获取器

        Args:
            timeout: 请求超时时间
            max_retries: 最大重试次数
            rate_limiter: 限流器实例
            config: 详细配置，如果为None则使用默认配置
        """
        self.config = config or L2FetchConfig(
            timeout=timeout,
            max_retries=max_retries
        )
        self.rate_limiter = rate_limiter
        self.logger = logging.getLogger(__name__)

        # HTTP客户端配置
        self._client: Optional[httpx.AsyncClient] = None
        self._headers = self.config.default_headers.copy()

        # 统计信息
        self._stats = {
            'total_requests': 0,
            'successful_requests': 0,
            'failed_requests': 0,
            'retry_count': 0,
            'compression_hits': 0,
            'compression_fallbacks': 0
        }

        # 支持的端点映射
        self._endpoint_map = {
            'match_details': '/matchDetails',
            'match_lineup': '/matchLineup',
            'match_stats': '/matchStats',
            'match_shots': '/matchShots'
        }

    async def initialize(self) -> None:
        """
        异步初始化HTTP客户端和其他资源

        注意：这个方法已弃用，L2Fetcher现在使用延迟初始化
        """
        self.logger.warning(
            "L2Fetcher.initialize() is deprecated. "
            "The fetcher now uses lazy initialization."
        )

    async def _ensure_client(self) -> httpx.AsyncClient:
        """确保HTTP客户端已初始化"""
        if self._client is None or self._client.is_closed:
            timeout = httpx.Timeout(self.config.timeout, connect=10.0)
            limits = httpx.Limits(max_keepalive_connections=20, max_connections=100)

            self._client = httpx.AsyncClient(
                timeout=timeout,
                limits=limits,
                headers=self._headers,
                follow_redirects=True
            )

            self.logger.debug("HTTP client initialized with timeout=%.1fs", self.config.timeout)

        return self._client

    def _get_endpoint_url(self, endpoint_type: str, match_id: str) -> str:
        """
        获取端点URL

        Args:
            endpoint_type: 端点类型
            match_id: 比赛ID

        Returns:
            str: 完整的URL
        """
        endpoint = self._endpoint_map.get(endpoint_type)
        if not endpoint:
            raise ValueError(f"Unknown endpoint type: {endpoint_type}")

        return f"{self.config.base_url}{endpoint}?matchId={match_id}"

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=4, max=10),
        retry=retry_if_exception_type((httpx.RequestError, httpx.TimeoutException))
    )
    async def _make_request(
        self,
        url: str,
        method: str = "GET",
        headers: Optional[Dict[str, str]] = None,
        params: Optional[Dict[str, Any]] = None
    ) -> httpx.Response:
        """
        发起HTTP请求

        Args:
            url: 请求URL
            method: HTTP方法
            headers: 请求头
            params: 查询参数

        Returns:
            httpx.Response: HTTP响应对象

        Raises:
            L2FetchError: 请求失败
        """
        client = await self._ensure_client()

        # 合并请求头
        request_headers = self._headers.copy()
        if headers:
            request_headers.update(headers)

        # 限流处理
        if self.rate_limiter:
            async with self.rate_limiter.acquire("fotmob.com"):
                return await self._execute_request_with_stats(
                    client, method, url, request_headers, params
                )
        else:
            return await self._execute_request_with_stats(
                client, method, url, request_headers, params
            )

    async def _execute_request_with_stats(
        self,
        client: httpx.AsyncClient,
        method: str,
        url: str,
        headers: Dict[str, str],
        params: Optional[Dict[str, Any]]
    ) -> httpx.Response:
        """执行HTTP请求并更新统计信息"""
        self._stats['total_requests'] += 1

        try:
            self.logger.debug("Making %s request to %s", method, url)

            response = await client.request(
                method=method,
                url=url,
                headers=headers,
                params=params
            )

            self._stats['successful_requests'] += 1
            self.logger.debug(
                "Request completed: status=%d, size=%d bytes",
                response.status_code,
                len(response.content)
            )

            return response

        except httpx.HTTPStatusError as e:
            self._stats['failed_requests'] += 1
            error_msg = f"HTTP {e.response.status_code}: {e.response.text[:200]}"

            raise L2FetchError(
                status_code=e.response.status_code,
                message=error_msg
            )

        except httpx.RequestError as e:
            self._stats['failed_requests'] += 1
            raise L2FetchError(
                status_code=-1,
                message=f"Request error: {str(e)}"
            )

        except Exception as e:
            self._stats['failed_requests'] += 1
            raise L2FetchError(
                status_code=-2,
                message=f"Unexpected error: {str(e)}"
            )

    async def _fetch_with_compression(self, url: str) -> Dict[str, Any]:
        """
        使用压缩获取数据

        Args:
            url: 请求URL

        Returns:
            Dict[str, Any]: 解析后的JSON数据

        Raises:
            L2FetchError: 请求失败
        """
        # 添加压缩请求头
        headers = {
            "Accept-Encoding": "gzip, deflate, br"
        }

        response = await self._make_request(url, headers=headers)

        # 检查响应是否被压缩
        content_encoding = response.headers.get("content-encoding", "").lower()

        if content_encoding:
            self._stats['compression_hits'] += 1
            self.logger.debug("Response compressed with: %s", content_encoding)
        else:
            self.logger.debug("Response not compressed")

        # 检查响应内容
        if response.content.startswith(b'\x1f\x8b'):  # gzip magic number
            self.logger.debug("Detected gzip compression")
        elif response.content.startswith(b'BZ'):  # bzip2 magic number
            self.logger.debug("Detected bzip2 compression")
        elif response.content.startswith(b'\x28\xb5\x2f\xfd'):  # zstd magic number
            self.logger.debug("Detected zstd compression")

        try:
            data = response.json()
            self.logger.debug(
                "Successfully parsed compressed JSON response (%d bytes)",
                len(response.content)
            )
            return data

        except Exception as e:
            self.logger.error("Failed to parse compressed JSON response: %s", e)
            raise L2FetchError(
                status_code=-3,
                message=f"JSON parsing error: {str(e)}"
            )

    async def _fetch_without_compression(self, url: str) -> Dict[str, Any]:
        """
        不使用压缩获取数据（回退选项）

        Args:
            url: 请求URL

        Returns:
            Dict[str, Any]: 解析后的JSON数据

        Raises:
            L2FetchError: 请求失败
        """
        self._stats['compression_fallbacks'] += 1
        self.logger.info("Using compression fallback for URL: %s", url)

        # 明确禁用压缩
        headers = {
            "Accept-Encoding": "identity"
        }

        response = await self._make_request(url, headers=headers)

        try:
            data = response.json()
            self.logger.debug(
                "Successfully parsed uncompressed JSON response (%d bytes)",
                len(response.content)
            )
            return data

        except Exception as e:
            self.logger.error("Failed to parse uncompressed JSON response: %s", e)
            raise L2FetchError(
                status_code=-4,
                message=f"JSON parsing error (uncompressed): {str(e)}"
            )

    async def fetch_match_details(self, match_id: str) -> Optional[Dict[str, Any]]:
        """
        获取比赛详情数据

        Args:
            match_id: 比赛ID

        Returns:
            Optional[Dict[str, Any]]: 比赛详情数据，获取失败返回None
        """
        url = self._get_endpoint_url('match_details', match_id)

        try:
            # 首先尝试使用压缩
            if self.config.enable_compression:
                try:
                    return await self._fetch_with_compression(url)
                except L2FetchError as e:
                    if self.config.compression_fallback and e.status_code == -3:
                        self.logger.warning(
                            "Compression failed for match %s, trying without compression",
                            match_id
                        )
                        return await self._fetch_without_compression(url)
                    else:
                        raise

            # 如果禁用压缩，直接使用无压缩方式
            else:
                return await self._fetch_without_compression(url)

        except L2FetchError as e:
            self.logger.error(
                "Failed to fetch match details for %s (status=%s): %s",
                match_id, e.status_code, e.message
            )

            # 对于某些错误状态码，返回None而不是抛出异常
            if e.status_code in [404, 401, 403]:
                self.logger.debug(
                    "Match %s not available (status=%s), returning None",
                    match_id, e.status_code
                )
                return None

            raise
        except Exception as e:
            self.logger.error("Unexpected error fetching match details for %s: %s", match_id, e)
            raise L2FetchError(
                status_code=-5,
                message=f"Unexpected error: {str(e)}",
                match_id=match_id
            )

    async def fetch_multiple_matches(
        self,
        match_ids: List[str],
        max_concurrent: int = 10
    ) -> Dict[str, Optional[Dict[str, Any]]]:
        """
        批量获取多个比赛的详情数据

        Args:
            match_ids: 比赛ID列表
            max_concurrent: 最大并发数

        Returns:
            Dict[str, Optional[Dict[str, Any]]]: 比赛ID到数据的映射
        """
        self.logger.info(
            "Fetching details for %d matches with max_concurrent=%d",
            len(match_ids), max_concurrent
        )

        semaphore = asyncio.Semaphore(max_concurrent)
        results = {}

        async def fetch_single(match_id: str) -> Tuple[str, Optional[Dict[str, Any]]]:
            async with semaphore:
                try:
                    data = await self.fetch_match_details(match_id)
                    return match_id, data
                except Exception as e:
                    self.logger.error("Error fetching match %s: %s", match_id, e)
                    return match_id, None

        tasks = [fetch_single(match_id) for match_id in match_ids]
        completed_tasks = await asyncio.gather(*tasks, return_exceptions=True)

        for task in completed_tasks:
            if isinstance(task, Exception):
                self.logger.error("Task failed with exception: %s", task)
                continue

            match_id, data = task
            results[match_id] = data

        successful_count = sum(1 for data in results.values() if data is not None)
        self.logger.info(
            "Batch fetch completed: %d/%d matches successful",
            successful_count, len(match_ids)
        )

        return results

    async def close(self) -> None:
        """关闭HTTP客户端和清理资源"""
        if self._client and not self._client.is_closed:
            await self._client.aclose()
            self.logger.debug("HTTP client closed")

    def get_stats(self) -> Dict[str, Any]:
        """获取统计信息"""
        success_rate = 0.0
        if self._stats['total_requests'] > 0:
            success_rate = (self._stats['successful_requests'] / self._stats['total_requests']) * 100

        return {
            **self._stats,
            'success_rate': round(success_rate, 2),
            'compression_hit_rate': round(
                (self._stats['compression_hits'] / max(self._stats['total_requests'], 1)) * 100, 2
            )
        }

    async def __aenter__(self):
        """异步上下文管理器入口"""
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """异步上下文管理器出口"""
        await self.close()