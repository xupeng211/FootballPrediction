"""
Async Base Class - 异步基础设施基类
为FootballPrediction项目提供统一的异步操作基础设施

功能:
1. 统一的HTTP客户端管理
2. 异步日志记录
3. 数据库会话管理
4. 错误处理和重试机制
5. 性能监控集成

作者: Async架构负责人
创建时间: 2025-12-06
"""

import asyncio
import logging
import time
from abc import ABC, abstractmethod
from contextlib import asynccontextmanager
from datetime import datetime
from typing import Any, dict, Optional, Union, list
from collections.abc import AsyncGenerator
from dataclasses import dataclass

import httpx
from httpx import AsyncClient, Response
from sqlalchemy.ext.asyncio import AsyncSession

from src.database.async_manager import get_db_session

# from src.performance.monitoring import performance_monitor  # 暂时注释避免依赖问题

# 简化的logger导入
import logging


def get_logger(name):
    return logging.getLogger(name)


@dataclass
class AsyncConfig:
    """异步配置类"""

    http_timeout: float = 30.0
    max_retries: int = 3
    retry_delay: float = 1.0
    max_connections: int = 100
    rate_limit_delay: float = 0.1
    enable_performance_monitoring: bool = True


@dataclass
class RequestStats:
    """请求统计信息"""

    total_requests: int = 0
    successful_requests: int = 0
    failed_requests: int = 0
    total_response_time_ms: float = 0.0
    last_request_time: Optional[datetime] = None

    @property
    def success_rate(self) -> float:
        """成功率"""
        if self.total_requests == 0:
            return 0.0
        return (self.successful_requests / self.total_requests) * 100

    @property
    def average_response_time_ms(self) -> float:
        """平均响应时间"""
        if self.total_requests == 0:
            return 0.0
        return self.total_response_time_ms / self.total_requests


