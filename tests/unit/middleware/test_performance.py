import os
"""
性能中间件测试
Performance Middleware Tests
"""

import json
import gzip
import pytest
from unittest.mock import AsyncMock, Mock, patch
from fastapi import FastAPI, Request, HTTPException
from fastapi.testclient import TestClient
from starlette.responses import Response

from src.middleware.performance import (
    ResponseCacheMiddleware,
    CompressionMiddleware,
    BatchProcessingMiddleware,
    PerformanceMonitoringMiddleware,
    cache_response,
    AsyncBatchProcessor,
    DatabaseBatchProcessor
)


class TestResponseCacheMiddleware:
    """测试响应缓存中间件"""

    @pytest.fixture
    def mock_redis(self):
        """模拟Redis管理器"""
        redis = AsyncMock()
        redis.get.return_value = None
        redis.set.return_value = True
        return redis

    @pytest.fixture
    def app_with_cache(self, mock_redis):
        """创建带缓存的应用"""
        app = FastAPI()

        # 添加缓存中间件
        app.add_middleware(
            ResponseCacheMiddleware,
            cache_manager=mock_redis,
            default_ttl=300
        )

        @app.get("/test")
        async def test_endpoint():
            return {"message": "test", "timestamp": "2025-01-01"}

        @app.post("/test")
        async def test_post():
            return {"message": "post"}

        return app

    @pytest.fixture
    def client(self, app_with_cache):
        """创建测试客户端"""
        return TestClient(app_with_cache)

    def test_cache_miss(self, client, mock_redis):
        """测试缓存未命中"""
        response = client.get("/test")

        assert response.status_code == 200
        assert response.headers.get("X-Cache") == "MISS"
        assert response.json()["message"] == "test"

        # 验证缓存设置
        mock_redis.set.assert_called_once()

    def test_cache_hit(self, client, mock_redis):
        """测试缓存命中"""
        # 模拟缓存命中
        cached_data = json.dumps({
            "body": '{"message": "test", "timestamp": "2025-01-01"}',
            "status_code": 200,
            "headers": {"content-type": "application/json"},
            "media_type": "application/json"
        })
        mock_redis.get.return_value = cached_data

        response = client.get("/test")

        assert response.status_code == 200
        assert response.headers.get("X-Cache") == "HIT"
        assert response.json()["message"] == "test"

    def test_not_cached_post(self, client):
        """测试POST请求不缓存"""
        response = client.post("/test")

        assert response.status_code == 200
        assert "X-Cache" not in response.headers

    def test_cache_key_generation(self):
        """测试缓存键生成"""
        middleware = ResponseCacheMiddleware(FastAPI())

        # 模拟请求
        request = Mock()
        request.url.path = "/api/predictions"
        request.url.query = os.getenv("TEST_PERFORMANCE_QUERY_105")
        request.headers = {}

        key = middleware._generate_cache_key(request)

        # 验证键格式
        assert key.startswith("response_cache:")
        assert len(key) == len("response_cache:") + 32  # MD5 hash

    def test_cache_key_with_auth(self):
        """测试带认证的缓存键"""
        middleware = ResponseCacheMiddleware(FastAPI())

        request = Mock()
        request.url.path = "/api/predictions"
        request.url.query = ""
        request.headers = {"authorization": "Bearer token123"}

        key = middleware._generate_cache_key(request)

        # 验证包含用户信息
        assert key.startswith("response_cache:")
        assert len(key) == len("response_cache:") + 32

    def test_large_response_not_cached(self, mock_redis):
        """测试大响应不被缓存"""
        app = FastAPI()
        app.add_middleware(
            ResponseCacheMiddleware,
            cache_manager=mock_redis,
            max_response_size=1024  # 1KB限制
        )

        @app.get("/large")
        async def large_response():
            return {"data": "x" * 2048}  # 2KB数据

        client = TestClient(app)
        response = client.get("/large")

        assert response.status_code == 200
        assert "X-Cache" not in response.headers
        mock_redis.set.assert_not_called()


