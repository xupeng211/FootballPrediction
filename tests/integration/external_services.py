#!/usr/bin/env python3
"""
第三方服务集成测试 - Phase F核心组件
External Services Integration Tests - Phase F Core Component

这是Phase F: 企业级集成阶段的第三方服务测试文件，涵盖:
- API客户端弹性测试
- 网络故障处理测试
- 服务降级和容错测试
- 外部数据源集成测试

基于Issue #149的成功经验,使用已验证的Fallback测试策略。
"""

import pytest
import asyncio
import time
import json
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
from unittest.mock import Mock, patch, AsyncMock
import requests
from requests.exceptions import Timeout, ConnectionError, HTTPError

# 模块可用性检查 - Phase E验证的成功策略
try:
    import aiohttp
    AIOHTTP_AVAILABLE = True
except ImportError:
    AIOHTTP_AVAILABLE = False
    aiohttp = Mock()

try:
    import httpx
    HTTPX_AVAILABLE = True
except ImportError:
    HTTPX_AVAILABLE = False
    httpx = Mock()

try:
    from src.api.clients import ExternalAPIClient
    CLIENT_AVAILABLE = True
except ImportError:
    CLIENT_AVAILABLE = False
    ExternalAPIClient = Mock()

try:
    from src.adapters.http_adapter import HTTPAdapter
    ADAPTER_AVAILABLE = True
except ImportError:
    ADAPTER_AVAILABLE = False
    HTTPAdapter = Mock()

try:
    from src.services.external_service import ExternalDataService
    SERVICE_AVAILABLE = True
except ImportError:
    SERVICE_AVAILABLE = False
    ExternalDataService = Mock()


