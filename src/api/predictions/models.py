"""
预测API模型定义
"""

from typing import List, Optional

from pydantic import BaseModel, Field


class MatchInfo(BaseModel):
    """比赛信息模式"""

    match_id: int
    home_team_id: int
    away_team_id: int
    league_id: int
    match_time: str
    match_status: str
    season: Optional[str] = None


class PredictionData(BaseModel):
    """预测数据模式"""

    id: Optional[int] = None
    model_version: str
    model_name: str
    home_win_probability: float = Field(ge=0.0, le=1.0)
    draw_probability: float = Field(ge=0.0, le=1.0)
    away_win_probability: float = Field(ge=0.0, le=1.0)
    predicted_result: str
    confidence_score: float = Field(ge=0.0, le=1.0)
    created_at: Optional[str] = None
    is_correct: Optional[bool] = None
    actual_result: Optional[str] = None


class PredictionRequest(BaseModel):
    """预测请求模式"""

    match_id: int
    model_version: Optional[str] = None
    model_name: Optional[str] = None
    include_confidence: bool = True


class PredictionResponse(BaseModel):
    """预测响应模式"""

    match_id: int
    match_info: MatchInfo
    prediction: PredictionData
    source: str = Field(default="cached", pattern="^(cached|real_time)$")


class BatchPredictionRequest(BaseModel):
    """批量预测请求模式"""

    match_ids: List[int] = Field(max_length=50)
    model_version: Optional[str] = None
    model_name: Optional[str] = None
    include_confidence: bool = True


class BatchPredictionResponse(BaseModel):
    """批量预测响应模式"""

    total_requested: int
    valid_matches: int
    successful_predictions: int
    invalid_match_ids: List[int]
    predictions: List[PredictionData]


class UpcomingMatchesRequest(BaseModel):
    """即将到来的比赛请求模式"""

    league_id: Optional[int] = None
    team_id: Optional[int] = None
    days_ahead: int = Field(default=7, ge=1, le=30)
    include_predictions: bool = False


class UpcomingMatchesResponse(BaseModel):
    """即将到来的比赛响应模式"""

    total_matches: int
    matches: List[MatchInfo]
    predictions: Optional[List[PredictionData]] = None


class ModelStats(BaseModel):
    """模型统计模式"""

    model_name: str
    model_version: str
    total_predictions: int
    correct_predictions: int
    accuracy: float = Field(ge=0.0, le=1.0)
    last_updated: str


class ModelStatsResponse(BaseModel):
    """模型统计响应模式"""

    models: List[ModelStats]
    total_models: int


class HistoryPrediction(BaseModel):
    """历史预测模式"""

    id: int
    model_version: str
    model_name: str
    home_win_probability: float
    draw_probability: float
    away_win_probability: float
    predicted_result: str
    confidence_score: float
    created_at: str
    is_correct: Optional[bool] = None
    actual_result: Optional[str] = None
    verified_at: Optional[str] = None


class PredictionHistoryResponse(BaseModel):
    """预测历史响应模式"""

    match_id: int
    total_predictions: int
    predictions: List[HistoryPrediction]


class RecentPrediction(BaseModel):
    """最近预测模式"""

    id: int
    match_id: int
    model_version: str
    model_name: str
    predicted_result: str
    confidence_score: float
    created_at: str
    is_correct: Optional[bool] = None
    match_info: MatchInfo


class RecentPredictionsResponse(BaseModel):
    """最近预测响应模式"""

    time_range_hours: int
    total_predictions: int
    predictions: List[RecentPrediction]


class PredictionOverview(BaseModel):
    """预测概览模式"""

    total_predictions: int
    correct_predictions: int
    accuracy: float
    last_prediction: Optional[str] = None
    model_count: int


class PredictionOverviewResponse(BaseModel):
    """预测概览响应模式"""

    overview: PredictionOverview
    recent_predictions: List[RecentPrediction]


class VerificationResponse(BaseModel):
    """验证响应模式"""

    match_id: int
    verified: bool
