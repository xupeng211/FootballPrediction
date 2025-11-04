"""
增强版JWT认证依赖注入
Enhanced JWT Authentication Dependencies

提供完整的JWT认证、权限控制和速率限制功能
"""

import logging

from fastapi import Depends, HTTPException, Request, Security, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from src.security.jwt_auth import JWTAuthManager, TokenData, get_jwt_auth_manager

logger = logging.getLogger(__name__)

# HTTP Bearer认证方案
security = HTTPBearer(auto_error=False)


async def get_current_user_optional(
    credentials: HTTPAuthorizationCredentials | None = Security(security),
    auth_manager: JWTAuthManager = Depends(get_jwt_auth_manager),
) -> TokenData | None:
    """
    获取当前用户（可选认证）

    Args:
        credentials: HTTP认证凭据
        auth_manager: JWT认证管理器

    Returns:
        用户token数据或None
    """
    if not credentials:
        return None

    try:
        token_data = await auth_manager.verify_token(credentials.credentials)
        if token_data.token_type != "access":
            return None
        return token_data
    except ValueError as e:
        logger.warning(f"Token验证失败: {e}")
        return None


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Security(security),
    auth_manager: JWTAuthManager = Depends(get_jwt_auth_manager),
) -> TokenData:
    """
    获取当前用户（必需认证）

    Args:
        credentials: HTTP认证凭据
        auth_manager: JWT认证管理器

    Returns:
        用户token数据

    Raises:
        HTTPException: 认证失败
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="无法验证凭据",
        headers={"WWW-Authenticate": "Bearer"},
    )

    if not credentials:
        raise credentials_exception

    try:
        token_data = await auth_manager.verify_token(credentials.credentials)

        # 检查token类型
        if token_data.token_type != "access":
            raise credentials_exception

        # TODO: 从数据库验证用户状态
        # user = await get_user_by_id(token_data.user_id)
        # if not user or not user.is_active:
        #     raise credentials_exception

        return token_data

    except ValueError as e:
        logger.warning(f"Token验证失败: {e}")
        raise credentials_exception


async def get_current_active_user(
    current_user: TokenData = Depends(get_current_user),
) -> TokenData:
    """
    获取当前活跃用户

    Args:
        current_user: 当前用户token数据

    Returns:
        活跃用户token数据

    Raises:
        HTTPException: 用户不活跃
    """
    # TODO: 从数据库验证用户状态
    # user = await get_user_by_id(current_user.user_id)
    # if not user.is_active:
    #     raise HTTPException(
    #         status_code=status.HTTP_400_BAD_REQUEST,
    #         detail="用户已被禁用"
    #     )
    return current_user


# 常用角色权限检查函数将在后面定义


class RateLimiter:
    """简单的速率限制器"""

    def __init__(self, max_requests: int = 100, window_seconds: int = 3600):  # TODO: 将魔法数字 100 提取为常量
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self.requests = []

    async def is_allowed(self, identifier: str) -> bool:
        """检查是否允许请求"""
        import time
        current_time = time.time()

        # 清理过期的请求记录
        self.requests = [
            req_time for req_time in self.requests
            if current_time - req_time < self.window_seconds
        ]

        # 检查是否超过限制
        if len(self.requests) >= self.max_requests:
            return False

        # 添加当前请求
        self.requests.append(current_time)
        return True

# 全局速率限制器实例
login_rate_limiter = RateLimiter(
    max_requests=5, window_seconds=900  # 15分钟5次登录尝试
)
api_rate_limiter = RateLimiter(
    max_requests=1000, window_seconds=3600  # 1小时1000次API请求
)


async def rate_limit_login(
    user_identifier: str,
    rate_limiter: RateLimiter = Depends(lambda: login_rate_limiter),
) -> None:
    """
    登录速率限制

    Args:
        user_identifier: 用户标识符（用户名或IP）
        rate_limiter: 速率限制器

    Raises:
        HTTPException: 超过速率限制
    """
    if not await rate_limiter.is_allowed(user_identifier):
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="登录尝试过于频繁，请稍后再试",
        )


async def rate_limit_api(
    current_user: TokenData = Depends(get_current_user),
    rate_limiter: RateLimiter = Depends(lambda: api_rate_limiter),
) -> None:
    """
    API速率限制

    Args:
        current_user: 当前用户
        rate_limiter: 速率限制器

    Raises:
        HTTPException: 超过速率限制
    """
    if not await rate_limiter.is_allowed(str(current_user.user_id)):
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="API请求过于频繁，请稍后再试",
        )


class SecurityHeaders:
    """安全头部配置"""

    @staticmethod
    async def add_security_headers() -> dict[str, str]:
        """添加安全头部的中间件依赖"""
        return SecurityHeaders.get_security_headers()

    @staticmethod
    def get_security_headers() -> dict[str, str]:
        """获取安全头部配置"""
        return {
            "X-Content-Type-Options": "nosniff",
            "X-Frame-Options": "DENY",
            "X-XSS-Protection": "1; mode=block",
            "Referrer-Policy": "strict-origin-when-cross-origin",
            "Content-Security-Policy": (
                "default-src 'self'; "
                "script-src 'self' 'unsafe-inline' 'unsafe-eval'; "
                "style-src 'self' 'unsafe-inline'; "
                "img-src 'self' data: https:; "
                "font-src 'self' https:; "
                "connect-src 'self' https:; "
                "frame-ancestors 'none';"
            ),
            "Strict-Transport-Security": "max-age=31536000; includeSubDomains; preload",  # TODO: 将魔法数字 31536000 提取为常量
        }


class AuthContext:
    """认证上下文管理器"""

    def __init__(self, auth_manager: JWTAuthManager):
        self.auth_manager = auth_manager


def require_roles(*allowed_roles: str):  # TODO: 添加返回类型注解  # TODO: 添加返回类型注解  # TODO: 添加返回类型注解  # TODO: 添加返回类型注解  # TODO: 添加返回类型注解
    """
    角色权限装饰器工厂

    Args:
        allowed_roles: 允许的角色列表

    Returns:
        权限检查依赖函数
    """
    async def role_checker(
        current_user: TokenData = Depends(get_current_active_user),
    ) -> TokenData:
        if current_user.role not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN, detail="权限不足"
            )
        return current_user

    return role_checker


# 常用角色权限检查函数
def require_admin():  # TODO: 添加返回类型注解  # TODO: 添加返回类型注解  # TODO: 添加返回类型注解  # TODO: 添加返回类型注解  # TODO: 添加返回类型注解
    """要求管理员权限"""
    return require_roles("admin")


def require_user():  # TODO: 添加返回类型注解  # TODO: 添加返回类型注解  # TODO: 添加返回类型注解  # TODO: 添加返回类型注解  # TODO: 添加返回类型注解
    """要求用户权限"""
    return require_roles("admin", "user")


def require_guest():  # TODO: 添加返回类型注解  # TODO: 添加返回类型注解  # TODO: 添加返回类型注解  # TODO: 添加返回类型注解  # TODO: 添加返回类型注解
    """要求访客权限"""
    return require_roles("admin", "user", "guest")


# 便捷的权限检查依赖
async def get_current_admin(
    current_user: TokenData = Depends(get_current_active_user),
) -> TokenData:
    """获取当前管理员用户"""
    if current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="需要管理员权限"
        )
    return current_user


# 会话管理工具类
class SessionManager:
    """用户会话管理器"""

    def __init__(self, auth_manager: JWTAuthManager):
        self.auth_manager = auth_manager

    async def logout_user(self, token_data: TokenData) -> None:
        """
        用户登出，将token加入黑名单

        Args:
            token_data: 用户token数据
        """
        await self.auth_manager.blacklist_token(jti=token_data.jti, exp=token_data.exp)
        logger.info(f"用户 {token_data.username} 已登出")

    async def logout_all_sessions(self, user_id: int) -> None:
        """
        登出用户的所有会话

        Args:
            user_id: 用户ID
        """
        # TODO: 实现清除用户所有token的逻辑
        # 可以通过数据库记录token或使用Redis模式
        logger.info(f"用户 {user_id} 的所有会话已清除")


# 全局会话管理器实例
_session_manager: SessionManager | None = None


def get_session_manager() -> SessionManager:
    """获取全局会话管理器"""
    global _session_manager
    if _session_manager is None:
        auth_manager = get_jwt_auth_manager()
        _session_manager = SessionManager(auth_manager)
    return _session_manager


# 安全相关常量
MAX_AGE_ONE_YEAR = 31536000  # 一年的秒数


class AuthContext:
    """认证上下文管理器"""

    @staticmethod
    def get_client_ip(request: Request) -> str:
        """
        获取客户端IP地址

        Args:
        request: FastAPI请求对象

    Returns:
        客户端IP地址
        """
        # 检查代理头
        forwarded_for = request.headers.get("x-forwarded-for")
        if forwarded_for:
            return forwarded_for.split(",")[0].strip()

        real_ip = request.headers.get("x-real-ip")
        if real_ip:
            return real_ip

        # 回退到直接连接IP
        return request.client.host if request.client else "unknown"


# 全局get_client_ip函数，重定向到类的静态方法
def get_client_ip(request: Request) -> str:
    """获取客户端IP地址的便捷函数"""
    return AuthContext.get_client_ip(request)


async def get_auth_context(
    request: Request,
    credentials: HTTPAuthorizationCredentials | None = Security(security)
) -> dict:
    """
    获取认证上下文信息

    Args:
        request: FastAPI请求对象
        credentials: HTTP认证凭据

    Returns:
        包含认证上下文信息的字典
    """
    context = {
        "ip_address": get_client_ip(request),
        "user_agent": request.headers.get("user-agent", "unknown"),
        "is_authenticated": False,
        "user_id": None,
        "username": None,
        "permissions": []
    }

    if credentials:
        try:
            jwt_manager = get_jwt_auth_manager()
            token_data = jwt_manager.verify_token(credentials.credentials)
            context.update({
                "is_authenticated": True,
                "user_id": token_data.user_id,
                "username": token_data.username,
                "permissions": token_data.permissions or []
            })
        except Exception:
            pass  # 保持未认证状态

    return context
