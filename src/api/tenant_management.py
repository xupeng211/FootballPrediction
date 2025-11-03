"""
多租户管理API
Multi-Tenant Management API

提供企业级多租户系统的REST API接口.
"""

from datetime import datetime
from typing import Any

from fastapi import APIRouter, HTTPException, Query, Request, status
from pydantic import BaseModel, Field, validator

from src.database.base import get_db_session
from src.database.models.tenant import TenantPlan, TenantStatus
from src.middleware.tenant_middleware import (
    check_resource_quota,
    get_tenant_context,
    require_permission,
)
from src.services.tenant_service import (
    TenantCreationRequest,
    TenantService,
)

router = APIRouter(prefix="/api/v1/tenants", tags=["多租户管理"])


# ==================== 请求/响应模型 ==================== None


class TenantCreationRequestModel(BaseModel):
    """租户创建请求模型"""

    name: str = Field(
        ...,
        min_length=1,
        max_length=100,  # TODO: 将魔法数字 100 提取为常量
        description="租户名称",  # TODO: 将魔法数字 100 提取为常量
    )  # TODO: 将魔法数字 100 提取为常量
    slug: str = Field(
        ...,
        min_length=1,
        max_length=50,  # TODO: 将魔法数字 50 提取为常量
        description="租户标识符",  # TODO: 将魔法数字 50 提取为常量
    )  # TODO: 将魔法数字 50 提取为常量
    contact_email: str = Field(..., description="联系邮箱")
    company_name: str | None = Field(
        None,
        max_length=100,  # TODO: 将魔法数字 100 提取为常量
        description="公司名称",  # TODO: 将魔法数字 100 提取为常量
    )  # TODO: 将魔法数字 100 提取为常量
    description: str | None = Field(
        None,
        max_length=500,  # TODO: 将魔法数字 500 提取为常量
        description="租户描述",  # TODO: 将魔法数字 500 提取为常量
    )  # TODO: 将魔法数字 500 提取为常量
    plan: TenantPlan = Field(TenantPlan.BASIC, description="租户计划")
    max_users: int = Field(
        10,
        ge=1,
        le=10000,  # TODO: 将魔法数字 10000 提取为常量
        description="最大用户数",  # TODO: 将魔法数字 10000 提取为常量
    )  # TODO: 将魔法数字 10000 提取为常量
    trial_days: int = Field(
        30,  # TODO: 将魔法数字 30 提取为常量
        ge=1,
        le=365,  # TODO: 将魔法数字 365 提取为常量
        description="试用天数",  # TODO: 将魔法数字 30 提取为常量
    )  # TODO: 将魔法数字 30 提取为常量
    custom_settings: dict[str, Any] | None = Field(None, description="自定义设置")

    @validator("slug")
    def validate_slug(cls, v):  # TODO: 添加返回类型注解  # TODO: 添加返回类型注解  # TODO: 添加返回类型注解  # TODO: 添加返回类型注解  # TODO: 添加返回类型注解  # TODO: 添加返回类型注解  # TODO: 添加返回类型注解  # TODO: 添加返回类型注解  # TODO: 添加返回类型注解
        """验证租户标识符"""
        if not re.match(r"^[a-z0-9-]+$", v):
            raise ValueError("租户标识符只能包含小写字母、数字和连字符")
        return v


