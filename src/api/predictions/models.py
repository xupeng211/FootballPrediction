"""
预测API数据模型
Prediction API Data Models

定义所有预测相关的请求和响应模型。
"""

from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class PredictionRequest(BaseModel):
    """预测请求模型"""

    match_id: int = Field(..., description="比赛ID", gt=0)
    force_refresh: bool = Field(False, description="是否强制刷新缓存")
    include_features: bool = Field(False, description="是否包含特征信息")


class BatchPredictionRequest(BaseModel):
    """批量预测请求模型"""

    match_ids: List[int] = Field(
        ..., description="比赛ID列表", min_items=1, max_items=100
    )
    force_refresh: bool = Field(False, description="是否强制刷新缓存")
    include_features: bool = Field(False, description="是否包含特征信息")


class UpcomingMatchesRequest(BaseModel):
    """即将开始比赛预测请求模型"""

    hours_ahead: int = Field(24, description="预测未来多少小时内的比赛", ge=1, le=168)
    league_ids: Optional[List[int]] = Field(None, description="指定联赛ID列表")
    force_refresh: bool = Field(False, description="是否强制刷新缓存")


class PredictionResponse(BaseModel):
    """预测响应模型"""

    match_id: int
    prediction: str
    probabilities: Dict[str, float]
    confidence: float
    model_version: str
    model_name: str
    prediction_time: str
    match_info: Optional[Dict[str, Any]] = None
    features: Optional[Dict[str, Any]] = None
    odds: Optional[Dict[str, Any]] = None


class BatchPredictionResponse(BaseModel):
    """批量预测响应模型"""

    total: int
    successful: int
    failed: int
    results: List[Dict[str, Any]]


class ModelStatsResponse(BaseModel):
    """模型统计响应模型"""

    model_name: str
    period_days: int
    total_predictions: int
    verified_predictions: int
    accuracy: Optional[float]
    avg_confidence: float
    predictions_by_result: Dict[str, int]
    last_updated: str


class PredictionHistoryResponse(BaseModel):
    """预测历史响应模型"""

    match_id: int
    total_records: int
    history: List[Dict[str, Any]]


class PredictionOverviewResponse(BaseModel):
    """预测概览响应模型"""

    period_days: int
    engine_performance: Dict[str, Any]
    overall_stats: Dict[str, Any]
    models: List[Dict[str, Any]]
    last_updated: str


class UpcomingMatchesResponse(BaseModel):
    """即将开始比赛响应模型"""

    total: int
    hours_ahead: int
    league_ids: Optional[List[int]]
    results: List[Dict[str, Any]]


class VerificationResponse(BaseModel):
    """验证响应模型"""

    match_id: int
    verified: bool
    correct: int
    accuracy: float
    message: str


class CacheClearResponse(BaseModel):
    """缓存清理响应模型"""

    pattern: str
    cleared_items: int
    message: str


class HealthCheckResponse(BaseModel):
    """健康检查响应模型"""

    status: str
    error: Optional[str] = None
    timestamp: str