class AsyncBaseCollector(ABC):
    """
    异步采集器基类

    提供统一的HTTP客户端、日志记录、性能监控功能
    所有数据采集器都应继承此基类
    """

    def __init__(
        self, config: Optional[AsyncConfig] = None, name: Optional[str] = None
    ):
        self.config = config or AsyncConfig()
        self.name = name or self.__class__.__name__
        self.logger = get_logger(f"{self.__class__.__module__}.{self.name}")
        self.session: Optional[AsyncClient] = None
        self.stats = RequestStats()
        self._is_initialized = False

    async def __aenter__(self):
        """异步上下文管理器入口"""
        await self._ensure_session()
        self._is_initialized = True
        self.logger.info(f"Async collector '{self.name}' initialized")
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """异步上下文管理器出口"""
        await self._cleanup()
        if exc_type:
            self.logger.error(
                f"Async collector '{self.name}' exited with error: {exc_val}"
            )
        else:
            self.logger.info(f"Async collector '{self.name}' shutdown gracefully")

    async def _ensure_session(self):
        """确保HTTP客户端已初始化"""
        if self.session is None or self.session.is_closed:
            headers = await self._get_headers()
            timeout = httpx.Timeout(self.config.http_timeout)

            self.session = AsyncClient(
                headers=headers,
                timeout=timeout,
                limits=httpx.Limits(max_connections=self.config.max_connections),
                follow_redirects=True,
            )
            self.logger.debug(f"HTTP client initialized for {self.name}")

    async def _cleanup(self):
        """清理资源"""
        if self.session and not self.session.is_closed:
            await self.session.aclose()
            self.session = None

    @abstractmethod
    async def _get_headers(self) -> dict[str, str]:
        """
        获取请求头

        Returns:
            dict[str, str]: HTTP请求头
        """
        return {
            "User-Agent": await self._get_user_agent(),
            "Accept": "application/json",
            "Accept-Encoding": "gzip, deflate, br",
            "Connection": "keep-alive",
            "Upgrade-Insecure-Requests": "1",
        }

    @abstractmethod
    async def _get_user_agent(self) -> str:
        """
        获取User-Agent

        Returns:
            str: User-Agent字符串
        """
        return (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/120.0.0.0 Safari/537.36"
        )

    # 性能监控装饰器 (暂时禁用)
    async def fetch(self, url: str, method: str = "GET", **kwargs) -> Response:
        """
        异步HTTP请求获取数据

        Args:
            url (str): 请求URL
            method (str): HTTP方法，默认GET
            **kwargs: httpx请求参数

        Returns:
            Response: HTTP响应对象

        Raises:
            httpx.HTTPError: HTTP请求错误
        """
        if not self._is_initialized:
            raise RuntimeError(
                "Async collector not initialized. Use 'async with' statement."
            )

        await self._ensure_session()

        # 速率限制
        await self._apply_rate_limit()

        start_time = time.time()
        self.stats.total_requests += 1

        try:
            self.logger.debug(f"Making {method} request to {url}")

            # 执行HTTP请求
            response = await self.session.request(method, url, **kwargs)

            # 记录统计信息
            response_time_ms = (time.time() - start_time) * 1000
            self.stats.total_response_time_ms += response_time_ms
            self.stats.last_request_time = datetime.now()

            if response.status_code == 200:
                self.stats.successful_requests += 1
                self.logger.debug(
                    f"Request successful: {url} "
                    f"({response.status_code}, {response_time_ms:.2f}ms)"
                )
            else:
                self.stats.failed_requests += 1
                self.logger.warning(
                    f"Request returned non-200 status: {url} "
                    f"({response.status_code})"
                )

            return response

        except Exception as e:
            self.stats.failed_requests += 1
            self.logger.error(f"Request failed: {url} - {str(e)}")
            raise

    async def fetch_with_retry(
        self, url: str, method: str = "GET", max_retries: Optional[int] = None, **kwargs
    ) -> Response:
        """
        带重试机制的异步HTTP请求

        Args:
            url (str): 请求URL
            method (str): HTTP方法
            max_retries (Optional[int]): 最大重试次数
            **kwargs: httpx请求参数

        Returns:
            Response: HTTP响应对象
        """
        max_retries = max_retries or self.config.max_retries
        last_exception = None

        for attempt in range(max_retries + 1):
            try:
                if attempt > 0:
                    delay = self.config.retry_delay * (2 ** (attempt - 1))
                    await asyncio.sleep(delay)
                    self.logger.debug(f"Retry attempt {attempt} for {url}")

                response = await self.fetch(url, method, **kwargs)

                # 如果是客户端错误(4xx)，不重试
                if 400 <= response.status_code < 500:
                    return response

                # 如果是成功响应，直接返回
                if response.status_code == 200:
                    return response

            except Exception as e:
                last_exception = e
                if attempt < max_retries:
                    self.logger.warning(
                        f"Request attempt {attempt + 1} failed for {url}: {str(e)}"
                    )
                else:
                    self.logger.error(f"All retry attempts failed for {url}: {str(e)}")

        raise last_exception

    async def _apply_rate_limit(self):
        """应用速率限制"""
        if self.config.rate_limit_delay > 0:
            await asyncio.sleep(self.config.rate_limit_delay)

    async def fetch_json(
        self, url: str, method: str = "GET", **kwargs
    ) -> dict[str, Any]:
        """
        获取JSON响应数据

        Args:
            url (str): 请求URL
            method (str): HTTP方法
            **kwargs: httpx请求参数

        Returns:
            dict[str, Any]: JSON响应数据
        """
        response = await self.fetch_with_retry(url, method, **kwargs)
        return response.json()

    def get_stats(self) -> dict[str, Any]:
        """
        获取采集器统计信息

        Returns:
            dict[str, Any]: 统计信息字典
        """
        return {
            "name": self.name,
            "total_requests": self.stats.total_requests,
            "successful_requests": self.stats.successful_requests,
            "failed_requests": self.stats.failed_requests,
            "success_rate": self.stats.success_rate,
            "average_response_time_ms": self.stats.average_response_time_ms,
            "last_request_time": (
                self.stats.last_request_time.isoformat()
                if self.stats.last_request_time
                else None
            ),
            "is_initialized": self._is_initialized,
        }

    def reset_stats(self):
        """重置统计信息"""
        self.stats = RequestStats()
        self.logger.info(f"Stats reset for {self.name}")


