#!/usr/bin/env python3
"""
预测API路由 - Sprint 3 架构解耦版本

实现轻量级的RESTful API路由，专注于HTTP处理。
所有业务逻辑已移至服务层，实现完全的关注点分离。

Sprint 3 改进:
- 路由逻辑完全剥离 (P0-004) ✅
- 使用依赖注入容器 ✅
- 简化路由函数，专注HTTP处理 ✅
- 统一错误处理 ✅

核心功能:
1. GET /predict/match/{match_id} - 单场比赛预测
2. POST /predict/batch - 批量比赛预测
3. GET /health - 服务健康检查

设计原则:
- Single Responsibility (单一职责)
- Separation of Concerns (关注点分离)
- Dependency Injection (依赖注入)
"""

import logging
from datetime import datetime
from typing import Dict, Any

from fastapi import APIRouter, HTTPException, Query, Depends, Path, status
from pydantic import BaseModel, Field, validator

# 导入服务层
from src.services.prediction_service import PredictionService
from src.services.dependency_injection import get_container

logger = logging.getLogger(__name__)

# 创建API路由
router = APIRouter(
    prefix="/predict",
    tags=["predictions"],
    responses={
        404: {"description": "比赛不存在"},
        400: {"description": "请求参数错误"},
        500: {"description": "服务器内部错误"},
        503: {"description": "服务不可用"},
    },
)


# 简化的请求模型
class BatchPredictionRequest(BaseModel):
    """批量预测请求模型 - Sprint 3 精简版本"""
    match_ids: list[str] = Field(..., description="比赛ID列表", min_items=1, max_items=100)
    include_features: bool = Field(default=False, description="是否包含特征信息")
    include_metadata: bool = Field(default=True, description="是否包含元数据")

    @validator("match_ids")
    def validate_match_ids(cls, v):
        if not v:
            raise ValueError("比赛ID列表不能为空")
        if len(v) > 100:
            raise ValueError("批量预测最多支持100场比赛")
        return v


# 依赖注入 - 从容器获取服务
async def get_prediction_service_dependency() -> PredictionService:
    """获取预测服务依赖"""
    try:
        container = get_container()
        prediction_service = await container.resolve("prediction_service")
        return prediction_service
    except Exception as e:
        logger.error(f"预测服务依赖注入失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="预测服务不可用，请稍后重试"
        )


# 核心API路由
@router.get(
    "/match/{match_id}",
    summary="单场比赛预测",
    description="根据比赛ID预测1X2结果",
    response_model=Dict[str, Any],
)
async def predict_match(
    match_id: str = Path(..., description="比赛唯一标识符"),
    include_features: bool = Query(default=False, description="是否包含特征信息"),
    include_metadata: bool = Query(default=True, description="是否包含元数据"),
    prediction_service: PredictionService = Depends(get_prediction_service_dependency),
) -> Dict[str, Any]:
    """
    单场比赛预测端点 - Sprint 3 精简版本

    职责:
    1. HTTP请求参数验证
    2. 调用预测服务
    3. HTTP响应构建
    """
    try:
        logger.info(f"收到单场比赛预测请求: match_id={match_id}")

        # 调用服务层进行业务处理
        service_response = await prediction_service.predict_single_match(
            match_id=match_id,
            include_features=include_features,
            include_metadata=include_metadata
        )

        # 构建HTTP响应
        if service_response.success:
            return {
                "success": True,
                "data": service_response.data,
                "processing_time_ms": service_response.processing_time_ms,
                "request_id": service_response.request_id,
                "timestamp": service_response.timestamp.isoformat()
            }
        else:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=service_response.error or "预测处理失败"
            )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"单场比赛预测处理失败: match_id={match_id}, error={e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"预测服务内部错误: {str(e)}"
        )


@router.post(
    "/batch",
    summary="批量比赛预测",
    description="批量预测多场比赛的1X2结果",
    response_model=Dict[str, Any],
)
async def predict_batch(
    request: BatchPredictionRequest,
    prediction_service: PredictionService = Depends(get_prediction_service_dependency),
) -> Dict[str, Any]:
    """
    批量比赛预测端点 - Sprint 3 精简版本

    职责:
    1. 批量请求参数验证
    2. 调用预测服务批量处理
    3. HTTP响应构建
    """
    try:
        logger.info(f"收到批量预测请求: {len(request.match_ids)} 场比赛")

        # 调用服务层进行批量处理
        service_response = await prediction_service.predict_batch_matches(
            match_ids=request.match_ids,
            include_features=request.include_features,
            include_metadata=request.include_metadata,
            max_concurrent=10  # 默认并发数
        )

        # 构建HTTP响应
        if service_response.success:
            return {
                "success": True,
                "data": service_response.data,
                "processing_time_ms": service_response.processing_time_ms,
                "request_id": service_response.request_id,
                "timestamp": service_response.timestamp.isoformat()
            }
        else:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=service_response.error or "批量预测处理失败"
            )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"批量预测处理失败: match_ids={request.match_ids}, error={e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"批量预测服务内部错误: {str(e)}"
        )


@router.get(
    "/health",
    summary="服务健康检查",
    description="检查预测服务的健康状态",
    response_model=Dict[str, Any],
)
async def health_check(
    prediction_service: PredictionService = Depends(get_prediction_service_dependency),
) -> Dict[str, Any]:
    """
    服务健康检查端点 - Sprint 3 精简版本

    职责:
    1. 调用预测服务健康检查
    2. 构建HTTP响应
    """
    try:
        logger.info("收到健康检查请求")

        # 调用服务层进行健康检查
        service_response = await prediction_service.get_service_health()

        # 构建HTTP响应
        if service_response.success:
            return {
                "success": True,
                "data": service_response.data,
                "processing_time_ms": service_response.processing_time_ms,
                "request_id": service_response.request_id,
                "timestamp": service_response.timestamp.isoformat()
            }
        else:
            return {
                "success": False,
                "error": service_response.error,
                "timestamp": datetime.now().isoformat()
            }

    except Exception as e:
        logger.error(f"健康检查失败: {e}")
        return {
            "success": False,
            "error": f"健康检查服务异常: {str(e)}",
            "timestamp": datetime.now().isoformat()
        }