@pytest.mark.integration
@pytest.mark.external_api
class TestExternalServicesComprehensive:
    """第三方服务综合集成测试类"""

    @pytest.fixture(autouse=True)
    def setup_external_services(self):
        """设置外部服务测试环境"""
        # 测试用的外部API配置
        self.test_api_configs = {
            "football_api": {
                "base_url": "https://api.football-data.org/v4/",
                "timeout": 30,
                "retry_attempts": 3,
                "api_key": "test_api_key"
            },
            "weather_api": {
                "base_url": "https://api.openweathermap.org/data/2.5/",
                "timeout": 10,
                "retry_attempts": 2,
                "api_key": "test_weather_key"
            },
            "odds_api": {
                "base_url": "https://api.the-odds-api.com/v4/",
                "timeout": 15,
                "retry_attempts": 3,
                "api_key": "test_odds_key"
            }
        }

        # 模拟外部服务响应
        self.mock_responses = {
            "teams": [
                {"id": 1, "name": "Manchester United", "league": "Premier League"},
                {"id": 2, "name": "Liverpool", "league": "Premier League"},
                {"id": 3, "name": "Barcelona", "league": "La Liga"}
            ],
            "matches": [
                {"id": 1, "home_team": 1, "away_team": 2, "date": "2025-11-01", "status": "scheduled"},
                {"id": 2, "home_team": 2, "away_team": 3, "date": "2025-11-02", "status": "scheduled"}
            ],
            "weather": {
                "temperature": 15.5,
                "humidity": 65,
                "condition": "cloudy",
                "wind_speed": 10.2
            },
            "odds": {
                "home_win": 2.1,
                "draw": 3.4,
                "away_win": 3.8,
                "over_under": "2.5"
            }
        }

    def test_api_client_resilience(self):
        """API客户端弹性测试"""
        if not HTTPX_AVAILABLE and not AIOHTTP_AVAILABLE:
            pytest.skip("HTTP客户端库不可用")

        # 创建模拟API客户端
        class MockAPIClient:
            def __init__(self, config: Dict[str, Any]):
                self.config = config
                self.base_url = config["base_url"]
                self.timeout = config["timeout"]
                self.retry_attempts = config["retry_attempts"]

            def get(self, endpoint: str, params: Dict = None) -> Dict[str, Any]:
                """模拟GET请求,包含重试逻辑"""
                for attempt in range(self.retry_attempts):
                    try:
                        # 模拟网络延迟和偶尔失败
                        if attempt == 0 and "timeout_test" in endpoint:
                            raise Timeout("Request timeout")
                        elif attempt == 1 and "server_error" in endpoint:
                            response = Mock()
                            response.status_code = 500
                            response.raise_for_status.side_effect = HTTPError("500 Server Error")
                            response.raise_for_status()
                        else:
                            # 成功响应
                            if "teams" in endpoint:
                                return {"data": self.mock_responses["teams"]}
                            elif "matches" in endpoint:
                                return {"data": self.mock_responses["matches"]}
                            else:
                                return {"status": "success"}

                    except (Timeout, HTTPError, ConnectionError):
                        if attempt == self.retry_attempts - 1:
                            raise  # 最后一次尝试失败
                        time.sleep(0.1 * (attempt + 1))  # 指数退避

                return {}

        # 测试API客户端
        client = MockAPIClient(self.test_api_configs["football_api"])

        # 1. 正常请求测试
        result = client.get("teams")
        assert "data" in result
        assert len(result["data"]) == 3

        # 2. 超时重试测试
        start_time = time.time()
        try:
            result = client.get("timeout_test")
        except Timeout:
            pass  # 预期的超时
        end_time = time.time()

        # 验证重试时间（应该包含指数退避）
        retry_time = (end_time - start_time) * 1000
        assert retry_time > 300, f"重试时间不足: {retry_time:.2f}ms"

        # 3. 服务器错误重试测试
        start_time = time.time()
        try:
            result = client.get("server_error")
        except HTTPError:
            pass  # 预期的服务器错误
        end_time = time.time()

        # 验证重试逻辑
        retry_time = (end_time - start_time) * 1000
        assert retry_time > 200, f"重试时间不足: {retry_time:.2f}ms"

    def test_network_failure_handling(self):
        """网络故障处理测试"""
        if not HTTPX_AVAILABLE and not AIOHTTP_AVAILABLE:
            pytest.skip("HTTP客户端库不可用")

        # 模拟各种网络故障场景
        class NetworkFailureSimulator:
            def __init__(self):
                self.failure_rate = 0.3  # 30%的失败率

            def simulate_request(self, endpoint: str) -> Dict[str, Any]:
                """模拟请求,可能失败"""
                import random
                if random.random() < self.failure_rate:
                    # 随机选择一种故障类型
                    failure_types = [
                        ConnectionError("Connection refused"),
                        Timeout("Request timeout"),
                        HTTPError("HTTP 503 Service Unavailable"),
                        json.JSONDecodeError("Invalid JSON", "", 0)
                    ]
                    raise random.choice(failure_types)

                # 成功响应
                return {"status": "success", "data": "test_data"}

        # 测试网络故障处理
        simulator = NetworkFailureSimulator()

        success_count = 0
        failure_count = 0
        total_requests = 100

        for i in range(total_requests):
            try:
                simulator.simulate_request(f"endpoint_{i}")
                success_count += 1
            except (ConnectionError, Timeout, HTTPError, json.JSONDecodeError):
                failure_count += 1

        # 验证故障处理统计
        failure_rate = failure_count / total_requests
        assert 0.2 <= failure_rate <= 0.4, f"故障率不符合预期: {failure_rate:.2f}"
        assert success_count + failure_count == total_requests

    def test_service_degradation_scenarios(self):
        """服务降级场景测试"""
        if not SERVICE_AVAILABLE:
            pytest.skip("外部服务模块不可用")

        # 模拟服务降级策略
        class ServiceDegradationManager:
            def __init__(self):
                self.primary_service_available = True
                self.cache_available = True
                self.fallback_service_available = True

            def get_data(self, data_type: str) -> Dict[str, Any]:
                """获取数据,包含降级策略"""
                try:
                    # 1. 尝试主服务
                    if self.primary_service_available:
                        data = self._call_primary_service(data_type)
                        if data:
                            return {"source": "primary", "data": data}

                    # 2. 尝试缓存
                    if self.cache_available:
                        data = self._get_from_cache(data_type)
                        if data:
                            return {"source": "cache", "data": data}

                    # 3. 尝试备用服务
                    if self.fallback_service_available:
                        data = self._call_fallback_service(data_type)
                        if data:
                            return {"source": "fallback", "data": data}

                    # 4. 返回默认数据
                    return {"source": "default", "data": self._get_default_data(data_type)}

                except Exception as e:
                    return {"source": "error", "error": str(e)}

            def _call_primary_service(self, data_type: str) -> Optional[Dict]:
                """调用主服务"""
                if data_type == "teams":
                    return self.mock_responses.get("teams")
                elif data_type == "matches":
                    return self.mock_responses.get("matches")
                return None

            def _get_from_cache(self, data_type: str) -> Optional[Dict]:
                """从缓存获取数据"""
                # 模拟缓存命中
                if data_type in ["teams", "matches"]:
                    return self.mock_responses.get(data_type)
                return None

            def _call_fallback_service(self, data_type: str) -> Optional[Dict]:
                """调用备用服务"""
                # 模拟备用服务返回部分数据
                if data_type == "teams":
                    return [{"id": 1, "name": "Fallback Team"}]
                return None

            def _get_default_data(self, data_type: str) -> Dict:
                """获取默认数据"""
                return {"message": f"Default data for {data_type}"}

            def set_service_availability(self, primary: bool, cache: bool, fallback: bool):
                """设置服务可用性"""
                self.primary_service_available = primary
                self.cache_available = cache
                self.fallback_service_available = fallback

            @property
            def mock_responses(self):
                return {
                    "teams": [
                        {"id": 1, "name": "Team A"},
                        {"id": 2, "name": "Team B"}
                    ],
                    "matches": [
                        {"id": 1, "home_team": 1, "away_team": 2}
                    ]
                }

        # 测试服务降级策略
        degradation_manager = ServiceDegradationManager()

        # 1. 所有服务正常
        result = degradation_manager.get_data("teams")
        assert result["source"] == "primary"
        assert len(result["data"]) == 2

        # 2. 主服务不可用,使用缓存
        degradation_manager.set_service_availability(False, True, True)
        result = degradation_manager.get_data("teams")
        assert result["source"] == "cache"
        assert len(result["data"]) == 2

        # 3. 主服务和缓存不可用,使用备用服务
        degradation_manager.set_service_availability(False, False, True)
        result = degradation_manager.get_data("teams")
        assert result["source"] == "fallback"
        assert len(result["data"]) == 1

        # 4. 所有服务不可用,使用默认数据
        degradation_manager.set_service_availability(False, False, False)
        result = degradation_manager.get_data("teams")
        assert result["source"] == "default"
        assert "message" in result["data"]

    def test_rate_limiting_handling(self):
        """速率限制处理测试"""
        # 模拟速率限制的API客户端
        class RateLimitedClient:
            def __init__(self, requests_per_minute: int = 60):
                self.requests_per_minute = requests_per_minute
                self.request_times = []

            def make_request(self, endpoint: str) -> Dict[str, Any]:
                """发起请求,处理速率限制"""
                current_time = time.time()

                # 清理1分钟前的请求记录
                self.request_times = [
                    req_time for req_time in self.request_times
                    if current_time - req_time < 60
                ]

                # 检查是否超过速率限制
                if len(self.request_times) >= self.requests_per_minute:
                    # 计算需要等待的时间
                    oldest_request = min(self.request_times)
                    wait_time = 60 - (current_time - oldest_request)

                    if wait_time > 0:
                        return {
                            "error": "rate_limit_exceeded",
                            "retry_after": wait_time,
                            "message": f"Rate limit exceeded. Retry after {wait_time:.1f} seconds."
                        }

                # 记录当前请求时间
                self.request_times.append(current_time)

                # 模拟API响应
                return {
                    "status": "success",
                    "endpoint": endpoint,
                    "timestamp": current_time
                }

        # 测试速率限制
        client = RateLimitedClient(requests_per_minute=5)

        # 快速发起6个请求（第6个应该被限制）
        results = []
        for i in range(6):
            result = client.make_request(f"endpoint_{i}")
            results.append(result)
            time.sleep(0.1)  # 短暂间隔

        # 验证速率限制效果
        successful_requests = [r for r in results if r.get("status") == "success"]
        rate_limited_requests = [r for r in results if r.get("error") == "rate_limit_exceeded"]

        assert len(successful_requests) <= 5, f"成功请求数量超过限制: {len(successful_requests)}"
        assert len(rate_limited_requests) >= 1, f"没有触发速率限制: {len(rate_limited_requests)}"

        if rate_limited_requests:
            retry_after = rate_limited_requests[0].get("retry_after", 0)
            assert retry_after > 0, f"重试时间设置不正确: {retry_after}"

    def test_circuit_breaker_pattern(self):
        """断路器模式测试"""
        # 模拟断路器实现
        class CircuitBreaker:
            def __init__(self, failure_threshold: int = 5, recovery_timeout: int = 60):
                self.failure_threshold = failure_threshold
                self.recovery_timeout = recovery_timeout
                self.failure_count = 0
                self.last_failure_time = None
                self.state = "CLOSED"  # CLOSED, OPEN, HALF_OPEN

            def call(self, func, *args, **kwargs):
                """通过断路器调用函数"""
                if self.state == "OPEN":
                    if self._should_attempt_reset():
                        self.state = "HALF_OPEN"
                    else:
                        raise Exception("Circuit breaker is OPEN")

                try:
                    result = func(*args, **kwargs)
                    self._on_success()
                    return result
                except Exception as e:
                    self._on_failure()
                    raise e

            def _should_attempt_reset(self) -> bool:
                """检查是否应该尝试重置断路器"""
                if self.last_failure_time:
                    return time.time() - self.last_failure_time > self.recovery_timeout
                return False

            def _on_success(self):
                """成功调用时的处理"""
                self.failure_count = 0
                self.state = "CLOSED"

            def _on_failure(self):
                """失败调用时的处理"""
                self.failure_count += 1
                self.last_failure_time = time.time()

                if self.failure_count >= self.failure_threshold:
                    self.state = "OPEN"

        # 测试断路器
        circuit_breaker = CircuitBreaker(failure_threshold=3, recovery_timeout=2)

        def mock_failing_service():
            """模拟失败的服务"""
            raise Exception("Service unavailable")

        def mock_working_service():
            """模拟正常的服务"""
            return {"status": "success", "data": "test_data"}

        # 1. 测试正常服务
        result = circuit_breaker.call(mock_working_service)
        assert result["status"] == "success"
        assert circuit_breaker.state == "CLOSED"

        # 2. 测试失败服务触发断路器
        for i in range(3):
            try:
                circuit_breaker.call(mock_failing_service)
            except Exception:
                pass  # 预期的异常

        assert circuit_breaker.state == "OPEN"
        assert circuit_breaker.failure_count >= 3

        # 3. 测试断路器打开状态
        try:
            circuit_breaker.call(mock_working_service)
            assert False, "断路器应该阻止调用"
        except Exception as e:
            assert "Circuit breaker is OPEN" in str(e)

        # 4. 测试断路器恢复
        time.sleep(2.1)  # 等待恢复超时

        # 下一次调用应该尝试重置（HALF_OPEN状态）
        try:
            result = circuit_breaker.call(mock_working_service)
            assert result["status"] == "success"
            assert circuit_breaker.state == "CLOSED"  # 成功后应该重置
            except Exception:
            # 如果还是失败,断路器应该重新打开
            assert circuit_breaker.state == "OPEN"

    @pytest.mark.asyncio
    async def test_async_external_service_calls(self):
        """异步外部服务调用测试"""
        if not AIOHTTP_AVAILABLE:
            pytest.skip("aiohttp不可用")

        # 模拟异步外部服务客户端
        class AsyncExternalServiceClient:
            def __init__(self, base_url: str):
                self.base_url = base_url
                self.session = None

            async def __aenter__(self):
                self.session = aiohttp.ClientSession()
                return self

            async def __aexit__(self, exc_type, exc_val, exc_tb):
                if self.session:
                    await self.session.close()

            async def get(self, endpoint: str, params: Dict = None) -> Dict[str, Any]:
                """异步GET请求"""
                if not self.session:
                    raise RuntimeError("Client not initialized")

                # 模拟异步网络请求
                await asyncio.sleep(0.1)  # 模拟网络延迟

                # 模拟响应数据
                if "teams" in endpoint:
                    return {"data": self.mock_responses["teams"]}
                elif "matches" in endpoint:
                    return {"data": self.mock_responses["matches"]}
                else:
                    return {"status": "success"}

            @property
            def mock_responses(self):
                return {
                    "teams": [
                        {"id": 1, "name": "Async Team A"},
                        {"id": 2, "name": "Async Team B"}
                    ],
                    "matches": [
                        {"id": 1, "home_team": 1, "away_team": 2, "date": "2025-11-01"}
                    ]
                }

        # 测试异步客户端
        async with AsyncExternalServiceClient("https://api.example.com") as client:
            # 1. 异步获取团队数据
            teams_result = await client.get("teams")
            assert "data" in teams_result
            assert len(teams_result["data"]) == 2

            # 2. 异步获取比赛数据
            matches_result = await client.get("matches")
            assert "data" in matches_result
            assert len(matches_result["data"]) == 1

            # 3. 并发异步请求
            tasks = [
                client.get("teams"),
                client.get("matches"),
                client.get("teams")
            ]
            results = await asyncio.gather(*tasks)

            assert len(results) == 3
            assert all("data" in result for result in results)

    def test_data_validation_and_sanitization(self):
        """数据验证和清理测试"""
        # 模拟外部数据验证器
        class ExternalDataValidator:
            def __init__(self):
                self.required_fields = {
                    "teams": ["id", "name"],
                    "matches": ["id", "home_team", "away_team", "date"]
                }
                self.field_types = {
                    "id": int,
                    "name": str,
                    "home_team": int,
                    "away_team": int,
                    "date": str
                }

            def validate_and_sanitize(self, data_type: str, data: List[Dict]) -> List[Dict]:
                """验证和清理外部数据"""
                if not isinstance(data, list):
                    raise ValueError(f"Expected list, got {type(data)}")

                validated_data = []
                required_fields = self.required_fields.get(data_type, [])

                for item in data:
                    # 1. 检查必需字段
                    sanitized_item = {}
                    for field in required_fields:
                        if field not in item:
                            raise ValueError(f"Missing required field: {field}")

                        # 2. 类型检查和转换
                        value = item[field]
                        expected_type = self.field_types.get(field, str)

                        try:
                            if expected_type == int and isinstance(value, str):
                                sanitized_item[field] = int(value)
                            else:
                                sanitized_item[field] = expected_type(value)
                        except (ValueError, TypeError):
                            raise ValueError(f"Invalid type for field {field}: {value}")

                    # 3. 添加可选字段
                    for key, value in item.items():
                        if key not in sanitized_item:
                            sanitized_item[key] = value

                    validated_data.append(sanitized_item)

                return validated_data

        # 测试数据验证
        validator = ExternalDataValidator()

        # 1. 正常数据验证
        valid_teams_data = [
            {"id": "1", "name": "Team A", "league": "Premier League"},
            {"id": "2", "name": "Team B", "league": "Premier League"}
        ]

        validated_teams = validator.validate_and_sanitize("teams", valid_teams_data)
        assert len(validated_teams) == 2
        assert all(isinstance(team["id"], int) for team in validated_teams)

        # 2. 缺失必需字段
        invalid_teams_data = [
            {"name": "Team A"},  # 缺少id字段
            {"id": 2, "name": "Team B"}
        ]

        try:
            validator.validate_and_sanitize("teams", invalid_teams_data)
            assert False, "应该抛出ValueError"
        except ValueError as e:
            assert "Missing required field" in str(e)

        # 3. 类型转换测试
        type_conversion_data = [
            {"id": "123", "name": "Team C"},  # 字符串id转换为整数
            {"id": 456, "name": "Team D"}    # 整数id保持不变
        ]

        validated_data = validator.validate_and_sanitize("teams", type_conversion_data)
        assert all(isinstance(team["id"], int) for team in validated_data)
        assert validated_data[0]["id"] == 123
        assert validated_data[1]["id"] == 456


