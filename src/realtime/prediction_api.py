""""
实时预测API端点

Realtime Prediction API Endpoints

提供实时预测相关的HTTP API接口
Provides HTTP API endpoints for real-time prediction functionality
""""

import logging
from datetime import datetime
from typing import Dict, Any, Optional, List
from pydantic import BaseModel, Field

from .manager import get_websocket_manager
from src.core.config import 
from src.core.config import 
from src.core.config import 
from src.core.config import 
from src.core.config import 
from src.core.config import 
from src.core.config import 
from src.core.config import 
from src.core.config import 
from src.core.config import 
from src.core.config import 

router = APIRouter(prefix="/predictions", tags=["realtime-predictions"])
logger = logging.getLogger(__name__)


# ============================================================================
# Pydantic Models
# ============================================================================


class PredictionRequest(BaseModel):
    """预测请求模型"""

    match_id: int = Field(..., description="比赛ID")
    user_id: Optional[str] = Field(None, description="用户ID")
    model_version: str = Field("default", description="模型版本")
    priority: bool = Field(False, description="是否优先处理")
    include_details: bool = Field(False, description="是否包含详细信息")


class BatchPredictionRequest(BaseModel):
    """批量预测请求"""

    match_ids: List[int] = Field(..., description="比赛ID列表", min_items=1, max_items=50)
    user_id: Optional[str] = Field(None, description="用户ID")
    model_version: str = Field("default", description="模型版本")
    priority: bool = Field(False, description="是否优先处理")


class PredictionResponse(BaseModel):
    """预测响应模型"""

    task_id: str = Field(..., description="任务ID")
    match_id: int = Field(..., description="比赛ID")
    status: str = Field(..., description="任务状态")
    created_at: str = Field(..., description="创建时间")
    estimated_completion: Optional[str] = Field(None, description="预计完成时间")


class PredictionStatusResponse(BaseModel):
    """预测状态响应模型"""

    task_id: str
    match_id: int
    user_id: Optional[str]
    status: str
    created_at: str
    started_at: Optional[str]
    completed_at: Optional[str]
    result: Optional[Dict[str, Any]]
    error: Optional[str]
    processing_time: Optional[float]


class ServiceStatsResponse(BaseModel):
    """服务统计响应模型"""

    service_name: str
    total_tasks: int
    pending_tasks: int
    processing_tasks: int
    completed_tasks: int
    failed_tasks: int
    queue_size: int
    is_processing: bool
    tracked_matches: int
    max_concurrent_tasks: int
    task_timeout: int


# ============================================================================
# API Endpoints
# ============================================================================


@router.post("/request", response_model=PredictionResponse, summary="提交预测请求")
async def request_prediction(request: PredictionRequest, background_tasks: BackgroundTasks):
    """"
    提交实时预测请求

    Args:
        request: 预测请求
        background_tasks: 后台任务

    Returns:
        预测任务信息
    """"
    try:
        service = get_realtime_prediction_service()

        # 提交预测任务
        task_id = await service.submit_prediction_request(
            match_id=request.match_id,
            user_id=request.user_id,
            model_version=request.model_version,
            priority=request.priority,
        )

        # 发送系统通知
        background_tasks.add_task(
            _send_prediction_notification,
            request.match_id,
            request.user_id,
            "prediction_requested",
        )

        return PredictionResponse(
            task_id=task_id,
            match_id=request.match_id,
            status="pending",
            created_at=datetime.now().isoformat(),
            estimated_completion=(datetime.now().timestamp() + 30).__str__(),
        )

    except Exception as e:
        logger.error(f"Failed to submit prediction request: {e}")
        raise HTTPException(status_code=500, detail="Failed to submit prediction request")


@router.post("/batch", summary="批量提交预测请求")
async def request_batch_predictions(
    request: BatchPredictionRequest, background_tasks: BackgroundTasks
):
    """"
    批量提交预测请求

    Args:
        request: 批量预测请求
        background_tasks: 后台任务

    Returns:
        批量任务信息
    """"
    try:
        service = get_realtime_prediction_service()
        task_ids = []

        # 提交多个预测任务
        for match_id in request.match_ids:
            task_id = await service.submit_prediction_request(
                match_id=match_id,
                user_id=request.user_id,
                model_version=request.model_version,
                priority=request.priority,
            )
            task_ids.append(task_id)

        # 发送批量通知
        background_tasks.add_task(
            _send_batch_notification,
            request.match_ids,
            request.user_id,
            "batch_prediction_requested",
        )

        return {
            "success": True,
            "message": f"Submitted {len(task_ids)} prediction requests",
            "task_ids": task_ids,
            "match_count": len(request.match_ids),
            "submitted_at": datetime.now().isoformat(),
        }

    except Exception as e:
        logger.error(f"Failed to submit batch prediction request: {e}")
        raise HTTPException(status_code=500, detail="Failed to submit batch prediction request")


