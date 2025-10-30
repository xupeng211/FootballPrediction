"""
企业级多租户管理服务
Enterprise Multi-Tenant Management Service

提供多租户架构的核心管理功能,包括租户生命周期管理,
权限控制,资源配额管理等.
"""

from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any
from dataclasses import dataclass

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_
from sqlalchemy.orm import selectinload

from src.database.models.tenant import (
    Tenant,
    TenantRole,
    UserRoleAssignment,
    TenantStatus,
    TenantPlan,
)
from src.core.exceptions import ValidationError, ResourceNotFoundError


class TenantManagementError(Exception):
    """租户管理异常"""

    pass


@dataclass
class TenantCreationRequest:
    """类文档字符串"""
    pass  # 添加pass语句
    """租户创建请求"""

    name: str
    slug: str
    contact_email: str
    company_name: Optional[str] = None
    description: Optional[str] = None
    plan: TenantPlan = TenantPlan.BASIC
    max_users: int = 10
    trial_days: int = 30
    custom_settings: Optional[Dict[str, Any]] = None


@dataclass
class ResourceQuotaCheck:
    """类文档字符串"""
    pass  # 添加pass语句
    """资源配额检查结果"""

    can_access: bool
    current_usage: int
    max_limit: int
    usage_percentage: float
    reason: Optional[str] = None


@dataclass
class PermissionCheckResult:
    """类文档字符串"""
    pass  # 添加pass语句
    """权限检查结果"""

    granted: bool
    permissions: List[str]
    restrictions: Dict[str, Any]
    reason: Optional[str] = None


