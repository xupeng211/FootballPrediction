"""
预测API模块
"""

from .models import (BatchPredictionRequest, BatchPredictionResponse,
                     HistoryPrediction, MatchInfo, ModelStatsResponse,
                     PredictionData, PredictionHistoryResponse,
                     PredictionOverviewResponse, PredictionRequest,
                     PredictionResponse, RecentPrediction,
                     RecentPredictionsResponse, UpcomingMatchesRequest,
                     UpcomingMatchesResponse, VerificationResponse)
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
