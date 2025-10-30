"""
多租户系统集成测试
Multi-Tenant System Integration Tests

测试企业级多租户系统的核心功能，包括租户管理、权限控制、
资源配额等。
"""

import pytest
import asyncio
from datetime import datetime, timedelta
from typing import Dict, Any

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from src.database.models.tenant import (
    Tenant, TenantRole, TenantPermission, UserRoleAssignment,
    TenantStatus, TenantPlan, PermissionScope
)
from src.database.models.user import User, UserRole
from src.services.tenant_service import (
    TenantService, TenantCreationRequest, ResourceQuotaCheck, PermissionCheckResult
)
from src.services.auth_service import AuthService


class TestTenantManagement:
    """租户管理测试"""

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_create_tenant_success(self, db_session: AsyncSession):
        """测试成功创建租户"""
        tenant_service = TenantService(db_session)

        # 创建租户请求
        request = TenantCreationRequest(
            name="测试租户",
            slug="test-tenant",
            contact_email="test@example.com",
            company_name="测试公司",
            description="这是一个测试租户",
            plan=TenantPlan.PROFESSIONAL,
            max_users=20,
            trial_days=30
        )

        # 创建租户
        tenant = await tenant_service.create_tenant(request)

        # 验证租户创建成功
        assert tenant is not None
        assert tenant.name == "测试租户"
        assert tenant.slug == "test-tenant"
        assert tenant.contact_email == "test@example.com"
        assert tenant.company_name == "测试公司"
        assert tenant.plan == TenantPlan.PROFESSIONAL
        assert tenant.status == TenantStatus.TRIAL
        assert tenant.max_users == 20
        assert tenant.is_trial is True
        assert tenant.is_active is True

        # 验证默认角色已创建
        result = await db_session.execute(
            select(TenantRole).where(TenantRole.tenant_id == tenant.id)
        )
        roles = result.scalars().all()
        assert len(roles) >= 3  # 至少有3个默认角色

        # 验证角色代码
        role_codes = [role.code for role in roles]
        assert "tenant_admin" in role_codes
        assert "analyst" in role_codes
        assert "user" in role_codes

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_create_tenant_duplicate_slug(self, db_session: AsyncSession):
        """测试创建重复标识符的租户"""
        tenant_service = TenantService(db_session)

        # 创建第一个租户
        request1 = TenantCreationRequest(
            name="租户1",
            slug="duplicate-test",
            contact_email="test1@example.com"
        )
        await tenant_service.create_tenant(request1)

        # 尝试创建相同标识符的租户
        request2 = TenantCreationRequest(
            name="租户2",
            slug="duplicate-test",  # 相同的标识符
            contact_email="test2@example.com"
        )

        with pytest.raises(Exception):  # 应该抛出验证错误
            await tenant_service.create_tenant(request2)

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_get_tenant_by_id(self, db_session: AsyncSession):
        """测试根据ID获取租户"""
        tenant_service = TenantService(db_session)

        # 创建租户
        request = TenantCreationRequest(
            name="查询测试租户",
            slug="query-test",
            contact_email="query@example.com"
        )
        created_tenant = await tenant_service.create_tenant(request)

        # 查询租户
        found_tenant = await tenant_service.get_tenant_by_id(created_tenant.id)

        assert found_tenant is not None
        assert found_tenant.id == created_tenant.id
        assert found_tenant.name == "查询测试租户"
        assert found_tenant.slug == "query-test"

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_update_tenant(self, db_session: AsyncSession):
        """测试更新租户信息"""
        tenant_service = TenantService(db_session)

        # 创建租户
        request = TenantCreationRequest(
            name="更新测试租户",
            slug="update-test",
            contact_email="update@example.com"
        )
        tenant = await tenant_service.create_tenant(request)

        # 更新租户
        updates = {
            "name": "更新后的租户名称",
            "description": "更新后的描述",
            "company_name": "更新后的公司名称"
        }
        updated_tenant = await tenant_service.update_tenant(tenant.id, updates)

        assert updated_tenant.name == "更新后的租户名称"
        assert updated_tenant.description == "更新后的描述"
        assert updated_tenant.company_name == "更新后的公司名称"
        assert updated_tenant.slug == "update-test"  # 标识符不应该改变

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_suspend_and_activate_tenant(self, db_session: AsyncSession):
        """测试暂停和激活租户"""
        tenant_service = TenantService(db_session)

        # 创建租户
        request = TenantCreationRequest(
            name="状态测试租户",
            slug="status-test",
            contact_email="status@example.com"
        )
        tenant = await tenant_service.create_tenant(request)

        # 暂停租户
        suspended_tenant = await tenant_service.suspend_tenant(
            tenant.id, "测试暂停"
        )
        assert suspended_tenant.status == TenantStatus.SUSPENDED

        # 激活租户
        activated_tenant = await tenant_service.activate_tenant(
            tenant.id, TenantPlan.ENTERPRISE
        )
        assert activated_tenant.status == TenantStatus.ACTIVE
        assert activated_tenant.plan == TenantPlan.ENTERPRISE


