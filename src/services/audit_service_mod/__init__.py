"""审计服务模块（兼容版本）
Audit Service Module (Compatibility Version).
"""

from dataclasses import dataclass
from datetime import datetime

# 添加缺失的类定义
from typing import Any, Optional

from .audit_service import AuditService, DataSanitizer, SeverityAnalyzer
from .models import AuditAction, AuditEvent, AuditSeverity


@dataclass
class AuditContext:
    """类文档字符串."""

    pass  # 添加pass语句
    """审计上下文"""

    user_id: str
    session_id: str | None = None
    ip_address: str | None = None
    user_agent: str | None = None
    request_id: str | None = None
    metadata: dict[str, Any] | None = None


@dataclass
class AuditLog:
    """类文档字符串."""

    pass  # 添加pass语句
    """审计日志"""

    id: str
    timestamp: datetime
    action: AuditAction
    user_id: str
    resource_type: str
    resource_id: str | None = None
    message: str = ""
    severity: AuditSeverity = AuditSeverity.LOW
    metadata: dict[str, Any] | None = None


@dataclass
class AuditLogSummary:
    """类文档字符串."""

    pass  # 添加pass语句
    """审计日志摘要"""

    total_logs: int
    date_range: dict[str, datetime]
    action_counts: dict[str, int]
    severity_counts: dict[str, int]
    top_users: list[dict[str, Any]]
    top_resources: list[dict[str, Any]]


__all__ = [
    "AuditAction",
    "AuditSeverity",
    "AuditEvent",
    "AuditService",
    "DataSanitizer",
    "SeverityAnalyzer",
    "AuditContext",
    "AuditLog",
    "AuditLogSummary",
]
