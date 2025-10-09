"""
    from .analyzers.data_analyzer import DataAnalyzer
    from .analyzers.pattern_analyzer import PatternAnalyzer
    from .analyzers.risk_analyzer import RiskAnalyzer
    from .decorators.audit_decorators import (
    from .decorators.performance_decorator import (
    from .decorators.security_decorator import (
    from .loggers.async_logger import AsyncLogger
    from .loggers.audit_logger import AuditLogger
    from .loggers.structured_logger import StructuredLogger
    from .reporters.export_manager import ExportManager
    from .reporters.report_generator import ReportGenerator
    from .reporters.template_manager import TemplateManager

高级审计服务
Advanced Audit Service

提供企业级的审计功能，包括数据分析、模式识别、风险评估等。
"""

from .context import AuditContext
from .models import (
from .sanitizer import DataSanitizer
from .service import AuditService

    AuditAction,
    AuditSeverity,
    AuditLog,
    AuditLogSummary,
    AuditFilter,
    AuditConfig,
)

__version__ = "1.0.0"
__author__ = "Audit Service Team"

# 延迟导入函数
def _import_analyzers():
    return DataAnalyzer, PatternAnalyzer, RiskAnalyzer

def _import_loggers():
    return AuditLogger, StructuredLogger, AsyncLogger

def _import_reporters():
    return ReportGenerator, TemplateManager, ExportManager

def _import_decorators():
        audit_action, audit_api_endpoint, audit_database_operation,
        audit_sensitive_operation, audit_batch_operation,
    )
        monitor_performance, cache_result, rate_limit,
        retry_on_failure, timeout,
    )
        require_permission, require_role, authenticate_user,
        rate_limit_by_user, validate_input, protect_csrf,
        detect_intrusion, SecurityError, AuthenticationError,
        PermissionError, ValidationError, CSRFError,
        RateLimitExceededError,
    )
    return (
        audit_action, audit_api_endpoint, audit_database_operation,
        audit_sensitive_operation, audit_batch_operation,
        monitor_performance, cache_result, rate_limit,
        retry_on_failure, timeout,
        require_permission, require_role, authenticate_user,
        rate_limit_by_user, validate_input, protect_csrf,
        detect_intrusion, SecurityError, AuthenticationError,
        PermissionError, ValidationError, CSRFError,
        RateLimitExceededError,
    )

# 添加延迟导入属性
def __getattr__(name):
    if name in ["DataAnalyzer", "PatternAnalyzer", "RiskAnalyzer"]:
        DataAnalyzer, PatternAnalyzer, RiskAnalyzer = _import_analyzers()
        globals().update({
            "DataAnalyzer": DataAnalyzer,
            "PatternAnalyzer": PatternAnalyzer,
            "RiskAnalyzer": RiskAnalyzer,
        })
        return locals()[name]
    elif name in ["AuditLogger", "StructuredLogger", "AsyncLogger"]:
        AuditLogger, StructuredLogger, AsyncLogger = _import_loggers()
        globals().update({
            "AuditLogger": AuditLogger,
            "StructuredLogger": StructuredLogger,
            "AsyncLogger": AsyncLogger,
        })
        return locals()[name]
    elif name in ["ReportGenerator", "TemplateManager", "ExportManager"]:
        ReportGenerator, TemplateManager, ExportManager = _import_reporters()
        globals().update({
            "ReportGenerator": ReportGenerator,
            "TemplateManager": TemplateManager,
            "ExportManager": ExportManager,
        })
        return locals()[name]
    elif name in [
        "audit_action", "audit_api_endpoint", "audit_database_operation",
        "audit_sensitive_operation", "audit_batch_operation",
        "monitor_performance", "cache_result", "rate_limit",
        "retry_on_failure", "timeout",
        "require_permission", "require_role", "authenticate_user",
        "rate_limit_by_user", "validate_input", "protect_csrf",
        "detect_intrusion", "SecurityError", "AuthenticationError",
        "PermissionError", "ValidationError", "CSRFError",
        "RateLimitExceededError",
    ]:
        decorators = _import_decorators()
        for i, decorator_name in enumerate([
            "audit_action", "audit_api_endpoint", "audit_database_operation",
            "audit_sensitive_operation", "audit_batch_operation",
            "monitor_performance", "cache_result", "rate_limit",
            "retry_on_failure", "timeout",
            "require_permission", "require_role", "authenticate_user",
            "rate_limit_by_user", "validate_input", "protect_csrf",
            "detect_intrusion", "SecurityError", "AuthenticationError",
            "PermissionError", "ValidationError", "CSRFError",
            "RateLimitExceededError",
        ]):
            globals()[decorator_name] = decorators[i]
        return locals()[name]
    else:
        raise AttributeError(f"module '{__name__}' has no attribute '{name}'")

__all__ = [
    # 核心类
    "AuditService",
    "AuditContext",
    "DataSanitizer",

    # 模型类
    "AuditAction",
    "AuditSeverity",
    "AuditLog",
    "AuditLogSummary",
    "AuditFilter",
    "AuditConfig",

    # 分析器
    "DataAnalyzer",
    "PatternAnalyzer",
    "RiskAnalyzer",

    # 日志器
    "AuditLogger",
    "StructuredLogger",
    "AsyncLogger",

    # 报告器
    "ReportGenerator",
    "TemplateManager",
    "ExportManager",

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