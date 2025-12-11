"""
Titan007 基础采集器 - 修复版本

简化重试逻辑，专注于核心功能。
"""

import json
import httpx
import asyncio
import time
from typing import Optional, Dict, Any

from src.collectors.rate_limiter import RateLimiter
from src.collectors.user_agent import UserAgentManager
from src.collectors.titan.exceptions import (
    TitanNetworkError,
    TitanParsingError,
    TitanRateLimitError,
)
from src.config.titan_settings import get_titan_settings
from src.collectors.titan.logging_enhancer import get_titan_logger, TitanOperationLogger


class BaseTitanCollector:
    """
    Titan007 基础采集器 - 简化版本

    提供统一的异步HTTP请求接口，集成限流、重试、错误处理等功能。
    """

    def __init__(
        self,
        rate_limiter: Optional[RateLimiter] = None,
        user_agent_manager: Optional[UserAgentManager] = None,
        settings: Optional[object] = None,
    ):
        """
        初始化基础采集器
        """
        # 加载配置
        self.settings = settings or get_titan_settings()
        titan_config = self.settings.titan

        # 从配置获取参数（不再硬编码）
        self.base_url = titan_config.base_url.rstrip("/")
        self.max_retries = titan_config.max_retries
        self.timeout = titan_config.timeout

        # 初始化日志器
        self.logger = get_titan_logger("BaseTitanCollector")
        self.op_logger = TitanOperationLogger("BaseTitanCollector")

        # 初始化限流器（使用配置参数）
        self.rate_limiter = rate_limiter or RateLimiter(
            rate=titan_config.rate_limit_qps,
            burst=titan_config.rate_limit_burst,
            max_wait_time=titan_config.rate_limit_max_wait,
        )

        # 初始化UA管理器
        self.user_agent_manager = user_agent_manager or UserAgentManager()

        # 创建HTTP客户端（使用配置的连接池参数）
        self.http_client = httpx.AsyncClient(
            timeout=httpx.Timeout(self.timeout),
            limits=httpx.Limits(
                max_connections=titan_config.max_connections,
                max_keepalive_connections=titan_config.max_keepalive_connections,
            ),
        )

        # 记录初始化信息
        self.logger.info(
            "BaseTitanCollector 初始化完成",
            extra={
                "base_url": self.base_url,
                "max_retries": self.max_retries,
                "timeout": self.timeout,
                "max_connections": titan_config.max_connections,
                "rate_limit_qps": titan_config.rate_limit_qps,
            },
        )

    async def _fetch_json(
        self,
        endpoint: str,
        params: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        获取 JSON 数据（带限流、重试、错误处理）

        简化版本：移除复杂的装饰器，直接在方法内实现重试逻辑。
        """
        params = params or {}
        url = f"{self.base_url}{endpoint}"

        # 提取业务上下文信息（用于日志）
        match_id = params.get("matchid")
        company_id = params.get("companyid")

        # 记录API请求开始
        self.op_logger.log_api_request(
            endpoint, params, match_id=match_id, company_id=company_id
        )

        # 简化的重试逻辑
        for attempt in range(self.max_retries):
            try:
                # Step 1: 限流控制
                start_time = time.time()
                await self.rate_limiter.acquire("titan_odds")

                # Step 2: 设置请求头
                headers = {
                    "User-Agent": self.user_agent_manager.get_random_user_agent(),
                    "Accept": "application/json, text/plain, */*",
                    "Accept-Language": "en-US,en;q=0.9",
                    "Accept-Encoding": "gzip, deflate, br",
                    "Connection": "keep-alive",
                }

                # Step 3: 发送异步HTTP请求
                response = await self.http_client.get(
                    url,
                    params=params,
                    headers=headers,
                    follow_redirects=True,
                )

                # Step 4: 响应状态码验证
                if response.status_code == 403:
                    raise TitanRateLimitError(
                        message="403 Forbidden - Rate limit exceeded",
                        status_code=403,
                        endpoint=endpoint,
                        params=params,
                    )
                elif response.status_code == 404:
                    raise TitanNetworkError(
                        message="404 Not Found",
                        status_code=404,
                        endpoint=endpoint,
                        params=params,
                    )
                elif response.status_code >= 400:
                    raise TitanNetworkError(
                        message=f"HTTP {response.status_code}: {response.text}",
                        status_code=response.status_code,
                        endpoint=endpoint,
                        params=params,
                    )

                # Step 5: 读取响应内容
                raw_content = response.text
                response_size = len(raw_content)

                # Step 6: 清理响应内容
                cleaned_content = self._clean_response_content(raw_content)

                # Step 7: 解析 JSON
                try:
                    data = json.loads(cleaned_content)

                    # 记录成功响应
                    end_time = time.time()
                    duration = (end_time - start_time) * 1000  # 转换为毫秒

                    self.op_logger.log_api_success(
                        endpoint,
                        response_size,
                        match_id=match_id,
                        company_id=company_id,
                        duration_ms=duration,
                        status_code=response.status_code,
                    )

                    return data
                except json.JSONDecodeError as e:
                    # JSON 解析失败
                    self.logger.error(
                        "JSON解析失败",
                        extra={
                            "endpoint": endpoint,
                            "match_id": match_id,
                            "company_id": company_id,
                            "error_type": "JSONDecodeError",
                            "error_message": str(e),
                            "response_size": response_size,
                            "raw_content_preview": raw_content[:200],
                        },
                    )
                    raise TitanParsingError(
                        message=f"JSON parsing failed: {str(e)}",
                        raw_content=raw_content[:500],
                        endpoint=endpoint,
                        params=params,
                    )

            except (httpx.TimeoutException, httpx.ConnectError, httpx.HTTPError) as e:
                # 网络错误处理
                if attempt < self.max_retries - 1:
                    wait_time = min(2**attempt, 10)  # 指数退避
                    self.logger.warning(
                        f"请求失败，{wait_time}秒后重试 (尝试 {attempt + 1}/{self.max_retries})",
                        extra={
                            "endpoint": endpoint,
                            "match_id": match_id,
                            "company_id": company_id,
                            "attempt": attempt + 1,
                            "error_type": type(e).__name__,
                            "error_message": str(e),
                            "wait_time": wait_time,
                        },
                    )
                    await asyncio.sleep(wait_time)
                    continue
                else:
                    # 最后一次重试失败
                    self.logger.error(
                        "所有重试尝试均失败",
                        extra={
                            "endpoint": endpoint,
                            "match_id": match_id,
                            "company_id": company_id,
                            "max_retries": self.max_retries,
                            "error_type": type(e).__name__,
                            "error_message": str(e),
                        },
                    )
                    raise TitanNetworkError(
                        message=f"Request failed after {self.max_retries} retries: {str(e)}",
                        status_code=getattr(e, "status_code", None),
                        endpoint=endpoint,
                        params=params,
                    ) from e

            except (TitanNetworkError, TitanRateLimitError) as e:
                # Titan 特定错误处理
                if attempt < self.max_retries - 1:
                    wait_time = min(2**attempt, 10)
                    self.logger.warning(
                        f"Titan错误，{wait_time}秒后重试",
                        extra={
                            "endpoint": endpoint,
                            "match_id": match_id,
                            "company_id": company_id,
                            "attempt": attempt + 1,
                            "error_type": type(e).__name__,
                            "error_message": str(e),
                            "wait_time": wait_time,
                        },
                    )
                    await asyncio.sleep(wait_time)
                    continue
                else:
                    raise

    def _clean_response_content(self, content: str) -> str:
        """
        清理响应内容

        处理可能的 JSONP 包装器和 BOM 头。

        Args:
            content: 原始响应内容

        Returns:
            str: 清理后的 JSON 内容
        """
        if not content:
            return ""

        # 移除 BOM 头
        if content.startswith("\ufeff"):
            content = content[1:]

        # 移除可能的 JSONP 包装器
        # 如: jsonp_callback({"key": "value"}) -> {"key": "value"}
        if content.startswith("var ") or content.startswith("jsonp_callback"):
            start = content.find("{")
            end = content.rfind("}") + 1
            if start != -1 and end != 0:
                content = content[start:end]

        return content.strip()

    async def close(self):
        """关闭HTTP客户端"""
        if hasattr(self, "http_client") and self.http_client:
            await self.http_client.aclose()

    async def __aenter__(self):
        """异步上下文管理器入口"""
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """异步上下文管理器出口"""
        await self.close()
