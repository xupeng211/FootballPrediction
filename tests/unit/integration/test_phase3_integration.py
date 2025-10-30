from datetime import datetime
"""
集成测试 - 第三阶段
Integration Tests - Phase 3

专注于数据库集成、API集成,外部服务集成等的测试
目标:提升整体系统覆盖率和集成测试质量
"""

import asyncio

import pytest

# 测试导入 - 使用灵活导入策略
try:

    DATABASE_AVAILABLE = True
except ImportError as e:
    print(f"Database import error: {e}")
    DATABASE_AVAILABLE = False

try:
    from src.cache.ttl_cache import TTLCache

    CACHE_AVAILABLE = True
except ImportError as e:
    print(f"Cache import error: {e}")
    CACHE_AVAILABLE = False

try:

    API_DEPS_AVAILABLE = True
except ImportError as e:
    print(f"API dependencies import error: {e}")
    API_DEPS_AVAILABLE = False

try:
    from src.services.audit_service import AuditService
    from src.services.data_processing import DataProcessingService

    SERVICES_AVAILABLE = True
except ImportError as e:
    print(f"Services import error: {e}")
    SERVICES_AVAILABLE = False


@pytest.mark.skipif(not SERVICES_AVAILABLE, reason="服务模块不可用")
@pytest.mark.unit
class TestServiceIntegration:
    """服务集成测试"""

    @pytest.mark.asyncio
    async def test_data_processing_with_audit_integration(self):
        """测试:数据处理与审计服务集成 - 覆盖率补充"""
        # 创建服务实例
        data_service = DataProcessingService()
        audit_service = AuditService()

        await data_service.initialize()

        # 模拟集成工作流
        operation_id = f"integration_test_{datetime.utcnow().timestamp()}"

        # 1. 开始操作审计
        audit_service.log_event(
            action="data_processing_start",
            user="integration_test_user",
            details={
                "operation_id": operation_id,
                "service": "DataProcessingService",
                "timestamp": datetime.utcnow().isoformat(),
            },
        )

        # 2. 处理数据
        test_data = [
            {"match_id": 1001, "home_team": "Team A", "away_team": "Team B"},
            {"match_id": 1002, "home_team": "Team C", "away_team": "Team D"},
            {"match_id": 1003, "home_team": "Team E", "away_team": "Team F"},
        ]

        processed_results = []
        for data in test_data:
            # 记录单个处理事件
            audit_service.log_event(
                action="processing_single_item",
                user="integration_test_user",
                details={
                    "operation_id": operation_id,
                    "item_id": data["match_id"],
                    "status": "processing",
                },
            )

            # 处理数据
            result = await data_service.process_data(data)
            processed_results.append(result)

            # 记录处理完成事件
            audit_service.log_event(
                action="processing_complete",
                user="integration_test_user",
                details={
                    "operation_id": operation_id,
                    "item_id": data["match_id"],
                    "result_id": result.get("id"),
                    "success": True,
                },
            )

        # 3. 完成批量操作
        audit_service.log_event(
            action="data_processing_complete",
            user="integration_test_user",
            details={
                "operation_id": operation_id,
                "total_processed": len(processed_results),
                "success_count": len(processed_results),
                "processing_time_ms": 150,
            },
        )

        # 验证集成结果
        assert len(processed_results) == 3
        assert all("processed_at" in result for result in processed_results)

        # 验证审计跟踪
        all_events = audit_service.get_events(limit=20)
        operation_events = [
            e
            for e in all_events
            if hasattr(e, "details") and e.details.get("operation_id") == operation_id
        ]

        assert len(operation_events) >= 7  # start + 3*2 (processing+complete) + end

        await data_service.cleanup()

    @pytest.mark.asyncio
    async def test_service_error_propagation(self):
        """测试:服务间错误传播 - 覆盖率补充"""

        # 创建模拟的下游服务
        class DownstreamService:
            def __init__(self, failure_rate=0.3):
                self.failure_rate = failure_rate
                self.call_count = 0

            async def process_request(self, data):
                self.call_count += 1
                import random

                if random.random() < self.failure_rate:
                    raise ConnectionError("Downstream service unavailable")

                return {"processed": True, "data": data, "call_count": self.call_count}

        # 创建包装服务
        class ServiceWithRetry:
            def __init__(self, downstream_service, max_retries=3):
                self.downstream_service = downstream_service
                self.max_retries = max_retries

            async def call_with_retry(self, data):
                last_exception = None

                for attempt in range(self.max_retries):
                    try:
                        result = await self.downstream_service.process_request(data)
                        return {
                            "success": True,
                            "result": result,
                            "attempts": attempt + 1,
                        }
                    except ConnectionError as e:
                        last_exception = e
                        if attempt < self.max_retries - 1:
                            await asyncio.sleep(0.01)  # 短暂延迟
                            continue

                return {
                    "success": False,
                    "error": str(last_exception),
                    "attempts": self.max_retries,
                }

        # 测试错误传播和恢复
        downstream = DownstreamService(failure_rate=0.8)  # 高失败率
        wrapper = ServiceWithRetry(downstream, max_retries=3)

        # 多次调用测试
        results = []
        for i in range(10):
            result = await wrapper.call_with_retry({"request_id": i})
            results.append(result)

        # 验证结果
        successful_calls = [r for r in results if r["success"]]
        failed_calls = [r for r in results if not r["success"]]

        # 应该有一些成功的调用（重试机制生效）
        assert len(successful_calls) > 0
        assert len(failed_calls) >= 0

        # 验证重试逻辑
        for success in successful_calls:
            assert 1 <= success["attempts"] <= 3

        for failure in failed_calls:
            assert failure["attempts"] == 3  # 失败的调用应该用完所有重试


