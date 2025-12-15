"""
手动验证 BaseTitanCollector 功能

测试异步采集器的核心功能，包括限流、重试、错误处理等。
"""

import sys

sys.path.insert(0, "/home/user/projects/FootballPrediction")

import asyncio
import json
import respx
import httpx
from unittest.mock import MagicMock, AsyncMock

from src.collectors.titan.base_collector import BaseTitanCollector
from src.collectors.titan.exceptions import (
    TitanScrapingError,
    TitanNetworkError,
    TitanRateLimitError,
)


async def test_fetch_json_success():
    """测试 200 OK: 成功返回 JSON"""
    print("\n" + "=" * 70)
    print("测试 1: 成功获取 JSON 数据")
    print("=" * 70)

    # 创建 Mock 限流器
    mock_rate_limiter = MagicMock()
    mock_rate_limiter.acquire = AsyncMock(return_value=True)

    # 创建采集器
    collector = BaseTitanCollector(
        base_url="https://live.titan007.com/api/odds",
        rate_limiter=mock_rate_limiter,
        max_retries=3,
    )

    # 模拟响应
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
                "updatetime": "2024-01-01 16:00:00",
            }
        ],
    }

    # 使用 respx mock
    with respx.mock:
        route = respx.get("https://live.titan007.com/api/odds/euro").mock(
            return_value=httpx.Response(200, json=mock_response)
        )

        # 执行请求
        result = await collector._fetch_json(
            "/euro", {"matchid": "2971465", "companyid": 8}
        )

        # 验证
        assert route.called, "应该调用 Titan API"
        assert result["matchid"] == "2971465", "应该返回正确的 matchid"
        assert result["success"] is True, "success 应该是 True"
        assert len(result["data"]) == 1, "应该有 1 条数据"
        assert result["data"][0]["companyid"] == 8, "companyid 应该是 8"

        print("✅ 请求成功！")
        print("   状态码: 200")
        print(f"   Match ID: {result['matchid']}")
        print(f"   公司: {result['data'][0]['companyname']}")
        print(
            f"   赔率: {result['data'][0]['homeodds']}/{result['data'][0]['drawodds']}/{result['data'][0]['awayodds']}"
        )
        print(f"   限流器被调用: {mock_rate_limiter.acquire.called}")

        # 清理
        await collector.close()

    return True


async def test_fetch_json_forbidden():
    """测试 403 Forbidden: 反爬拦截"""
    print("\n" + "=" * 70)
    print("测试 2: 403 Forbidden - 反爬拦截")
    print("=" * 70)

    mock_rate_limiter = MagicMock()
    mock_rate_limiter.acquire = AsyncMock(return_value=True)

    collector = BaseTitanCollector(rate_limiter=mock_rate_limiter)

    with respx.mock:
        route = respx.get("https://live.titan007.com/api/odds/euro").mock(
            return_value=httpx.Response(403, text="Forbidden - Access Denied")
        )

        # 应该抛出 TitanScrapingError
        try:
            await collector._fetch_json("/euro", {"matchid": "2971465"})
            assert False, "应该抛出 TitanScrapingError"
        except TitanScrapingError as e:
            assert route.called, "应该调用 Titan API"
            assert e.status_code == 403
            print("✅ 正确捕获 TitanScrapingError")
            print(f"   状态码: {e.status_code}")
            print(f"   错误消息: {str(e)}")

        await collector.close()

    return True


