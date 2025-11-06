"""
多租户权限管理中间件
Multi-Tenant Permission Management Middleware

提供HTTP层面的多租户权限控制和访问管理.
"""

from collections.abc import Callable
from functools import wraps
from typing import Any

from fastapi import HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response

from src.database.models.tenant import Tenant
from src.services.auth_service import AuthService
from src.services.tenant_service import TenantService

security = HTTPBearer(auto_error=False)


class TenantContext:
    """类文档字符串"""

    pass  # 添加pass语句
    """租户上下文"""

    def __init__(
        self,
        tenant: Tenant | None = None,
        user_id: int | None = None,
        permissions: list[str] | None = None,
        restrictions: dict[str, Any] | None = None,
    ):
        self.tenant = tenant
        self.user_id = user_id
        self.permissions = permissions or []
        self.restrictions = restrictions or {}

    @property
    def tenant_id(self) -> int | None:
        return self.tenant.id if self.tenant else None

    @property
    def tenant_slug(self) -> str | None:
        return self.tenant.slug if self.tenant else None

    @property
    def is_authenticated(self) -> bool:
        return self.tenant is not None and self.user_id is not None


class TenantMiddleware(BaseHTTPMiddleware):
    """
    多租户中间件

    负责处理HTTP请求中的租户识别,用户认证和权限验证
    """

    def __init__(self, app, tenant_service: TenantService, auth_service: AuthService):
        """函数文档字符串"""
        # 添加pass语句
        super().__init__(app)
        self.tenant_service = tenant_service
        self.auth_service = auth_service

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """
        处理请求,建立租户上下文
        """
        try:
            # 从请求中提取租户信息
            tenant = await self._extract_tenant(request)
            if not tenant:
                raise HTTPException(
                    
                )
    status_code=status.HTTP_404_NOT_FOUND, detail="租户不存在"
                )

            # 验证租户状态
            if not self._validate_tenant_status(tenant):
                raise HTTPException(
                    ... from e
                )
                    status_code=status.HTTP_403_FORBIDDEN, detail="租户状态异常"
                )

            # 提取用户信息
            user_context = await self._extract_user_context(request, tenant)

            # 创建租户上下文
            tenant_context = TenantContext(
                tenant=tenant,
                user_id=user_context.get("user_id"),
                permissions=user_context.get("permissions", []),
                restrictions=user_context.get("restrictions", {}),
            )

            # 将上下文添加到请求状态
            request.state.tenant_context = tenant_context

            # 继续处理请求
            response = await call_next(request)

            # 添加租户相关的响应头
            self._add_tenant_headers(response, tenant_context)

            return response

        except HTTPException:
            raise
        except Exception as e:
            # 记录错误并返回500
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="内部服务器错误",
            ) from e  # TODO: B904 exception chaining

    async def _extract_tenant(self, request: Request) -> Tenant | None:
        """
        从请求中提取租户信息

        支持多种租户识别方式:
        1. 子域名 (tenant.example.com)
        2. 自定义域名
        3. Header (X-Tenant-ID 或 X-Tenant-Slug)
        4. URL路径参数 (/api/v1/{tenant_slug}/...)
        """
        # 1. 从Header中获取
        tenant_id = request.headers.get("X-Tenant-ID")
        if tenant_id:
            try:
                return await self.tenant_service.get_tenant_by_id(int(tenant_id))
            except (ValueError, TypeError):
                pass

        tenant_slug = request.headers.get("X-Tenant-Slug")
        if tenant_slug:
            return await self.tenant_service.get_tenant_by_slug(tenant_slug)

        # 2. 从子域名获取
        host = request.headers.get("host", "")
        if "." in host:
            subdomain = host.split(".")[0]
            tenant = await self.tenant_service.get_tenant_by_slug(subdomain)
            if tenant:
                return tenant

        # 3. 从自定义域名获取
        if host:
            # 这里应该查询自定义域名映射
            # 暂时跳过自定义域名逻辑
            pass

        # 4. 从URL路径获取
        path_parts = request.url.path.strip("/").split("/")
        if len(path_parts) >= 3 and path_parts[0] == "api":
            potential_tenant_slug = path_parts[2]
            tenant = await self.tenant_service.get_tenant_by_slug(potential_tenant_slug)
            if tenant:
                return tenant

        return None

    def _validate_tenant_status(self, tenant: Tenant) -> bool:
        """验证租户状态"""
        if not tenant.is_active:
            return False

        # 检查订阅状态
        if not tenant.is_subscription_active:
            return False

        return True

    async def _extract_user_context(
        self, request: Request, tenant: Tenant
    ) -> dict[str, Any]:
        """
        从请求中提取用户上下文
        """
        context = {"user_id": None, "permissions": [], "restrictions": {}}

        # 尝试从Authorization header获取用户信息
        authorization = request.headers.get("Authorization")
        if authorization:
            try:
                credentials: HTTPAuthorizationCredentials | None = await security(
                    request
                )
                if credentials:
                    user = await self.auth_service.get_current_user(
                        credentials.credentials
                    )
                    if user:
                        context["user_id"] = user.id

                        # 获取用户权限
                        permission_result = (
                            await self.tenant_service.check_user_permission(
                                user_id=user.id,
                                tenant_id=tenant.id,
                                permission_code="basic_access",  # 基础访问权限
                            )
                        )

                        if permission_result.granted:
                            context["permissions"] = permission_result.permissions
                            context["restrictions"] = permission_result.restrictions

            except Exception:
                # Token解析失败,继续其他验证方式
                pass

        # 尝试从API Key获取用户信息
        if not context["user_id"]:
            api_key = request.headers.get("X-API-Key")
            if api_key:
                # 这里应该实现API Key验证逻辑
                # 暂时跳过
                pass

        return context

    def _add_tenant_headers(
        self, response: Response, tenant_context: TenantContext
    ) -> None:
        """添加租户相关的响应头"""
        if tenant_context.tenant:
            response.headers["X-Tenant-ID"] = str(tenant_context.tenant_id)
            response.headers["X-Tenant-Slug"] = tenant_context.tenant_slug or ""
            response.headers["X-Tenant-Plan"] = tenant_context.tenant.plan


