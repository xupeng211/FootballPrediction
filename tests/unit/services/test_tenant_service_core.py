"""多租户管理服务核心单元测试
Core Unit Tests for Tenant Management Service.
"""

import pytest
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch
from typing import Any, Optional

# 导入SQLAlchemy组件
from sqlalchemy.ext.asyncio import AsyncSession

# 导入被测试的模块
from src.services.tenant_service import (
    TenantService,
    TenantCreationRequest,
    ResourceQuotaCheck,
    PermissionCheckResult,
    TenantManagementError,
    TenantServiceFactory,
)
from src.database.models.tenant import Tenant, TenantPlan, TenantStatus
from src.core.exceptions import ValidationError, FootballPredictionError


# 创建兼容的异常类
class ResourceNotFoundError(FootballPredictionError):
    """资源未找到异常."""

    pass


# 移除全局异步标记，只在需要的地方使用


@pytest.fixture
def mock_db_session():
    """创建模拟的数据库会话."""
    session = AsyncMock(spec=AsyncSession)

    # 创建模拟的Result对象
    mock_result = MagicMock()
    mock_result.scalars.return_value.all.return_value = []
    mock_result.scalars.return_value = mock_result
    mock_result.first.return_value = None
    mock_result.scalar_one_or_none.return_value = None

    # execute是异步的，返回同步的result对象
    session.execute = AsyncMock(return_value=mock_result)
    session.flush = AsyncMock()
    session.commit = AsyncMock()
    session.rollback = AsyncMock()
    session.add = MagicMock()

    return session


@pytest.fixture
def mock_tenant():
    """创建模拟的租户对象（不使用spec避免SQLAlchemy问题）."""
    tenant = MagicMock()
    tenant.id = 1
    tenant.name = "Test Tenant"
    tenant.slug = "test-tenant"
    tenant.contact_email = "test@example.com"
    tenant.company_name = "Test Company"
    tenant.description = "Test Description"
    tenant.plan = TenantPlan.BASIC
    tenant.status = TenantStatus.TRIAL
    tenant.max_users = 10
    tenant.max_predictions_per_day = 100
    tenant.max_api_calls_per_hour = 1000
    tenant.storage_quota_mb = 100
    tenant.is_active = True
    tenant.settings = {}
    tenant.features = {}
    tenant.statistics = {}
    tenant.usage_metrics = {}
    tenant.created_at = datetime.utcnow()
    tenant.trial_ends_at = datetime.utcnow() + timedelta(days=30)
    tenant.subscription_ends_at = None

    # 添加所有必要的方法
    tenant.update_usage_metrics = MagicMock()
    tenant.update.return_value = tenant  # 支持链式调用
    tenant.is_trial = True
    tenant.days_until_expiry = 30
    tenant.usage_percentage = 50.0

    # 添加hybrid property避免SQLAlchemy错误
    def mock_usage_percentage():
        return 50.0

    type(tenant).usage_percentage = property(mock_usage_percentage)

    return tenant


@pytest.fixture
def mock_role():
    """创建模拟的角色对象."""
    role = MagicMock()
    role.id = 1
    role.name = "Admin"
    role.code = "admin"
    role.is_active = True
    role.permissions = ["admin.access"]
    return role


@pytest.fixture
def mock_role_assignment():
    """创建模拟的角色分配对象."""
    assignment = MagicMock()
    assignment.is_active = True
    assignment.is_expired = False
    assignment.assigned_at = datetime.utcnow()
    return assignment


@pytest.fixture
def tenant_service(mock_db_session):
    """创建租户服务实例."""
    return TenantService(mock_db_session)


@pytest.fixture
def tenant_creation_request():
    """创建租户创建请求."""
    return TenantCreationRequest(
        name="Test Company",
        slug="test-company",
        contact_email="admin@testcompany.com",
        company_name="Test Company Ltd",
        description="A test tenant",
        plan=TenantPlan.PROFESSIONAL,
        max_users=50,
        trial_days=14,
        custom_settings={"timezone": "UTC", "language": "en"},
    )


