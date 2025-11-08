"""
增强的安全中间件
Enhanced Security Middleware

提供企业级安全中间件，包括CORS、安全头部、CSRF保护等。
"""

import secrets
from datetime import UTC, datetime

from fastapi import FastAPI, Request, Response, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from ..auth.enhanced_security import get_client_identifier, rate_limiter

# ============================================================================
# CORS配置
# ============================================================================


def configure_cors(app: FastAPI) -> None:
    """配置CORS中间件"""

    # 生产环境允许的源
    allowed_origins = [
        "http://localhost:3000",  # 开发环境
        "http://localhost:8080",  # 开发环境
        "https://yourdomain.com",  # 生产环境
        "https://api.yourdomain.com",  # API域名
    ]

    app.add_middleware(
        CORSMiddleware,
        allow_origins=allowed_origins,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS"],
        allow_headers=[
            "Authorization",
            "Content-Type",
            "X-Requested-With",
            "X-CSRF-Token",
            "X-API-Key",
            "Accept",
            "Origin",
        ],
        expose_headers=["X-Total-Count", "X-Rate-Limit-Remaining"],
    )


# ============================================================================
# 安全头部中间件
# ============================================================================


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """安全头部中间件"""

    async def dispatch(self, request: Request, call_next) -> Response:
        response = await call_next(request)

        # 安全头部配置
        security_headers = {
            # 内容安全策略
            "Content-Security-Policy": (
                "default-src 'self'; "
                "script-src 'self' 'unsafe-inline' 'unsafe-eval'; "
                "style-src 'self' 'unsafe-inline'; "
                "img-src 'self' data: https:; "
                "font-src 'self' data:; "
                "connect-src 'self' https://api.yourdomain.com; "
                "frame-ancestors 'none'; "
                "base-uri 'self'; "
                "form-action 'self'"
            ),
            # 严格传输安全（仅HTTPS）
            "Strict-Transport-Security": "max-age=31536000; includeSubDomains; preload",
            # XSS保护
            "X-XSS-Protection": "1; mode=block",
            # 内容类型嗅探保护
            "X-Content-Type-Options": "nosniff",
            # 点击劫持保护
            "X-Frame-Options": "DENY",
            # 引用策略
            "Referrer-Policy": "strict-origin-when-cross-origin",
            # 权限策略
            "Permissions-Policy": (
                "geolocation=(), "
                "microphone=(), "
                "camera=(), "
                "payment=(), "
                "usb=(), "
                "magnetometer=(), "
                "gyroscope=(), "
                "accelerometer=()"
            ),
            # API安全
            "X-API-Version": "1.0.0",
            "X-Content-Security-Policy": "default-src 'self'",
        }

        # 添加安全头部
        for header, value in security_headers.items():
            response.headers[header] = value

        return response


# ============================================================================
# 速率限制中间件
# ============================================================================


class RateLimitMiddleware(BaseHTTPMiddleware):
    """增强的速率限制中间件"""

    def __init__(self, app):
        super().__init__(app)

        # 不同端点的限制配置
        self.rate_limits = {
            "default": {"requests": 100, "window": 3600},  # 100请求/小时
            "auth": {"requests": 10, "window": 300},  # 10请求/5分钟
            "predict": {"requests": 50, "window": 3600},  # 50预测/小时
            "upload": {"requests": 5, "window": 300},  # 5上传/5分钟
        }

    async def dispatch(self, request: Request, call_next) -> Response:
        # 获取客户端标识符
        client_id = get_client_identifier(request)

        # 确定限制配置
        path = request.url.path
        if "/auth/" in path:
            limit_config = self.rate_limits["auth"]
        elif "/predict" in path:
            limit_config = self.rate_limits["predict"]
        elif "/upload" in path:
            limit_config = self.rate_limits["upload"]
        else:
            limit_config = self.rate_limits["default"]

        # 检查速率限制
        key = f"rate_limit:{client_id}:{path}"
        if not rate_limiter.is_allowed(
            key, limit_config["requests"], limit_config["window"]
        ):
            # 计算重试时间
            retry_after = limit_config["window"]

            return JSONResponse(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                content={
                    "error": True,
                    "message": "请求过于频繁，请稍后再试",
                    "retry_after": retry_after,
                    "limit": limit_config["requests"],
                    "window": limit_config["window"],
                },
                headers={
                    "Retry-After": str(retry_after),
                    "X-Rate-Limit-Limit": str(limit_config["requests"]),
                    "X-Rate-Limit-Window": str(limit_config["window"]),
                    "X-Rate-Limit-Remaining": "0",
                },
            )

        response = await call_next(request)

        # 添加速率限制头部
        response.headers["X-Rate-Limit-Limit"] = str(limit_config["requests"])
        response.headers["X-Rate-Limit-Window"] = str(limit_config["window"])

        # 计算剩余请求数（简化实现）
        remaining_requests = max(0, limit_config["requests"] - 1)
        response.headers["X-Rate-Limit-Remaining"] = str(remaining_requests)

        return response


