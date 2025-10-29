"""
实时比赛状态API端点

Realtime Match Status API Endpoints

提供实时比赛状态相关的HTTP API接口
Provides HTTP API endpoints for real-time match status functionality
"""

import logging
from datetime import datetime
from typing import Dict, Any, Optional, List
from fastapi import APIRouter, HTTPException, Query, BackgroundTasks
from pydantic import BaseModel, Field

from .match_service import get_realtime_match_service, MatchStatus
from .events import EventType, create_system_alert_event
from .manager import get_websocket_manager

router = APIRouter(prefix="/matches", tags=["realtime-matches"])
logger = logging.getLogger(__name__)


# ============================================================================
# Pydantic Models
# ============================================================================

class MatchInfo(BaseModel):
    """比赛信息模型"""
    match_id: int = Field(..., description="比赛ID")
    home_team: str = Field(..., description="主队")
    away_team: str = Field(..., description="客队")
    league: str = Field(..., description="联赛")
    status: str = Field(..., description="比赛状态")
    home_score: Optional[int] = Field(None, description="主队得分")
    away_score: Optional[int] = Field(None, description="客队得分")
    minute: Optional[int] = Field(None, description="比赛分钟")
    start_time: Optional[str] = Field(None, description="开始时间")
    last_update: Optional[str] = Field(None, description="最后更新时间")


class AddMatchRequest(BaseModel):
    """添加比赛请求模型"""
    match_id: int = Field(..., description="比赛ID")
    home_team: str = Field(..., description="主队")
    away_team: str = Field(..., description="客队")
    league: str = Field(..., description="联赛")
    status: str = Field("upcoming", description="比赛状态")
    start_time: Optional[str] = Field(None, description="开始时间")


class UpdateScoreRequest(BaseModel):
    """更新比分请求模型"""
    home_score: int = Field(..., ge=0, description="主队得分")
    away_score: int = Field(..., ge=0, description="客队得分")
    minute: Optional[int] = Field(None, ge=0, le=120, description="比赛分钟")


class UpdateStatusRequest(BaseModel):
    """更新状态请求模型"""
    status: str = Field(..., description="新状态")
    current_time: Optional[str] = Field(None, description="当前时间")


class MatchStatsResponse(BaseModel):
    """比赛统计响应模型"""
    service_name: str
    total_matches: int
    live_matches: int
    upcoming_matches: int
    completed_matches: int
    tracked_leagues: int
    total_subscribers: int
    is_monitoring: bool
    monitoring_interval: int
    live_update_interval: int


# ============================================================================
# API Endpoints
# ============================================================================

@router.post("/add", summary="添加比赛到监控")
async def add_match_to_monitoring(
    request: AddMatchRequest,
    background_tasks: BackgroundTasks
):
    """
    添加比赛到实时监控

    Args:
        request: 比赛信息
        background_tasks: 后台任务

    Returns:
        添加结果
    """
    try:
        service = get_realtime_match_service()

        # 解析开始时间
        start_time = None
        if request.start_time:
            start_time = datetime.fromisoformat(request.start_time)

        # 添加比赛
        success = await service.add_match(
            match_id=request.match_id,
            home_team=request.home_team,
            away_team=request.away_team,
            league=request.league,
            status=MatchStatus(request.status),
            start_time=start_time
        )

        if not success:
            raise HTTPException(status_code=400, detail="Failed to add match to monitoring")

        # 发送通知
        background_tasks.add_task(
            _send_match_notification,
            request.match_id,
            "match_added",
            {
                "home_team": request.home_team,
                "away_team": request.away_team,
                "league": request.league,
                "status": request.status
            }
        )

        return {
            "success": True,
            "message": "Match added to monitoring successfully",
            "match_id": request.match_id,
            "added_at": datetime.now().isoformat()
        }

    except ValueError:
        raise HTTPException(status_code=400, detail=f"Invalid status: {request.status}")
    except Exception as e:
        logger.error(f"Failed to add match to monitoring: {e}")
        raise HTTPException(status_code=500, detail="Failed to add match to monitoring")