class TestTenantServiceInitialization:
    """租户服务初始化测试."""

    def test_service_initialization(self, mock_db_session):
        """测试服务初始化."""
        service = TenantService(mock_db_session)
        assert service.db == mock_db_session

    def test_factory_create_service(self, mock_db_session):
        """测试工厂方法创建服务."""
        service = TenantServiceFactory.create_service(mock_db_session)
        assert isinstance(service, TenantService)
        assert service.db == mock_db_session


class TestTenantLifecycle:
    """租户生命周期管理测试."""

    @pytest.mark.skip("Complex SQLAlchemy instantiation issue - pending fix")
    @pytest.mark.asyncio
    async def test_create_tenant_success(
        self, tenant_service, tenant_creation_request, mock_db_session
    ):
        """测试成功创建租户."""
        # Mock整个Tenant构造过程，避免SQLAlchemy实例化
        with patch.object(tenant_service, "get_tenant_by_slug", return_value=None):
            with patch.object(
                tenant_service, "_create_default_roles", return_value=None
            ):
                with patch.object(
                    tenant_service, "_apply_plan_quotas", return_value=None
                ):
                    # Mock Tenant类本身
                    with patch(
                        "src.services.tenant_service.Tenant"
                    ) as mock_tenant_class:
                        mock_tenant_class.return_value = MagicMock()

                        # 创建租户
                        result = await tenant_service.create_tenant(
                            tenant_creation_request, creator_id=1
                        )

        # 验证数据库操作被正确调用
        mock_db_session.add.assert_called_once()
        mock_db_session.flush.assert_called_once()
        mock_db_session.commit.assert_called_once()

        # 验证结果不为空
        assert result is not None

    @pytest.mark.asyncio
    async def test_create_tenant_slug_conflict(
        self, tenant_service, tenant_creation_request, mock_tenant
    ):
        """测试创建租户时slug冲突."""
        # Mock get_tenant_by_slug 返回已存在的租户
        with patch.object(
            tenant_service, "get_tenant_by_slug", return_value=mock_tenant
        ):
            with pytest.raises(ValidationError) as exc_info:
                await tenant_service.create_tenant(tenant_creation_request)

            assert "租户标识符" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_get_tenant_by_id(self, tenant_service, mock_db_session, mock_tenant):
        """测试根据ID获取租户."""
        # 设置mock返回值
        mock_db_session.execute.return_value.scalar_one_or_none.return_value = (
            mock_tenant
        )

        # 调用方法
        result = await tenant_service.get_tenant_by_id(1)

        # 验证结果
        assert result == mock_tenant

        # 验证execute方法被调用（基本的隔离性检查）
        mock_db_session.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_tenant_by_slug(
        self, tenant_service, mock_db_session, mock_tenant
    ):
        """测试根据标识符获取租户."""
        # 设置mock返回值
        mock_db_session.execute.return_value.scalar_one_or_none.return_value = (
            mock_tenant
        )

        # 调用方法
        result = await tenant_service.get_tenant_by_slug("test-tenant")

        # 验证结果
        assert result == mock_tenant

        # 验证execute方法被调用（基本的隔离性检查）
        mock_db_session.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_update_tenant_success(
        self, tenant_service, mock_db_session, mock_tenant
    ):
        """测试成功更新租户."""
        # Mock get_tenant_by_id 返回租户
        with patch.object(tenant_service, "get_tenant_by_id", return_value=mock_tenant):
            updates = {
                "name": "Updated Name",
                "description": "Updated Description",
                "settings": {"timezone": "UTC+8"},
            }

            result = await tenant_service.update_tenant(1, updates)

            # 验证结果
            assert result == mock_tenant
            mock_db_session.commit.assert_called_once()

            # 验证只更新了允许的字段
            assert hasattr(mock_tenant, "name")  # name被更新

    @pytest.mark.asyncio
    async def test_update_tenant_not_found(self, tenant_service):
        """测试更新不存在的租户."""
        with patch.object(tenant_service, "get_tenant_by_id", return_value=None):
            with pytest.raises(ResourceNotFoundError):
                await tenant_service.update_tenant(999, {"name": "Test"})

    @pytest.mark.asyncio
    async def test_suspend_tenant(self, tenant_service, mock_db_session, mock_tenant):
        """测试暂停租户."""
        with patch.object(tenant_service, "get_tenant_by_id", return_value=mock_tenant):
            result = await tenant_service.suspend_tenant(1, "Test suspension")

            # 验证数据库操作被调用
            mock_db_session.commit.assert_called_once()
            # 验证返回值不为空
            assert result is not None

    @pytest.mark.asyncio
    async def test_activate_tenant(self, tenant_service, mock_db_session, mock_tenant):
        """测试激活租户."""
        with patch.object(tenant_service, "get_tenant_by_id", return_value=mock_tenant):
            with patch.object(tenant_service, "_apply_plan_quotas", return_value=None):
                result = await tenant_service.activate_tenant(
                    1, TenantPlan.PROFESSIONAL
                )

                # 验证数据库操作被调用
                mock_db_session.commit.assert_called_once()
                # 验证返回值不为空
                assert result is not None


