#!/usr/bin/env python3
"""
安全中间件
集成安全监控到FastAPI应用中，提供请求安全检查、IP阻止、速率限制等功能
"""

import time

from fastapi import HTTPException, Request, Response
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from src.core.logger import get_logger
from src.security.security_automation import get_automation_engine
from src.security.security_monitor import (
    SecurityEventType,
    get_security_monitor,
)

logger = get_logger(__name__)


class SecurityMiddleware(BaseHTTPMiddleware):
    """安全中间件"""

    def __init__(self, app, **kwargs):
        super().__init__(app)
        self.monitor = get_security_monitor()
        self.automation_engine = get_automation_engine()

        # 配置选项
        self.enable_ip_blocking = kwargs.get("enable_ip_blocking", True)
        self.enable_rate_limiting = kwargs.get("enable_rate_limiting", True)
        self.enable_request_analysis = kwargs.get("enable_request_analysis", True)
        self.enable_automation = kwargs.get("enable_automation", True)

        # 速率限制配置
        self.rate_limits = {
            "requests_per_minute": kwargs.get("requests_per_minute", 100),
            "requests_per_hour": kwargs.get("requests_per_hour", 1000),
            "failed_auth_per_minute": kwargs.get("failed_auth_per_minute", 10),
            "suspicious_per_minute": kwargs.get("suspicious_per_minute", 5),
        }

        # 统计数据
        self.request_counts = {}
        self.auth_failures = {}
        self.suspicious_requests = {}

    async def dispatch(self, request: Request, call_next):
        """处理请求"""
        start_time = time.time()
        client_ip = self._get_client_ip(request)

        try:
            # 1. IP阻止检查
            if self.enable_ip_blocking and self.monitor.is_ip_blocked(client_ip):
                await self._handle_blocked_ip(request, client_ip)
                return self._create_blocked_response()

            # 2. 速率限制检查
            if self.enable_rate_limiting and await self._check_rate_limit(
                request, client_ip
            ):
                await self._handle_rate_limit_exceeded(request, client_ip)
                return self._create_rate_limit_response()

            # 3. 处理请求
            response = await call_next(request)

            # 4. 请求分析
            if self.enable_request_analysis:
                await self._analyze_request(request, response, client_ip, start_time)

            return response

        except HTTPException as e:
            # 记录HTTP异常
            await self._handle_http_exception(request, e, client_ip)
            raise

        except Exception as e:
            # 记录未预期的异常
            await self._handle_unexpected_exception(request, e, client_ip)
            raise

    def _get_client_ip(self, request: Request) -> str:
        """获取客户端真实IP地址"""
        # 检查代理头
        forwarded_for = request.headers.get("x-forwarded-for")
        if forwarded_for:
            # 取第一个IP（真实的客户端IP）
            return forwarded_for.split(",")[0].strip()

        real_ip = request.headers.get("x-real-ip")
        if real_ip:
            return real_ip.strip()

        # 回退到连接IP
        if hasattr(request, "client") and request.client:
            return request.client.host

        return "unknown"

    async def _check_rate_limit(self, request: Request, client_ip: str) -> bool:
        """检查速率限制"""
        now = time.time()
        current_minute = int(now // 60)

        # 初始化计数器
        if client_ip not in self.request_counts:
            self.request_counts[client_ip] = {}

        minute_counts = self.request_counts[client_ip]

        # 清理旧的分钟数据（保留最近5分钟）
        old_minutes = [m for m in minute_counts.keys() if m < current_minute - 5]
        for old_min in old_minutes:
            del minute_counts[old_min]

        # 更新当前分钟计数
        minute_counts[current_minute] = minute_counts.get(current_minute, 0) + 1

        # 计算最近1分钟的总请求数
        requests_last_minute = sum(
            count
            for min_key, count in minute_counts.items()
            if min_key >= current_minute - 1
        )

        # 检查分钟级限制
        if requests_last_minute > self.rate_limits["requests_per_minute"]:
            return True

        # 检查小时级限制
        if hasattr(request, "hour_counts"):
            current_hour = int(now // 3600)
            if request.hour_counts != current_hour:
                request.hour_counts = current_hour
                request.hour_requests = 1
            else:
                request.hour_requests += 1

            if request.hour_requests > self.rate_limits["requests_per_hour"]:
                return True

        return False

    async def _analyze_request(
        self, request: Request, response: Response, client_ip: str, start_time: float
    ):
        """分析请求安全性"""
        try:
            # 获取请求信息
            request_path = str(request.url.path)
            request_method = request.method
            user_agent = request.headers.get("user-agent", "")

            # 获取响应信息
            status_code = (
                response.status_code if hasattr(response, "status_code") else 200
            )
            response_time = (time.time() - start_time) * 1000  # 毫秒

            # 检测认证失败
            if status_code == 401:
                await self._handle_auth_failure(request, client_ip)

            # 检测权限不足
            elif status_code == 403:
                await self._handle_unauthorized_access(request, client_ip)

            # 检测可疑响应（如500错误）
            elif status_code >= 500:
                await self._handle_server_error(request, client_ip, status_code)

            # 通用请求安全分析
            request_data = await self._get_request_data(request)
            headers = dict(request.headers)

            # 提取用户信息（如果可用）
            user_id = await self._extract_user_id(request)

            # 执行安全分析
            security_events = await self.monitor.analyze_request_security(
                source_ip=client_ip,
                request_path=request_path,
                request_method=request_method,
                user_agent=user_agent,
                request_data=request_data,
                headers=headers,
                user_id=user_id,
            )

            # 处理检测到的安全事件
            if security_events and self.enable_automation:
                await self._process_security_events(security_events, request)

            # 记录异常响应时间
            if response_time > 5000:  # 超过5秒
                await self._monitor.log_security_event(
                    SecurityEventType.UNUSUAL_TRAFFIC,
                    client_ip,
                    request_path,
                    request_method,
                    user_agent,
                    user_id,
                    description=f"异常响应时间: {response_time:.0f}ms",
                    metadata={
                        "response_time_ms": response_time,
                        "status_code": status_code,
                    },
                )

        except Exception as e:
            logger.error(f"请求安全分析失败: {e}")

    async def _get_request_data(self, request: Request) -> str | None:
        """获取请求数据"""
        try:
            if request.method in ["POST", "PUT", "PATCH"]:
                # 对于大的请求体，只读取前1KB
                body = await request.body()
                if len(body) > 1024:
                    return body[:1024].decode("utf-8", errors="ignore")
                return body.decode("utf-8", errors="ignore")
        except Exception:
            pass
        return None

    async def _extract_user_id(self, request: Request) -> str | None:
        """提取用户ID"""
        try:
            # 从请求头中获取用户信息
            user_id = request.headers.get("x-user-id")
            if user_id:
                return user_id

            # 从查询参数中获取用户信息
            if hasattr(request, "query_params"):
                user_id = request.query_params.get("user_id")
                if user_id:
                    return user_id

            # 从JWT token中提取用户信息（如果有认证中间件）
            auth_header = request.headers.get("authorization")
            if auth_header and auth_header.startswith("Bearer "):
                # 这里应该解析JWT token，简化实现
                pass

        except Exception:
            pass
        return None

    async def _handle_auth_failure(self, request: Request, client_ip: str):
        """处理认证失败"""
        now = time.time()
        current_minute = int(now // 60)

        # 更新认证失败计数
        if client_ip not in self.auth_failures:
            self.auth_failures[client_ip] = {}

        minute_failures = self.auth_failures[client_ip]
        minute_failures[current_minute] = minute_failures.get(current_minute, 0) + 1

        # 清理旧的失败记录
        old_minutes = [m for m in minute_failures.keys() if m < current_minute - 10]
        for old_min in old_minutes:
            del minute_failures[old_min]

        # 检查是否超过阈值
        total_failures = sum(minute_failures.values())
        if total_failures >= self.rate_limits["failed_auth_per_minute"]:
            await self.monitor.log_security_event(
                SecurityEventType.BRUTE_FORCE,
                client_ip,
                str(request.url.path),
                request.method,
                request.headers.get("user-agent", ""),
                description=f"认证失败次数过多: {total_failures}",
                metadata={"failure_count": total_failures},
            )

    async def _handle_unauthorized_access(self, request: Request, client_ip: str):
        """处理权限不足"""
        await self.monitor.log_security_event(
            SecurityEventType.UNAUTHORIZED_ACCESS,
            client_ip,
            str(request.url.path),
            request.method,
            request.headers.get("user-agent", ""),
            user_id=await self._extract_user_id(request),
            description="访问被拒绝的敏感资源",
            metadata={"path": str(request.url.path)},
        )

    async def _handle_server_error(
        self, request: Request, client_ip: str, status_code: int
    ):
        """处理服务器错误"""
        await self.monitor.log_security_event(
            SecurityEventType.SUSPICIOUS_REQUEST,
            client_ip,
            str(request.url.path),
            request.method,
            request.headers.get("user-agent", ""),
            description=f"服务器错误: HTTP {status_code}",
            metadata={"status_code": status_code},
        )

    async def _handle_blocked_ip(self, request: Request, client_ip: str):
        """处理被阻止的IP"""
        await self.monitor.log_security_event(
            SecurityEventType.SUSPICIOUS_REQUEST,
            client_ip,
            str(request.url.path),
            request.method,
            request.headers.get("user-agent", ""),
            description="被阻止IP尝试访问",
            metadata={"blocked": True},
        )

    async def _handle_rate_limit_exceeded(self, request: Request, client_ip: str):
        """处理速率限制超出"""
        await self.monitor.log_security_event(
            SecurityEventType.RATE_LIMIT_EXCEEDED,
            client_ip,
            str(request.url.path),
            request.method,
            request.headers.get("user-agent", ""),
            description="超出速率限制",
            metadata={"rate_limit_exceeded": True},
        )

    async def _handle_http_exception(
        self, request: Request, exception: HTTPException, client_ip: str
    ):
        """处理HTTP异常"""
        await self.monitor.log_security_event(
            SecurityEventType.SUSPICIOUS_REQUEST,
            client_ip,
            str(request.url.path),
            request.method,
            request.headers.get("user-agent", ""),
            description=f"HTTP异常: {exception.status_code} - {exception.detail}",
            metadata={
                "exception_type": "HTTPException",
                "status_code": exception.status_code,
                "detail": str(exception.detail),
            },
        )

    async def _handle_unexpected_exception(
        self, request: Request, exception: Exception, client_ip: str
    ):
        """处理未预期异常"""
        await self.monitor.log_security_event(
            SecurityEventType.SUSPICIOUS_REQUEST,
            client_ip,
            str(request.url.path),
            request.method,
            request.headers.get("user-agent", ""),
            description=f"未预期异常: {type(exception).__name__}",
            metadata={
                "exception_type": type(exception).__name__,
                "exception_message": str(exception),
            },
        )

    async def _process_security_events(self, events: list, request: Request):
        """处理检测到的安全事件"""
        for event in events:
            # 自动化响应
            try:
                await self.automation_engine.process_security_event(event)
            except Exception as e:
                logger.error(f"安全事件自动化处理失败: {e}")

    def _create_blocked_response(self) -> JSONResponse:
        """创建IP被阻止的响应"""
        return JSONResponse(
            status_code=403,
            content={
                "error": "Access Denied",
                "message": "您的IP地址已被阻止访问此服务",
                "code": "IP_BLOCKED",
            },
        )

    def _create_rate_limit_response(self) -> JSONResponse:
        """创建速率限制的响应"""
        return JSONResponse(
            status_code=429,
            content={
                "error": "Rate Limit Exceeded",
                "message": "您的请求频率过高，请稍后重试",
                "code": "RATE_LIMITED",
            },
            headers={"Retry-After": "60"},  # 建议60秒后重试
        )


class AdminSecurityMiddleware(SecurityMiddleware):
    """管理员安全中间件（更严格的安全策略）"""

    def __init__(self, app, **kwargs):
        # 使用更严格的默认配置
        admin_config = {
            "requests_per_minute": kwargs.get("requests_per_minute", 50),
            "requests_per_hour": kwargs.get("requests_per_hour", 500),
            "failed_auth_per_minute": kwargs.get("failed_auth_per_minute", 5),
            "suspicious_per_minute": kwargs.get("suspicious_per_minute", 3),
            "enable_ip_blocking": True,
            "enable_rate_limiting": True,
            "enable_request_analysis": True,
            "enable_automation": True,
        }

        super().__init__(app, **admin_config)

    async def _analyze_request(
        self, request: Request, response: Response, client_ip: str, start_time: float
    ):
        """管理员请求的额外安全分析"""
        # 执行基础分析
        await super()._analyze_request(request, response, client_ip, start_time)

        # 管理员特定检查
        request_path = str(request.url.path)

        # 检查敏感的管理操作
        sensitive_operations = [
            "/admin/delete",
            "/admin/drop",
            "/admin/reset",
            "/admin/backup-delete",
            "/admin/system-",
        ]

        for sensitive_op in sensitive_operations:
            if sensitive_op in request_path:
                await self.monitor.log_security_event(
                    SecurityEventType.SUSPICIOUS_REQUEST,
                    client_ip,
                    request_path,
                    request.method,
                    request.headers.get("user-agent", ""),
                    user_id=await self._extract_user_id(request),
                    description="访问敏感管理操作",
                    metadata={"sensitive_operation": sensitive_op},
                )
                break


# 便捷函数
def add_security_middleware(app, admin_routes: bool = False, **config):
    """添加安全中间件到FastAPI应用"""
    if admin_routes:
        # 为管理员路由使用更严格的中间件
        app.add_middleware(AdminSecurityMiddleware, **config)
    else:
        # 为普通路由使用标准中间件
        app.add_middleware(SecurityMiddleware, **config)


async def initialize_security_system(**config):
    """初始化安全系统"""
    # 初始化安全监控
    monitor = get_security_monitor()
    await monitor.start_monitoring()

    # 初始化自动化引擎
    automation_engine = get_automation_engine()
    await automation_engine.start_automation()

    logger.info("✅ 安全系统初始化完成")
    return monitor, automation_engine


if __name__ == "__main__":
    import uvicorn
    from fastapi import FastAPI

    # 创建应用
    app = FastAPI()

    # 添加安全中间件
    add_security_middleware(
        app,
        enable_ip_blocking=True,
        enable_rate_limiting=True,
        requests_per_minute=100,
        failed_auth_per_minute=10,
    )

    @app.get("/")
    async def root():
        return {"message": "Hello World"}

    @app.get("/admin/test")
    async def admin_test():
        return {"message": "Admin test"}

    # 启动服务
    uvicorn.run(app, host="0.0.0.0", port=8000)
