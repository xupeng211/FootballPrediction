from __future__ import annotations

from datetime import datetime
from typing import Any,  List[Any], Optional

from sqlalchemy import Boolean, Column, DateTime, Integer, JSON, String, Text
from sqlalchemy.orm import relationship

from src.database.base import BaseModel

"""用户数据模型。"""


class User(BaseModel):
    """平台用户表，支持RBAC权限控制。"""

    __tablename__ = "users"

    username = Column(String(64), unique=True, nullable=False, comment="用户名")
    email = Column(String(128), unique=True, nullable=False, comment="邮箱")
    full_name = Column(String(128), nullable=True, comment="全名")
    password_hash = Column(String(255), nullable=True, comment="密码哈希")
    is_active = Column(Boolean, default=True, nullable=False, comment="是否激活")
    is_verified = Column(Boolean, default=False, nullable=False, comment="是否验证")
    roles = Column(Text, default="user", comment="用户角色，逗号分隔")

    # 原有的角色字段保持兼容
    is_admin = Column(Boolean, default=False, nullable=False, comment="管理员标记")
    is_analyst = Column(Boolean, default=False, nullable=False, comment="分析师标记")
    is_premium = Column(Boolean, default=False, nullable=False, comment="高级订阅标记")
    is_professional_bettor = Column(
        Boolean, default=False, nullable=False, comment="职业投注者"
    )
    is_casual_bettor = Column(
        Boolean, default=False, nullable=False, comment="休闲投注者"
    )
    last_login = Column(DateTime, nullable=True, comment="最近登录时间")
    subscription_plan = Column(String(32), nullable=True, comment="订阅计划")
    subscription_expires_at = Column(DateTime, nullable=True, comment="订阅过期时间")
    bankroll = Column(Integer, nullable=True, comment="资金池")
    risk_preference = Column(String(16), nullable=True, comment="风险偏好")
    favorite_leagues = Column(JSON, nullable=True, comment="偏好联赛列表")
    timezone = Column(String(64), nullable=True, comment="时区")
    avatar_url = Column(String(256), nullable=True, comment="头像地址")
    specialization = Column(String(128), nullable=True, comment="分析师专长")
    experience_years = Column(Integer, nullable=True, comment="相关经验年限")

    def touch_login(self) -> None:
        """更新最近登录时间。"""
        self.last_login = datetime.utcnow()  # type: ignore[assignment]

    def get_roles(self) -> List[str]:
        """获取用户角色列表"""
        if self.roles:
            return [role.strip() for role in self.roles.split(",") if role.strip()]

        # 兼容旧的角色字段
        role_list = []
        if self.is_admin:
            role_list.append("admin")
        if self.is_analyst:
            role_list.append("analyst")
        if self.is_premium:
            role_list.append("premium")
        if self.is_professional_bettor:
            role_list.append("professional_bettor")
        if self.is_casual_bettor:
            role_list.append("casual_bettor")

        # 如果没有任何角色，默认为user
        if not role_list:
            role_list = ["user"]

        return role_list

    def set_roles(self, roles: List[str]):
        """设置用户角色"""
        self.roles = ",".join(roles) if roles else "user"

        # 同步更新旧的角色字段
        self.is_admin = "admin" in roles
        self.is_analyst = "analyst" in roles
        self.is_premium = "premium" in roles
        self.is_professional_bettor = "professional_bettor" in roles
        self.is_casual_bettor = "casual_bettor" in roles

    def has_role(self, role: str) -> bool:
        """检查用户是否有指定角色"""
        return role in self.get_roles()

    def add_role(self, role: str):
        """添加角色"""
        roles = self.get_roles()
        if role not in roles:
            roles.append(role)
            self.set_roles(roles)

    def remove_role(self, role: str):
        """移除角色"""
        roles = self.get_roles()
        if role in roles:
            roles.remove(role)
            self.set_roles(roles)

    def __repr__(self) -> str:  # pragma: no cover - 调试友好
        return f"<User(id={self.id}, username='{self.username}', email='{self.email}')>"
