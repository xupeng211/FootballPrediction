""""
WebSocket处理器 - 实时通信接口

WebSocket Handlers - Real-time Communication Interface

处理WebSocket连接,消息路由和订阅管理
Handles WebSocket connections, message routing, and subscription management
""""

import json
import logging
from typing import Dict, Any, Optional
from fastapi import WebSocket, WebSocketDisconnect, Depends, Query
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

from .subscriptions import (
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
from src.core.config import 
from src.core.config import 
from src.core.config import 
from src.core.config import 
    get_subscription_manager,
    subscribe_to_predictions,
    subscribe_to_matches,
    subscribe_to_odds,
)


security = HTTPBearer()
logger = logging.getLogger(__name__)


async def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
):
    """获取当前用户（简化版本,实际应该验证JWT token）"""
    # 这里应该实现JWT token验证逻辑
    # 暂时返回一个示例用户ID
    if credentials:
        # 实际应该解析JWT token获取用户ID
        return "demo_user"
    return None


class WebSocketHandler:
    """WebSocket处理器"""

    def __init__(self):
        self.manager = get_websocket_manager()
        self.subscription_manager = get_subscription_manager()
        self.logger = logging.getLogger(f"{__name__}.WebSocketHandler")

    async def handle_connection(
        self,
        websocket: WebSocket,
        user_id: Optional[str] = None,
        session_id: Optional[str] = None,
    ) -> str:
        """处理WebSocket连接"""
        try:
            # 建立连接
            connection = await self.manager.connect(websocket, user_id, session_id)
            connection_id = connection.connection_id

            self.logger.info(
                f"WebSocket connection established: {connection_id} for user: {user_id}"
            )

            # 发送欢迎消息
            welcome_event = RealtimeEvent(
                event_type=EventType.CONNECTION_STATUS,
                data={
                    "connection_id": connection_id,
                    "user_id": user_id,
                    "status": "connected",
                    "message": "Welcome to Football Prediction Real-time Service",
                    "timestamp": connection.info.connected_at.isoformat(),
                },
                source="websocket_handler",
            )
            await connection.send(welcome_event)

            return connection_id

        except Exception as e:
            self.logger.error(f"Failed to handle WebSocket connection: {e}")
            raise

    async def handle_message(self, connection_id: str, message: Dict[str, Any]) -> None:
        """处理接收到的消息"""
        try:
            message_type = message.get("type")
            data = message.get("data", {})

            self.logger.debug(f"Received message from {connection_id}: {message_type}")

            if message_type == "subscribe":
                await self._handle_subscribe(connection_id, data)
            elif message_type == "unsubscribe":
                await self._handle_unsubscribe(connection_id, data)
            elif message_type == "heartbeat":
                await self._handle_heartbeat(connection_id)
            elif message_type == "get_stats":
                await self._handle_get_stats(connection_id)
            elif message_type == "get_subscriptions":
                await self._handle_get_subscriptions(connection_id)
            else:
                self.logger.warning(f"Unknown message type: {message_type}")

        except Exception as e:
            self.logger.error(f"Error handling message from {connection_id}: {e}")

    async def _handle_subscribe(self, connection_id: str, data: Dict[str, Any]) -> None:
        """处理订阅请求"""
        try:
            subscription_type = data.get("subscription_type")
            event_types = data.get("event_types", [])
            filters = data.get("filters", {})

            # 验证事件类型
            valid_event_types = []
            for event_type_str in event_types:
                try:
                    event_type = EventType(event_type_str)
                    valid_event_types.append(event_type)
                except ValueError:
                    self.logger.warning(f"Invalid event type: {event_type_str}")

            # 创建订阅
            success_count = 0
            for event_type in valid_event_types:
                if self.subscription_manager.subscribe(
                    connection_id, event_type, filters, subscription_type
                ):
                    success_count += 1

            # 发送订阅结果
            result_event = RealtimeEvent(
                event_type=EventType.USER_SUBSCRIPTION_CHANGED,
                data={
                    "action": "subscribe",
                    "success": success_count > 0,
                    "subscribed_count": success_count,
                    "requested_count": len(valid_event_types),
                    "event_types": [et.value for et in valid_event_types],
                },
                source="websocket_handler",
            )
            await self.manager.send_to_connection(connection_id, result_event)

            self.logger.info(
                f"Connection {connection_id} subscribed to {success_count} event types"
            )

        except Exception as e:
            self.logger.error(f"Error handling subscribe: {e}")

    async def _handle_unsubscribe(self, connection_id: str, data: Dict[str, Any]) -> None:
        """处理取消订阅请求"""
        try:
            event_types = data.get("event_types", [])

            success_count = 0
            for event_type_str in event_types:
                try:
                    event_type = EventType(event_type_str)
                    if self.subscription_manager.unsubscribe(connection_id, event_type):
                        success_count += 1
                except ValueError:
                    self.logger.warning(f"Invalid event type: {event_type_str}")

            # 发送取消订阅结果
            result_event = RealtimeEvent(
                event_type=EventType.USER_SUBSCRIPTION_CHANGED,
                data={
                    "action": "unsubscribe",
                    "success": success_count > 0,
                    "unsubscribed_count": success_count,
                    "requested_count": len(event_types),
                    "event_types": event_types,
                },
                source="websocket_handler",
            )
            await self.manager.send_to_connection(connection_id, result_event)

            self.logger.info(
                f"Connection {connection_id} unsubscribed from {success_count} event types"
            )

        except Exception as e:
            self.logger.error(f"Error handling unsubscribe: {e}")

    async def _handle_heartbeat(self, connection_id: str) -> None:
        """处理心跳消息"""
        heartbeat_event = RealtimeEvent(
            event_type=EventType.CONNECTION_STATUS,
            data={
                "connection_id": connection_id,
                "status": "alive",
                "timestamp": "pong",
            },
            source="websocket_handler",
        )
        await self.manager.send_to_connection(connection_id, heartbeat_event)

    async def _handle_get_stats(self, connection_id: str) -> None:
        """处理获取统计信息请求"""
        stats = self.manager.get_stats()
        stats_event = RealtimeEvent(
            event_type=EventType.SYSTEM_STATUS, data=stats, source="websocket_handler"
        )
        await self.manager.send_to_connection(connection_id, stats_event)

    async def _handle_get_subscriptions(self, connection_id: str) -> None:
        """处理获取订阅信息请求"""
        subscriptions = self.subscription_manager.get_connection_subscriptions(connection_id)
        subscriptions_event = RealtimeEvent(
            event_type=EventType.USER_SUBSCRIPTION_CHANGED,
            data={"action": "list", "subscriptions": subscriptions},
            source="websocket_handler",
        )
        await self.manager.send_to_connection(connection_id, subscriptions_event)

    async def handle_disconnection(self, connection_id: str) -> None:
        """处理连接断开"""
        try:
            await self.manager.disconnect(connection_id)
            self.logger.info(f"WebSocket connection closed: {connection_id}")
        except Exception as e:
            self.logger.error(f"Error handling disconnection: {e}")


