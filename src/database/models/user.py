from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Optional

from sqlalchemy import Boolean, Column, DateTime, String, Text, JSON

from ..base import BaseModel


class UserRole(str, Enum):
    """用户角色枚举"""

    USER = "user"
    PREMIUM = "premium"
    ADMIN = "admin"
    ANALYST = "analyst"


class User(BaseModel):
    """用户数据模型"""

    __tablename__ = "users"

    # 基本信息
    username = Column(String(50), unique=True, nullable=False, index=True, comment="用户名")
    email = Column(String(255), unique=True, nullable=False, index=True, comment="邮箱")
    password_hash = Column(String(255), nullable=False, comment="密码哈希")

    # 个人资料
    first_name = Column(String(50), nullable=True, comment="名")
    last_name = Column(String(50), nullable=True, comment="姓")
    avatar_url = Column(String(500), nullable=True, comment="头像URL")
    bio = Column(Text, nullable=True, comment="个人简介")

    # 状态字段
    is_active = Column(Boolean, default=True, nullable=False, comment="是否激活")
    is_verified = Column(Boolean, default=False, nullable=False, comment="是否已验证")
    last_login = Column(DateTime(timezone=True), nullable=True, comment="最后登录时间")

    # 角色和权限
    role = Column(String(20), default=UserRole.USER, nullable=False, comment="用户角色")

    # 偏好设置 (JSON格式存储)
    preferences = Column(JSON, nullable=True, default=dict, comment="用户偏好设置")

    # 统计数据 (JSON格式存储)
    statistics = Column(JSON, nullable=True, default=dict, comment="用户统计数据")

    # 等级和成就
    level = Column(String(10), default="1", nullable=False, comment="用户等级")
    experience_points = Column(String(20), default="0", nullable=False, comment="经验值")
    achievements = Column(JSON, nullable=True, default=list, comment="成就列表")

    # 时间戳字段继承自BaseModel (created_at, updated_at)

    @property
    def full_name(self) -> str:
        """获取全名"""
        if self.first_name and self.last_name:
            return f"{self.first_name} {self.last_name}"
        return self.username

    @property
    def is_premium(self) -> bool:
        """是否为高级用户"""
        return self.role in [UserRole.PREMIUM, UserRole.ADMIN, UserRole.ANALYST]

    @property
    def is_admin(self) -> bool:
        """是否为管理员"""
        return self.role == UserRole.ADMIN

    def update_last_login(self) -> None:
        """更新最后登录时间"""
        self.last_login = datetime.utcnow()

    def to_dict(self, exclude_fields: Optional[set] = None) -> dict:
        """转换为字典,排除敏感字段"""
        if exclude_fields is None:
            exclude_fields = {"password_hash"}

        result = super().to_dict(exclude_fields)
        # 添加计算属性
        result["full_name"] = self.full_name
        result["is_premium"] = self.is_premium
        result["is_admin"] = self.is_admin

        return result
