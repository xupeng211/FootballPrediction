"""
预测服务模块
Prediction Service Module

提供模型预测相关的功能，包括模型加载、预测执行、结果存储等。
"""

from .cache import PredictionCache
from .metrics import (
from .models import PredictionResult
from .service import PredictionService

    predictions_total,
    prediction_duration_seconds,
    prediction_accuracy,
    model_load_duration_seconds,
    cache_hit_ratio,
)

__all__ = [
    # 数据模型
    "PredictionResult",

    # 核心服务
    "PredictionService",

    # 缓存
    "PredictionCache",

    # 监控指标
    "predictions_total",
    "prediction_duration_seconds",
    "prediction_accuracy",
    "model_load_duration_seconds",
    "cache_hit_ratio",
]