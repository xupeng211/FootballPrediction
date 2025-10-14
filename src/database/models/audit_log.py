from typing import Any,  Dict[str, Any],  Any, Optional
from datetime import datetime
from datetime import timedelta
from enum import Enum
from sqlalchemy import Boolean, Column, DateTime, Index, Integer, String, Text, func

"""
权限审计日志模型

实现全面的数据库操作审计功能，记录所有敏感数据的访问和修改操作。
支持合规要求和安全审计。

基于 DATA_DESIGN.md 中的权限控制设计。
"""

from datetime import datetime, timedelta
from typing import Any,  Dict[str, Any],  Any, Optional
from sqlalchemy import Boolean, Column, DateTime, Index, Integer, String, Text
from sqlalchemy.sql import func
from ..base import BaseModel
from ..types import SQLiteCompatibleJSONB
from sqlalchemy import Column
from sqlalchemy import DateTime
from sqlalchemy import Enum  # type: ignore
from sqlalchemy import Index
from sqlalchemy import Integer
from sqlalchemy import String
from sqlalchemy import Text


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
    """
    权限审计日志模型

    记录系统中所有敏感操作的详细信息，包括：
    - 用户身份和操作类型
    - 受影响的数据表和字段
    - 操作前后的数据值
    - 操作时间和上下文信息
    """

    __tablename__ = "audit_logs"

    # 主键
    id = Column(Integer, primary_key=True, autoincrement=True, comment="审计日志ID")

    # 用户信息
    user_id = Column(String(100), nullable=False, comment="操作用户ID")
    username = Column(String(100), nullable=True, comment="操作用户名")
    user_role = Column(String(50), nullable=True, comment="用户角色")
    session_id = Column(String(100), nullable=True, comment="会话ID")

    # 操作信息
    action = Column(String(50), nullable=False, comment="操作类型")
    severity = Column(
        String(20), nullable=False, default=AuditSeverity.MEDIUM, comment="严重级别"
    )
    table_name = Column(String(100), nullable=True, comment="目标表名")
    column_name = Column(String(100), nullable=True, comment="目标列名")
    record_id = Column(String(100), nullable=True, comment="记录ID")

    # 数据变更信息
    old_value = Column(Text, nullable=True, comment="操作前值")
    new_value = Column(Text, nullable=True, comment="操作后值")
    old_value_hash = Column(String(64), nullable=True, comment="旧值哈希（敏感数据）")
    new_value_hash = Column(String(64), nullable=True, comment="新值哈希（敏感数据）")

    # 上下文信息
    ip_address = Column(String(45), nullable=True, comment="客户端IP地址")
    user_agent = Column(Text, nullable=True, comment="用户代理")
    request_path = Column(String(500), nullable=True, comment="请求路径")
    request_method = Column(String(10), nullable=True, comment="HTTP方法")

    # 操作结果
    success = Column(
        Boolean,
        nullable=False,
        default=True,
        server_default="true",
        comment="操作是否成功",
    )
    error_message = Column(Text, nullable=True, comment="错误信息")

    # 时间信息
    timestamp = Column(
        DateTime(timezone=True),
        nullable=False,
        default=func.now(),
        comment="操作时间戳",
    )
    duration_ms = Column(Integer, nullable=True, comment="操作耗时（毫秒）")

    # 扩展信息
    extra_data = Column(SQLiteCompatibleJSONB, nullable=True, comment="扩展元数据")
    tags = Column(String(500), nullable=True, comment="标签（逗号分隔）")

    # 合规相关
    compliance_category = Column(String(100), nullable=True, comment="合规分类")
    retention_period_days = Column(
        Integer, nullable=True, default=2555, comment="保留期限（天）"
    )  # 7年
    is_sensitive = Column(
        Boolean, nullable=False, default=False, comment="是否包含敏感数据"
    )

    # 索引优化
    __table_args__ = (
        Index("idx_audit_user_timestamp", "user_id", "timestamp"),
        Index("idx_audit_table_action", "table_name", "action"),
        Index("idx_audit_timestamp", "timestamp"),
        Index("idx_audit_severity", "severity"),
        Index("idx_audit_success", "success"),
        Index("idx_audit_sensitive", "is_sensitive"),
        Index("idx_audit_compliance", "compliance_category"),
        {"comment": "权限审计日志表，记录所有敏感操作的详细信息"},
    )

    def __repr__(self) -> str:
        """字符串表示"""
        return (
            f"<AuditLog(id={self.id}, user_id='{self.user_id}', "
            f"action='{self.action}', table_name='{self.table_name}', "
            f"timestamp='{self.timestamp}')>"
        )

    @property
    def is_high_risk(self) -> bool:
        """判断是否为高风险操作"""
        high_risk_actions = {
            AuditAction.DELETE,
            AuditAction.GRANT,
            AuditAction.REVOKE,
            AuditAction.BACKUP,
            AuditAction.RESTORE,
            AuditAction.SCHEMA_CHANGE,
        }
        return self.action in high_risk_actions or self.severity in [
            AuditSeverity.HIGH,
            AuditSeverity.CRITICAL,
        ]

    @property
    def risk_score(self) -> int:
        """计算风险评分（0-100）"""
        base_score = {  # type: ignore
            AuditSeverity.INFO: 5,
            AuditSeverity.LOW: 10,
            AuditSeverity.MEDIUM: 30,
            AuditSeverity.HIGH: 70,
            AuditSeverity.CRITICAL: 90,
        }.get(str(self.severity), 30)

        # 根据操作类型调整分数
        if self.action == AuditAction.DELETE:
            base_score += 20
        elif self.action in [AuditAction.GRANT, AuditAction.REVOKE]:
            base_score += 15
        elif self.action in [AuditAction.BACKUP, AuditAction.RESTORE]:
            base_score += 10

        # 敏感数据操作额外加分
        if self.is_sensitive:
            base_score += 15

        # 失败操作额外加分
        if not self.success:
            base_score += 10

        return min(base_score, 100)  # type: ignore

    def to_dict(self, exclude_fields: Optional[set[Any]] = None) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            "id": self.id,
            "user_id": self.user_id,
            "username": self.username,
            "user_role": self.user_role,
            "action": self.action,
            "severity": self.severity,
            "table_name": self.table_name,
            "column_name": self.column_name,
            "record_id": self.record_id,
            "old_value": self.old_value,
            "new_value": self.new_value,
            "ip_address": self.ip_address,
            "user_agent": self.user_agent,
            "request_path": self.request_path,
            "request_method": self.request_method,
            "success": self.success,
            "error_message": self.error_message,
            "timestamp": self.timestamp.isoformat() if self.timestamp else None,
            "duration_ms": self.duration_ms,
            "extra_data": self.extra_data,
            "tags": self.tags,
            "compliance_category": self.compliance_category,
            "is_sensitive": self.is_sensitive,
            "risk_score": self.risk_score,
            "is_high_risk": self.is_high_risk,
        }

    def set_extra_data(self, **kwargs) -> None:
        """设置扩展数据"""
        if self.extra_data is None:
            self.extra_data = {}  # type: ignore
        self.extra_data.update(kwargs)

    def add_tag(self, tag: str) -> None:
        """添加标签"""
        if self.tags:
            tags_list = [t.strip() for t in self.tags.split(",")]
            if tag not in tags_list:
                tags_list.append(tag)
                self.tags = ",".join(tags_list)  # type: ignore
        else:
            self.tags = tag  # type: ignore

    def remove_tag(self, tag: str) -> None:
        """移除标签"""
        if self.tags:
            tags_list = [t.strip() for t in self.tags.split(",")]
            if tag in tags_list:
                tags_list.remove(tag)
                self.tags = ",".join(tags_list) if tags_list else None  # type: ignore

    @classmethod
    def create_audit_entry(
        cls,
        user_id: str,
        action: str,
        table_name: Optional[str] = None,
        column_name: Optional[str] = None,
        old_value: Optional[str] = None,
        new_value: Optional[str] = None,
        **kwargs,
    ) -> "AuditLog":
        """
        创建审计日志条目的便捷方法

        Args:
            user_id: 操作用户ID
            action: 操作类型
            table_name: 目标表名
            column_name: 目标列名
            old_value: 操作前值
            new_value: 操作后值
            **kwargs: 其他属性

        Returns:
            AuditLog: 审计日志实例
        """
        # 自动确定严重级别
        if "severity" not in kwargs:
            if action in [AuditAction.DELETE, AuditAction.GRANT, AuditAction.REVOKE]:
                kwargs["severity"] = AuditSeverity.HIGH
            elif action in [
                AuditAction.BACKUP,
                AuditAction.RESTORE,
                AuditAction.SCHEMA_CHANGE,
            ]:
                kwargs["severity"] = AuditSeverity.CRITICAL
            elif action == AuditAction.READ:
                kwargs["severity"] = AuditSeverity.LOW
            else:
                kwargs["severity"] = AuditSeverity.MEDIUM

        # 判断是否为敏感数据
        if "is_sensitive" not in kwargs:
            sensitive_tables = {"users", "permissions", "tokens", "passwords"}
            sensitive_columns = {"password", "token", "secret", "key", "email", "phone"}

            kwargs["is_sensitive"] = table_name in sensitive_tables or (
                column_name and any(s in column_name.lower() for s in sensitive_columns)
            )

        # 设置默认合规分类
        if "compliance_category" not in kwargs:
            # 优先检查权限相关操作
            if action in [AuditAction.GRANT, AuditAction.REVOKE]:
                kwargs["compliance_category"] = "ACCESS_CONTROL"
            elif action in [AuditAction.BACKUP, AuditAction.RESTORE]:
                kwargs["compliance_category"] = "DATA_PROTECTION"
            elif kwargs.get("is_sensitive"):
                kwargs[
                    "compliance_category"
                ] = "PII"  # Personally Identifiable Information
            else:
                kwargs["compliance_category"] = "GENERAL"

        return cls(
            user_id=user_id,
            action=action,
            table_name=table_name,
            column_name=column_name,
            old_value=old_value,
            new_value=new_value,
            **kwargs,
        )


