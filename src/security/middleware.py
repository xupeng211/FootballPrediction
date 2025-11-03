"""
安全中间件
Security Middleware

提供各种安全功能的中间件,包括:
- 安全头设置
- CORS配置
- 速率限制
- 审计日志
"""

import logging
import os
import time
from collections.abc import Callable
from typing import Any

from fastapi import HTTPException, Request, Response, status

try:
    from fastapi.middleware.base import BaseHTTPMiddleware
    from fastapi.middleware.cors import CORSMiddleware
except ImportError:
    # 使用starlette的中间件作为替代
    from starlette.middleware.base import BaseHTTPMiddleware
    from starlette.middleware.cors import CORSMiddleware

from collections import defaultdict

from starlette.types import ASGIApp

logger = logging.getLogger(__name__)


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """安全头中间件"""

    def __init__(self, app: ASGIApp, enabled: bool = True):
        """函数文档字符串"""
        pass
        # 添加pass语句
        super().__init__(app)
        self.enabled = enabled
        self.headers = self._get_security_headers()

    def _get_security_headers(self) -> dict[str, str]:
        """获取安全头配置"""
        return {
            "X-Frame-Options": os.getenv("X_FRAME_OPTIONS", "DENY"),
            "X-Content-Type-Options": os.getenv("X_CONTENT_TYPE_OPTIONS", "nosniff"),
            "X-XSS-Protection": os.getenv("X_XSS_PROTECTION", "1; mode=block"),
            "Referrer-Policy": "strict-origin-when-cross-origin",
            "Permissions-Policy": "geolocation=(), microphone=(), camera=()",
        }

        # 只有在HTTPS环境下才添加HSTS头
        if os.getenv("FORCE_HTTPS", "false").lower() == "true":
            self.headers["Strict-Transport-Security"] = os.getenv(
                "STRICT_TRANSPORT_SECURITY", "max-age=31536000; includeSubDomains"
            )

        return self.headers

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """处理请求并添加安全头"""
        if not self.enabled:
            return await call_next(request)

        response = await call_next(request)

        # 添加安全头
        for header, value in self.headers.items():
            response.headers[header] = value

        return response


class RateLimitMiddleware(BaseHTTPMiddleware):
    """速率限制中间件"""

    def __init__(
        self, app: ASGIApp, requests_per_minute: int = 60, burst_size: int = 10
    ):
        super().__init__(app)
        self.requests_per_minute = requests_per_minute
        self.burst_size = burst_size
        self.clients = defaultdict(list)

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """处理请求并实施速率限制"""
        client_ip = self._get_client_ip(request)
        current_time = time.time()

        # 清理过期的请求记录
        self._cleanup_old_requests(client_ip, current_time)

        # 检查速率限制
        if self._is_rate_limited(client_ip, current_time):
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Rate limit exceeded",
            )

        # 记录当前请求
        self.clients[client_ip].append(current_time)

        return await call_next(request)

    def _get_client_ip(self, request: Request) -> str:
        """获取客户端IP地址"""
        # 优先使用X-Forwarded-For头（在代理后）
        forwarded_for = request.headers.get("X-Forwarded-For")
        if forwarded_for:
            return forwarded_for.split(",")[0].strip()

        # 使用X-Real-IP头
        real_ip = request.headers.get("X-Real-IP")
        if real_ip:
            return real_ip.strip()

        # 使用直接连接的IP
        return request.client.host if request.client else "unknown"

    def _cleanup_old_requests(self, client_ip: str, current_time: float):
        """函数文档字符串"""
        pass
        # 添加pass语句
        """清理过期的请求记录"""
        cutoff_time = current_time - 60  # 1分钟前
        self.clients[client_ip] = [
            req_time for req_time in self.clients[client_ip] if req_time > cutoff_time
        ]

    def _is_rate_limited(self, client_ip: str, current_time: float) -> bool:
        """检查是否超过速率限制"""
        requests = self.clients[client_ip]

        # 检查突发限制
        if len(requests) >= self.burst_size:
            return True

        # 检查每分钟限制
        one_minute_ago = current_time - 60
        recent_requests = [
            req_time for req_time in requests if req_time > one_minute_ago
        ]

        return len(recent_requests) >= self.requests_per_minute