class TenantUpdateRequestModel(BaseModel):
    """租户更新请求模型"""

    name: str | None = Field(
        None,
        min_length=1,
        max_length=100,  # TODO: 将魔法数字 100 提取为常量
        description="租户名称",  # TODO: 将魔法数字 100 提取为常量
    )  # TODO: 将魔法数字 100 提取为常量
    description: str | None = Field(
        None,
        max_length=500,  # TODO: 将魔法数字 500 提取为常量
        description="租户描述",  # TODO: 将魔法数字 500 提取为常量
    )  # TODO: 将魔法数字 500 提取为常量
    contact_email: str | None = Field(None, description="联系邮箱")
    contact_phone: str | None = Field(
        None,
        max_length=50,  # TODO: 将魔法数字 50 提取为常量
        description="联系电话",  # TODO: 将魔法数字 50 提取为常量
    )  # TODO: 将魔法数字 50 提取为常量
    company_name: str | None = Field(
        None,
        max_length=100,  # TODO: 将魔法数字 100 提取为常量
        description="公司名称",  # TODO: 将魔法数字 100 提取为常量
    )  # TODO: 将魔法数字 100 提取为常量
    company_address: str | None = Field(
        None,
        max_length=500,  # TODO: 将魔法数字 500 提取为常量
        description="公司地址",  # TODO: 将魔法数字 500 提取为常量
    )  # TODO: 将魔法数字 500 提取为常量
    settings: dict[str, Any] | None = Field(None, description="租户设置")
    features: dict[str, bool] | None = Field(None, description="功能配置")
    branding: dict[str, Any] | None = Field(None, description="品牌定制")


class TenantResponseModel(BaseModel):
    """租户响应模型"""

    id: int
    name: str
    slug: str
    domain: str | None
    description: str | None
    company_name: str | None
    contact_email: str
    status: TenantStatus
    plan: TenantPlan
    max_users: int
    max_predictions_per_day: int
    max_api_calls_per_hour: int
    storage_quota_mb: int
    is_trial: bool
    is_subscription_active: bool
    days_until_expiry: int | None
    usage_percentage: float
    created_at: str
    updated_at: str

    class Config:
        """Pydantic配置"""

        from_attributes = True


class RoleAssignmentRequestModel(BaseModel):
    """角色分配请求模型"""

    role_code: str = Field(..., description="角色代码")
    expires_at: datetime | None = Field(None, description="过期时间")


class PermissionCheckRequestModel(BaseModel):
    """权限检查请求模型"""

    permission_code: str = Field(..., description="权限代码")
    resource_context: dict[str, Any] | None = Field(None, description="资源上下文")


class QuotaCheckResponseModel(BaseModel):
    """配额检查响应模型"""

    can_access: bool
    current_usage: int
    max_limit: int
    usage_percentage: float
    reason: str | None


class TenantStatisticsResponseModel(BaseModel):
    """租户统计响应模型"""

    tenant_info: dict[str, Any]
    user_statistics: dict[str, Any]
    prediction_statistics: dict[str, Any]
    api_statistics: dict[str, Any]
    quota_status: dict[str, QuotaCheckResponseModel]


# ==================== 租户管理端点 ==================== None


@router.post(
    "/", response_model=TenantResponseModel, status_code=status.HTTP_201_CREATED
)
@require_permission("tenant.create")
async def create_tenant(request: Request, tenant_data: TenantCreationRequestModel):
    """
    创建新租户

    需要权限: tenant.create
    """
    async with get_db_session() as db:
        tenant_service = TenantService(db)

        # 获取当前用户ID
        tenant_context = get_tenant_context(request)
        creator_id = tenant_context.user_id if tenant_context else None

        # 创建租户
        creation_request = TenantCreationRequest(
            name=tenant_data.name,
            slug=tenant_data.slug,
            contact_email=tenant_data.contact_email,
            company_name=tenant_data.company_name,
            description=tenant_data.description,
            plan=tenant_data.plan,
            max_users=tenant_data.max_users,
            trial_days=tenant_data.trial_days,
            custom_settings=tenant_data.custom_settings,
        )

        tenant = await tenant_service.create_tenant(creation_request, creator_id)
        return TenantResponseModel.from_orm(tenant)


@router.get("/{tenant_id}", response_model=TenantResponseModel)
@require_permission("tenant.view")
async def get_tenant(tenant_id: int):
    """
    获取租户详情

    需要权限: tenant.view
    """
    async with get_db_session() as db:
        tenant_service = TenantService(db)
        tenant = await tenant_service.get_tenant_by_id(tenant_id)

        if not tenant:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="租户不存在"
            )

        return TenantResponseModel.from_orm(tenant)


