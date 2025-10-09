"""
预测服务核心模块

包含预测结果数据类和配置
"""

from .config import PredictionConfig, MLFLOW_RETRY_CONFIG
from .result import PredictionResult

__all__ = [
    "PredictionResult",
    "PredictionConfig",
    "MLFLOW_RETRY_CONFIG",
]