"""
FastAPI性能中间件模板
用于足球预测API的性能监控和优化
"""

import time
import uuid
import asyncio
from typing import Callable
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import StreamingResponse
import logging
import json

logger = logging.getLogger(__name__)

class PerformanceMonitoringMiddleware(BaseHTTPMiddleware):
    """性能监控中间件"""

    def __init__(self, app, enabled: bool = True):
        super().__init__(app)
        self.enabled = enabled
        self.request_counts = {}
        self.response_times = {}

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """处理请求并记录性能指标"""

        if not self.enabled:
            return await call_next(request)

        # 生成请求ID
        request_id = str(uuid.uuid4())
        request.state.request_id = request_id
        request.state.start_time = time.time()

        # 记录请求开始
        logger.info(
            f"Request started: {request.method} {request.url.path}",
            extra={
                "request_id": request_id,
                "method": request.method,
                "path": request.url.path,
                "query_params": str(request.query_params),
                "client_ip": request.client.host if request.client else None
            }
        )

        try:
            # 处理请求
            response = await call_next(request)

            # 计算响应时间
            process_time = time.time() - request.state.start_time

            # 添加响应头
            response.headers["X-Request-ID"] = request_id
            response.headers["X-Process-Time"] = str(process_time)

            # 记录请求完成
            logger.info(
                f"Request completed: {request.method} {request.url.path} - {response.status_code}",
                extra={
                    "request_id": request_id,
                    "method": request.method,
                    "path": request.url.path,
                    "status_code": response.status_code,
                    "process_time": process_time,
                    "response_size": response.headers.get("content-length", 0)
                }
            )

            # 更新统计信息
            self._update_stats(request.method, request.url.path, response.status_code, process_time)

            return response

        except Exception as e:
            # 记录异常
            process_time = time.time() - request.state.start_time
            logger.error(
                f"Request failed: {request.method} {request.url.path} - {str(e)}",
                extra={
                    "request_id": request_id,
                    "method": request.method,
                    "path": request.url.path,
                    "error": str(e),
                    "process_time": process_time
                },
                exc_info=True
            )

            # 更新错误统计
            self._update_stats(request.method, request.url.path, 500, process_time)
            raise

    def _update_stats(self, method: str, path: str, status_code: int, process_time: float):
        """更新统计信息"""
        key = f"{method} {path}"

        if key not in self.request_counts:
            self.request_counts[key] = 0
            self.response_times[key] = []

        self.request_counts[key] += 1
        self.response_times[key].append(process_time)

        # 保留最近1000个响应时间
        if len(self.response_times[key]) > 1000:
            self.response_times[key] = self.response_times[key][-1000:]

    def get_stats(self) -> dict:
        """获取统计信息"""
        stats = {}
        for key, count in self.request_counts.items():
            if key in self.response_times:
                times = self.response_times[key]
                stats[key] = {
                    "request_count": count,
                    "avg_response_time": sum(times) / len(times),
                    "min_response_time": min(times),
                    "max_response_time": max(times),
                    "p95_response_time": sorted(times)[int(len(times) * 0.95)]
                }
        return stats

class RateLimitMiddleware(BaseHTTPMiddleware):
    """限流中间件"""

    def __init__(self, app, requests_per_minute: int = 60, burst_size: int = 10):
        super().__init__(app)
        self.requests_per_minute = requests_per_minute
        self.burst_size = burst_size
        self.client_requests = {}  # {client_ip: [(timestamp, count), ...]}

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """处理请求并应用限流"""
        client_ip = request.client.host if request.client else "unknown"
        current_time = time.time()

        # 清理过期记录
        self._cleanup_old_requests(current_time)

        # 检查当前客户端请求计数
        recent_requests = [
            timestamp for timestamp, _ in self.client_requests.get(client_ip, [])
            if current_time - timestamp < 60  # 1分钟内
        ]

        # 检查是否超过限制
        if len(recent_requests) >= self.requests_per_minute:
            logger.warning(
                f"Rate limit exceeded for {client_ip}: {len(recent_requests)}/min",
                extra={"client_ip": client_ip}
            )
            from fastapi import HTTPException
            raise HTTPException(
                status_code=429,
                detail="Too many requests",
                headers={"Retry-After": "60"}
            )

        # 记录当前请求
        if client_ip not in self.client_requests:
            self.client_requests[client_ip] = []
        self.client_requests[client_ip].append((current_time, 1))

        # 处理请求
        response = await call_next(request)

        # 添加限流头
        response.headers["X-RateLimit-Limit"] = str(self.requests_per_minute)
        response.headers["X-RateLimit-Remaining"] = str(max(0, self.requests_per_minute - len(recent_requests) - 1))

        return response

    def _cleanup_old_requests(self, current_time: float):
        """清理过期的请求记录"""
        for client_ip in list(self.client_requests.keys()):
            self.client_requests[client_ip] = [
                (timestamp, count) for timestamp, count in self.client_requests[client_ip]
                if current_time - timestamp < 300  # 保留5分钟内的记录
            ]
            if not self.client_requests[client_ip]:
                del self.client_requests[client_ip]

