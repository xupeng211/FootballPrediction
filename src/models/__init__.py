from typing import cast, Any, Optional, Union

"""
足球预测模型模块

提供模型训练、预测、评估等核心功能：
- BaselineModelTrainer: 基准模型训练器
- PredictionService: 预测服务
- ModelMetricsExporter: 模型指标导出器
- 通用数据模型: Content, AnalysisResult, User等
"""

from .common_models import (
    AnalysisResult,
    Content,
    ContentType,
    User,
    UserProfile,
    UserRole,
)
from .metrics_exporter import ModelMetricsExporter
from .model_training import BaselineModelTrainer
from .prediction_service import PredictionResult, PredictionService

__all__ = [
    "BaselineModelTrainer",
    "PredictionService",
    "PredictionResult",
    "ModelMetricsExporter",
    "Content",
    "AnalysisResult",
    "User",
    "UserProfile",
    "ContentType",
    "UserRole",
]
