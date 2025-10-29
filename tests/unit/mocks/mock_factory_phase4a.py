"""
Phase 4A 简化版 Mock 工厂
为集成测试提供基础 Mock 对象
"""

import asyncio
import uuid
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, List, Optional
from unittest.mock import AsyncMock, Mock


@dataclass
class MockCacheConfig:
    """Mock缓存配置"""

    redis_url: str = "redis://localhost:6379/0"
    default_ttl: int = 3600
    max_connections: int = 10


class MockTransactionManager:
    """Mock事务管理器"""

    def __init__(self):
        self.transaction = Mock()
        self.transaction.commit = AsyncMock()
        self.transaction.rollback = AsyncMock()
        self.is_active = True

    async def begin(self):
        """开始事务"""
        return self.transaction

    async def commit(self):
        """提交事务"""
        await self.transaction.commit()

    async def rollback(self):
        """回滚事务"""
        await self.transaction.rollback()


class MockConnection:
    """Mock数据库连接"""

    def __init__(self, connection_id: str):
        self.connection_id = connection_id
        self.is_connected = True
        self.in_transaction = False
        self.transaction = None
        self.query_history = []

    async def execute(self, query: str, params: Dict = None):
        """执行查询"""
        if not self.is_connected:
            raise ConnectionError("Database connection is not active")

        self.query_history.append(
            {
                "query": query,
                "params": params or {},
                "timestamp": asyncio.get_event_loop().time(),
            }
        )

        # Mock返回结果
        if "SELECT" in query:
            return [
                {"id": 1, "username": "test_user"},
                {"id": 2, "username": "test_user2"},
            ]
        return {"affected_rows": 1}

    async def fetchall(self, query: str, params: Dict = None):
        """获取所有结果"""
        await self.execute(query, params)
        return [{"id": 1, "username": "test_user"}, {"id": 2, "username": "test_user2"}]

    async def fetchone(self, query: str, params: Dict = None):
        """获取单行结果"""
        await self.execute(query, params)
        return {"id": 1, "username": "test_user"}

    async def begin_transaction(self):
        """开始事务"""
        if self.in_transaction:
            raise RuntimeError("Transaction already active")
        self.in_transaction = True
        self.transaction = {"id": str(uuid.uuid4()), "state": "active"}

    async def commit(self):
        """提交事务"""
        if self.transaction:
            self.transaction["state"] = "committed"
        self.in_transaction = False
        self.transaction = None

    async def rollback(self):
        """回滚事务"""
        if self.transaction:
            self.transaction["state"] = "rolled_back"
        self.in_transaction = False
        self.transaction = None

    async def close(self):
        """关闭连接"""
        if self.in_transaction:
            await self.rollback()  # 关闭连接时回滚未提交的事务
        self.is_connected = False


class MockConnectionPool:
    """Mock连接池"""

    def __init__(self, max_connections: int = 10):
        self.max_connections = max_connections
        self.active_connections = []
        self.available_connections = []
        self.total_connections_created = 0
        self.is_shutdown = False

    async def get_connection(self, connection_id: str = None) -> MockConnection:
        """获取连接"""
        if self.is_shutdown:
            raise ConnectionError("Connection pool is shutdown")

        if len(self.active_connections) >= self.max_connections:
            # 模拟连接池耗尽，等待或超时
            await asyncio.sleep(0.001)  # 短暂等待
            if len(self.active_connections) >= self.max_connections:
                raise TimeoutError("Connection pool exhausted")

        if not connection_id:
            self.total_connections_created += 1
            connection_id = f"conn_{self.total_connections_created}"

        if self.available_connections:
            conn = self.available_connections.pop()
            # 重新激活连接
            conn.is_connected = True
        else:
            conn = MockConnection(connection_id)

        self.active_connections.append(conn)
        return conn

    async def release_connection(self, connection: MockConnection):
        """释放连接"""
        if connection in self.active_connections:
            self.active_connections.remove(connection)
            if not self.is_shutdown:
                self.available_connections.append(connection)

    def get_pool_stats(self) -> Dict:
        """获取连接池统计"""
        return {
            "active_connections": len(self.active_connections),
            "available_connections": len(self.available_connections),
            "max_connections": self.max_connections,
            "total_created": self.total_connections_created,
        }

    async def shutdown(self):
        """关闭连接池"""
        self.is_shutdown = True
        # 关闭所有连接
        for conn in self.active_connections + self.available_connections:
            await conn.close()
        self.active_connections.clear()
        self.available_connections.clear()