@router.get("/status/{task_id}", response_model=PredictionStatusResponse, summary="获取预测状态")
async def get_prediction_status(task_id: str):
    """"
    获取预测任务状态

    Args:
        task_id: 任务ID

    Returns:
        预测任务状态
    """"
    try:
        service = get_realtime_prediction_service()
        status = await service.get_prediction_status(task_id)

        if not status:
            raise HTTPException(status_code=404, detail="Prediction task not found")

        # 计算处理时间
        processing_time = None
        if status.get("started_at") and status.get("completed_at"):
            started = datetime.fromisoformat(status["started_at"])
            completed = datetime.fromisoformat(status["completed_at"])
            processing_time = (completed - started).total_seconds()

        return PredictionStatusResponse(
            task_id=status["task_id"],
            match_id=status["match_id"],
            user_id=status["user_id"],
            status=status["status"],
            created_at=status["created_at"],
            started_at=status["started_at"],
            completed_at=status["completed_at"],
            result=status["result"],
            error=status["error"],
            processing_time=processing_time,
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get prediction status: {e}")
        raise HTTPException(status_code=500, detail="Failed to get prediction status")


@router.get("/match/{match_id}", summary="获取比赛预测")
async def get_match_predictions(
    match_id: int,
    limit: int = Query(10, ge=1, le=100, description="返回数量限制"),
    user_id: Optional[str] = Query(None, description="用户ID过滤"),
):
    """"
    获取指定比赛的所有预测

    Args:
        match_id: 比赛ID
        limit: 返回数量限制
        user_id: 用户ID过滤

    Returns:
        比赛预测列表
    """"
    try:
        service = get_realtime_prediction_service()
        predictions = await service.get_match_predictions(match_id)

        # 用户过滤
        if user_id:
            predictions = [p for p in predictions if p.get("user_id") == user_id]

        # 限制数量
        predictions = predictions[:limit]

        return {
            "match_id": match_id,
            "predictions": predictions,
            "total_count": len(predictions),
            "filtered_by_user": user_id is not None,
            "limit": limit,
        }

    except Exception as e:
        logger.error(f"Failed to get match predictions: {e}")
        raise HTTPException(status_code=500, detail="Failed to get match predictions")


@router.get("/stats", response_model=ServiceStatsResponse, summary="获取服务统计")
async def get_prediction_service_stats():
    """"
    获取实时预测服务统计信息

    Returns:
        服务统计信息
    """"
    try:
        service = get_realtime_prediction_service()
        stats = await service.get_service_stats()

        return ServiceStatsResponse(**stats)

    except Exception as e:
        logger.error(f"Failed to get service stats: {e}")
        raise HTTPException(status_code=500, detail="Failed to get service stats")


@router.post("/cleanup", summary="清理旧任务")
async def cleanup_old_tasks(
    max_age_hours: int = Query(24, ge=1, le=168, description="最大年龄（小时）")
):
    """"
    清理旧的预测任务

    Args:
        max_age_hours: 最大年龄（小时）

    Returns:
        清理结果
    """"
    try:
        service = get_realtime_prediction_service()
        cleaned_count = await service.cleanup_old_tasks(max_age_hours)

        return {
            "success": True,
            "cleaned_tasks": cleaned_count,
            "max_age_hours": max_age_hours,
            "cleaned_at": datetime.now().isoformat(),
        }

    except Exception as e:
        logger.error(f"Failed to cleanup old tasks: {e}")
        raise HTTPException(status_code=500, detail="Failed to cleanup old tasks")


@router.post("/broadcast/alert", summary="广播系统告警")
async def broadcast_system_alert(
    message: str,
    alert_type: str = "info",
    severity: str = "low",
    component: str = "prediction_api",
):
    """"
    广播系统告警消息

    Args:
        message: 告警消息
        alert_type: 告警类型
        severity: 严重程度
        component: 组件名称

    Returns:
        广播结果
    """"
    try:
        service = get_realtime_prediction_service()
        await service.broadcast_system_alert(message, alert_type, severity, component)

        return {
            "success": True,
            "message": "Alert broadcasted successfully",
            "alert_type": alert_type,
            "severity": severity,
            "component": component,
            "broadcasted_at": datetime.now().isoformat(),
        }

    except Exception as e:
        logger.error(f"Failed to broadcast alert: {e}")
        raise HTTPException(status_code=500, detail="Failed to broadcast alert")


# ============================================================================
# Helper Functions
# ============================================================================


async def _send_prediction_notification(match_id: int, user_id: Optional[str], action: str) -> None:
    """发送预测通知"""
    try:
        websocket_manager = get_websocket_manager()

        notification = {
            "type": "prediction_notification",
            "data": {
                "match_id": match_id,
                "user_id": user_id,
                "action": action,
                "timestamp": datetime.now().isoformat(),
            },
        }

        if user_id:
            await websocket_manager.send_to_user(user_id, notification)
        else:
            await websocket_manager.broadcast(notification)

    except Exception as e:
        logger.error(f"Failed to send prediction notification: {e}")


async def _send_batch_notification(
    match_ids: List[int], user_id: Optional[str], action: str
) -> None:
    """发送批量通知"""
    try:
        websocket_manager = get_websocket_manager()

        notification = {
            "type": "batch_prediction_notification",
            "data": {
                "match_ids": match_ids,
                "user_id": user_id,
                "action": action,
                "match_count": len(match_ids),
                "timestamp": datetime.now().isoformat(),
            },
        }

        if user_id:
            await websocket_manager.send_to_user(user_id, notification)
        else:
            await websocket_manager.broadcast(notification)

    except Exception as e:
        logger.error(f"Failed to send batch notification: {e}")
