"""
认证API端点
Authentication API Endpoints

提供用户登录、注册、token刷新等认证相关API
"""

from datetime import timedelta
from typing import Any
from fastapi import APIRouter, Depends, HTTPException, status, Request
from fastapi.security import OAuth2PasswordRequestForm
from pydantic import BaseModel, EmailStr, Field
import logging

from src.security.jwt_auth import JWTAuthManager, get_jwt_auth_manager, UserAuth
from src.api.auth_dependencies import (
    get_current_user,
    get_current_active_user,
    rate_limit_login,
    get_client_ip,
    AuthContext,
    get_auth_context,
)

logger = logging.getLogger(__name__)

# 创建认证路由器
router = APIRouter(prefix="/auth", tags=["认证"])


# Pydantic模型定义
class UserRegister(BaseModel):
    """用户注册请求"""

    username: str = Field(..., min_length=3, max_length=50, description="用户名")
    email: EmailStr = Field(..., description="邮箱地址")
    password: str = Field(..., min_length=8, max_length=128, description="密码")
    full_name: Optional[str] = Field(None, max_length=100, description="全名")


class UserLogin(BaseModel):
    """用户登录请求"""

    username: str = Field(..., description="用户名或邮箱")
    password: str = Field(..., description="密码")
    remember_me: bool = Field(False, description="记住我")


class TokenResponse(BaseModel):
    """Token响应"""

    access_token: str = Field(..., description="访问令牌")
    refresh_token: str = Field(..., description="刷新令牌")
    token_type: str = Field("bearer", description="令牌类型")
    expires_in: int = Field(..., description="过期时间（秒）")
    user_info: dict = Field(..., description="用户信息")


class RefreshTokenRequest(BaseModel):
    """刷新令牌请求"""

    refresh_token: str = Field(..., description="刷新令牌")


class PasswordChangeRequest(BaseModel):
    """修改密码请求"""

    current_password: str = Field(..., description="当前密码")
    new_password: str = Field(..., min_length=8, max_length=128, description="新密码")


class PasswordResetRequest(BaseModel):
    """密码重置请求"""

    email: EmailStr = Field(..., description="邮箱地址")


class PasswordResetConfirm(BaseModel):
    """确认密码重置"""

    token: str = Field(..., description="重置令牌")
    new_password: str = Field(..., min_length=8, max_length=128, description="新密码")


class UserResponse(BaseModel):
    """用户信息响应"""

    id: int
    username: str
    email: str
    full_name: Optional[str]
    role: str
    is_active: bool
    created_at: str


# 模拟用户数据库（生产环境应该使用真实数据库）
MOCK_USERS = {
    1: UserAuth(
        id=1,
        username="admin",
        email="admin@football-prediction.com",
        hashed_password="$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LewdBPj3bp.Gm.F5G",  # admin123
        role="admin",
        is_active=True,
    ),
    2: UserAuth(
        id=2,
        username="user",
        email="user@football-prediction.com",
        hashed_password="$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LewdBPj3bp.Gm.F5G",  # user123
        role="user",
        is_active=True,
    ),
}


async def authenticate_user(
    username: str, password: str, auth_manager: JWTAuthManager
) -> UserAuth:
    """
    验证用户凭据

    Args:
        username: 用户名或邮箱
        password: 密码
        auth_manager: JWT认证管理器

    Returns:
        用户信息或None
    """
    # 在真实应用中，这里应该查询数据库
    user = None
    for mock_user in MOCK_USERS.values():
        if mock_user.username == username or mock_user.email == username:
            user = mock_user
            break

    if not user:
        return None

    if not auth_manager.verify_password(password, user.hashed_password):
        return None

    return user


async def get_user_by_id(user_id: int) -> UserAuth:
    """根据ID获取用户"""
    return MOCK_USERS.get(user_id)


async def create_user(
    user_data: UserRegister, auth_manager: JWTAuthManager
) -> UserAuth:
    """
    创建新用户

    Args:
        user_data: 用户注册数据
        auth_manager: JWT认证管理器

    Returns:
        新创建的用户信息
    """
    # 验证密码强度
    is_valid, errors = auth_manager.validate_password_strength(user_data.password)
    if not is_valid:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"密码不符合要求: {'; '.join(errors)}",
        )

    # 检查用户名和邮箱是否已存在
    for existing_user in MOCK_USERS.values():
        if existing_user.username == user_data.username:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail="用户名已存在"
            )
        if existing_user.email == user_data.email:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail="邮箱已被注册"
            )

    # 创建新用户（在真实应用中应该保存到数据库）
    new_user_id = max(MOCK_USERS.keys()) + 1
    new_user = UserAuth(
        id=new_user_id,
        username=user_data.username,
        email=user_data.email,
        hashed_password=auth_manager.hash_password(user_data.password),
        role="user",
        is_active=True,
    )

    MOCK_USERS[new_user_id] = new_user
    logger.info(f"新用户注册成功: {user_data.username}")

    return new_user