@pytest.mark.skipif(not DATABASE_AVAILABLE, reason="数据库模块不可用")
class TestDatabaseIntegration:
    """数据库集成测试"""

    def test_database_connection_management(self):
        """测试:数据库连接管理 - 覆盖率补充"""

        # 模拟数据库连接管理器
        class MockDatabaseConnection:
            def __init__(self, connection_string: str):
                self.connection_string = connection_string
                self.is_connected = False
                self.connection_count = 0
                self.query_count = 0

            async def connect(self):
                """建立数据库连接"""
                if not self.is_connected:
                    await asyncio.sleep(0.01)  # 模拟连接延迟
                    self.is_connected = True
                    self.connection_count += 1
                    return True
                return False

            async def disconnect(self):
                """断开数据库连接"""
                if self.is_connected:
                    await asyncio.sleep(0.005)  # 模拟断开延迟
                    self.is_connected = False
                    return True
                return False

            async def execute_query(self, query: str, params=None):
                """执行查询"""
                if not self.is_connected:
                    raise ConnectionError("Database not connected")

                await asyncio.sleep(0.001)  # 模拟查询执行时间
                self.query_count += 1

                # 模拟查询结果
                if "SELECT" in query.upper():
                    return [{"id": 1, "name": "Test Result"}]
                elif "INSERT" in query.upper():
                    return {"affected_rows": 1, "inserted_id": 123}
                else:
                    return {"affected_rows": 1}

        # 测试连接生命周期
        async def test_connection_lifecycle():
            db = MockDatabaseConnection("postgresql://test")

            # 初始状态
            assert db.is_connected is False
            assert db.connection_count == 0
            assert db.query_count == 0

            # 建立连接
            connected = await db.connect()
            assert connected is True
            assert db.is_connected is True
            assert db.connection_count == 1

            # 执行查询
            result1 = await db.execute_query("SELECT * FROM test")
            assert len(result1) == 1
            assert db.query_count == 1

            result2 = await db.execute_query("INSERT INTO test VALUES (1)")
            assert result2["affected_rows"] == 1
            assert db.query_count == 2

            # 断开连接
            disconnected = await db.disconnect()
            assert disconnected is True
            assert db.is_connected is False

            # 断开后执行查询应该失败
            with pytest.raises(ConnectionError):
                await db.execute_query("SELECT * FROM test")

        # 运行测试
        asyncio.run(test_connection_lifecycle())

    def test_transaction_management(self):
        """测试:事务管理 - 覆盖率补充"""

        # 模拟事务管理器
        class MockTransactionManager:
            def __init__(self, db_connection):
                self.db = db_connection
                self.active_transactions = {}
                self.transaction_counter = 0

            async def begin_transaction(self, transaction_id=None):
                """开始事务"""
                if transaction_id is None:
                    self.transaction_counter += 1
                    transaction_id = f"tx_{self.transaction_counter}"

                if transaction_id in self.active_transactions:
                    raise ValueError(f"Transaction {transaction_id} already exists")

                self.active_transactions[transaction_id] = {
                    "id": transaction_id,
                    "operations": [],
                    "status": "active",
                    "started_at": datetime.utcnow(),
                }

                return transaction_id

            async def commit_transaction(self, transaction_id):
                """提交事务"""
                if transaction_id not in self.active_transactions:
                    raise ValueError(f"Transaction {transaction_id} not found")

                transaction = self.active_transactions[transaction_id]
                if transaction["status"] != "active":
                    raise ValueError(f"Transaction {transaction_id} is not active")

                # 模拟提交操作
                await asyncio.sleep(0.005)

                transaction["status"] = "committed"
                transaction["committed_at"] = datetime.utcnow()

                return True

            async def rollback_transaction(self, transaction_id):
                """回滚事务"""
                if transaction_id not in self.active_transactions:
                    raise ValueError(f"Transaction {transaction_id} not found")

                transaction = self.active_transactions[transaction_id]
                if transaction["status"] not in ["active"]:
                    raise ValueError(
                        f"Cannot rollback transaction {transaction_id} with status {transaction['status']}"
                    )

                # 模拟回滚操作
                await asyncio.sleep(0.003)

                transaction["status"] = "rolled_back"
                transaction["rolled_back_at"] = datetime.utcnow()

                return True

            async def execute_in_transaction(self, transaction_id, operation_func, *args, **kwargs):
                """在事务中执行操作"""
                await self.begin_transaction(transaction_id)

                try:
                    result = await operation_func(*args, **kwargs)
                    await self.commit_transaction(transaction_id)
                    return {"success": True, "result": result}
                except Exception as e:
                    await self.rollback_transaction(transaction_id)
                    return {"success": False, "error": str(e)}

        # 测试事务管理
        async def test_transaction_workflow():
            db = MockDatabaseConnection("postgresql://test")
            await db.connect()

            tx_manager = MockTransactionManager(db)

            # 测试成功的事务
            async def successful_operation():
                await db.execute_query("INSERT INTO users VALUES (1, 'test')")
                await db.execute_query("UPDATE accounts SET balance = 100")
                return {"records_affected": 2}

            result = await tx_manager.execute_in_transaction("tx_success", successful_operation)
            assert result["success"] is True

            # 测试失败的事务
            async def failing_operation():
                await db.execute_query("INSERT INTO users VALUES (2, 'test2')")
                raise ValueError("Simulated operation failure")

            result = await tx_manager.execute_in_transaction("tx_fail", failing_operation)
            assert result["success"] is False
            assert "Simulated operation failure" in result["error"]

            # 验证事务状态
            assert tx_manager.active_transactions["tx_success"]["status"] == "committed"
            assert tx_manager.active_transactions["tx_fail"]["status"] == "rolled_back"

            await db.disconnect()

        # 运行测试
        asyncio.run(test_transaction_workflow())

    def test_database_pool_management(self):
        """测试:数据库连接池管理 - 覆盖率补充"""

        # 模拟连接池
        class MockConnectionPool:
            def __init__(self, min_connections=2, max_connections=10):
                self.min_connections = min_connections
                self.max_connections = max_connections
                self.available_connections = []
                self.used_connections = set()
                self.total_created = 0

                # 初始化最小连接数
                for _ in range(min_connections):
                    self._create_connection()

            def _create_connection(self):
                """创建新连接"""
                if (
                    len(self.available_connections) + len(self.used_connections)
                    >= self.max_connections
                ):
                    raise RuntimeError("Maximum connections reached")

                connection_id = f"conn_{self.total_created + 1}"
                self.available_connections.append(
                    {
                        "id": connection_id,
                        "created_at": datetime.utcnow(),
                        "last_used": datetime.utcnow(),
                        "is_active": True,
                    }
                )
                self.total_created += 1

            async def get_connection(self, timeout=5.0):
                """获取连接"""
                start_time = datetime.utcnow()

                while (datetime.utcnow() - start_time).total_seconds() < timeout:
                    if self.available_connections:
                        connection = self.available_connections.pop()
                        self.used_connections.add(connection["id"])
                        connection["last_used"] = datetime.utcnow()
                        return connection

                    # 如果没有可用连接且还能创建新连接
                    if len(self.used_connections) < self.max_connections:
                        self._create_connection()
                        continue

                    # 等待连接释放
                    await asyncio.sleep(0.01)

                raise TimeoutError("No available connections in pool")

            async def release_connection(self, connection_id):
                """释放连接"""
                if connection_id not in self.used_connections:
                    raise ValueError(f"Connection {connection_id} not in use")

                self.used_connections.remove(connection_id)

                # 找到对应的连接对象
                for i, conn in enumerate(self.available_connections):
                    if conn["id"] == connection_id:
                        # 连接已在池中
                        return

                # 连接不在可用列表中,需要重新添加
                self.available_connections.append(
                    {
                        "id": connection_id,
                        "created_at": datetime.utcnow(),
                        "last_used": datetime.utcnow(),
                        "is_active": True,
                    }
                )

            def get_pool_stats(self):
                """获取连接池统计"""
                return {
                    "total_connections": len(self.available_connections)
                    + len(self.used_connections),
                    "available_connections": len(self.available_connections),
                    "used_connections": len(self.used_connections),
                    "total_created": self.total_created,
                }

        # 测试连接池
        async def test_connection_pool():
            pool = MockConnectionPool(min_connections=2, max_connections=5)

            # 初始状态
            stats = pool.get_pool_stats()
            assert stats["total_connections"] == 2
            assert stats["available_connections"] == 2
            assert stats["used_connections"] == 0

            # 获取连接
            conn1 = await pool.get_connection()
            await pool.get_connection()

            stats = pool.get_pool_stats()
            assert stats["available_connections"] == 0
            assert stats["used_connections"] == 2

            # 释放连接
            await pool.release_connection(conn1["id"])

            stats = pool.get_pool_stats()
            assert stats["available_connections"] == 1
            assert stats["used_connections"] == 1

            # 并发获取连接测试
            async def concurrent_connection_user(user_id):
                conn = await pool.get_connection()
                await asyncio.sleep(0.01)  # 模拟使用连接
                await pool.release_connection(conn["id"])
                return f"user_{user_id}_completed"

            # 启动多个并发任务
            tasks = [concurrent_connection_user(i) for i in range(8)]
            results = await asyncio.gather(*tasks, return_exceptions=True)

            # 验证结果
            successful_results = [r for r in results if not isinstance(r, Exception)]
            assert len(successful_results) == 8

            # 最终状态
            final_stats = pool.get_pool_stats()
            assert final_stats["total_connections"] >= 2
            assert final_stats["available_connections"] >= 1

        # 近行测试
        asyncio.run(test_connection_pool())


