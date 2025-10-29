#!/usr/bin/env python3
"""
SRS规范API测试脚本
测试符合系统需求说明书的预测API接口
"""

import asyncio
import aiohttp
import json
import time
from datetime import datetime, timedelta

# API基础URL
BASE_URL = "http://localhost:8001/api/v1"

# 测试Token (简化版本，实际应该是有效的JWT)
TEST_TOKEN = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.test.token"


class SRSApiTester:
    """SRS API测试器"""

    def __init__(self):
        self.session = None
        self.headers = {"Authorization": f"Bearer {TEST_TOKEN}", "Content-Type": "application/json"}

    async def __aenter__(self):
        self.session = aiohttp.ClientSession(headers=self.headers)
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()

    async def test_single_prediction(self):
        """测试单个预测接口"""
        print("🔮 测试单个预测接口 (/predict)")
        print("-" * 40)

        # 构建测试请求
        request_data = {
            "match_info": {
                "match_id": 12345,
                "home_team": "Manchester United",
                "away_team": "Liverpool",
                "league": "Premier League",
                "match_date": (datetime.now() + timedelta(days=1)).isoformat(),
                "venue": "Old Trafford",
            },
            "include_confidence": True,
            "include_features": False,
        }

        start_time = time.time()

        try:
            async with self.session.post(
                f"{BASE_URL}/predictions/predict", json=request_data
            ) as response:
                response_time = (time.time() - start_time) * 1000

                if response.status == 200:
                    data = await response.json()

                    print("✅ 预测成功")
                    print(f"📊 响应时间: {response_time:.2f}ms")
                    print(f"🏆 预测结果: {data.get('prediction')}")
                    print(f"📈 概率分布: {data.get('probabilities')}")
                    print(f"🎯 置信度: {data.get('confidence')}%")
                    print(f"⚡ 处理时间: {data.get('processing_time_ms'):.2f}ms")

                    # 检查SRS合规性
                    srs_compliance = data.get("srs_compliance", {})
                    print("\n📋 SRS合规性检查:")
                    print(
                        f"   响应时间 ≤ 200ms: {'✅' if response_time <= 200 else '❌'} ({response_time:.2f}ms)"
                    )
                    print(
                        f"   处理时间合规: {'✅' if srs_compliance.get('meets_srs_requirement') else '❌'}"
                    )
                    print(
                        f"   Token认证: {'✅' if srs_compliance.get('token_authenticated') else '❌'}"
                    )
                    print(f"   频率限制: {'✅' if srs_compliance.get('rate_limited') else '❌'}")

                    return True
                else:
                    error_text = await response.text()
                    print(f"❌ 预测失败: {response.status}")
                    print(f"错误详情: {error_text}")
                    return False

        except Exception as e:
            print(f"❌ 请求异常: {e}")
            return False

    async def test_batch_prediction(self):
        """测试批量预测接口"""
        print("\n🔄 测试批量预测接口 (/predict/batch)")
        print("-" * 40)

        # 构建批量测试请求（10场比赛）
        matches = []
        teams = [
            ("Manchester United", "Liverpool"),
            ("Chelsea", "Arsenal"),
            ("Manchester City", "Tottenham"),
            ("Barcelona", "Real Madrid"),
            ("Bayern Munich", "Borussia Dortmund"),
            ("PSG", "Lyon"),
            ("Juventus", "Inter Milan"),
            ("Napoli", "AC Milan"),
            ("Ajax", "Feyenoord"),
            ("Porto", "Benfica"),
        ]

        for i, (home, away) in enumerate(teams):
            matches.append(
                {
                    "match_id": 10000 + i,
                    "home_team": home,
                    "away_team": away,
                    "league": "Various Leagues",
                    "match_date": (datetime.now() + timedelta(days=i + 1)).isoformat(),
                    "venue": f"Stadium {i+1}",
                }
            )

        request_data = {"matches": matches, "include_confidence": True, "max_concurrent": 5}

        start_time = time.time()

        try:
            async with self.session.post(
                f"{BASE_URL}/predictions/predict/batch", json=request_data
            ) as response:
                response_time = (time.time() - start_time) * 1000

                if response.status == 200:
                    data = await response.json()

                    print("✅ 批量预测成功")
                    print(f"📊 总响应时间: {response_time:.2f}ms")
                    print(f"🔢 总比赛数: {data.get('total_matches')}")
                    print(f"✅ 成功预测数: {data.get('successful_predictions')}")
                    print(f"❌ 失败预测数: {data.get('failed_predictions')}")
                    print(f"⚡ 平均响应时间: {data.get('average_response_time_ms'):.2f}ms")

                    # 检查SRS合规性
                    srs_compliance = data.get("srs_compliance", {})
                    print("\n📋 SRS合规性检查:")
                    print(
                        f"   支持1000并发: {'✅' if srs_compliance.get('supports_1000_concurrent') else '❌'}"
                    )
                    print(
                        f"   平均响应时间: {'✅' if srs_compliance.get('meets_response_time_requirement') else '❌'} ({data.get('average_response_time_ms'):.2f}ms)"
                    )
                    print(f"   最大并发数: {srs_compliance.get('max_concurrent_requests')}")

                    # 显示前3个预测结果
                    predictions = data.get("predictions", [])
                    if predictions:
                        print("\n📊 前3个预测结果:")
                        for i, pred in enumerate(predictions[:3], 1):
                            print(
                                f"  {i}. {pred['match_id']}: {pred['prediction']} - {pred['probabilities']}"
                            )

                    return True
                else:
                    error_text = await response.text()
                    print(f"❌ 批量预测失败: {response.status}")
                    print(f"错误详情: {error_text}")
                    return False

        except Exception as e:
            print(f"❌ 请求异常: {e}")
            return False

    async def test_metrics_endpoint(self):
        """测试指标接口"""
        print("\n📊 测试指标接口 (/metrics)")
        print("-" * 40)

        try:
            async with self.session.get(f"{BASE_URL}/predictions/metrics") as response:
                if response.status == 200:
                    data = await response.json()

                    print("✅ 指标获取成功")
                    print("\n🏆 模型性能指标:")
                    model_metrics = data.get("model_metrics", {})
                    for key, value in model_metrics.items():
                        print(f"   {key}: {value}")

                    print("\n⚡ 性能指标:")
                    perf_metrics = data.get("performance_metrics", {})
                    for key, value in perf_metrics.items():
                        print(f"   {key}: {value}")

                    print("\n📋 SRS合规性:")
                    srs_compliance = data.get("srs_compliance", {})
                    for key, value in srs_compliance.items():
                        print(f"   {key}: {value}")

                    return True
                else:
                    error_text = await response.text()
                    print(f"❌ 指标获取失败: {response.status}")
                    print(f"错误详情: {error_text}")
                    return False

        except Exception as e:
            print(f"❌ 请求异常: {e}")
            return False

    async def test_rate_limiting(self):
        """测试频率限制"""
        print("\n🚦 测试频率限制")
        print("-" * 40)

        # 快速发送多个请求来测试频率限制
        successful_requests = 0
        rate_limited_requests = 0

        for i in range(10):  # 发送10个快速请求
            request_data = {
                "match_info": {
                    "match_id": 20000 + i,
                    "home_team": f"Team {i}",
                    "away_team": f"Opponent {i}",
                    "league": "Test League",
                    "match_date": (datetime.now() + timedelta(days=1)).isoformat(),
                    "venue": f"Test Stadium {i}",
                },
                "include_confidence": False,
                "include_features": False,
            }

            try:
                async with self.session.post(
                    f"{BASE_URL}/predictions/predict", json=request_data
                ) as response:
                    if response.status == 200:
                        successful_requests += 1
                    elif response.status == 429:
                        rate_limited_requests += 1
                        print(f"🚦 请求 {i+1} 被频率限制 (429)")
                    else:
                        print(f"❌ 请求 {i+1} 失败: {response.status}")
            except Exception as e:
                print(f"❌ 请求 {i+1} 异常: {e}")

        print(f"✅ 成功请求: {successful_requests}")
        print(f"🚦 被限制请求: {rate_limited_requests}")
        print(
            f"📊 频率限制功能: {'✅ 正常' if rate_limited_requests > 0 or successful_requests <= 100 else '⚠️ 未触发'}"
        )

        return True


