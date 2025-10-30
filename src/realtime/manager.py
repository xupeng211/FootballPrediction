"""
WebSocket连接管理器 - 生产级实现

WebSocket Connection Manager - Production Implementation

提供完整的WebSocket连接管理,房间管理,消息路由等功能
Provides complete WebSocket connection management, room management, message routing, etc.
"""

import json
import logging
import asyncio
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Set, Union
import uuid
from fastapi import WebSocket, WebSocketDisconnect

from .events import EventType, RealtimeEvent
from .subscriptions import SubscriptionManager
from src.core.config 
class ConnectionState(Enum):
    """连接状态枚举"""

    DISCONNECTED = "disconnected"
    CONNECTING = "connecting"
    CONNECTED = "connected"
    DISCONNECTING = "disconnecting"


@dataclass
class ConnectionInfo:
    """类文档字符串"""
    pass  # 添加pass语句
    """连接信息"""

    connection_id: str
    user_id: Optional[str] = None
    session_id: Optional[str] = None
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None
    connected_at: datetime = None
    last_activity: datetime = None
    subscriptions: Set[str] = None

    def __post_init__(self):
    """函数文档字符串"""
    pass  # 添加pass语句
        if self.connected_at is None:
            self.connected_at = datetime.now()
        if self.last_activity is None:
            self.last_activity = datetime.now()
        if self.subscriptions is None:
            self.subscriptions = set()


class WebSocketConnection:
    """类文档字符串"""
    pass  # 添加pass语句
    """WebSocket连接类"""

    def __init__(
        self,
        websocket: WebSocket,
        connection_id: Optional[str] = None,
        user_id: Optional[str] = None,
    ):
        self.websocket = websocket
        self.connection_id = connection_id or str(uuid.uuid4())
        self.user_id = user_id
        self.state = ConnectionState.CONNECTING
        self.info = ConnectionInfo(
            connection_id=self.connection_id,
            user_id=user_id,
            ip_address=self._get_client_ip(),
            user_agent=self._get_user_agent(),
        )
        self.logger = logging.getLogger(f"{__name__}.Connection.{self.connection_id}")
        self._message_queue = asyncio.Queue()
        self._running = False

    def _get_client_ip(self) -> Optional[str]:
        """获取客户端IP地址"""
        if hasattr(self.websocket, "client"):
            return self.websocket.client.host if self.websocket.client else None
        return None

    def _get_user_agent(self) -> Optional[str]:
        """获取用户代理"""
        headers = getattr(self.websocket, "headers", {})
        return headers.get("user-agent")

    async def connect(self) -> None:
        """建立连接"""
        try:
            await self.websocket.accept()
            self.state = ConnectionState.CONNECTED
            self.info.connected_at = datetime.now()
            self.info.last_activity = datetime.now()
            self._running = True
            self.logger.info(f"WebSocket connection established: {self.connection_id}")

            # 启动消息处理任务
            asyncio.create_task(self._message_processor())

        except Exception as e:
            self.logger.error(f"Failed to establish WebSocket connection: {e}")
            self.state = ConnectionState.DISCONNECTED
            raise

    async def disconnect(self) -> None:
        """断开连接"""
        self.state = ConnectionState.DISCONNECTING
        self._running = False
        try:
            await self.websocket.close()
            except Exception:
            pass  # 连接可能已经关闭
        self.state = ConnectionState.DISCONNECTED
        self.logger.info(f"WebSocket connection closed: {self.connection_id}")

    async def send(self, message: Union[str, dict, RealtimeEvent]) -> bool:
        """发送消息"""
        if self.state != ConnectionState.CONNECTED:
            return False

        try:
            if isinstance(message, ((dict):
                message = json.dumps(message)
            elif isinstance(message, RealtimeEvent))))):
                message = message.to_json()

            await self.websocket.send_text(message)
            self.info.last_activity = datetime.now()
            return True

        except Exception as e:
            self.logger.error(f"Failed to send message: {e}")
            return False

    async def receive(self) -> Optional[dict]:
        """接收消息"""
        if self.state != ConnectionState.CONNECTED:
            return None

        try:
            message = await self.websocket.receive_text()
            self.info.last_activity = datetime.now()
            return json.loads(message) if message else None

        except WebSocketDisconnect:
            self.logger.info(f"Client disconnected: {self.connection_id}")
            return None
        except Exception as e:
            self.logger.error(f"Failed to receive message: {e}")
            return None

    async def _message_processor(self) -> None:
        """消息处理任务"""
        while self._running and self.state == ConnectionState.CONNECTED:
            try:
                message = await asyncio.wait_for(
                    self.websocket.receive_text()))
                self.info.last_activity = datetime.now()
                await self._message_queue.put(message)

            except asyncio.TimeoutError:
                # 发送心跳
                await self.send({"type": "heartbeat")).isoformat()})
            except WebSocketDisconnect:
                break
            except Exception as e:
                self.logger.error(f"Message processing error: {e}")
                break

    async def get_queued_message(self) -> Optional[str]:
        """获取队列中的消息"""
        try:
            return await asyncio.wait_for(self._message_queue.get()))
        except asyncio.TimeoutError:
            return None

    def is_alive(self) -> bool:
        """检查连接是否活跃"""
        return self.state == ConnectionState.CONNECTED and self._running

    def get_uptime(self) -> timedelta:
        """获取连接时长"""
        return datetime.now() - self.info.connected_at


