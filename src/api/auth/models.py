"""
用户认证API的数据模型

定义认证相关的请求和响应模型
"""

from typing import Any

from pydantic import BaseModel, ConfigDict, EmailStr, Field


class UserRegisterRequest(BaseModel):
    """用户注册请求模型"""

    username: str = Field(..., min_length=3, max_length=50, description="用户名")
    email: EmailStr = Field(..., description="邮箱地址")
    password: str = Field(..., min_length=6, max_length=100, description="密码")
    first_name: str | None = Field(None, max_length=50, description="名")
    last_name: str | None = Field(None, max_length=50, description="姓")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "username": "testuser",
                "email": "test@example.com",
                "password": "password123",
                "first_name": "张",
                "last_name": "三",
            }
        }
    )


class UserResponse(BaseModel):
    """用户响应模型"""

    id: int
    username: str
    email: str
    first_name: str | None = None
    last_name: str | None = None
    full_name: str
    avatar_url: str | None = None
    bio: str | None = None
    is_active: bool
    is_verified: bool
    is_premium: bool
    is_admin: bool
    role: str
    last_login: str | None = None
    preferences: dict[str, Any] | None = None
    statistics: dict[str, Any] | None = None
    level: str
    experience_points: str
    achievements: list | None = None
    created_at: str
    updated_at: str

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "id": 1,
                "username": "testuser",
                "email": "test@example.com",
                "first_name": "张",
                "last_name": "三",
                "full_name": "张三",
                "avatar_url": None,
                "bio": None,
                "is_active": True,
                "is_verified": False,
                "is_premium": False,
                "is_admin": False,
                "role": "user",
                "last_login": None,
                "preferences": {
                    "favorite_teams": [],
                    "favorite_leagues": [],
                    "notification_enabled": True,
                    "language": "zh-CN",
                },
                "statistics": {
                    "total_predictions": 0,
                    "correct_predictions": 0,
                    "accuracy_rate": 0.0,
                },
                "level": "1",
                "experience_points": "0",
                "achievements": [],
                "created_at": "2025-10-28T18:50:00Z",
                "updated_at": "2025-10-28T18:50:00Z",
            }
        }
    )


class TokenResponse(BaseModel):
    """令牌响应模型"""

    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int
    user: UserResponse

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
                "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
                "token_type": "bearer",
                "expires_in": 1800,
                "user": {
                    "id": 1,
                    "username": "testuser",
                    "email": "test@example.com",
                    "role": "user",
                },
            }
        }
    )


class PasswordChangeRequest(BaseModel):
    """密码修改请求模型"""

    current_password: str = Field(..., description="当前密码")
    new_password: str = Field(..., min_length=6, max_length=100, description="新密码")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "current_password": "oldpassword123",
                "new_password": "newpassword123",
            }
        }
    )


class PasswordResetRequest(BaseModel):
    """密码重置请求模型"""

    email: EmailStr = Field(..., description="邮箱地址")

    model_config = ConfigDict(
        json_schema_extra={"example": {"email": "test@example.com"}}
    )


class PasswordResetConfirm(BaseModel):
    """密码重置确认模型"""

    token: str = Field(..., description="重置令牌")
    new_password: str = Field(..., min_length=6, max_length=100, description="新密码")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
                "new_password": "newpassword123",
            }
        }
    )


class MessageResponse(BaseModel):
    """通用消息响应模型"""

    message: str

    model_config = ConfigDict(json_schema_extra={"example": {"message": "操作成功"}})


class UserUpdateRequest(BaseModel):
    """用户更新请求模型"""

    first_name: str | None = Field(None, max_length=50, description="名")
    last_name: str | None = Field(None, max_length=50, description="姓")
    avatar_url: str | None = Field(None, max_length=500, description="头像URL")
    bio: str | None = Field(None, max_length=1000, description="个人简介")
    preferences: dict[str, Any] | None = Field(None, description="偏好设置")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "first_name": "张",
                "last_name": "三",
                "avatar_url": "https://example.com/avatar.jpg",
                "bio": "足球预测爱好者",
                "preferences": {"favorite_teams": [1, 2], "language": "zh-CN"},
            }
        }
    )


class UserStatsResponse(BaseModel):
    """用户统计响应模型"""

    total_predictions: int = Field(..., description="总预测次数")
    correct_predictions: int = Field(..., description="正确预测次数")
    accuracy_rate: float = Field(..., description="准确率")
    total_profit_loss: float = Field(..., description="总盈亏")
    roi: float = Field(..., description="投资回报率")
    best_streak: int = Field(..., description="最佳连续预测")
    current_streak: int = Field(..., description="当前连续预测")
    average_odds: float = Field(..., description="平均赔率")
    average_confidence: float = Field(..., description="平均信心度")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "total_predictions": 100,
                "correct_predictions": 65,
                "accuracy_rate": 65.0,
                "total_profit_loss": 1250.50,
                "roi": 12.5,
                "best_streak": 8,
                "current_streak": 3,
                "average_odds": 2.15,
                "average_confidence": 75.5,
            }
        }
    )
