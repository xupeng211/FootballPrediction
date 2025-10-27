"""
审计服务模型（兼容版本）
Audit Service Models (Compatibility Version)
"""

from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Any, Dict, Optional


class AuditAction(Enum):
    """审计动作"""

    CREATE = "create"
    UPDATE = "update"
    DELETE = "delete"
    READ = "read"
    LOGIN = "login"
    LOGOUT = "logout"
    EXPORT = "export"


class AuditSeverity(Enum):
    """审计严重级别"""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class AuditEvent:
    """审计事件"""

    id: str
    action: AuditAction
    severity: AuditSeverity
    user_id: str
    resource_type: str
    resource_id: Optional[str]
    message: str
    timestamp: datetime
    metadata: Optional[Dict[str, Any]] = None

    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}
