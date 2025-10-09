"""

"""





    """


    """









    """


    """









    """


    """











    """


    """




















    """


    """









    """


    """









    """


    """























    """提取用户权限 / Extract User Permissions"""





    """提取用户角色 / Extract User Role"""





    """提取用户信息 / Extract User Info"""





    """提取用户键 / Extract User Key"""




    """提取请求对象 / Extract Request Object"""




    """获取客户端IP / Get Client IP"""




    """检查权限 / Check Permissions"""



    """检查角色 / Check Role"""





    """检查认证是否有效 / Check if Authentication is Valid"""





    """异步验证输入 / Async Validate Input"""







    """同步验证输入 / Sync Validate Input"""






    """验证CSRF token / Validate CSRF Token"""






    """安全错误 / Security Error"""


    """认证错误 / Authentication Error"""


    """权限错误 / Permission Error"""


    """验证错误 / Validation Error"""


    """CSRF错误 / CSRF Error"""


    """速率限制错误 / Rate Limit Exceeded Error"""



from datetime import datetime
from typing import Callable
import asyncio
import functools
import time

安全装饰器
Security Decorators
提供安全相关的装饰器实现。
logger = get_logger(__name__)
def require_permission(permission: str, require_all: bool = False):
    权限验证装饰器 / Permission Verification Decorator
    Args:
        permission: 所需权限 / Required permission
        require_all: 是否需要所有权限 / Whether all permissions are required
    Returns:
        Callable: 装饰器函数 / Decorator function
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        async def async_wrapper(*args, **kwargs):
            # 获取用户权限
            user_permissions = _extract_user_permissions(args, kwargs)
            # 验证权限
            if not _check_permissions(user_permissions, permission, require_all):
                raise PermissionError(f"权限不足: 需要权限 '{permission}'")
            # 执行原函数
            return await func(*args, **kwargs)
        @functools.wraps(func)
        def sync_wrapper(*args, **kwargs):
            # 获取用户权限
            user_permissions = _extract_user_permissions(args, kwargs)
            # 验证权限
            if not _check_permissions(user_permissions, permission, require_all):
                raise PermissionError(f"权限不足: 需要权限 '{permission}'")
            # 执行原函数
            return func(*args, **kwargs)
        # 根据函数类型返回合适的包装器
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        else:
            return sync_wrapper
    return decorator
def require_role(role: str, allow_higher: bool = True):
    角色验证装饰器 / Role Verification Decorator
    Args:
        role: 所需角色 / Required role
        allow_higher: 是否允许更高级别角色 / Whether higher roles are allowed
    Returns:
        Callable: 装饰器函数 / Decorator function
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        async def async_wrapper(*args, **kwargs):
            # 获取用户角色
            user_role = _extract_user_role(args, kwargs)
            # 验证角色
            if not _check_role(user_role, role, allow_higher):
                raise PermissionError(f"角色不足: 需要角色 '{role}'")
            # 执行原函数
            return await func(*args, **kwargs)
        @functools.wraps(func)
        def sync_wrapper(*args, **kwargs):
            # 获取用户角色
            user_role = _extract_user_role(args, kwargs)
            # 验证角色
            if not _check_role(user_role, role, allow_higher):
                raise PermissionError(f"角色不足: 需要角色 '{role}'")
            # 执行原函数
            return func(*args, **kwargs)
        # 根据函数类型返回合适的包装器
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        else:
            return sync_wrapper
    return decorator
def authenticate_user(required: bool = True):
    用户认证装饰器 / User Authentication Decorator
    Args:
        required: 是否必须认证 / Whether authentication is required
    Returns:
        Callable: 装饰器函数 / Decorator function
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        async def async_wrapper(*args, **kwargs):
            # 检查用户认证状态
            user_info = _extract_user_info(args, kwargs)
            if required and not user_info:
                raise AuthenticationError("用户未认证")
            # 检查认证是否有效
            if user_info and not _is_valid_authentication(user_info):
                raise AuthenticationError("认证已过期或无效")
            # 执行原函数
            return await func(*args, **kwargs)
        @functools.wraps(func)
        def sync_wrapper(*args, **kwargs):
            # 检查用户认证状态
            user_info = _extract_user_info(args, kwargs)
            if required and not user_info:
                raise AuthenticationError("用户未认证")
            # 检查认证是否有效
            if user_info and not _is_valid_authentication(user_info):
                raise AuthenticationError("认证已过期或无效")
            # 执行原函数
            return func(*args, **kwargs)
        # 根据函数类型返回合适的包装器
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        else:
            return sync_wrapper
    return decorator
