"""
测试：Titan007 基础采集器

使用 respx 模拟 HTTP 响应，测试异步采集器的核心功能。
"""

import pytest
import respx
import httpx
from unittest.mock import AsyncMock, MagicMock
from datetime import datetime

from src.collectors.titan.exceptions import (
    TitanScrapingError,
    TitanNetworkError,
    TitanParsingError,
)
from src.collectors.titan.base_collector import BaseTitanCollector
from src.schemas.titan import EuroOddsResponse


@pytest.fixture
def mock_rate_limiter():
    """创建 Mock 限流器"""
    rate_limiter = MagicMock()
    rate_limiter.acquire = AsyncMock(return_value=True)
    return rate_limiter


@pytest.fixture
def collector(mock_rate_limiter):
    """创建 BaseTitanCollector 实例"""
    return BaseTitanCollector(
        base_url="https://live.titan007.com/api/odds",
        rate_limiter=mock_rate_limiter,
        max_retries=3,
    )


@respx.mock
@pytest.mark.asyncio
async def test_fetch_json_success(collector):
    """测试 200 OK: 成功返回 JSON"""
    # 模拟 Titan API 返回欧赔数据
    endpoint = "/euro"
    params = {"matchid": "2971465", "companyid": 8}

    mock_response = {
        "matchid": "2971465",
        "success": True,
        "data": [
            {
                "companyid": 8,
                "companyname": "Bet365",
                "homeodds": 1.85,
                "drawodds": 3.60,
                "awayodds": 4.20,
                "updatetime": "2024-01-01 16:00:00"
            }
        ],
        "message": None
    }

    # 配置 respx mock
    route = respx.get("https://live.titan007.com/api/odds/euro").mock(
        return_value=httpx.Response(200, json=mock_response)
    )

    # 执行请求
    result = await collector._fetch_json(endpoint, params)

    # 验证
    assert route.called, "应该调用 Titan API"
    assert result == mock_response, "应该返回正确的 JSON 数据"
    assert result["success"] is True
    assert len(result["data"]) == 1
    assert result["data"][0]["companyid"] == 8

    # 验证限流器被调用
    collector.rate_limiter.acquire.assert_called_once_with("titan_odds")


@respx.mock
@pytest.mark.asyncio
async def test_fetch_json_forbidden(collector):
    """测试 403 Forbidden: 反爬拦截，触发 TitanScrapingError"""
    endpoint = "/euro"
    params = {"matchid": "2971465", "companyid": 8}

    # 模拟 403 响应（反爬拦截）
    route = respx.get("https://live.titan007.com/api/odds/euro").mock(
        return_value=httpx.Response(
            403,
            text="Forbidden - Access Denied",
            headers={"Content-Type": "text/html; charset=utf-8"}
        )
    )

    # 执行请求，应该抛出 TitanScrapingError
    with pytest.raises(TitanScrapingError) as exc_info:
        await collector._fetch_json(endpoint, params)

    # 验证
    assert route.called, "应该调用 Titan API"
    error = exc_info.value
    assert error.status_code == 403
    assert "403" in str(error)
    assert "Forbidden" in str(error)

    # 验证限流器被调用
    collector.rate_limiter.acquire.assert_called_once_with("titan_odds")


@respx.mock
@pytest.mark.asyncio
async def test_fetch_json_retry_success(collector):
    """测试重试逻辑：前两次失败，第三次成功"""
    endpoint = "/handicap"
    params = {"matchid": "2971466", "companyid": 8}

    # 模拟 API 行为：
    # 第1次: 500 (服务器错误)
    # 第2次: 429 (限流)
    # 第3次: 200 (成功)
    route = respx.get("https://live.titan007.com/api/odds/handicap").mock(side_effect=[
        httpx.Response(500, text="Internal Server Error"),
        httpx.Response(429, json={"error": "Too Many Requests"}),
        httpx.Response(200, json={
            "matchid": "2971466",
            "success": True,
            "data": [],
            "message": "No handicap data"
        })
    ])

    # 执行请求（应该自动重试，最终成功）
    result = await collector._fetch_json(endpoint, params)

    # 验证：调用了 3 次（2次失败 + 1次成功）
    assert route.call_count == 3, f"应该调用 3 次，实际调用 {route.call_count} 次"
    assert result["success"] is True
    assert result["matchid"] == "2971466"

    # 验证限流器被调用 3 次（每次重试都会调用）
    assert collector.rate_limiter.acquire.call_count == 3


@respx.mock
@pytest.mark.asyncio
async def test_fetch_json_max_retries_exceeded(collector):
    """测试最大重试次数 exceeded"""
    endpoint = "/overunder"
    params = {"matchid": "2971467", "companyid": 8}

    # 模拟：前3次都失败（超过最大重试次数）
    route = respx.get("https://live.titan007.com/api/odds/overunder").mock(side_effect=[
        httpx.Response(500, text="Internal Server Error"),
        httpx.Response(500, text="Internal Server Error"),
        httpx.Response(500, text="Internal Server Error"),
        httpx.Response(200, json={"success": True})  # 这个不会被调用
    ])

    # 执行请求，应该抛出 TitanNetworkError
    with pytest.raises(TitanNetworkError) as exc_info:
        await collector._fetch_json(endpoint, params)

    # 验证：只调用了 3 次（达到最大重试次数后停止）
    assert route.call_count == 3, f"应该调用 3 次，实际调用 {route.call_count} 次"
    assert "Max retry attempts exceeded" in str(exc_info.value)
    assert exc_info.value.status_code == 500


