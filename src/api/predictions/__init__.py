"""
预测API模块
"""

# 预测API模块相关类 - 模块暂未实现
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
