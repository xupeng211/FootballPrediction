"""
Titan007 具体采集器单元测试

测试欧赔、亚盘、大小球三个采集器的功能。
"""

import pytest
import respx
import httpx
from unittest.mock import MagicMock, AsyncMock

from src.collectors.titan.constants import CompanyID
from src.collectors.titan.collectors import (
    TitanEuroCollector,
    TitanAsianCollector,
    TitanOverUnderCollector,
)


@pytest.fixture
def mock_rate_limiter():
    """创建 Mock 限流器"""
    rate_limiter = MagicMock()
    rate_limiter.acquire = AsyncMock(return_value=True)
    return rate_limiter


@pytest.fixture
def euro_collector(mock_rate_limiter):
    """创建欧赔采集器"""
    return TitanEuroCollector(rate_limiter=mock_rate_limiter)


@pytest.fixture
def asian_collector(mock_rate_limiter):
    """创建亚盘采集器"""
    return TitanAsianCollector(rate_limiter=mock_rate_limiter)


@pytest.fixture
def overunder_collector(mock_rate_limiter):
    """创建大小球采集器"""
    return TitanOverUnderCollector(rate_limiter=mock_rate_limiter)


# ==============================================================================
# 欧赔采集器测试
# ==============================================================================


@respx.mock
@pytest.mark.asyncio
async def test_titan_euro_collector_success(euro_collector):
    """测试欧赔采集器 - 成功获取并解析数据"""
    match_id = "2971465"
    company_id = CompanyID.BET365

    # 模拟 Titan 欧赔接口响应
    mock_response = {
        "matchid": match_id,
        "success": True,
        "data": [
            {
                "cid": company_id,  # 公司ID
                "cname": "Bet365",  # 公司名称
                "h": 1.85,  # h = home win (主胜赔率)
                "d": 3.60,  # d = draw (平局赔率)
                "a": 4.20,  # a = away win (客胜赔率)
                "go": 1.85,  # go = current home win
                "go2": 3.60,  # go2 = current draw
                "go3": 4.20,  # go3 = current away win
                "utime": "2024-01-01 16:00:00",  # 更新时间
            }
        ],
    }

    route = respx.get("https://live.titan007.com/api/odds/euro").mock(
        return_value=httpx.Response(200, json=mock_response)
    )

    result = await euro_collector.fetch_euro_odds(
        match_id=match_id, company_id=company_id
    )

    # 验证请求被调用
    assert route.called
    request = route.calls[0].request
    assert str(request.url).endswith("/euro")

    # 验证解析后的数据
    assert result is not None
    assert result["match_id"] == match_id
    assert result["company_id"] == company_id
    assert result["company_name"] == "Bet365"
    assert result["home_win"] == 1.85
    assert result["draw"] == 3.60
    assert result["away_win"] == 4.20

    # 验证限流器被调用
    euro_collector.rate_limiter.acquire.assert_called_once_with("titan_odds")


@respx.mock
@pytest.mark.asyncio
async def test_titan_euro_collector_missing_fields(euro_collector):
    """测试欧赔采集器 - 缺少关键字段"""
    match_id = "2971465"

    # 模拟缺少关键字段的响应
    mock_response = {
        "matchid": match_id,
        "success": True,
        "data": [
            {
                "cid": CompanyID.BET365,
                "cname": "Bet365",
                # 缺少 h, d, a 字段
            }
        ],
    }

    route = respx.get("https://live.titan007.com/api/odds/euro").mock(
        return_value=httpx.Response(200, json=mock_response)
    )

    result = await euro_collector.fetch_euro_odds(
        match_id=match_id, company_id=CompanyID.BET365
    )

    assert route.called
    # 缺少关键字段应该返回 None
    assert result is None


# ==============================================================================
# 亚盘采集器测试
# ==============================================================================