def rate_limit_by_user(
    calls: int,
    period: float,
    user_key_func: Optional[Callable] = None,
):
    基于用户的速率限制装饰器 / Rate Limit by User Decorator
    Args:
        calls: 允许的调用次数 / Allowed calls
        period: 时间周期（秒）/ Time period (seconds)
        user_key_func: 用户键生成函数 / User key generation function
    Returns:
        Callable: 装饰器函数 / Decorator function
    user_call_records = {}
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        async def async_wrapper(*args, **kwargs):
            # 获取用户键
            if user_key_func:
                user_key = user_key_func(*args, **kwargs)
            else:
                user_key = _extract_user_key(args, kwargs)
            if not user_key:
                raise SecurityError("无法识别用户进行速率限制")
            current_time = time.time()
            # 获取用户调用记录
            if user_key not in user_call_records:
                user_call_records[user_key] = []
            # 清理过期的调用记录
            user_call_records[user_key] = [
                call_time for call_time in user_call_records[user_key]
                if current_time - call_time < period
            ]
            # 检查是否超过限制
            if len(user_call_records[user_key]) >= calls:
                logger.warning(f"用户 {user_key} 速率限制: {calls} calls per {period}s")
                raise RateLimitExceededError(f"速率限制 exceeded: {calls} calls per {period} seconds")
            # 记录当前调用
            user_call_records[user_key].append(current_time)
            # 执行原函数
            return await func(*args, **kwargs)
        @functools.wraps(func)
        def sync_wrapper(*args, **kwargs):
            # 获取用户键
            if user_key_func:
                user_key = user_key_func(*args, **kwargs)
            else:
                user_key = _extract_user_key(args, kwargs)
            if not user_key:
                raise SecurityError("无法识别用户进行速率限制")
            current_time = time.time()
            # 获取用户调用记录
            if user_key not in user_call_records:
                user_call_records[user_key] = []
            # 清理过期的调用记录
            user_call_records[user_key] = [
                call_time for call_time in user_call_records[user_key]
                if current_time - call_time < period
            ]
            # 检查是否超过限制
            if len(user_call_records[user_key]) >= calls:
                logger.warning(f"用户 {user_key} 速率限制: {calls} calls per {period}s")
                raise RateLimitExceededError(f"速率限制 exceeded: {calls} calls per {period} seconds")
            # 记录当前调用
            user_call_records[user_key].append(current_time)
            # 执行原函数
            return func(*args, **kwargs)
        # 根据函数类型返回合适的包装器
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        else:
            return sync_wrapper
    return decorator
def validate_input(
    validators: Dict[str, Callable],
    sanitize: bool = True,
):
    输入验证装饰器 / Input Validation Decorator
    Args:
        validators: 验证器字典 / Validators dictionary
        sanitize: 是否清理输入 / Whether to sanitize input
    Returns:
        Callable: 装饰器函数 / Decorator function
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        async def async_wrapper(*args, **kwargs):
            try:
                # 验证输入
                validated_kwargs = await _validate_input(validators, kwargs, sanitize)
                # 执行原函数
                return await func(*args, **validated_kwargs)
            except ValidationError as e:
                logger.warning(f"输入验证失败: {e}")
                raise
        @functools.wraps(func)
        def sync_wrapper(*args, **kwargs):
            try:
                # 验证输入
                validated_kwargs = _validate_input_sync(validators, kwargs, sanitize)
                # 执行原函数
                return func(*args, **validated_kwargs)
            except ValidationError as e:
                logger.warning(f"输入验证失败: {e}")
                raise
        # 根据函数类型返回合适的包装器
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        else:
            return sync_wrapper
    return decorator
def protect_csrf(
    token_header: str = "X-CSRF-Token",
    session_token_key: str = "csrf_token",
):
    CSRF保护装饰器 / CSRF Protection Decorator
    Args:
        token_header: Token头部名称 / Token header name
        session_token_key: 会话token键名 / Session token key name
    Returns:
        Callable: 装饰器函数 / Decorator function
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        async def async_wrapper(*args, **kwargs):
            # 获取请求对象
            request = _extract_request(args, kwargs)
            if request:
                # 验证CSRF token
                if not _validate_csrf_token(request, token_header, session_token_key):
                    raise CSRFError("CSRF token验证失败")
            # 执行原函数
            return await func(*args, **kwargs)
        @functools.wraps(func)
        def sync_wrapper(*args, **kwargs):
            # 获取请求对象
            request = _extract_request(args, kwargs)
            if request:
                # 验证CSRF token
                if not _validate_csrf_token(request, token_header, session_token_key):
                    raise CSRFError("CSRF token验证失败")
            # 执行原函数
            return func(*args, **kwargs)
        # 根据函数类型返回合适的包装器
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        else:
            return sync_wrapper
    return decorator