class AuditLoggingMiddleware(BaseHTTPMiddleware):
    """审计日志中间件"""

    def __init__(self, app: ASGIApp, enabled: bool = True):
        """函数文档字符串"""
        pass
        # 添加pass语句
        super().__init__(app)
        self.enabled = enabled
        self.setup_audit_logger()

    def setup_audit_logger(self):
        """函数文档字符串"""
        pass
        # 添加pass语句
        """设置审计日志记录器"""
        if not self.enabled:
            return None
        audit_file = os.getenv("AUDIT_LOG_FILE", "/var/log/app/audit.log")
        audit_level = os.getenv("AUDIT_LOG_LEVEL", "INFO")

        # 创建审计日志记录器
        self.audit_logger = logging.getLogger("audit")
        self.audit_logger.setLevel(getattr(logging, audit_level))

        # 创建文件处理器
        try:
            os.makedirs(os.path.dirname(audit_file), exist_ok=True)
            handler = logging.FileHandler(audit_file)
            formatter = logging.Formatter(
                "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
            )
            handler.setFormatter(formatter)
            self.audit_logger.addHandler(handler)
        except Exception as e:
            logger.warning(f"Failed to setup audit logger: {e}")
            self.audit_logger = logger

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """处理请求并记录审计日志"""
        if not self.enabled:
            return await call_next(request)

        start_time = time.time()

        # 记录请求开始
        self._log_request_start(request)

        try:
            response = await call_next(request)

            # 记录请求完成
            duration = time.time() - start_time
            self._log_request_complete(request, response, duration)

            return response

        except Exception as e:
            # 记录请求错误
            duration = time.time() - start_time
            self._log_request_error(request, e, duration)
            raise

    def _log_request_start(self, request: Request):
        """函数文档字符串"""
        pass
        # 添加pass语句
        """记录请求开始"""
        self.audit_logger.info(
            f"Request started: {request.method} {request.url} - "
            f"Client: {self._get_client_info(request)} - "
            f"User-Agent: {request.headers.get('User-Agent', 'Unknown')}"
        )

    def _log_request_complete(
        self, request: Request, response: Response, duration: float
    ):
        """记录请求完成"""
        self.audit_logger.info(
            f"Request completed: {request.method} {request.url} - "
            f"Status: {response.status_code} - "
            f"Duration: {duration:.3f}s - "
            f"Client: {self._get_client_info(request)}"
        )

    def _log_request_error(self, request: Request, error: Exception, duration: float):
        """函数文档字符串"""
        pass
        # 添加pass语句
        """记录请求错误"""
        self.audit_logger.error(
            f"Request failed: {request.method} {request.url} - "
            f"Error: {str(error)} - "
            f"Duration: {duration:.3f}s - "
            f"Client: {self._get_client_info(request)}"
        )

    def _get_client_info(self, request: Request) -> str:
        """获取客户端信息"""
        client_ip = request.client.host if request.client else "unknown"
        forwarded_for = request.headers.get("X-Forwarded-For")
        if forwarded_for:
            client_ip = f"{forwarded_for.split(',')[0].strip()} (via {client_ip})"
        return client_ip


class CSPMiddleware(BaseHTTPMiddleware):
    """内容安全策略中间件"""

    def __init__(self, app: ASGIApp, enabled: bool = True):
        """函数文档字符串"""
        pass
        # 添加pass语句
        super().__init__(app)
        self.enabled = enabled
        self.csp_policy = self._build_csp_policy()

    def _build_csp_policy(self) -> str:
        """构建CSP策略"""
        if not self.enabled:
            return ""

        default_src = os.getenv("CSP_DEFAULT_SRC", "'self'")
        script_src = os.getenv("CSP_SCRIPT_SRC", "'self' 'unsafe-inline'")
        style_src = os.getenv("CSP_STYLE_SRC", "'self' 'unsafe-inline'")

        directives = [
            f"default-src {default_src}",
            f"script-src {script_src}",
            f"style-src {style_src}",
            "img-src 'self' data: https:",
            "font-src 'self' data:",
            "connect-src 'self'",
            "frame-ancestors 'none'",
            "base-uri 'self'",
            "form-action 'self'",
        ]

        return "; ".join(directives)

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """处理请求并添加CSP头"""
        if not self.enabled:
            return await call_next(request)

        response = await call_next(request)
        response.headers["Content-Security-Policy"] = self.csp_policy

        return response