async def test_fetch_json_retry_success():
    """测试重试逻辑：前两次失败，第三次成功"""
    print("\n" + "=" * 70)
    print("测试 3: 重试机制 - 前两次失败，第三次成功")
    print("=" * 70)

    mock_rate_limiter = MagicMock()
    mock_rate_limiter.acquire = AsyncMock(return_value=True)

    collector = BaseTitanCollector(rate_limiter=mock_rate_limiter, max_retries=3)

    with respx.mock:
        # 第1次: 500 (服务器错误)
        # 第2次: 429 (限流)
        # 第3次: 200 (成功)
        route = respx.get("https://live.titan007.com/api/odds/handicap").mock(
            side_effect=[
                httpx.Response(500, text="Internal Server Error"),
                httpx.Response(429, json={"error": "Too Many Requests"}),
                httpx.Response(
                    200,
                    json={
                        "matchid": "2971466",
                        "success": True,
                        "data": [{"companyid": 8, "handicap": "0.25"}],
                    },
                ),
            ]
        )

        # 执行请求（应该自动重试，最终成功）
        result = await collector._fetch_json("/handicap", {"matchid": "2971466"})

        # 验证应该调用了 3 次
        assert route.call_count == 3, f"应该调用 3 次，实际调用 {route.call_count} 次"
        assert result["success"] is True
        assert result["matchid"] == "2971466"

        print("✅ 重试成功！")
        print(f"   总调用次数: {route.call_count}")
        print("   最终结果: HTTP 200 (成功)")
        print(f"   数据: {result['data']}")

        await collector.close()

    return True


async def test_fetch_json_rate_limit_error():
    """测试 429 限流错误"""
    print("\n" + "=" * 70)
    print("测试 4: 429 限流错误（会触发重试）")
    print("=" * 70)

    mock_rate_limiter = MagicMock()
    mock_rate_limiter.acquire = AsyncMock(return_value=True)

    collector = BaseTitanCollector(rate_limiter=mock_rate_limiter, max_retries=3)

    with respx.mock:
        # 前3次都返回 429
        route = respx.get("https://live.titan007.com/api/odds/overunder").mock(
            side_effect=[
                httpx.Response(429, headers={"Retry-After": "60"}),
                httpx.Response(429),
                httpx.Response(429),
            ]
        )

        try:
            await collector._fetch_json("/overunder", {"matchid": "2971467"})
            assert False, "应该抛出 TitanRateLimitError"
        except TitanRateLimitError as e:
            # 3次都失败后，应该抛出 RateLimitError
            assert route.call_count == 3
            print("✅ 正确捕获 TitanRateLimitError")
            print(f"   总调用次数: {route.call_count}")
            print("   状态码: 429")
            print(f"   重试等待: {e.retry_after} 秒")

        await collector.close()

    return True


async def test_fetch_json_jsonp_cleaning():
    """测试 JSONP 清洗和 BOM 头处理"""
    print("\n" + "=" * 70)
    print("测试 5: JSONP 清洗和 BOM 头处理")
    print("=" * 70)

    mock_rate_limiter = MagicMock()
    mock_rate_limiter.acquire = AsyncMock(return_value=True)

    collector = BaseTitanCollector(rate_limiter=mock_rate_limiter)

    # 模拟带有 BOM 头和 JSONP 包装器的响应
    jsonp_response = '\ufeffcallback({"matchid": "2971465", "success": true, "data": [{"companyid": 8}]});'

    with respx.mock:
        route = respx.get("https://live.titan007.com/api/odds/euro").mock(
            return_value=httpx.Response(200, text=jsonp_response)
        )

        # 执行请求
        result = await collector._fetch_json("/euro", {"matchid": "2971465"})

        # 验证：成功解析清洗后的 JSON
        assert route.called
        assert result["matchid"] == "2971465"
        assert result["success"] is True
        assert len(result["data"]) == 1
        assert result["data"][0]["companyid"] == 8

        print("✅ JSONP清洗成功！")
        print(f"   原始响应: {jsonp_response[:50]}...")
        print(f"   清洗后: {json.dumps(result)[:50]}...")
        print(
            f"   成功提取: matchid={result['matchid']}, companyid={result['data'][0]['companyid']}"
        )

        await collector.close()

    return True


async def test_fetch_json_timeout():
    """测试网络超时"""
    print("\n" + "=" * 70)
    print("测试 6: 网络超时")
    print("=" * 70)

    mock_rate_limiter = MagicMock()
    mock_rate_limiter.acquire = AsyncMock(return_value=True)

    collector = BaseTitanCollector(rate_limiter=mock_rate_limiter, timeout=1.0)

    with respx.mock:
        # 模拟连接超时
        route = respx.get("https://live.titan007.com/api/odds/euro").mock(
            side_effect=httpx.ConnectTimeout("Connection timeout")
        )

        try:
            await collector._fetch_json("/euro", {"matchid": "2971465"})
            assert False, "应该抛出 TitanNetworkError"
        except TitanNetworkError as e:
            assert route.called
            assert "timeout" in str(e).lower() or "connection" in str(e).lower()
            print("✅ 正确捕获 TitanNetworkError")
            print("   错误类型: 网络超时")
            print(f"   错误消息: {str(e)[:80]}")

        await collector.close()

    return True


