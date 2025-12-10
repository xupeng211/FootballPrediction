"""P4-3: HTTP 安全头中间件
为所有响应添加安全 HTTP 头，防止常见的 Web 安全漏洞.
"""

import os
from collections.abc import Callable

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """安全头中间件

    为所有响应添加安全 HTTP 头，包括：
    - X-Content-type-Options: nosniff
    - X-Frame-Options: DENY
    - X-XSS-Protection: 1; mode=block
    - Strict-Transport-Security: (仅生产环境)
    - Content-Security-Policy: 基础 CSP 策略
    """

    def __init__(self, app, environment: str = None):
        super().__init__(app)
        self.environment = environment or os.getenv("ENV", "development").lower()
        self.is_production = self.environment in ["production", "prod"]

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """处理请求并添加安全头"""

        # 调用下一个中间件/路由处理器
        response = await call_next(request)

        # 添加安全头
        self._add_security_headers(request, response)

        return response

    def _add_security_headers(self, request: Request, response: Response) -> None:
        """添加安全 HTTP 头到响应"""

        # 1. X-Content-type-Options: 防止 MIME 类型嗅探攻击
        response.headers["X-Content-type-Options"] = "nosniff"

        # 2. X-Frame-Options: 防止点击劫持攻击
        response.headers["X-Frame-Options"] = "DENY"

        # 3. X-XSS-Protection: 启用 XSS 过滤器
        response.headers["X-XSS-Protection"] = "1; mode=block"

        # 4. Referrer-Policy: 控制 Referrer 信息泄露
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"

        # 5. Permissions-Policy: 控制浏览器功能
        permissions_policy = (
            "geolocation=(), "
            "microphone=(), "
            "camera=(), "
            "payment=(), "
            "usb=(), "
            "magnetometer=(), "
            "gyroscope=(), "
            "accelerometer=()"
        )
        response.headers["Permissions-Policy"] = permissions_policy

        # 6. Content-Security-Policy: 基础 CSP 策略
        csp_directives = [
            "default-src 'self'",
            "script-src 'self' 'unsafe-inline' 'unsafe-eval'",  # 允许内联脚本（为兼容性）
            "style-src 'self' 'unsafe-inline'",  # 允许内联样式（为兼容性）
            "img-src 'self' data: https:",  # 允许图片和数据 URI
            "font-src 'self' data:",  # 允许字体和数据 URI
            "connect-src 'self' https:",  # 限制连接目标
            "frame-ancestors 'none'",  # 禁止嵌入
            "base-uri 'self'",  # 限制基础 URI
            "form-action 'self'",  # 限制表单提交目标
        ]

        # 在生产环境中添加更严格的 CSP
        if self.is_production:
            csp_directives = [
                "default-src 'self'",
                "script-src 'self'",  # 生产环境移除内联脚本
                "style-src 'self'",  # 生产环境移除内联样式
                "img-src 'self' data:",
                "font-src 'self' data:",
                "connect-src 'self'",
                "frame-ancestors 'none'",
                "base-uri 'self'",
                "form-action 'self'",
                "object-src 'none'",  # 禁止插件
                "media-src 'self'",  # 限制媒体源
            ]

        response.headers["Content-Security-Policy"] = "; ".join(csp_directives)

        # 7. Strict-Transport-Security: 强制 HTTPS（仅生产环境）
        if self.is_production and request.url.scheme == "https":
            # 1年有效期，包含子域名，预加载
            hsts_value = "max-age=31536000; " "includeSubDomains; " "preload"
            response.headers["Strict-Transport-Security"] = hsts_value

        # 8. 清除可能泄露服务器信息的不安全头
        if "Server" in response.headers:
            del response.headers["Server"]
        if "X-Powered-By" in response.headers:
            del response.headers["X-Powered-By"]

        # 9. 添加缓存控制头（敏感内容）
        if self._is_sensitive_path(request.url.path):
            # 对于敏感路径，禁止缓存
            response.headers["Cache-Control"] = (
                "no-store, no-cache, must-revalidate, private"
            )
            response.headers["Pragma"] = "no-cache"
            response.headers["Expires"] = "0"

    def _is_sensitive_path(self, path: str) -> bool:
        """检查是否为敏感路径"""
        sensitive_paths = [
            "/api/v1/auth/",
            "/api/v1/users/",
            "/api/v1/admin/",
            "/login",
            "/register",
            "/profile",
            "/settings",
        ]

        return any(sensitive_path in path for sensitive_path in sensitive_paths)


def add_security_middleware(app, environment: str = None) -> None:
    """向 FastAPI 应用添加安全头中间件

    Args:
        app: FastAPI 应用实例
        environment: 环境标识（可选）
    """
    app.add_middleware(SecurityHeadersMiddleware, environment=environment)


# 便捷函数，用于在路由级别应用安全头
def apply_security_headers(response: Response, is_sensitive: bool = False) -> Response:
    """手动应用安全头到响应

    Args:
        response: FastAPI 响应对象
        is_sensitive: 是否为敏感内容

    Returns:
        Response: 添加了安全头的响应对象
    """
    environment = os.getenv("ENV", "development").lower()
    is_production = environment in ["production", "prod"]

    # 基础安全头
    response.headers["X-Content-type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["X-XSS-Protection"] = "1; mode=block"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"

    # CSP 策略
    csp = (
        "default-src 'self'; "
        "script-src 'self' 'unsafe-inline'; "
        "style-src 'self' 'unsafe-inline'; "
        "img-src 'self' data:; "
        "connect-src 'self'"
    )

    if is_production:
        csp = (
            "default-src 'self'; "
            "script-src 'self'; "
            "style-src 'self'; "
            "img-src 'self' data:; "
            "connect-src 'self'"
        )

    response.headers["Content-Security-Policy"] = csp

    # 敏感内容的缓存控制
    if is_sensitive:
        response.headers["Cache-Control"] = (
            "no-store, no-cache, must-revalidate, private"
        )
        response.headers["Pragma"] = "no-cache"
        response.headers["Expires"] = "0"

    return response


# 导出主要接口
__all__ = [
    "SecurityHeadersMiddleware",
    "add_security_middleware",
    "apply_security_headers",
]