@router.put("/{match_id}/score", summary="更新比赛比分")
async def update_match_score(
    match_id: int,
    request: UpdateScoreRequest,
    background_tasks: BackgroundTasks
):
    """
    更新比赛比分

    Args:
        match_id: 比赛ID
        request: 比分更新请求
        background_tasks: 后台任务

    Returns:
        更新结果
    """
    try:
        service = get_realtime_match_service()

        # 更新比分
        score_changed = await service.update_match_score(
            match_id=match_id,
            home_score=request.home_score,
            away_score=request.away_score,
            minute=request.minute
        )

        if not score_changed:
            raise HTTPException(status_code=404, detail="Match not found or score unchanged")

        # 获取比赛信息
        match_info = await service.get_match_info(match_id)

        # 发送通知
        background_tasks.add_task(
            _send_match_notification,
            match_id,
            "score_updated",
            {
                "home_score": request.home_score,
                "away_score": request.away_score,
                "minute": request.minute,
                "display_score": f"{request.home_score}:{request.away_score}"
            }
        )

        return {
            "success": True,
            "message": "Score updated successfully",
            "match_id": match_id,
            "home_score": request.home_score,
            "away_score": request.away_score,
            "minute": request.minute,
            "updated_at": datetime.now().isoformat(),
            "match_info": match_info
        }

    except Exception as e:
        logger.error(f"Failed to update match score: {e}")
        raise HTTPException(status_code=500, detail="Failed to update match score")


@router.put("/{match_id}/status", summary="更新比赛状态")
async def update_match_status(
    match_id: int,
    request: UpdateStatusRequest,
    background_tasks: BackgroundTasks
):
    """
    更新比赛状态

    Args:
        match_id: 比赛ID
        request: 状态更新请求
        background_tasks: 后台任务

    Returns:
        更新结果
    """
    try:
        service = get_realtime_match_service()

        # 解析当前时间
        current_time = None
        if request.current_time:
            current_time = datetime.fromisoformat(request.current_time)

        # 更新状态
        status_changed = await service.update_match_status(
            match_id=match_id,
            status=MatchStatus(request.status),
            current_time=current_time
        )

        if not status_changed:
            raise HTTPException(status_code=404, detail="Match not found or status unchanged")

        # 获取比赛信息
        match_info = await service.get_match_info(match_id)

        # 发送通知
        background_tasks.add_task(
            _send_match_notification,
            match_id,
            "status_updated",
            {
                "new_status": request.status,
                "current_score": match_info.get("display_score") if match_info else None,
                "minute": match_info.get("minute") if match_info else None
            }
        )

        return {
            "success": True,
            "message": "Status updated successfully",
            "match_id": match_id,
            "new_status": request.status,
            "updated_at": datetime.now().isoformat(),
            "match_info": match_info
        }

    except ValueError:
        raise HTTPException(status_code=400, detail=f"Invalid status: {request.status}")
    except Exception as e:
        logger.error(f"Failed to update match status: {e}")
        raise HTTPException(status_code=500, detail="Failed to update match status")


@router.get("/{match_id}", summary="获取比赛信息")
async def get_match_info(match_id: int):
    """
    获取指定比赛的信息

    Args:
        match_id: 比赛ID

    Returns:
        比赛信息
    """
    try:
        service = get_realtime_match_service()
        match_info = await service.get_match_info(match_id)

        if not match_info:
            raise HTTPException(status_code=404, detail="Match not found")

        return match_info

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get match info: {e}")
        raise HTTPException(status_code=500, detail="Failed to get match info")


@router.get("/league/{league}", summary="获取联赛比赛")
async def get_league_matches(
    league: str,
    status: Optional[str] = Query(None, description="状态过滤"),
    limit: int = Query(50, ge=1, le=200, description="返回数量限制")
):
    """
    获取指定联赛的所有比赛

    Args:
        league: 联赛名称
        status: 状态过滤
        limit: 返回数量限制

    Returns:
        联赛比赛列表
    """
    try:
        service = get_realtime_match_service()
        matches = await service.get_league_matches(league)

        # 状态过滤
        if status:
            matches = [m for m in matches if m.get("status") == status]

        # 限制数量
        matches = matches[:limit]

        return {
            "league": league,
            "matches": matches,
            "total_count": len(matches),
            "status_filter": status,
            "limit": limit,
            "retrieved_at": datetime.now().isoformat()
        }

    except Exception as e:
        logger.error(f"Failed to get league matches: {e}")
        raise HTTPException(status_code=500, detail="Failed to get league matches")


