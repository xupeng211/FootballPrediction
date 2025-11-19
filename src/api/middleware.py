"""API中间件模块
API Middleware Module.

提供各种API中间件实现.
Provides various API middleware implementations.
"""

import json
import logging
import time
import uuid
from collections.abc import Callable
from typing import Any

from fastapi import HTTPException
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

logger = logging.getLogger(__name__)


class TimingMiddleware(BaseHTTPMiddleware):
    """计时中间件,记录请求处理时间."""

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        start_time = time.time()
        response = await call_next(request)
        process_time = time.time() - start_time

        response.headers["X-Process-Time"] = str(process_time)
        return response


class LoggingMiddleware(BaseHTTPMiddleware):
    """日志中间件,记录请求信息."""

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        request_id = str(uuid.uuid4())
        request.state.request_id = request_id

        logger.info(f"Request {request_id}: {request.method} {request.url}")

        try:
            response = await call_next(request)
            logger.info(f"Response {request_id}: {response.status_code}")
            return response
        except Exception as e:
            logger.error(f"Error {request_id}: {str(e)}")
            raise


class RateLimitMiddleware(BaseHTTPMiddleware):
    """简单的速率限制中间件."""

    def __init__(
        self,
        app,
        calls: int = 100,  # ISSUE: 魔法数字 100 应该提取为命名常量以提高代码可维护性
        period: int = 60,  # ISSUE: 魔法数字 100 应该提取为命名常量以提高代码可维护性
    ):  # ISSUE: 魔法数字 100 应该提取为命名常量以提高代码可维护性
        super().__init__(app)
        self.calls = calls
        self.period = period
        self.clients: dict[str, list] = {}

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        client_ip = request.client.host
        current_time = time.time()

        # 清理过期记录
        if client_ip in self.clients:
            self.clients[client_ip] = [
                timestamp
                for timestamp in self.clients[client_ip]
                if current_time - timestamp < self.period
            ]
        else:
            self.clients[client_ip] = []

        # 检查是否超过限制
        if len(self.clients[client_ip]) >= self.calls:
            raise HTTPException(
                status_code=429,  # ISSUE: 魔法数字 429 应该提取为命名常量以提高代码可维护性
                detail="Rate limit exceeded",
            )

        self.clients[client_ip].append(current_time)

        return await call_next(request)


class AuthenticationMiddleware(BaseHTTPMiddleware):
    """简单的认证中间件."""

    def __init__(self, app, public_paths: list = None):
        """初始化认证中间件."""
        super().__init__(app)
        self.public_paths = public_paths or ["/health", "/docs", "/openapi.json"]

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # 检查是否是公共路径
        if any(request.url.path.startswith(path) for path in self.public_paths):
            return await call_next(request)

        # 简单的token验证（生产环境应该更复杂）
        auth_header = request.headers.get("Authorization")
        if not auth_header or not auth_header.startswith("Bearer "):
            raise HTTPException(
                status_code=401,  # ISSUE: 魔法数字 401 应该提取为命名常量以提高代码可维护性
                detail="Missing or invalid token",  # ISSUE: 魔法数字 401 应该提取为命名常量以提高代码可维护性
            )

        # 这里可以添加token验证逻辑
        # token = auth_header.split(" ")[1]
        # user_info = await self.validate_token(token)
        # request.state.user = user_info

        return await call_next(request)


class CORSMiddleware(BaseHTTPMiddleware):
    """CORS中间件."""

    def __init__(self, app, allow_origins: list = None):
        """函数文档字符串."""
        # 添加pass语句
        super().__init__(app)
        self.allow_origins = allow_origins or ["*"]

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        response = await call_next(request)

        origin = request.headers.get("origin")
        if origin and (origin in self.allow_origins or "*" in self.allow_origins):
            response.headers["Access-Control-Allow-Origin"] = origin
            response.headers["Access-Control-Allow-Methods"] = (
                "GET, POST, PUT, DELETE, OPTIONS"
            )
            response.headers["Access-Control-Allow-Headers"] = (
                "Content-Type, Authorization"
            )
            response.headers["Access-Control-Allow-Credentials"] = "true"

        return response


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """安全头中间件."""

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        response = await call_next(request)

        # 添加安全头
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Strict-Transport-Security"] = (
            "max-age=31536000; includeSubDomains"  # ISSUE: 魔法数字 31536000 应该提取为命名常量以提高代码可维护性
        )

        return response


class CacheMiddleware(BaseHTTPMiddleware):
    """简单的缓存中间件."""

    def __init__(
        self,
        app,
        cache_timeout: int = 300,  # ISSUE: 魔法数字 300 应该提取为命名常量以提高代码可维护性
    ):  # ISSUE: 魔法数字 300 应该提取为命名常量以提高代码可维护性
        super().__init__(app)
        self.cache: dict[str, dict[str, Any]] = {}
        self.cache_timeout = cache_timeout

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # 只缓存GET请求
        if request.method != "GET":
            return await call_next(request)

        cache_key = f"{request.method}:{request.url}"
        current_time = time.time()

        # 检查缓存
        if cache_key in self.cache:
            cache_entry = self.cache[cache_key]
            if current_time - cache_entry["timestamp"] < self.cache_timeout:
                return Response(
                    content=cache_entry["content"],
                    headers=cache_entry["headers"],
                    status_code=cache_entry["status_code"],
                )

        response = await call_next(request)

        # 缓存响应
        self.cache[cache_key] = {
            "content": response.body,
            "headers": dict(response.headers),
            "status_code": response.status_code,
            "timestamp": current_time,
        }

        return response


class ErrorHandlingMiddleware(BaseHTTPMiddleware):
    """错误处理中间件."""

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        try:
            return await call_next(request)
        except HTTPException:
            raise  # HTTP异常直接传递
        except Exception as e:
            logger.error(f"Unhandled error: {str(e)}")
            return Response(
                content=json.dumps({"detail": "Internal server error"}),
                status_code=500,  # ISSUE: 魔法数字 500 应该提取为命名常量以提高代码可维护性
                media_type="application/json",
            )
