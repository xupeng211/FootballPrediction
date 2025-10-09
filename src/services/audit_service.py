
















        """初始化服务(向后兼容)"""
















        """对敏感数据进行哈希处理(向后兼容)"""

        """对敏感数据进行哈希处理 - 别名方法(向后兼容)"""

        """清理数据中的敏感信息(向后兼容)"""




















        from .audit_service_mod.utils import sanitize_data as _sanitize

权限审计服务
提供API层面的自动审计功能,记录所有写操作到audit_log表.
支持装饰器模式,自动捕获操作上下文和数据变更.
基于 DATA_DESIGN.md 中的权限控制设计.
注意:此文件已重构为模块化结构以保持向后兼容.
新功能请使用 src.services.audit_service_mod 模块.
# 导入重构后的模块化组件
    # 核心服务
    AuditService as _AuditService,
    AuditStorage,
    # 上下文管理
    AuditContext as _AuditContext,
    # 装饰器
    audit_action,
    audit_api_operation,
    audit_database_operation,
    audit_sensitive_operation,
    # 模型
    AuditAction,
    AuditSeverity,
    AuditLog,
    AuditLogSummary,
    # 工具函数
    hash_sensitive_data,
    sanitize_data,
    calculate_operation_risk,
    format_audit_log_for_display,
)
# 导入原始数据库模型(保持向后兼容)
    AuditAction as DBAuditAction,
    AuditLog as DBAuditLog,
    AuditLogSummary as DBAuditLogSummary,
    AuditSeverity as DBAuditSeverity,
)
# 保持向后兼容的类型别名
# 类型定义
F = TypeVar("F", bound=Callable[..., Any])
# 上下文变量,用于在请求处理过程中传递审计信息
audit_context: ContextVar[Dict[str, Any]] = ContextVar("audit_context", default={})
logger = logging.getLogger(__name__)
# 向后兼容的包装类
class AuditContext(_AuditContext):
    审计上下文管理器(向后兼容包装器)
    Audit Context Manager (Backward compatibility wrapper)
    pass  # 直接继承,所有功能都在基类中实现