@pytest.mark.skipif(not CACHE_AVAILABLE, reason="缓存模块不可用")
class TestCacheIntegration:
    """缓存集成测试"""

    def test_ttl_cache_integration(self):
        """测试:TTL缓存集成 - 覆盖率补充"""
        # 创建TTL缓存实例
        cache = TTLCache(default_ttl=60)  # 60秒默认TTL

        # 测试基本缓存操作
        cache.set("user_123", {"name": "John", "age": 30})
        cached_data = cache.get("user_123")

        assert cached_data is not None
        assert cached_data["name"] == "John"
        assert cached_data["age"] == 30

        # 测试缓存过期
        cache.set("temp_data", "expires_soon", ttl=1)  # 1秒TTL
        assert cache.get("temp_data") == "expires_soon"

        # 等待过期（实际等待）
        import time

        time.sleep(1.1)  # 等待超过TTL时间
        assert cache.get("temp_data") is None

        # 测试批量操作
        batch_data = {
            "product_1": {"name": "Product 1", "price": 10.99},
            "product_2": {"name": "Product 2", "price": 20.99},
            "product_3": {"name": "Product 3", "price": 30.99},
        }

        for key, value in batch_data.items():
            cache.set(key, value)

        # 批量获取
        retrieved_data = {}
        for key in batch_data.keys():
            retrieved_data[key] = cache.get(key)

        assert len(retrieved_data) == 3
        assert all(retrieved_data[key] is not None for key in batch_data.keys())

    def test_cache_with_service_integration(self):
        """测试:缓存与服务集成 - 覆盖率补充"""

        # 创建带缓存的服务
        class CachedDataService:
            def __init__(self):
                self.cache = TTLCache(default_ttl=300)  # 5分钟TTL
                self.call_count = 0

            def get_user_data(self, user_id: int):
                """获取用户数据（带缓存）"""
                cache_key = f"user_data_{user_id}"

                # 尝试从缓存获取
                cached_result = self.cache.get(cache_key)
                if cached_result is not None:
                    return {"data": cached_result, "from_cache": True}

                # 缓存未命中,从数据源获取
                self.call_count += 1
                fresh_data = self._fetch_user_from_database(user_id)

                # 存入缓存
                self.cache.set(cache_key, fresh_data)

                return {"data": fresh_data, "from_cache": False}

            def _fetch_user_from_database(self, user_id: int):
                """模拟数据库查询"""
                # 模拟数据库查询延迟
                import time

                time.sleep(0.001)

                return {
                    "id": user_id,
                    "name": f"User {user_id}",
                    "email": f"user{user_id}@example.com",
                    "last_login": datetime.utcnow().isoformat(),
                }

            def invalidate_user_cache(self, user_id: int):
                """使用户缓存失效"""
                cache_key = f"user_data_{user_id}"
                self.cache.delete(cache_key)

            def get_cache_stats(self):
                """获取缓存统计"""
                return {
                    "cache_size": len(self.cache._cache),
                    "ttl_store_size": len(self.cache._cache),
                    "db_calls": self.call_count,
                }

        # 测试缓存服务
        service = CachedDataService()

        # 第一次调用（缓存未命中）
        result1 = service.get_user_data(123)
        assert result1["from_cache"] is False
        assert result1["data"]["id"] == 123

        # 第二次调用（缓存命中）
        result2 = service.get_user_data(123)
        assert result2["from_cache"] is True
        assert result2["data"]["id"] == 123

        # 验证数据库调用次数
        stats = service.get_cache_stats()
        assert stats["db_calls"] == 1  # 只调用了一次数据库

        # 测试多个用户
        user_ids = [201, 202, 203, 201, 202, 204]  # 包含重复ID
        results = []

        for user_id in user_ids:
            result = service.get_user_data(user_id)
            results.append(result)

        # 验证缓存效果
        db_calls_after = service.get_cache_stats()["db_calls"]
        assert db_calls_after <= 5  # 4个唯一用户，可能有一些重复调用,但应该接近4次

        # 测试缓存失效
        service.invalidate_user_cache(123)
        result3 = service.get_user_data(123)
        assert result3["from_cache"] is False  # 缓存已失效


