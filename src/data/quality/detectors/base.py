"""
异常检测基础类
Anomaly Detection Base Classes

提供异常检测的基础类和结果类。
"""

from datetime import datetime
from typing import Any, Dict, List


class AnomalyDetectionResult:
    """异常检测结果类"""

    def __init__(
        self,
        table_name: str,
        detection_method: str,
        anomaly_type: str,
        severity: str = "medium",
    ):
        """
        初始化异常检测结果

        Args:
            table_name: 表名
            detection_method: 检测方法
            anomaly_type: 异常类型
            severity: 严重程度 (low, medium, high, critical)
        """
        self.table_name = table_name
        self.detection_method = detection_method
        self.anomaly_type = anomaly_type
        self.severity = severity
        self.timestamp = datetime.now()
        self.anomalous_records: List[Dict[str, Any]] = []
        self.statistics: Dict[str, Any] = {}
        self.metadata: Dict[str, Any] = {}

    def add_anomalous_record(self, record: Dict[str, Any]) -> None:
        """添加异常记录"""
        self.anomalous_records.append(record)

    def set_statistics(self, stats: Dict[str, Any]) -> None:
        """设置统计信息"""
        self.statistics = stats

    def set_metadata(self, metadata: Dict[str, Any]) -> None:
        """设置元数据"""
        self.metadata = metadata

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            "table_name": self.table_name,
            "detection_method": self.detection_method,
            "anomaly_type": self.anomaly_type,
            "severity": self.severity,
            "timestamp": self.timestamp.isoformat(),
            "anomalous_records_count": len(self.anomalous_records),
            "anomalous_records": self.anomalous_records,
            "statistics": self.statistics,
            "metadata": self.metadata,
        }