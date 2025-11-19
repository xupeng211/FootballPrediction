"""性能监控中间件
Performance Monitoring Middleware.
"""

import logging
import time
from collections.abc import Callable

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

logger = logging.getLogger(__name__)


class PerformanceMiddleware(BaseHTTPMiddleware):
    """性能监控中间件."""

    def __init__(self, app, enabled: bool = True):
        """函数文档字符串."""
        # 添加pass语句
        super().__init__(app)
        self.enabled = enabled

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """处理请求并记录性能指标."""
        if not self.enabled:
            return await call_next(request)

        start_time = time.time()

        # 处理请求
        response = await call_next(request)

        # 计算处理时间
        process_time = time.time() - start_time

        # 记录性能指标
        logger.info(
            "Request processed",
            extra={
                "method": request.method,
                "url": str(request.url),
                "status_code": response.status_code,
                "process_time": process_time,
                "user_agent": request.headers.get("user-agent"),
                "remote_addr": request.client.host if request.client else None,
            },
        )

        # 添加响应头
        response.headers["X-Process-Time"] = str(process_time)

        return response


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """请求日志中间件."""

    def __init__(self, app, enabled: bool = True):
        """函数文档字符串."""
        # 添加pass语句
        super().__init__(app)
        self.enabled = enabled

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """记录请求日志."""
        if not self.enabled:
            return await call_next(request)

        # 记录请求开始
        logger.info(
            "Request started",
            extra={
                "method": request.method,
                "url": str(request.url),
                "headers": dict(request.headers),
                "client": request.client.host if request.client else None,
            },
        )

        try:
            response = await call_next(request)

            # 记录请求完成
            logger.info(
                "Request completed",
                extra={
                    "method": request.method,
                    "url": str(request.url),
                    "status_code": response.status_code,
                    "client": request.client.host if request.client else None,
                },
            )

            return response

        except Exception as e:
            # 记录请求错误
            logger.error(
                "Request failed",
                extra={
                    "method": request.method,
                    "url": str(request.url),
                    "error": str(e),
                    "client": request.client.host if request.client else None,
                },
                exc_info=True,
            )
            raise
