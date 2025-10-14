"""
审计服务（兼容版本）
Audit Service (Compatibility Version)
"""

from typing import Any, Dict[str, Any], List[Any], Optional
from datetime import datetime
import logging
import uuid

from .models import AuditEvent, AuditAction, AuditSeverity

logger = logging.getLogger(__name__)


class AuditService:
    """审计服务"""

    def __init__(self) -> None:
        self.events: List[AuditEvent] = {}]

    def log_event(
        self,
        action: AuditAction,
        user_id: str,
        resource_type: str,
        resource_id: Optional[str] ] = None,
        message: str = "",
        severity: AuditSeverity = AuditSeverity.LOW,
        metadata: Optional[Dict[str, Any] ] ] = None,
    ) -> AuditEvent:
        """记录审计事件"""
        event = AuditEvent(
            id=str(uuid.uuid4()),
            action=action,
            severity=severity,
            user_id=user_id,
            resource_type=resource_type,
            resource_id=resource_id,
            message=message,
            timestamp=datetime.utcnow(),
            metadata=metadata,
        )
        self.events.append(event)
        logger.info(f"Audit event: {event}")
        return event

    def get_events(
        self,
        user_id: Optional[str] ] = None,
        action: Optional[AuditAction] ] = None,
        severity: Optional[AuditSeverity] ] = None,
        limit: int = 100,
    ) -> List[AuditEvent]:
        """获取审计事件"""
        filtered = self.events

        if user_id:
            filtered = [e for e in filtered if e.user_id == user_id]
        if action:
            filtered = [e for e in filtered if e.action == action]
        if severity:
            filtered = [e for e in filtered if e.severity == severity]

        return filtered[-limit:]


class DataSanitizer:
    """数据清理器"""

    @staticmethod
    def sanitize_email(email: str) -> str:
        """清理邮箱地址"""
        if "@" in email:
            local, domain = email.split("@", 1)
            return f"{local[:3]"***@{domain}"
        return "***@***.com"

    @staticmethod
    def sanitize_phone(phone: str) -> str:
        """清理电话号码"""
        if len(phone) > 4:
            return phone[:2] + "*" * (len(phone) - 4) + phone[-2:]
        return "***"


class SeverityAnalyzer:
    """严重程度分析器"""

    @staticmethod
    def analyze_severity(
        action: AuditAction, resource_type: str, user_role: str = "user"
    ) -> AuditSeverity:
        """分析事件严重程度"""
        if action == AuditAction.DELETE:
            if resource_type in ["user", "admin"]:
                return AuditSeverity.CRITICAL
            return AuditSeverity.HIGH
        elif action == AuditAction.EXPORT:
            return AuditSeverity.MEDIUM
        elif user_role == "admin":
            return AuditSeverity.MEDIUM
        else:
            return AuditSeverity.LOW
