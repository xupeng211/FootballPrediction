"""
数据质量日志数据库模型

记录数据质量检查中发现的问题和异常处理情况，
支持人工排查和质量改进追踪。

用途：
- 记录数据质量异常和错误
- 跟踪异常处理进度
- 支持数据治理决策
"""





class DataQualityLog(BaseModel):
    """
    数据质量日志模型

    记录数据质量检查过程中发现的各类问题，
    包括数据异常、处理结果和人工干预需求。
    """

    __tablename__ = "data_quality_logs"

    # 基础信息
    id = Column(Integer, primary_key=True, index=True, comment="日志记录唯一标识")
    table_name = Column(
        String(100), nullable=False, index=True, comment="出现问题的表名"
    )
    record_id = Column(Integer, nullable=True, index=True, comment="出现问题的记录ID")

    # 问题分类
    error_type = Column(String(100), nullable=False, index=True, comment="错误类型")
    severity = Column(
        String(20), default="medium", comment="严重程度: low/medium/high/critical"
    )

    # 错误详情
    error_data = Column(JSON, nullable=True, comment="错误数据和上下文信息")
    error_message = Column(Text, nullable=True, comment="详细错误描述")

    # 处理状态
    status = Column(
        String(20),
        default="logged",
        index=True,
        comment="处理状态: logged/in_progress/resolved/ignored",
    )
    requires_manual_review = Column(
        Boolean, default=False, index=True, comment="是否需要人工审核"
    )

    # 处理信息
    handled_by = Column(String(100), nullable=True, comment="处理人员")
    handled_at = Column(DateTime, nullable=True, comment="处理时间")
    resolution_notes = Column(Text, nullable=True, comment="解决方案说明")

    # 时间戳
    detected_at = Column(
        DateTime, default=func.now(), nullable=False, index=True, comment="发现时间"
    )

    def __init__(self, **kwargs):
        """初始化数据质量日志"""
        # 设置默认值
        if "status" not in kwargs:
            kwargs["status"] = "logged"
        if "requires_manual_review" not in kwargs:
            kwargs["requires_manual_review"] = False
        if "severity" not in kwargs:
            kwargs["severity"] = "medium"
        super().__init__(**kwargs)

    def __repr__(self) -> str:
        """字符串表示"""
        return (
            f"<DataQualityLog(id={self.id}, table={self.table_name}, "
            f"type={self.error_type}, status={self.status})>"
        )

    def to_dict(self, exclude_fields: Optional[set] = None) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            "id": self.id,
            "table_name": self.table_name,
            "record_id": self.record_id,
            "error_type": self.error_type,
            "severity": self.severity,
            "error_data": self.error_data,
            "error_message": self.error_message,
            "status": self.status,
            "requires_manual_review": self.requires_manual_review,
            "handled_by": self.handled_by,
            "handled_at": self.handled_at.isoformat() if self.handled_at else None,
            "resolution_notes": self.resolution_notes,
            "detected_at": self.detected_at.isoformat() if self.detected_at else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }

    def mark_as_resolved(self, handler: str, notes: str) -> None:
        """标记为已解决"""
        self.status = "resolved"  # type: ignore[assignment]
        self.handled_by = handler  # type: ignore[assignment]
        self.handled_at = datetime.now()  # type: ignore[assignment]
        self.resolution_notes = notes  # type: ignore[assignment]

    def mark_as_ignored(self, handler: str, reason: str) -> None:
        """标记为忽略"""
        self.status = "ignored"  # type: ignore[assignment]
        self.handled_by = handler  # type: ignore[assignment]
        self.handled_at = datetime.now()  # type: ignore[assignment]
        self.resolution_notes = f"忽略原因: {reason}"  # type: ignore[assignment]

    def assign_to_handler(self, handler: str) -> None:
        """分配给处理人员"""
        self.status = "in_progress"  # type: ignore[assignment]
        self.handled_by = handler  # type: ignore[assignment]

    @classmethod
    def get_severity_level(cls, error_type: str) -> str:
        """根据错误类型获取严重程度"""
        severity_mapping = {
            "missing_values_filled": "low",
            "suspicious_odds": "medium",
            "invalid_scores": "high",
            "data_consistency": "medium",
            "exception_handling": "high",
            "ge_validation_failed": "medium",
            "data_corruption": "critical",
        }

        return severity_mapping.get(str(error_type), "medium")

    @classmethod
    def create_from_ge_result(
        cls, table_name: str, validation_result: Dict[str, Any]
    ) -> "DataQualityLog":
        """从GE验证结果创建日志记录"""
        return cls(
            table_name=table_name,
            record_id=None,
            error_type="ge_validation_failed",
            severity="medium", Dict, Optional, cast



            error_data={
                "validation_result": validation_result,
                "failed_expectations": validation_result.get(
                    str("failed_expectations"), []
                ),
                "success_rate": validation_result.get(str("success_rate"), 0),
            },
            error_message=f"GE数据质量验证失败，成功率: {validation_result.get(str('success_rate'), 0)}%",
            status="logged",
            requires_manual_review=validation_result.get(str("success_rate"), 0) < 80,
            detected_at=datetime.now(),
        )