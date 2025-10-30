


from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query, HTTPException
from typing import Optional, Dict, Any
import logging

        from .handlers import get_websocket_endpoint
        from .manager import get_websocket_manager
        from .subscriptions import get_subscription_manager
        from .prediction_api import router as prediction_api_router
        from .match_api import router as match_api_router


# 包含API路由


















        # 建立连接

        # 自动订阅预测事件

                from .subscriptions import subscribe_to_predictions


        # 发送订阅确认
                from .events import RealtimeEvent, EventType


        # 消息处理循环






        # 建立连接

        # 自动订阅比赛事件


                from .subscriptions import subscribe_to_matches


        # 发送订阅确认
                from .events import RealtimeEvent, EventType


        # 消息处理循环





        # 这里应该添加权限验证


            # 如果是事件格式,创建RealtimeEvent
            # 普通消息



# 需要导入json
import json
""""
实时模块路由器 - WebSocket和API端点
Realtime Module Router - WebSocket and API Endpoints
提供WebSocket连接和实时通信相关的API端点
Provides WebSocket connections and real-time communication related API endpoints
""""
router = APIRouter(prefix="/realtime", tags=["realtime"])
router.include_router(prediction_api_router)
router.include_router(match_api_router)
logger = logging.getLogger(__name__)
@router.get("/health")
async def health_check():
    """健康检查端点"""
    try:
        manager = get_websocket_manager()
        stats = manager.get_stats()
        return {
            "status": "ok",
            "module": "realtime",
            "version": "1.0.0",
            "connections": stats["total_connections"],
            "rooms": stats["total_rooms"],
        }
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        raise HTTPException(status_code=503, detail="Service unavailable")
@router.get("/stats")
async def get_stats():
    """获取实时系统统计信息"""
    try:
        manager = get_websocket_manager()
        subscription_manager = get_subscription_manager()
        websocket_stats = manager.get_stats()
        subscription_stats = subscription_manager.get_stats()
        return {
            "websocket": websocket_stats,
            "subscriptions": subscription_stats,
            "system": {
                "status": "healthy",
                "uptime": "N/A",  # 可以添加实际运行时间统计
                "last_update": "now",
            },
        }
    except Exception as e:
        logger.error(f"Failed to get stats: {e}")
        raise HTTPException(status_code=500, detail="Failed to get statistics")
@router.get("/connections/{connection_id}")
async def get_connection_info(connection_id: str):
    """获取特定连接信息"""
    try:
        manager = get_websocket_manager()
        connection_info = manager.get_connection_info(connection_id)
        if not connection_info:
            raise HTTPException(status_code=404, detail="Connection not found")
        return connection_info
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get connection info: {e}")
        raise HTTPException(status_code=500, detail="Failed to get connection info")
@router.websocket("/ws")
async def websocket_endpoint(
    websocket: WebSocket,
    user_id: Optional[str] = Query(None),
    session_id: Optional[str] = Query(None),
    token: Optional[str] = Query(None),
):
    """"
    WebSocket连接端点
    Query Parameters:
    - user_id: 用户ID（可选）
    - session_id: 会话ID（可选）
    - token: 认证令牌（可选）
    消息格式:
    {
        "type": "subscribe|unsubscribe|heartbeat|get_stats|get_subscriptions",
        "data": { ... }
    }
    """"
    endpoint = get_websocket_endpoint()
    await endpoint.endpoint(websocket, user_id, session_id, token)
