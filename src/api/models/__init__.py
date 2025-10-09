"""
模型API模块
Models API Module

提供模型管理相关的API接口。
"""

from .endpoints import router
from .mlflow_client import mlflow_client
from .model_info import get_model_info
from src.models.prediction_service import PredictionService

# 创建预测服务实例
prediction_service = PredictionService()

__all__ = [
    "router",
    "mlflow_client",
    "prediction_service",
    "get_model_info",
]