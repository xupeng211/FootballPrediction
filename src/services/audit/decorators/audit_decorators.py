"""

"""





    """审计状态枚举（临时定义）"""




    """从FastAPI请求中提取审计上下文"""



    """

    """

















    """

    """















    """创建操作审计"""


    """读取操作审计"""


    """更新操作审计"""


    """删除操作审计"""




import functools
import inspect
import time
from ..context import AuditContext, audit_context
from ..loggers.audit_logger import AuditLogger
from src.database.models.audit_log import AuditAction, AuditSeverity

审计装饰器
自动审计函数调用和数据库操作。
class AuditStatus(str, Enum):
    SUCCESS = "success"
    FAILED = "failed"
    PENDING = "pending"
F = TypeVar("F", bound=Callable[..., Any])
logger = logging.getLogger(__name__)
def extract_request_context(request: Request) -> AuditContext:
    # 尝试从请求状态中获取用户信息
    user_id = getattr(request.state, "user_id", None)
    if not user_id:
        # 从JWT token或其他认证信息中获取
        auth_header = request.headers.get("authorization")
        if auth_header:
            # 这里应该解析JWT或其他认证信息
            user_id = "unknown"  # 临时实现
    return AuditContext.from_request(request, user_id or "anonymous")
def audit_operation(
    action: AuditAction,
    table_name: Optional[str] = None,
    severity: AuditSeverity = AuditSeverity.INFO,
    include_args: Optional[list[str]] = None,
    include_result: bool = False,
):
    审计操作装饰器
    Args:
        action: 操作类型
        table_name: 表名
        severity: 严重程度
        include_args: 包含的参数列表
        include_result: 是否包含返回结果
    def decorator(func: F) -> F:
        @functools.wraps(func)
        async def async_wrapper(*args, **kwargs):
            # 获取审计上下文
            context = audit_context.get()
            if not context and args:
                # 尝试从第一个参数（通常是self）获取上下文
                request = getattr(args[0], "request", None) if hasattr(args[0], "request") else None
                if request:
                    audit_ctx = extract_request_context(request)
                    context = audit_ctx.to_dict()
            # 记录开始时间
            start_time = time.time()
            log_id = None
            audit_logger = AuditLogger()
            try:
                # 提取参数信息
                op_data = {}
                if include_args:
                    sig = inspect.signature(func)
                    bound_args = sig.bind(*args, **kwargs)
                    for arg_name in include_args:
                        if arg_name in bound_args.arguments:
                            op_data[arg_name] = bound_args.arguments[arg_name]
                # 执行函数
                result = await func(*args, **kwargs)
                # 计算执行时间
                execution_time = int((time.time() - start_time) * 1000)
                # 准备审计数据
                audit_data = {
                    "new_values": op_data if include_args else None,
                    "execution_time_ms": execution_time,
                }
                if include_result and isinstance(result, (dict, list)):
                    audit_data["new_values"] = audit_data.get("new_values", {})
                    audit_data["new_values"]["result"] = str(result)[:1000]  # 限制长度
                # 记录成功日志
                log_id = await audit_logger.log_operation(
                    action=action,
                    table_name=table_name,
                    severity=severity,
                    status=AuditStatus.SUCCESS,
                    context=context,
                    **audit_data,
                )
                return result
            except Exception as e:
                # 计算执行时间
                execution_time = int((time.time() - start_time) * 1000)
                # 记录失败日志
                await audit_logger.log_operation(
                    action=action,
                    table_name=table_name,
                    severity=AuditSeverity.ERROR,
                    status=AuditStatus.FAILED,
                    error_message=str(e),
                    execution_time_ms=execution_time,
                    context=context,
                )
                # 重新抛出异常
                raise
        @functools.wraps(func)
        def sync_wrapper(*args, **kwargs):
            # 同步函数的简化实现
            try:
                result = func(*args, **kwargs)
                # 这里可以添加异步记录逻辑
                logger.info(f"审计操作: {action.value} - {func.__name__}")
                return result
            except Exception as e:
                logger.error(f"审计操作失败: {action.value} - {func.__name__} - {e}")
                raise
        # 根据函数类型返回相应的包装器
        if inspect.iscoroutinefunction(func):
            return async_wrapper  # type: ignore
        else:
            return sync_wrapper  # type: ignore
    return decorator  # type: ignore
def audit_database_operation(
    action: AuditAction,
    table_name: str,
    record_id_param: Optional[str] = None,
    old_values_param: Optional[str] = None,
    new_values_param: Optional[str] = None,
):
    数据库操作审计装饰器
    Args:
        action: 操作类型
        table_name: 表名
        record_id_param: 记录ID参数名
        old_values_param: 旧值参数名
        new_values_param: 新值参数名
    def decorator(func: F) -> F:
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            start_time = time.time()
            audit_logger = AuditLogger()
            context = audit_context.get()
            # 提取参数
            sig = inspect.signature(func)
            bound_args = sig.bind(*args, **kwargs)
            record_id = None
            old_values = None
            new_values = None
            if record_id_param:
                record_id = bound_args.arguments.get(record_id_param)
            if old_values_param:
                old_values = bound_args.arguments.get(old_values_param)
            if new_values_param:
                new_values = bound_args.arguments.get(new_values_param)
            try:
                # 执行操作
                result = await func(*args, **kwargs)
                # 计算执行时间
                execution_time = int((time.time() - start_time) * 1000)
                # 记录审计日志
                await audit_logger.log_operation(
                    action=action,
                    table_name=table_name,
                    record_id=record_id,
                    old_values=old_values,
                    new_values=new_values,
                    execution_time_ms=execution_time,
                    context=context,
                )
                return result
            except Exception as e:
                execution_time = int((time.time() - start_time) * 1000)
                await audit_logger.log_operation(
                    action=action,
                    table_name=table_name,
                    record_id=record_id,
                    old_values=old_values,
                    new_values=new_values,
                    status=AuditStatus.FAILED,
                    error_message=str(e),
                    execution_time_ms=execution_time,
                    context=context,
                )
                raise
        return wrapper  # type: ignore
    return decorator  # type: ignore
# 便捷装饰器
def audit_create(table_name: str):
    return audit_database_operation(AuditAction.CREATE, table_name)
def audit_read(table_name: str):
    return audit_database_operation(AuditAction.READ, table_name)
def audit_update(table_name: str):
    return audit_database_operation(
        AuditAction.UPDATE,
        table_name,
        record_id_param="id",
        old_values_param="old_data",
        new_values_param="new_data",
    )
def audit_delete(table_name: str):
    return audit_database_operation(
        AuditAction.DELETE,
        table_name,
        record_id_param="id",
        old_values_param="old_data",
    )