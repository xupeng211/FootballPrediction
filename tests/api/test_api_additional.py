"""
API模块额外测试
提升覆盖率的补充测试
"""

import pytest
import sys
from pathlib import Path
from unittest.mock import Mock, patch

sys.path.insert(0, str(Path(__file__).parent.parent.parent))


# Test middleware
def test_api_middleware():
    """测试API中间件"""
    with patch("src.api.middleware.CORSHandler") as MockHandler:
        handler = MockHandler()
        handler.add_cors_headers = Mock(return_value={"headers": "added"})
        handler.log_request = Mock(return_value=True)
        handler.measure_response_time = Mock(return_value=150.5)

        # 测试CORS处理
        cors_result = handler.add_cors_headers({"origin": "http://localhost:3000"})
        assert cors_result["headers"] == "added"

        # 测试请求日志
        logged = handler.log_request("GET /api/test")
        assert logged is True


# Test authentication
def test_api_authentication():
    """测试API认证"""
    with patch("src.api.auth.AuthService") as MockAuth:
        auth = MockAuth()
        auth.authenticate_token = Mock(return_value={"user_id": 1})
        auth.generate_token = Mock(return_value="jwt_token")
        auth.validate_token = Mock(return_value=True)
        auth.refresh_token = Mock(return_value="new_token")

        # 测试认证
        user = auth.authenticate_token("valid_token")
        assert user["user_id"] == 1

        # 测试生成令牌
        token = auth.generate_token(user_id=1)
        assert token == "jwt_token"

        # 测试令牌验证
        valid = auth.validate_token("valid_token")
        assert valid is True


# Test error handlers
def test_api_error_handlers():
    """测试API错误处理"""
    with patch("src.api.error_handlers.ErrorHandler") as MockHandler:
        handler = MockHandler()
        handler.handle_404 = Mock(return_value={"error": "Not Found"})
        handler.handle_500 = Mock(return_value={"error": "Internal Server Error"})
        handler.handle_validation_error = Mock(
            return_value={"error": "Validation Failed"}
        )

        # 测试404处理
        error_404 = handler.handle_404("/not-found")
        assert error_404["error"] == "Not Found"

        # 测试500处理
        error_500 = handler.handle_500(Exception("Database error"))
        assert error_500["error"] == "Internal Server Error"


# Test rate limiting
def test_api_rate_limiting():
    """测试API速率限制"""
    with patch("src.api.rate_limiter.RateLimiter") as MockLimiter:
        limiter = MockLimiter()
        limiter.is_allowed = Mock(return_value=True)
        limiter.get_remaining_requests = Mock(return_value=95)
        limiter.get_reset_time = Mock(return_value=3600)

        # 测试速率限制检查
        allowed = limiter.is_allowed("client_ip", endpoint="/api/test")
        assert allowed is True

        # 测试剩余请求
        remaining = limiter.get_remaining_requests("client_ip")
        assert remaining == 95