class TestPermissionManagement:
    """权限管理测试"""

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_assign_user_role(self, db_session: AsyncSession):
        """测试为用户分配角色"""
        tenant_service = TenantService(db_session)
        auth_service = AuthService(db_session)

        # 创建租户
        tenant_request = TenantCreationRequest(
            name="权限测试租户",
            slug="permission-test",
            contact_email="permission@example.com"
        )
        tenant = await tenant_service.create_tenant(tenant_request)

        # 创建用户
        user = await auth_service.register_user(
            username="testuser",
            email="user@example.com",
            password="testpass123",
            first_name="测试",
            last_name="用户"
        )

        # 为用户分配角色
        assignment = await tenant_service.assign_user_role(
            user_id=user.id,
            tenant_id=tenant.id,
            role_code="analyst",
            assigned_by=user.id
        )

        assert assignment is not None
        assert assignment.user_id == user.id
        assert assignment.tenant_id == tenant.id
        assert assignment.is_active is True

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_check_user_permission(self, db_session: AsyncSession):
        """测试检查用户权限"""
        tenant_service = TenantService(db_session)
        auth_service = AuthService(db_session)

        # 创建租户
        tenant_request = TenantCreationRequest(
            name="权限检查测试租户",
            slug="permission-check-test",
            contact_email="permcheck@example.com"
        )
        tenant = await tenant_service.create_tenant(tenant_request)

        # 创建用户
        user = await auth_service.register_user(
            username="permuser",
            email="permuser@example.com",
            password="testpass123"
        )

        # 为用户分配管理员角色
        await tenant_service.assign_user_role(
            user_id=user.id,
            tenant_id=tenant.id,
            role_code="tenant_admin",
            assigned_by=user.id
        )

        # 检查用户权限
        permission_result = await tenant_service.check_user_permission(
            user_id=user.id,
            tenant_id=tenant.id,
            permission_code="tenant.manage"
        )

        assert permission_result.granted is True
        assert "tenant.manage" in permission_result.permissions

        # 检查用户没有的权限
        no_permission_result = await tenant_service.check_user_permission(
            user_id=user.id,
            tenant_id=tenant.id,
            permission_code="nonexistent.permission"
        )

        assert no_permission_result.granted is False

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_revoke_user_role(self, db_session: AsyncSession):
        """测试撤销用户角色"""
        tenant_service = TenantService(db_session)
        auth_service = AuthService(db_session)

        # 创建租户
        tenant_request = TenantCreationRequest(
            name="角色撤销测试租户",
            slug="revoke-test",
            contact_email="revoke@example.com"
        )
        tenant = await tenant_service.create_tenant(tenant_request)

        # 创建用户
        user = await auth_service.register_user(
            username="revokeuser",
            email="revoke@example.com",
            password="testpass123"
        )

        # 分配角色
        await tenant_service.assign_user_role(
            user_id=user.id,
            tenant_id=tenant.id,
            role_code="analyst",
            assigned_by=user.id
        )

        # 验证权限
        permission_result_before = await tenant_service.check_user_permission(
            user_id=user.id,
            tenant_id=tenant.id,
            permission_code="predictions.view"
        )
        assert permission_result_before.granted is True

        # 撤销角色
        success = await tenant_service.revoke_user_role(
            user_id=user.id,
            tenant_id=tenant.id,
            role_code="analyst"
        )
        assert success is True

        # 验证权限已撤销
        permission_result_after = await tenant_service.check_user_permission(
            user_id=user.id,
            tenant_id=tenant.id,
            permission_code="predictions.view"
        )
        assert permission_result_after.granted is False


class TestResourceQuota:
    """资源配额测试"""

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_check_resource_quota(self, db_session: AsyncSession):
        """测试检查资源配额"""
        tenant_service = TenantService(db_session)

        # 创建租户
        tenant_request = TenantCreationRequest(
            name="配额测试租户",
            slug="quota-test",
            contact_email="quota@example.com",
            max_users=5,
            max_predictions_per_day=100
        )
        tenant = await tenant_service.create_tenant(tenant_request)

        # 检查用户配额
        quota_check = await tenant_service.check_resource_quota(
            tenant_id=tenant.id,
            resource_type="users",
            additional_amount=3
        )

        assert isinstance(quota_check, ResourceQuotaCheck)
        assert quota_check.can_access is True
        assert quota_check.current_usage == 0  # 初始使用量为0
        assert quota_check.max_limit == 5
        assert quota_check.usage_percentage == 0.0

        # 检查超出配额的情况
        quota_check_exceeded = await tenant_service.check_resource_quota(
            tenant_id=tenant.id,
            resource_type="users",
            additional_amount=10  # 超出最大用户数
        )

        assert quota_check_exceeded.can_access is False
        assert "配额超限" in quota_check_exceeded.reason

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_update_usage_metrics(self, db_session: AsyncSession):
        """测试更新使用指标"""
        tenant_service = TenantService(db_session)

        # 创建租户
        tenant_request = TenantCreationRequest(
            name="使用指标测试租户",
            slug="metrics-test",
            contact_email="metrics@example.com"
        )
        tenant = await tenant_service.create_tenant(tenant_request)

        # 更新使用指标
        metrics = {
            "current_users": 3,
            "daily_predictions": 25,
            "hourly_api_calls": 150,
            "storage_used_mb": 45
        }

        await tenant_service.update_usage_metrics(tenant.id, metrics)

        # 验证指标已更新
        updated_tenant = await tenant_service.get_tenant_by_id(tenant.id)
        assert updated_tenant.usage_metrics is not None
        assert updated_tenant.usage_metrics["current_users"] == 3
        assert updated_tenant.usage_metrics["daily_predictions"] == 25
        assert updated_tenant.usage_metrics["hourly_api_calls"] == 150
        assert updated_tenant.usage_metrics["storage_used_mb"] == 45


