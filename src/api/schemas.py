"""
API响应模型定义

为所有API端点提供标准化的响应模型，确保API文档的一致性和完整性。
"""


class ServiceCheck(BaseModel):
    """服务检查结果模型"""

    status: str = Field(..., description="服务状态")
    response_time_ms: float = Field(..., description="响应时间(毫秒)")
    details: Optional[Dict[str, Any]] = Field(None, description="详细信息")


class HealthCheckResponse(BaseModel):
    """健康检查API响应模型"""

    status: str = Field(..., description="整体健康状态")
    timestamp: str = Field(..., description="检查时间(ISO格式)")
    service: str = Field(..., description="服务名称")
    version: str = Field(..., description="服务版本")
    uptime: float = Field(..., description="应用运行时间(秒)")
    response_time_ms: float = Field(..., description="总响应时间(毫秒)")
    checks: Dict[str, ServiceCheck] = Field(..., description="各服务检查结果")


class StatusResponse(BaseModel):
    """服务状态API响应模型"""

    status: str = Field(..., description="整体状态")
    timestamp: str = Field(..., description="检查时间")
    services: Dict[str, str] = Field(..., description="各服务状态")


class MetricsResponse(BaseModel):
    """监控指标API响应模型"""

    status: str = Field(..., description="API状态")
    response_time_ms: float = Field(..., description="响应时间(毫秒)")
    system: Dict[str, Any] = Field(..., description="系统资源指标")
    database: Dict[str, Any] = Field(..., description="数据库性能指标")
    runtime: Dict[str, Any] = Field(..., description="运行时指标")
    business: Dict[str, Any] = Field(..., description="业务指标统计")


class RootResponse(BaseModel):
    """根路径API响应模型"""

    service: str = Field(..., description="服务名称")
    version: str = Field(..., description="版本号")
    status: str = Field(..., description="服务状态")
    docs_url: str = Field(..., description="API文档地址")
    health_check: str = Field(..., description="健康检查地址")


class ErrorResponse(BaseModel):
    """错误响应模型"""

    error: bool = Field(..., description="是否为错误")
    status_code: int = Field(..., description="HTTP状态码")

    message: str = Field(..., description="错误消息")
    path: str = Field(..., description="请求路径")
