"""
审计服务模块（兼容性包装器）
Audit Service Module (Compatibility Wrapper)

提供向后兼容的接口，同时支持新的高级功能。
Provides backward-compatible interfaces while supporting new advanced features.
"""

# 导入原有的服务类以保持兼容性
from .service import AuditService as LegacyAuditService
from .context import AuditContext
from .models import (
    AuditAction,
    AuditSeverity,
    AuditLog,
    AuditLogSummary,
)

# 导入新的高级审计服务
from ..audit.advanced import (
    AuditService as AdvancedAuditService,
    DataAnalyzer,
    PatternAnalyzer,
    RiskAnalyzer,
    DataSanitizer,
    ReportGenerator,
    TemplateManager,
    ExportManager,
    # 导出装饰器
    audit_action,
    audit_api_endpoint,
    monitor_performance,
    require_permission,
    authenticate_user,
)

# 版本兼容性映射
def get_audit_service(use_advanced: bool = True, **kwargs):
    """
    获取审计服务实例 / Get Audit Service Instance

    Args:
        use_advanced: 是否使用高级版本 / Whether to use advanced version
        **kwargs: 其他参数 / Other parameters

    Returns:
        AuditService: 审计服务实例 / Audit service instance
    """
    if use_advanced:
        return AdvancedAuditService(**kwargs)
    else:
        return LegacyAuditService(**kwargs)

# 为了向后兼容，默认导出原有的服务类
AuditService = LegacyAuditService

__all__ = [
    # 向后兼容
    "AuditService",
    "AuditContext",
    "AuditAction",
    "AuditSeverity",
    "AuditLog",
    "AuditLogSummary",
    "LegacyAuditService",

    # 新的高级功能
    "AdvancedAuditService",
    "DataAnalyzer",
    "PatternAnalyzer",
    "RiskAnalyzer",
    "DataSanitizer",
    "ReportGenerator",
    "TemplateManager",
    "ExportManager",

    # 装饰器
    "audit_action",
    "audit_api_endpoint",
    "monitor_performance",
    "require_permission",
    "authenticate_user",

    # 工厂函数
    "get_audit_service",
]

# 版本信息
__version__ = "2.0.0"
__legacy_version__ = "1.0.0"