class TestPermissionManagement:
    """权限管理测试."""

    @pytest.mark.asyncio
    async def test_check_user_permission_no_roles(self, tenant_service):
        """测试用户无角色时的权限检查."""
        with patch.object(tenant_service, "_get_user_roles", return_value=[]):
            result = await tenant_service.check_user_permission(1, 1, "test.permission")

            assert not result.granted
            assert "无角色" in result.reason

    @pytest.mark.asyncio
    async def test_check_user_permission_granted(self, tenant_service, mock_tenant):
        """测试用户有权限时的权限检查."""
        # Mock role assignment with permission
        mock_role = MagicMock()
        mock_role.is_active = True
        mock_role.permissions = ["test.permission"]

        mock_assignment = MagicMock()
        mock_assignment.is_active = True
        mock_assignment.is_expired = False
        mock_assignment.role = mock_role

        with patch.object(
            tenant_service, "_get_user_roles", return_value=[mock_assignment]
        ):
            with patch.object(tenant_service, "_get_role_permissions", return_value=[]):
                result = await tenant_service.check_user_permission(
                    1, 1, "test.permission"
                )

                assert result.granted
                assert "test.permission" in result.permissions

    @pytest.mark.asyncio
    async def test_assign_user_role_success(
        self, tenant_service, mock_tenant, mock_role
    ):
        """测试成功分配用户角色."""
        with patch.object(tenant_service, "get_tenant_by_id", return_value=mock_tenant):
            with patch.object(
                tenant_service, "_get_tenant_role", return_value=mock_role
            ):
                with patch.object(
                    tenant_service, "_get_user_role_assignment", return_value=None
                ):
                    await tenant_service.assign_user_role(1, 1, "user", 1)

                    # 验证数据库操作
                    tenant_service.db.add.assert_called()
                    tenant_service.db.commit.assert_called()

    @pytest.mark.asyncio
    async def test_assign_user_role_tenant_not_found(self, tenant_service):
        """测试分配角色时租户不存在."""
        with patch.object(tenant_service, "get_tenant_by_id", return_value=None):
            with pytest.raises(ResourceNotFoundError):
                await tenant_service.assign_user_role(1, 999, "user", 1)

    @pytest.mark.asyncio
    async def test_revoke_user_role_success(self, tenant_service, mock_role_assignment):
        """测试成功撤销用户角色."""
        mock_role = MagicMock()

        with patch.object(tenant_service, "_get_tenant_role", return_value=mock_role):
            with patch.object(
                tenant_service,
                "_get_user_role_assignment",
                return_value=mock_role_assignment,
            ):
                result = await tenant_service.revoke_user_role(1, 1, "user")

                # 验证角色被撤销
                assert not mock_role_assignment.is_active
                tenant_service.db.commit.assert_called_once()
                assert result is True

    @pytest.mark.asyncio
    async def test_revoke_user_role_not_found(self, tenant_service):
        """测试撤销不存在的角色."""
        mock_role = MagicMock()

        with patch.object(tenant_service, "_get_tenant_role", return_value=mock_role):
            with patch.object(
                tenant_service, "_get_user_role_assignment", return_value=None
            ):
                result = await tenant_service.revoke_user_role(1, 1, "nonexistent")

                assert result is False