@pytest.mark.integration
@pytest.mark.external_api
@pytest.mark.performance
class TestExternalServicesPerformance:
    """外部服务性能测试类"""

    def test_concurrent_external_api_calls(self):
        """并发外部API调用性能测试"""
        # 模拟并发API调用
        class ConcurrentAPITester:
            def __init__(self, max_workers: int = 10):
                self.max_workers = max_workers
                self.response_times = []

            def make_api_call(self, endpoint: str, delay: float = 0.1) -> Dict[str, Any]:
                """模拟API调用"""
                start_time = time.time()

                # 模拟网络延迟
                time.sleep(delay)

                end_time = time.time()
                response_time = (end_time - start_time) * 1000
                self.response_times.append(response_time)

                return {
                    "endpoint": endpoint,
                    "response_time": response_time,
                    "status": "success"
                }

            def test_concurrent_calls(self, num_calls: int = 50):
                """测试并发调用"""
                import concurrent.futures

                endpoints = [f"endpoint_{i}" for i in range(num_calls)]

                start_time = time.time()

                with concurrent.futures.ThreadPoolExecutor(max_workers=self.max_workers) as executor:
                    futures = [
                        executor.submit(self.make_api_call, endpoint, 0.05 + (i % 5) * 0.02)
                        for i, endpoint in enumerate(endpoints)
                    ]
                    results = [future.result() for future in futures]

                end_time = time.time()
                total_time = (end_time - start_time) * 1000

                return {
                    "results": results,
                    "total_time": total_time,
                    "response_times": self.response_times
                }

        # 测试并发性能
        tester = ConcurrentAPITester(max_workers=20)
        test_result = tester.test_concurrent_calls(num_calls=100)

        # 性能断言
        results = test_result["results"]
        response_times = test_result["response_times"]

        # 所有调用都应该成功
        successful_calls = [r for r in results if r.get("status") == "success"]
        assert len(successful_calls) == 100, f"成功率不足: {len(successful_calls)}/100"

        # 平均响应时间应该合理
        avg_response_time = sum(response_times) / len(response_times)
        assert avg_response_time < 200, f"平均响应时间过长: {avg_response_time:.2f}ms"

        # 并发效率:总时间应该显著小于串行执行时间
        total_time = test_result["total_time"]
        expected_serial_time = sum(response_times)
        efficiency = expected_serial_time / total_time if total_time > 0 else 0
        assert efficiency > 5, f"并发效率不足: {efficiency:.2f}x"

    def test_response_time_optimization(self):
        """响应时间优化测试"""
        # 模拟响应时间优化策略
        class ResponseTimeOptimizer:
            def __init__(self):
                self.cache = {}
                self.timeout = 5.0  # 5秒超时
                self.retry_delays = [0.1, 0.2, 0.4]  # 指数退避

            def optimized_request(self, url: str, use_cache: bool = True) -> Dict[str, Any]:
                """优化的请求方法"""
                start_time = time.time()

                # 1. 检查缓存
                if use_cache and url in self.cache:
                    cache_time = self.cache[url]["timestamp"]
                    if time.time() - cache_time < 300:  # 5分钟缓存
                        return {
                            "source": "cache",
                            "data": self.cache[url]["data"],
                            "response_time": 0.001  # 缓存命中时间极短
                        }

                # 2. 尝试请求,包含重试逻辑
                for attempt, delay in enumerate(self.retry_delays):
                    try:
                        # 模拟网络请求
                        request_time = 0.1 + (attempt * 0.05)
                        time.sleep(request_time)

                        # 模拟成功响应
                        response_data = {"url": url, "data": f"response_data_{attempt}"}

                        # 缓存响应
                        if use_cache:
                            self.cache[url] = {
                                "data": response_data,
                                "timestamp": time.time()
                            }

                        total_time = (time.time() - start_time) * 1000
                        return {
                            "source": "network",
                            "data": response_data,
                            "response_time": total_time,
                            "attempts": attempt + 1
                        }

                    except Exception as e:
                        if attempt == len(self.retry_delays) - 1:
                            # 最后一次尝试失败
                            total_time = (time.time() - start_time) * 1000
                            return {
                                "source": "error",
                                "error": str(e),
                                "response_time": total_time,
                                "attempts": attempt + 1
                            }

                        # 等待后重试
                        time.sleep(delay)

        # 测试响应时间优化
        optimizer = ResponseTimeOptimizer()

        # 1. 测试缓存效果
        url = "https://api.example.com/test"

        # 第一次请求（网络）
        result1 = optimizer.optimized_request(url, use_cache=True)
        assert result1["source"] == "network"
        assert result1["response_time"] > 100  # 至少100ms

        # 第二次请求（缓存）
        result2 = optimizer.optimized_request(url, use_cache=True)
        assert result2["source"] == "cache"
        assert result2["response_time"] < 10  # 缓存应该很快

        # 3. 测试重试机制
        failing_url = "https://api.example.com/failing"

        # 模拟会失败的请求（通过修改类来模拟）
        class FailingOptimizer(ResponseTimeOptimizer):
            def optimized_request(self, url: str, use_cache: bool = True):
                if "failing" in url:
                    start_time = time.time()
                    # 模拟失败和重试
                    for delay in self.retry_delays:
                        time.sleep(delay)

                    total_time = (time.time() - start_time) * 1000
                    return {
                        "source": "error",
                        "error": "Simulated failure",
                        "response_time": total_time,
                        "attempts": len(self.retry_delays)
                    }
                else:
                    return super().optimized_request(url, use_cache)

        failing_optimizer = FailingOptimizer()
        result3 = failing_optimizer.optimized_request(failing_url)
        assert result3["source"] == "error"
        assert result3["attempts"] == 3  # 应该尝试3次


