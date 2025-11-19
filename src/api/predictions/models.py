"""预测API模型定义."""

from pydantic import BaseModel, Field


class MatchInfo(BaseModel):
    """比赛信息模式."""

    match_id: int
    home_team_id: int
    away_team_id: int
    league_id: int
    match_time: str
    match_status: str
    season: str | None = None


class PredictionData(BaseModel):
    """预测数据模式."""

    id: int | None = None
    model_version: str
    model_name: str
    home_win_probability: float = Field(ge=0.0, le=1.0)
    draw_probability: float = Field(ge=0.0, le=1.0)
    away_win_probability: float = Field(ge=0.0, le=1.0)
    predicted_result: str
    confidence_score: float = Field(ge=0.0, le=1.0)
    created_at: str | None = None
    is_correct: bool | None = None
    actual_result: str | None = None


class PredictionRequest(BaseModel):
    """预测请求模式."""

    match_id: int
    model_version: str | None = None
    model_name: str | None = None
    include_confidence: bool = True


class PredictionResponse(BaseModel):
    """预测响应模式."""

    match_id: int
    match_info: MatchInfo
    prediction: PredictionData
    source: str = Field(default="cached", pattern="^(cached|real_time)$")


class BatchPredictionRequest(BaseModel):
    """批量预测请求模式."""

    match_ids: list[int] = Field(max_length=50)
    model_version: str | None = None
    model_name: str | None = None
    include_confidence: bool = True


class BatchPredictionResponse(BaseModel):
    """批量预测响应模式."""

    total_requested: int
    valid_matches: int
    successful_predictions: int
    invalid_match_ids: list[int]
    predictions: list[PredictionData]


class UpcomingMatchesRequest(BaseModel):
    """即将到来的比赛请求模式."""

    league_id: int | None = None
    team_id: int | None = None
    days_ahead: int = Field(default=7, ge=1, le=30)
    include_predictions: bool = False


class UpcomingMatchesResponse(BaseModel):
    """即将到来的比赛响应模式."""

    total_matches: int
    matches: list[MatchInfo]
    predictions: list[PredictionData] | None = None


class ModelStats(BaseModel):
    """模型统计模式."""

    model_name: str
    model_version: str
    total_predictions: int
    correct_predictions: int
    accuracy: float = Field(ge=0.0, le=1.0)
    last_updated: str


class ModelStatsResponse(BaseModel):
    """模型统计响应模式."""

    models: list[ModelStats]
    total_models: int


class HistoryPrediction(BaseModel):
    """历史预测模式."""

    id: int
    model_version: str
    model_name: str
    home_win_probability: float
    draw_probability: float
    away_win_probability: float
    predicted_result: str
    confidence_score: float
    created_at: str
    is_correct: bool | None = None
    actual_result: str | None = None
    verified_at: str | None = None


class PredictionHistoryResponse(BaseModel):
    """预测历史响应模式."""

    match_id: int
    total_predictions: int
    predictions: list[HistoryPrediction]


class RecentPrediction(BaseModel):
    """最近预测模式."""

    id: int
    match_id: int
    model_version: str
    model_name: str
    predicted_result: str
    confidence_score: float
    created_at: str
    is_correct: bool | None = None
    match_info: MatchInfo


class RecentPredictionsResponse(BaseModel):
    """最近预测响应模式."""

    time_range_hours: int
    total_predictions: int
    predictions: list[RecentPrediction]


class PredictionOverview(BaseModel):
    """预测概览模式."""

    total_predictions: int
    correct_predictions: int
    accuracy: float
    last_prediction: str | None = None
    model_count: int


class PredictionOverviewResponse(BaseModel):
    """预测概览响应模式."""

    overview: PredictionOverview
    recent_predictions: list[RecentPrediction]


class VerificationResponse(BaseModel):
    """验证响应模式."""

    match_id: int
    verified: bool