@respx.mock
@pytest.mark.asyncio
async def test_fetch_json_jsonp_cleaning(collector):
    """测试 JSONP 清洗和 BOM 头处理"""
    endpoint = "/euro"
    params = {"matchid": "2971465", "companyid": 8}

    # 模拟带有 BOM 头和 JSONP 包装器的响应
    jsonp_response = '\ufeffcallback({"matchid": "2971465", "success": true, "data": []});'

    route = respx.get("https://live.titan007.com/api/odds/euro").mock(
        return_value=httpx.Response(200, text=jsonp_response)
    )

    # 执行请求
    result = await collector._fetch_json(endpoint, params)

    # 验证：成功解析清洗后的 JSON
    assert route.called
    assert result["matchid"] == "2971465"
    assert result["success"] is True
    assert result["data"] == []


@respx.mock
@pytest.mark.asyncio
async def test_fetch_json_network_error(collector):
    """测试网络错误（连接超时）"""
    endpoint = "/euro"
    params = {"matchid": "2971465", "companyid": 8}

    # 模拟网络错误（连接超时）
    route = respx.get("https://live.titan007.com/api/odds/euro").mock(
        side_effect=httpx.ConnectTimeout("Connection timeout")
    )

    # 执行请求，应该抛出 TitanNetworkError
    with pytest.raises(TitanNetworkError) as exc_info:
        await collector._fetch_json(endpoint, params)

    # 验证
    assert route.called
    assert "Connection timeout" in str(exc_info.value)


@respx.mock
@pytest.mark.asyncio
async def test_fetch_json_unexpected_format(collector):
    """测试意外响应格式（不是 JSON）"""
    endpoint = "/euro"
    params = {"matchid": "2971465", "companyid": 8}

    # 模拟返回 HTML 页面（可能是错误页面）
    route = respx.get("https://live.titan007.com/api/odds/euro").mock(
        return_value=httpx.Response(
            200,
            text="<html><body>Unexpected HTML response</body></html>",
            headers={"Content-Type": "text/html"}
        )
    )

    # 执行请求，应该抛出 TitanParsingError
    with pytest.raises(TitanParsingError) as exc_info:
        await collector._fetch_json(endpoint, params)

    # 验证
    assert route.called
    assert "JSON parsing failed" in str(exc_info.value)
    assert exc_info.value.raw_content is not None


@respx.mock
@pytest.mark.asyncio
async def test_rate_limiter_integration(collector):
    """测试限流器集成"""
    endpoint = "/euro"
    params = {"matchid": "2971465", "companyid": 8}

    # 模拟多个并发请求
    route = respx.get("https://live.titan007.com/api/odds/euro").mock(
        return_value=httpx.Response(200, json={"success": True, "data": []})
    )

    # 发起 5 个并发请求
    tasks = [collector._fetch_json(endpoint, params) for _ in range(5)]
    results = await asyncio.gather(*tasks)

    # 验证：所有请求都成功
    assert len(results) == 5
    for result in results:
        assert result["success"] is True

    # 验证：限流器被调用了 5 次，每次都使用正确的 key
    assert collector.rate_limiter.acquire.call_count == 5
    for call in collector.rate_limiter.acquire.call_args_list:
        assert call.args[0] == "titan_odds"


@respx.mock
@pytest.mark.asyncio
async def test_custom_headers_and_user_agent(collector):
    """测试自定义请求头 (User-Agent)"""
    endpoint = "/euro"
    params = {"matchid": "2971465", "companyid": 8}

    # 创建一个 route 来捕获请求头
    route = respx.get("https://live.titan007.com/api/odds/euro")
    route.mock(return_value=httpx.Response(200, json={"success": True, "data": []}))

    # 执行请求
    await collector._fetch_json(endpoint, params)

    # 验证：请求被正确调用
    assert route.called

    # 验证：请求头中包含 User-Agent
    request = route.calls[0].request
    assert "user-agent" in request.headers
    assert len(request.headers["user-agent"]) > 0


@respx.mock
@pytest.mark.asyncio
async def test_parameter_encoding(collector):
    """测试参数编码"""
    endpoint = "/euro"
    params = {"matchid": "2971465", "companyid": 8, "test": "value with spaces"}

    route = respx.get("https://live.titan007.com/api/odds/euro").mock(
        return_value=httpx.Response(200, json={"success": True, "data": []})
    )

    # 执行请求
    await collector._fetch_json(endpoint, params)

    # 验证：参数被正确编码
    assert route.called
    request = route.calls[0].request

    url = str(request.url)
    assert "matchid=2971465" in url
    assert "companyid=8" in url
    # URL 编码的空格应该是 %20 或 +
    assert "value+with+spaces" in url or "value%20with%20spaces" in url


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
