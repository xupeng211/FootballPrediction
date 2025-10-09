"""
异常检测模型
Anomaly Detection Models

定义异常检测相关的数据模型。
"""



class AnomalyType(Enum):
    """异常类型枚举"""
    OUTLIER = "outlier"  # 离群值
    TREND_CHANGE = "trend_change"  # 趋势变化
    PATTERN_BREAK = "pattern_break"  # 模式中断
    VALUE_RANGE = "value_range"  # 数值范围异常
    FREQUENCY = "frequency"  # 频率异常
    NULL_SPIKE = "null_spike"  # 空值激增


class AnomalySeverity(Enum):
    """异常严重程度"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class AnomalyResult:
    """异常检测结果"""

    def __init__(
        self,
        table_name: str,
        column_name: str,
        anomaly_type: AnomalyType,
        severity: AnomalySeverity,
        anomalous_values: List[Any],
        anomaly_score: float,
        detection_method: str,
        description: str,
        detected_at: datetime | None = None,
    ):
        """
        初始化异常检测结果

        Args:
            table_name: 表名
            column_name: 列名
            anomaly_type: 异常类型
            severity: 严重程度
            anomalous_values: 异常值列表
            anomaly_score: 异常得分
            detection_method: 检测方法
            description: 异常描述
            detected_at: 检测时间
        """
        self.table_name = table_name
        self.column_name = column_name
        self.anomaly_type = anomaly_type
        self.severity = severity
        self.anomalous_values = anomalous_values
        self.anomaly_score = anomaly_score
        self.detection_method = detection_method
        self.description = description
        self.detected_at = detected_at or datetime.now()

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            "table_name": self.table_name,
            "column_name": self.column_name,
            "anomaly_type": self.anomaly_type.value,
            "severity": self.severity.value,
            "anomalous_values": self.anomalous_values,
            "anomaly_score": round(self.anomaly_score, 4),
            "detection_method": self.detection_method,
            "description": self.description,
            "detected_at": self.detected_at.isoformat(),
        }

    def __repr__(self) -> str:
        """字符串表示"""
        return (
            f"AnomalyResult({self.table_name}.{self.column_name}, "
            "detected_at": self.detected_at.isoformat(),)

            f"severity={self.severity.value}, "
            f"score={self.anomaly_score:.3f})"
        )