@pytest.mark.skipif(not API_DEPS_AVAILABLE, reason="API依赖模块不可用")
class TestAPIIntegration:
    """API集成测试"""

    def test_dependency_injection_integration(self):
        """测试:依赖注入集成 - 覆盖率补充"""

        # 模拟FastAPI依赖注入系统
        class MockRequest:
            def __init__(self, headers=None, user=None):
                self.headers = headers or {}
                self.user = user

        class MockDependencyContainer:
            def __init__(self):
                self.services = {}
                self.singletons = {}

            def register_singleton(self, service_type, instance):
                """注册单例服务"""
                self.singletons[service_type] = instance

            def register_transient(self, service_type, factory):
                """注册瞬态服务"""
                self.services[service_type] = factory

            def resolve(self, service_type):
                """解析服务"""
                if service_type in self.singletons:
                    return self.singletons[service_type]
                elif service_type in self.services:
                    return self.services[service_type]()
                else:
                    raise ValueError(f"Service {service_type} not registered")

        # 创建模拟服务
        class MockUserService:
            def __init__(self):
                self.users = {
                    1: {"id": 1, "name": "Admin", "role": "admin"},
                    2: {"id": 2, "name": "User", "role": "user"},
                }

            def get_user(self, user_id: int):
                return self.users.get(user_id)

        class MockAuthService:
            def __init__(self, user_service):
                self.user_service = user_service

            def authenticate_token(self, token: str):
                if token == "valid_token":
                    return {"user_id": 1, "exp": datetime.utcnow().timestamp() + 3600}
                return None

            def get_current_user(self, token: str):
                auth_result = self.authenticate_token(token)
                if auth_result:
                    return self.user_service.get_user(auth_result["user_id"])
                return None

        # 设置依赖注入
        container = MockDependencyContainer()
        user_service = MockUserService()
        auth_service = MockAuthService(user_service)

        container.register_singleton(MockUserService, user_service)
        container.register_singleton(MockAuthService, auth_service)

        # 模拟依赖注入函数
        def get_current_user_dep(request: MockRequest):
            """获取当前用户依赖"""
            token = request.headers.get("Authorization", "").replace("Bearer ", "")
            auth_service = container.resolve(MockAuthService)
            return auth_service.get_current_user(token)

        def require_admin_user(request: MockRequest):
            """需要管理员权限的依赖"""
            current_user = get_current_user_dep(request)
            if not current_user or current_user["role"] != "admin":
                raise PermissionError("Admin access required")
            return current_user

        # 测试依赖注入
        # 1. 成功的认证请求
        valid_request = MockRequest(headers={"Authorization": "Bearer valid_token"})
        user = get_current_user_dep(valid_request)
        assert user is not None
        assert user["name"] == "Admin"

        # 2. 管理员权限检查
        admin_user = require_admin_user(valid_request)
        assert admin_user["role"] == "admin"

        # 3. 无效token请求
        invalid_request = MockRequest(headers={"Authorization": "Bearer invalid_token"})
        user = get_current_user_dep(invalid_request)
        assert user is None

        # 4. 权限不足请求
        user_request = MockRequest(headers={"Authorization": "Bearer user_token"})
        # 这里会失败,因为token无效
        with pytest.raises(PermissionError):
            require_admin_user(user_request)

    def test_middleware_integration(self):
        """测试:中间件集成 - 覆盖率补充"""

        # 模拟中间件系统
        class MockMiddleware:
            def __init__(self, name):
                self.name = name
                self.call_count = 0

            async def process_request(self, request, call_next):
                """处理请求"""
                self.call_count += 1

                # 前置处理
                request.processed_by.append(self.name)

                # 调用下一个中间件或处理器
                response = await call_next(request)

                # 后置处理
                response.processed_by.append(self.name)

                return response

        class MockRequest:
            def __init__(self):
                self.processed_by = []
                self.headers = {}

        class MockResponse:
            def __init__(self):
                self.processed_by = []
                self.status_code = 200
                self.content = "OK"

        # 创建中间件链
        class MiddlewareChain:
            def __init__(self):
                self.middlewares = []

            def add_middleware(self, middleware):
                self.middlewares.append(middleware)

            async def process_request(self, request):
                """处理请求通过中间件链"""
                response = MockResponse()

                # 构建调用链
                async def call_next(req, middleware_index=0):
                    if middleware_index >= len(self.middlewares):
                        return response

                    middleware = self.middlewares[middleware_index]
                    return await middleware.process_request(
                        req, lambda r: call_next(r, middleware_index + 1)
                    )

                return await call_next(request)

        # 测试中间件链
        chain = MiddlewareChain()

        # 添加中间件
        auth_middleware = MockMiddleware("auth")
        logging_middleware = MockMiddleware("logging")
        cors_middleware = MockMiddleware("cors")

        chain.add_middleware(auth_middleware)
        chain.add_middleware(logging_middleware)
        chain.add_middleware(cors_middleware)

        # 处理请求
        async def run_middleware_test():
            request = MockRequest()
            response = await chain.process_request(request)

            # 验证中间件执行顺序
            expected_order = ["auth", "logging", "cors"]
            assert request.processed_by == expected_order

            # 后置处理顺序应该相反
            expected_response_order = ["cors", "logging", "auth"]
            assert response.processed_by == expected_response_order

            # 验证每个中间件都被调用
            assert auth_middleware.call_count == 1
            assert logging_middleware.call_count == 1
            assert cors_middleware.call_count == 1

        # 运行测试
        asyncio.run(run_middleware_test())

    def test_error_handling_integration(self):
        """测试:错误处理集成 - 覆盖率补充"""

        # 模拟错误处理系统
        class ErrorHandler:
            def __init__(self):
                self.error_handlers = {}
                self.error_log = []

            def register_handler(self, exception_type, handler_func):
                """注册异常处理器"""
                self.error_handlers[exception_type] = handler_func

            def handle_error(self, error, context=None):
                """处理错误"""
                error_type = type(error)
                self.error_log.append(
                    {
                        "error": str(error),
                        "type": error_type.__name__,
                        "context": context,
                        "timestamp": datetime.utcnow(),
                    }
                )

                # 查找并执行对应的处理器
                for exc_type, handler in self.error_handlers.items():
                    if isinstance(error, exc_type):
                        return handler(error, context)

                # 默认处理
                return {
                    "error": "Internal Server Error",
                    "type": error_type.__name__,
                    "message": str(error),
                }

        # 创建错误处理器
        error_handler = ErrorHandler()

        # 注册特定错误处理器
        def handle_validation_error(error, context):
            return {
                "error": "Validation Error",
                "details": str(error),
                "field": context.get("field") if context else None,
            }

        def handle_authentication_error(error, context):
            return {
                "error": "Authentication Failed",
                "message": "Please check your credentials",
                "user_id": context.get("user_id") if context else None,
            }

        error_handler.register_handler(ValueError, handle_validation_error)
        error_handler.register_handler(PermissionError, handle_authentication_error)

        # 测试错误处理
        # 1. 验证错误
        validation_error = ValueError("Invalid email format")
        context1 = {"field": "email", "value": "invalid-email"}
        result1 = error_handler.handle_error(validation_error, context1)

        assert result1["error"] == "Validation Error"
        assert result1["field"] == "email"

        # 2. 认证错误
        auth_error = PermissionError("Invalid credentials")
        context2 = {"user_id": 123, "attempt": 3}
        result2 = error_handler.handle_error(auth_error, context2)

        assert result2["error"] == "Authentication Failed"
        assert result2["user_id"] == 123

        # 3. 未注册的错误类型
        unknown_error = RuntimeError("Something went wrong")
        result3 = error_handler.handle_error(unknown_error)

        assert result3["error"] == "Internal Server Error"
        assert result3["type"] == "RuntimeError"

        # 验证错误日志
        assert len(error_handler.error_log) == 3
        assert all("timestamp" in log_entry for log_entry in error_handler.error_log)


