import os
"""
API响应模型定义

为所有API端点提供标准化的响应模型，确保API文档的一致性和完整性。
"""

from typing import Any, Dict, Optional

from pydantic import BaseModel, Field


class ServiceCheck(BaseModel):
    """服务检查结果模型"""

    status: str = Field(..., description="服务状态")
    response_time_ms: float = Field(..., description = os.getenv("SCHEMAS_DESCRIPTION_16"))
    details: Optional[Dict[str, Any]] = Field(None, description="详细信息")


class HealthCheckResponse(BaseModel):
    """健康检查API响应模型"""

    status: str = Field(..., description = os.getenv("SCHEMAS_DESCRIPTION_23"))
    timestamp: str = Field(..., description = os.getenv("SCHEMAS_DESCRIPTION_23"))
    service: str = Field(..., description="服务名称")
    version: str = Field(..., description="服务版本")
    uptime: float = Field(..., description = os.getenv("SCHEMAS_DESCRIPTION_26"))
    response_time_ms: float = Field(..., description = os.getenv("SCHEMAS_DESCRIPTION_27"))
    checks: Dict[str, ServiceCheck] = Field(..., description = os.getenv("SCHEMAS_DESCRIPTION_28"))


class StatusResponse(BaseModel):
    """服务状态API响应模型"""

    status: str = Field(..., description="整体状态")
    timestamp: str = Field(..., description="检查时间")
    services: Dict[str, str] = Field(..., description="各服务状态")


class MetricsResponse(BaseModel):
    """监控指标API响应模型"""

    status: str = Field(..., description="API状态")
    response_time_ms: float = Field(..., description = os.getenv("SCHEMAS_DESCRIPTION_16"))
    system: Dict[str, Any] = Field(..., description = os.getenv("SCHEMAS_DESCRIPTION_41"))
    database: Dict[str, Any] = Field(..., description = os.getenv("SCHEMAS_DESCRIPTION_44"))
    runtime: Dict[str, Any] = Field(..., description="运行时指标")
    business: Dict[str, Any] = Field(..., description = os.getenv("SCHEMAS_DESCRIPTION_45"))


class RootResponse(BaseModel):
    """根路径API响应模型"""

    service: str = Field(..., description="服务名称")
    version: str = Field(..., description="版本号")
    status: str = Field(..., description="服务状态")
    docs_url: str = Field(..., description = os.getenv("SCHEMAS_DESCRIPTION_48"))
    health_check: str = Field(..., description = os.getenv("SCHEMAS_DESCRIPTION_51"))


class ErrorResponse(BaseModel):
    """错误响应模型"""

    error: bool = Field(..., description="是否为错误")
    status_code: int = Field(..., description = os.getenv("SCHEMAS_DESCRIPTION_56"))
    message: str = Field(..., description="错误消息")
    path: str = Field(..., description="请求路径")