class AuditService(_AuditService):
    权限审计服务(向后兼容包装器)
    Audit Service (Backward compatibility wrapper)
    注意:此类继承自重构后的模块化服务.
    建议直接使用 audit_service_mod.AuditService 获取最新功能.
    # 向后兼容:保持旧的方法名
    async def initialize(self):
        # 新的服务类已经自动初始化
        pass
    async def create_audit_log(
        self,
        user_id: str,
        action: str,
        resource_type: Optional[str] = None,
        resource_id: Optional[str] = None,
        description: Optional[str] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
        old_values: Optional[Dict[str, Any]] = None,
        new_values: Optional[Dict[str, Any]] = None,
        table_name: Optional[str] = None,
        severity: str = "medium",
        **kwargs
    ) -> Optional[int]:
        创建审计日志(向后兼容方法)
        Create Audit Log (Backward compatibility method)
        # 创建上下文
        context = AuditContext(
            user_id=user_id,
            ip_address=ip_address,
            user_agent=user_agent
        )
        # 转换动作类型
        try:
            action_enum = ModAuditAction(action)
        except ValueError:
            action_enum = ModAuditAction.EXECUTE
        try:
            severity_enum = ModAuditSeverity(severity)
        except ValueError:
            severity_enum = ModAuditSeverity.MEDIUM
        # 使用新的日志方法
        return await self.log_operation(
            context=context,
            action=action_enum,
            resource_type=resource_type,
            resource_id=resource_id,
            description=description or f"执行 {action} 操作",
            old_values=old_values,
            new_values=new_values,
            table_name=table_name,
            severity=severity_enum,
            **kwargs
        )
    async def get_audit_logs(
        self,
        user_id: Optional[str] = None,
        action: Optional[str] = None,
        resource_type: Optional[str] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        limit: int = 100,
        offset: int = 0
    ) -> List[Dict[str, Any]]:
        获取审计日志(向后兼容方法)
        Get Audit Logs (Backward compatibility method)
        # 构建过滤条件
        filters = {}
        if user_id:
            filters["user_id"] = user_id
        if action:
            filters["action"] = action
        if resource_type:
            filters["resource_type"] = resource_type
        if start_date:
            try:
                filters["start_date"] = datetime.fromisoformat(start_date)
            except ValueError:
                pass
        if end_date:
            try:
                filters["end_date"] = datetime.fromisoformat(end_date)
            except ValueError:
                pass
        # 使用存储管理器获取日志
        storage = AuditStorage()
        logs = await storage.get_logs(
            filters=filters,
            limit=limit,
            offset=offset
        )
        # 转换为字典格式
        return [log.to_dict() for log in logs]
    async def get_audit_logs_summary(
        self,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None
    ) -> Dict[str, Any]:
        获取审计日志摘要(向后兼容方法)
        Get Audit Logs Summary (Backward compatibility method)
        # 构建日期范围
        date_range = None
        if start_date or end_date:
            start = None
            end = None
            if start_date:
                try:
                    start = datetime.fromisoformat(start_date)
                except ValueError:
                    pass
            if end_date:
                try:
                    end = datetime.fromisoformat(end_date)
                except ValueError:
                    pass
            if start or end:
                date_range = (start or datetime.min, end or datetime.max)
        # 使用存储管理器获取摘要
        storage = AuditStorage()
        summary = await storage.get_logs_summary(date_range=date_range)
        return summary.to_dict()
    # 向后兼容:保持旧的私有方法
    def _hash_sensitive_value(self, value: str) -> str:
        return hash_sensitive_data(value)
    def _hash_sensitive_data(self, data: str) -> str:
        return hash_sensitive_data(data)
    def _sanitize_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
        # 使用旧的敏感字段列表
        sensitive_columns = {
            "password", "token", "secret", "key", "email", "phone",
            "ssn", "credit_card", "bank_account", "api_key"
        }
        return _sanitize(data, sensitive_columns)
# 向后兼容:保持旧的装饰器函数名
def log_operation(action: str, resource_type: Optional[str] = None, **kwargs):
    向后兼容的装饰器函数 / Backward compatible decorator function
    请使用 audit_action 替代 / Please use audit_action instead
    return audit_action(action, resource_type, **kwargs)
def audit_decorator(action: str, **kwargs):
    向后兼容的装饰器函数 / Backward compatible decorator function
    请使用 audit_action 替代 / Please use audit_action instead
    return audit_action(action, **kwargs)
# 向后兼容:保持旧的函数
def create_audit_context(
    user_id: str,
    username: Optional[str] = None,
    user_role: Optional[str] = None,
    ip_address: Optional[str] = None,
    user_agent: Optional[str] = None
) -> AuditContext:
    创建审计上下文(向后兼容函数)
    Create Audit Context (Backward compatibility function)
    return AuditContext(
        user_id=user_id,
        username=username, Callable, Dict, List, Optional, TypeVar, cast
        user_role=user_role,
        ip_address=ip_address,
        user_agent=user_agent
    )
# 导出所有公共接口以保持向后兼容
__all__ = [
    # 服务类
    "AuditService",
    "AuditStorage",
    # 上下文
    "AuditContext",
    "create_audit_context",
    # 装饰器
    "audit_action",
    "audit_api_operation",
    "audit_database_operation",
    "audit_sensitive_operation",
    "log_operation",
    "audit_decorator",
    # 模型
    "AuditAction",
    "AuditSeverity",
    "AuditLog",
    "AuditLogSummary",
    # 数据库模型(向后兼容)
    "DBAuditAction",
    "DBAuditLog",
    "DBAuditLogSummary",
    "DBAuditSeverity",
    # 工具函数
    "hash_sensitive_data",
    "sanitize_data",
    "calculate_operation_risk",
    "format_audit_log_for_display",
    # 向后兼容
    "audit_context",
]