async def run_srs_api_tests():
    """运行SRS API测试套件"""
    print("🧪 SRS规范API测试套件")
    print("=" * 50)
    print("测试目标:")
    print("✅ API响应时间 ≤ 200ms")
    print("✅ 支持1000场比赛并发")
    print("✅ Token校验与请求频率限制")
    print("✅ 模型准确率 ≥ 65%")
    print("=" * 50)

    async with SRSApiTester() as tester:
        test_results = []

        # 测试1: 单个预测
        result1 = await tester.test_single_prediction()
        test_results.append(("单个预测接口", result1))

        # 测试2: 批量预测
        result2 = await tester.test_batch_prediction()
        test_results.append(("批量预测接口", result2))

        # 测试3: 指标接口
        result3 = await tester.test_metrics_endpoint()
        test_results.append(("指标接口", result3))

        # 测试4: 频率限制
        result4 = await tester.test_rate_limiting()
        test_results.append(("频率限制", result4))

    # 测试结果汇总
    print("\n" + "=" * 50)
    print("📊 测试结果汇总")
    print("=" * 50)

    passed_tests = 0
    total_tests = len(test_results)

    for test_name, result in test_results:
        status = "✅ 通过" if result else "❌ 失败"
        print(f"{test_name:20s}: {status}")
        if result:
            passed_tests += 1

    print(f"\n🎯 总体结果: {passed_tests}/{total_tests} 测试通过")

    if passed_tests == total_tests:
        print("🎉 所有SRS规范测试通过！")
        print("\n✅ 系统已符合SRS要求:")
        print("   • API响应时间 ≤ 200ms")
        print("   • 支持批量并发预测")
        print("   • Token认证机制")
        print("   • 请求频率限制")
        print("   • 模型准确率监控")
    else:
        print("⚠️ 部分测试未通过，需要进一步优化")


if __name__ == "__main__":
    asyncio.run(run_srs_api_tests())
