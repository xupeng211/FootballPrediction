"""
用户认证API路由

提供用户注册、登录、令牌管理等认证相关的API端点
"""

from datetime import timedelta
from typing import Any, Dict

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.auth.models import (
    TokenResponse,
    UserRegisterRequest,
    UserResponse,
    PasswordChangeRequest,
    PasswordResetRequest,
    PasswordResetConfirm,
    MessageResponse,
)
from src.database.models.user import User
from src.database.connection import get_async_session
from src.services.auth_service import AuthService
# 暂时移除监控指标，避免导入问题
# from src.monitoring.metrics_collector import (
#     increase_user_registrations,
#     increase_user_logins,
#     increase_password_changes,
#     increase_password_resets,
# )

router = APIRouter(prefix="/auth", tags=["认证"])
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="api/v1/auth/login")


async def get_auth_service(
    db: AsyncSession = Depends(get_async_session)
) -> AuthService:
    """获取认证服务实例"""
    return AuthService(db)


async def get_current_user(
    token: str = Depends(oauth2_scheme),
    auth_service: AuthService = Depends(get_auth_service)
) -> User:
    """
    获取当前登录用户

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


@router.post(
    "/register",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
    summary="用户注册",
)
async def register(
    user_data: UserRegisterRequest,
    auth_service: AuthService = Depends(get_auth_service),
) -> User:
    """
    用户注册接口

    - **username**: 用户名（唯一）
    - **email**: 邮箱地址（唯一）
    - **password**: 密码
    - **first_name**: 名（可选）
    - **last_name**: 姓（可选）
    """
    try:
        user = await auth_service.register_user(
            username=user_data.username,
            email=user_data.email,
            password=user_data.password,
            first_name=user_data.first_name,
            last_name=user_data.last_name,
        )

        # 记录注册指标 (暂时禁用)
        # increase_user_registrations()

        return user

    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"注册失败: {str(e)}",
        )


@router.post(
    "/login",
    response_model=TokenResponse,
    summary="用户登录",
)
async def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    auth_service: AuthService = Depends(get_auth_service),
) -> Dict[str, Any]:
    """
    用户登录接口

    - **username**: 用户名或邮箱
    - **password**: 密码

    返回JWT访问令牌和刷新令牌
    """
    login_result = await auth_service.login_user(
        username=form_data.username, password=form_data.password
    )

    if not login_result:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="用户名或密码错误",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # 记录登录指标 (暂时禁用)
    # increase_user_logins()

    return login_result


@router.post(
    "/refresh",
    response_model=Dict[str, str],
    summary="刷新访问令牌",
)
async def refresh_token(
    refresh_token: str,
    auth_service: AuthService = Depends(get_auth_service),
) -> Dict[str, str]:
    """
    使用刷新令牌获取新的访问令牌
    """
    access_token = await auth_service.refresh_access_token(refresh_token)

    if not access_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="无效的刷新令牌",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return {"access_token": access_token, "token_type": "bearer"}


@router.get(
    "/me",
    response_model=UserResponse,
    summary="获取当前用户信息",
)
async def get_current_user_info(
    current_user: User = Depends(get_current_user),
) -> User:
    """
    获取当前登录用户的详细信息
    """
    return current_user


@router.put(
    "/me",
    response_model=UserResponse,
    summary="更新当前用户信息",
)
async def update_current_user(
    user_update: Dict[str, Any],
    current_user: User = Depends(get_current_user),
    auth_service: AuthService = Depends(get_auth_service),
) -> User:
    """
    更新当前登录用户的信息
    """
    # 更新允许的字段
    allowed_fields = {
        "first_name", "last_name", "avatar_url", "bio", "preferences"
    }

    update_data = {
        key: value for key, value in user_update.items()
        if key in allowed_fields
    }

    if not update_data:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="没有提供有效的更新字段",
        )

    # 更新用户信息
    for field, value in update_data.items():
        setattr(current_user, field, value)

    updated_user = await auth_service.user_repo.update(current_user)
    return updated_user


@router.post(
    "/change-password",
    response_model=MessageResponse,
    summary="修改密码",
)
async def change_password(
    password_data: PasswordChangeRequest,
    current_user: User = Depends(get_current_user),
    auth_service: AuthService = Depends(get_auth_service),
) -> Dict[str, str]:
    """
    修改当前用户密码

    - **current_password**: 当前密码
    - **new_password**: 新密码
    """
    success = await auth_service.change_password(
        current_user, password_data.current_password, password_data.new_password
    )

    if not success:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="当前密码错误",
        )

    # 记录密码修改指标 (暂时禁用)
    # increase_password_changes()

    return {"message": "密码修改成功"}


@router.post(
    "/reset-password-request",
    response_model=MessageResponse,
    summary="请求密码重置",
)
async def request_password_reset(
    reset_request: PasswordResetRequest,
    auth_service: AuthService = Depends(get_auth_service),
) -> Dict[str, str]:
    """
    请求密码重置，发送重置令牌到用户邮箱

    - **email**: 用户邮箱
    """
    reset_token = await auth_service.reset_password_request(reset_request.email)

    if not reset_token:
        # 为了安全，即使用户不存在也返回成功消息
        return {"message": "如果邮箱存在，重置链接已发送"}

    # 这里应该发送邮件，暂时返回令牌（实际生产中不应该返回）
    # TODO: 集成邮件服务
    print(f"密码重置令牌: {reset_token}")  # 调试用

    # 记录密码重置请求指标 (暂时禁用)
    # increase_password_resets()

    return {"message": "密码重置链接已发送到您的邮箱"}


@router.post(
    "/reset-password",
    response_model=MessageResponse,
    summary="确认密码重置",
)
async def reset_password(
    reset_data: PasswordResetConfirm,
    auth_service: AuthService = Depends(get_auth_service),
) -> Dict[str, str]:
    """
    使用重置令牌设置新密码

    - **token**: 重置令牌
    - **new_password**: 新密码
    """
    success = await auth_service.reset_password(reset_data.token, reset_data.new_password)

    if not success:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="无效或已过期的重置令牌",
        )

    return {"message": "密码重置成功"}


@router.post(
    "/verify-email",
    response_model=MessageResponse,
    summary="验证邮箱",
)
async def verify_email(
    verification_token: str,
    auth_service: AuthService = Depends(get_auth_service),
) -> Dict[str, str]:
    """
    验证用户邮箱

    - **token**: 邮箱验证令牌
    """
    success = await auth_service.verify_email(verification_token)

    if not success:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="无效或已过期的验证令牌",
        )

    return {"message": "邮箱验证成功"}


@router.post(
    "/resend-verification",
    response_model=MessageResponse,
    summary="重新发送验证邮件",
)
async def resend_verification_email(
    current_user: User = Depends(get_current_user),
    auth_service: AuthService = Depends(get_auth_service),
) -> Dict[str, str]:
    """
    为当前用户重新发送邮箱验证邮件
    """
    if current_user.is_verified:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="邮箱已经验证过了",
        )

    verification_token = auth_service.create_email_verification_token(current_user)

    # TODO: 集成邮件服务
    print(f"邮箱验证令牌: {verification_token}")  # 调试用

    return {"message": "验证邮件已发送"}


@router.post(
    "/logout",
    response_model=MessageResponse,
    summary="用户登出",
)
async def logout(
    current_user: User = Depends(get_current_user),
) -> Dict[str, str]:
    """
    用户登出接口

    注意：由于JWT是无状态的，实际的令牌失效需要客户端删除
    这个接口主要用于记录登出事件和清理服务器端状态
    """
    # TODO: 实现令牌黑名单机制（可选）
    return {"message": "登出成功"}


# 导出router供其他模块使用
__all__ = ["router"]