"""
高级数据质量异常检测模块
Advanced Data Quality Anomaly Detection Module

实现基于统计学和机器学习的数据异常检测功能，用于足球预测系统的数据质量监控。

⚠️ 注意：此文件已重构为模块化结构。
为了向后兼容性，这里保留了原始的导入接口。
建议使用：from src.data.quality.detectors import <class_name>

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

基于 DATA_DESIGN.md 中的数据治理与质量控制架构设计。
"""

from .detectors import (

# 为了向后兼容性，从新的模块化结构中导入所有内容
    # 基础类
    AnomalyDetectionResult,

    # 检测器
    StatisticalAnomalyDetector,
    MachineLearningAnomalyDetector,
    AdvancedAnomalyDetector,

    # 监控指标
    anomalies_detected_total,
    data_drift_score,
    anomaly_detection_duration_seconds,
    anomaly_detection_coverage,
)

# 重新导出以保持原始接口
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

# 原始实现已移至 src/data/quality/detectors/ 模块
# 此处保留仅用于向后兼容性
# 请使用新的模块化结构以获得更好的维护性

# 包含的所有功能：
# - AnomalyDetectionResult: 异常检测结果类
# - StatisticalAnomalyDetector: 统计学异常检测器
#   - detect_outliers_3sigma: 3σ规则检测
#   - detect_distribution_shift: 分布偏移检测
#   - detect_outliers_iqr: IQR异常值检测
# - MachineLearningAnomalyDetector: 机器学习异常检测器
#   - detect_anomalies_isolation_forest: Isolation Forest检测
#   - detect_data_drift: 数据漂移检测
#   - detect_anomalies_clustering: DBSCAN聚类检测
# - AdvancedAnomalyDetector: 高级异常检测器
#   - run_comprehensive_detection: 综合异常检测
#   - get_anomaly_summary: 获取异常检测摘要