def detect_intrusion(
    max_attempts: int = 5,
    time_window: float = 300.0,  # 5分钟
    block_duration: float = 3600.0,  # 1小时
):
    入侵检测装饰器 / Intrusion Detection Decorator
    Args:
        max_attempts: 最大尝试次数 / Max attempts
        time_window: 时间窗口（秒）/ Time window (seconds)
        block_duration: 阻塞持续时间（秒）/ Block duration (seconds)
    Returns:
        Callable: 装饰器函数 / Decorator function
    suspicious_activities = {}
    blocked_users = {}
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        async def async_wrapper(*args, **kwargs):
            # 获取用户标识
            user_key = _extract_user_key(args, kwargs)
            if not user_key:
                # 如果无法识别用户，记录为可疑活动
                user_key = f"anonymous_{_get_client_ip(args, kwargs)}"
            current_time = time.time()
            # 检查用户是否被阻塞
            if user_key in blocked_users:
                block_end_time = blocked_users[user_key]
                if current_time < block_end_time:
                    remaining_time = block_end_time - current_time
                    raise SecurityError(f"用户已被阻塞，剩余时间: {remaining_time:.0f}秒")
                else:
                    # 阻塞时间已过，移除阻塞
                    del blocked_users[user_key]
            # 记录活动
            if user_key not in suspicious_activities:
                suspicious_activities[user_key] = []
            # 清理过期的活动记录
            suspicious_activities[user_key] = [
                activity_time for activity_time in suspicious_activities[user_key]
                if current_time - activity_time < time_window
            ]
            # 添加当前活动
            suspicious_activities[user_key].append(current_time)
            # 检查是否超过阈值
            if len(suspicious_activities[user_key]) > max_attempts:
                # 阻塞用户
                blocked_users[user_key] = current_time + block_duration
                logger.warning(f"检测到可疑活动，用户 {user_key} 已被阻塞 {block_duration} 秒")
                raise SecurityError("检测到可疑活动，用户已被阻塞")
            # 执行原函数
            return await func(*args, **kwargs)
        @functools.wraps(func)
        def sync_wrapper(*args, **kwargs):
            # 获取用户标识
            user_key = _extract_user_key(args, kwargs)
            if not user_key:
                # 如果无法识别用户，记录为可疑活动
                user_key = f"anonymous_{_get_client_ip(args, kwargs)}"
            current_time = time.time()
            # 检查用户是否被阻塞
            if user_key in blocked_users:
                block_end_time = blocked_users[user_key]
                if current_time < block_end_time:
                    remaining_time = block_end_time - current_time
                    raise SecurityError(f"用户已被阻塞，剩余时间: {remaining_time:.0f}秒")
                else:
                    # 阻塞时间已过，移除阻塞
                    del blocked_users[user_key]
            # 记录活动
            if user_key not in suspicious_activities:
                suspicious_activities[user_key] = []
            # 清理过期的活动记录
            suspicious_activities[user_key] = [
                activity_time for activity_time in suspicious_activities[user_key]
                if current_time - activity_time < time_window
            ]
            # 添加当前活动
            suspicious_activities[user_key].append(current_time)
            # 检查是否超过阈值
            if len(suspicious_activities[user_key]) > max_attempts:
                # 阻塞用户
                blocked_users[user_key] = current_time + block_duration
                logger.warning(f"检测到可疑活动，用户 {user_key} 已被阻塞 {block_duration} 秒")
                raise SecurityError("检测到可疑活动，用户已被阻塞")
            # 执行原函数
            return func(*args, **kwargs)
        # 根据函数类型返回合适的包装器
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        else:
            return sync_wrapper
    return decorator
# 辅助函数
def _extract_user_permissions(args: tuple, kwargs: dict) -> List[str]:
    # 尝试从不同位置获取用户权限
    if "current_user" in kwargs:
        user = kwargs["current_user"]
        if hasattr(user, 'permissions'):
            return user.permissions
        elif hasattr(user, 'get_permissions'):
            return user.get_permissions()
    # 尝试从第一个参数获取
    if args and hasattr(args[0], 'permissions'):
        return args[0].permissions
    # 尝试从kwargs获取
    for key in ['user', 'user_info', 'auth_user']:
        if key in kwargs:
            user = kwargs[key]
            if hasattr(user, 'permissions'):
                return user.permissions
    return []
def _extract_user_role(args: tuple, kwargs: dict) -> Optional[str]:
    # 尝试从不同位置获取用户角色
    if "current_user" in kwargs:
        user = kwargs["current_user"]
        if hasattr(user, 'role'):
            return user.role
    # 尝试从第一个参数获取
    if args and hasattr(args[0], 'role'):
        return args[0].role
    # 尝试从kwargs获取
    for key in ['user', 'user_info', 'auth_user']:
        if key in kwargs:
            user = kwargs[key]
            if hasattr(user, 'role'):
                return user.role
    return None