class TestTenantStatistics:
    """租户统计测试"""

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_get_tenant_statistics(self, db_session: AsyncSession):
        """测试获取租户统计信息"""
        tenant_service = TenantService(db_session)

        # 创建租户
        tenant_request = TenantCreationRequest(
            name="统计测试租户",
            slug="stats-test",
            contact_email="stats@example.com"
        )
        tenant = await tenant_service.create_tenant(tenant_request)

        # 获取统计信息
        stats = await tenant_service.get_tenant_statistics(tenant.id)

        # 验证统计信息结构
        assert "tenant_info" in stats
        assert "user_statistics" in stats
        assert "prediction_statistics" in stats
        assert "api_statistics" in stats
        assert "quota_status" in stats

        # 验证租户基本信息
        tenant_info = stats["tenant_info"]
        assert tenant_info["id"] == tenant.id
        assert tenant_info["name"] == tenant.name
        assert tenant_info["plan"] == tenant.plan.value
        assert tenant_info["status"] == tenant.status.value

        # 验证配额状态
        quota_status = stats["quota_status"]
        assert "users" in quota_status
        assert "predictions_daily" in quota_status
        assert "api_calls_hourly" in quota_status
        assert "storage" in quota_status

        # 验证配额检查结果
        for quota_name, quota_check in quota_status.items():
            assert isinstance(quota_check, dict)
            assert "can_access" in quota_check
            assert "current_usage" in quota_check
            assert "max_limit" in quota_check
            assert "usage_percentage" in quota_check


class TestTenantLifecycle:
    """租户生命周期测试"""

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_trial_to_active_transition(self, db_session: AsyncSession):
        """测试试用到激活的转换"""
        tenant_service = TenantService(db_session)

        # 创建试用租户
        tenant_request = TenantCreationRequest(
            name="生命周期测试租户",
            slug="lifecycle-test",
            contact_email="lifecycle@example.com",
            trial_days=1  # 1天试用
        )
        tenant = await tenant_service.create_tenant(tenant_request)

        # 验证初始状态
        assert tenant.status == TenantStatus.TRIAL
        assert tenant.is_trial is True
        assert tenant.trial_ends_at is not None

        # 激活租户
        activated_tenant = await tenant_service.activate_tenant(
            tenant.id, TenantPlan.PROFESSIONAL
        )

        # 验证激活后状态
        assert activated_tenant.status == TenantStatus.ACTIVE
        assert activated_tenant.is_trial is False
        assert activated_tenant.plan == TenantPlan.PROFESSIONAL
        assert activated_tenant.subscription_ends_at is not None

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_subscription_expiry(self, db_session: AsyncSession):
        """测试订阅过期逻辑"""
        tenant_service = TenantService(db_session)

        # 创建已过期的租户
        tenant_request = TenantCreationRequest(
            name="过期测试租户",
            slug="expiry-test",
            contact_email="expiry@example.com"
        )
        tenant = await tenant_service.create_tenant(tenant_request)

        # 手动设置过期时间为过去
        from sqlalchemy import update
        await db_session.execute(
            update(Tenant)
            .where(Tenant.id == tenant.id)
            .values(
                subscription_ends_at=datetime.utcnow() - timedelta(days=1),
                status=TenantStatus.ACTIVE
            )
        )
        await db_session.commit()

        # 重新加载租户
        expired_tenant = await tenant_service.get_tenant_by_id(tenant.id)

        # 验证过期状态
        assert expired_tenant.is_subscription_active is False
        assert expired_tenant.days_until_expiry is not None
        assert expired_tenant.days_until_expiry <= 0


# ==================== 测试辅助函数 ====================

@pytest.fixture
async def sample_tenant(db_session: AsyncSession) -> Tenant:
    """创建示例租户"""
    tenant_service = TenantService(db_session)
    request = TenantCreationRequest(
        name="示例租户",
        slug="sample-tenant",
        contact_email="sample@example.com"
    )
    return await tenant_service.create_tenant(request)


@pytest.fixture
async def sample_user(db_session: AsyncSession) -> User:
    """创建示例用户"""
    auth_service = AuthService(db_session)
    return await auth_service.register_user(
        username="sampleuser",
        email="sample@example.com",
        password="testpass123",
        first_name="示例",
        last_name="用户"
    )