class AuditLogSummary:
    """审计日志统计摘要类"""

    def __init__(self, session):
        """初始化"""
        self.session = session

    def get_user_activity_summary(self, user_id: str, days: int = 30) -> Dict[str, Any]:
        """获取用户活动摘要"""
        from sqlalchemy import and_, func

        cutoff_date = datetime.now() - timedelta(days=days)

        # 基础统计
        total_actions = (
            self.session.query(AuditLog)
            .filter(
                and_(AuditLog.user_id == user_id, AuditLog.timestamp >= cutoff_date)
            )
            .count()
        )

        # 按操作类型统计
        action_stats = (
            self.session.query(AuditLog.action, func.count(AuditLog.id).label("count"))
            .filter(
                and_(AuditLog.user_id == user_id, AuditLog.timestamp >= cutoff_date)
            )
            .group_by(AuditLog.action)
            .all()  # type: ignore
        )

        # 按严重级别统计
        severity_stats = (
            self.session.query(
                AuditLog.severity, func.count(AuditLog.id).label("count")
            )
            .filter(
                and_(AuditLog.user_id == user_id, AuditLog.timestamp >= cutoff_date)
            )
            .group_by(AuditLog.severity)
            .all()  # type: ignore
        )

        # 高风险操作
        high_risk_count = (
            self.session.query(AuditLog)
            .filter(
                and_(
                    AuditLog.user_id == user_id,
                    AuditLog.timestamp >= cutoff_date,
                    AuditLog.severity.in_([AuditSeverity.HIGH, AuditSeverity.CRITICAL]),
                )
            )
            .count()
        )

        # 失败操作
        failed_count = (
            self.session.query(AuditLog)
            .filter(
                and_(
                    AuditLog.user_id == user_id,
                    AuditLog.timestamp >= cutoff_date,
                    AuditLog.success.is_(False),
                )
            )
            .count()
        )

        return {
            "user_id": user_id,
            "period_days": days,
            "total_actions": total_actions,
            "action_breakdown": {action: count for action, count in action_stats},
            "severity_breakdown": {
                severity: count for severity, count in severity_stats
            },
            "high_risk_actions": high_risk_count,
            "failed_actions": failed_count,
            "risk_ratio": high_risk_count / max(total_actions, 1),
            "failure_ratio": failed_count / max(total_actions, 1),
        }

    def get_table_activity_summary(
        self, table_name: str, days: int = 7
    ) -> Dict[str, Any]:
        """获取表操作活动摘要"""

        cutoff_date = datetime.now() - timedelta(days=days)

        # 基础统计
        total_operations = (
            self.session.query(AuditLog)
            .filter(
                and_(  # type: ignore
                    AuditLog.table_name == table_name, AuditLog.timestamp >= cutoff_date
                )
            )
            .count()
        )

        # 按操作类型统计
        operation_stats = (
            self.session.query(AuditLog.action, func.count(AuditLog.id).label("count"))
            .filter(
                and_(  # type: ignore
                    AuditLog.table_name == table_name, AuditLog.timestamp >= cutoff_date
                )
            )
            .group_by(AuditLog.action)
            .all()  # type: ignore
        )

        # 按用户统计
        user_stats = (
            self.session.query(AuditLog.user_id, func.count(AuditLog.id).label("count"))
            .filter(
                and_(  # type: ignore
                    AuditLog.table_name == table_name, AuditLog.timestamp >= cutoff_date
                )
            )
            .group_by(AuditLog.user_id)
            .all()  # type: ignore
        )

        return {
            "table_name": table_name,
            "period_days": days,
            "total_operations": total_operations,
            "operation_breakdown": {action: count for action, count in operation_stats},
            "user_breakdown": {user_id: count for user_id, count in user_stats},
            "operations_per_day": total_operations / days,
        }
