from typing import Any

from fastapi import FastAPI, HTTPException, Request, status
from fastapi.responses import JSONResponse

from .auth.enhanced_router import router as auth_router
from .auth.enhanced_security import EnhancedSecurity, Permission
from .middleware.enhanced_security import configure_cors, configure_security_middleware
from .validation.input_validators import comprehensive_security_check

"""
API安全系统集成
API Security Integration

将所有安全组件整合到FastAPI应用中。
"""


def setup_enhanced_security(app: FastAPI) -> None:
    """
    设置增强的安全系统

    包括CORS、安全中间件、认证路由等。
    """
    # 1. 配置CORS
    configure_cors(app)

    # 2. 配置安全中间件
    configure_security_middleware(app)

    # 3. 注册认证路由
    app.include_router(auth_router)

    # 4. 添加全局异常处理
    setup_global_exception_handlers(app)

    # 5. 添加请求验证中间件
    app.middleware("http")(security_validation_middleware)


def setup_global_exception_handlers(app: FastAPI) -> None:
    """设置全局异常处理器"""

    @app.exception_handler(HTTPException)
    async def http_exception_handler(
        request: Request, exc: HTTPException
    ) -> JSONResponse:
        """HTTP异常处理"""
        return JSONResponse(
            status_code=exc.status_code,
            content={
                "error": True,
                "message": exc.detail,
                "status_code": exc.status_code,
                "path": str(request.url),
                "timestamp": "2025-11-07T21:58:00Z",  # 可以使用实际时间戳
            },
        )

    @app.exception_handler(Exception)
    async def general_exception_handler(
        request: Request, exc: Exception
    ) -> JSONResponse:
        """通用异常处理"""
        # 在生产环境中不应该暴露详细错误信息
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "error": True,
                "message": "内部服务器错误",
                "status_code": 500,
                "path": str(request.url),
            },
        )


async def security_validation_middleware(request: Request, call_next) -> Any:
    """安全验证中间件"""
    # 对POST/PUT/DELETE请求进行安全检查
    if request.method in ["POST", "PUT", "DELETE", "PATCH"]:
        try:
            # 获取请求体（仅对JSON请求）
            if request.headers.get("content-type", "").startswith("application/json"):
                body = await request.body()
                if body:
                    import json

                    try:
                        data = json.loads(body.decode())
                        # 进行安全检查
                        security_result = comprehensive_security_check(
                            data, "api_request"
                        )

                        if not security_result["is_safe"]:
                            return JSONResponse(
                                status_code=status.HTTP_400_BAD_REQUEST,
                                content={
                                    "error": True,
                                    "message": "检测到安全问题",
                                    "issues": security_result["issues"],
                                },
                            )
                    except (json.JSONDecodeError, UnicodeDecodeError):
                        # JSON解析错误，继续处理
                        pass
        except Exception:
            # 中间件错误不应该阻止请求处理
            pass

    response = await call_next(request)
    return response


RequireRead = EnhancedSecurity([Permission.READ])
RequireWrite = EnhancedSecurity([Permission.WRITE])
RequirePredict = EnhancedSecurity([Permission.PREDICT])
RequireAdmin = EnhancedSecurity([Permission.ADMIN])
RequireReadWrite = EnhancedSecurity([Permission.READ, Permission.WRITE])
RequireAll = EnhancedSecurity(
    [Permission.READ, Permission.WRITE, Permission.ADMIN, Permission.PREDICT]
)
SECURITY_FEATURES = {
    "jwt_authentication": True,
    "password_encryption": True,
    "rate_limiting": True,
    "permission_control": True,
    "input_validation": True,
    "cors_protection": True,
    "security_headers": True,
    "csrf_protection": False,  # 可选启用
    "ip_whitelist": False,  # 可选启用
}
SECURITY_ENDPOINTS = {
    "login": "/auth/login",
    "refresh": "/auth/refresh",
    "logout": "/auth/logout",
    "me": "/auth/me",
    "change_password": "/auth/change-password",
    "verify_token": "/auth/verify-token",
    "health": "/auth/health",
}


def get_security_info() -> dict[str, Any]:
    """获取安全系统信息"""
    return {
        "version": "2.0.0",
        "features": SECURITY_FEATURES,
        "endpoints": SECURITY_ENDPOINTS,
        "permissions": {
            "read": Permission.READ,
            "write": Permission.WRITE,
            "admin": Permission.ADMIN,
            "predict": Permission.PREDICT,
        },
    }