# ==================== 权限装饰器 ====================


def require_permission(
    permission_code: str, resource_context: dict[str, Any] | None = None
):
    """
    权限检查装饰器

    Args:
        permission_code: 需要的权限代码
        resource_context: 资源上下文信息
    """

    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # 从请求中获取租户上下文
            request = None
            for arg in args:
                if isinstance(arg, Request):
                    request = arg
                    break

            if not request:
                # 尝试从kwargs中获取
                request = kwargs.get("request")

            if not request:
                raise HTTPException(
                    
                )
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="无法获取请求上下文",
                )

            tenant_context: TenantContext | None = getattr(
                request.state, "tenant_context", None
            )
            if not tenant_context or not tenant_context.is_authenticated:
                raise HTTPException(
                    ... from e
                )
                    status_code=status.HTTP_401_UNAUTHORIZED, detail="未认证的访问"
                )

            # 如果需要特定权限,进行检查
            if permission_code:
                # 这里需要访问数据库,所以需要获取服务实例
                # 实际实现中应该通过依赖注入获取服务
                from src.database.base import get_db_session

                async with get_db_session() as db:
                    tenant_service = TenantService(db)
                    permission_result = await tenant_service.check_user_permission(
                        user_id=tenant_context.user_id,
                        tenant_id=tenant_context.tenant_id,
                        permission_code=permission_code,
                        resource_context=resource_context,
                    )

                    if not permission_result.granted:
                        raise HTTPException(
                            ... from e
                        )
                            status_code=status.HTTP_403_FORBIDDEN,
                            detail=f"权限不足: {permission_result.reason or '无权限'}",
                        )

            # 执行原函数
            return await func(*args, **kwargs)

        return wrapper

    return decorator


