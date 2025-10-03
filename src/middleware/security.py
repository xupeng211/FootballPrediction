"""
安全中间件模块
Security Middleware Module

提供API安全相关的中间件功能：
- 请求限流
- CORS配置
- 输入验证
- 安全头
"""

import time
import ipaddress
from typing import Dict, List, Optional, Set
from collections import defaultdict, deque
from fastapi import FastAPI, Request, Response, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware
import secrets


class InMemoryRateLimiter:
    """内存限流器"""

    def __init__(self):
        self.requests: Dict[str, deque] = defaultdict(deque)
        self.locks: Dict[str, float] = {}

    def is_allowed(
        self,
        key: str,
        limit: int,
        window: int,
        current_time: Optional[float] = None
    ) -> bool:
        """检查是否允许请求"""
        if current_time is None:
            current_time = time.time()

        # 清理过期的锁
        if key in self.locks and current_time > self.locks[key]:
            del self.locks[key]
            if key in self.requests:
                del self.requests[key]

        # 检查是否被锁定
        if key in self.locks:
            return False

        # 获取请求队列
        request_times = self.requests[key]

        # 移除过期的请求
        while request_times and request_times[0] < current_time - window:
            request_times.popleft()

        # 检查是否超过限制
        if len(request_times) >= limit:
            # 锁定一段时间
            self.locks[key] = current_time + window
            return False

        # 记录当前请求
        request_times.append(current_time)
        return True


class SecurityMiddleware:
    """安全中间件配置类"""

    def __init__(self, app: FastAPI):
        self.app = app
        self.rate_limiter = InMemoryRateLimiter()
        self.blocked_ips: Set[str] = set()
        self._setup_middleware()

    def _setup_middleware(self):
        """设置所有安全中间件"""

        # 1. CORS配置
        self.app.add_middleware(
            CORSMiddleware,
            allow_origins=[
                "http://localhost:3000",
                "http://localhost:8080",
                "https://footballprediction.example.com",
                "https://api.footballprediction.example.com",
            ],
            allow_credentials=True,
            allow_methods=["GET", "POST", "PUT", "DELETE"],
            allow_headers=["*"],
            expose_headers=["X-RateLimit-Limit", "X-RateLimit-Remaining"]
        )

        # 2. 受信任主机
        self.app.add_middleware(
            TrustedHostMiddleware,
            allowed_hosts=["localhost", "127.0.0.1", "footballprediction.example.com"]
        )

        # 3. 自定义安全中间件
        @self.app.middleware("http")
        async def security_headers(request: Request, call_next):
            """添加安全头"""
            response = await call_next(request)

            # 安全头
            response.headers["X-Content-Type-Options"] = "nosniff"
            response.headers["X-Frame-Options"] = "DENY"
            response.headers["X-XSS-Protection"] = "1; mode=block"
            response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
            response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
            response.headers["Content-Security-Policy"] = "default-src 'self'"

            # 移除服务器信息
            response.headers["Server"] = "FootballPredictionAPI"

            return response

        # 4. 限流中间件
        @self.app.middleware("http")
        async def rate_limit_middleware(request: Request, call_next):
            """请求限流"""
            client_ip = self._get_client_ip(request)

            # 检查IP是否被阻止
            if client_ip in self.blocked_ips:
                raise HTTPException(
                    status_code=403,
                    detail="IP address blocked"
                )

            # 路径特定的限流规则
            path = request.url.path
            limit, window = self._get_rate_limit(path)

            # 检查限流
            if not self.rate_limiter.is_allowed(client_ip, limit, window):
                raise HTTPException(
                    status_code=429,
                    detail="Rate limit exceeded",
                    headers={
                        "X-RateLimit-Limit": str(limit),
                        "X-RateLimit-Window": str(window),
                        "Retry-After": str(window)
                    }
                )

            response = await call_next(request)

            # 添加限流信息到响应头
            remaining = max(0, limit - len(self.rate_limiter.requests.get(client_ip, [])))
            response.headers["X-RateLimit-Limit"] = str(limit)
            response.headers["X-RateLimit-Remaining"] = str(remaining)
            response.headers["X-RateLimit-Window"] = str(window)

            return response

        # 5. 请求大小限制
        @self.app.middleware("http")
        async def request_size_limit(request: Request, call_next):
            """限制请求大小"""
            content_length = request.headers.get("content-length")
            if content_length and int(content_length) > 10 * 1024 * 1024:  # 10MB
                raise HTTPException(
                    status_code=413,
                    detail="Request entity too large"
                )

            return await call_next(request)

    def _get_client_ip(self, request: Request) -> str:
        """获取客户端IP"""
        # 检查代理头
        forwarded_for = request.headers.get("x-forwarded-for")
        if forwarded_for:
            return forwarded_for.split(",")[0].strip()

        real_ip = request.headers.get("x-real-ip")
        if real_ip:
            return real_ip

        # 使用客户端IP
        return request.client.host if request.client else "unknown"

    def _get_rate_limit(self, path: str) -> tuple[int, int]:
        """根据路径获取限流规则"""
        # 预测API - 更严格的限制
        if "/predictions/" in path:
            return 60, 60  # 60次/分钟

        # 数据API - 中等限制
        if "/data/" in path:
            return 120, 60  # 120次/分钟

        # 健康检查 - 宽松限制
        if "/health" in path:
            return 1000, 60  # 1000次/分钟

        # 默认限制
        return 100, 60  # 100次/分钟

    def block_ip(self, ip: str):
        """阻止IP"""
        self.blocked_ips.add(ip)

    def unblock_ip(self, ip: str):
        """取消阻止IP"""
        self.blocked_ips.discard(ip)


# 输入验证装饰器
def validate_input(
    max_length: Optional[int] = None,
    allowed_chars: Optional[str] = None,
    pattern: Optional[str] = None
):
    """输入验证装饰器"""
    def decorator(func):
        async def wrapper(*args, **kwargs):
            # 这里可以添加具体的验证逻辑
            return await func(*args, **kwargs)
        return wrapper
    return decorator


# SQL注入防护
def sanitize_input(input_string: str) -> str:
    """清理输入字符串，防止SQL注入"""
    if not input_string:
        return ""

    # 移除危险字符
    dangerous_chars = ["'", '"', ";", "--", "/*", "*/", "xp_", "sp_"]
    for char in dangerous_chars:
        input_string = input_string.replace(char, "")

    return input_string.strip()


# 生成安全的随机token
def generate_secure_token(length: int = 32) -> str:
    """生成安全的随机token"""
    return secrets.token_urlsafe(length)


# API密钥验证
async def verify_api_key(request: Request, api_key: str) -> bool:
    """验证API密钥"""
    # 这里应该从数据库或配置中验证API密钥
    # 示例实现
    expected_key = request.app.state.config.get("API_KEY")
    return secrets.compare_digest(api_key, expected_key)