"""
审计服务模块（兼容版本）
Audit Service Module (Compatibility Version)
"""

from dataclasses import dataclass
from datetime import datetime

# 添加缺失的类定义
from typing import Any, Dict, List, Optional

from .audit_service import AuditService, DataSanitizer, SeverityAnalyzer
from .models import AuditAction, AuditEvent, AuditSeverity


@dataclass
class AuditContext:
    """类文档字符串"""

    pass  # 添加pass语句
    """审计上下文"""

    user_id: str
    session_id: Optional[str] = None
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None
    request_id: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None


@dataclass
class AuditLog:
    """类文档字符串"""

    pass  # 添加pass语句
    """审计日志"""

    id: str
    timestamp: datetime
    action: AuditAction
    user_id: str
    resource_type: str
    resource_id: Optional[str] = None
    message: str = ""
    severity: AuditSeverity = AuditSeverity.LOW
    metadata: Optional[Dict[str, Any]] = None


@dataclass
class AuditLogSummary:
    """类文档字符串"""

    pass  # 添加pass语句
    """审计日志摘要"""

    total_logs: int
    date_range: Dict[str, datetime]
    action_counts: Dict[str, int]
    severity_counts: Dict[str, int]
    top_users: List[Dict[str, Any]]
    top_resources: List[Dict[str, Any]]


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