def _extract_user_info(args: tuple, kwargs: dict) -> Optional[Dict[str, Any]]:
    # 尝试从不同位置获取用户信息
    if "current_user" in kwargs:
        return kwargs["current_user"]
    # 尝试从第一个参数获取
    if args and hasattr(args[0], '__dict__'):
        return args[0]
    # 尝试从kwargs获取
    for key in ['user', 'user_info', 'auth_user']:
        if key in kwargs:
            return kwargs[key]
    return None
def _extract_user_key(args: tuple, kwargs: dict) -> Optional[str]:
    user_info = _extract_user_info(args, kwargs)
    if user_info:
        if hasattr(user_info, 'user_id'):
            return str(user_info.user_id)
        elif hasattr(user_info, 'id'):
            return str(user_info.id)
        elif hasattr(user_info, 'username'):
            return str(user_info.username)
    return None
def _extract_request(args: tuple, kwargs: dict) -> Optional[Any]:
    # 尝试从第一个参数获取（FastAPI风格）
    if args and hasattr(args[0], 'headers'):
        return args[0]
    # 尝试从kwargs获取
    if "request" in kwargs:
        return kwargs["request"]
    return None
def _get_client_ip(args: tuple, kwargs: dict) -> str:
    request = _extract_request(args, kwargs)
    if request:
        if hasattr(request, 'client') and request.client:
            return request.client.host
        elif hasattr(request, 'remote_addr'):
            return request.remote_addr
    return "unknown"
def _check_permissions(user_permissions: List[str], required_permission: str, require_all: bool) -> bool:
    if not user_permissions:
        return False
    if require_all:
        # 检查是否包含所有权限（如果required_permission是列表）
        if isinstance(required_permission, (list, tuple)):
            return all(perm in user_permissions for perm in required_permission)
        else:
            return required_permission in user_permissions
    else:
        # 检查是否包含任一权限
        if isinstance(required_permission, (list, tuple)):
            return any(perm in user_permissions for perm in required_permission)
        else:
            return required_permission in user_permissions
def _check_role(user_role: Optional[str], required_role: str, allow_higher: bool) -> bool:
    if not user_role:
        return False
    # 角色层次结构
    role_hierarchy = {
        "guest": 0,
        "user": 1,
        "member": 2,
        "moderator": 3,
        "admin": 4,
        "super_admin": 5,
        "root": 6,
    }
    user_level = role_hierarchy.get(user_role.lower(), 0)
    required_level = role_hierarchy.get(required_role.lower(), 0)
    if allow_higher:
        return user_level >= required_level
    else:
        return user_level == required_level
def _is_valid_authentication(user_info: Dict[str, Any]) -> bool:
    if not user_info:
        return False
    # 检查是否有过期时间
    if hasattr(user_info, 'expires_at'):
        return datetime.now() < user_info.expires_at
    # 检查是否有有效令牌
    if hasattr(user_info, 'token_valid'):
        return user_info.token_valid
    # 默认认为有效
    return True
async def _validate_input(validators: Dict[str, Callable], kwargs: dict, sanitize: bool) -> dict:
    validated_kwargs = kwargs.copy()
    for field, validator in validators.items():
        if field in kwargs:
            value = kwargs[field]
            try:
                # 执行验证
                if asyncio.iscoroutinefunction(validator):
                    validated_value = await validator(value)
                else:
                    validated_value = validator(value)
                validated_kwargs[field] = validated_value
            except Exception as e:
                raise ValidationError(f"字段 '{field}' 验证失败: {e}")
    return validated_kwargs
def _validate_input_sync(validators: Dict[str, Callable], kwargs: dict, sanitize: bool) -> dict:
    validated_kwargs = kwargs.copy()
    for field, validator in validators.items():
        if field in kwargs:
            value = kwargs[field]
            try:
                # 执行验证
                validated_value = validator(value)
                validated_kwargs[field] = validated_value
            except Exception as e:
                raise ValidationError(f"字段 '{field}' 验证失败: {e}")
    return validated_kwargs
def _validate_csrf_token(request: Any, token_header: str, session_token_key: str) -> bool:
    try:
        # 获取请求中的token
        request_token = request.headers.get(token_header)
        if not request_token:
            request_token = getattr(request, 'form', {}).get('csrf_token')
        # 获取会话中的token
        session_token = getattr(request, 'session', {}).get(session_token_key)
        # 验证token
        return request_token == session_token
    except Exception as e:
        logger.error(f"CSRF token验证失败: {e}")
        return False
# 自定义异常
class SecurityError(Exception):
    pass
class AuthenticationError(SecurityError):
    pass
class PermissionError(SecurityError):
    pass
class ValidationError(SecurityError):
    pass
class CSRFError(SecurityError):
    pass
class RateLimitExceededError(SecurityError):
    pass