@router.put("/{tenant_id}", response_model=TenantResponseModel)
@require_permission("tenant.manage")
async def update_tenant(tenant_id: int, update_data: TenantUpdateRequestModel):
    """
    更新租户信息

    需要权限: tenant.manage
    """
    async with get_db_session() as db:
        tenant_service = TenantService(db)

        # 构建更新数据
        updates = {}
        for field, value in update_data.dict(exclude_unset=True).items():
            updates[field] = value

        tenant = await tenant_service.update_tenant(tenant_id, updates)
        return TenantResponseModel.from_orm(tenant)


@router.post("/{tenant_id}/suspend")
@require_permission("tenant.manage")
async def suspend_tenant(
    tenant_id: int, reason: str = Query(..., description="暂停原因")
):
    """
    暂停租户

    需要权限: tenant.manage
    """
    async with get_db_session() as db:
        tenant_service = TenantService(db)
        tenant = await tenant_service.suspend_tenant(tenant_id, reason)
        return {"message": "租户已暂停", "tenant_id": tenant.id}


@router.post("/{tenant_id}/activate")
@require_permission("tenant.manage")
async def activate_tenant(
    tenant_id: int, plan: TenantPlan | None = Query(None, description="租户计划")
):
    """
    激活租户

    需要权限: tenant.manage
    """
    async with get_db_session() as db:
        tenant_service = TenantService(db)
        tenant = await tenant_service.activate_tenant(tenant_id, plan)
        return {"message": "租户已激活", "tenant_id": tenant.id}


@router.get("/{tenant_id}/statistics", response_model=TenantStatisticsResponseModel)
@require_permission("tenant.analytics")
async def get_tenant_statistics(tenant_id: int):
    """
    获取租户统计信息

    需要权限: tenant.analytics
    """
    async with get_db_session() as db:
        tenant_service = TenantService(db)
        stats = await tenant_service.get_tenant_statistics(tenant_id)
        return TenantStatisticsResponseModel(**stats)


# ==================== 权限管理端点 ==================== None


@router.post("/{tenant_id}/users/{user_id}/roles")
@require_permission("roles.manage")
async def assign_user_role(
    tenant_id: int,
    user_id: int,
    role_data: RoleAssignmentRequestModel,
    request: Request,
):
    """
    为用户分配角色

    需要权限: roles.manage
    """
    async with get_db_session() as db:
        tenant_service = TenantService(db)
        tenant_context = get_tenant_context(request)

        assignment = await tenant_service.assign_user_role(
            user_id=user_id,
            tenant_id=tenant_id,
            role_code=role_data.role_code,
            assigned_by=tenant_context.user_id,
            expires_at=role_data.expires_at,
        )

        return {"message": "角色分配成功", "assignment_id": assignment.id}


@router.delete("/{tenant_id}/users/{user_id}/roles/{role_code}")
@require_permission("roles.manage")
async def revoke_user_role(tenant_id: int, user_id: int, role_code: str):
    """
    撤销用户角色

    需要权限: roles.manage
    """
    async with get_db_session() as db:
        tenant_service = TenantService(db)
        success = await tenant_service.revoke_user_role(user_id, tenant_id, role_code)

        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="角色分配不存在"
            )

        return {"message": "角色撤销成功"}


@router.post("/{tenant_id}/permissions/check")
@require_permission("permissions.check")
async def check_permission(
    tenant_id: int, permission_data: PermissionCheckRequestModel, request: Request
):
    """
    检查用户权限

    需要权限: permissions.check
    """
    tenant_context = get_tenant_context(request)
    if not tenant_context:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="未认证")

    async with get_db_session() as db:
        tenant_service = TenantService(db)
        result = await tenant_service.check_user_permission(
            user_id=tenant_context.user_id,
            tenant_id=tenant_id,
            permission_code=permission_data.permission_code,
            resource_context=permission_data.resource_context,
        )

        return {
            "granted": result.granted,
            "permissions": result.permissions,
            "restrictions": result.restrictions,
            "reason": result.reason,
        }


# ==================== 资源配额端点 ==================== None