class MockRepository:
    """Mock仓储基类"""

    def __init__(self, connection: MockConnection = None):
        self.connection = connection or MockConnection("test_conn")
        self._data_store = {}

    async def create(self, data: Dict) -> Dict:
        """创建记录"""
        data["id"] = str(uuid.uuid4())
        data["created_at"] = datetime.utcnow().isoformat()
        self._data_store[data["id"]] = data.copy()
        return data

    async def get_by_id(self, id: str) -> Optional[Dict]:
        """根据ID获取记录"""
        return self._data_store.get(id)

    async def update(self, id: str, data: Dict) -> Dict:
        """更新记录"""
        if id in self._data_store:
            self._data_store[id].update(data)
            self._data_store[id]["updated_at"] = datetime.utcnow().isoformat()
            return self._data_store[id]
        return None

    async def delete(self, id: str) -> bool:
        """删除记录"""
        if id in self._data_store:
            del self._data_store[id]
            return True
        return False

    async def list(self, limit: int = 100, offset: int = 0) -> List[Dict]:
        """列出记录"""
        records = list(self._data_store.values())
        return records[offset : offset + limit]

    # 新增方法以满足测试需求
    async def find_with_filters(self, filters: Dict) -> List[Dict]:
        """根据过滤器查找记录"""
        return list(self._data_store.values())

    async def exists(self, id: str) -> bool:
        """检查记录是否存在"""
        return id in self._data_store

    async def find_paginated(self, page: int, per_page: int) -> Dict:
        """分页查找记录"""
        offset = (page - 1) * per_page
        records = list(self._data_store.values())[offset : offset + per_page]
        return {
            "records": records,
            "total": len(self._data_store),
            "page": page,
            "per_page": per_page,
        }

    async def bulk_create(self, entities: List[Dict]) -> List[Dict]:
        """批量创建记录"""
        results = []
        for entity in entities:
            result = await self.create(entity)
            results.append(result)
        return results

    # 添加缺失的方法以满足测试需求
    async def find_by_id(self, entity_id: Any) -> Optional[Dict]:
        """根据ID查找记录（别名方法）"""
        return await self.get_by_id(str(entity_id))

    async def find_all(self) -> List[Dict]:
        """查找所有记录（别名方法）"""
        return await self.list()

    async def count(self) -> int:
        """统计记录数量"""
        return len(self._data_store)


class MockDatabaseService:
    """Mock数据库服务"""

    def __init__(self):
        self.connection_pool = MockConnectionPool()
        self.transaction_manager = MockTransactionManager()
        self.is_running = True

    async def get_connection(self) -> MockConnection:
        """获取数据库连接"""
        return await self.connection_pool.get_connection()

    async def execute_query(self, query: str, params: Dict = None) -> List[Dict]:
        """执行查询"""
        conn = await self.get_connection()
        try:
            return await conn.fetchall(query, params)
        finally:
            await self.connection_pool.release_connection(conn)

    async def health_check(self) -> Dict:
        """健康检查"""
        return {
            "status": "healthy" if self.is_running else "shutdown",
            "connection_pool": self.connection_pool.get_pool_stats(),
            "timestamp": datetime.utcnow().isoformat(),
        }

    async def shutdown(self):
        """关闭数据库服务"""
        self.is_running = False
        await self.connection_pool.shutdown()