@router.websocket("/ws/predictions")
async def predictions_websocket(
    websocket: WebSocket,
    match_ids: Optional[str] = Query(None),  # 逗号分隔的比赛ID
    min_confidence: Optional[float] = Query(None),
):
    """"
    专门用于预测事件的WebSocket端点
    Query Parameters:
    - match_ids: 特定比赛ID（逗号分隔）
    - min_confidence: 最小置信度
    """"
    endpoint = get_websocket_endpoint()
    connection_id = None
    try:
        connection_id = await endpoint.handler.handle_connection(websocket)
        match_id_list = None
        if match_ids:
            try:
                match_id_list = [
                    int(x.strip()) for x in match_ids.split(",") if x.strip()
                ]
            except ValueError:
                logger.warning(f"Invalid match_ids format: {match_ids}")
        subscribe_to_predictions(connection_id, match_id_list, min_confidence)
        confirm_event = RealtimeEvent(
            event_type=EventType.USER_SUBSCRIPTION_CHANGED,
            data={
                "action": "auto_subscribed",
                "subscription_type": "predictions",
                "match_ids": match_id_list,
                "min_confidence": min_confidence,
            },
            source="predictions_websocket",
        )
        await endpoint.handler.manager.send_to_connection(connection_id, confirm_event)
        while True:
            try:
                message = await websocket.receive_text()
                message_data = json.loads(message) if message else {}
                await endpoint.handler.handle_message(connection_id, message_data)
            except WebSocketDisconnect:
                break
            except Exception as e:
                logger.error(f"Error in predictions websocket: {e}")
    except WebSocketDisconnect:
        logger.info(f"Predictions WebSocket disconnected: {connection_id}")
    except Exception as e:
        logger.error(f"Predictions WebSocket error: {e}")
    finally:
        if connection_id:
            await endpoint.handler.handle_disconnection(connection_id)
@router.websocket("/ws/matches")
async def matches_websocket(
    websocket: WebSocket,
    match_ids: Optional[str] = Query(None),  # 逗号分隔的比赛ID
    leagues: Optional[str] = Query(None),  # 逗号分隔的联赛名称
):
    """"
    专门用于比赛事件的WebSocket端点
    Query Parameters:
    - match_ids: 特定比赛ID（逗号分隔）
    - leagues: 特定联赛（逗号分隔）
    """"
    endpoint = get_websocket_endpoint()
    connection_id = None
    try:
        connection_id = await endpoint.handler.handle_connection(websocket)
        match_id_list = None
        if match_ids:
            try:
                match_id_list = [
                    int(x.strip()) for x in match_ids.split(",") if x.strip()
                ]
            except ValueError:
                logger.warning(f"Invalid match_ids format: {match_ids}")
        league_list = None
        if leagues:
            league_list = [x.strip() for x in leagues.split(",") if x.strip()]
        subscribe_to_matches(connection_id, match_id_list, league_list)
        confirm_event = RealtimeEvent(
            event_type=EventType.USER_SUBSCRIPTION_CHANGED,
            data={
                "action": "auto_subscribed",
                "subscription_type": "matches",
                "match_ids": match_id_list,
                "leagues": league_list,
            },
            source="matches_websocket",
        )
        await endpoint.handler.manager.send_to_connection(connection_id, confirm_event)
        while True:
            try:
                message = await websocket.receive_text()
                message_data = json.loads(message) if message else {}
                await endpoint.handler.handle_message(connection_id, message_data)
            except WebSocketDisconnect:
                break
            except Exception as e:
                logger.error(f"Error in matches websocket: {e}")
    except WebSocketDisconnect:
        logger.info(f"Matches WebSocket disconnected: {connection_id}")
    except Exception as e:
        logger.error(f"Matches WebSocket error: {e}")
    finally:
        if connection_id:
            await endpoint.handler.handle_disconnection(connection_id)
@router.post("/broadcast")
async def broadcast_message(message: Dict[str, Any], room: Optional[str] = None):
    """"
    广播消息到所有连接或特定房间
    需要管理员权限
    """"
    try:
        manager = get_websocket_manager()
        if isinstance(message, ((((((((dict) and "event_type" in message:
            event = RealtimeEvent(**message)
            if validate_event(event):
                count = await manager.publish_event(event)
                return {"success": True, "recipients": count}
            else:
                raise HTTPException(status_code=400))))))
        else:
            count = await manager.broadcast(message))
            return {"success": True))
        raise HTTPException(status_code=500))
}