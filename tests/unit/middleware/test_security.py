"""
安全中间件测试
Security Middleware Tests
"""

import pytest
import time
from unittest.mock import AsyncMock, Mock
from fastapi import FastAPI, Request, HTTPException
from fastapi.testclient import TestClient
from starlette.responses import Response

from src.middleware.security import (
    SecurityMiddleware,
    InMemoryRateLimiter,
    sanitize_input,
    generate_secure_token,
)


class TestInMemoryRateLimiter:
    """测试内存限流器"""

    def test_rate_limiting_within_limits(self):
        """测试在限制内的请求"""
        limiter = InMemoryRateLimiter()
        key = "test_key"

        # 5次请求，限制10次/分钟
        for _ in range(5):
            assert limiter.is_allowed(key, 10, 60) is True

    def test_rate_limiting_exceeds_limit(self):
        """测试超过限制的请求"""
        limiter = InMemoryRateLimiter()
        key = "test_key"

        # 发送10次请求，限制10次/分钟
        for _ in range(10):
            assert limiter.is_allowed(key, 10, 60) is True

        # 第11次请求应该被拒绝
        assert limiter.is_allowed(key, 10, 60) is False

    def test_rate_limiting_window_reset(self):
        """测试时间窗口重置"""
        limiter = InMemoryRateLimiter()
        key = "test_key"
        current_time = time.time()

        # 在时间窗口内发送请求
        for _ in range(5):
            assert limiter.is_allowed(key, 5, 60, current_time) is True

        # 超过限制
        assert limiter.is_allowed(key, 5, 60, current_time) is False

        # 时间窗口后，应该重置
        future_time = current_time + 61
        assert limiter.is_allowed(key, 5, 60, future_time) is True

    def test_different_keys_independent(self):
        """测试不同key的独立性"""
        limiter = InMemoryRateLimiter()

        # 两个不同的key应该独立计算
        assert limiter.is_allowed("key1", 1, 60) is True
        assert limiter.is_allowed("key2", 1, 60) is True
        assert limiter.is_allowed("key1", 1, 60) is False
        assert limiter.is_allowed("key2", 1, 60) is False


class TestSecurityMiddleware:
    """测试安全中间件"""

    @pytest.fixture
    def app(self):
        """创建测试应用"""
        app = FastAPI()

        # 添加安全中间件
        security = SecurityMiddleware(app)

        @app.get("/test")
        async def test_endpoint():
            return {"message": "test"}

        @app.get("/predictions/123")
        async def predictions_endpoint():
            return {"prediction": "test"}

        @app.get("/data/matches")
        async def data_endpoint():
            return {"data": "test"}

        @app.get("/health")
        async def health_endpoint():
            return {"status": "healthy"}

        return app

    @pytest.fixture
    def client(self, app):
        """创建测试客户端"""
        return TestClient(app)

    def test_security_headers(self, client):
        """测试安全头"""
        response = client.get("/test")

        assert response.headers.get("X-Content-Type-Options") == "nosniff"
        assert response.headers.get("X-Frame-Options") == "DENY"
        assert response.headers.get("X-XSS-Protection") == "1; mode=block"
        assert response.headers.get("Server") == "FootballPredictionAPI"

    def test_rate_limit_headers(self, client):
        """测试限流头"""
        response = client.get("/test")

        assert "X-RateLimit-Limit" in response.headers
        assert "X-RateLimit-Remaining" in response.headers
        assert "X-RateLimit-Window" in response.headers

    def test_different_rate_limits(self, client):
        """测试不同路径的限流规则"""
        # 预测API应该有更严格的限制
        response = client.get("/predictions/123")
        limit = int(response.headers["X-RateLimit-Limit"])
        assert limit == 60  # 60次/分钟

        # 数据API限制
        response = client.get("/data/matches")
        limit = int(response.headers["X-RateLimit-Limit"])
        assert limit == 120  # 120次/分钟

        # 健康检查限制
        response = client.get("/health")
        limit = int(response.headers["X-RateLimit-Limit"])
        assert limit == 1000  # 1000次/分钟

    def test_rate_limit_exceeded(self, client):
        """测试限流超出"""
        # 快速发送多个请求
        for _ in range(100):
            response = client.get("/test")
            if response.status_code == 429:
                break
        else:
            pytest.fail("Expected rate limit to be triggered")

        assert response.status_code == 429
        assert "Rate limit exceeded" in response.json()["detail"]

    def test_cors_headers(self, client):
        """测试CORS头"""
        response = client.options("/test")

        assert "access-control-allow-origin" in response.headers
        assert "access-control-allow-methods" in response.headers
        assert "access-control-allow-headers" in response.headers

    def test_blocked_ip(self, app):
        """测试IP阻止"""
        security = app.state.security_middleware
        security.block_ip("192.168.1.100")

        # 创建模拟请求
        request = Mock()
        request.client = Mock()
        request.client.host = "192.168.1.100"

        # 验证IP被阻止
        assert "192.168.1.100" in security.blocked_ips

    def test_get_client_ip(self, app):
        """测试获取客户端IP"""
        security = app.state.security_middleware

        # 测试直接IP
        request = Mock()
        request.client = Mock()
        request.client.host = "192.168.1.1"
        request.headers = {}

        assert security._get_client_ip(request) == "192.168.1.1"

        # 测试X-Forwarded-For
        request.headers = {"x-forwarded-for": "10.0.0.1, 192.168.1.1"}
        assert security._get_client_ip(request) == "10.0.0.1"

        # 测试X-Real-IP
        request.headers = {"x-real-ip": "10.0.0.2"}
        assert security._get_client_ip(request) == "10.0.0.2"

    def test_request_size_limit(self, client):
        """测试请求大小限制"""
        # 发送大请求体
        large_data = "x" * (11 * 1024 * 1024)  # 11MB
        response = client.post(
            "/test",
            data=large_data,
            headers={"content-length": str(len(large_data))}
        )

        # 应该被拒绝
        assert response.status_code == 413
        assert "Request entity too large" in response.json()["detail"]


