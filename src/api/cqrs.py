"""
CQRS API端点
CQRS API Endpoints

提供CQRS模式的HTTP接口。
Provides HTTP interface for CQRS pattern.
"""

from datetime import date, datetime
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query
from pydantic import BaseModel, Field

from ..cqrs.application import CQRSServiceFactory
from src.core.config import Config 

router = APIRouter(prefix="/cqrs", tags=["CQRS"])


# 依赖注入函数
# 请求模型
class CreatePredictionRequest(BaseModel):
    """创建预测请求"""

    match_id: int = Field(..., description="比赛ID")
    user_id: Optional[int] = Field(None, description="用户ID")
    predicted_home: int = Field(..., ge=0, description="主队预测得分")
    predicted_away: int = Field(..., ge=0, description="客队预测得分")
    confidence: float = Field(..., ge=0, le=1, description="置信度")
    strategy_used: Optional[str] = Field(None, description="使用的策略")
    notes: Optional[str] = Field(None, description="备注")


class UpdatePredictionRequest(BaseModel):
    """更新预测请求"""

    predicted_home: Optional[int] = Field(None, ge=0, description="主队预测得分")
    predicted_away: Optional[int] = Field(None, ge=0, description="客队预测得分")
    confidence: Optional[float] = Field(None, ge=0, le=1, description="置信度")
    strategy_used: Optional[str] = Field(None, description="使用的策略")
    notes: Optional[str] = Field(None, description="备注")


class CreateUserRequest(BaseModel):
    """创建用户请求"""

    username: str = Field(..., min_length=3, description="用户名")
    email: str = Field(..., pattern=r"^[^@]+@[^@]+\.[^@]+$", description="邮箱")
    password_hash: str = Field(..., description="密码哈希")


class CreateMatchRequest(BaseModel):
    """创建比赛请求"""

    home_team: str = Field(..., description="主队名称")
    away_team: str = Field(..., description="客队名称")
    match_date: datetime = Field(..., description="比赛时间")
    competition: Optional[str] = Field(None, description="赛事")
    venue: Optional[str] = Field(None, description="场地")


# 响应模型
class CommandResponse(BaseModel):
    """命令响应"""

    success: bool
    message: str
    data: Optional[Dict[str, Any]] = None
    errors: Optional[List[str]] = None


# 依赖注入
# 预测命令端点
@router.post("/predictions", response_model=CommandResponse, summary="创建预测")
async def create_prediction(
    request: CreatePredictionRequest,
    background_tasks: BackgroundTasks,
    service=Depends(get_prediction_cqrs_service),
):
    """创建新的预测"""
    result = await service.create_prediction(
        match_id=request.match_id,
        user_id=request.user_id or 1,  # 从认证中获取，默认为1
        predicted_home=request.predicted_home,
        predicted_away=request.predicted_away,
        confidence=request.confidence,
        strategy_used=request.strategy_used,
        notes=request.notes,
    )

    return CommandResponse(
        success=result.success,
        message=result.message,
        data=result.data.to_dict() if result.data else None,
        errors=result.errors,
    )


@router.put("/predictions/{prediction_id}", response_model=CommandResponse, summary="更新预测")
async def update_prediction(
    prediction_id: int,
    request: UpdatePredictionRequest,
    service=Depends(get_prediction_cqrs_service),
):
    """更新预测"""
    result = await service.update_prediction(
        prediction_id=prediction_id,
        predicted_home=request.predicted_home,
        predicted_away=request.predicted_away,
        confidence=request.confidence,
        strategy_used=request.strategy_used,
        notes=request.notes,
    )

    return CommandResponse(
        success=result.success,
        message=result.message,
        data=result.data.to_dict() if result.data else None,
        errors=result.errors,
    )


@router.delete("/predictions/{prediction_id}", response_model=CommandResponse, summary="删除预测")
async def delete_prediction(prediction_id: int, service=Depends(get_prediction_cqrs_service)):
    """删除预测"""
    result = await service.delete_prediction(prediction_id)

    return CommandResponse(
        success=result.success,
        message=result.message,
        data=result.data,
        errors=result.errors,
    )


