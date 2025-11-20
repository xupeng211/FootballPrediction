# 数据收集器基础模块
import logging
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, Optional

import httpx
from tenacity import retry, stop_after_attempt, wait_exponential

logger = logging.getLogger(__name__)


@dataclass
class CollectionResult:
    """数据收集结果."""

    success: bool
    data: Any = None
    error: str | None = None
    metadata: dict[str, Any] | None = None
    timestamp: datetime | None = None

    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now()


class BaseCollector:
    """数据收集器基类."""

    def __init__(self, config: dict[str, Any] | None = None):
        self.config = config or {}
        self.timeout = self.config.get("timeout", 30.0)
        self.max_retries = self.config.get("max_retries", 3)
        self.logger = logger

    async def collect(self, *args, **kwargs) -> CollectionResult:
        """收集数据的抽象方法."""
        raise NotImplementedError("Subclasses must implement collect method")

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=4, max=10),
        reraise=True
    )
    async def _make_request(
        self,
        url: str,
        method: str = "GET",
        headers: Optional[Dict[str, str]] = None,
        params: Optional[Dict[str, Any]] = None,
        data: Optional[Dict[str, Any]] = None,
        timeout: Optional[float] = None,
    ) -> Dict[str, Any]:
        """
        发送HTTP请求的核心方法.

        Args:
            url: 请求URL
            method: HTTP方法 (GET, POST, PUT, DELETE)
            headers: 请求头
            params: URL参数
            data: 请求数据
            timeout: 超时时间

        Returns:
            Dict[str, Any]: 响应JSON数据

        Raises:
            httpx.RequestError: 请求错误
            httpx.TimeoutException: 超时错误
            httpx.HTTPStatusError: HTTP状态错误
            ValueError: JSON解析错误
        """
        if timeout is None:
            timeout = self.timeout

        async with httpx.AsyncClient(timeout=timeout) as client:
            try:
                self.logger.debug(f"Making {method} request to {url}")

                response = await client.request(
                    method=method,
                    url=url,
                    headers=headers,
                    params=params,
                    json=data
                )

                # 检查HTTP状态码
                response.raise_for_status()

                # 解析JSON响应
                try:
                    result = response.json()
                    self.logger.debug(f"Successfully received response from {url}")
                    return result

                except ValueError as e:
                    self.logger.error(f"Failed to parse JSON response from {url}: {e}")
                    raise ValueError(f"Invalid JSON response from {url}: {e}")

            except httpx.HTTPStatusError as e:
                self.logger.error(f"HTTP {e.response.status_code} error for {url}: {e.response.text}")
                raise httpx.HTTPStatusError(
                    f"HTTP {e.response.status_code} error for {url}",
                    request=e.request,
                    response=e.response
                )

            except httpx.TimeoutException as e:
                self.logger.error(f"Request timeout for {url}: {e}")
                raise httpx.TimeoutException(f"Request timeout for {url}: {e}")

            except httpx.RequestError as e:
                self.logger.error(f"Request error for {url}: {e}")
                raise httpx.RequestError(f"Request error for {url}: {e}")

    def create_success_result(
        self, data: Any, metadata: dict[str, Any] | None = None
    ) -> CollectionResult:
        """创建成功的结果."""
        return CollectionResult(success=True, data=data, metadata=metadata)

    def create_error_result(
        self, error: str, metadata: dict[str, Any] | None = None
    ) -> CollectionResult:
        """创建错误的结果."""
        return CollectionResult(success=False, error=error, metadata=metadata)


def example():
    return None


EXAMPLE = "value"
