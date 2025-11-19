from typing import Optional

"""anomaly_detector 主模块.

此文件由长文件拆分工具自动生成

拆分策略: domain_split
"""

# 导入拆分的模块
try:
    from .anomaly_detector_core import (
        AnomalyDetector,
        AnomalyResult,
        AnomalySeverity,
        AnomalyType,
    )
except ImportError:
    AnomalyDetector = None
    AnomalyResult = None
    AnomalySeverity = None
    AnomalyType = None

# 导出所有公共接口
__all__ = [
    "AnomalyDetector",
    "AnomalyResult",
    "AnomalySeverity",
    "AnomalyType",
]
