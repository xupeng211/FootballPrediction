"""
Schemas Package - Pydantic模型定义

包含所有API请求和响应的Pydantic模型定义。
"""

from .prediction import (
    PredictionRequest,
    PredictionResponse,
    ErrorResponse,
    HealthResponse
)

__all__ = [
    "PredictionRequest",
    "PredictionResponse",
    "ErrorResponse",
    "HealthResponse"
]