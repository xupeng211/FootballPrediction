#!/usr/bin/env python3
"""
FotMob API 客户端熔断器测试
Circuit Breaker State Transition Tests for FotMob API Client

测试熔断器的三种状态转换：
CLOSED -> OPEN -> HALF_OPEN -> CLOSED
"""

import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, patch
from datetime import datetime, timedelta
from typing import Dict, Any

from src.api.fotmob_client import FotMobAPIClient, CircuitState
from src.core.exceptions import ExternalAPIError, CircuitBreakerError


class TestFotMobAPIClientCircuitBreaker:
    """FotMob API 客户端熔断器测试"""

    @pytest.fixture
    def client(self):
        """创建带有熔断器的客户端实例"""
        config = {
            "base_url": "https://www.fotmob.com/api",
            "timeout": 30,
            "rate_limit_delay": 1.0,
            "circuit_breaker": {"failure_threshold": 3, "recovery_timeout": 60, "half_open_max_calls": 5},
        }
        return FotMobAPIClient(config)

    @pytest.mark.asyncio
    async def test_circuit_breaker_closed_to_open_transition(self, client):
        """测试熔断器从 CLOSED 到 OPEN 的状态转换"""
        # 模拟连续失败
        with patch("aiohttp.ClientSession.get") as mock_get:
            mock_response = AsyncMock()
            mock_response.status = 500
            mock_response.text = AsyncMock(return_value="Internal Server Error")
            mock_get.return_value.__aenter__.return_value = mock_response

            # 初始状态应该是 CLOSED
            assert client.circuit_breaker.state == CircuitState.CLOSED
            assert client.circuit_breaker.failure_count == 0

            # 连续失败 3 次（达到阈值）
            for i in range(3):
                with pytest.raises(ExternalAPIError):
                    await client.get_match_details("test_match")

                assert client.circuit_breaker.state == CircuitState.CLOSED
                assert client.circuit_breaker.failure_count == i + 1

            # 第 4 次调用应该触发熔断器打开
            with pytest.raises(CircuitBreakerError):
                await client.get_match_details("test_match")

            assert client.circuit_breaker.state == CircuitState.OPEN
            assert client.circuit_breaker.failure_count == 3

    @pytest.mark.asyncio
    async def test_circuit_breaker_open_blocks_requests(self, client):
        """测试熔断器在 OPEN 状态下阻止请求"""
        # 手动设置熔断器为 OPEN 状态
        client.circuit_breaker.state = CircuitState.OPEN
        client.circuit_breaker.last_failure_time = datetime.now()

        # 在 OPEN 状态下，所有请求都应该被阻止
        with patch("aiohttp.ClientSession.get") as mock_get:
            mock_get.return_value.__aenter__.return_value = AsyncMock()

            with pytest.raises(CircuitBreakerError, match="Circuit breaker is OPEN"):
                await client.get_match_details("test_match")

            # 验证没有实际的 HTTP 请求被发送
            mock_get.assert_not_called()

    @pytest.mark.asyncio
    async def test_circuit_breaker_open_to_half_open_transition(self, client):
        """测试熔断器从 OPEN 到 HALF_OPEN 的状态转换"""
        # 设置熔断器为 OPEN 状态，并模拟时间流逝
        client.circuit_breaker.state = CircuitState.OPEN
        client.circuit_breaker.failure_count = 3
        client.circuit_breaker.last_failure_time = datetime.now() - timedelta(seconds=61)

        # 模拟成功的响应
        with patch("aiohttp.ClientSession.get") as mock_get:
            mock_response = AsyncMock()
            mock_response.status = 200
            mock_response.json = AsyncMock(return_value={"data": "success"})
            mock_get.return_value.__aenter__.return_value = mock_response

            # 下一个请求应该触发状态转换到 HALF_OPEN
            result = await client.get_match_details("test_match")

            assert result == {"data": "success"}
            assert client.circuit_breaker.state == CircuitState.HALF_OPEN
            assert client.circuit_breaker.half_open_calls == 1

    @pytest.mark.asyncio
    async def test_circuit_breaker_half_open_to_closed_on_success(self, client):
        """测试熔断器在 HALF_OPEN 状态下成功后转换到 CLOSED"""
        # 设置熔断器为 HALF_OPEN 状态
        client.circuit_breaker.state = CircuitState.HALF_OPEN
        client.circuit_breaker.failure_count = 2
        client.circuit_breaker.half_open_calls = 0

        # 模拟连续成功的响应
        with patch("aiohttp.ClientSession.get") as mock_get:
            mock_response = AsyncMock()
            mock_response.status = 200
            mock_response.json = AsyncMock(return_value={"data": "success"})
            mock_get.return_value.__aenter__.return_value = mock_response

            # 进行几次成功调用
            for i in range(3):
                result = await client.get_match_details(f"test_match_{i}")
                assert result == {"data": "success"}
                assert client.circuit_breaker.state == CircuitState.HALF_OPEN
                assert client.circuit_breaker.half_open_calls == i + 1

            # 第 3 次成功后，熔断器应该回到 CLOSED 状态
            assert client.circuit_breaker.state == CircuitState.CLOSED
            assert client.circuit_breaker.failure_count == 0
            assert client.circuit_breaker.half_open_calls == 0

    @pytest.mark.asyncio
    async def test_circuit_breaker_half_open_to_open_on_failure(self, client):
        """测试熔断器在 HALF_OPEN 状态下失败后回到 OPEN"""
        # 设置熔断器为 HALF_OPEN 状态
        client.circuit_breaker.state = CircuitState.HALF_OPEN
        client.circuit_breaker.failure_count = 2
        client.circuit_breaker.half_open_calls = 1

        # 模拟失败的响应
        with patch("aiohttp.ClientSession.get") as mock_get:
            mock_response = AsyncMock()
            mock_response.status = 500
            mock_response.text = AsyncMock(return_value="Internal Server Error")
            mock_get.return_value.__aenter__.return_value = mock_response

            # 一次失败应该让熔断器回到 OPEN 状态
            with pytest.raises(ExternalAPIError):
                await client.get_match_details("test_match")

            assert client.circuit_breaker.state == CircuitState.OPEN
            assert client.circuit_breaker.failure_count == 3
            assert client.circuit_breaker.half_open_calls == 0

    @pytest.mark.asyncio
    async def test_circuit_breaker_half_open_max_calls_limit(self, client):
        """测试熔断器在 HALF_OPEN 状态下的最大调用次数限制"""
        # 设置熔断器为 HALF_OPEN 状态，并设置最大调用次数为 2
        client.circuit_breaker.state = CircuitState.HALF_OPEN
        client.circuit_breaker.half_open_max_calls = 2
        client.circuit_breaker.half_open_calls = 2

        # 达到最大调用次数后，新请求应该被阻止
        with patch("aiohttp.ClientSession.get") as mock_get:
            mock_response = AsyncMock()
            mock_response.status = 200
            mock_response.json = AsyncMock(return_value={"data": "success"})
            mock_get.return_value.__aenter__.return_value = mock_response

            with pytest.raises(CircuitBreakerError, match="Half-open max calls exceeded"):
                await client.get_match_details("test_match")

            # 验证没有实际的 HTTP 请求被发送
            mock_get.assert_not_called()

    def test_circuit_breaker_state_persistence(self, client):
        """测试熔断器状态的持久化"""
        # 测试状态变量
        assert client.circuit_breaker.state == CircuitState.CLOSED
        assert client.circuit_breaker.failure_count == 0
        assert client.circuit_breaker.half_open_calls == 0
        assert client.circuit_breaker.last_failure_time is None

        # 手动改变状态
        client.circuit_breaker.state = CircuitState.OPEN
        client.circuit_breaker.failure_count = 5
        client.circuit_breaker.half_open_calls = 3
        client.circuit_breaker.last_failure_time = datetime.now()

        # 验证状态被正确保存
        assert client.circuit_breaker.state == CircuitState.OPEN
        assert client.circuit_breaker.failure_count == 5
        assert client.circuit_breaker.half_open_calls == 3
        assert client.circuit_breaker.last_failure_time is not None

    def test_circuit_breaker_configuration_validation(self):
        """测试熔断器配置验证"""
        # 测试默认配置
        client = FotMobAPIClient({})
        assert client.circuit_breaker.failure_threshold == 5
        assert client.circuit_breaker.recovery_timeout == 60
        assert client.circuit_breaker.half_open_max_calls == 3

        # 测试自定义配置
        config = {"circuit_breaker": {"failure_threshold": 10, "recovery_timeout": 120, "half_open_max_calls": 5}}
        client = FotMobAPIClient(config)
        assert client.circuit_breaker.failure_threshold == 10
        assert client.circuit_breaker.recovery_timeout == 120
        assert client.circuit_breaker.half_open_max_calls == 5
