"""
异常检测模块
Anomaly Detection Module

提供基于统计学和机器学习的数据异常检测功能。
"""

from .base import AnomalyDetectionResult
from .statistical import StatisticalAnomalyDetector
from .machine_learning import MachineLearningAnomalyDetector
from .advanced import AdvancedAnomalyDetector
from .metrics import (
    anomalies_detected_total,
    data_drift_score,
    anomaly_detection_duration_seconds,
    anomaly_detection_coverage,
)

__all__ = [
    # 基础类
    "AnomalyDetectionResult",

    # 检测器
    "StatisticalAnomalyDetector",
    "MachineLearningAnomalyDetector",
    "AdvancedAnomalyDetector",

    # 监控指标
    "anomalies_detected_total",
    "data_drift_score",
    "anomaly_detection_duration_seconds",
    "anomaly_detection_coverage",
]