def setup_security_middleware(app: ASGIApp) -> ASGIApp:
    """设置所有安全中间件"""

    # CORS中间件
    app.add_middleware(
        CORSMiddleware,
        allow_origins=os.getenv("CORS_ORIGINS", "*").split(","),
        allow_credentials=os.getenv("CORS_ALLOW_CREDENTIALS", "false").lower()
        == "true",
        allow_methods=os.getenv(
            "CORS_ALLOW_METHODS", "GET,POST,PUT,DELETE,OPTIONS"
        ).split(","),
        allow_headers=os.getenv("CORS_ALLOW_HEADERS", "*").split(","),
    )

    # 速率限制中间件
    rate_limit_enabled = os.getenv("RATE_LIMIT_ENABLED", "true").lower() == "true"
    if rate_limit_enabled:
        app.add_middleware(
            RateLimitMiddleware,
            requests_per_minute=int(os.getenv("RATE_LIMIT_PER_MINUTE", "60")),
            burst_size=int(os.getenv("RATE_LIMIT_BURST", "10")),
        )

    # 审计日志中间件
    audit_enabled = os.getenv("AUDIT_LOG_ENABLED", "true").lower() == "true"
    app.add_middleware(AuditLoggingMiddleware, enabled=audit_enabled)

    # 安全头中间件
    security_headers_enabled = (
        os.getenv("SECURE_HEADERS_ENABLED", "true").lower() == "true"
    )
    app.add_middleware(SecurityHeadersMiddleware, enabled=security_headers_enabled)

    # CSP中间件
    csp_enabled = os.getenv("CSP_ENABLED", "true").lower() == "true"
    app.add_middleware(CSPMiddleware, enabled=csp_enabled)

    return app


class SecurityConfig:
    """类文档字符串"""

    pass  # 添加pass语句
    """安全配置类"""

    def __init__(self):
        """函数文档字符串"""
        pass
        # 添加pass语句
        self.load_config()

    def load_config(self):
        """函数文档字符串"""
        pass
        # 添加pass语句
        """加载安全配置"""
        self.rate_limit_per_minute = int(os.getenv("RATE_LIMIT_PER_MINUTE", "60"))
        self.rate_limit_burst = int(os.getenv("RATE_LIMIT_BURST", "10"))

        self.cors_origins = os.getenv("CORS_ORIGINS", "*").split(",")
        self.cors_allow_credentials = (
            os.getenv("CORS_ALLOW_CREDENTIALS", "false").lower() == "true"
        )

        self.security_headers_enabled = (
            os.getenv("SECURE_HEADERS_ENABLED", "true").lower() == "true"
        )
        self.csp_enabled = os.getenv("CSP_ENABLED", "true").lower() == "true"

        self.force_https = os.getenv("FORCE_HTTPS", "false").lower() == "true"

        self.audit_log_enabled = (
            os.getenv("AUDIT_LOG_ENABLED", "true").lower() == "true"
        )
        self.audit_log_level = os.getenv("AUDIT_LOG_LEVEL", "INFO")

        self.password_min_length = int(os.getenv("PASSWORD_MIN_LENGTH", "12"))
        self.password_require_uppercase = (
            os.getenv("PASSWORD_REQUIRE_UPPERCASE", "true").lower() == "true"
        )
        self.password_require_lowercase = (
            os.getenv("PASSWORD_REQUIRE_LOWERCASE", "true").lower() == "true"
        )
        self.password_require_numbers = (
            os.getenv("PASSWORD_REQUIRE_NUMBERS", "true").lower() == "true"
        )
        self.password_require_symbols = (
            os.getenv("PASSWORD_REQUIRE_SYMBOLS", "true").lower() == "true"
        )

        self.session_timeout_minutes = int(os.getenv("SESSION_TIMEOUT_MINUTES", "30"))
        self.session_secure_cookie = (
            os.getenv("SESSION_SECURE_COOKIE", "true").lower() == "true"
        )
        self.session_http_only_cookie = (
            os.getenv("SESSION_HTTP_ONLY_COOKIE", "true").lower() == "true"
        )
        self.session_samesite_cookie = os.getenv("SESSION_SAMESITE_COOKIE", "Strict")

    def validate_password(self, password: str) -> bool:
        """验证密码强度"""
        if len(password) < self.password_min_length:
            return False

        if self.password_require_uppercase and not any(c.isupper() for c in password):
            return False

        if self.password_require_lowercase and not any(c.islower() for c in password):
            return False

        if self.password_require_numbers and not any(c.isdigit() for c in password):
            return False

        if self.password_require_symbols and not any(
            c in "!@#$%^&*()_+-=[]{}|;:,.<>?" for c in password
        ):
            return False

        return True

    def get_session_config(self) -> dict[str, Any]:
        """获取会话配置"""
        return {
            "max_age": self.session_timeout_minutes * 60,
            "secure": self.session_secure_cookie,
            "httponly": self.session_http_only_cookie,
            "samesite": self.session_samesite_cookie,
        }


# 全局安全配置实例
security_config = SecurityConfig()