class TenantService:
    """类文档字符串"""
    pass  # 添加pass语句
    """
    企业级多租户管理服务

    提供完整的租户生命周期管理,权限控制和资源配额管理功能
    """

    def __init__(self, db: AsyncSession):
    """函数文档字符串"""
    pass  # 添加pass语句
        self.db = db

    # ==================== 租户生命周期管理 ====================

    async def create_tenant(
        self, request: TenantCreationRequest, creator_id: Optional[int] = None
    ) -> Tenant:
        """
        创建新租户

        Args:
            request: 租户创建请求
            creator_id: 创建者ID

        Returns:
            Tenant: 创建的租户对象

        Raises:
            ValidationError: 验证失败
            TenantManagementError: 租户管理错误
        """
        # 验证租户标识符唯一性
        existing_tenant = await self.get_tenant_by_slug(request.slug)
        if existing_tenant:
            raise ValidationError(f"租户标识符 '{request.slug}' 已存在")

        # 创建租户
        tenant = Tenant(
            name=request.name,
            slug=request.slug,
            contact_email=request.contact_email,
            company_name=request.company_name,
            description=request.description,
            plan=request.plan,
            status=TenantStatus.TRIAL,
            max_users=request.max_users,
            trial_ends_at=datetime.utcnow() + timedelta(days=request.trial_days),
            created_by=creator_id,
            is_active=True,
        )

        # 设置默认配置
        tenant.settings = {
            "timezone": "UTC+8",
            "language": "zh-CN",
            "currency": "CNY",
            "odds_format": "decimal",
            "notifications_enabled": True,
            "data_retention_days": 90,
            **(request.custom_settings or {}),
        }

        # 设置默认功能
        tenant.features = self._get_default_features_for_plan(request.plan)

        # 设置默认配额
        await self._apply_plan_quotas(tenant, request.plan)

        # 初始化统计信息
        tenant.statistics = {
            "total_users": 0,
            "total_predictions": 0,
            "total_api_calls": 0,
            "storage_used_mb": 0,
            "created_predictions": 0,
            "successful_predictions": 0,
        }

        tenant.usage_metrics = {
            "current_users": 0,
            "daily_predictions": 0,
            "hourly_api_calls": 0,
            "storage_used_mb": 0,
            "last_updated": datetime.utcnow().isoformat(),
        }

        # 保存租户
        self.db.add(tenant)
        await self.db.flush()

        # 创建默认角色
        await self._create_default_roles(tenant.id)

        await self.db.commit()
        return tenant

    async def get_tenant_by_id(self, tenant_id: int) -> Optional[Tenant]:
        """根据ID获取租户"""
        result = await self.db.execute(select(Tenant).where(Tenant.id == tenant_id))
        return result.scalar_one_or_none()

    async def get_tenant_by_slug(self, slug: str) -> Optional[Tenant]:
        """根据标识符获取租户"""
        result = await self.db.execute(select(Tenant).where(Tenant.slug == slug))
        return result.scalar_one_or_none()

    async def update_tenant(self, tenant_id: int, updates: Dict[str, Any]) -> Tenant:
        """更新租户信息"""
        tenant = await self.get_tenant_by_id(tenant_id)
        if not tenant:
            raise ResourceNotFoundError(f"租户 {tenant_id} 不存在")

        # 更新允许的字段
        allowed_fields = {
            "name",
            "description",
            "contact_email",
            "contact_phone",
            "company_name",
            "company_address",
            "settings",
            "features",
            "branding",
        }

        for field, value in updates.items():
            if field in allowed_fields and hasattr(tenant, field):
                setattr(tenant, field, value)

        await self.db.commit()
        return tenant

    async def suspend_tenant(self, tenant_id: int, reason: str) -> Tenant:
        """暂停租户"""
        tenant = await self.get_tenant_by_id(tenant_id)
        if not tenant:
            raise ResourceNotFoundError(f"租户 {tenant_id} 不存在")

        tenant.status = TenantStatus.SUSPENDED
        tenant.statistics = tenant.statistics or {}
        tenant.statistics["suspension_reason"] = reason
        tenant.statistics["suspended_at"] = datetime.utcnow().isoformat()

        await self.db.commit()
        return tenant

    async def activate_tenant(
        self, tenant_id: int, plan: Optional[TenantPlan] = None
    ) -> Tenant:
        """激活租户"""
        tenant = await self.get_tenant_by_id(tenant_id)
        if not tenant:
            raise ResourceNotFoundError(f"租户 {tenant_id} 不存在")

        if plan:
            tenant.plan = plan
            await self._apply_plan_quotas(tenant, plan)

        tenant.status = TenantStatus.ACTIVE
        tenant.subscription_ends_at = datetime.utcnow() + timedelta(days=30)

        await self.db.commit()
        return tenant

    # ==================== 权限管理 ====================

    async def check_user_permission(
        self,
        user_id: int,
        tenant_id: int,
        permission_code: str,
        resource_context: Optional[Dict[str, Any]] = None,
    ) -> PermissionCheckResult:
        """
        检查用户权限

        Args:
            user_id: 用户ID
            tenant_id: 租户ID
            permission_code: 权限代码
            resource_context: 资源上下文

        Returns:
            PermissionCheckResult: 权限检查结果
        """
        # 获取用户在租户内的角色
        user_roles = await self._get_user_roles(user_id, tenant_id)
        if not user_roles:
            return PermissionCheckResult(
                granted=False,
                permissions=[],
                restrictions={},
                reason="用户在租户内无角色",
            )

        # 收集所有权限
        all_permissions = []
        all_restrictions = {}

        for role_assignment in user_roles:
            if not role_assignment.is_active or role_assignment.is_expired:
                continue

            role = role_assignment.role
            if not role.is_active:
                continue

            # 检查直接权限
            if permission_code in (role.permissions or []):
                all_permissions.append(permission_code)

            # 检查关联的详细权限
            role_permissions = await self._get_role_permissions(role.id)
            for role_perm in role_permissions:
                permission = role_perm.permission
                if permission.code == permission_code and permission.is_active:
                    if permission.can_perform_action(permission_code, resource_context):
                        all_permissions.append(permission_code)
                        if permission.restrictions:
                            all_restrictions.update(permission.restrictions)

        granted = len(all_permissions) > 0
        reason = None if granted else "权限不足"

        return PermissionCheckResult(
            granted=granted,
            permissions=all_permissions,
            restrictions=all_restrictions,
            reason=reason,
        )

    async def assign_user_role(
        self,
        user_id: int,
        tenant_id: int,
        role_code: str,
        assigned_by: int,
        expires_at: Optional[datetime] = None,
    ) -> UserRoleAssignment:
        """
        为用户分配角色

        Args:
            user_id: 用户ID
            tenant_id: 租户ID
            role_code: 角色代码
            assigned_by: 分配者ID
            expires_at: 过期时间

        Returns:
            UserRoleAssignment: 角色分配对象
        """
        # 验证租户和角色存在
        tenant = await self.get_tenant_by_id(tenant_id)
        if not tenant:
            raise ResourceNotFoundError(f"租户 {tenant_id} 不存在")

        role = await self._get_tenant_role(tenant_id, role_code)
        if not role:
            raise ResourceNotFoundError(f"角色 {role_code} 不存在")

        # 检查是否已存在分配
        existing_assignment = await self._get_user_role_assignment(
            user_id, tenant_id, role.id
        )
        if existing_assignment:
            existing_assignment.is_active = True
            existing_assignment.assigned_by = assigned_by
            existing_assignment.assigned_at = datetime.utcnow()
            existing_assignment.expires_at = expires_at
            assignment = existing_assignment
        else:
            assignment = UserRoleAssignment(
                user_id=user_id,
                tenant_id=tenant_id,
                role_id=role.id,
                assigned_by=assigned_by,
                expires_at=expires_at,
            )
            self.db.add(assignment)

        await self.db.commit()
        return assignment

    async def revoke_user_role(
        self, user_id: int, tenant_id: int, role_code: str
    ) -> bool:
        """撤销用户角色"""
        role = await self._get_tenant_role(tenant_id, role_code)
        if not role:
            return False

        assignment = await self._get_user_role_assignment(user_id, tenant_id, role.id)
        if assignment:
            assignment.is_active = False
            await self.db.commit()
            return True

        return False

    # ==================== 资源配额管理 ====================

    async def check_resource_quota(
        self, tenant_id: int, resource_type: str, additional_amount: int = 1
    ) -> ResourceQuotaCheck:
        """
        检查资源配额

        Args:
            tenant_id: 租户ID
            resource_type: 资源类型
            additional_amount: 额外需要量

        Returns:
            ResourceQuotaCheck: 配额检查结果
        """
        tenant = await self.get_tenant_by_id(tenant_id)
        if not tenant:
            raise ResourceNotFoundError(f"租户 {tenant_id} 不存在")

        # 获取当前使用量
        current_usage = await self._get_resource_usage(tenant_id, resource_type)
        max_limit = self._get_resource_limit(tenant, resource_type)

        if max_limit is None:
            return ResourceQuotaCheck(
                can_access=True,
                current_usage=current_usage,
                max_limit=-1,
                usage_percentage=0.0,
            )

        new_usage = current_usage + additional_amount
        usage_percentage = (new_usage / max_limit) * 100 if max_limit > 0 else 0

        can_access = new_usage <= max_limit
        reason = None if can_access else f"资源配额超限: {new_usage}/{max_limit}"

        return ResourceQuotaCheck(
            can_access=can_access,
            current_usage=current_usage,
            max_limit=max_limit,
            usage_percentage=usage_percentage,
            reason=reason,
        )

    async def update_usage_metrics(
        self, tenant_id: int, metrics: Dict[str, Any]
    ) -> None:
        """更新使用指标"""
        tenant = await self.get_tenant_by_id(tenant_id)
        if not tenant:
            return None
        tenant.update_usage_metrics(metrics)
        await self.db.commit()

    # ==================== 租户统计和分析 ====================

    async def get_tenant_statistics(self, tenant_id: int) -> Dict[str, Any]:
        """获取租户统计信息"""
        tenant = await self.get_tenant_by_id(tenant_id)
        if not tenant:
            raise ResourceNotFoundError(f"租户 {tenant_id} 不存在")

        # 获取用户统计
        user_stats = await self._get_tenant_user_stats(tenant_id)

        # 获取预测统计
        prediction_stats = await self._get_tenant_prediction_stats(tenant_id)

        # 获取API使用统计
        api_stats = await self._get_tenant_api_stats(tenant_id)

        return {
            "tenant_info": {
                "id": tenant.id,
                "name": tenant.name,
                "plan": tenant.plan,
                "status": tenant.status,
                "created_at": tenant.created_at.isoformat(),
                "is_trial": tenant.is_trial,
                "days_until_expiry": tenant.days_until_expiry,
                "usage_percentage": tenant.usage_percentage,
            },
            "user_statistics": user_stats,
            "prediction_statistics": prediction_stats,
            "api_statistics": api_stats,
            "quota_status": {
                "users": await self.check_resource_quota(tenant_id, "users", 0),
                "predictions_daily": await self.check_resource_quota(
                    tenant_id, "daily_predictions", 0
                ),
                "api_calls_hourly": await self.check_resource_quota(
                    tenant_id, "hourly_api_calls", 0
                ),
                "storage": await self.check_resource_quota(tenant_id, "storage_mb", 0),
            },
        }

    # ==================== 私有辅助方法 ====================

    def _get_default_features_for_plan(self, plan: TenantPlan) -> Dict[str, bool]:
        """获取计划对应的默认功能"""
        features = {
            "basic_predictions": True,
            "data_export": False,
            "custom_models": False,
            "api_access": True,
            "advanced_analytics": False,
            "white_label": False,
            "priority_support": False,
            "custom_integrations": False,
        }

        if plan == TenantPlan.PROFESSIONAL:
            features.update(
                {
                    "data_export": True,
                    "advanced_analytics": True,
                    "priority_support": True,
                }
            )
        elif plan == TenantPlan.ENTERPRISE:
            features.update(
                {
                    "data_export": True,
                    "custom_models": True,
                    "advanced_analytics": True,
                    "white_label": True,
                    "priority_support": True,
                    "custom_integrations": True,
                }
            )
        elif plan == TenantPlan.CUSTOM:
            # 自定义计划启用所有功能
            for key in features:
                features[key] = True

        return features

    async def _apply_plan_quotas(self, tenant: Tenant, plan: TenantPlan) -> None:
        """应用计划配额"""
        quotas = {
            TenantPlan.BASIC: {
                "max_users": 10,
                "max_predictions_per_day": 100,
                "max_api_calls_per_hour": 1000,
                "storage_quota_mb": 100,
            },
            TenantPlan.PROFESSIONAL: {
                "max_users": 50,
                "max_predictions_per_day": 1000,
                "max_api_calls_per_hour": 10000,
                "storage_quota_mb": 1000,
            },
            TenantPlan.ENTERPRISE: {
                "max_users": 200,
                "max_predictions_per_day": 10000,
                "max_api_calls_per_hour": 100000,
                "storage_quota_mb": 10000,
            },
            TenantPlan.CUSTOM: {
                "max_users": 1000,
                "max_predictions_per_day": 100000,
                "max_api_calls_per_hour": 1000000,
                "storage_quota_mb": 100000,
            },
        }

        plan_quotas = quotas.get(plan, quotas[TenantPlan.BASIC])
        for field, value in plan_quotas.items():
            if hasattr(tenant, field):
                setattr(tenant, field, value)

    async def _create_default_roles(self, tenant_id: int) -> None:
        """创建默认角色"""
        default_roles = [
            {
                "name": "租户管理员",
                "code": "tenant_admin",
                "description": "租户管理员,拥有所有权限",
                "level": 10,
                "permissions": [
                    "tenant.manage",
                    "users.manage",
                    "roles.manage",
                    "predictions.manage",
                    "data.manage",
                    "settings.manage",
                ],
            },
            {
                "name": "数据分析师",
                "code": "analyst",
                "description": "数据分析师,可以查看和分析数据",
                "level": 5,
                "permissions": [
                    "predictions.view",
                    "predictions.create",
                    "data.view",
                    "analytics.view",
                    "reports.view",
                ],
            },
            {
                "name": "普通用户",
                "code": "user",
                "description": "普通用户,基本使用权限",
                "level": 1,
                "permissions": ["predictions.view", "predictions.create", "data.view"],
            },
        ]

        for role_data in default_roles:
            role = TenantRole(tenant_id=tenant_id, **role_data, is_system_role=True)
            self.db.add(role)

        await self.db.flush()

    async def _get_user_roles(
        self, user_id: int, tenant_id: int
    ) -> List[UserRoleAssignment]:
        """获取用户在租户内的角色"""
        result = await self.db.execute(
            select(UserRoleAssignment)
            .options(selectinload(UserRoleAssignment.role))
            .where(
                and_(
                    UserRoleAssignment.user_id == user_id,
                    UserRoleAssignment.tenant_id == tenant_id,
                    UserRoleAssignment.is_active,
                )
            )
        )
        return result.scalars().all()

    async def _get_tenant_role(
        self, tenant_id: int, role_code: str
    ) -> Optional[TenantRole]:
        """获取租户角色"""
        result = await self.db.execute(
            select(TenantRole).where(
                and_(
                    TenantRole.tenant_id == tenant_id,
                    TenantRole.code == role_code,
                    TenantRole.is_active,
                )
            )
        )
        return result.scalar_one_or_none()

    async def _get_role_permissions(self, role_id: int) -> List["RolePermission"]:
        """获取角色权限"""
        result = await self.db.execute(
            select(RolePermission)
            .options(selectinload(RolePermission.permission))
            .where(RolePermission.role_id == role_id)
        )
        return result.scalars().all()

    async def _get_user_role_assignment(
        self, user_id: int, tenant_id: int, role_id: int
    ) -> Optional[UserRoleAssignment]:
        """获取用户角色分配"""
        result = await self.db.execute(
            select(UserRoleAssignment).where(
                and_(
                    UserRoleAssignment.user_id == user_id,
                    UserRoleAssignment.tenant_id == tenant_id,
                    UserRoleAssignment.role_id == role_id,
                )
            )
        )
        return result.scalar_one_or_none()

    def _get_resource_limit(self, tenant: Tenant, resource_type: str) -> Optional[int]:
        """获取资源限制"""
        limits = {
            "users": tenant.max_users,
            "daily_predictions": tenant.max_predictions_per_day,
            "hourly_api_calls": tenant.max_api_calls_per_hour,
            "storage_mb": tenant.storage_quota_mb,
        }
        return limits.get(resource_type)

    async def _get_resource_usage(self, tenant_id: int, resource_type: str) -> int:
        """获取资源使用量"""
        # 这里应该从实际的统计数据中获取
        # 暂时返回模拟数据
        return 0

    async def _get_tenant_user_stats(self, tenant_id: int) -> Dict[str, Any]:
        """获取租户用户统计"""
        # 模拟统计数据
        return {
            "total_users": 5,
            "active_users": 3,
            "new_users_this_month": 1,
            "users_by_role": {"tenant_admin": 1, "analyst": 2, "user": 2},
        }

    async def _get_tenant_prediction_stats(self, tenant_id: int) -> Dict[str, Any]:
        """获取租户预测统计"""
        # 模拟统计数据
        return {
            "total_predictions": 150,
            "successful_predictions": 95,
            "success_rate": 63.3,
            "predictions_this_month": 45,
            "average_confidence": 0.75,
        }

    async def _get_tenant_api_stats(self, tenant_id: int) -> Dict[str, Any]:
        """获取租户API统计"""
        # 模拟统计数据
        return {
            "total_api_calls": 2500,
            "api_calls_today": 85,
            "average_response_time_ms": 120,
            "success_rate": 98.5,
        }


# ==================== 租户工厂 ====================


class TenantServiceFactory:
    """类文档字符串"""
    pass  # 添加pass语句
    """租户服务工厂"""

    @staticmethod
    def create_service(db: AsyncSession) -> TenantService:
        """创建租户服务实例"""
        return TenantService(db)