@router.post(
    "/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED
)
async def register(
    user_data: UserRegister,
    request: Request,
    auth_manager: JWTAuthManager = Depends(get_jwt_auth_manager),
):
    """
    用户注册
    """
    client_ip = get_client_ip(request)
    logger.info(f"用户注册请求: {user_data.username} from {client_ip}")

    # 创建用户
    user = await create_user(user_data, auth_manager)

    return UserResponse(
        id=user.id,
        username=user.username,
        email=user.email,
        full_name=None,
        role=user.role,
        is_active=user.is_active,
        created_at="2025-10-31T00:00:00Z",  # 在真实应用中应该是实际创建时间
    )


@router.post("/login", response_model=TokenResponse)
async def login(
    user_data: UserLogin,
    request: Request,
    auth_manager: JWTAuthManager = Depends(get_jwt_auth_manager),
):
    """
    用户登录
    """
    client_ip = get_client_ip(request)
    user_identifier = user_data.username

    # 速率限制检查
    await rate_limit_login(f"{user_identifier}:{client_ip}")

    logger.info(f"用户登录请求: {user_identifier} from {client_ip}")

    # 验证用户凭据
    user = await authenticate_user(user_data.username, user_data.password, auth_manager)
    if not user:
        logger.warning(f"登录失败: {user_identifier} from {client_ip}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="用户名或密码错误",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="用户账户已被禁用"
        )

    # 生成tokens
    access_token_expire = timedelta(minutes=auth_manager.access_token_expire_minutes)
    refresh_token_expire = timedelta(days=auth_manager.refresh_token_expire_days)

    if user_data.remember_me:
        # 记住我选项，延长token有效期
        access_token_expire = timedelta(hours=24)
        refresh_token_expire = timedelta(days=30)

    access_token = auth_manager.create_access_token(
        data={
            "sub": str(user.id),
            "username": user.username,
            "email": user.email,
            "role": user.role,
        },
        expires_delta=access_token_expire,
    )

    refresh_token = auth_manager.create_refresh_token(
        data={"sub": str(user.id)}, expires_delta=refresh_token_expire
    )

    logger.info(f"用户登录成功: {user.username} from {client_ip}")

    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        token_type="bearer",
        expires_in=int(access_token_expire.total_seconds()),
        user_info={
            "id": user.id,
            "username": user.username,
            "email": user.email,
            "role": user.role,
            "full_name": None,  # 可以从数据库获取
        },
    )


@router.post("/refresh", response_model=TokenResponse)
async def refresh_token(
    token_data: RefreshTokenRequest,
    auth_manager: JWTAuthManager = Depends(get_jwt_auth_manager),
):
    """
    刷新访问令牌
    """
    try:
        # 验证刷新令牌
        token_payload = await auth_manager.verify_token(token_data.refresh_token)

        if token_payload.token_type != "refresh":
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED, detail="无效的刷新令牌"
            )

        # 获取用户信息
        user = await get_user_by_id(token_payload.user_id)
        if not user or not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED, detail="用户不存在或已被禁用"
            )

        # 生成新的访问令牌
        access_token_expire = timedelta(
            minutes=auth_manager.access_token_expire_minutes
        )
        new_access_token = auth_manager.create_access_token(
            data={
                "sub": str(user.id),
                "username": user.username,
                "email": user.email,
                "role": user.role,
            },
            expires_delta=access_token_expire,
        )

        # 可选：生成新的刷新令牌
        new_refresh_token = auth_manager.create_refresh_token(
            data={"sub": str(user.id)},
            expires_delta=timedelta(days=auth_manager.refresh_token_expire_days),
        )

        logger.info(f"Token刷新成功: {user.username}")

        return TokenResponse(
            access_token=new_access_token,
            refresh_token=new_refresh_token,
            token_type="bearer",
            expires_in=int(access_token_expire.total_seconds()),
            user_info={
                "id": user.id,
                "username": user.username,
                "email": user.email,
                "role": user.role,
                "full_name": None,
            },
        )

    except ValueError as e:
        logger.warning(f"Token刷新失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail=f"令牌刷新失败: {str(e)}"
        )