class Phase4AMockFactory:
    """Phase 4A 简化版 Mock 工厂"""

    @staticmethod
    def create_mock_gateway_service():
        """创建网关服务 Mock"""
        service = Mock()
        service.route_request = AsyncMock(
            return_value={"status": "success", "service": "mock_service"}
        )
        service.health_check = AsyncMock(return_value={"healthy": True})
        return service

    @staticmethod
    def create_mock_load_balancer():
        """创建负载均衡器 Mock"""
        balancer = Mock()
        balancer.select_service = AsyncMock(return_value={"service": "service_1", "load": 0.3})
        balancer.get_services = AsyncMock(
            return_value=[
                {"name": "service_1", "healthy": True, "load": 0.3},
                {"name": "service_2", "healthy": True, "load": 0.5},
            ]
        )
        return balancer

    @staticmethod
    def create_mock_database_service():
        """创建数据库服务 Mock"""
        service = Mock()
        service.initialize = AsyncMock(
            return_value={
                "success": True,
                "database_type": "postgresql",
                "connected": True,
            }
        )
        service.execute_query = AsyncMock(
            return_value={"success": True, "rows": [{"id": 1}], "execution_time": 0.002}
        )
        service.execute_batch = AsyncMock(return_value={"success": True, "results": [{"rows": []}]})
        service.health_check = AsyncMock(return_value={"healthy": True, "active_connections": 5})
        return service

    @staticmethod
    def create_mock_cache_service():
        """创建缓存服务 Mock"""
        service = Mock()
        service.get = AsyncMock(return_value={"success": True, "value": "cached_data"})
        service.set = AsyncMock(return_value={"success": True, "key": "test_key"})
        service.delete = AsyncMock(return_value={"success": True, "deleted": True})
        service.health_check = AsyncMock(return_value={"healthy": True, "memory_usage": "45%"})
        return service

    @staticmethod
    def create_mock_prediction_service():
        """创建预测服务 Mock"""
        service = Mock()
        service.predict = AsyncMock(
            return_value={
                "success": True,
                "prediction": {"home_win": 0.6, "draw": 0.3, "away_win": 0.1},
            }
        )
        service.get_prediction_history = AsyncMock(return_value={"predictions": [], "total": 0})
        service.health_check = AsyncMock(return_value={"healthy": True, "models_loaded": 5})
        return service

    @staticmethod
    def create_mock_auth_service():
        """创建认证服务 Mock"""
        service = Mock()
        service.login = AsyncMock(
            return_value={
                "success": True,
                "user_id": "mock_user",
                "token": "mock_token",
                "expires_in": 3600,
            }
        )
        service.logout = AsyncMock(return_value={"success": True, "message": "Session invalidated"})
        service.authenticate = AsyncMock(return_value={"success": True, "user_id": "mock_user"})
        service.validate_token = AsyncMock(return_value={"valid": True, "user_id": "mock_user"})
        return service

    @staticmethod
    def create_mock_notification_service():
        """创建通知服务 Mock"""
        service = Mock()
        service.send_notification = AsyncMock(
            return_value={"success": True, "notification_id": "notif_123"}
        )
        service.get_notifications = AsyncMock(return_value={"notifications": [], "unread_count": 0})
        service.mark_as_read = AsyncMock(return_value={"success": True, "marked_count": 1})
        return service

    @staticmethod
    def create_mock_monitoring_service():
        """创建监控服务 Mock"""
        service = Mock()
        service.get_metrics = AsyncMock(
            return_value={
                "cpu_usage": 45.2,
                "memory_usage": 67.8,
                "disk_usage": 23.4,
                "active_connections": 125,
                "response_time": 0.045,
            }
        )
        service.get_health_status = AsyncMock(return_value={"status": "healthy", "checks": []})
        service.get_logs = AsyncMock(return_value={"logs": [], "total": 0})
        return service

    @staticmethod
    def create_mock_data_collector_service():
        """创建数据收集服务 Mock"""
        service = Mock()
        service.collect_match_data = AsyncMock(
            return_value={"success": True, "matches_collected": 10}
        )
        service.collect_team_stats = AsyncMock(return_value={"success": True, "teams_updated": 20})
        service.process_live_data = AsyncMock(return_value={"success": True, "events_processed": 5})
        return service

    @staticmethod
    def create_mock_service_registry():
        """创建服务注册中心 Mock"""
        registry = Mock()
        registry.register_service = AsyncMock(
            return_value={"success": True, "service_id": "service_123"}
        )
        registry.discover_service = AsyncMock(
            return_value={"service": {"name": "test_service", "host": "localhost", "port": 8080}}
        )
        registry.get_all_services = AsyncMock(return_value={"services": []})
        registry.health_check = AsyncMock(return_value={"healthy": True, "registered_services": 15})
        return registry

    @staticmethod
    def create_mock_circuit_breaker():
        """创建熔断器 Mock"""
        circuit_breaker = Mock()
        circuit_breaker.call = AsyncMock(return_value={"success": True, "data": "mock_response"})
        circuit_breaker.get_state = Mock(return_value="CLOSED")
        circuit_breaker.is_open = Mock(return_value=False)
        return circuit_breaker

    @staticmethod
    def create_mock_rate_limiter():
        """创建限流器 Mock"""
        limiter = Mock()
        limiter.is_allowed = Mock(return_value=True)
        limiter.get_remaining_requests = Mock(return_value=95)
        limiter.get_reset_time = Mock(return_value=60)
        return limiter

    @staticmethod
    def create_mock_message_queue():
        """创建消息队列 Mock"""
        queue = Mock()
        queue.publish = AsyncMock(return_value={"success": True, "message_id": "msg_123"})
        queue.consume = AsyncMock(return_value={"message": {"type": "test", "data": {}}})
        queue.get_queue_size = Mock(return_value=10)
        queue.health_check = AsyncMock(return_value={"healthy": True, "consumers": 3})
        return queue

    @staticmethod
    def create_mock_cache_service():
        """创建缓存服务 Mock"""
        service = Mock()
        service.get = AsyncMock(return_value={"key": "test_key", "value": "test_value"})
        service.set = AsyncMock(return_value={"success": True, "key": "test_key"})
        service.delete = AsyncMock(return_value={"success": True, "key": "test_key"})
        service.clear = AsyncMock(return_value={"success": True, "cleared_keys": 10})
        service.health_check = AsyncMock(return_value={"healthy": True, "cache_size": "1MB"})
        return service

    @staticmethod
    def create_mock_database_service():
        """创建数据库服务 Mock"""
        service = Mock()
        service.query = AsyncMock(return_value={"success": True, "rows": 5, "data": []})
        service.execute = AsyncMock(return_value={"success": True, "affected_rows": 1})
        service.transaction = AsyncMock(return_value={"success": True, "transaction_id": "tx_123"})
        service.get_connection_info = Mock(return_value={"host": "localhost", "port": 5432})
        service.health_check = AsyncMock(return_value={"healthy": True, "connections": 10})
        return service

    @staticmethod
    def create_mock_redis_client():
        """创建Redis客户端 Mock"""
        client = Mock()
        client.get = AsyncMock(
            return_value={"key": "test_key", "value": "test_value", "exists": True}
        )
        client.set = AsyncMock(return_value={"success": True, "key": "test_key"})
        client.delete = AsyncMock(return_value={"success": True, "key": "test_key"})
        client.exists = AsyncMock(return_value=True)
        client.ping = AsyncMock(return_value={"status": "PONG"})
        client.info = Mock(return_value={"redis_version": "6.2.0", "used_memory": "1MB"})
        return client

    @staticmethod
    def create_mock_cache_service():
        """创建缓存服务 Mock"""
        cache = Mock()
        cache.set = AsyncMock(return_value=True)
        cache.get = AsyncMock(return_value=None)
        cache.exists = AsyncMock(return_value=False)
        cache.delete = AsyncMock(return_value=True)
        cache.clear = AsyncMock(return_value=True)
        cache.keys = AsyncMock(return_value=[])
        cache.increment = AsyncMock(return_value=1)
        cache.decrement = AsyncMock(return_value=1)
        cache.expire = AsyncMock(return_value=True)
        cache.ttl = AsyncMock(return_value=300)
        cache.info = Mock(
            return_value={
                "used_memory": "1MB",
                "used_memory_human": "1MB",
                "keys_count": 100,
            }
        )
        return cache

    @staticmethod
    def create_mock_repository():
        """创建仓储 Mock - 使用真实的MockRepository类"""
        return MockRepository()


# 创建直接的Mock实例以供导入
MockCacheService = Phase4AMockFactory.create_mock_cache_service()
MockRedisClient = Phase4AMockFactory.create_mock_redis_client()