@respx.mock
@pytest.mark.asyncio
async def test_titan_asian_collector_success(asian_collector):
    """测试亚盘采集器 - 成功获取并解析数据"""
    match_id = "2971465"
    company_id = CompanyID.CROWN

    # 模拟 Titan 亚盘接口响应
    mock_response = {
        "matchid": match_id,
        "success": True,
        "data": [
            {
                "cid": company_id,  # 公司ID
                "cname": "Crown",  # 公司名称
                "h": 0.85,  # h = home_odds (上盘赔率)
                "a": 1.05,  # a = away_odds (下盘赔率)
                "l": "0.25",  # l = line (让球盘口)
                "go": 0.85,  # go = current home_odds
                "go2": 1.05,  # go2 = current away_odds
                "go3": "0.25",  # go3 = current line
                "utime": "2024-01-01 16:00:00",
            }
        ],
    }

    route = respx.get("https://live.titan007.com/api/odds/handicap").mock(
        return_value=httpx.Response(200, json=mock_response)
    )

    result = await asian_collector.fetch_asian_handicap(
        match_id=match_id, company_id=company_id
    )

    assert route.called
    request = route.calls[0].request
    assert str(request.url).endswith("/handicap")

    # 验证解析后的数据
    assert result is not None
    assert result["match_id"] == match_id
    assert result["company_id"] == company_id
    assert result["company_name"] == "Crown"
    assert result["home_odds"] == 0.85  # 上盘赔率
    assert result["away_odds"] == 1.05  # 下盘赔率
    assert result["handicap"] == "0.25"  # 盘口


@respx.mock
@pytest.mark.asyncio
async def test_titan_asian_collector_invalid_handicap(asian_collector):
    """测试亚盘采集器 - 无效的盘口值"""
    match_id = "2971465"

    # 模拟盘口值为空字符串
    mock_response = {
        "matchid": match_id,
        "success": True,
        "data": [
            {
                "cid": CompanyID.BET365,
                "cname": "Bet365",
                "h": 0.95,
                "a": 0.95,
                "l": "",  # 盘口为空
            }
        ],
    }

    route = respx.get("https://live.titan007.com/api/odds/handicap").mock(
        return_value=httpx.Response(200, json=mock_response)
    )

    result = await asian_collector.fetch_asian_handicap(
        match_id=match_id, company_id=CompanyID.BET365
    )

    assert route.called
    # 无效盘口应该返回 None
    assert result is None


# ==============================================================================
# 大小球采集器测试
# ==============================================================================


@respx.mock
@pytest.mark.asyncio
async def test_titan_overunder_collector_success(overunder_collector):
    """测试大小球采集器 - 成功获取并解析数据"""
    match_id = "2971465"
    company_id = CompanyID.PINNACLE

    # 模拟 Titan 大小球接口响应
    mock_response = {
        "matchid": match_id,
        "success": True,
        "data": [
            {
                "cid": company_id,  # 公司ID
                "cname": "Pinnacle",  # 公司名称
                "o": 0.82,  # o = over_odds (大球赔率)
                "u": 1.08,  # u = under_odds (小球赔率)
                "l": "2.5",  # l = line (盘口)
                "go": 0.82,  # go = current over_odds
                "go2": 1.08,  # go2 = current under_odds
                "go3": "2.5",  # go3 = current line
                "utime": "2024-01-01 16:00:00",
            }
        ],
    }

    route = respx.get("https://live.titan007.com/api/odds/overunder").mock(
        return_value=httpx.Response(200, json=mock_response)
    )

    result = await overunder_collector.fetch_over_under(
        match_id=match_id, company_id=company_id
    )

    assert route.called
    request = route.calls[0].request
    assert str(request.url).endswith("/overunder")

    # 验证解析后的数据
    assert result is not None
    assert result["match_id"] == match_id
    assert result["company_id"] == company_id
    assert result["company_name"] == "Pinnacle"
    assert result["over_odds"] == 0.82  # 大球赔率
    assert result["under_odds"] == 1.08  # 小球赔率
    assert result["handicap"] == "2.5"  # 盘口


# ==============================================================================
# 错误处理测试
# ==============================================================================


@respx.mock
@pytest.mark.asyncio
async def test_titan_collectors_403_error(euro_collector):
    """测试采集器 - 403 反爬错误"""
    match_id = "2971465"

    route = respx.get("https://live.titan007.com/api/odds/euro").mock(
        return_value=httpx.Response(403, text="Forbidden")
    )

    from src.collectors.titan.exceptions import TitanScrapingError

    with pytest.raises(TitanScrapingError) as exc_info:
        await euro_collector.fetch_euro_odds(
            match_id=match_id, company_id=CompanyID.BET365
        )

    assert route.called
    assert exc_info.value.status_code == 403


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