class AsyncBaseService(ABC):
    """
    异步服务基类

    提供数据库会话管理、日志记录等通用服务功能
    """

    def __init__(self, name: Optional[str] = None):
        self.name = name or self.__class__.__name__
        self.logger = get_logger(f"{self.__class__.__module__}.{self.name}")

    @asynccontextmanager
    async def get_db_session(self) -> AsyncGenerator[AsyncSession, None]:
        """
        获取数据库会话上下文管理器

        Returns:
            AsyncGenerator[AsyncSession, None]: 数据库会话
        """
        async with get_db_session() as session:
            try:
                yield session
                await session.commit()
            except Exception:
                await session.rollback()
                raise
            finally:
                await session.close()

    async def execute_query(self, query, params: Optional[dict[str, Any]] = None):
        """
        执行数据库查询

        Args:
            query: SQLAlchemy查询对象
            params: 查询参数

        Returns:
            查询结果
        """
        async with self.get_db_session() as session:
            result = await session.execute(query, params)
            return result

    async def log_performance(
        self,
        operation: str,
        duration_ms: float,
        details: Optional[dict[str, Any]] = None,
    ):
        """
        记录性能日志

        Args:
            operation (str): 操作名称
            duration_ms (float): 执行时间(毫秒)
            details (Optional[dict[str, Any]]): 详细信息
        """
        self.logger.info(f"Performance: {operation} completed in {duration_ms:.2f}ms")
        if details:
            self.logger.debug(f"Operation details: {details}")


class AsyncBatchProcessor(AsyncBaseService):
    """
    异步批处理器基类

    用于批量处理数据采集任务
    """

    def __init__(self, batch_size: int = 10, name: Optional[str] = None):
        super().__init__(name)
        self.batch_size = batch_size

    async def process_batch(
        self, items: list[Any], processor_func: callable, max_concurrent: int = 5
    ) -> list[Any]:
        """
        批量处理数据

        Args:
            items (list[Any]): 待处理数据列表
            processor_func (callable): 处理函数
            max_concurrent (int): 最大并发数

        Returns:
            list[Any]: 处理结果列表
        """
        semaphore = asyncio.Semaphore(max_concurrent)

        async def process_with_semaphore(item):
            async with semaphore:
                return await processor_func(item)

        # 分批处理
        results = []
        for i in range(0, len(items), self.batch_size):
            batch = items[i : i + self.batch_size]
            batch_tasks = [process_with_semaphore(item) for item in batch]
            batch_results = await asyncio.gather(*batch_tasks, return_exceptions=True)

            for result in batch_results:
                if isinstance(result, Exception):
                    self.logger.error(f"Batch processing error: {result}")
                else:
                    results.append(result)

        self.logger.info(
            f"Batch processing completed: {len(results)}/{len(items)} items processed"
        )
        return results


# 便捷函数
async def create_async_collector(
    collector_class: typing.Type, config: Optional[AsyncConfig] = None, **kwargs
) -> AsyncBaseCollector:
    """
    创建异步采集器实例

    Args:
        collector_class (typing.Type): 采集器类
        config (Optional[AsyncConfig]): 异步配置
        **kwargs: 采集器初始化参数

    Returns:
        AsyncBaseCollector: 异步采集器实例
    """
    collector = collector_class(config=config, **kwargs)
    await collector.__aenter__()
    return collector


# 导出的主要类
__all__ = [
    "AsyncConfig",
    "RequestStats",
    "AsyncBaseCollector",
    "AsyncBaseService",
    "AsyncBatchProcessor",
    "create_async_collector",
]
