"""
企业级多租户系统数据模型
Enterprise Multi-Tenant System Data Models

提供多租户架构的核心数据模型,包括租户,权限,角色等.
"""

from datetime import datetime
from enum import Enum
from typing import Optional, List, Dict, Any

from sqlalchemy import (
    Boolean, Column, String, Text, Integer, ForeignKey,
    JSON, DateTime, UniqueConstraint, Index
)
from sqlalchemy.orm import relationship, Mapped, mapped_column
from sqlalchemy.ext.hybrid import hybrid_property

from ..base import BaseModel


class TenantStatus(str, Enum):
    """租户状态枚举"""
    ACTIVE = "active"
    INACTIVE = "inactive"
    SUSPENDED = "suspended"
    TRIAL = "trial"
    EXPIRED = "expired"


class TenantPlan(str, Enum):
    """租户计划枚举"""
    BASIC = "basic"
    PROFESSIONAL = "professional"
    ENTERPRISE = "enterprise"
    CUSTOM = "custom"


class Tenant(BaseModel):
    """
    租户模型

    支持多租户架构的核心租户管理
    """
    __tablename__ = "tenants"

    # 基本信息
    name = Column(String(100), nullable=False, index=True, comment="租户名称")
    slug = Column(String(50), unique=True, nullable=False, index=True, comment="租户标识符")
    domain = Column(String(255), nullable=True, unique=True, comment="自定义域名")
    description = Column(Text, nullable=True, comment="租户描述")

    # 联系信息
    contact_email = Column(String(255), nullable=False, comment="联系邮箱")
    contact_phone = Column(String(50), nullable=True, comment="联系电话")
    company_name = Column(String(100), nullable=True, comment="公司名称")
    company_address = Column(Text, nullable=True, comment="公司地址")

    # 状态和计划
    status = Column(String(20), default=TenantStatus.TRIAL, nullable=False, comment="租户状态")
    plan = Column(String(20), default=TenantPlan.BASIC, nullable=False, comment="租户计划")

    # 配额和限制
    max_users = Column(Integer, default=10, nullable=False, comment="最大用户数")
    max_predictions_per_day = Column(Integer, default=100, nullable=False, comment="每日最大预测数")
    max_api_calls_per_hour = Column(Integer, default=1000, nullable=False, comment="每小时最大API调用数")
    storage_quota_mb = Column(Integer, default=100, nullable=False, comment="存储配额(MB)")

    # 时间相关
    trial_ends_at = Column(DateTime(timezone=True), nullable=True, comment="试用结束时间")
    subscription_ends_at = Column(DateTime(timezone=True), nullable=True, comment="订阅结束时间")

    # 设置和配置 (JSON格式)
    settings = Column(JSON, nullable=True, default=dict, comment="租户设置")
    features = Column(JSON, nullable=True, default=dict, comment="启用的功能")
    branding = Column(JSON, nullable=True, default=dict, comment="品牌定制")

    # 统计信息 (JSON格式)
    statistics = Column(JSON, nullable=True, default=dict, comment="租户统计")
    usage_metrics = Column(JSON, nullable=True, default=dict, comment="使用指标")

    # 审计字段
    created_by = Column(Integer, ForeignKey("users.id"), nullable=True, comment="创建者ID")
    is_active = Column(Boolean, default=True, nullable=False, comment="是否激活")

    # 关系
    users: Mapped[List["User"]] = relationship("User", back_populates="tenant", cascade="all, delete-orphan")
    tenant_roles: Mapped[List["TenantRole"]] = relationship("TenantRole", back_populates="tenant", cascade="all, delete-orphan")
    tenant_permissions: Mapped[List["TenantPermission"]] = relationship("TenantPermission", back_populates="tenant", cascade="all, delete-orphan")

    # 索引
    __table_args__ = (
        Index("idx_tenant_status_plan", "status", "plan"),
        Index("idx_tenant_subscription", "subscription_ends_at"),
        UniqueConstraint("slug", name="uq_tenant_slug"),
        UniqueConstraint("domain", name="uq_tenant_domain"),
    )

    @hybrid_property
    def is_trial(self) -> bool:
        """是否为试用状态"""
        return self.status == TenantStatus.TRIAL

    @hybrid_property
    def is_subscription_active(self) -> bool:
        """订阅是否激活"""
        if self.status != TenantStatus.ACTIVE:
            return False
        if self.subscription_ends_at is None:
            return True
        return datetime.utcnow() < self.subscription_ends_at

    @hybrid_property
    def days_until_expiry(self) -> Optional[int]:
        """距离过期的天数"""
        if self.subscription_ends_at is None:
            return None
        delta = self.subscription_ends_at - datetime.utcnow()
        return max(0, delta.days)

    @hybrid_property
    def usage_percentage(self) -> float:
        """存储使用百分比"""
        if self.storage_quota_mb <= 0:
            return 0.0
        used_mb = self.usage_metrics.get("storage_used_mb", 0) if self.usage_metrics else 0
        return min(100.0, (used_mb / self.storage_quota_mb) * 100)

    def can_add_user(self) -> bool:
        """是否可以添加新用户"""
        current_users = self.usage_metrics.get("current_users", 0) if self.usage_metrics else 0
        return current_users < self.max_users

    def can_make_prediction(self) -> bool:
        """是否可以创建新预测"""
        if not self.is_subscription_active:
            return False

        daily_predictions = self.usage_metrics.get("daily_predictions", 0) if self.usage_metrics else 0
        return daily_predictions < self.max_predictions_per_day

    def can_make_api_call(self) -> bool:
        """是否可以调用API"""
        if not self.is_subscription_active:
            return False

        hourly_api_calls = self.usage_metrics.get("hourly_api_calls", 0) if self.usage_metrics else 0
        return hourly_api_calls < self.max_api_calls_per_hour

    def get_feature_access(self, feature_name: str) -> bool:
        """检查功能访问权限"""
        if not self.features:
            return False
        return self.features.get(feature_name, False)

    def update_usage_metrics(self, metrics: Dict[str, Any]) -> None:
        """更新使用指标"""
        if self.usage_metrics is None:
            self.usage_metrics = {}
        self.usage_metrics.update(metrics)

    def to_dict(self, exclude_fields: Optional[set] = None) -> dict:
        """转换为字典"""
        result = super().to_dict(exclude_fields)
        # 添加计算属性
        result["is_trial"] = self.is_trial
        result["is_subscription_active"] = self.is_subscription_active
        result["days_until_expiry"] = self.days_until_expiry
        result["usage_percentage"] = self.usage_percentage
        return result