class TestInputSanitization:
    """测试输入清理"""

    def test_sanitize_input_removes_sql_injection(self):
        """测试移除SQL注入字符"""
        malicious_input = "'; DROP TABLE users; --"
        sanitized = sanitize_input(malicious_input)

        assert "'" not in sanitized
        assert ";" not in sanitized
        assert "--" not in sanitized
        assert "DROP TABLE" not in sanitized

    def test_sanitize_input_handles_empty_input(self):
        """测试处理空输入"""
        assert sanitize_input("") == ""
        assert sanitize_input(None) == ""

    def test_sanitize_input_strips_whitespace(self):
        """测试去除空白字符"""
        input_str = "  test input  "
        assert sanitize_input(input_str) == "test input"

    def test_sanitize_input_preserves_valid_chars(self):
        """测试保留有效字符"""
        input_str = "user@example.com"
        assert sanitize_input(input_str) == input_str


class TestSecureTokenGeneration:
    """测试安全token生成"""

    def test_generate_secure_token_length(self):
        """测试token长度"""
        token = generate_secure_token(32)
        # URL safe base64编码，32字节输入产生43字符输出
        assert len(token) == 43

    def test_generate_secure_token_uniqueness(self):
        """测试token唯一性"""
        tokens = [generate_secure_token() for _ in range(100)]
        assert len(set(tokens)) == 100  # 所有token都应该是唯一的

    def test_generate_secure_token_different_lengths(self):
        """测试不同长度的token"""
        token16 = generate_secure_token(16)
        token32 = generate_secure_token(32)
        token64 = generate_secure_token(64)

        assert len(token16) < len(token32)
        assert len(token32) < len(token64)

        # 所有token都应该是URL安全的
        for token in [token16, token32, token64]:
            assert "+" not in token or " " in token
            assert "/" not in token or " " in token


class TestSecurityIntegration:
    """安全功能集成测试"""

    def test_full_security_flow(self):
        """测试完整的安全流程"""
        app = FastAPI()
        security = SecurityMiddleware(app)

        @app.post("/api/predict")
        async def predict_endpoint(request: Request):
            data = await request.json()
            # 清理输入
            match_id = sanitize_input(data.get("match_id", ""))
            return {"match_id": match_id, "prediction": "home"}

        client = TestClient(app)

        # 正常请求
        response = client.post(
            "/api/predict",
            json={"match_id": "12345"}
        )
        assert response.status_code == 200
        assert response.headers.get("X-Content-Type-Options") == "nosniff"

        # 恶意请求
        response = client.post(
            "/api/predict",
            json={"match_id": "'; DROP TABLE predictions; --"}
        )
        assert response.status_code == 200
        assert ";" not in response.json()["match_id"]

    def test_rate_limit_with_different_ips(self):
        """测试不同IP的限流"""
        app = FastAPI()
        security = SecurityMiddleware(app)

        @app.get("/test")
        async def test_endpoint():
            return {"message": "test"}

        # 模拟来自不同IP的请求
        # 注意：在实际测试中，可能需要使用更复杂的设置来模拟IP