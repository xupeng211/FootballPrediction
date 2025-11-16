"""用户管理服务
User Management Service.

提供完整的用户管理功能，包括注册、登录、信息管理、权限控制等。
遵循CLAUDE.md中的防呆约束。
"""

import hashlib
import re
from datetime import datetime
from typing import Any

from pydantic import BaseModel, EmailStr

from src.core.exceptions import (
    InvalidCredentialsError,
    UserAlreadyExistsError,
    UserNotFoundError,
)
from src.database.repositories.user import UserRepository
from src.utils.crypto_utils import hash_password, verify_password
from src.utils.data_validator import validate_email, validate_password_strength


class UserCreateRequest(BaseModel):
    """用户创建请求模型."""

    username: str
    email: EmailStr
    password: str
    full_name: str | None = None


class UserUpdateRequest(BaseModel):
    """用户更新请求模型."""

    email: EmailStr | None = None
    full_name: str | None = None
    is_active: bool | None = None


class UserResponse(BaseModel):
    """用户响应模型."""

    id: int
    username: str
    email: str
    full_name: str | None
    is_active: bool
    created_at: datetime
    updated_at: datetime


class UserAuthResponse(BaseModel):
    """用户认证响应模型."""

    access_token: str
    token_type: str
    expires_in: int
    user: UserResponse