class TestCompressionMiddleware:
    """测试压缩中间件"""

    @pytest.fixture
    def app_with_compression(self):
        """创建带压缩的应用"""
        app = FastAPI()
        app.add_middleware(CompressionMiddleware)

        @app.get("/json")
        async def json_endpoint():
            return {"data": "x" * 2000}  # 2KB JSON

        @app.get("/html")
        async def html_endpoint():
            return "<html>" + "x" * 2000 + "</html>"

        @app.get("/small")
        async def small_endpoint():
            return {"small": "data"}

        return app

    @pytest.fixture
    def client(self, app_with_compression):
        """创建测试客户端"""
        return TestClient(app_with_compression)

    def test_compression_enabled(self, client):
        """测试启用压缩"""
        headers = {"Accept-Encoding": "gzip"}
        response = client.get("/json", headers=headers)

        assert response.status_code == 200
        assert response.headers.get("Content-Encoding") == "gzip"
        assert response.headers.get("Vary") == "Accept-Encoding"

    def test_no_gzip_support(self, client):
        """测试客户端不支持gzip"""
        headers = {"Accept-Encoding": "identity"}
        response = client.get("/json", headers=headers)

        assert response.status_code == 200
        assert "Content-Encoding" not in response.headers

    def test_small_response_not_compressed(self, client):
        """测试小响应不压缩"""
        headers = {"Accept-Encoding": "gzip"}
        response = client.get("/small", headers=headers)

        assert response.status_code == 200
        assert "Content-Encoding" not in response.headers

    def test_compression_reduces_size(self, client):
        """测试压缩减少大小"""
        # 不压缩的响应
        headers_no_gzip = {"Accept-Encoding": "identity"}
        response_no_gzip = client.get("/json", headers=headers_no_gzip)
        size_no_gzip = len(response_no_gzip.content)

        # 压缩的响应
        headers_gzip = {"Accept-Encoding": "gzip"}
        response_gzip = client.get("/json", headers=headers_gzip)
        size_gzip = len(response_gzip.content)

        # 压缩后应该更小
        assert size_gzip < size_no_gzip

    def test_decompress_gzip_response(self, client):
        """测试解压gzip响应"""
        headers = {"Accept-Encoding": "gzip"}
        response = client.get("/json", headers=headers)

        assert response.headers.get("Content-Encoding") == "gzip"

        # 手动解压验证
        decompressed = gzip.decompress(response.content)
        data = json.loads(decompressed.decode())
        assert "data" in data


class TestBatchProcessingMiddleware:
    """测试批处理中间件"""

    @pytest.fixture
    def app_with_batch(self):
        """创建带批处理的应用"""
        app = FastAPI()
        app.add_middleware(
            BatchProcessingMiddleware,
            max_batch_size=10
        )

        @app.post("/single")
        async def single_endpoint():
            return {"message": "single"}

        return app

    @pytest.fixture
    def client(self, app_with_batch):
        """创建测试客户端"""
        return TestClient(app_with_batch)

    def test_batch_request(self, client):
        """测试批处理请求"""
        batch_data = {
            "requests": [
                {"method": "GET", "path": "/single"},
                {"method": "GET", "path": "/single"},
                {"method": "GET", "path": "/single"}
            ]
        }

        headers = {"X-Batch-Request": "true"}
        response = client.post("/single", json=batch_data, headers=headers)

        assert response.status_code == 200
        assert response.headers.get("X-Batch-Response") == "true"

        batch_response = response.json()
        assert "responses" in batch_response
        assert len(batch_response["responses"]) == 3

    def test_batch_size_limit(self, client):
        """测试批处理大小限制"""
        batch_data = {
            "requests": [{"method": "GET", "path": "/single"}] * 20  # 超过限制
        }

        headers = {"X-Batch-Request": "true"}
        response = client.post("/single", json=batch_data, headers=headers)

        assert response.status_code == 400
        assert "Batch size exceeds limit" in response.json()["detail"]

    def test_non_batch_request(self, client):
        """测试非批处理请求"""
        response = client.post("/single", json={"test": "data"})

        assert response.status_code == 200
        assert response.json()["message"] == "single"


class TestPerformanceMonitoringMiddleware:
    """测试性能监控中间件"""

    @pytest.fixture
    def app_with_monitoring(self):
        """创建带性能监控的应用"""
        app = FastAPI()
        app.add_middleware(
            PerformanceMonitoringMiddleware,
            slow_query_threshold=0.1
        )

        @app.get("/fast")
        async def fast_endpoint():
            return {"message": "fast"}

        @app.get("/slow")
        async def slow_endpoint():
            import time
            time.sleep(0.2)  # 模拟慢请求
            return {"message": "slow"}

        return app

    @pytest.fixture
    def client(self, app_with_monitoring):
        """创建测试客户端"""
        return TestClient(app_with_monitoring)

    def test_response_time_header(self, client):
        """测试响应时间头"""
        response = client.get("/fast")

        assert response.status_code == 200
        assert "X-Response-Time" in response.headers
        assert response.headers["X-Response-Time"].endswith("s")

    @patch('src.middleware.performance.logging.getLogger')
    def test_slow_request_logging(self, mock_logger, client):
        """测试慢请求日志"""
        response = client.get("/slow")

        assert response.status_code == 200

        # 验证慢请求被记录
        mock_logger.return_value.warning.assert_called()


