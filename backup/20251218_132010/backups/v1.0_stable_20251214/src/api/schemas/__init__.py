"""API schemas package."""

# 简单导入,避免循环导入
from typing import Any, Optional, Generic, TypeVar

from pydantic import BaseModel, Field

# 定义泛型类型变量
T = TypeVar("T")


class APIResponse(BaseModel):
    """通用API响应模型."""

    success: bool = Field(..., description="请求是否成功")
    message: str = Field(..., description="响应消息")
    data: Any | None = Field(None, description="响应数据")
    errors: list[str] | None = Field(None, description="错误信息列表")
    timestamp: str | None = Field(None, description="响应时间戳")


class StandardResponse(BaseModel, Generic[T]):
    """标准化API响应模型."""

    success: bool = Field(..., description="请求是否成功")
    message: str = Field(..., description="响应消息")
    data: T = Field(..., description="响应数据")
    errors: list[str] | None = Field(None, description="错误信息列表")
    timestamp: str | None = Field(None, description="响应时间戳")


class PaginatedResponse(BaseModel, Generic[T]):
    """分页响应模型."""

    success: bool = Field(..., description="请求是否成功")
    message: str = Field(..., description="响应消息")
    data: list[T] = Field(..., description="响应数据列表")
    pagination: dict[str, Any] = Field(..., description="分页信息")
    errors: list[str] | None = Field(None, description="错误信息列表")
    timestamp: str | None = Field(None, description="响应时间戳")


class ServiceCheck(BaseModel):
    """服务检查结果模型."""

    status: str = Field(..., description="服务状态")
    response_time_ms: float = Field(..., description="响应时间(毫秒)")
    details: dict[str, Any] | None = Field(None, description="详细信息")


class HealthCheckResponse(BaseModel):
    """健康检查API响应模型."""

    status: str = Field(..., description="整体健康状态")
    timestamp: str = Field(..., description="检查时间(ISO格式)")
    service: str = Field(..., description="服务名称")
    version: str = Field(..., description="服务版本")
    uptime: float = Field(..., description="应用运行时间(秒)")
    response_time_ms: float = Field(..., description="总响应时间(毫秒)")
    checks: dict[str, ServiceCheck] = Field(..., description="各服务检查结果")


class StatusResponse(BaseModel):
    """服务状态API响应模型."""

    status: str = Field(..., description="整体状态")
    timestamp: str = Field(..., description="检查时间")
    services: dict[str, str] = Field(..., description="各服务状态")


class MetricsResponse(BaseModel):
    """监控指标API响应模型."""

    status: str = Field(..., description="API状态")
    response_time_ms: float = Field(..., description="响应时间(毫秒)")
    system: dict[str, Any] = Field(..., description="系统资源指标")
    database: dict[str, Any] = Field(..., description="数据库性能指标")
    runtime: dict[str, Any] = Field(..., description="运行时指标")
    business: dict[str, Any] = Field(..., description="业务指标统计")


class HealthResponse(BaseModel):
    """健康检查响应模型."""

    status: str = Field(..., description="健康状态")
    timestamp: str = Field(..., description="检查时间")
    service: str = Field(..., description="服务名称")
    version: str | None = Field(None, description="服务版本")
    uptime: float | None = Field(None, description="运行时间(秒)")
    checks: dict[str, Any] | None = Field(None, description="检查项目")


class RootResponse(BaseModel):
    """根路径API响应模型."""

    service: str = Field(..., description="服务名称")
    version: str = Field(..., description="版本号")
    status: str = Field(..., description="服务状态")
    docs_url: str = Field(..., description="API文档地址")
    health_check: str = Field(..., description="健康检查地址")


class ErrorResponse(BaseModel):
    """错误响应模型."""

    error: bool = Field(..., description="是否为错误")
    status_code: int = Field(..., description="HTTP状态码")
    message: str = Field(..., description="错误消息")
    path: str = Field(..., description="请求路径")


__all__ = [
    "APIResponse",
    "StandardResponse",
    "PaginatedResponse",
    "ErrorResponse",
    "HealthCheckResponse",
    "HealthResponse",
    "MetricsResponse",
    "RootResponse",
    "ServiceCheck",
    "StatusResponse",
]