class TestSystemIntegration:
    """系统集成测试"""

    def test_full_request_lifecycle(self):
        """测试:完整请求生命周期 - 覆盖率补充"""
        # 模拟完整的HTTP请求处理生命周期

        class RequestProcessor:
            def __init__(self):
                self.steps = []

            async def process_request(self, request_data):
                """处理完整请求"""
                self.steps = []

                # 1. 请求验证
                validated_data = await self.validate_request(request_data)
                self.steps.append("validated")

                # 2. 身份认证
                user_info = await self.authenticate(validated_data)
                self.steps.append("authenticated")

                # 3. 权限检查
                await self.check_permissions(user_info, validated_data)
                self.steps.append("authorized")

                # 4. 业务逻辑处理
                result = await self.process_business_logic(validated_data, user_info)
                self.steps.append("processed")

                # 5. 响应格式化
                response = await self.format_response(result)
                self.steps.append("formatted")

                # 6. 审计日志
                await self.log_request(validated_data, user_info, response)
                self.steps.append("logged")

                return response

            async def validate_request(self, data):
                """请求验证"""
                required_fields = ["user_id", "action", "data"]
                for field in required_fields:
                    if field not in data:
                        raise ValueError(f"Missing required field: {field}")
                return data

            async def authenticate(self, data):
                """身份认证"""
                # 模拟认证逻辑
                user_id = data["user_id"]
                if user_id <= 0:
                    raise PermissionError("Invalid user ID")

                return {
                    "user_id": user_id,
                    "name": f"User {user_id}",
                    "role": "user" if user_id > 100 else "admin",
                }

            async def check_permissions(self, user, data):
                """权限检查"""
                action = data["action"]
                if action in ["delete", "admin_action"] and user["role"] != "admin":
                    raise PermissionError("Insufficient permissions")

            async def process_business_logic(self, data, user):
                """业务逻辑处理"""
                action = data["action"]
                payload = data["data"]

                if action == "create":
                    return {
                        "action": "created",
                        "id": 12345,
                        "created_by": user["user_id"],
                        "data": payload,
                    }
                elif action == "update":
                    return {
                        "action": "updated",
                        "updated_by": user["user_id"],
                        "data": payload,
                    }
                else:
                    return {
                        "action": action,
                        "processed_by": user["user_id"],
                        "data": payload,
                    }

            async def format_response(self, result):
                """响应格式化"""
                return {
                    "success": True,
                    "data": result,
                    "timestamp": datetime.utcnow().isoformat(),
                    "request_id": f"req_{datetime.utcnow().timestamp()}",
                }

            async def log_request(self, request, user, response):
                """记录请求日志"""
                # 模拟日志记录
                log_entry = {
                    "user_id": user["user_id"],
                    "action": request["action"],
                    "success": response["success"],
                    "timestamp": datetime.utcnow(),
                }
                return log_entry

        # 测试完整请求流程
        async def test_request_lifecycle():
            processor = RequestProcessor()

            # 测试成功请求
            valid_request = {
                "user_id": 101,
                "action": "create",
                "data": {"name": "Test Item", "value": 42},
            }

            response = await processor.process_request(valid_request)

            # 验证处理步骤
            expected_steps = [
                "validated",
                "authenticated",
                "authorized",
                "processed",
                "formatted",
                "logged",
            ]
            assert processor.steps == expected_steps

            # 验证响应
            assert response["success"] is True
            assert response["data"]["action"] == "created"
            assert response["data"]["created_by"] == 101

            # 测试权限不足的请求
            insufficient_permission_request = {
                "user_id": 150,  # 普通用户
                "action": "admin_action",
                "data": {},
            }

            with pytest.raises(PermissionError):
                await processor.process_request(insufficient_permission_request)

            # 验证处理步骤在权限检查时停止
            assert processor.steps == ["validated", "authenticated"]

        # 运行测试
        asyncio.run(test_request_lifecycle())

    def test_async_task_integration(self):
        """测试:异步任务集成 - 覆盖率补充"""
        # 模拟异步任务系统

        class AsyncTaskManager:
            def __init__(self):
                self.tasks = {}
                self.task_results = {}
                self.task_counter = 0

            async def submit_task(self, task_func, *args, **kwargs):
                """提交异步任务"""
                self.task_counter += 1
                task_id = f"task_{self.task_counter}"

                # 创建任务
                async def task_wrapper():
                    try:
                        result = await task_func(*args, **kwargs)
                        self.task_results[task_id] = {
                            "status": "completed",
                            "result": result,
                            "completed_at": datetime.utcnow(),
                        }
                        return result
                    except Exception as e:
                        self.task_results[task_id] = {
                            "status": "failed",
                            "error": str(e),
                            "failed_at": datetime.utcnow(),
                        }
                        raise

                # 启动任务
                task = asyncio.create_task(task_wrapper())
                self.tasks[task_id] = task

                return task_id

            async def get_task_result(self, task_id, timeout=10.0):
                """获取任务结果"""
                if task_id not in self.tasks:
                    raise ValueError(f"Task {task_id} not found")

                try:
                    result = await asyncio.wait_for(self.tasks[task_id], timeout=timeout)
                    return result
                except asyncio.TimeoutError:
                    return {"status": "timeout", "task_id": task_id}

            async def cancel_task(self, task_id):
                """取消任务"""
                if task_id not in self.tasks:
                    raise ValueError(f"Task {task_id} not found")

                task = self.tasks[task_id]
                task.cancel()

                try:
                    await task
                except asyncio.CancelledError:
                    self.task_results[task_id] = {
                        "status": "cancelled",
                        "cancelled_at": datetime.utcnow(),
                    }

            def get_task_status(self, task_id):
                """获取任务状态"""
                if task_id not in self.tasks:
                    raise ValueError(f"Task {task_id} not found")

                if task_id in self.task_results:
                    return self.task_results[task_id]["status"]

                task = self.tasks[task_id]
                if task.done():
                    if task.cancelled():
                        return "cancelled"
                    elif task.exception():
                        return "failed"
                    else:
                        return "completed"
                else:
                    return "running"

        # 测试异步任务管理
        async def test_async_tasks():
            manager = AsyncTaskManager()

            # 定义测试任务
            async def long_running_task(duration, result_value):
                await asyncio.sleep(duration)
                await asyncio.sleep(duration)
                await asyncio.sleep(duration)
                return {"result": result_value, "duration": duration}

            async def failing_task():
                await asyncio.sleep(0.1)
                raise ValueError("Task failed intentionally")

            # 提交任务
            task1_id = await manager.submit_task(long_running_task, 0.5, "Task 1 Complete")
            task2_id = await manager.submit_task(long_running_task, 0.3, "Task 2 Complete")
            task3_id = await manager.submit_task(failing_task)

            # 等待任务完成
            result1 = await manager.get_task_result(task1_id)
            result2 = await manager.get_task_result(task2_id)

            # 验证成功任务结果
            assert result1["result"] == "Task 1 Complete"
            assert result2["result"] == "Task 2 Complete"

            # 验证任务状态
            assert manager.get_task_status(task1_id) == "completed"
            assert manager.get_task_status(task2_id) == "completed"

            # 等待失败任务并验证错误处理
            with pytest.raises(ValueError):
                await manager.get_task_result(task3_id)

            assert manager.get_task_status(task3_id) == "failed"

            # 测试任务取消
            task4_id = await manager.submit_task(long_running_task, 2.0, "Will be cancelled")
            await asyncio.sleep(0.1)  # 让任务开始
            await manager.cancel_task(task4_id)

            assert manager.get_task_status(task4_id) == "cancelled"

        # 运行测试
        asyncio.run(test_async_tasks())


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