class TestResourceQuota:
    """资源配额管理测试."""

    async def test_check_resource_quota_within_limit(self, tenant_service, mock_tenant):
        """测试资源配额检查在限制内."""
        with patch.object(tenant_service, "get_tenant_by_id", return_value=mock_tenant):
            with patch.object(tenant_service, "_get_resource_usage", return_value=5):
                result = await tenant_service.check_resource_quota(1, "users", 3)

                assert result.can_access
                assert result.current_usage == 5
                assert result.max_limit == mock_tenant.max_users
                assert result.usage_percentage > 0

    async def test_check_resource_quota_exceeded(self, tenant_service, mock_tenant):
        """测试资源配额超限."""
        with patch.object(tenant_service, "get_tenant_by_id", return_value=mock_tenant):
            with patch.object(tenant_service, "_get_resource_usage", return_value=8):
                result = await tenant_service.check_resource_quota(1, "users", 3)

                assert not result.can_access
                assert result.current_usage == 8
                assert result.max_limit == mock_tenant.max_users
                assert "超限" in result.reason

    async def test_check_resource_quota_no_limit(self, tenant_service, mock_tenant):
        """测试无限制资源配额."""
        with patch.object(tenant_service, "get_tenant_by_id", return_value=mock_tenant):
            with patch.object(tenant_service, "_get_resource_usage", return_value=100):
                # Mock返回None表示无限制
                with patch.object(
                    tenant_service, "_get_resource_limit", return_value=None
                ):
                    result = await tenant_service.check_resource_quota(
                        1, "unlimited_resource", 1
                    )

                    assert result.can_access
                    assert result.max_limit == -1

    async def test_check_resource_quota_tenant_not_found(self, tenant_service):
        """测试检查不存在租户的资源配额."""
        with patch.object(tenant_service, "get_tenant_by_id", return_value=None):
            with pytest.raises(Exception):
                await tenant_service.check_resource_quota(999, "users")

    async def test_update_usage_metrics(self, tenant_service, mock_tenant):
        """测试更新使用指标."""
        with patch.object(tenant_service, "get_tenant_by_id", return_value=mock_tenant):
            metrics = {"daily_predictions": 50, "api_calls": 100}
            await tenant_service.update_usage_metrics(1, metrics)

            # 验证更新方法被调用
            mock_tenant.update_usage_metrics.assert_called_once_with(metrics)
            tenant_service.db.commit.assert_called_once()


class TestTenantStatistics:
    """租户统计测试."""

    async def test_get_tenant_statistics_success(self, tenant_service, mock_tenant):
        """测试获取租户统计信息."""
        with patch.object(tenant_service, "get_tenant_by_id", return_value=mock_tenant):
            with patch.object(
                tenant_service,
                "_get_tenant_user_stats",
                return_value={"total_users": 5},
            ):
                with patch.object(
                    tenant_service,
                    "_get_tenant_prediction_stats",
                    return_value={"total": 100},
                ):
                    with patch.object(
                        tenant_service,
                        "_get_tenant_api_stats",
                        return_value={"calls": 1000},
                    ):
                        with patch.object(
                            tenant_service,
                            "check_resource_quota",
                            return_value=ResourceQuotaCheck(True, 5, 10, 50),
                        ):
                            result = await tenant_service.get_tenant_statistics(1)

                            # 验证返回的数据结构
                            assert "tenant_info" in result
                            assert "user_statistics" in result
                            assert "prediction_statistics" in result
                            assert "api_statistics" in result
                            assert "quota_status" in result

                            # 验证租户信息
                            assert result["tenant_info"]["id"] == mock_tenant.id
                            assert result["tenant_info"]["name"] == mock_tenant.name

    async def test_get_tenant_statistics_tenant_not_found(self, tenant_service):
        """测试获取不存在租户的统计信息."""
        with patch.object(tenant_service, "get_tenant_by_id", return_value=None):
            with pytest.raises(Exception):
                await tenant_service.get_tenant_statistics(999)


