"""
Prediction Schemas - 预测服务的Pydantic模型定义

Phase 4: API Integration - 将PredictionService集成到FastAPI

定义标准的请求和响应模型，确保API接口的类型安全和数据验证。
"""

from pydantic import BaseModel, Field
from datetime import datetime
from typing import Dict, Optional


class PredictionRequest(BaseModel):
    """预测请求模型"""

    home_team_id: int = Field(
        ...,
        description="主队ID",
        example=8650,
        gt=0  # 确保ID为正数
    )

    away_team_id: int = Field(
        ...,
        description="客队ID",
        example=8456,
        gt=0  # 确保ID为正数
    )

    match_date: datetime = Field(
        default_factory=datetime.now,
        description="比赛时间",
        example="2024-05-20T15:00:00"
    )

    class Config:
        """Pydantic配置"""
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }
        schema_extra = {
            "example": {
                "home_team_id": 8650,
                "away_team_id": 8456,
                "match_date": "2024-05-20T15:00:00"
            }
        }


class PredictionResponse(BaseModel):
    """预测响应模型"""

    prediction: str = Field(
        ...,
        description="预测结果 (home_win/draw/away_win)",
        example="home_win"
    )

    confidence: float = Field(
        ...,
        description="置信度 (0-1)",
        ge=0.0,
        le=1.0,
        example=0.65
    )

    home_win_prob: float = Field(
        ...,
        description="主胜概率",
        ge=0.0,
        le=1.0,
        example=0.65
    )

    draw_prob: float = Field(
        ...,
        description="平局概率",
        ge=0.0,
        le=1.0,
        example=0.20
    )

    away_win_prob: float = Field(
        ...,
        description="客胜概率",
        ge=0.0,
        le=1.0,
        example=0.15
    )

    model_version: str = Field(
        ...,
        description="模型版本",
        example="v1"
    )

    features: Optional[Dict[str, float]] = Field(
        None,
        description="使用的特征值 (Debug用)"
    )

    match_info: Optional[Dict[str, object]] = Field(
        None,
        description="比赛信息"
    )

    generated_at: Optional[str] = Field(
        None,
        description="预测生成时间"
    )

    class Config:
        """Pydantic配置"""
        schema_extra = {
            "example": {
                "prediction": "home_win",
                "confidence": 0.65,
                "home_win_prob": 0.65,
                "draw_prob": 0.20,
                "away_win_prob": 0.15,
                "model_version": "v1",
                "features": {
                    "rolling_home_score_3": 1.8,
                    "rolling_home_expected_goals_3": 2.1,
                    "rolling_away_score_3": 1.2
                },
                "match_info": {
                    "home_team_id": 8650,
                    "away_team_id": 8456,
                    "match_date": "2024-05-20T15:00:00"
                },
                "generated_at": "2024-05-15T10:30:00Z"
            }
        }


class ErrorResponse(BaseModel):
    """错误响应模型"""

    error: str = Field(
        ...,
        description="错误类型",
        example="PredictionError"
    )

    message: str = Field(
        ...,
        description="错误消息",
        example="预测服务内部错误: 模型未初始化"
    )

    details: Optional[Dict[str, object]] = Field(
        None,
        description="错误详情"
    )

    timestamp: str = Field(
        default_factory=lambda: datetime.now().isoformat(),
        description="错误发生时间"
    )

    class Config:
        schema_extra = {
            "example": {
                "error": "PredictionError",
                "message": "预测服务内部错误: 模型未初始化",
                "timestamp": "2024-05-15T10:30:00Z"
            }
        }


class HealthResponse(BaseModel):
    """健康检查响应模型"""

    status: str = Field(
        ...,
        description="服务状态",
        example="healthy"
    )

    model_ready: bool = Field(
        ...,
        description="模型是否就绪",
        example=True
    )

    model_version: Optional[str] = Field(
        None,
        description="当前模型版本",
        example="v1"
    )

    uptime: Optional[str] = Field(
        None,
        description="服务运行时间",
        example="00:05:30"
    )

    timestamp: str = Field(
        default_factory=lambda: datetime.now().isoformat(),
        description="检查时间"
    )