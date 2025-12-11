"""
Titan007 基础采集器 - 生产就绪版本

提供异步HTTP请求、限流、重试、错误处理等基础设施。
所有具体采集器（欧赔、亚盘、大小球）都继承此类。

生产环境特性：
- 基于环境变量的配置管理
- 结构化日志记录
- 可调优的重试和限流策略
- 完整的业务上下文日志
"""

import json
import httpx
from typing import Optional, Dict, Any
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

from src.collectors.http_client_factory import HttpClientFactory
from src.collectors.rate_limiter import RateLimiter
from src.collectors.user_agent import UserAgentManager
from src.collectors.titan.exceptions import (
    TitanError,
    TitanNetworkError,
    TitanParsingError,
    TitanScrapingError,
    TitanRateLimitError,
)
from src.config.titan_settings import get_titan_settings
from src.collectors.titan.logging_enhancer import get_titan_logger, TitanOperationLogger


class BaseTitanCollector:
    """
    Titan007 基础采集器 - 生产就绪版本

    提供统一的异步HTTP请求接口，集成限流、重试、错误处理等功能。
    所有具体业务采集器（欧赔、亚盘、大小球）都应继承此类。

    生产环境特性：
    - 基于环境变量的配置管理
    - 结构化日志记录
    - 可调优的连接池和重试策略
    - 完整的业务上下文日志

    Example:
        >>> collector = BaseTitanCollector()
        >>> data = await collector._fetch_json("/euro", {"matchid": "2971465"})
    """

    def __init__(
        self,
        rate_limiter: Optional[RateLimiter] = None,
        user_agent_manager: Optional[UserAgentManager] = None,
        settings: Optional[object] = None,
    ):
        """
        初始化基础采集器

        Args:
            rate_limiter: 限流器实例（可选）
            user_agent_manager: UA管理器（可选）
            settings: 配置对象（可选，默认从环境变量加载）

        Example:
            >>> rate_limiter = RateLimiter(rate=2.0, interval=1.0)  # 2 QPS
            >>> collector = BaseTitanCollector(rate_limiter=rate_limiter)
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
            max_wait_time=titan_config.rate_limit_max_wait
        )

        # 初始化UA管理器
        self.user_agent_manager = user_agent_manager or UserAgentManager()

        # 创建HTTP客户端（使用配置的连接池参数）
        self.http_client = httpx.AsyncClient(
            timeout=httpx.Timeout(self.timeout),
            limits=httpx.Limits(
                max_connections=titan_config.max_connections,
                max_keepalive_connections=titan_config.max_keepalive_connections
            ),
        )

        # 记录初始化信息
        self.logger.info("BaseTitanCollector 初始化完成", extra={
            'base_url': self.base_url,
            'max_retries': self.max_retries,
            'timeout': self.timeout,
            'max_connections': titan_config.max_connections,
            'rate_limit_qps': titan_config.rate_limit_qps
        })

    def get_retry_decorator(self):
        """获取重试装饰器（基于配置）"""
        titan_config = self.settings.titan
        return retry(
            stop=stop_after_attempt(self.max_retries),
            wait=wait_exponential(
                multiplier=titan_config.retry_multiplier,
                min=titan_config.retry_min_wait,
                max=titan_config.retry_max_wait
            ),
            retry=retry_if_exception_type((
                TitanNetworkError,
                TitanRateLimitError,
            )),
            reraise=True,
        )
    def get_retry_decorator(self):
        """获取重试装饰器（基于配置）"""
        titan_config = self.settings.titan
        return retry(
            stop=stop_after_attempt(self.max_retries),
            wait=wait_exponential(
                multiplier=titan_config.retry_multiplier,
                min=titan_config.retry_min_wait,
                max=titan_config.retry_max_wait
            ),
            retry=retry_if_exception_type((
                TitanNetworkError,
                TitanRateLimitError,
            )),
            reraise=True,
        )

    # 获取重试装饰器并应用
    def _fetch_json(self, endpoint: str, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        self,
        endpoint: str,
        params: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        获取 JSON 数据（带限流、重试、错误处理）

        核心方法：所有具体采集器都通过此方法请求数据。

        流程：
        1. 限流控制（rate_limiter.acquire）
        2. 设置请求头（User-Agent）
        3. 发送异步HTTP请求
        4. 响应验证（状态码、内容类型）
        5. JSON解析（清理JSONP/BOM）
        6. 错误处理（网络、解析、反爬）

        Args:
            endpoint: API端点（如 "/euro", "/handicap"）
            params: 请求参数（如 {"matchid": "2971465", "companyid": 8}）

        Returns:
            Dict[str, Any]: 解析后的 JSON 数据

        Raises:
            TitanScrapingError: 403 Forbidden（反爬拦截）
            TitanNetworkError: 网络错误、超时、5xx错误（超过重试次数）
            TitanRateLimitError: 429 Too Many Requests
            TitanParsingError: JSON解析失败（JSONP格式、BOM头等）
            TitanAuthenticationError: 401 Unauthorized

        Example:
            >>> data = await collector._fetch_json("/euro", {"matchid": "2971465"})
            >>> print(f"Home odds: {data['data'][0]['homeodds']}")

        Notes:
            - 自动处理 JSONP 包装器（callback(...);）
            - 自动清理 BOM 头（\ufeff）
            - 指数退避重试：1s, 2s, 4s
            - 限流器 key: "titan_odds"
        """
        params = params or {}
        url = f"{self.base_url}{endpoint}"

        # 提取业务上下文信息（用于日志）
        match_id = params.get("matchid")
        company_id = params.get("companyid")

        # 记录API请求开始
        self.op_logger.log_api_request(endpoint, params, match_id=match_id, company_id=company_id)

        try:
            # Step 1: 限流控制
            # 每次请求前必须获取限流令牌
            start_time = httpx._utils.current_time()
            await self.rate_limiter.acquire("titan_odds")

            # Step 2: 设置请求头
            # 使用动态 User-Agent 避免被识别为爬虫
            headers = {
                "User-Agent": self.user_agent_manager.get_random_user_agent(),
                "Accept": "application/json, text/plain, */*",
                "Accept-Language": "en-US,en;q=0.9",
                "Accept-Encoding": "gzip, deflate, br",
                "Connection": "keep-alive",
            }

            # Step 3: 发送异步HTTP请求
            # 注意：不使用 async with，避免重试时客户端已关闭
            response = await self.http_client.get(
                url,
                params=params,
                headers=headers,
                follow_redirects=True,
            )

            # Step 4: 响应状态码验证
            if response.status_code == 403:
                # 403 Forbidden: 反爬拦截
                raise TitanScrapingError(
                    message=f"Access denied (403 Forbidden). Possibly blocked by anti-scraping measures.",
                    status_code=403,
                    endpoint=endpoint,
                    params=params,
                )

            elif response.status_code == 429:
                # 429 Too Many Requests: 触发限流
                retry_after = response.headers.get("Retry-After")
                retry_after = int(retry_after) if retry_after else None

                # 抛出限流错误（会触发重试）
                raise TitanRateLimitError(
                    message=f"Rate limit exceeded (429). Retry after: {retry_after}s" if retry_after else "Rate limit exceeded (429)",
                    retry_after=retry_after,
                    endpoint=endpoint,
                    params=params,
                )
            elif response.status_code >= 500:
                # 5xx 服务器错误（会触发重试）
                raise TitanNetworkError(
                    message=f"Server error ({response.status_code}): {response.text[:200]}",
                    status_code=response.status_code,
                    endpoint=endpoint,
                    params=params,
                )
            elif response.status_code >= 400:
                # 4xx 客户端错误（不重试）
                raise TitanNetworkError(
                    message=f"Client error ({response.status_code}): {response.text[:200]}",
                    status_code=response.status_code,
                    endpoint=endpoint,
                    params=params,
                )

            # Step 5: 读取响应内容
            raw_content = response.text
            response_size = len(raw_content)

            # Step 6: 清理响应内容
            # 处理可能的 JSONP 包装器和 BOM 头
            cleaned_content = self._clean_response_content(raw_content)

            # Step 7: 解析 JSON
            try:
                data = json.loads(cleaned_content)

                # 记录成功响应
                end_time = httpx._utils.current_time()
                duration = (end_time - start_time) * 1000  # 转换为毫秒

                self.op_logger.log_api_success(endpoint, response_size,
                    match_id=match_id, company_id=company_id,
                    duration_ms=duration, status_code=response.status_code)

                return data
            except json.JSONDecodeError as e:
                # JSON 解析失败
                self.logger.error("JSON解析失败", extra={
                    'endpoint': endpoint,
                    'match_id': match_id,
                    'company_id': company_id,
                    'error_type': 'JSONDecodeError',
                    'error_message': str(e),
                    'response_size': response_size,
                    'raw_content_preview': raw_content[:200]
                })
                raise TitanParsingError(
                    message=f"JSON parsing failed: {str(e)}",
                    raw_content=raw_content[:500],  # 保留前500字符用于调试
                    endpoint=endpoint,
                    params=params,
                )

        except httpx.TimeoutException as e:
            # 请求超时（会触发重试）
            self.logger.warning("请求超时", extra={
                'endpoint': endpoint,
                'match_id': match_id,
                'company_id': company_id,
                'error_type': 'TimeoutException',
                'timeout': self.timeout,
                'error_message': str(e)
            })
            raise TitanNetworkError(
                message=f"Request timeout after {self.timeout}s: {str(e)}",
                status_code=None,
                endpoint=endpoint,
                params=params,
            ) from e

        except httpx.ConnectError as e:
            # 连接错误（会触发重试）
            self.logger.warning("连接错误", extra={
                'endpoint': endpoint,
                'match_id': match_id,
                'company_id': company_id,
                'error_type': 'ConnectError',
                'error_message': str(e)
            })
            raise TitanNetworkError(
                message=f"Connection error: {str(e)}",
                status_code=None,
                endpoint=endpoint,
                params=params,
            ) from e

        except httpx.HTTPError as e:
            # 其他 HTTP 错误
            self.logger.error("HTTP请求错误", extra={
                'endpoint': endpoint,
                'match_id': match_id,
                'company_id': company_id,
                'error_type': 'HTTPError',
                'error_message': str(e)
            })
            raise TitanNetworkError(
                message=f"HTTP error: {str(e)}",
                status_code=None,
                endpoint=endpoint,
                params=params,
            ) from e

    def _clean_response_content(self, content: str) -> str:
        """
        清理响应内容

        处理：
        - JSONP 包装器（callback(...);）
        - BOM 头（\ufeff）
        - 前后空白字符

        Args:
            content: 原始响应内容

        Returns:
            str: 清理后的内容

        Example:
            >>> raw = 'callback({"data": []});'
            >>> cleaned = collector._clean_response_content(raw)
            >>> print(cleaned)  # '{"data": []}'
        """
        if not content:
            return ""

        # 移除 BOM 头（UTF-8 BOM: \ufeff）
        content = content.lstrip('\ufeff')

        # 移除前后空白
        content = content.strip()

        # 处理 JSONP 包装器
        # 格式：callbackName({json_data});
        if content.startswith('callback(') and content.endswith(');'):
            # 提取括号内的 JSON 数据
            content = content[9:-2]  # 移除 "callback(" 和 ");"
        elif content.startswith('(') and content.endswith(');'):
            # 格式：({json_data});
            content = content[1:-2]

        return content

    async def __aenter__(self):
        """异步上下文管理器入口"""
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """异步上下文管理器出口（自动关闭 HTTP 客户端）"""
        await self.close()

    async def close(self):
        """关闭 HTTP 客户端"""
        if self.http_client and not self.http_client.is_closed:
            await self.http_client.aclose()

    def __repr__(self) -> str:
        """字符串表示"""
        return (
            f"BaseTitanCollector("
            f"base_url='{self.base_url}', "
            f"max_retries={self.max_retries}, "
            f"timeout={self.timeout}s"
            f")"
        )
