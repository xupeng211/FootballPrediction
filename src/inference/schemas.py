"""
Inference Service Schemas
推理服务数据模型和Schema定义

使用Pydantic v2定义请求和响应的数据模型，确保类型安全和数据验证。
"""

from datetime import datetime
from typing import Any, Optional
from enum import Enum

from pydantic import BaseModel, Field, field_validator, ConfigDict


class ModelType(str, Enum):
    """模型类型枚举"""
    XGBOOST = "xgboost"
    LSTM = "lstm"
    ENSEMBLE = "ensemble"
    MOCK = "mock"


class PredictionType(str, Enum):
    """预测类型枚举"""
    WINNER = "winner"
    SCORE = "score"
    OVER_UNDER = "over_under"
    PROBABILITY = "probability"


class ModelInfo(BaseModel):
    """模型信息"""

    model_name: str = Field(..., description="模型名称")
    model_version: str = Field(..., description="模型版本")
    model_type: ModelType = Field(..., description="模型类型")
    created_at: datetime = Field(..., description="创建时间")
    file_size: Optional[int] = Field(None, description="模型文件大小（字节）")
    accuracy: Optional[float] = Field(None, ge=0.0, le=1.0, description="模型准确率")
    features: list[str] = Field(default_factory=list, description="使用的特征列表")
    metadata: dict[str, Any] = Field(default_factory=dict, description="额外元数据")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "model_name": "xgboost_football_v1",
                "model_version": "1.0.0",
                "model_type": "xgboost",
                "created_at": "2025-12-06T10:00:00Z",
                "file_size": 1048576,
                "accuracy": 0.75,
                "features": ["home_goals", "away_goals", "home_possession"],
                "metadata": {"training_dataset": "epl_2024", "framework": "xgboost"}
            }
        }
    )


class PredictionRequest(BaseModel):
    """预测请求"""

    match_id: str = Field(..., min_length=1, max_length=50, description="比赛ID")
    model_name: str = Field(default="default", description="使用的模型名称")
    model_version: Optional[str] = Field(None, description="指定的模型版本")
    prediction_type: PredictionType = Field(default=PredictionType.WINNER, description="预测类型")
    features: Optional[dict[str, Any]] = Field(None, description="自定义特征（可选）")
    force_recalculate: bool = Field(default=False, description="是否强制重新计算")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "match_id": "match_12345",
                "model_name": "xgboost_football_v1",
                "model_version": "1.0.0",
                "prediction_type": "winner",
                "features": {"home_goals": 2, "away_goals": 1},
                "force_recalculate": False
            }
        }
    )


class PredictionResponse(BaseModel):
    """预测响应"""

    request_id: str = Field(..., description="请求ID")
    match_id: str = Field(..., description="比赛ID")
    predicted_at: datetime = Field(..., description="预测时间")

    # 预测结果
    home_win_prob: float = Field(..., ge=0.0, le=1.0, description="主队获胜概率")
    draw_prob: float = Field(..., ge=0.0, le=1.0, description="平局概率")
    away_win_prob: float = Field(..., ge=0.0, le=1.0, description="客队获胜概率")
    predicted_outcome: str = Field(..., description="预测结果")
    confidence: float = Field(..., ge=0.0, le=1.0, description="预测置信度")

    # 模型信息
    model_name: str = Field(..., description="使用的模型名称")
    model_version: str = Field(..., description="使用的模型版本")
    model_type: ModelType = Field(..., description="模型类型")

    # 元数据
    features_used: list[str] = Field(default_factory=list, description="使用的特征列表")
    prediction_time_ms: Optional[float] = Field(None, description="预测耗时（毫秒）")
    cached: bool = Field(default=False, description="是否来自缓存")
    metadata: dict[str, Any] = Field(default_factory=dict, description="额外元数据")

    @field_validator('predicted_outcome')
    @classmethod
    def validate_predicted_outcome(cls, v):
        if v not in ['home_win', 'draw', 'away_win']:
            raise ValueError('predicted_outcome must be one of: home_win, draw, away_win')
        return v

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "request_id": "req_12345",
                "match_id": "match_12345",
                "predicted_at": "2025-12-06T10:00:00Z",
                "home_win_prob": 0.65,
                "draw_prob": 0.25,
                "away_win_prob": 0.10,
                "predicted_outcome": "home_win",
                "confidence": 0.75,
                "model_name": "xgboost_football_v1",
                "model_version": "1.0.0",
                "model_type": "xgboost",
                "features_used": ["home_goals", "away_goals", "home_possession"],
                "prediction_time_ms": 45.2,
                "cached": False,
                "metadata": {"calibrated": True, "ensemble_weight": 0.8}
            }
        }
    )


class BatchPredictionRequest(BaseModel):
    """批量预测请求"""

    requests: list[PredictionRequest] = Field(..., min_items=1, max_items=100, description="预测请求列表")
    batch_id: Optional[str] = Field(None, description="批次ID（可选）")
    parallel: bool = Field(default=True, description="是否并行处理")

    @field_validator('requests')
    @classmethod
    def validate_requests(cls, v):
        if len(v) == 0:
            raise ValueError('requests cannot be empty')
        return v


class BatchPredictionResponse(BaseModel):
    """批量预测响应"""

    batch_id: str = Field(..., description="批次ID")
    total_requests: int = Field(..., description="总请求数")
    successful_predictions: int = Field(..., description="成功预测数")
    failed_predictions: int = Field(..., description="失败预测数")
    predictions: list[PredictionResponse] = Field(..., description="预测结果列表")
    errors: list[dict[str, Any]] = Field(default_factory=list, description="错误信息列表")
    batch_time_ms: float = Field(..., description="批次处理时间（毫秒）")
    cached_count: int = Field(default=0, description="缓存命中数量")


class ErrorResponse(BaseModel):
    """错误响应"""

    error: str = Field(..., description="错误码")
    message: str = Field(..., description="错误消息")
    details: dict[str, Any] = Field(default_factory=dict, description="错误详情")
    request_id: Optional[str] = Field(None, description="请求ID")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="错误时间")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "error": "MODEL_LOAD_FAILED",
                "message": "Failed to load model 'xgboost_football_v1'",
                "details": {
                    "model_name": "xgboost_football_v1",
                    "model_path": "/app/models/xgboost_football_v1.pkl",
                    "error_type": "FileNotFoundError"
                },
                "request_id": "req_12345",
                "timestamp": "2025-12-06T10:00:00Z"
            }
        }
    )


class HealthCheckResponse(BaseModel):
    """健康检查响应"""

    status: str = Field(..., description="服务状态")
    model_loaded: bool = Field(..., description="模型是否已加载")
    cache_status: str = Field(..., description="缓存状态")
    hot_reload_enabled: bool = Field(..., description="热更新是否启用")
    loaded_models: list[ModelInfo] = Field(default_factory=list, description="已加载的模型")
    uptime_seconds: float = Field(..., description="运行时间（秒）")
    memory_usage_mb: float = Field(..., description="内存使用量（MB）")
    last_prediction_time: Optional[datetime] = Field(None, description="最后预测时间")


class ModelListResponse(BaseModel):
    """模型列表响应"""

    models: list[ModelInfo] = Field(..., description="可用模型列表")
    total_models: int = Field(..., description="总模型数")
    default_model: Optional[str] = Field(None, description="默认模型名称")
