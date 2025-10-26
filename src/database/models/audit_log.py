from typing import Any, Dict, Optional
from datetime import datetime, timedelta
from enum import Enum
from sqlalchemy import Boolean, Column, DateTime, Index, Integer, String, Text, func
from sqlalchemy.sql import func
from ..base import BaseModel
from ..types import SQLiteCompatibleJSONB

"""
权限审计日志模型

实现全面的数据库操作审计功能，记录所有敏感数据的访问和修改操作。
支持合规要求和安全审计。

基于 DATA_DESIGN.md 中的权限控制设计。
"""


class AuditAction(str, Enum):
    """审计操作类型枚举"""

    # 数据操作
    CREATE = "CREATE"  # 创建记录
    READ = "READ"  # 读取记录
    UPDATE = "UPDATE"  # 更新记录
    DELETE = "DELETE"  # 删除记录

    # 权限操作
    GRANT = "GRANT"  # 授予权限
    REVOKE = "REVOKE"  # 撤销权限

    # 系统操作
    LOGIN = "LOGIN"  # 用户登录
    LOGOUT = "LOGOUT"  # 用户登出
    BACKUP = "BACKUP"  # 数据备份
    RESTORE = "RESTORE"  # 数据恢复

    # 配置操作
    CONFIG_CHANGE = "CONFIG_CHANGE"  # 配置变更
    SCHEMA_CHANGE = "SCHEMA_CHANGE"  # 架构变更


class AuditSeverity(str, Enum):
    """审计事件严重级别"""

    INFO = "INFO"  # 信息级：一般性成功事件
    LOW = "LOW"  # 低风险：普通读操作
    MEDIUM = "MEDIUM"  # 中风险：普通写操作
    HIGH = "HIGH"  # 高风险：删除、权限变更
    CRITICAL = "CRITICAL"  # 极高风险：系统级操作


class AuditLog(BaseModel):
    __table_args__ = {"extend_existing": True}
    __tablename__ = "audit_logs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, nullable=True, index=True)
    username = Column(String(255), nullable=True, index=True)
    action = Column(String(50), nullable=False, index=True)
    resource_type = Column(String(100), nullable=True, index=True)
    resource_id = Column(String(100), nullable=True, index=True)
    severity = Column(String(20), nullable=False, default="INFO", index=True)
    ip_address = Column(String(45), nullable=True)
    user_agent = Column(Text, nullable=True)
    details = Column(Text, nullable=True)
    audit_metadata = Column(SQLiteCompatibleJSONB, nullable=True)
    timestamp = Column(DateTime, nullable=False, default=func.now(), index=True)
    session_id = Column(String(255), nullable=True, index=True)

    # 索引定义
    __table_args__ = (
        Index("idx_audit_user_action", "user_id", "action"),
        Index("idx_audit_timestamp_severity", "timestamp", "severity"),
        Index("idx_audit_resource", "resource_type", "resource_id"),
        {"extend_existing": True},
    )

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            "id": self.id,
            "user_id": self.user_id,
            "username": self.username,
            "action": self.action,
            "resource_type": self.resource_type,
            "resource_id": self.resource_id,
            "severity": self.severity,
            "ip_address": self.ip_address,
            "user_agent": self.user_agent,
            "details": self.details,
            "audit_metadata": self.audit_metadata,
            "timestamp": self.timestamp.isoformat() if self.timestamp else None,
            "session_id": self.session_id,
        }


class AuditLogSummary(BaseModel):
    """审计日志汇总模型"""

    __table_args__ = {"extend_existing": True}
    __tablename__ = "audit_log_summaries"

    id = Column(Integer, primary_key=True, autoincrement=True)
    date = Column(DateTime, nullable=False, index=True)
    total_actions = Column(Integer, nullable=False, default=0)
    actions_by_type = Column(SQLiteCompatibleJSONB, nullable=True)
    actions_by_severity = Column(SQLiteCompatibleJSONB, nullable=True)
    top_users = Column(SQLiteCompatibleJSONB, nullable=True)
    top_resources = Column(SQLiteCompatibleJSONB, nullable=True)
    created_at = Column(DateTime, nullable=False, default=func.now())

    # 索引定义
    __table_args__ = (Index("idx_summary_date", "date"), {"extend_existing": True})

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            "id": self.id,
            "date": self.date.isoformat() if self.date else None,
            "total_actions": self.total_actions,
            "actions_by_type": self.actions_by_type,
            "actions_by_severity": self.actions_by_severity,
            "top_users": self.top_users,
            "top_resources": self.top_resources,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
