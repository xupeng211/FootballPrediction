import os
"""
数据采集日志模型

记录数据采集任务的执行日志，包括采集状态、成功失败统计等信息。
对应数据库表：data_collection_logs

基于 DATA_DESIGN.md 第1.3节设计。
"""

from datetime import datetime
from enum import Enum
from typing import Any, Dict, Optional

from sqlalchemy import Column, DateTime, Integer, String, Text, func
from sqlalchemy.orm import validates

from src.database.base import BaseModel


class CollectionStatus(Enum):
    """采集状态枚举"""

    SUCCESS = os.getenv("DATA_COLLECTION_LOG_SUCCESS_23")
    FAILED = os.getenv("DATA_COLLECTION_LOG_FAILED_23")
    PARTIAL = os.getenv("DATA_COLLECTION_LOG_PARTIAL_23")
    RUNNING = os.getenv("DATA_COLLECTION_LOG_RUNNING_24")


class CollectionType(Enum):
    """采集类型枚举"""

    FIXTURES = os.getenv("DATA_COLLECTION_LOG_FIXTURES_25")
    ODDS = "odds"
    SCORES = os.getenv("DATA_COLLECTION_LOG_SCORES_26")
    LIVE_SCORES = os.getenv("DATA_COLLECTION_LOG_LIVE_SCORES_26")


class DataCollectionLog(BaseModel):
    """
    数据采集日志模型

    记录每次数据采集任务的详细执行信息，
    用于监控采集状态、调试错误、统计性能等。
    """

    __tablename__ = os.getenv("DATA_COLLECTION_LOG___TABLENAME___34")

    # 基础字段
    id = Column(Integer, primary_key=True, comment="主键ID")
    data_source = Column(String(100), nullable=False, comment="数据源标识")
    collection_type = Column(String(50), nullable=False, comment="采集类型")

    # 时间字段
    start_time = Column(DateTime, nullable=False, comment="开始时间")
    end_time = Column(DateTime, nullable=True, comment="结束时间")

    # 统计字段
    records_collected = Column(Integer, nullable=False, default=0, comment="采集记录数")
    success_count = Column(Integer, nullable=False, default=0, comment="成功数量")
    error_count = Column(Integer, nullable=False, default=0, comment="错误数量")

    # 状态字段
    status = Column(String(20), nullable=False, comment="采集状态")
    error_message = Column(Text, nullable=True, comment="错误信息")

    # 元数据字段
    created_at = Column(
        DateTime, nullable=False, default=func.now(), comment="创建时间"
    )

    @validates("collection_type")
    def validate_collection_type(self, key: str, collection_type: str) -> str:
        """验证采集类型"""
        valid_types = [ct.value for ct in CollectionType]
        if collection_type not in valid_types:
            raise ValueError(
                f"Invalid collection type: {collection_type}. Must be one of: {valid_types}"
            )
        return collection_type

    @validates("status")
    def validate_status(self, key: str, status: str) -> str:
        """验证采集状态"""
        valid_statuses = [cs.value for cs in CollectionStatus]
        if status not in valid_statuses:
            raise ValueError(
                f"Invalid status: {status}. Must be one of: {valid_statuses}"
            )
        return status

    @property
    def duration_seconds(self) -> Optional[float]:
        """计算采集耗时（秒）"""
        if self.start_time and self.end_time:
            return (self.end_time - self.start_time).total_seconds()
        return None

    @property
    def success_rate(self) -> float:
        """计算成功率"""
        total = self.success_count + self.error_count
        if total == 0:
            return 0.0
        return self.success_count / total

    @property
    def is_completed(self) -> bool:
        """是否已完成（成功或失败）"""
        return self.status in [
            CollectionStatus.SUCCESS.value,
            CollectionStatus.FAILED.value,
            CollectionStatus.PARTIAL.value,
        ]

    @property
    def is_successful(self) -> bool:
        """是否成功完成"""
        return self.status == CollectionStatus.SUCCESS.value

    def mark_started(self) -> None:
        """标记采集开始"""
        self.start_time = datetime.now()
        self.status = CollectionStatus.RUNNING.value

    def mark_completed(
        self,
        status: CollectionStatus,
        records_collected: int = 0,
        success_count: int = 0,
        error_count: int = 0,
        error_message: Optional[str] = None,
    ) -> None:
        """
        标记采集完成

        Args:
            status: 最终状态
            records_collected: 采集的记录数
            success_count: 成功处理数量
            error_count: 错误数量
            error_message: 错误信息
        """
        self.end_time = datetime.now()
        self.status = status.value
        self.records_collected = records_collected
        self.success_count = success_count
        self.error_count = error_count
        if error_message:
            self.error_message = error_message

    def __repr__(self) -> str:
        """字符串表示"""
        return (
            f"<DataCollectionLog("
            f"id={self.id}, "
            f"source={self.data_source}, "
            f"type={self.collection_type}, "
            f"status={self.status}, "
            f"records={self.records_collected}"
            f")>"
        )

    def to_dict(self, exclude_fields: Optional[set] = None) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            "id": self.id,
            "data_source": self.data_source,
            "collection_type": self.collection_type,
            "start_time": self.start_time.isoformat() if self.start_time else None,
            "end_time": self.end_time.isoformat() if self.end_time else None,
            "records_collected": self.records_collected,
            "success_count": self.success_count,
            "error_count": self.error_count,
            "status": self.status,
            "error_message": self.error_message,
            "duration_seconds": self.duration_seconds,
            "success_rate": self.success_rate,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