class PermissionScope(str, Enum):
    """权限范围枚举"""
    GLOBAL = "global"          # 全局权限
    TENANT = "tenant"          # 租户权限
    TEAM = "team"             # 团队权限
    USER = "user"             # 用户权限


class ResourceType(str, Enum):
    """资源类型枚举"""
    PREDICTIONS = "predictions"
    MODELS = "models"
    DATA = "data"
    USERS = "users"
    ANALYTICS = "analytics"
    SETTINGS = "settings"
    API = "api"


class TenantPermission(BaseModel):
    """
    租户权限模型
    定义租户级别的高层权限和资源访问控制
    """
    __tablename__ = "tenant_permissions"

    # 基本信息
    tenant_id = Column(Integer, ForeignKey("tenants.id"), nullable=False, comment="租户ID")
    name = Column(String(100), nullable=False, comment="权限名称")
    code = Column(String(50), nullable=False, comment="权限代码")
    description = Column(Text, nullable=True, comment="权限描述")

    # 权限范围和资源
    scope = Column(String(20), default=PermissionScope.TENANT, nullable=False, comment="权限范围")
    resource_type = Column(String(50), nullable=True, comment="资源类型")
    resource_id = Column(String(100), nullable=True, comment="资源ID")

    # 权限动作
    actions = Column(JSON, nullable=True, default=list, comment="允许的动作列表")

    # 条件和限制 (JSON格式)
    conditions = Column(JSON, nullable=True, default=dict, comment="权限条件")
    restrictions = Column(JSON, nullable=True, default=dict, comment="权限限制")

    # 状态
    is_active = Column(Boolean, default=True, nullable=False, comment="是否激活")

    # 关系
    tenant: Mapped["Tenant"] = relationship("Tenant", back_populates="tenant_permissions")
    role_permissions: Mapped[List["RolePermission"]] = relationship("RolePermission", back_populates="permission", cascade="all, delete-orphan")

    # 索引和约束
    __table_args__ = (
        UniqueConstraint("tenant_id", "code", name="uq_tenant_permission"),
        Index("idx_tenant_permission_scope", "tenant_id", "scope"),
        Index("idx_tenant_permission_resource", "resource_type", "resource_id"),
    )

    def can_perform_action(self, action: str, resource_context: Optional[Dict[str, Any]] = None) -> bool:
        """检查是否可以执行指定动作"""
        if not self.is_active:
            return False

        # 检查动作权限
        if self.actions and action not in self.actions:
            return False

        # 检查条件限制
        if self.conditions and resource_context:
            return self._evaluate_conditions(resource_context)

        return True

    def _evaluate_conditions(self, context: Dict[str, Any]) -> bool:
        """评估权限条件"""
        # 简单的条件评估逻辑,可根据需要扩展
        for condition_key, condition_value in self.conditions.items():
            if condition_key not in context:
                return False

            context_value = context[condition_key]
            if isinstance(condition_value, list):
                if context_value not in condition_value:
                    return False
            elif context_value != condition_value:
                return False

        return True