class CacheControlMiddleware(BaseHTTPMiddleware):
    """缓存控制中间件"""

    def __init__(self, app, default_ttl: int = 300):
        super().__init__(app)
        self.default_ttl = default_ttl
        self.cache_rules = {
            # 静态资源
            "/static/": {"max-age": 86400},  # 1天
            "/docs": {"max-age": 3600},      # 1小时
            "/openapi.json": {"max-age": 3600},
            # API端点
            "/api/health": {"max-age": 30},  # 30秒
            "/api/predict": {"no-cache": True},  # 不缓存预测结果
        }

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """处理请求并设置缓存头"""
        response = await call_next(request)

        # 根据路径设置缓存头
        path = request.url.path
        cache_rule = self._get_cache_rule(path)

        if cache_rule.get("no-cache"):
            response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
            response.headers["Pragma"] = "no-cache"
            response.headers["Expires"] = "0"
        else:
            max_age = cache_rule.get("max-age", self.default_ttl)
            response.headers["Cache-Control"] = f"public, max-age={max_age}"

        return response

    def _get_cache_rule(self, path: str) -> dict:
        """获取路径的缓存规则"""
        for pattern, rule in self.cache_rules.items():
            if path.startswith(pattern):
                return rule
        return {"max-age": self.default_ttl}

class CompressionMiddleware(BaseHTTPMiddleware):
    """响应压缩中间件"""

    def __init__(self, app, minimum_size: int = 1024):
        super().__init__(app)
        self.minimum_size = minimum_size

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """处理请求并压缩响应"""
        response = await call_next(request)

        # 检查是否应该压缩
        if self._should_compress(request, response):
            # 这里可以添加压缩逻辑
            # 例如使用gzip压缩JSON响应
            response.headers["Content-Encoding"] = "gzip"

        return response

    def _should_compress(self, request: Request, response: Response) -> bool:
        """判断是否应该压缩响应"""
        # 检查Accept-Encoding头
        accept_encoding = request.headers.get("accept-encoding", "")
        if "gzip" not in accept_encoding.lower():
            return False

        # 检查内容类型
        content_type = response.headers.get("content-type", "")
        compressible_types = [
            "application/json",
            "text/html",
            "text/css",
            "text/javascript",
            "application/javascript"
        ]
        if not any(ct in content_type for ct in compressible_types):
            return False

        # 检查响应大小（简化处理）
        content_length = response.headers.get("content-length")
        if content_length and int(content_length) < self.minimum_size:
            return False

        return True

class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """安全头中间件"""

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """处理请求并添加安全头"""
        response = await call_next(request)

        # 添加安全头
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"

        # 移除敏感信息
        response.headers.pop("Server", None)

        return response

# 中间件配置类
class MiddlewareConfig:
    """中间件配置"""

    @staticmethod
    def setup_middleware(app):
        """设置所有中间件"""
        # 注意：中间件的顺序很重要！
        # 最后添加的中间件最先执行

        # 1. 安全头中间件（最先执行）
        app.add_middleware(SecurityHeadersMiddleware)

        # 2. 性能监控中间件
        app.add_middleware(PerformanceMonitoringMiddleware)

        # 3. 限流中间件
        app.add_middleware(RateLimitMiddleware, requests_per_minute=100)

        # 4. 缓存控制中间件
        app.add_middleware(CacheControlMiddleware)

        # 5. 压缩中间件
        app.add_middleware(CompressionMiddleware)

        print("✅ 所有中间件已设置完成")

# 使用示例
"""
from fastapi import FastAPI
from templates.performance_middleware import MiddlewareConfig

app = FastAPI(title="Football Prediction API", version="2.0.0")

# 设置中间件
MiddlewareConfig.setup_middleware(app)

@app.get("/api/health")
async def health_check():
    return {"status": "healthy"}

@app.post("/api/predict")
async def predict_match(request: dict):
    # 预测逻辑
    return {"prediction": "HOME", "confidence": 0.75}
"""