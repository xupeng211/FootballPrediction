"""
审计模型
Audit Models

定义审计相关的数据模型和枚举。
"""

from enum import Enum
from typing import Any, Dict, List, Optional
from dataclasses import dataclass
from datetime import datetime


class AuditAction(str, Enum):
    """
    审计动作枚举 / Audit Action Enumeration

    定义所有可能的审计动作类型。
    Defines all possible audit action types.

    CREATE: 创建操作 / Create operation
    READ: 读取操作 / Read operation
    UPDATE: 更新操作 / Update operation
    DELETE: 删除操作 / Delete operation
    LOGIN: 登录操作 / Login operation
    LOGOUT: 登出操作 / Logout operation
    EXPORT: 导出操作 / Export operation
    IMPORT: 导入操作 / Import operation
    ACCESS: 访问操作 / Access operation
    EXECUTE: 执行操作 / Execute operation
    """

    CREATE = "create"
    READ = "read"
    UPDATE = "update"
    DELETE = "delete"
    LOGIN = "login"
    LOGOUT = "logout"
    EXPORT = "export"
    IMPORT = "import"
    ACCESS = "access"
    EXECUTE = "execute"


class AuditSeverity(str, Enum):
    """
    审计严重性枚举 / Audit Severity Enumeration

    定义审计事件的严重级别。
    Defines severity levels for audit events.

    LOW: 低严重性 / Low severity
    MEDIUM: 中等严重性 / Medium severity
    HIGH: 高严重性 / High severity
    CRITICAL: 严重性 / Critical severity
    """

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class AuditLog:
    """
    审计日志数据类 / Audit Log Data Class

    存储单个审计事件的详细信息。
    Stores detailed information of a single audit event.

    Attributes:
        id (Optional[int]): 日志ID / Log ID
        timestamp (datetime): 时间戳 / Timestamp
        user_id (str): 用户ID / User ID
        username (Optional[str]): 用户名 / Username
        user_role (Optional[str]): 用户角色 / User role
        session_id (Optional[str]): 会话ID / Session ID
        action (AuditAction): 动作类型 / Action type
        resource_type (Optional[str]): 资源类型 / Resource type
        resource_id (Optional[str]): 资源ID / Resource ID
        description (str): 描述 / Description
        ip_address (Optional[str]): IP地址 / IP address
        user_agent (Optional[str]): 用户代理 / User agent
        old_values (Optional[Dict[str, Any]]): 旧值 / Old values
        new_values (Optional[Dict[str, Any]]): 新值 / New values
        severity (AuditSeverity): 严重性 / Severity
        table_name (Optional[str]): 表名 / Table name
        compliance_category (Optional[str]): 合规类别 / Compliance category
        request_id (Optional[str]): 请求ID / Request ID
        correlation_id (Optional[str]): 关联ID / Correlation ID
        metadata (Optional[Dict[str, Any]]): 元数据 / Metadata
    """

    id: Optional[int] = None
    timestamp: datetime = None
    user_id: str = ""
    username: Optional[str] = None
    user_role: Optional[str] = None
    session_id: Optional[str] = None
    action: AuditAction = AuditAction.READ
    resource_type: Optional[str] = None
    resource_id: Optional[str] = None
    description: str = ""
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None
    old_values: Optional[Dict[str, Any]] = None
    new_values: Optional[Dict[str, Any]] = None
    severity: AuditSeverity = AuditSeverity.LOW
    table_name: Optional[str] = None
    compliance_category: Optional[str] = None
    request_id: Optional[str] = None
    correlation_id: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None

    def to_dict(self) -> Dict[str, Any]:
        """
        转换为字典 / Convert to Dictionary

        Returns:
            Dict[str, Any]: 日志字典 / Log dictionary
        """
        return {
            "id": self.id,
            "timestamp": self.timestamp.isoformat() if self.timestamp else None,
            "user_id": self.user_id,
            "username": self.username,
            "user_role": self.user_role,
            "session_id": self.session_id,
            "action": self.action.value if self.action else None,
            "resource_type": self.resource_type,
            "resource_id": self.resource_id,
            "description": self.description,
            "ip_address": self.ip_address,
            "user_agent": self.user_agent,
            "old_values": self.old_values,
            "new_values": self.new_values,
            "severity": self.severity.value if self.severity else None,
            "table_name": self.table_name,
            "compliance_category": self.compliance_category,
            "request_id": self.request_id,
            "correlation_id": self.correlation_id,
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "AuditLog":
        """
        从字典创建日志 / Create Log from Dictionary

        Args:
            data: 日志字典 / Log dictionary

        Returns:
            AuditLog: 审计日志对象 / Audit log object
        """
        # 处理时间戳
        timestamp = data.get("timestamp")
        if isinstance(timestamp, str):
            timestamp = datetime.fromisoformat(timestamp)

        # 处理枚举
        action = data.get("action")
        if action and isinstance(action, str):
            action = AuditAction(action)

        severity = data.get("severity")
        if severity and isinstance(severity, str):
            severity = AuditSeverity(severity)

        return cls(
            id=data.get("id"),
            timestamp=timestamp,
            user_id=data.get("user_id", ""),
            username=data.get("username"),
            user_role=data.get("user_role"),
            session_id=data.get("session_id"),
            action=action,
            resource_type=data.get("resource_type"),
            resource_id=data.get("resource_id"),
            description=data.get("description", ""),
            ip_address=data.get("ip_address"),
            user_agent=data.get("user_agent"),
            old_values=data.get("old_values"),
            new_values=data.get("new_values"),
            severity=severity,
            table_name=data.get("table_name"),
            compliance_category=data.get("compliance_category"),
            request_id=data.get("request_id"),
            correlation_id=data.get("correlation_id"),
            metadata=data.get("metadata"),
        )


@dataclass
class AuditLogSummary:
    """
    审计日志摘要数据类 / Audit Log Summary Data Class

    存储审计日志的统计摘要信息。
    Stores statistical summary information of audit logs.

    Attributes:
        total_logs (int): 总日志数 / Total logs
        action_counts (Dict[str, int]): 动作计数 / Action counts
        severity_counts (Dict[str, int]): 严重性计数 / Severity counts
        user_counts (Dict[str, int]): 用户计数 / User counts
        resource_counts (Dict[str, int]): 资源计数 / Resource counts
        date_range (Dict[str, datetime]): 日期范围 / Date range
        top_actions (List[Dict[str, Any]]): 热门动作 / Top actions
        high_risk_operations (List[Dict[str, Any]]): 高风险操作 / High risk operations
    """

    total_logs: int = 0
    action_counts: Dict[str, int] = None
    severity_counts: Dict[str, int] = None
    user_counts: Dict[str, int] = None
    resource_counts: Dict[str, int] = None
    date_range: Dict[str, datetime] = None
    top_actions: List[Dict[str, Any]] = None
    high_risk_operations: List[Dict[str, Any]] = None

    def __post_init__(self):
        if self.action_counts is None:
            self.action_counts = {}
        if self.severity_counts is None:
            self.severity_counts = {}
        if self.user_counts is None:
            self.user_counts = {}
        if self.resource_counts is None:
            self.resource_counts = {}
        if self.date_range is None:
            self.date_range = {}
        if self.top_actions is None:
            self.top_actions = []
        if self.high_risk_operations is None:
            self.high_risk_operations = []

    def to_dict(self) -> Dict[str, Any]:
        """
        转换为字典 / Convert to Dictionary

        Returns:
            Dict[str, Any]: 摘要字典 / Summary dictionary
        """
        return {
            "total_logs": self.total_logs,
            "action_counts": self.action_counts,
            "severity_counts": self.severity_counts,
            "user_counts": self.user_counts,
            "resource_counts": self.resource_counts,
            "date_range": {
                "start": self.date_range.get("start").isoformat() if self.date_range.get("start") else None,
                "end": self.date_range.get("end").isoformat() if self.date_range.get("end") else None,
            },
            "top_actions": self.top_actions,
            "high_risk_operations": self.high_risk_operations,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "AuditLogSummary":
        """
        从字典创建摘要 / Create Summary from Dictionary

        Args:
            data: 摘要字典 / Summary dictionary

        Returns:
            AuditLogSummary: 审计摘要对象 / Audit summary object
        """
        # 处理日期范围
        date_range = data.get("date_range", {})
        if date_range:
            start = date_range.get("start")
            end = date_range.get("end")
            if isinstance(start, str):
                start = datetime.fromisoformat(start)
            if isinstance(end, str):
                end = datetime.fromisoformat(end)
            date_range = {"start": start, "end": end}

        return cls(
            total_logs=data.get("total_logs", 0),
            action_counts=data.get("action_counts", {}),
            severity_counts=data.get("severity_counts", {}),
            user_counts=data.get("user_counts", {}),
            resource_counts=data.get("resource_counts", {}),
            date_range=date_range,
            top_actions=data.get("top_actions", []),
            high_risk_operations=data.get("high_risk_operations", []),
        )


class AuditFilter:
    """
    审计过滤器 / Audit Filter

    用于过滤审计日志的条件。
    Conditions for filtering audit logs.
    """

    def __init__(
        self,
        user_id: Optional[str] = None,
        action: Optional[str] = None,
        severity: Optional[str] = None,
        resource_type: Optional[str] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        ip_address: Optional[str] = None,
        session_id: Optional[str] = None,
    ):
        """
        初始化过滤器 / Initialize Filter

        Args:
            user_id: 用户ID / User ID
            action: 动作 / Action
            severity: 严重性 / Severity
            resource_type: 资源类型 / Resource type
            start_date: 开始日期 / Start date
            end_date: 结束日期 / End date
            ip_address: IP地址 / IP address
            session_id: 会话ID / Session ID
        """
        self.user_id = user_id
        self.action = action
        self.severity = severity
        self.resource_type = resource_type
        self.start_date = start_date
        self.end_date = end_date
        self.ip_address = ip_address
        self.session_id = session_id

    def to_dict(self) -> Dict[str, Any]:
        """
        转换为字典 / Convert to Dictionary

        Returns:
            Dict[str, Any]: 过滤器字典 / Filter dictionary
        """
        return {
            "user_id": self.user_id,
            "action": self.action,
            "severity": self.severity,
            "resource_type": self.resource_type,
            "start_date": self.start_date.isoformat() if self.start_date else None,
            "end_date": self.end_date.isoformat() if self.end_date else None,
            "ip_address": self.ip_address,
            "session_id": self.session_id,
        }

    def is_empty(self) -> bool:
        """
        检查是否为空过滤器 / Check if Empty Filter

        Returns:
            bool: 是否为空 / Whether empty
        """
        return all([
            self.user_id is None,
            self.action is None,
            self.severity is None,
            self.resource_type is None,
            self.start_date is None,
            self.end_date is None,
            self.ip_address is None,
            self.session_id is None,
        ])


class AuditConfig:
    """
    审计配置 / Audit Configuration

    审计服务的配置参数。
    Configuration parameters for audit service.
    """

    def __init__(
        self,
        enable_async_logging: bool = True,
        enable_batch_logging: bool = True,
        max_batch_size: int = 100,
        batch_timeout: float = 5.0,
        enable_sensitive_data_masking: bool = True,
        sensitive_tables: Optional[List[str]] = None,
        sensitive_columns: Optional[List[str]] = None,
        compliance_mapping: Optional[Dict[str, str]] = None,
        log_retention_days: int = 365,
        enable_compression: bool = True,
        enable_encryption: bool = False,
    ):
        """
        初始化配置 / Initialize Configuration

        Args:
            enable_async_logging: 启用异步日志 / Enable async logging
            enable_batch_logging: 启用批量日志 / Enable batch logging
            max_batch_size: 最大批量大小 / Max batch size
            batch_timeout: 批量超时 / Batch timeout
            enable_sensitive_data_masking: 启用敏感数据掩码 / Enable sensitive data masking
            sensitive_tables: 敏感表列表 / Sensitive tables list
            sensitive_columns: 敏感列列表 / Sensitive columns list
            compliance_mapping: 合规映射 / Compliance mapping
            log_retention_days: 日志保留天数 / Log retention days
            enable_compression: 启用压缩 / Enable compression
            enable_encryption: 启用加密 / Enable encryption
        """
        self.enable_async_logging = enable_async_logging
        self.enable_batch_logging = enable_batch_logging
        self.max_batch_size = max_batch_size
        self.batch_timeout = batch_timeout
        self.enable_sensitive_data_masking = enable_sensitive_data_masking
        self.sensitive_tables = sensitive_tables or []
        self.sensitive_columns = sensitive_columns or []
        self.compliance_mapping = compliance_mapping or {}
        self.log_retention_days = log_retention_days
        self.enable_compression = enable_compression
        self.enable_encryption = enable_encryption

    def to_dict(self) -> Dict[str, Any]:
        """
        转换为字典 / Convert to Dictionary

        Returns:
            Dict[str, Any]: 配置字典 / Configuration dictionary
        """
        return {
            "enable_async_logging": self.enable_async_logging,
            "enable_batch_logging": self.enable_batch_logging,
            "max_batch_size": self.max_batch_size,
            "batch_timeout": self.batch_timeout,
            "enable_sensitive_data_masking": self.enable_sensitive_data_masking,
            "sensitive_tables": self.sensitive_tables,
            "sensitive_columns": self.sensitive_columns,
            "compliance_mapping": self.compliance_mapping,
            "log_retention_days": self.log_retention_days,
            "enable_compression": self.enable_compression,
            "enable_encryption": self.enable_encryption,
        }