class WebSocketEndpoint:
    """WebSocket端点"""

    def __init__(self):
        self.handler = WebSocketHandler()
        self.logger = logging.getLogger(f"{__name__}.WebSocketEndpoint")

    async def endpoint(
        self,
        websocket: WebSocket,
        user_id: Optional[str] = Query(None),
        session_id: Optional[str] = Query(None),
        token: Optional[str] = Query(None),
    ) -> None:
        """WebSocket端点处理"""
        connection_id = None

        try:
            connection_id = await self.handler.handle_connection(websocket, user_id, session_id)

            # 消息处理循环
            while True:
                try:
                    # 接收消息
                    message = await websocket.receive_text()
                    message_data = json.loads(message) if message else {}

                    # 处理消息
                    await self.handler.handle_message(connection_id, message_data)

                except WebSocketDisconnect:
                    break
                except json.JSONDecodeError:
                    self.logger.warning(f"Invalid JSON received from {connection_id}")
                except Exception as e:
                    self.logger.error(f"Error processing message: {e}")

        except WebSocketDisconnect:
            self.logger.info(f"Client disconnected: {connection_id}")
        except Exception as e:
            self.logger.error(f"WebSocket error: {e}")
        finally:
            if connection_id:
                await self.handler.handle_disconnection(connection_id)


# 全局端点实例
_websocket_endpoint = WebSocketEndpoint()


def get_websocket_endpoint() -> WebSocketEndpoint:
    """获取WebSocket端点实例"""
    return _websocket_endpoint


# 便捷订阅处理函数
async def handle_quick_subscribe(
    connection_id: str, subscribe_to: str, params: Optional[Dict[str, Any]] = None
) -> bool:
    """处理快速订阅"""
    params = params or {}
    success = False

    if subscribe_to == "predictions":
        success = subscribe_to_predictions(
            connection_id, params.get("match_ids"), params.get("min_confidence")
        )
    elif subscribe_to == "matches":
        success = subscribe_to_matches(
            connection_id, params.get("match_ids"), params.get("leagues")
        )
    elif subscribe_to == "odds":
        success = subscribe_to_odds(
            connection_id, params.get("match_ids"), params.get("bookmakers")
        )

    return success