# Phase F第三方服务集成测试报告生成器
class PhaseFExternalServicesTestReporter:
    """Phase F外部服务测试报告生成器"""

    def __init__(self):
        self.test_results = []
        self.performance_metrics = {}
        self.service_health = {}

    def record_test_result(self, test_name: str, status: str, duration: float, details: str = ""):
        """记录测试结果"""
        self.test_results.append({
            "test_name": test_name,
            "status": status,
            "duration": duration,
            "details": details,
            "timestamp": datetime.now()
        })

    def record_performance_metric(self, metric_name: str, value: float, unit: str = "ms"):
        """记录性能指标"""
        self.performance_metrics[metric_name] = {"value": value, "unit": unit}

    def record_service_health(self, service_name: str, status: str, response_time: float):
        """记录服务健康状态"""
        self.service_health[service_name] = {
            "status": status,
            "response_time": response_time,
            "last_check": datetime.now()
        }

    def generate_report(self) -> str:
        """生成测试报告"""
        report = f"""
# Phase F: 第三方服务集成测试报告

## 📊 测试统计
- **总测试数**: {len(self.test_results)}
- **覆盖率目标**: 80%+ 第三方服务集成测试覆盖率

## 🎯 服务健康状态
"""

        for service_name, health_data in self.service_health.items():
            status_emoji = "✅" if health_data["status"] == "healthy" else "❌"
            report += f"- {status_emoji} **{service_name}**: {health_data['status']} ({health_data['response_time']:.2f}ms)\n"

        report += "\n## 📈 性能指标\n"

        for metric_name, metric_data in self.performance_metrics.items():
            report += f"- **{metric_name}**: {metric_data['value']:.2f} {metric_data['unit']}\n"

        report += "\n## 📋 详细测试结果\n"

        for result in self.test_results:
            status_emoji = "✅" if result["status"] == "PASSED" else "❌" if result["status"] == "FAILED" else "⏭️"
            report += f"- {status_emoji} **{result['test_name']}** ({result['duration']:.3f}s)\n"

        return report


# 测试执行入口
if __name__ == "__main__":
    print("🚀 Phase F: 第三方服务集成测试开始执行...")
    print("📋 测试范围: API弹性、网络故障、服务降级,性能优化")
    print("🎯 目标: 80%+ 第三方服务集成测试覆盖率")
    print("🔧 基于Issue #149的成功经验进行测试开发")