class TenantRole(BaseModel):
    """
    租户角色模型
    定义租户内的角色和职责
    """
    __tablename__ = "tenant_roles"

    # 基本信息
    tenant_id = Column(Integer, ForeignKey("tenants.id"), nullable=False, comment="租户ID")
    name = Column(String(100), nullable=False, comment="角色名称")
    code = Column(String(50), nullable=False, comment="角色代码")
    description = Column(Text, nullable=True, comment="角色描述")

    # 角色级别
    level = Column(Integer, default=1, nullable=False, comment="角色级别")
    is_system_role = Column(Boolean, default=False, nullable=False, comment="是否为系统角色")

    # 权限和限制
    permissions = Column(JSON, nullable=True, default=list, comment="权限列表")
    restrictions = Column(JSON, nullable=True, default=dict, comment="角色限制")

    # 状态
    is_active = Column(Boolean, default=True, nullable=False, comment="是否激活")

    # 关系
    tenant: Mapped["Tenant"] = relationship("Tenant", back_populates="tenant_roles")
    role_permissions: Mapped[List["RolePermission"]] = relationship("RolePermission", back_populates="role", cascade="all, delete-orphan")
    user_roles: Mapped[List["UserRoleAssignment"]] = relationship("UserRoleAssignment", back_populates="role", cascade="all, delete-orphan")

    # 索引和约束
    __table_args__ = (
        UniqueConstraint("tenant_id", "code", name="uq_tenant_role"),
        Index("idx_tenant_role_level", "tenant_id", "level"),
    )

    def has_permission(self, permission_code: str) -> bool:
        """检查是否拥有指定权限"""
        if not self.is_active:
            return False
        return permission_code in (self.permissions or [])


class RolePermission(BaseModel):
    """
    角色权限关联模型
    多对多关系表,连接角色和权限
    """
    __tablename__ = "role_permissions"

    # 关联字段
    role_id = Column(Integer, ForeignKey("tenant_roles.id"), nullable=False, comment="角色ID")
    permission_id = Column(Integer, ForeignKey("tenant_permissions.id"), nullable=False, comment="权限ID")

    # 额外属性
    granted_by = Column(Integer, ForeignKey("users.id"), nullable=True, comment="授权者ID")
    granted_at = Column(DateTime(timezone=True), default=datetime.utcnow, nullable=False, comment="授权时间")
    conditions = Column(JSON, nullable=True, default=dict, comment="特殊条件")

    # 关系
    role: Mapped["TenantRole"] = relationship("TenantRole", back_populates="role_permissions")
    permission: Mapped["TenantPermission"] = relationship("TenantPermission", back_populates="role_permissions")

    # 索引和约束
    __table_args__ = (
        UniqueConstraint("role_id", "permission_id", name="uq_role_permission"),
        Index("idx_role_permission_granted", "granted_at"),
    )


class UserRoleAssignment(BaseModel):
    """
    用户角色分配模型
    记录用户在租户内的角色分配
    """
    __tablename__ = "user_role_assignments"

    # 关联字段
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, comment="用户ID")
    tenant_id = Column(Integer, ForeignKey("tenants.id"), nullable=False, comment="租户ID")
    role_id = Column(Integer, ForeignKey("tenant_roles.id"), nullable=False, comment="角色ID")

    # 分配信息
    assigned_by = Column(Integer, ForeignKey("users.id"), nullable=True, comment="分配者ID")
    assigned_at = Column(DateTime(timezone=True), default=datetime.utcnow, nullable=False, comment="分配时间")
    expires_at = Column(DateTime(timezone=True), nullable=True, comment="过期时间")

    # 状态和备注
    is_active = Column(Boolean, default=True, nullable=False, comment="是否激活")
    notes = Column(Text, nullable=True, comment="备注")

    # 关系
    role: Mapped["TenantRole"] = relationship("TenantRole", back_populates="user_roles")

    # 索引和约束
    __table_args__ = (
        UniqueConstraint("user_id", "tenant_id", "role_id", name="uq_user_tenant_role"),
        Index("idx_user_role_assignment", "user_id", "tenant_id"),
        Index("idx_role_assignment_expiry", "expires_at"),
    )

    @hybrid_property
    def is_expired(self) -> bool:
        """是否已过期"""
        if self.expires_at is None:
            return False
        return datetime.utcnow() > self.expires_at

    @hybrid_property
    def is_valid(self) -> bool:
        """是否有效"""
        return self.is_active and not self.is_expired