class UserManagementService:
    """用户管理服务类."""

    def __init__(self, user_repository: UserRepository):
        self.user_repository = user_repository

    async def create_user(self, request: UserCreateRequest) -> UserResponse:
        """创建新用户."""
        # 验证输入数据
        self._validate_create_request(request)

        # 检查用户是否已存在
        existing_user = await self.user_repository.get_by_email(request.email)
        if existing_user:
            raise UserAlreadyExistsError(f"用户邮箱 {request.email} 已存在")

        # 创建用户
        user_data = {
            "username": request.username,
            "email": request.email,
            "password_hash": hash_password(request.password),
            "full_name": request.full_name,
            "is_active": True,
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow(),
        }

        user = await self.user_repository.create(user_data)
        return self._convert_to_response(user)

    async def authenticate_user(self, email: str, password: str) -> UserAuthResponse:
        """用户认证."""
        # 验证输入数据
        if not email or not password:
            raise InvalidCredentialsError("邮箱和密码不能为空")

        # 查找用户
        user = await self.user_repository.get_by_email(email)
        if not user:
            raise UserNotFoundError(f"用户邮箱 {email} 不存在")

        # 验证密码
        if not verify_password(password, user.password_hash):
            raise InvalidCredentialsError("密码错误")

        # 生成访问令牌
        access_token = self._generate_access_token(user)

        return UserAuthResponse(
            access_token=access_token,
            token_type="bearer",
            expires_in=3600,
            user=self._convert_to_response(user),
        )

    async def get_user_by_id(self, user_id: int) -> UserResponse:
        """根据ID获取用户信息."""
        user = await self.user_repository.get_by_id(user_id)
        if not user:
            raise UserNotFoundError(f"用户ID {user_id} 不存在")

        return self._convert_to_response(user)

    async def get_user_by_email(self, email: str) -> UserResponse:
        """根据邮箱获取用户信息."""
        user = await self.user_repository.get_by_email(email)
        if not user:
            raise UserNotFoundError(f"用户邮箱 {email} 不存在")

        return self._convert_to_response(user)

    async def update_user(
        self, user_id: int, request: UserUpdateRequest
    ) -> UserResponse:
        """更新用户信息."""
        # 检查用户是否存在
        existing_user = await self.user_repository.get_by_id(user_id)
        if not existing_user:
            raise UserNotFoundError(f"用户ID {user_id} 不存在")

        # 验证更新数据
        update_data = self._validate_update_request(request)

        # 如果更新邮箱，检查邮箱是否已被其他用户使用
        if request.email and request.email != existing_user.email:
            email_user = await self.user_repository.get_by_email(request.email)
            if email_user and email_user.id != user_id:
                raise UserAlreadyExistsError(f"邮箱 {request.email} 已被其他用户使用")

        # 更新用户信息
        updated_user = await self.user_repository.update(user_id, update_data)
        return self._convert_to_response(updated_user)

    async def delete_user(self, user_id: int) -> bool:
        """删除用户."""
        # 检查用户是否存在
        existing_user = await self.user_repository.get_by_id(user_id)
        if not existing_user:
            raise UserNotFoundError(f"用户ID {user_id} 不存在")

        return await self.user_repository.delete(user_id)

    async def get_users(
        self, skip: int = 0, limit: int = 100, active_only: bool = True
    ) -> list[UserResponse]:
        """获取用户列表."""
        users = await self.user_repository.get_list(
            skip=skip, limit=limit, active_only=active_only
        )
        return [self._convert_to_response(user) for user in users]

    async def search_users(self, query: str, limit: int = 20) -> list[UserResponse]:
        """搜索用户."""
        users = await self.user_repository.search(query, limit)
        return [self._convert_to_response(user) for user in users]

    async def change_password(
        self, user_id: int, old_password: str, new_password: str
    ) -> bool:
        """修改密码."""
        # 检查用户是否存在
        user = await self.user_repository.get_by_id(user_id)
        if not user:
            raise UserNotFoundError(f"用户ID {user_id} 不存在")

        # 验证旧密码
        if not verify_password(old_password, user.password_hash):
            raise InvalidCredentialsError("旧密码错误")

        # 验证新密码强度
        validate_password_strength(new_password)

        # 更新密码
        update_data = {
            "password_hash": hash_password(new_password),
            "updated_at": datetime.utcnow(),
        }

        await self.user_repository.update(user_id, update_data)
        return True

    async def deactivate_user(self, user_id: int) -> UserResponse:
        """停用用户."""
        # 检查用户是否存在
        user = await self.user_repository.get_by_id(user_id)
        if not user:
            raise UserNotFoundError(f"用户ID {user_id} 不存在")

        update_data = {
            "is_active": False,
            "updated_at": datetime.utcnow(),
        }

        updated_user = await self.user_repository.update(user_id, update_data)
        return self._convert_to_response(updated_user)

    async def activate_user(self, user_id: int) -> UserResponse:
        """激活用户."""
        # 检查用户是否存在
        user = await self.user_repository.get_by_id(user_id)
        if not user:
            raise UserNotFoundError(f"用户ID {user_id} 不存在")

        update_data = {
            "is_active": True,
            "updated_at": datetime.utcnow(),
        }

        updated_user = await self.user_repository.update(user_id, update_data)
        return self._convert_to_response(updated_user)

    def _validate_create_request(self, request: UserCreateRequest) -> None:
        """验证创建用户请求."""
        # 验证用户名
        if not request.username or len(request.username.strip()) < 3:
            raise ValueError("用户名至少需要3个字符")

        if not re.match(r"^[a-zA-Z0-9_]+$", request.username):
            raise ValueError("用户名只能包含字母、数字和下划线")

        # 验证邮箱
        validate_email(request.email)

        # 验证密码强度
        validate_password_strength(request.password)

    def _validate_update_request(self, request: UserUpdateRequest) -> dict[str, Any]:
        """验证更新用户请求."""
        update_data = {}

        if request.email is not None:
            validate_email(request.email)
            update_data["email"] = request.email

        if request.full_name is not None:
            if request.full_name and len(request.full_name.strip()) < 2:
                raise ValueError("姓名至少需要2个字符")
            update_data["full_name"] = request.full_name.strip()

        if request.is_active is not None:
            update_data["is_active"] = request.is_active
            update_data["updated_at"] = datetime.utcnow()

        return update_data

    def _convert_to_response(self, user) -> UserResponse:
        """转换为响应模型."""
        return UserResponse(
            id=user.id,
            username=user.username,
            email=user.email,
            full_name=user.full_name,
            is_active=user.is_active,
            created_at=user.created_at,
            updated_at=user.updated_at,
        )

    def _generate_access_token(self, user) -> str:
        """生成访问令牌."""
        # 简单的令牌生成，实际项目中应该使用JWT
        token_data = f"{user.id}:{user.email}:{datetime.utcnow().timestamp()}"
        return hashlib.sha256(token_data.encode()).hexdigest()

    async def get_user_stats(self) -> dict[str, Any]:
        """获取用户统计信息."""
        total_users = await self.user_repository.count()
        active_users = await self.user_repository.count(active_only=True)

        return {
            "total_users": total_users,
            "active_users": active_users,
            "inactive_users": total_users - active_users,
            "activity_rate": (
                round((active_users / total_users) * 100, 2) if total_users > 0 else 0
            ),
        }
