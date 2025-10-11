"""
预测API模块
"""

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
    RecentPredictionsResponse,
    VerificationResponse,
    MatchInfo,
    PredictionData,
    HistoryPrediction,
    RecentPrediction,
)
from .router import router

__all__ = [
    "PredictionRequest",
    "PredictionResponse",
    "BatchPredictionRequest",
    "BatchPredictionResponse",
    "UpcomingMatchesRequest",
    "UpcomingMatchesResponse",
    "ModelStatsResponse",
    "PredictionHistoryResponse",
    "PredictionOverviewResponse",
    "RecentPredictionsResponse",
    "VerificationResponse",
    "MatchInfo",
    "PredictionData",
    "HistoryPrediction",
    "RecentPrediction",
    "router",
]