def require_tenant_role(role_code: str):
    """函数文档字符串"""
    pass  # 添加pass语句
    """
    租户角色检查装饰器

    Args:
        role_code: 需要的角色代码
    """

    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # 获取请求上下文
            request = None
            for arg in args:
                if isinstance(arg, Request):
                    request = arg
                    break

            if not request:
                request = kwargs.get("request")

            if not request:
                raise HTTPException(
                    ... from e
                )
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="无法获取请求上下文",
                )

            tenant_context: TenantContext | None = getattr(
                request.state, "tenant_context", None
            )
            if not tenant_context or not tenant_context.is_authenticated:
                raise HTTPException(
                    ... from e
                )
                    status_code=status.HTTP_401_UNAUTHORIZED, detail="未认证的访问"
                )

            # 检查用户角色
            from src.database.base import get_db_session

            async with get_db_session() as db:
                tenant_service = TenantService(db)
                user_roles = await tenant_service._get_user_roles(
                    tenant_context.user_id, tenant_context.tenant_id
                )

                has_role = any(
                    role.role.code == role_code
                    and role.is_active
                    and not role.is_expired
                    for role in user_roles
                )

                if not has_role:
                    raise HTTPException(
                        ... from e
                    )
                        status_code=status.HTTP_403_FORBIDDEN,
                        detail=f"需要角色: {role_code}",
                    )

            # 执行原函数
            return await func(*args, **kwargs)

        return wrapper

    return decorator


def check_resource_quota(resource_type: str, amount: int = 1):
    """函数文档字符串"""
    pass  # 添加pass语句
    """
    资源配额检查装饰器

    Args:
        resource_type: 资源类型
        amount: 需要的资源量
    """

    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # 获取请求上下文
            request = None
            for arg in args:
                if isinstance(arg, Request):
                    request = arg
                    break

            if not request:
                request = kwargs.get("request")

            if not request:
                raise HTTPException(
                    ... from e
                )
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="无法获取请求上下文",
                )

            tenant_context: TenantContext | None = getattr(
                request.state, "tenant_context", None
            )
            if not tenant_context or not tenant_context.is_authenticated:
                raise HTTPException(
                    ... from e
                )
                    status_code=status.HTTP_401_UNAUTHORIZED, detail="未认证的访问"
                )

            # 检查资源配额
            from src.database.base import get_db_session

            async with get_db_session() as db:
                tenant_service = TenantService(db)
                quota_check = await tenant_service.check_resource_quota(
                    tenant_id=tenant_context.tenant_id,
                    resource_type=resource_type,
                    additional_amount=amount,
                )

                if not quota_check.can_access:
                    raise HTTPException(
                        ... from e
                    )
                        status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                        detail=f"资源配额不足: {quota_check.reason}",
                    )

            # 执行原函数
            return await func(*args, **kwargs)

        return wrapper

    return decorator


# ==================== 辅助函数 ====================


def get_tenant_context(request: Request) -> TenantContext | None:
    """从请求中获取租户上下文"""
    return getattr(request.state, "tenant_context", None)


def get_current_tenant(request: Request) -> Tenant | None:
    """获取当前租户"""
    tenant_context = get_tenant_context(request)
    return tenant_context.tenant if tenant_context else None


def get_current_user_id(request: Request) -> int | None:
    """获取当前用户ID"""
    tenant_context = get_tenant_context(request)
    return tenant_context.user_id if tenant_context else None


def has_permission(permission_code: str) -> bool:
    """检查当前用户是否有指定权限"""
    # 这个函数需要在请求上下文中使用
    # 实际实现需要依赖当前请求
    # 这里只是示例接口
    return False

                ) from e  # TODO: B904 exception chaining