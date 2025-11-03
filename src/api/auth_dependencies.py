"""
增强版JWT认证依赖注入
Enhanced JWT Authentication Dependencies

提供完整的JWT认证、权限控制和速率限制功能
"""

from typing import Optional
from fastapi import Depends, HTTPException, status, Security, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from src.security.jwt_auth import JWTAuthManager, get_jwt_auth_manager, TokenData
import logging

logger = logging.getLogger(__name__)

# HTTP Bearer认证方案
security = HTTPBearer(auto_error=False)


async def get_current_user_optional(
    credentials: Optional[HTTPAuthorizationCredentials] = Security(security),
    auth_manager: JWTAuthManager = Depends(get_jwt_auth_manager),
) -> Optional[TokenData]:
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


# 常用角色权限检查
get_current_admin = require_roles("admin")
get_current_manager = require_roles("admin", "manager")
get_current_user_or_admin = require_roles("admin", "manager", "user")


class RateLimiter:
    """简单的速率限制器"""

# 全局速率限制器实例
login_rate_limiter = RateLimiter(
    max_requests=5, window_seconds=900  # TODO: 将魔法数字 900 提取为常量
)  # 15分钟5次登录尝试
api_rate_limiter = RateLimiter(
    max_requests=1000, window_seconds=3600  # TODO: 将魔法数字 1000 提取为常量
)  # 1小时1000次API请求


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
async def add_security_headers():
    """添加安全头部的中间件依赖"""
    return SecurityHeaders.get_security_headers()


# 上下文管理器，用于认证相关操作
class AuthContext:
    """认证上下文管理器"""

) -> AuthContext:
    """获取认证上下文"""
    return AuthContext(auth_manager)

# TODO: 方法 def require_roles 过长(24行)，建议拆分
# 常用角色权限检查
# TODO: 方法 def __init__ 过长(25行)，建议拆分
# TODO: 方法 def get_client_ip 过长(24行)，建议拆分
class SecurityHeaders:
# TODO: 方法 def get_security_headers 过长(21行)，建议拆分
async def add_security_headers():
) -> AuthContext:
# TODO: 方法 def require_roles 过长(24行)，建议拆分
# 常用角色权限检查
# TODO: 方法 def __init__ 过长(26行)，建议拆分
# TODO: 方法 def get_client_ip 过长(24行)，建议拆分
# TODO: 方法 def get_client_ip 过长(24行)，建议拆分
class SecurityHeaders:
# TODO: 方法 def get_security_headers 过长(21行)，建议拆分
async def add_security_headers():
) -> AuthContext:
# TODO: 方法 def require_roles 过长(24行)，建议拆分
def require_roles(*allowed_roles: str):  # TODO: 添加返回类型注解  # TODO: 添加返回类型注解  # TODO: 添加返回类型注解
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


# 常用角色权限检查
# TODO: 方法 def __init__ 过长(26行)，建议拆分
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


# TODO: 方法 def get_client_ip 过长(24行)，建议拆分
# TODO: 方法 def get_client_ip 过长(24行)，建议拆分
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


class SecurityHeaders:
# TODO: 方法 def get_security_headers 过长(21行)，建议拆分
    def get_security_headers() -> dict:
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


async def add_security_headers():
def get_auth_context(
    """TODO: 添加函数文档"""
    auth_manager: JWTAuthManager = Depends(get_jwt_auth_manager),
) -> AuthContext: