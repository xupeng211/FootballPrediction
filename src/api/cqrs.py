"""
CQRS API端点
CQRS API Endpoints

提供CQRS模式的HTTP接口.
Provides HTTP interface for CQRS pattern.
"""

from datetime import date, datetime

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query
from pydantic import BaseModel, Field

from src.cqrs.application import CQRSServiceFactory

router = APIRouter(prefix="/cqrs", tags=["CQRS"])


def get_prediction_cqrs_service():
    """获取预测CQRS服务"""
    return CQRSServiceFactory.create_prediction_service()


def get_match_cqrs_service():
    """获取比赛CQRS服务"""
    return CQRSServiceFactory.create_match_service()


def get_user_cqrs_service():
    """获取用户CQRS服务"""
    return CQRSServiceFactory.create_user_service()


def get_analytics_cqrs_service():
    """获取分析CQRS服务"""
    return CQRSServiceFactory.create_analytics_service()


# 预测命令端点


class PredictionCreateCommand(BaseModel):
    """创建预测命令"""

    match_id: int = Field(..., description="比赛ID")
    user_id: int = Field(..., description="用户ID")
    predicted_home: int = Field(..., description="预测主队进球数")
    predicted_away: int = Field(..., description="预测客队进球数")
    confidence: float = Field(..., ge=0.0, le=1.0, description="置信度")
    strategy_used: str = Field(..., description="使用的策略")
    notes: str | None = Field(None, description="备注")


class PredictionResponse(BaseModel):
    """预测响应"""

    id: int
    match_id: int
    user_id: int
    predicted_home: int
    predicted_away: int
    confidence: float
    strategy_used: str
    notes: str | None
    created_at: datetime
    updated_at: datetime


@router.post("/predictions/", response_model=PredictionResponse)
async def create_prediction(
    command: PredictionCreateCommand,
    background_tasks: BackgroundTasks,
    service=Depends(get_prediction_cqrs_service),
):
    """创建预测"""
    try:
        result = await service.create_prediction(command)
        return result
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/predictions/{prediction_id}", response_model=PredictionResponse)
async def get_prediction(
    prediction_id: int,
    service=Depends(get_prediction_cqrs_service),
):
    """获取预测"""
    try:
        result = await service.get_prediction(prediction_id)
        return result
    except Exception as e:
        raise HTTPException(
            status_code=404, detail=str(e)
        ) from e  # TODO: B904 exception chaining


@router.get("/predictions/", response_model=list[PredictionResponse])
async def list_predictions(
    user_id: int | None = Query(None, description="用户ID"),
    limit: int = Query(10, ge=1, le=100, description="限制数量"),
    offset: int = Query(0, ge=0, description="偏移量"),
    service=Depends(get_prediction_cqrs_service),
):
    """列出预测"""
    try:
        result = await service.list_predictions(user_id, limit, offset)
        return result
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


# 比赛查询端点


class MatchResponse(BaseModel):
    """比赛响应"""

    id: int
    home_team: str
    away_team: str
    home_score: int | None
    away_score: int | None
    match_date: datetime
    status: str
    created_at: datetime
    updated_at: datetime


@router.get("/matches/{match_id}", response_model=MatchResponse)
async def get_match(
    match_id: int,
    service=Depends(get_match_cqrs_service),
):
    """获取比赛"""
    try:
        result = await service.get_match(match_id)
        return result
    except Exception as e:
        raise HTTPException(
            status_code=404, detail=str(e)
        ) from e  # TODO: B904 exception chaining


@router.get("/matches/", response_model=list[MatchResponse])
async def list_matches(
    date_from: date | None = Query(None, description="开始日期"),
    date_to: date | None = Query(None, description="结束日期"),
    limit: int = Query(10, ge=1, le=100, description="限制数量"),
    offset: int = Query(0, ge=0, description="偏移量"),
    service=Depends(get_match_cqrs_service),
):
    """列出比赛"""
    try:
        result = await service.list_matches(date_from, date_to, limit, offset)
        return result
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


# 用户查询端点


class UserResponse(BaseModel):
    """用户响应"""

    id: int
    username: str
    email: str
    created_at: datetime
    updated_at: datetime


@router.get("/users/{user_id}", response_model=UserResponse)
async def get_user(
    user_id: int,
    service=Depends(get_user_cqrs_service),
):
    """获取用户"""
    try:
        result = await service.get_user(user_id)
        return result
    except Exception as e:
        raise HTTPException(
            status_code=404, detail=str(e)
        ) from e  # TODO: B904 exception chaining


@router.get("/users/", response_model=list[UserResponse])
async def list_users(
    limit: int = Query(10, ge=1, le=100, description="限制数量"),
    offset: int = Query(0, ge=0, description="偏移量"),
    service=Depends(get_user_cqrs_service),
):
    """列出用户"""
    try:
        result = await service.list_users(limit, offset)
        return result
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


# 分析查询端点


class AnalyticsResponse(BaseModel):
    """分析响应"""

    total_predictions: int
    accuracy_rate: float
    average_confidence: float
    most_used_strategy: str
    recent_predictions: list[dict]


@router.get("/analytics/", response_model=AnalyticsResponse)
async def get_analytics(
    user_id: int | None = Query(None, description="用户ID"),
    days: int = Query(30, ge=1, le=365, description="分析天数"),
    service=Depends(get_analytics_cqrs_service),
):
    """获取分析数据"""
    try:
        result = await service.get_analytics(user_id, days)
        return result
    except Exception as e:
        raise HTTPException(
            status_code=400, detail=str(e)
        ) from e  # TODO: B904 exception chaining
