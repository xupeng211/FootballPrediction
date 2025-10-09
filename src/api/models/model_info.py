"""
模型信息
Model Information

提供模型基本信息和路由配置。
"""

from fastapi import APIRouter
from mlflow import MlflowClient

from src.models.prediction_service import PredictionService

# 创建路由器
router = APIRouter(prefix="/models", tags=["models"])

# 预测服务实例
prediction_service = PredictionService()


def get_model_info() -> dict:
    """
    获取模型基本信息

    Returns:
        包含模型基本信息的字典
    """
    return {
        "api": router,
        "prefix": "/models",
        "tags": ["models"],
        "prediction_service": prediction_service,
    }