from datetime import datetime
from enum import Enum

from sqlalchemy import Column, DateTime, Integer, String, Text, func
from sqlalchemy.orm import validates

from src.database.base import BaseModel

"""
数据质量日志数据库模型

记录数据质量检查中发现的问题和异常处理情况,
支持人工排查和质量改进追踪.

用途:
- 记录数据质量异常和错误
- 跟踪异常处理进度
- 支持数据治理决策
"""


class IssueType(Enum):
    """问题类型枚举."""

    MISSING_DATA = "missing_data"
    INVALID_FORMAT = "invalid_format"
    DUPLICATE_RECORD = "duplicate_record"
    INCONSISTENT_DATA = "inconsistent_data"
    OUT_OF_RANGE = "out_of_range"
    NULL_VALUE = "null_value"


class Severity(Enum):
    """严重程度枚举."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class QualityStatus(Enum):
    """质量状态枚举."""

    OPEN = "open"
    IN_PROGRESS = "in_progress"
    RESOLVED = "resolved"
    IGNORED = "ignored"


class DataQualityLog(BaseModel):
    __tablename__ = "data_quality_logs"
    __table_args__ = {"extend_existing": True}

    # 基础字段
    id = Column(Integer, primary_key=True, comment="主键ID")
    table_name = Column(String(100), nullable=False, comment="表名")
    record_id = Column(Integer, nullable=True, comment="记录ID")

    # 问题描述字段
    issue_type = Column(String(50), nullable=False, comment="问题类型")
    issue_description = Column(Text, nullable=False, comment="问题描述")
    severity = Column(String(20), nullable=False, comment="严重程度")

    # 状态字段
    status = Column(String(20), nullable=False, default="open", comment="处理状态")

    # 时间字段
    created_at = Column(DateTime, nullable=False, default=func.now(), comment="创建时间")
    resolved_at = Column(DateTime, nullable=True, comment="解决时间")

    # 附加信息
    additional_info = Column(Text, nullable=True, comment="附加信息")
    resolution_notes = Column(Text, nullable=True, comment="解决备注")

    @validates("issue_type")
    def validate_issue_type(self, key: str, issue_type: str) -> str:
        """验证问题类型."""
        valid_types = [it.value for it in IssueType]
        if issue_type not in valid_types:
            raise ValueError(
                f"Invalid issue typing.Type: {issue_type}. Must be one of: {valid_types}"
            )
        return issue_type

    @validates("severity")
    def validate_severity(self, key: str, severity: str) -> str:
        """验证严重程度."""
        valid_severities = [s.value for s in Severity]
        if severity not in valid_severities:
            raise ValueError(
                f"Invalid severity: {severity}. Must be one of: {valid_severities}"
            )
        return severity

    @validates("status")
    def validate_status(self, key: str, status: str) -> str:
        """验证处理状态."""
        valid_statuses = [s.value for s in QualityStatus]
        if status not in valid_statuses:
            raise ValueError(
                f"Invalid status: {status}. Must be one of: {valid_statuses}"
            )
        return status

    def mark_resolved(self, resolution_notes: str = None) -> None:
        """标记为已解决."""
        self.status = QualityStatus.RESOLVED.value
        self.resolved_at = datetime.now()
        if resolution_notes:
            self.resolution_notes = resolution_notes

    def __repr__(self) -> str:
        """字符串表示."""
        return (
            f"<DataQualityLog("
            f"id={self.id}, "
            f"table={self.table_name}, "
            f"typing.Type={self.issue_type}, "
            f"severity={self.severity}, "
            f"status={self.status}"
            f")>"
        )
