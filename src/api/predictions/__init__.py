"""
预测API模块
Prediction API Module

提供完整的预测相关API接口。
"""

from fastapi import APIRouter

from .endpoints import routers
from .models import (
    PredictionRequest,
    PredictionResponse,
    BatchPredictionRequest,
    BatchPredictionResponse,
    UpcomingMatchesRequest,
    UpcomingMatchesResponse,
    ModelStatsResponse,
    PredictionHistoryResponse,
    PredictionOverviewResponse,
    VerificationResponse,
    CacheClearResponse,
    HealthCheckResponse,
)

# 创建主路由器
router = APIRouter(prefix="/api/v1/predictions", tags=["predictions"])

# 包含所有子路由器
for sub_router in routers:
    router.include_router(sub_router)

# 导出所有模型和路由器
__all__ = [
    "router",
    "PredictionRequest",
    "PredictionResponse",
    "BatchPredictionRequest",
    "BatchPredictionResponse",
    "UpcomingMatchesRequest",
    "UpcomingMatchesResponse",
    "ModelStatsResponse",
    "PredictionHistoryResponse",
    "PredictionOverviewResponse",
    "VerificationResponse",
    "CacheClearResponse",
    "HealthCheckResponse",
]