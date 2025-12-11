"""
推理API的Pydantic数据模型
定义请求和响应的数据结构

作者: Backend Engineer
创建时间: 2025-12-10
版本: 1.0.0 - Phase 3 Inference
"""

from typing import Dict, Any, Optional
from pydantic import BaseModel, Field
from datetime import datetime


class PredictionRequest(BaseModel):
    """预测请求模型"""

    # 基础比赛信息
    match_id: int = Field(..., description="比赛ID", example=12345)

    # 球队信息
    home_team_name: str = Field(
        ..., description="主队名称", example="Manchester United"
    )
    away_team_name: str = Field(..., description="客队名称", example="Liverpool")

    # 比赛时间
    match_date: datetime = Field(
        ..., description="比赛时间", example="2024-01-15T15:00:00"
    )

    # 当前比分 (如果是直播中的比赛)
    home_score: Optional[int] = Field(None, description="主队当前比分", example=0)
    away_score: Optional[int] = Field(None, description="客队当前比分", example=0)

    # 比赛统计 (从数据库或API获取的实时数据)
    home_xg: Optional[float] = Field(None, description="主队期望进球", example=1.8)
    away_xg: Optional[float] = Field(None, description="客队期望进球", example=1.2)

    # 基础统计 (如果可用)
    home_total_shots: Optional[int] = Field(
        None, description="主队总射门数", example=15
    )
    away_total_shots: Optional[int] = Field(
        None, description="客队总射门数", example=12
    )
    home_shots_on_target: Optional[int] = Field(
        None, description="主队射正数", example=6
    )
    away_shots_on_target: Optional[int] = Field(
        None, description="客队射正数", example=4
    )

    # 比赛上下文
    league_id: Optional[str] = Field(None, description="联赛ID", example="PL")
    league_name: Optional[str] = Field(
        None, description="联赛名称", example="Premier League"
    )

    # 其他统计数据 (JSON格式)
    stats_json: Optional[Dict[str, Any]] = Field(
        None,
        description="比赛统计数据JSON",
        example={"possession": {"home": 55, "away": 45}},
    )

    class Config:
        json_encoders = {datetime: lambda v: v.isoformat()}


class PredictionResponse(BaseModel):
    """预测响应模型"""

    # 基础信息
    match_id: int = Field(..., description="比赛ID", example=12345)

    # 预测结果
    prediction: str = Field(
        ...,
        description="预测的比赛结果: Home(主胜)/Away(客胜)/Draw(平局)",
        example="Home",
    )

    # 概率分布
    probabilities: Dict[str, float] = Field(
        ...,
        description="各类别概率",
        example={"Home": 0.55, "Away": 0.25, "Draw": 0.20},
    )

    # 置信度
    confidence: float = Field(
        ..., description="最高概率值，表示模型置信度", example=0.55, ge=0.0, le=1.0
    )

    # 模型信息
    model_version: str = Field(..., description="模型版本", example="v1.0.0")

    # 元数据
    timestamp: datetime = Field(
        ..., description="预测时间", example="2024-01-10T10:30:00"
    )

    # 特征信息
    feature_count: int = Field(..., description="使用的特征数量", example=52)
    missing_features: int = Field(..., description="缺失特征数量", example=0)

    # 处理时间
    processing_time_ms: Optional[float] = Field(
        None, description="处理时间(毫秒)", example=15.5
    )

    class Config:
        json_encoders = {datetime: lambda v: v.isoformat()}


class ModelInfoResponse(BaseModel):
    """模型信息响应模型"""

    # 模型状态
    status: str = Field(..., description="模型状态", example="loaded")

    # 模型详情
    model_type: str = Field(..., description="模型类型", example="XGBoost Classifier")
    model_version: str = Field(..., description="模型版本", example="v1.0.0")

    # 特征信息
    feature_count: int = Field(..., description="特征数量", example=52)

    # 目标类别
    target_classes: list[str] = Field(
        ..., description="目标类别", example=["Home", "Away", "Draw"]
    )

    # 性能指标
    performance_metrics: Optional[Dict[str, Any]] = Field(
        None, description="性能指标", example={"accuracy": 0.5553, "log_loss": 1.0396}
    )

    # 加载时间
    loaded_at: datetime = Field(
        ..., description="模型加载时间", example="2024-01-10T09:00:00"
    )

    class Config:
        json_encoders = {datetime: lambda v: v.isoformat()}


class ErrorResponse(BaseModel):
    """错误响应模型"""

    error: str = Field(..., description="错误类型", example="ValidationError")
    message: str = Field(..., description="错误信息", example="Invalid input data")
    details: Optional[Dict[str, Any]] = Field(None, description="错误详情")

    timestamp: datetime = Field(
        ..., description="错误发生时间", example="2024-01-10T10:30:00"
    )

    class Config:
        json_encoders = {datetime: lambda v: v.isoformat()}