@router.get("/live", summary="获取直播比赛")
async def get_live_matches(
    league: Optional[str] = Query(None, description="联赛过滤"),
    limit: int = Query(20, ge=1, le=100, description="返回数量限制")
):
    """
    获取所有直播中的比赛

    Args:
        league: 联赛过滤
        limit: 返回数量限制

    Returns:
        直播比赛列表
    """
    try:
        service = get_realtime_match_service()
        live_matches = await service.get_live_matches()

        # 联赛过滤
        if league:
            live_matches = [m for m in live_matches if m.get("league") == league]

        # 限制数量
        live_matches = live_matches[:limit]

        return {
            "live_matches": live_matches,
            "total_count": len(live_matches),
            "league_filter": league,
            "limit": limit,
            "retrieved_at": datetime.now().isoformat()
        }

    except Exception as e:
        logger.error(f"Failed to get live matches: {e}")
        raise HTTPException(status_code=500, detail="Failed to get live matches")


@router.get("/stats", response_model=MatchStatsResponse, summary="获取比赛服务统计")
async def get_match_service_stats():
    """
    获取实时比赛服务统计信息

    Returns:
        服务统计信息
    """
    try:
        service = get_realtime_match_service()
        stats = await service.get_service_stats()

        return MatchStatsResponse(**stats)

    except Exception as e:
        logger.error(f"Failed to get service stats: {e}")
        raise HTTPException(status_code=500, detail="Failed to get service stats")


@router.post("/{match_id}/subscribe", summary="订阅比赛更新")
async def subscribe_to_match_updates(
    match_id: int,
    user_id: str = Query(..., description="用户ID")
):
    """
    订阅比赛更新通知

    Args:
        match_id: 比赛ID
        user_id: 用户ID

    Returns:
        订阅结果
    """
    try:
        service = get_realtime_match_service()
        success = await service.subscribe_to_match(match_id, user_id)

        if not success:
            raise HTTPException(status_code=404, detail="Match not found")

        return {
            "success": True,
            "message": "Successfully subscribed to match updates",
            "match_id": match_id,
            "user_id": user_id,
            "subscribed_at": datetime.now().isoformat()
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to subscribe to match updates: {e}")
        raise HTTPException(status_code=500, detail="Failed to subscribe to match updates")


@router.delete("/{match_id}/subscribe", summary="取消订阅比赛更新")
async def unsubscribe_from_match_updates(
    match_id: int,
    user_id: str = Query(..., description="用户ID")
):
    """
    取消订阅比赛更新通知

    Args:
        match_id: 比赛ID
        user_id: 用户ID

    Returns:
        取消订阅结果
    """
    try:
        service = get_realtime_match_service()
        success = await service.unsubscribe_from_match(match_id, user_id)

        if not success:
            raise HTTPException(status_code=404, detail="Match not found")

        return {
            "success": True,
            "message": "Successfully unsubscribed from match updates",
            "match_id": match_id,
            "user_id": user_id,
            "unsubscribed_at": datetime.now().isoformat()
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to unsubscribe from match updates: {e}")
        raise HTTPException(status_code=500, detail="Failed to unsubscribe from match updates")


@router.post("/broadcast/alert", summary="广播比赛告警")
async def broadcast_match_alert(
    message: str,
    match_id: Optional[int] = None,
    alert_type: str = "info",
    severity: str = "low",
    component: str = "match_api"
):
    """
    广播比赛相关告警消息

    Args:
        message: 告警消息
        match_id: 比赛ID（可选）
        alert_type: 告警类型
        severity: 严重程度
        component: 组件名称

    Returns:
        广播结果
    """
    try:
        service = get_realtime_match_service()

        # 构建告警数据
        alert_data = {
            "message": message,
            "match_id": match_id,
            "alert_type": alert_type,
            "severity": severity,
            "component": component,
            "timestamp": datetime.now().isoformat()
        }

        await service.broadcast_system_alert(message, alert_type, severity, component)

        return {
            "success": True,
            "message": "Match alert broadcasted successfully",
            "alert_data": alert_data,
            "broadcasted_at": datetime.now().isoformat()
        }

    except Exception as e:
        logger.error(f"Failed to broadcast match alert: {e}")
        raise HTTPException(status_code=500, detail="Failed to broadcast match alert")


# ============================================================================
# Helper Functions
# ============================================================================

async def _send_match_notification(
    match_id: int,
    action: str,
    data: Dict[str, Any]
) -> None:
    """发送比赛通知"""
    try:
        websocket_manager = get_websocket_manager()

        notification = {
            "type": "match_notification",
            "data": {
                "match_id": match_id,
                "action": action,
                "timestamp": datetime.now().isoformat(),
                **data
            }
        }

        await websocket_manager.broadcast(notification)

    except Exception as e:
        logger.error(f"Failed to send match notification: {e}")