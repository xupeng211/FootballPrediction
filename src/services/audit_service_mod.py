
"""Audit Service - 简化版本"""

from typing import Dict, Any, Optional
from datetime import datetime
from enum import Enum

class AuditSeverity(Enum):
    """审计严重程度"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"

class AuditEvent:
    """审计事件"""

    def __init__(self, action: str, user: str, severity: AuditSeverity, details: Dict[str, Any]):
        self.action = action
        self.user = user
        self.severity = severity
        self.details = details
        self.timestamp = datetime.utcnow()

class DataSanitizer:
    """数据清理器 - 简化版本"""

    def sanitize(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """清理敏感数据"""
        # 简化的清理逻辑
        sanitized = data.copy()
        if "password" in sanitized:
            sanitized["password"] = "***"
        if "token" in sanitized:
            sanitized["token"] = "***"
        return sanitized

class SeverityAnalyzer:
    """严重程度分析器"""

    def analyze(self, event: AuditEvent) -> AuditSeverity:
        """分析事件严重程度"""
        # 简化的分析逻辑
        if "delete" in event.action.lower():
            return AuditSeverity.HIGH
        elif "modify" in event.action.lower():
            return AuditSeverity.MEDIUM
        return AuditSeverity.LOW

class AuditService:
    """审计服务 - 简化版本"""

    def __init__(self):
        self.events: List[AuditEvent] = []
        self.sanitizer = DataSanitizer()
        self.analyzer = SeverityAnalyzer()

    def log_event(self, action: str, user: str, details: Dict[str, Any]):
        """记录审计事件"""
        # 清理数据
        sanitized_details = self.sanitizer.sanitize(details)

        # 创建事件
        event = AuditEvent(action, user, AuditSeverity.LOW, sanitized_details)

        # 分析严重程度
        event.severity = self.analyzer.analyze(event)

        self.events.append(event)
        return event

    def get_events(self, limit: int = 100) -> List[AuditEvent]:
        """获取审计事件"""
        return self.events[-limit:]
