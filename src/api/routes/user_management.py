from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPBearer
from pydantic import BaseModel

from src.api.dependencies import get_current_user, get_user_management_service
from src.core.exceptions import (
    InvalidCredentialsError,
    UserAlreadyExistsError,
    UserNotFoundError,
)
from src.services.user_management_service import (
    UserAuthResponse,
    UserCreateRequest,
    UserResponse,
    UserUpdateRequest,
)

"""
用户管理API路由
User Management API Routes

提供用户管理的REST API端点。
"""

router = APIRouter(prefix="/api/v1/users", tags=["用户管理"])
security = HTTPBearer()


class LoginRequest(BaseModel):
    """登录请求模型"""

    email: str
    password: str


class ChangePasswordRequest(BaseModel):
    """修改密码请求模型"""

    old_password: str
    new_password: str


async def register_user(
    request: UserCreateRequest,
    user_service=Depends(get_user_management_service),
) -> UserResponse:
    """注册新用户"""
    try:
        user = await user_service.create_user(request)
        return user
    except UserAlreadyExistsError as e:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(e)) from e
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)
        ) from e  # TODO: B904 exception chaining


async def login_user(
    request: LoginRequest,
    user_service=Depends(get_user_management_service),
) -> UserAuthResponse:
    """用户登录"""
    try:
        auth_response = await user_service.authenticate_user(
            email=request.email, password=request.password
        )
        return auth_response
    except (UserNotFoundError, InvalidCredentialsError) as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail=str(e)
        ) from e


async def get_current_user_info(
    current_user: dict = Depends(get_current_user),
    user_service=Depends(get_user_management_service),
) -> UserResponse:
    """获取当前用户信息"""
    try:
        user = await user_service.get_user_by_id(current_user["id"])
        return user
    except UserNotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=str(e)
        ) from e  # TODO: B904 exception chaining


async def get_user(
    user_id: int,
    user_service=Depends(get_user_management_service),
) -> UserResponse:
    """获取指定用户信息"""
    try:
        user = await user_service.get_user_by_id(user_id)
        return user
    except UserNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e)) from e


async def update_user(
    user_id: int,
    request: UserUpdateRequest,
    current_user: dict = Depends(get_current_user),
    user_service=Depends(get_user_management_service),
) -> UserResponse:
    """更新用户信息"""
    try:
        # 检查权限：只能更新自己的信息
        if current_user["id"] != user_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="只能更新自己的用户信息",
            )
        user = await user_service.update_user(user_id, request)
        return user
    except UserNotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=str(e)
        ) from e  # TODO: B904 exception chaining
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)
        ) from e


async def delete_user(
    user_id: int,
    current_user: dict = Depends(get_current_user),
    user_service=Depends(get_user_management_service),
):
    """删除用户"""
    try:
        # 检查权限：只能删除自己的账户
        if current_user["id"] != user_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="只能删除自己的账户",
            )
        await user_service.delete_user(user_id)
    except UserNotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=str(e)
        ) from e  # TODO: B904 exception chaining


async def get_users(
    skip: int = 0,
    limit: int = 100,
    active_only: bool = True,
    current_user: dict = Depends(get_current_user),
    user_service=Depends(get_user_management_service),
) -> list[UserResponse]:
    """获取用户列表"""
    # 检查权限：只有管理员可以查看所有用户
    if not current_user.get("is_admin", False):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="只有管理员可以查看用户列表",
        )
    try:
        users = await user_service.get_users(
            skip=skip, limit=limit, active_only=active_only
        )
        return users
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e)
        ) from e


async def search_users(
    query: str,
    limit: int = 20,
    current_user: dict = Depends(get_current_user),
    user_service=Depends(get_user_management_service),
) -> list[UserResponse]:
    """搜索用户"""
    # 检查权限
    if not current_user.get("is_admin", False):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="只有管理员可以搜索用户",
        )
    try:
        users = await user_service.search_users(query, limit)
        return users
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e)
        ) from e


async def change_password(
    request: ChangePasswordRequest,
    current_user: dict = Depends(get_current_user),
    user_service=Depends(get_user_management_service),
):
    """修改密码"""
    try:
        success = await user_service.change_password(
            user_id=current_user["id"],
            old_password=request.old_password,
            new_password=request.new_password,
        )
        return {"message": "密码修改成功" if success else "密码修改失败"}
    except (UserNotFoundError, InvalidCredentialsError) as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)
        ) from e  # TODO: B904 exception chaining
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)
        ) from e


async def deactivate_user(
    user_id: int,
    current_user: dict = Depends(get_current_user),
    user_service=Depends(get_user_management_service),
) -> UserResponse:
    """停用用户"""
    try:
        # 检查权限：只有管理员可以停用用户
        if not current_user.get("is_admin", False):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="只有管理员可以停用用户",
            )
        user = await user_service.deactivate_user(user_id)
        return user
    except UserNotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=str(e)
        ) from e  # TODO: B904 exception chaining


async def activate_user(
    user_id: int,
    current_user: dict = Depends(get_current_user),
    user_service=Depends(get_user_management_service),
) -> UserResponse:
    """激活用户"""
    try:
        # 检查权限：只有管理员可以激活用户
        if not current_user.get("is_admin", False):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="只有管理员可以激活用户",
            )
        user = await user_service.activate_user(user_id)
        return user
    except UserNotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=str(e)
        ) from e  # TODO: B904 exception chaining


async def get_user_stats(
    current_user: dict = Depends(get_current_user),
    user_service=Depends(get_user_management_service),
):
    """获取用户统计信息"""
    # 检查权限：只有管理员可以查看统计
    if not current_user.get("is_admin", False):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="只有管理员可以查看用户统计",
        )
    try:
        stats = await user_service.get_user_stats()
        return stats
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e)
        ) from e
