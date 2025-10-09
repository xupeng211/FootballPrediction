"""




"""









from .core.anomaly_detector import AdvancedAnomalyDetector
from .core.result import AnomalyDetectionResult
from .machine_learning.ml_detector import MachineLearningAnomalyDetector
from .metrics.prometheus_metrics import (
from .statistical.statistical_detector import StatisticalAnomalyDetector

异常检测模块
提供基于统计学和机器学习的数据异常检测功能。
支持的检测方法：
1. 统计学方法：
   - 3σ规则检测
   - 分布偏移检测（Kolmogorov-Smirnov检验）
   - 四分位距(IQR)异常值检测
2. 机器学习方法：
   - Isolation Forest 异常检测
   - 数据漂移检测（Data Drift）
   - 聚类异常检测
集成 Prometheus 监控指标，支持实时异常告警。
# 导入核心结果类
# 导入高级异常检测器（主要接口）
# 导入具体检测器（供高级检测器内部使用）
# 导入Prometheus指标（供监控系统使用）
    anomaly_detection_coverage,
    anomaly_detection_duration_seconds,
    anomalies_detected_total,
    data_drift_score,
)
__all__ = [
    # 核心类
    "AnomalyDetectionResult",
    "AdvancedAnomalyDetector",
    # 检测器（可选导出，供高级用户使用）
    "StatisticalAnomalyDetector",
    "MachineLearningAnomalyDetector",
    # 监控指标（供监控系统使用）
    "anomalies_detected_total",
    "data_drift_score",
    "anomaly_detection_duration_seconds",
    "anomaly_detection_coverage",
]
# 版本信息
__version__ = "2.0.0"
__description__ = "重构后的异常检测模块，提供模块化、可扩展的异常检测功能"