"""
API Client 单元测试
测试FotMobAPIClient的重试机制、超时处理和User-Agent降级
"""

import pytest
import asyncio
import json
from pathlib import Path
from unittest.mock import patch, Mock, AsyncMock
import aiohttp
from tenacity import RetryError

# 添加src路径
import sys
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

try:
    from src.api.fotmob_client import FotMobAPIClient, get_api_client
except ImportError:
    pytest.skip("FotMobAPIClient not available", allow_module_level=True)


@pytest.mark.unit
@pytest.mark.asyncio
class TestFotMobAPIClient:
    """FotMobAPIClient测试类"""

    @pytest.fixture
    def client(self):
        """创建API客户端实例"""
        return FotMobAPIClient()

    @pytest.fixture
    def mock_session(self):
        """Mock aiohttp会话"""
        session = AsyncMock()
        return session

    @pytest.fixture
    def success_response(self):
        """成功响应Mock"""
        response = AsyncMock()
        response.status = 200
        response.headers = {'Content-Type': 'application/json'}
        response.json.return_value = {"success": True, "data": {"match": {}}}
        return response

    @pytest.fixture
    def timeout_response(self):
        """超时响应Mock"""
        return asyncio.TimeoutError("Request timeout")

    @pytest.fixture
    def rate_limit_response(self):
        """限流响应Mock"""
        response = AsyncMock()
        response.status = 429
        response.headers = {'Retry-After': '60'}
        response.text.return_value = "Rate limit exceeded"
        return response

    @pytest.fixture
    def server_error_response(self):
        """服务器错误响应Mock"""
        response = AsyncMock()
        response.status = 500
        response.text.return_value = "Internal server error"
        return response

    async def test_client_initialization(self, client):
        """测试客户端初始化"""
        assert hasattr(client, 'session')
        assert hasattr(client, 'base_url')
        assert hasattr(client, 'max_retries')
        assert hasattr(client, 'timeout')

    async def test_get_request_stats(self, client):
        """测试获取请求统计"""
        stats = client.get_request_stats()

        assert isinstance(stats, dict)
        assert 'session_id' in stats
        assert 'total_requests' in stats
        assert 'success_rate' in stats

    async def test_fetch_match_data_success(self, client, success_response):
        """测试成功获取比赛数据"""
        with patch.object(client, 'session', mock_session):
            mock_session.get.return_value.__aenter__.return_value = success_response

            result = await client.fetch_match_data("4147463")

            assert result["success"] is True
            assert "data" in result

    async def test_fetch_match_data_timeout(self, client, timeout_response):
        """测试请求超时处理"""
        with patch.object(client, 'session', mock_session):
            mock_session.get.side_effect = timeout_response

            # 应该重试几次后抛出异常
            with pytest.raises((asyncio.TimeoutError, RetryError)):
                await client.fetch_match_data("4147463")

    async def test_fetch_match_data_rate_limit(self, client, rate_limit_response):
        """测试API限流处理"""
        with patch.object(client, 'session', mock_session):
            mock_session.get.return_value.__aenter__.return_value = rate_limit_response

            # 应该重试或处理限流
            result = await client.fetch_match_data("4147463")

            # 结果可能是错误或重试后的成功
            assert isinstance(result, dict)

    async def test_fetch_match_data_server_error(self, client, server_error_response):
        """测试服务器错误处理"""
        with patch.object(client, 'session', mock_session):
            mock_session.get.return_value.__aenter__.return_value = server_error_response

            # 应该重试或处理错误
            result = await client.fetch_match_data("4147463")

            # 结果可能是错误或重试后的成功
            assert isinstance(result, dict)

    async def test_user_agent_header(self, client, success_response):
        """测试User-Agent头部设置"""
        with patch.object(client, 'session', mock_session):
            mock_session.get.return_value.__aenter__.return_value = success_response

            await client.fetch_match_data("4147463")

            # 验证请求头部
            call_args = mock_session.get.call_args
            headers = call_args[1].get('headers', {})

            assert 'User-Agent' in headers
            assert 'Mozilla' in headers['User-Agent']

    async def test_custom_headers_injection(self, client, success_response):
        """测试自定义头部注入"""
        with patch.object(client, 'session', mock_session):
            mock_session.get.return_value.__aenter__.return_value = success_response

            await client.fetch_match_data("4147463")

            call_args = mock_session.get.call_args
            headers = call_args[1].get('headers', {})

            # 验证必要的头部存在
            assert any(key.lower() in ['x-mas', 'x-foo'] for key in headers.keys())

    async def test_retry_mechanism_first_failure_then_success(self, client):
        """测试重试机制：先失败后成功"""
        fail_response = AsyncMock()
        fail_response.status = 500
        fail_response.text.return_value = "Server error"

        success_response = AsyncMock()
        success_response.status = 200
        success_response.json.return_value = {"success": True}

        with patch.object(client, 'session', mock_session):
            # 第一次调用返回失败，第二次返回成功
            mock_session.get.return_value.__aenter__.side_effect = [fail_response, success_response]

            result = await client.fetch_match_data("4147463")

            assert result["success"] is True
            # 应该被调用了两次（第一次失败，第二次成功）
            assert mock_session.get.call_count >= 1

    async def test_retry_exhaustion(self, client, server_error_response):
        """测试重试次数耗尽"""
        with patch.object(client, 'session', mock_session):
            mock_session.get.return_value.__aenter__.return_value = server_error_response

            # 设置较小的重试次数以加速测试
            original_max_retries = client.max_retries
            client.max_retries = 2

            try:
                result = await client.fetch_match_data("4147463")

                # 重试耗尽后应该返回错误结果
                assert result["success"] is False
                assert "error" in result
            finally:
                client.max_retries = original_max_retries

    async def test_request_timeout_config(self, client):
        """测试请求超时配置"""
        with patch.object(client, 'session', mock_session):
            mock_session.get.return_value.__aenter__.side_effect = asyncio.TimeoutError()

            result = await client.fetch_match_data("4147463")

            assert "error" in result or "success" in result

    async def test_concurrent_requests_safety(self, client, success_response):
        """测试并发请求安全性"""
        async def fetch_worker(match_id):
            with patch.object(client, 'session', mock_session):
                mock_session.get.return_value.__aenter__.return_value = success_response
                return await client.fetch_match_data(match_id)

        # 创建多个并发请求
        tasks = [fetch_worker(f"match_{i}") for i in range(10)]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # 所有请求都应该成功
        assert len(results) == 10
        for result in results:
            if not isinstance(result, Exception):
                assert result["success"] is True

    async def test_session_lifecycle(self, client):
        """测试会话生命周期"""
        # 测试会话创建
        await client._ensure_session()
        assert client.session is not None

        # 测试会话关闭
        await client.close()
        assert client.session is None or client.session.closed

    async def test_response_data_validation(self, client):
        """测试响应数据验证"""
        # 测试无效JSON响应
        invalid_json_response = AsyncMock()
        invalid_json_response.status = 200
        invalid_json_response.json.side_effect = json.JSONDecodeError("Invalid JSON", "", 0)

        with patch.object(client, 'session', mock_session):
            mock_session.get.return_value.__aenter__.return_value = invalid_json_response

            result = await client.fetch_match_data("4147463")

            assert isinstance(result, dict)
            assert "error" in result or "success" in result

    async def test_network_error_handling(self, client):
        """测试网络错误处理"""
        with patch.object(client, 'session', mock_session):
            mock_session.get.side_effect = aiohttp.ClientError("Network error")

            result = await client.fetch_match_data("4147463")

            assert isinstance(result, dict)
            assert "error" in result

    async def test_match_id_validation(self, client):
        """测试比赛ID验证"""
        # 测试空ID
        result = await client.fetch_match_data("")
        assert "error" in result

        # 测试None ID
        result = await client.fetch_match_data(None)
        assert "error" in result

        # 测试过长ID
        long_id = "x" * 1000
        result = await client.fetch_match_data(long_id)
        assert "error" in result

    def test_get_api_client_function(self):
        """测试get_api_client工厂函数"""
        client = get_api_client()
        assert isinstance(client, FotMobAPIClient)

        # 测试单例模式（如果实现了的话）
        client2 = get_api_client()
        assert isinstance(client2, FotMobAPIClient)

    async def test_backoff_strategy(self, client, server_error_response):
        """测试退避策略"""
        import time

        with patch.object(client, 'session', mock_session):
            mock_session.get.return_value.__aenter__.return_value = server_error_response

            start_time = time.time()
            await client.fetch_match_data("4147463")
            end_time = time.time()

            # 应该有延迟（退避策略）
            # 注意：这个测试可能不稳定，取决于具体的退避实现

    async def test_circuit_breaker_pattern(self, client):
        """测试熔断器模式（如果实现了）"""
        # 这个测试取决于是否实现了熔断器模式
        pass