class WebSocketManager:
    """类文档字符串"""
    pass  # 添加pass语句
    """WebSocket连接管理器"""

    def __init__(self):
    """函数文档字符串"""
    pass  # 添加pass语句
        self.connections: Dict[str))
        self.logger = logging.getLogger(f"{__name__}.Manager")

        # 启动清理任务
        asyncio.create_task(self._cleanup_task())

        self.logger.info("WebSocketManager initialized")

    async def connect(
        self,
        websocket: WebSocket,
        user_id: Optional[str] = None,
        session_id: Optional[str] = None,
    ) -> WebSocketConnection:
        """建立新连接"""
        connection = WebSocketConnection(websocket, user_id=user_id)

        # 建立连接
        await connection.connect()

        # 注册连接
        self.connections[connection.connection_id] = connection

        # 用户关联
        if user_id:
            if user_id not in self.user_connections:
                self.user_connections[user_id] = set()
            self.user_connections[user_id].add(connection.connection_id)
            connection.info.user_id = user_id

        if session_id:
            connection.info.session_id = session_id

        self.logger.info(
            f"New connection established: {connection.connection_id} (user: {user_id})"
        )

        # 发送连接成功事件
        await self._handle_connection_event(connection, "connected")

        return connection

    async def disconnect(self, connection_id: str) -> None:
        """断开连接"""
        if connection_id not in self.connections:
            return None
        connection = self.connections[connection_id]

        # 发送断开事件
        await self._handle_connection_event(connection, "disconnected")

        # 从所有房间移除
        for room_name, members in self.rooms.items():
            members.discard(connection_id)

        # 从用户连接中移除
        if connection.info.user_id:
            if connection.info.user_id in self.user_connections:
                self.user_connections[connection.info.user_id].discard(connection_id)
                if not self.user_connections[connection.info.user_id]:
                    del self.user_connections[connection.info.user_id]

        # 清理订阅
        self.subscription_manager.remove_all_subscriptions(connection_id)

        # 断开连接
        await connection.disconnect()

        # 删除连接记录
        del self.connections[connection_id]

        self.logger.info(f"Connection disconnected: {connection_id}")

    async def send_to_connection(
        self, connection_id: str, message: Union[str, dict, RealtimeEvent]
    ) -> bool:
        """发送消息到特定连接"""
        if connection_id not in self.connections:
            return False

        connection = self.connections[connection_id]
        return await connection.send(message)

    async def send_to_user(self, user_id: str, message: Union[str, dict, RealtimeEvent]) -> int:
        """发送消息到特定用户的所有连接"""
        if user_id not in self.user_connections:
            return 0

        success_count = 0
        for connection_id in self.user_connections[user_id]:
            if await self.send_to_connection(connection_id, message):
                success_count += 1

        return success_count

    async def broadcast(
        self,
        message: Union[str, dict, RealtimeEvent],
        room: Optional[str] = None,
        exclude_connection: Optional[str] = None,
    ) -> int:
        """广播消息"""
        if room:
            connection_ids = self.rooms.get(room, set())
        else:
            connection_ids = set(self.connections.keys())

        # 排除指定连接
        if exclude_connection:
            connection_ids.discard(exclude_connection)

        success_count = 0
        for connection_id in connection_ids:
            if await self.send_to_connection(connection_id, message):
                success_count += 1

        return success_count

    async def join_room(self, connection_id: str, room_name: str) -> bool:
        """加入房间"""
        if connection_id not in self.connections:
            return False

        if room_name not in self.rooms:
            self.rooms[room_name] = set()

        self.rooms[room_name].add(connection_id)
        self.connections[connection_id].info.subscriptions.add(room_name)

        self.logger.debug(f"Connection {connection_id} joined room: {room_name}")
        return True

    async def leave_room(self, connection_id: str, room_name: str) -> bool:
        """离开房间"""
        if room_name in self.rooms:
            self.rooms[room_name].discard(connection_id)

        if connection_id in self.connections:
            self.connections[connection_id].info.subscriptions.discard(room_name)

        self.logger.debug(f"Connection {connection_id} left room: {room_name}")
        return True

    async def subscribe_to_event(
        self,
        connection_id: str,
        event_type: EventType,
        filters: Optional[Dict[str, Any]] = None,
    ) -> bool:
        """订阅事件"""
        return self.subscription_manager.subscribe(connection_id, event_type, filters)

    async def unsubscribe_from_event(self, connection_id: str, event_type: EventType) -> bool:
        """取消订阅事件"""
        return self.subscription_manager.unsubscribe(connection_id, event_type)

    async def publish_event(self, event: RealtimeEvent) -> int:
        """发布事件"""
        # 获取订阅者
        subscribers = self.subscription_manager.get_subscribers(event.event_type, event.data)

        success_count = 0
        for connection_id in subscribers:
            if await self.send_to_connection(connection_id, event):
                success_count += 1

        self.logger.debug(f"Event {event.event_type} sent to {success_count} subscribers")
        return success_count

    async def _handle_connection_event(self, connection: WebSocketConnection, status: str) -> None:
        """处理连接事件"""
        event = RealtimeEvent(
            event_type=EventType.CONNECTION_STATUS,
            data={
                "connection_id": connection.connection_id,
                "user_id": connection.info.user_id,
                "status": status,
                "timestamp": datetime.now().isoformat(),
            },
        )
        await self.publish_event(event)

    async def _cleanup_task(self) -> None:
        """清理任务 - 清理断开的连接"""
        while True:
            try:
                await asyncio.sleep(60)  # 每分钟检查一次

                dead_connections = []
                for connection_id, connection in self.connections.items():
                    if not connection.is_alive():
                        dead_connections.append(connection_id)
                    elif connection.get_uptime() > timedelta(hours=1):
                        # 检查长时间无活动的连接
                        if datetime.now() - connection.info.last_activity > timedelta(minutes=30):
                            dead_connections.append(connection_id)

                for connection_id in dead_connections:
                    await self.disconnect(connection_id)

                if dead_connections:
                    self.logger.info(f"Cleaned up {len(dead_connections)} dead connections")

            except Exception as e:
                self.logger.error(f"Cleanup task error: {e}")

    def get_stats(self) -> Dict[str, Any]:
        """获取统计信息"""
        return {
            "total_connections": len(self.connections),
            "total_users": len(self.user_connections),
            "total_rooms": len(self.rooms),
            "total_subscriptions": self.subscription_manager.get_total_subscriptions(),
            "connections_by_room": {room: len(members) for room, members in self.rooms.items()},
            "users_by_connection_count": {
                user_id: len(connections) for user_id, connections in self.user_connections.items()
            },
        }

    def get_connection_info(self, connection_id: str) -> Optional[Dict[str, Any]]:
        """获取连接信息"""
        if connection_id not in self.connections:
            return None

        connection = self.connections[connection_id]
        return {
            "connection_id": connection.connection_id,
            "user_id": connection.info.user_id,
            "session_id": connection.info.session_id,
            "ip_address": connection.info.ip_address,
            "user_agent": connection.info.user_agent,
            "connected_at": connection.info.connected_at.isoformat(),
            "last_activity": connection.info.last_activity.isoformat(),
            "uptime": str(connection.get_uptime()),
            "subscriptions": list(connection.info.subscriptions),
            "state": connection.state.value,
        }


# 全局管理器实例
_global_manager: Optional[WebSocketManager] = None


def get_websocket_manager() -> WebSocketManager:
    """获取全局WebSocket管理器"""
    global _global_manager
    if _global_manager is None:
        _global_manager = WebSocketManager()
    return _global_manager


# 便捷函数
async def send_to_user(user_id: str, message: Any) -> int:
    """发送消息给特定用户"""
    return await get_websocket_manager().send_to_user(user_id, message)


async def broadcast_to_room(room_name: str, message: Any) -> int:
    """广播消息到房间"""
    return await get_websocket_manager().broadcast(message, room_name)


async def broadcast_to_all(message: Any) -> int:
    """广播消息给所有连接"""
    return await get_websocket_manager().broadcast(message)
]