# ============================================================================
# 请求日志中间件
# ============================================================================


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """请求日志中间件"""

    async def dispatch(self, request: Request, call_next) -> Response:
        start_time = datetime.now(UTC)

        # 记录请求信息
        request.headers.get("X-Forwarded-For", request.client.host)
        request.headers.get("User-Agent", "Unknown")
        str(request.url.path)

        # 记录敏感信息时要注意隐私
        query_params = dict(request.query_params)

        # 移除敏感参数
        sensitive_params = ["password", "token", "api_key", "secret"]
        for param in sensitive_params:
            if param in query_params:
                query_params[param] = "***REDACTED***"

        # 执行请求
        response = await call_next(request)

        # 计算处理时间
        process_time = (datetime.now(UTC) - start_time).total_seconds()

        # 记录响应信息

        # 这里可以添加实际的日志记录
        # logger.info(f"{method} {path} - {status_code} - {process_time:.3f}s - {client_ip}")

        # 添加处理时间头部
        response.headers["X-Process-Time"] = f"{process_time:.3f}"

        return response


# ============================================================================
# CSRF保护中间件
# ============================================================================


class CSRFProtectionMiddleware(BaseHTTPMiddleware):
    """CSRF保护中间件"""

    def __init__(self, app):
        super().__init__(app)
        self.csrf_tokens = {}
        self.token_expiry = 3600  # 1小时

    def generate_csrf_token(self) -> str:
        """生成CSRF令牌"""
        return secrets.token_urlsafe(32)

    async def dispatch(self, request: Request, call_next) -> Response:
        # 对状态改变的方法应用CSRF保护
        if request.method in ["POST", "PUT", "DELETE", "PATCH"]:
            # 检查是否是API请求（通常使用JSON）
            content_type = request.headers.get("Content-Type", "")

            if "application/json" in content_type:
                # JSON API请求使用Authorization头部，不需要CSRF保护
                pass
            else:
                # 表单请求需要CSRF令牌
                csrf_token = request.headers.get("X-CSRF-Token")
                if not csrf_token or not self.validate_csrf_token(csrf_token, request):
                    return JSONResponse(
                        status_code=status.HTTP_403_FORBIDDEN,
                        content={"error": True, "message": "无效的CSRF令牌"},
                    )

        response = await call_next(request)

        # 为新会话生成CSRF令牌
        if request.method == "GET" and "/auth/" in str(request.url):
            csrf_token = self.generate_csrf_token()
            self.csrf_tokens[csrf_token] = datetime.now(UTC).timestamp()
            response.headers["X-CSRF-Token"] = csrf_token

        return response

    def validate_csrf_token(self, token: str, request: Request) -> bool:
        """验证CSRF令牌"""
        token_timestamp = self.csrf_tokens.get(token)
        if not token_timestamp:
            return False

        # 检查令牌是否过期
        current_time = datetime.now(UTC).timestamp()
        if current_time - token_timestamp > self.token_expiry:
            del self.csrf_tokens[token]
            return False

        return True


# ============================================================================
# IP白名单中间件
# ============================================================================


class IPWhitelistMiddleware(BaseHTTPMiddleware):
    """IP白名单中间件"""

    def __init__(self, app, allowed_ips: list[str] = None):
        super().__init__(app)
        # 生产环境应该配置允许的IP地址
        self.allowed_ips = allowed_ips or [
            "127.0.0.1",  # 本地回环
            "::1",  # IPv6本地回环
            # 添加其他允许的IP地址
        ]

    async def dispatch(self, request: Request, call_next) -> Response:
        # 获取真实IP地址
        forwarded_for = request.headers.get("X-Forwarded-For")
        if forwarded_for:
            ip = forwarded_for.split(",")[0].strip()
        else:
            ip = request.client.host

        # 检查IP白名单
        if ip not in self.allowed_ips:
            return JSONResponse(
                status_code=status.HTTP_403_FORBIDDEN,
                content={"error": True, "message": "访问被拒绝"},
            )

        return await call_next(request)


# ============================================================================
# 中间件配置函数
# ============================================================================


def configure_security_middleware(app: FastAPI) -> None:
    """配置所有安全中间件"""

    # 1. 信任的主机中间件
    app.add_middleware(
        TrustedHostMiddleware,
        allowed_hosts=[
            "localhost",
            "127.0.0.1",
            "yourdomain.com",
            "api.yourdomain.com",
        ],
    )

    # 2. 安全头部中间件
    app.add_middleware(SecurityHeadersMiddleware)

    # 3. 速率限制中间件
    app.add_middleware(RateLimitMiddleware)

    # 4. 请求日志中间件
    app.add_middleware(RequestLoggingMiddleware)

    # 5. CSRF保护中间件（可选，根据需要启用）
    # app.add_middleware(CSRFProtectionMiddleware)

    # 6. IP白名单中间件（可选，根据需要启用）
    # app.add_middleware(IPWhitelistMiddleware)


# ============================================================================
# 安全配置导出
# ============================================================================

SECURITY_CONFIG = {
    "csrf_protection": True,
    "rate_limiting": True,
    "security_headers": True,
    "cors_enabled": True,
    "ip_whitelist": False,  # 生产环境可启用
    "request_logging": True,
}
