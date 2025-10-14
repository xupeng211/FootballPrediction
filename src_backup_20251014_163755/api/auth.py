"""
认证相关API路由
"""

from datetime import timedelta
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session

from src.api.deps import get_db
from src.domain.user import Token, UserCreate, UserLogin, UserResponse
from src.security.auth import (
    Role,
    get_auth_manager,
    get_user_permissions,
    get_current_user,
)
from src.services.user_service import UserService

router = APIRouter()


@router.post("/register", response_model=UserResponse)
async def register(
    user_data: UserCreate,
    db: Session = Depends(get_db),
) -> Any:
    """用户注册"""
    user_service = UserService(db)

    # 检查用户名是否已存在
    if user_service.get_by_username(user_data.username):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username already registered",
        )

    # 检查邮箱是否已存在
    if user_service.get_by_email(user_data.email):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered",
        )

    # 创建用户
    user = user_service.create(user_data)
    return user


@router.post("/login", response_model=Token)
async def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db),
) -> Any:
    """用户登录"""
    user_service = UserService(db)

    # 验证用户
    user = user_service.authenticate(form_data.username, form_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Inactive user",
        )

    # 更新最后登录时间
    user_service.update_last_login(user.id)

    # 创建token
    auth = get_auth_manager()
    user_roles = user.get_roles()
    user_permissions = get_user_permissions(user_roles)

    access_token = auth.create_access_token(
        data={
            "sub": str(user.id),
            "roles": user_roles,
            "permissions": user_permissions,
        },
        expires_delta=timedelta(minutes=30),
    )

    refresh_token = auth.create_refresh_token(
        data={
            "sub": str(user.id),
            "roles": user_roles,
            "permissions": user_permissions,
        }
    )

    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer",
        "expires_in": 1800,  # 30分钟
    }


@router.post("/refresh", response_model=Token)
async def refresh_token(
    refresh_token: str,
    db: Session = Depends(get_db),
) -> Any:
    """刷新访问令牌"""
    try:
        auth = get_auth_manager()
        payload = auth.verify_token(refresh_token, "refresh")

        user_id = payload.get("sub")
        if user_id is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token",
            )

        # 获取用户信息
        user_service = UserService(db)
        user = user_service.get(int(user_id))
        if not user or not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User not found or inactive",
            )

        # 生成新的访问令牌
        user_roles = user.get_roles()
        user_permissions = get_user_permissions(user_roles)

        new_access_token = auth.create_access_token(
            data={
                "sub": str(user.id),
                "roles": user_roles,
                "permissions": user_permissions,
            },
            expires_delta=timedelta(minutes=30),
        )

        # 生成新的刷新令牌
        new_refresh_token = auth.create_refresh_token(
            data={
                "sub": str(user.id),
                "roles": user_roles,
                "permissions": user_permissions,
            }
        )

        return {
            "access_token": new_access_token,
            "refresh_token": new_refresh_token,
            "token_type": "bearer",
            "expires_in": 1800,
        }

    except Exception:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not refresh token",
        )


@router.get("/me", response_model=UserResponse)
async def get_current_user_info(
    current_user: Dict[str, Any] = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Any:
    """获取当前用户信息"""
    user_service = UserService(db)
    user = user_service.get(int(current_user["user_id"]))
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )
    return user


@router.post("/logout")
async def logout(
    current_user: Dict[str, Any] = Depends(get_current_user),
) -> Any:
    """用户登出"""
    # 这里可以实现token黑名单机制
    # 目前仅返回成功消息
    return {"message": "Successfully logged out"}


@router.post("/change-password")
async def change_password(
    current_password: str,
    new_password: str,
    current_user: Dict[str, Any] = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Any:
    """修改密码"""
    user_service = UserService(db)
    user = user_service.get(int(current_user["user_id"]))

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )

    # 验证当前密码
    auth = get_auth_manager()
    if not auth.verify_password(current_password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Incorrect current password",
        )

    # 更新密码
    user_service.update_password(user.id, new_password)

    return {"message": "Password successfully changed"}
