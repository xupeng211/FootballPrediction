"""
告警事件实体类
Incident Entity

定义告警事件的数据结构和管理功能。
Defines the data structure and management functionality for alert incidents.
"""

from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

from .enums import IncidentSeverity, IncidentStatus


class Incident:
    """
    告警事件类
    Incident Class

    管理相关告警的集合，形成一个事件。
    Manages a collection of related alerts as an incident.

    Attributes:
        incident_id (str): 事件唯一标识 / Incident unique identifier
        title (str): 事件标题 / Incident title
        description (str): 事件描述 / Incident description
        severity (IncidentSeverity): 事件严重程度 / Incident severity
        status (IncidentStatus): 事件状态 / Incident status
        alert_ids (List[str]): 关联的告警ID列表 / Related alert IDs
        assigned_to (Optional[str]): 分配给谁 / Assigned to
        created_at (datetime): 创建时间 / Creation time
        updated_at (datetime): 更新时间 / Update time
        resolved_at (Optional[datetime]): 解决时间 / Resolution time
        labels (Dict[str, str]): 标签 / Labels
        annotations (Dict[str, str]): 注释 / Annotations
        metadata (Dict[str, Any]): 元数据 / Metadata
    """

    def __init__(
        self,
        incident_id: str,
        title: str,
        severity: IncidentSeverity,
        alert_ids: Optional[List[str]] = None,
        description: Optional[str] = None,
        assigned_to: Optional[str] = None,
        created_at: Optional[datetime] = None,
        labels: Optional[Dict[str, str]] = None,
        annotations: Optional[Dict[str, str]] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ):
        """
        初始化告警事件
        Initialize Incident

        Args:
            incident_id: 事件ID / Incident ID
            title: 事件标题 / Incident title
            severity: 事件严重程度 / Incident severity
            alert_ids: 关联的告警ID列表 / Related alert IDs
            description: 事件描述 / Incident description
            assigned_to: 分配给谁 / Assigned to
            created_at: 创建时间 / Creation time
            labels: 标签 / Labels
            annotations: 注释 / Annotations
            metadata: 元数据 / Metadata
        """
        self.incident_id = incident_id
        self.title = title
        self.description = description or title
        self.severity = severity
        self.status = IncidentStatus.OPEN
        self.alert_ids = alert_ids or []
        self.assigned_to = assigned_to
        self.created_at = created_at or datetime.utcnow()
        self.updated_at = self.created_at
        self.resolved_at: Optional[datetime] = None
        self.labels = labels or {}
        self.annotations = annotations or {}
        self.metadata = metadata or {}

    def add_alert(self, alert_id: str) -> None:
        """
        添加告警到事件
        Add Alert to Incident

        Args:
            alert_id: 告警ID / Alert ID
        """
        if alert_id not in self.alert_ids:
            self.alert_ids.append(alert_id)
            self.updated_at = datetime.utcnow()

    def remove_alert(self, alert_id: str) -> None:
        """
        从事件中移除告警
        Remove Alert from Incident

        Args:
            alert_id: 告警ID / Alert ID
        """
        if alert_id in self.alert_ids:
            self.alert_ids.remove(alert_id)
            self.updated_at = datetime.utcnow()

    def assign_to(self, user: str) -> None:
        """
        分配事件给用户
        Assign Incident to User

        Args:
            user: 用户名 / Username
        """
        self.assigned_to = user
        self.updated_at = datetime.utcnow()

    def start_investigation(self) -> None:
        """
        开始调查事件
        Start Investigation
        """
        if self.status == IncidentStatus.OPEN:
            self.status = IncidentStatus.INVESTIGATING
            self.updated_at = datetime.utcnow()

    def resolve(self) -> None:
        """
        解决事件
        Resolve Incident
        """
        self.status = IncidentStatus.RESOLVED
        self.resolved_at = datetime.utcnow()
        self.updated_at = datetime.utcnow()

    def close(self) -> None:
        """
        关闭事件
        Close Incident
        """
        if self.status == IncidentStatus.RESOLVED:
            self.status = IncidentStatus.CLOSED
            self.updated_at = datetime.utcnow()

    def reopen(self) -> None:
        """
        重新打开事件
        Reopen Incident
        """
        self.status = IncidentStatus.OPEN
        self.resolved_at = None
        self.updated_at = datetime.utcnow()

    def get_duration(self) -> Optional[timedelta]:
        """
        获取事件持续时间
        Get Incident Duration

        Returns:
            Optional[timedelta]: 事件持续时间 / Incident duration
        """
        end_time = self.resolved_at or datetime.utcnow()
        return end_time - self.created_at

    def get_age(self) -> timedelta:
        """
        获取事件年龄
        Get Incident Age

        Returns:
            timedelta: 事件存在时间 / Time since incident creation
        """
        return datetime.utcnow() - self.created_at

    def is_active(self) -> bool:
        """
        检查事件是否活跃
        Check if Incident is Active

        Returns:
            bool: 是否活跃 / Whether active
        """
        return self.status in [IncidentStatus.OPEN, IncidentStatus.INVESTIGATING]

    def is_resolved(self) -> bool:
        """
        检查事件是否已解决
        Check if Incident is Resolved

        Returns:
            bool: 是否已解决 / Whether resolved
        """
        return self.status in [IncidentStatus.RESOLVED, IncidentStatus.CLOSED]

    def update_severity(self, severity: IncidentSeverity) -> None:
        """
        更新事件严重程度
        Update Incident Severity

        Args:
            severity: 新的严重程度 / New severity
        """
        self.severity = severity
        self.updated_at = datetime.utcnow()

    def add_label(self, key: str, value: str) -> None:
        """
        添加标签
        Add Label

        Args:
            key: 标签键 / Label key
            value: 标签值 / Label value
        """
        self.labels[key] = value
        self.updated_at = datetime.utcnow()

    def add_annotation(self, key: str, value: str) -> None:
        """
        添加注释
        Add Annotation

        Args:
            key: 注释键 / Annotation key
            value: 注释值 / Annotation value
        """
        self.annotations[key] = value
        self.updated_at = datetime.utcnow()

    def set_metadata(self, key: str, value: Any) -> None:
        """
        设置元数据
        Set Metadata

        Args:
            key: 元数据键 / Metadata key
            value: 元数据值 / Metadata value
        """
        self.metadata[key] = value
        self.updated_at = datetime.utcnow()

    def to_dict(self) -> Dict[str, Any]:
        """
        转换为字典格式
        Convert to Dictionary Format

        Returns:
            Dict[str, Any]: 字典表示 / Dictionary representation
        """
        return {
            "incident_id": self.incident_id,
            "title": self.title,
            "description": self.description,
            "severity": self.severity.value,
            "status": self.status.value,
            "alert_ids": self.alert_ids,
            "assigned_to": self.assigned_to,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "resolved_at": self.resolved_at.isoformat() if self.resolved_at else None,
            "labels": self.labels,
            "annotations": self.annotations,
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Incident":
        """
        从字典创建事件对象
        Create Incident Object from Dictionary

        Args:
            data: 字典数据 / Dictionary data

        Returns:
            Incident: 事件对象 / Incident object
        """
        # 处理时间字段
        created_at = None
        if data.get("created_at"):
            if isinstance(data["created_at"], str):
                created_at = datetime.fromisoformat(data["created_at"])
            else:
                created_at = data["created_at"]

        updated_at = None
        if data.get("updated_at"):
            if isinstance(data["updated_at"], str):
                updated_at = datetime.fromisoformat(data["updated_at"])
            else:
                updated_at = data["updated_at"]

        resolved_at = None
        if data.get("resolved_at"):
            if isinstance(data["resolved_at"], str):
                resolved_at = datetime.fromisoformat(data["resolved_at"])
            else:
                resolved_at = data["resolved_at"]

        # 创建事件对象
        incident = cls(
            incident_id=data["incident_id"],
            title=data["title"],
            severity=IncidentSeverity(data["severity"]),
            alert_ids=data.get("alert_ids", []),
            description=data.get("description"),
            assigned_to=data.get("assigned_to"),
            created_at=created_at,
            labels=data.get("labels", {}),
            annotations=data.get("annotations", {}),
            metadata=data.get("metadata", {}),
        )

        # 设置状态和时间
        if data.get("status"):
            incident.status = IncidentStatus(data["status"])
        incident.updated_at = updated_at or incident.created_at
        incident.resolved_at = resolved_at

        return incident

    def __str__(self) -> str:
        """
        字符串表示
        String Representation

        Returns:
            str: 字符串 / String
        """
        return f"Incident({self.title}: {self.severity.value.upper()})"

    def __repr__(self) -> str:
        """
        对象表示
        Object Representation

        Returns:
            str: 对象字符串 / Object string
        """
        return (
            f"Incident(id={self.incident_id}, severity={self.severity.value}, "
            f"status={self.status.value}, alerts={len(self.alert_ids)})"
        )