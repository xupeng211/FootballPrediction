"""用户认证API的依赖项.

提供获取当前用户,认证服务等依赖函数
"""

from fastapi import Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.auth.oauth2_scheme import oauth2_scheme
from src.database.connection import get_async_session
from src.database.models.user import User
from src.services.auth_service import AuthService


async def get_auth_service(
    db: AsyncSession = Depends(get_async_session),
) -> AuthService:
    """获取认证服务实例."""
    return AuthService(db)


async def get_current_user(
    token: str = Depends(oauth2_scheme),
    auth_service: AuthService = Depends(get_auth_service),
) -> User:
    """获取当前登录用户.

    Args:
        token: JWT访问令牌
        auth_service: 认证服务

    Returns:
        User: 当前用户对象

    Raises:
        HTTPException: 令牌无效或用户不存在
    """
    user = await auth_service.get_current_user(token)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="无效的认证令牌",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return user


async def get_current_active_user(
    current_user: User = Depends(get_current_user),
) -> User:
    """获取当前活跃用户.

    Args:
        current_user: 当前用户

    Returns:
        User: 当前活跃用户

    Raises:
        HTTPException: 用户未激活
    """
    if not current_user.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="用户账户已被禁用"
        )
    return current_user


async def get_current_verified_user(
    current_user: User = Depends(get_current_active_user),
) -> User:
    """获取当前已验证用户.

    Args:
        current_user: 当前活跃用户

    Returns:
        User: 当前已验证用户

    Raises:
        HTTPException: 用户未验证邮箱
    """
    if not current_user.is_verified:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="请先验证您的邮箱地址"
        )
    return current_user


async def get_current_admin_user(
    current_user: User = Depends(get_current_active_user),
) -> User:
    """获取当前管理员用户.

    Args:
        current_user: 当前活跃用户

    Returns:
        User: 当前管理员用户

    Raises:
        HTTPException: 用户不是管理员
    """
    if not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="权限不足,需要管理员权限"
        )
    return current_user


async def get_current_premium_user(
    current_user: User = Depends(get_current_active_user),
) -> User:
    """获取当前高级用户.

    Args:
        current_user: 当前活跃用户

    Returns:
        User: 当前高级用户

    Raises:
        HTTPException: 用户不是高级用户
    """
    if not current_user.is_premium:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="此功能需要高级用户权限"
        )
    return current_user


def require_permissions(required_roles: list | None = None):
    """函数文档字符串."""
    pass  # 添加pass语句
    """
    权限装饰器工厂函数

    Args:
        required_roles: 需要的角色列表

    Returns:
        依赖函数
    """

    async def permission_dependency(
        current_user: User = Depends(get_current_active_user),
    ) -> User:
        if required_roles and current_user.role not in required_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"权限不足,需要以下角色之一: {', '.join(required_roles)}",
            )
        return current_user

    return permission_dependency


# 预定义的权限依赖
RequireAdmin = require_permissions(["admin"])
RequirePremiumOrAdmin = require_permissions(["premium", "admin", "analyst"])
RequireAnalystOrAdmin = require_permissions(["analyst", "admin"])


class OptionalAuth:
    """类文档字符串."""

    pass  # 添加pass语句
    """
    可选认证依赖类

    用于不强制要求用户登录的端点
    """

    def __init__(self):
        """函数文档字符串."""
        # 添加pass语句

    async def __call__(
        self,
        token: str | None = Depends(oauth2_scheme),
        auth_service: AuthService = Depends(get_auth_service),
    ) -> User | None:
        """可选获取当前用户.

        Args:
            token: JWT访问令牌（可选）
            auth_service: 认证服务

        Returns:
            Optional[User]: 当前用户对象,如果未登录则返回None
        """
        if not token:
            return None

        try:
            user = await auth_service.get_current_user(token)
            return user
        except HTTPException:
            return None


# 创建可选认证依赖实例
optional_auth = OptionalAuth()