# CQRS服务根路径
@router.get("/", summary="CQRS服务根路径")
async def get_cqrs_root():
    """CQRS服务根路径"""
    return {
        "service": "足球预测API",
        "module": "cqrs",
        "version": "1.0.0",
        "status": "运行中",
        "description": "CQRS模式实现 - 命令查询职责分离",
        "endpoints": {
            "predictions": "/predictions/{prediction_id}",
            "user_predictions": "/users/{user_id}/predictions",
            "user_stats": "/users/{user_id}/stats",
            "match_details": "/matches/{match_id}",
            "upcoming_matches": "/matches/upcoming",
            "system_status": "/system/status",
        },
        "commands": {
            "create_prediction": "POST /predictions",
            "update_prediction": "PUT /predictions/{prediction_id}",
            "delete_prediction": "DELETE /predictions/{prediction_id}",
            "create_user": "POST /users",
        },
    }


# 预测查询端点
@router.get("/predictions/{prediction_id}", summary="获取预测详情")
async def get_prediction(prediction_id: int, service=Depends(get_prediction_cqrs_service)):
    """获取预测详情"""
    prediction = await service.get_prediction_by_id(prediction_id)
    if not prediction:
        raise HTTPException(
            status_code=404, detail="预测不存在"  # TODO: 将魔法数字 404 提取为常量
        )  # TODO: 将魔法数字 404 提取为常量

    return prediction.to_dict()


@router.get("/users/{user_id}/predictions", summary="获取用户预测列表")
async def get_user_predictions(
    user_id: int,
    limit: Optional[int] = Query(10, ge=1, le=100),  # TODO: 将魔法数字 100 提取为常量
    offset: Optional[int] = Query(0, ge=0),
    start_date: Optional[date] = Query(None),
    end_date: Optional[date] = Query(None),
    service=Depends(get_prediction_cqrs_service),
):
    """获取用户的所有预测"""
    predictions = await service.get_predictions_by_user(
        user_id=user_id,
        limit=limit,
        offset=offset,
        start_date=start_date,
        end_date=end_date,
    )

    return {
        "predictions": [p.to_dict() for p in predictions],
        "total": len(predictions),
        "limit": limit,
        "offset": offset,
    }


@router.get("/users/{user_id}/stats", summary="获取用户统计")
async def get_user_statistics(
    user_id: int,
    include_predictions: bool = Query(False),
    service=Depends(get_prediction_cqrs_service),
):
    """获取用户统计信息"""
    stats = await service.get_user_stats(user_id, include_predictions)
    if not stats:
        raise HTTPException(
            status_code=404, detail="用户统计不存在"  # TODO: 将魔法数字 404 提取为常量
        )  # TODO: 将魔法数字 404 提取为常量

    return stats.to_dict()


# 比赛命令端点
@router.post("/matches", response_model=CommandResponse, summary="创建比赛")
async def create_match(request: CreateMatchRequest, service=Depends(get_match_cqrs_service)):
    """创建新的比赛"""
    result = await service.create_match(
        home_team=request.home_team,
        away_team=request.away_team,
        match_date=request.match_date,
        competition=request.competition,
        venue=request.venue,
    )

    return CommandResponse(
        success=result.success,
        message=result.message,
        data=result.data.to_dict() if result.data else None,
        errors=result.errors,
    )


# 比赛查询端点
@router.get("/matches/{match_id}", summary="获取比赛详情")
async def get_match(
    match_id: int,
    include_predictions: bool = Query(False),
    service=Depends(get_match_cqrs_service),
):
    """获取比赛详情"""
    match = await service.get_match_by_id(match_id, include_predictions)
    if not match:
        raise HTTPException(
            status_code=404, detail="比赛不存在"  # TODO: 将魔法数字 404 提取为常量
        )  # TODO: 将魔法数字 404 提取为常量

    return match.to_dict()


@router.get("/matches/upcoming", summary="获取即将到来的比赛")
async def get_upcoming_matches(
    days_ahead: int = Query(7, ge=1, le=30),  # TODO: 将魔法数字 30 提取为常量
    competition: Optional[str] = Query(None),
    limit: Optional[int] = Query(10, ge=1, le=100),  # TODO: 将魔法数字 100 提取为常量
    offset: Optional[int] = Query(0, ge=0),
    service=Depends(get_match_cqrs_service),
):
    """获取即将到来的比赛列表"""
    _matches = await service.get_upcoming_matches(
        days_ahead=days_ahead, competition=competition, limit=limit, offset=offset
    )

    return {
        "matches": [m.to_dict() for m in _matches],
        "total": len(_matches),
        "filters": {"days_ahead": days_ahead, "competition": competition},
    }