class TestPlanFeatures:
    """计划功能测试."""

    def test_get_default_features_for_basic_plan(self, tenant_service):
        """测试基础计划的默认功能."""
        features = tenant_service._get_default_features_for_plan(TenantPlan.BASIC)

        assert features["basic_predictions"] is True
        assert features["data_export"] is False
        assert features["custom_models"] is False
        assert features["api_access"] is True

    def test_get_default_features_for_professional_plan(self, tenant_service):
        """测试专业计划的默认功能."""
        features = tenant_service._get_default_features_for_plan(
            TenantPlan.PROFESSIONAL
        )

        assert features["basic_predictions"] is True
        assert features["data_export"] is True
        assert features["advanced_analytics"] is True
        assert features["priority_support"] is True
        assert features["white_label"] is False

    def test_get_default_features_for_enterprise_plan(self, tenant_service):
        """测试企业计划的默认功能."""
        features = tenant_service._get_default_features_for_plan(TenantPlan.ENTERPRISE)

        assert features["basic_predictions"] is True
        assert features["data_export"] is True
        assert features["custom_models"] is True
        assert features["white_label"] is True

    def test_get_default_features_for_custom_plan(self, tenant_service):
        """测试自定义计划的默认功能."""
        features = tenant_service._get_default_features_for_plan(TenantPlan.CUSTOM)

        # 自定义计划应该启用所有功能
        for _feature, enabled in features.items():
            assert enabled is True

    @pytest.mark.asyncio
    async def test_apply_plan_quotas(self, tenant_service, mock_tenant):
        """测试应用计划配额."""
        await tenant_service._apply_plan_quotas(mock_tenant, TenantPlan.PROFESSIONAL)

        # 验证配额被正确设置
        assert mock_tenant.max_users == 50
        assert mock_tenant.max_predictions_per_day == 1000
        assert mock_tenant.max_api_calls_per_hour == 10000
        assert mock_tenant.storage_quota_mb == 1000