async def test_limiter_integration():
    """测试限流器集成"""
    print("\n" + "=" * 70)
    print("测试 7: 限流器集成 - 5个并发请求")
    print("=" * 70)

    mock_rate_limiter = MagicMock()
    mock_rate_limiter.acquire = AsyncMock(return_value=True)

    collector = BaseTitanCollector(rate_limiter=mock_rate_limiter)

    with respx.mock:
        respx.get("https://live.titan007.com/api/odds/euro").mock(
            return_value=httpx.Response(200, json={"success": True, "data": []})
        )

        # 发起 5 个并发请求
        tasks = [
            collector._fetch_json("/euro", {"matchid": f"297146{i}"}) for i in range(5)
        ]
        results = await asyncio.gather(*tasks)

        # 验证：所有请求都成功
        assert len(results) == 5
        for result in results:
            assert result["success"] is True

        # 验证：限流器被调用了 5 次
        assert mock_rate_limiter.acquire.call_count == 5
        for call in mock_rate_limiter.acquire.call_args_list:
            assert call.args[0] == "titan_odds"

        print("✅ 限流器集成成功！")
        print("   发起请求: 5 个并发")
        print(f"   限流器调用: {mock_rate_limiter.acquire.call_count} 次")
        print("   限流器 key: 'titan_odds'")
        print("   全部请求成功: ✓")

        await collector.close()

    return True


async def test_user_agent_header():
    """测试 User-Agent 头"""
    print("\n" + "=" * 70)
    print("测试 8: User-Agent 请求头")
    print("=" * 70)

    mock_rate_limiter = MagicMock()
    mock_rate_limiter.acquire = AsyncMock(return_value=True)

    collector = BaseTitanCollector(rate_limiter=mock_rate_limiter)

    with respx.mock:
        route = respx.get("https://live.titan007.com/api/odds/euro").mock(
            return_value=httpx.Response(200, json={"success": True, "data": []})
        )

        # 执行请求
        await collector._fetch_json("/euro", {"matchid": "2971465"})

        # 验证请求头
        assert route.called
        request = route.calls[0].request
        assert "user-agent" in request.headers
        ua = request.headers["user-agent"]
        assert len(ua) > 0
        print("✅ User-Agent 设置成功！")
        print(f"   User-Agent: {ua[:60]}...")

        await collector.close()

    return True


async def main():
    """运行所有测试"""
    print("\n" + "🔥" * 35)
    print("BaseTitanCollector - 手动验证测试")
    print("🔥" * 35)

    tests = [
        ("✓ 成功获取 JSON", test_fetch_json_success),
        ("✓ 403 Forbidden 处理", test_fetch_json_forbidden),
        ("✓ 重试机制", test_fetch_json_retry_success),
        ("✓ 429 限流错误", test_fetch_json_rate_limit_error),
        ("✓ JSONP 清洗", test_fetch_json_jsonp_cleaning),
        ("✓ 网络超时", test_fetch_json_timeout),
        ("✓ 限流器集成", test_limiter_integration),
        ("✓ User-Agent 头", test_user_agent_header),
    ]

    passed = 0
    failed = 0

    for test_name, test_func in tests:
        try:
            print(f"\n{'='*70}")
            print(f"测试: {test_name}")
            print("=" * 70)
            await test_func()
            passed += 1
            print(f"{'='*70}")
            print(f"✅ {test_name} 通过")
            print("=" * 70)
        except Exception as e:
            failed += 1
            print(f"{'='*70}")
            print(f"❌ {test_name} 失败")
            print(f"错误: {e}")
            print("=" * 70)
            import traceback

            traceback.print_exc()

    print("\n" + "🎉" * 35)
    print(f"测试完成: {passed} 通过, {failed} 失败")
    print("🎉" * 35 + "\n")

    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
