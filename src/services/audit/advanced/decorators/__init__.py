"""
装饰器模块
Decorators Module

提供审计、性能和安全相关的装饰器。
"""

from .audit_decorators import (
from .performance_decorator import (
from .security_decorator import (

    audit_action,
    audit_api_endpoint,
    audit_database_operation,
    audit_sensitive_operation,
    audit_batch_operation,
)

    monitor_performance,
    cache_result,
    rate_limit,
    retry_on_failure,
    timeout,
)

    require_permission,
    require_role,
    authenticate_user,
    rate_limit_by_user,
    validate_input,
    protect_csrf,
    detect_intrusion,
    SecurityError,
    AuthenticationError,
    PermissionError,
    ValidationError,
    CSRFError,
    RateLimitExceededError,
)

__all__ = [
    # 审计装饰器
    "audit_action",
    "audit_api_endpoint",
    "audit_database_operation",
    "audit_sensitive_operation",
    "audit_batch_operation",

    # 性能装饰器
    "monitor_performance",
    "cache_result",
    "rate_limit",
    "retry_on_failure",
    "timeout",

    # 安全装饰器
    "require_permission",
    "require_role",
    "authenticate_user",
    "rate_limit_by_user",
    "validate_input",
    "protect_csrf",
    "detect_intrusion",

    # 异常类
    "SecurityError",
    "AuthenticationError",
    "PermissionError",
    "ValidationError",
    "CSRFError",
    "RateLimitExceededError",
]