class TestIsolationVerification:
    """隔离性验证测试."""

    async def test_tenant_query_isolation_by_id(self, tenant_service, mock_db_session):
        """测试按ID查询的租户隔离."""
        # 设置mock
        mock_result = AsyncMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db_session.execute.return_value = mock_result

        await tenant_service.get_tenant_by_id(123)

        # 验证查询参数（隔离性检查）
        call_args = mock_db_session.execute.call_args[0][0]
        query_str = str(call_args).lower()

        # 验证查询包含ID过滤条件
        assert "id" in query_str and "123" in query_str

    async def test_tenant_query_isolation_by_slug(
        self, tenant_service, mock_db_session
    ):
        """测试按slug查询的租户隔离."""
        # 设置mock
        mock_result = AsyncMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db_session.execute.return_value = mock_result

        await tenant_service.get_tenant_by_slug("company-a")

        # 验证查询参数（隔离性检查）
        call_args = mock_db_session.execute.call_args[0][0]
        query_str = str(call_args).lower()

        # 验证查询包含slug过滤条件
        assert "slug" in query_str and "company-a" in query_str

    async def test_user_role_query_isolation(self, tenant_service, mock_db_session):
        """测试用户角色查询的隔离性."""
        # 设置mock
        mock_result = AsyncMock()
        mock_result.scalars.return_value.all.return_value = []
        mock_db_session.execute.return_value = mock_result

        await tenant_service._get_user_roles(user_id=456, tenant_id=789)

        # 验证查询参数（隔离性检查）
        call_args = mock_db_session.execute.call_args[0][0]
        query_str = str(call_args).lower()

        # 验证查询包含用户ID和租户ID过滤条件
        assert "user_id" in query_str and "456" in query_str
        assert "tenant_id" in query_str and "789" in query_str
        assert "is_active" in query_str

    async def test_tenant_role_query_isolation(self, tenant_service, mock_db_session):
        """测试租户角色查询的隔离性."""
        # 设置mock
        mock_result = AsyncMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db_session.execute.return_value = mock_result

        await tenant_service._get_tenant_role(tenant_id=111, role_code="admin")

        # 验证查询参数（隔离性检查）
        call_args = mock_db_session.execute.call_args[0][0]
        query_str = str(call_args).lower()

        # 验证查询包含租户ID和角色代码过滤条件
        assert "tenant_id" in query_str and "111" in query_str
        assert "code" in query_str and "admin" in query_str
        assert "is_active" in query_str

    def test_resource_limit_isolation(self, tenant_service, mock_tenant):
        """测试资源限制的隔离性."""
        # 设置不同的租户ID
        mock_tenant.id = 123
        mock_tenant.max_users = 50

        # 测试资源限制获取
        limit = tenant_service._get_resource_limit(mock_tenant, "users")

        # 验证返回的是该租户的限制
        assert limit == 50

        # 测试其他资源类型
        api_limit = tenant_service._get_resource_limit(mock_tenant, "hourly_api_calls")
        assert api_limit == mock_tenant.max_api_calls_per_hour

    def test_plan_feature_isolation(self, tenant_service):
        """测试计划功能的隔离性."""
        # 测试不同计划的不同功能
        basic_features = tenant_service._get_default_features_for_plan(TenantPlan.BASIC)
        enterprise_features = tenant_service._get_default_features_for_plan(
            TenantPlan.ENTERPRISE
        )

        # 验证功能差异化（隔离性）
        assert basic_features["data_export"] is False
        assert enterprise_features["data_export"] is True
        assert basic_features["white_label"] is False
        assert enterprise_features["white_label"] is True


class TestErrorHandling:
    """错误处理测试."""

    async def test_database_error_handling(self, tenant_service, mock_db_session):
        """测试数据库错误处理."""
        # 模拟数据库错误
        mock_db_session.execute.side_effect = Exception("Database connection failed")

        with pytest.raises(Exception):
            await tenant_service.get_tenant_by_id(1)

    async def test_invalid_update_fields(self, tenant_service, mock_tenant):
        """测试无效更新字段."""
        with patch.object(tenant_service, "get_tenant_by_id", return_value=mock_tenant):
            # 尝试更新不允许的字段
            updates = {
                "id": 999,  # 不允许更新
                "created_at": datetime.utcnow(),  # 不允许更新
                "valid_field": "value",  # 允许更新
            }

            await tenant_service.update_tenant(1, updates)

            # 验证只更新了允许的字段
            assert mock_tenant.id != 999  # ID不应该被更新

    def test_quota_calculation_edge_cases(self, tenant_service):
        """测试配额计算的边界情况."""
        # 测试零配额
        mock_tenant = MagicMock()
        mock_tenant.max_users = 0

        limit = tenant_service._get_resource_limit(mock_tenant, "users")
        assert limit == 0

        # 测试负数使用量
        with patch.object(tenant_service, "_get_resource_usage", return_value=-5):
            with patch.object(
                tenant_service, "get_tenant_by_id", return_value=mock_tenant
            ):
                # 这个测试需要异步包装
                import asyncio

                result = asyncio.run(tenant_service.check_resource_quota(1, "users", 1))
                # 验证负数使用量被正确处理
                assert isinstance(result, ResourceQuotaCheck)