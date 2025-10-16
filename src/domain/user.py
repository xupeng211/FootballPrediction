from typing import Any, Dict, List, Optional, Union
"" 用户领域模型
"" from datetime import datetime

from pydantic import BaseModel, EmailStr, Field, validator


class User(BaseModel)
:
    """用户模型"" id: Optional[int] = Noneusername: str = Field(..., min_length=3, max_length=50)

    email: EmailStrfull_name: Optional[str] = None

    is_active: bool = Trueis_verified

    bool = Falseroles: List[str] = ["user"]

    created_at: Optional[datetime] = Noneupdated_at: Optional[datetime] = None

    last_login: Optional[datetime] = None
    @validator("username")
    def validate_username(cls, v) -> None:
        if not v.isalnum() and "_" not in vraise ValueError("Username must be alphanumeric or contain underscores")

        return v

    class Config:
        from_attributes = True


class UserCreate(BaseModel)
:
    """创建用户请求模型"" username: str = Field(..., min_length=3, max_length=50)
    email: EmailStrpassword: str = Field(..., min_length=8)

    full_name: Optional[str] = None
    @validator("password")
    def validate_password(cls, v) -> None:
        if len(v) < 8
    raise ValueError("Password must be at least 8 characters long")
        return v


class UserUpdate(BaseModel)
:
    """更新用户请求模型"" full_name: Optional[str] = Noneemail: Optional[EmailStr] = None

    is_active: Optional[bool] = Noneclass UserLogin(BaseModel)
:

    """用户登录请求模型"" username: strpassword: str



class Token(BaseModel)
:
    """Token响应模型"" access_token: strrefresh_token: str

    token_type: str = "bearer expires_in: int


class TokenData(BaseModel)
:
    """Token数据模型"" user_id: Optional[str] = Noneroles: List[str] = []

    permissions: List[str] = []


class UserPasswordChange(BaseModel)
:
    """修改密码请求模型"" current_password: strnew_password: str = Field(..., min_length=8)


    @validator("new_password")
    def validate_new_password(cls, v) -> None:
        if len(v) < 8
    raise ValueError("Password must be at least 8 characters long")
        return v


class UserResponse(BaseModel)
:
    """用户响应模型"""
    id: intusername: str

    email: strfull_name: Optional[str]

    is_active: boolis_verified

    boolroles: List[str]

    created_at: datetimelast_login: Optional[datetime]


    class Config:
        from_attributes = True
