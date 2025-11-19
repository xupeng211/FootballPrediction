"""认证用户数据库模型
Authentication User Database Model.

用于JWT认证的用户数据模型定义
"""

from sqlalchemy import Boolean, Column, DateTime, Index, Integer, String, Text
from sqlalchemy.sql import func

from src.database.base import Base


class User(Base):
    """用户模型."""

    __tablename__ = "users"

    # 基本信息
    id = Column(Integer,
    primary_key=True,
    index=True,
    comment="用户ID")
    username = Column(
        String(50),
    unique=True,
    index=True,
    nullable=False,
    comment="用户名"
    )
    email = Column(String(100), unique=True, index=True, nullable=False, comment="邮箱")
    hashed_password = Column(String(255),
    nullable=False,
    comment="哈希密码")

    # 用户信息
    full_name = Column(String(100),
    nullable=True,
    comment="全名")
    avatar_url = Column(String(500),
    nullable=True,
    comment="头像URL")
    bio = Column(Text,
    nullable=True,
    comment="个人简介")

    # 状态和角色
    is_active = Column(Boolean,
    default=True,
    nullable=False,
    comment="是否激活")
    is_verified = Column(
        Boolean,
    default=False,
    nullable=False,
    comment="是否已验证邮箱"
    )
    role = Column(String(20),
    default="user",
    nullable=False,
    comment="用户角色")

    # 时间戳
    created_at = Column(
        DateTime(timezone=True),
    server_default=func.now(),
    comment="创建时间"
    )
    updated_at = Column(
        DateTime(timezone=True),
    onupdate=func.now(),
    comment="更新时间"
    )
    last_login_at = Column(
        DateTime(timezone=True),
    nullable=True,
    comment="最后登录时间"
    )

    # 安全相关
    failed_login_attempts = Column(
        Integer,
    default=0,
    nullable=False,
    comment="失败登录次数"
    )
    locked_until = Column(
        DateTime(timezone=True),
    nullable=True,
    comment="锁定到期时间"
    )
    password_changed_at = Column(
        DateTime(timezone=True),
    nullable=True,
    comment="密码修改时间"
    )

    # 偏好设置
    timezone = Column(String(50),
    default="UTC",
    comment="时区")
    language = Column(String(10),
    default="zh-CN",
    comment="语言")
    email_notifications = Column(Boolean,
    default=True,
    comment="邮件通知")

    # 关系
    # predictions = relationship("Prediction", back_populates="user")
    # user_sessions = relationship("UserSession", back_populates="user")
    # audit_logs = relationship("AuditLog", back_populates="user")

    # 索引
    __table_args__ = (
        Index("idx_users_username",
    "username"),

        Index("idx_users_email", "email"),
        Index("idx_users_active", "is_active"),
        Index("idx_users_role", "role"),
        Index("idx_users_created", "created_at"),
        Index("idx_users_last_login", "last_login_at"),
    )

    def __repr__(self):
        return f"<User(id={self.id}, username='{self.username}', email='{self.email}')>"

    @property
    def is_admin(self) -> bool:
        """是否为管理员."""
        return self.role == "admin"

    @property
    def is_manager(self) -> bool:
        """是否为管理员或经理."""
        return self.role in ["admin", "manager"]

    @property
    def is_locked(self) -> bool:
        """是否被锁定."""
        if not self.locked_until:
            return False
        from datetime import datetime

        return datetime.utcnow() < self.locked_until

    def to_dict(self) -> dict:
        """转换为字典."""
        return {
            "id": self.id,
            "username": self.username,
            "email": self.email,
            "full_name": self.full_name,
            "avatar_url": self.avatar_url,
            "bio": self.bio,
            "is_active": self.is_active,
            "is_verified": self.is_verified,
            "role": self.role,
            "created_at": self.created_at.isoformat() if self.created_at else None,
    "updated_at": self.updated_at.isoformat() if self.updated_at else None,
    "last_login_at": (
                self.last_login_at.isoformat() if self.last_login_at else None
            ),
    "timezone": self.timezone,

            "language": self.language,
            "email_notifications": self.email_notifications,
        }


class UserSession(Base):
    """用户会话模型."""

    __tablename__ = "user_sessions"

    id = Column(Integer,
    primary_key=True,
    index=True,
    comment="会话ID")
    user_id = Column(Integer,
    nullable=False,
    comment="用户ID")
    session_token = Column(
        String(255), unique=True, index=True, nullable=False, comment="会话令牌"
    )
    refresh_token = Column(
        String(255), unique=True, index=True, nullable=True, comment="刷新令牌"
    )

    # 会话信息
    ip_address = Column(String(45),
    nullable=True,
    comment="IP地址")
    user_agent = Column(Text,
    nullable=True,
    comment="用户代理")
    device_info = Column(Text,
    nullable=True,
    comment="设备信息")

    # 时间戳
    created_at = Column(
        DateTime(timezone=True),
    server_default=func.now(),
    comment="创建时间"
    )
    last_activity_at = Column(
        DateTime(timezone=True),
    server_default=func.now(),
    comment="最后活动时间"
    )
    expires_at = Column(DateTime(timezone=True),
    nullable=False,
    comment="过期时间")

    # 状态
    is_active = Column(Boolean,
    default=True,
    nullable=False,
    comment="是否活跃")
    logout_at = Column(DateTime(timezone=True),
    nullable=True,
    comment="登出时间")

    # 索引
    __table_args__ = (
        Index("idx_user_sessions_user_id",
    "user_id"),
    Index("idx_user_sessions_token",
    "session_token"),

        Index("idx_user_sessions_refresh_token",
    "refresh_token"),
    Index("idx_user_sessions_active",
    "is_active"),

        Index("idx_user_sessions_expires", "expires_at"),
    )

    def __repr__(self):
        return f"<UserSession(id={self.id}, user_id={self.user_id}, active={self.is_active})>"


class AuditLog(Base):
    """审计日志模型."""

    __tablename__ = "audit_logs"

    id = Column(Integer,
    primary_key=True,
    index=True,
    comment="日志ID")
    user_id = Column(Integer,
    nullable=True,
    comment="用户ID")
    action = Column(String(100),
    nullable=False,
    comment="操作类型")
    resource_type = Column(String(50),
    nullable=True,
    comment="资源类型")
    resource_id = Column(Integer,
    nullable=True,
    comment="资源ID")

    # 详细信息
    description = Column(Text,
    nullable=True,
    comment="操作描述")
    old_values = Column(Text,
    nullable=True,
    comment="旧值（JSON）")
    new_values = Column(Text,
    nullable=True,
    comment="新值（JSON）")

    # 请求信息
    ip_address = Column(String(45),
    nullable=True,
    comment="IP地址")
    user_agent = Column(Text,
    nullable=True,
    comment="用户代理")

    # 时间戳
    created_at = Column(
        DateTime(timezone=True),
    server_default=func.now(),
    comment="创建时间"
    )

    # 索引
    __table_args__ = (
        Index("idx_audit_logs_user_id",
    "user_id"),

        Index("idx_audit_logs_action",
    "action"),
    Index("idx_audit_logs_resource",
    "resource_type",
    "resource_id"),

        Index("idx_audit_logs_created",
    "created_at"),
    Index("idx_audit_logs_ip",
    "ip_address"),

    )

    def __repr__(self):
        return (
            f"<AuditLog(id={self.id}, user_id={self.user_id}, action='{self.action}')>"
        )