# 用户命令端点
@router.post("/users", response_model=CommandResponse, summary="创建用户")
async def create_user(request: CreateUserRequest, service=Depends(get_user_cqrs_service)):
    """创建新用户"""
    result = await service.create_user(
        username=request.username,
        email=request.email,
        password_hash=request.password_hash,
    )

    return CommandResponse(
        success=result.success,
        message=result.message,
        data=result.data.to_dict() if result.data else None,
        errors=result.errors,
    )


# 系统端点
@router.get("/system/status", summary="获取CQRS系统状态")
async def get_cqrs_system_status():
    """获取CQRS系统状态"""
    from ..cqrs.bus import get_command_bus, get_query_bus

    command_bus = get_command_bus()
    query_bus = get_query_bus()

    return {
        "status": "运行中",
        "commands": command_bus.get_registered_commands(),
        "queries": query_bus.get_registered_queries(),
        "total_commands": len(command_bus.get_registered_commands()),
        "total_queries": len(query_bus.get_registered_queries()),
    }


# 预测命令端点
# 预测命令端点
# 预测命令端点


# 预测命令端点
# 预测命令端点


# 预测命令端点
# 预测命令端点
# 预测命令端点

# 预测命令端点
# 预测命令端点
# 预测命令端点
# 预测命令端点
# 预测命令端点
def get_prediction_cqrs_service():  # TODO: 添加返回类型注解  # TODO: 添加返回类型注解  # TODO: 添加返回类型注解  # TODO: 添加返回类型注解  # TODO: 添加返回类型注解  # TODO: 添加返回类型注解  # TODO: 添加返回类型注解  # TODO: 添加返回类型注解  # TODO: 添加返回类型注解  # TODO: 添加返回类型注解  # TODO: 添加返回类型注解  # TODO: 添加返回类型注解  # TODO: 添加返回类型注解  # TODO: 添加返回类型注解
    """获取预测CQRS服务"""
    return CQRSServiceFactory.create_prediction_service()


def get_match_cqrs_service():  # TODO: 添加返回类型注解  # TODO: 添加返回类型注解  # TODO: 添加返回类型注解  # TODO: 添加返回类型注解  # TODO: 添加返回类型注解  # TODO: 添加返回类型注解  # TODO: 添加返回类型注解  # TODO: 添加返回类型注解  # TODO: 添加返回类型注解  # TODO: 添加返回类型注解  # TODO: 添加返回类型注解  # TODO: 添加返回类型注解  # TODO: 添加返回类型注解  # TODO: 添加返回类型注解
    """获取比赛CQRS服务"""
    return CQRSServiceFactory.create_match_service()


def get_user_cqrs_service():  # TODO: 添加返回类型注解  # TODO: 添加返回类型注解  # TODO: 添加返回类型注解  # TODO: 添加返回类型注解  # TODO: 添加返回类型注解  # TODO: 添加返回类型注解  # TODO: 添加返回类型注解  # TODO: 添加返回类型注解  # TODO: 添加返回类型注解  # TODO: 添加返回类型注解  # TODO: 添加返回类型注解  # TODO: 添加返回类型注解  # TODO: 添加返回类型注解  # TODO: 添加返回类型注解
    """获取用户CQRS服务"""
    return CQRSServiceFactory.create_user_service()


def get_analytics_cqrs_service():  # TODO: 添加返回类型注解  # TODO: 添加返回类型注解  # TODO: 添加返回类型注解  # TODO: 添加返回类型注解  # TODO: 添加返回类型注解  # TODO: 添加返回类型注解  # TODO: 添加返回类型注解  # TODO: 添加返回类型注解  # TODO: 添加返回类型注解  # TODO: 添加返回类型注解  # TODO: 添加返回类型注解  # TODO: 添加返回类型注解  # TODO: 添加返回类型注解  # TODO: 添加返回类型注解
    """获取分析CQRS服务"""
    return CQRSServiceFactory.create_analytics_service()


# 预测命令端点