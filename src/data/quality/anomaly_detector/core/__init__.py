"""
异常检测核心模块

提供异常检测的核心数据结构和主检测器。
"""

from .result import AnomalyDetectionResult
from .anomaly_detector import AdvancedAnomalyDetector

__all__ = ["AnomalyDetectionResult", "AdvancedAnomalyDetector"]