@router.get(
    "/{tenant_id}/quota/{resource_type}", response_model=QuotaCheckResponseModel
)
@require_permission("quota.view")
async def check_resource_quota(
    tenant_id: int,
    resource_type: str,
    amount: int = Query(1, ge=1, description="需要的资源量"),
):
    """
    检查资源配额

    需要权限: quota.view
    """
    async with get_db_session() as db:
        tenant_service = TenantService(db)
        quota_check = await tenant_service.check_resource_quota(
            tenant_id=tenant_id, resource_type=resource_type, additional_amount=amount
        )

        return QuotaCheckResponseModel(
            can_access=quota_check.can_access,
            current_usage=quota_check.current_usage,
            max_limit=quota_check.max_limit,
            usage_percentage=quota_check.usage_percentage,
            reason=quota_check.reason,
        )


@router.post("/{tenant_id}/usage/update")
@require_permission("usage.update")
async def update_usage_metrics(tenant_id: int, metrics: dict[str, Any]):
    """
    更新使用指标

    需要权限: usage.update
    """
    async with get_db_session() as db:
        tenant_service = TenantService(db)
        await tenant_service.update_usage_metrics(tenant_id, metrics)
        return {"message": "使用指标更新成功"}


# ==================== 租户列表和搜索 ==================== None


@router.get("/", response_model=list[TenantResponseModel])
@require_permission("tenant.list")
async def list_tenants(
    skip: int = Query(0, ge=0, description="跳过数量"),
    limit: int = Query(
        50,  # TODO: 将魔法数字 50 提取为常量
        ge=1,
        le=100,  # TODO: 将魔法数字 100 提取为常量
        description="返回数量",  # TODO: 将魔法数字 50 提取为常量
    ),  # TODO: 将魔法数字 50 提取为常量
    status: TenantStatus | None = Query(None, description="状态筛选"),
    plan: TenantPlan | None = Query(None, description="计划筛选"),
    search: str | None = Query(None, description="搜索关键词"),
):
    """
    获取租户列表

    需要权限: tenant.list
    """
    async with get_db_session() as db:
        TenantService(db)

        # 这里应该实现分页查询逻辑
        # 暂时返回空列表作为示例
        # 实际实现需要在TenantService中添加list_tenants方法

        return []


# ==================== 健康检查和状态端点 ==================== None


@router.get("/health", tags=["健康检查"])
async def tenant_management_health():
    """多租户管理健康检查"""
    return {
        "status": "healthy",
        "service": "tenant_management",
        "timestamp": datetime.utcnow().isoformat(),
    }


@router.get("/{tenant_id}/health")
@require_permission("tenant.view")
async def tenant_health_check(tenant_id: int):
    """
    租户健康检查

    需要权限: tenant.view
    """
    async with get_db_session() as db:
        tenant_service = TenantService(db)
        tenant = await tenant_service.get_tenant_by_id(tenant_id)

        if not tenant:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="租户不存在"
            )

        return {
            "tenant_id": tenant.id,
            "tenant_name": tenant.name,
            "status": tenant.status,
            "is_active": tenant.is_active,
            "is_subscription_active": tenant.is_subscription_active,
            "usage_percentage": tenant.usage_percentage,
            "days_until_expiry": tenant.days_until_expiry,
            "health_score": _calculate_health_score(tenant),
        }


# 重复的类定义已清理
def _calculate_health_score(tenant: Tenant) -> float:
    """计算租户健康分数"""
    score = 100.0  # TODO: 将魔法数字 100 提取为常量

    # 状态检查
    if tenant.status != TenantStatus.ACTIVE:
        score -= 50.0  # TODO: 将魔法数字 50 提取为常量

    # 订阅检查
    if not tenant.is_subscription_active:
        score -= 30.0  # TODO: 将魔法数字 30 提取为常量

    # 使用率检查
    if tenant.usage_percentage > 90:  # TODO: 将魔法数字 90 提取为常量
        score -= 20.0  # TODO: 将魔法数字 20 提取为常量
    elif tenant.usage_percentage > 80:  # TODO: 将魔法数字 80 提取为常量
        score -= 10.0

    # 过期时间检查
    if tenant.days_until_expiry is not None and tenant.days_until_expiry < 7:
        score -= 15.0  # TODO: 将魔法数字 15 提取为常量

    return max(0.0, score)
