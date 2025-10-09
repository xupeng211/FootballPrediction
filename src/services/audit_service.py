"""
audit_service - 兼容性垫片

为了向后兼容，重新导出拆分后的模块。
建议使用: from src.services.audit_service_mod import AuditService
"""

# 从新的模块化实现重新导出
from .audit_service_mod import (
    AuditService,
    AuditContext,
    AuditAction,
    AuditSeverity,
    AuditLog,
    AuditLogSummary,
)

__all__ = [
    "AuditService",
    "AuditContext",
    "AuditAction",
    "AuditSeverity",
    "AuditLog",
    "AuditLogSummary",
]
