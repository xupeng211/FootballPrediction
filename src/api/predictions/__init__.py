"""
预测API模块
"""

# 导入预测API模块相关类
try:
    from .预测api模块 import (
        BatchPredictionRequest,
        BatchPredictionResponse,
        HistoryPrediction,
        MatchInfo,
        ModelStatsResponse,
        PredictionData,
        PredictionHistoryResponse,
        PredictionOverviewResponse,
        PredictionRequest,
        PredictionResponse,
        RecentPrediction,
        RecentPredictionsResponse,
        UpcomingMatchesRequest,
        UpcomingMatchesResponse,
        VerificationResponse,
    )
except ImportError:
    BatchPredictionRequest = None
    BatchPredictionResponse = None
    HistoryPrediction = None
    MatchInfo = None
    ModelStatsResponse = None
    PredictionData = None
    PredictionHistoryResponse = None
    PredictionOverviewResponse = None
    PredictionRequest = None
    PredictionResponse = None
    RecentPrediction = None
    RecentPredictionsResponse = None
    UpcomingMatchesRequest = None
    UpcomingMatchesResponse = None
    VerificationResponse = None

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