@router.post("/logout")
async def logout(
    current_user=Depends(get_current_user),
    auth_context: AuthContext = Depends(get_auth_context),
):
    """
    用户登出
    """
    await auth_context.logout_user(current_user)
    logger.info(f"用户登出: {current_user.username}")

    return {"message": "登出成功"}


@router.get("/me", response_model=UserResponse)
async def get_current_user_info(current_user=Depends(get_current_active_user)):
    """
    获取当前用户信息
    """
    user = await get_user_by_id(current_user.user_id)

    return UserResponse(
        id=user.id,
        username=user.username,
        email=user.email,
        full_name=None,
        role=user.role,
        is_active=user.is_active,
        created_at="2025-10-31T00:00:00Z",
    )


@router.post("/change-password")
async def change_password(
    password_data: PasswordChangeRequest,
    current_user=Depends(get_current_user),
    auth_manager: JWTAuthManager = Depends(get_jwt_auth_manager),
    auth_context: AuthContext = Depends(get_auth_context),
):
    """
    修改密码
    """
    user = await get_user_by_id(current_user.user_id)

    # 验证当前密码
    if not auth_manager.verify_password(
        password_data.current_password, user.hashed_password
    ):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="当前密码错误"
        )

    # 验证新密码强度
    is_valid, errors = auth_manager.validate_password_strength(
        password_data.new_password
    )
    if not is_valid:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"新密码不符合要求: {'; '.join(errors)}",
        )

    # 更新密码（在真实应用中应该更新数据库）
    user.hashed_password = auth_manager.hash_password(password_data.new_password)
    MOCK_USERS[user.id] = user

    # 登出所有会话
    await auth_context.logout_all_sessions(user.id)

    logger.info(f"用户修改密码: {user.username}")

    return {"message": "密码修改成功，请重新登录"}


@router.post("/request-password-reset")
async def request_password_reset(
    request_data: PasswordResetRequest,
    request: Request,
    auth_manager: JWTAuthManager = Depends(get_jwt_auth_manager),
):
    """
    请求密码重置
    """
    client_ip = get_client_ip(request)

    # 查找用户
    user = None
    for mock_user in MOCK_USERS.values():
        if mock_user.email == request_data.email:
            user = mock_user
            break

    if not user:
        # 为了安全，即使用户不存在也返回成功消息
        logger.info(
            f"密码重置请求（用户不存在）: {request_data.email} from {client_ip}"
        )
        return {"message": "如果邮箱存在，重置链接已发送"}

    # 生成重置令牌
    reset_token = auth_manager.generate_password_reset_token(user.email)

    # 在真实应用中，这里应该发送邮件
    logger.info(
        f"密码重置令牌生成: {user.email}, token: {reset_token[:20]}... from {client_ip}"
    )

    return {"message": "密码重置链接已发送到您的邮箱"}


@router.post("/reset-password")
async def reset_password(
    reset_data: PasswordResetConfirm,
    auth_manager: JWTAuthManager = Depends(get_jwt_auth_manager),
):
    """
    确认密码重置
    """
    try:
        # 验证重置令牌
        email = await auth_manager.verify_password_reset_token(reset_data.token)

        # 查找用户
        user = None
        for mock_user in MOCK_USERS.values():
            if mock_user.email == email:
                user = mock_user
                break

        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="用户不存在"
            )

        # 验证新密码强度
        is_valid, errors = auth_manager.validate_password_strength(
            reset_data.new_password
        )
        if not is_valid:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"密码不符合要求: {'; '.join(errors)}",
            )

        # 更新密码
        user.hashed_password = auth_manager.hash_password(reset_data.new_password)
        MOCK_USERS[user.id] = user

        logger.info(f"密码重置成功: {user.email}")

        return {"message": "密码重置成功，请使用新密码登录"}

    except ValueError as e:
        logger.warning(f"密码重置失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=f"重置失败: {str(e)}"
        )


@router.get("/verify-token")
async def verify_token(current_user=Depends(get_current_user)):
    """
    验证token有效性
    """
    return {
        "valid": True,
        "user_id": current_user.user_id,
        "username": current_user.username,
        "role": current_user.role,
        "expires_at": current_user.exp.isoformat(),
    }