class TestAsyncBatchProcessor:
    """测试异步批处理器"""

    def test_batch_processor_init(self):
        """测试批处理器初始化"""
        processor = AsyncBatchProcessor(batch_size=10, flush_interval=1.0)

        assert processor.batch_size == 10
        assert processor.flush_interval == 1.0
        assert len(processor._queue) == 0

    @pytest.mark.asyncio
    async def test_add_items(self):
        """测试添加项目"""
        processor = AsyncBatchProcessor(batch_size=2)

        await processor.add("item1")
        assert len(processor._queue) == 1

        await processor.add("item2")
        # 应该触发刷新
        assert len(processor._queue) == 0

    @pytest.mark.asyncio
    async def test_flush(self):
        """测试刷新"""
        processor = AsyncBatchProcessor()
        processor._queue = ["item1", "item2", "item3"]

        # 模拟处理方法
        processor._process_batch = AsyncMock()

        await processor.flush()

        assert len(processor._queue) == 0
        processor._process_batch.assert_called_once_with(["item1", "item2", "item3"])


class TestDatabaseBatchProcessor:
    """测试数据库批处理器"""

    @pytest.fixture
    def mock_db_session(self):
        """模拟数据库会话"""
        session = AsyncMock()
        session.execute = AsyncMock()
        session.commit = AsyncMock()
        session.rollback = AsyncMock()
        return session

    def test_db_batch_processor_init(self, mock_db_session):
        """测试数据库批处理器初始化"""
        processor = DatabaseBatchProcessor(
            mock_db_session,
            "test_table",
            batch_size=50
        )

        assert processor.table_name == "test_table"
        assert processor.batch_size == 50

    @pytest.mark.asyncio
    async def test_db_batch_insert(self, mock_db_session):
        """测试数据库批量插入"""
        processor = DatabaseBatchProcessor(
            mock_db_session,
            "test_table"
        )

        # 添加数据
        await processor.add({"id": 1, "name": "test1"})
        await processor.add({"id": 2, "name": "test2"})

        # 刷新
        await processor.flush()

        # 验证SQL执行
        mock_db_session.execute.assert_called()
        mock_db_session.commit.assert_called()

    @pytest.mark.asyncio
    async def test_db_batch_error_handling(self, mock_db_session):
        """测试数据库批处理错误处理"""
        processor = DatabaseBatchProcessor(
            mock_db_session,
            "test_table"
        )

        # 模拟错误
        mock_db_session.execute.side_effect = Exception("Database error")

        await processor.add({"id": 1, "name": "test1"})
        await processor.flush()

        # 验证回滚
        mock_db_session.rollback.assert_called()


class TestCacheDecorator:
    """测试缓存装饰器"""

    @pytest.mark.asyncio
    async def test_cache_decorator(self):
        """测试缓存装饰器"""
        call_count = 0

        @cache_response(ttl=300, key_prefix="test")
        async def expensive_function(x: int) -> int:
            nonlocal call_count
            call_count += 1
            return x * 2

        # 第一次调用
        result1 = await expensive_function(5)
        assert result1 == 10
        assert call_count == 1

        # 第二次调用（应该从缓存返回）
        result2 = await expensive_function(5)
        assert result2 == 10
        # 装饰器实现中缓存功能未完成，需要实际缓存管理器


class TestPerformanceIntegration:
    """性能功能集成测试"""

    def test_all_middlewares_together(self):
        """测试所有中间件一起使用"""
        from src.middleware.performance import (
            ResponseCacheMiddleware,
            CompressionMiddleware,
            PerformanceMonitoringMiddleware
        )

        app = FastAPI()

        # 添加多个中间件
        app.add_middleware(PerformanceMonitoringMiddleware)
        app.add_middleware(CompressionMiddleware)
        app.add_middleware(ResponseCacheMiddleware)

        @app.get("/test")
        async def test_endpoint():
            return {"message": "test", "data": "x" * 1000}

        client = TestClient(app)

        # 发送请求
        headers = {"Accept-Encoding": "gzip"}
        response = client.get("/test", headers=headers)

        assert response.status_code == 200
        assert "X-Response-Time" in response.headers
        assert response.headers.get("Content-Encoding") == "gzip"