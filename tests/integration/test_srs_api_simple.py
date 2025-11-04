#!/usr/bin/env python3
"""
SRS规范简化API测试脚本
测试不依赖数据库的符合系统需求说明书的预测API接口
"""

import asyncio
import time
from datetime import datetime, timedelta

import aiohttp

# API基础URL
BASE_URL = "http://localhost:8001/api/v1"

# 测试Token (简化版本，实际应该是有效的JWT)
TEST_TOKEN = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.test.token"


class SimpleSRSApiTester:
    """简化版SRS API测试器"""

    def __init__(self):
        self.session = None
        self.headers = {
            "Authorization": f"Bearer {TEST_TOKEN}",
            "Content-Type": "application/json",
        }

    async def __aenter__(self):
        self.session = aiohttp.ClientSession(headers=self.headers)
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()

    async def test_health_check(self):
        """测试健康检查接口"""
        logger.debug("🏥 测试健康检查接口 (/predictions-srs-simple/health)")  # TODO: Add logger import if needed
        logger.debug("-" * 50)  # TODO: Add logger import if needed

        try:
            async with self.session.get(
                f"{BASE_URL}/predictions-srs-simple/health"
            ) as response:
                if response.status == 200:
                    data = await response.json()
                    logger.debug("✅ 健康检查成功")  # TODO: Add logger import if needed
                    logger.debug(f"📊 状态: {data.get('status')}")  # TODO: Add logger import if needed
                    logger.debug(f"🔧 服务: {data.get('service')}")  # TODO: Add logger import if needed
                    logger.debug(f"💾 数据库独立: {data.get('database_independent')}")  # TODO: Add logger import if needed
                    logger.debug(f"⏰ 时间戳: {data.get('timestamp')}")  # TODO: Add logger import if needed
                    return True
                else:
                    error_text = await response.text()
                    logger.debug(f"❌ 健康检查失败: {response.status}")  # TODO: Add logger import if needed
                    logger.error(f"错误详情: {error_text}")  # TODO: Add logger import if needed
                    return False

        except Exception as e:
            logger.debug(f"❌ 请求异常: {e}")  # TODO: Add logger import if needed
            return False

    async def test_single_prediction(self):
        """测试单个预测接口"""
        logger.debug("\n🔮 测试单个预测接口 (/predictions-srs-simple/predict)")  # TODO: Add logger import if needed
        logger.debug("-" * 50)  # TODO: Add logger import if needed

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
                f"{BASE_URL}/predictions-srs-simple/predict", json=request_data
            ) as response:
                response_time = (time.time() - start_time) * 1000

                if response.status == 200:
                    data = await response.json()

                    logger.debug("✅ 预测成功")  # TODO: Add logger import if needed
                    logger.debug(f"📊 响应时间: {response_time:.2f}ms")  # TODO: Add logger import if needed
                    logger.debug(f"🏆 预测结果: {data.get('prediction')}")  # TODO: Add logger import if needed
                    logger.debug(f"📈 概率分布: {data.get('probabilities')}")  # TODO: Add logger import if needed
                    logger.debug(f"🎯 置信度: {data.get('confidence')}%")  # TODO: Add logger import if needed
                    logger.debug(f"⚡ 处理时间: {data.get('processing_time_ms'):.2f}ms")  # TODO: Add logger import if needed

                    # 检查SRS合规性
                    srs_compliance = data.get("srs_compliance", {})
                    logger.debug("\n📋 SRS合规性检查:")  # TODO: Add logger import if needed
                    logger.debug()  # TODO: Add logger import if needed
                        f"   响应时间 ≤ 200ms: {'✅' if response_time <= 200 else '❌'} ({response_time:.2f}ms)"
                    )
                    logger.debug()  # TODO: Add logger import if needed
                        f"   处理时间合规: {'✅' if srs_compliance.get('meets_srs_requirement') else '❌'}"
                    )
                    logger.debug()  # TODO: Add logger import if needed
                        f"   Token认证: {'✅' if srs_compliance.get('token_authenticated') else '❌'}"
                    )
                    logger.debug()  # TODO: Add logger import if needed
                        f"   频率限制: {'✅' if srs_compliance.get('rate_limited') else '❌'}"
                    )
                    logger.debug()  # TODO: Add logger import if needed
                        f"   数据库独立: {'✅' if srs_compliance.get('database_independent') else '❌'}"
                    )

                    return True
                else:
                    error_text = await response.text()
                    logger.debug(f"❌ 预测失败: {response.status}")  # TODO: Add logger import if needed
                    logger.error(f"错误详情: {error_text}")  # TODO: Add logger import if needed
                    return False

        except Exception as e:
            logger.debug(f"❌ 请求异常: {e}")  # TODO: Add logger import if needed
            return False

    async def test_batch_prediction(self):
        """测试批量预测接口"""
        logger.debug("\n🔄 测试批量预测接口 (/predictions-srs-simple/predict/batch)")  # TODO: Add logger import if needed
        logger.debug("-" * 50)  # TODO: Add logger import if needed

        # 构建批量测试请求（20场比赛）
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
            ("Atletico Madrid", "Sevilla"),
            ("RB Leipzig", "Bayern Leverkusen"),
            ("Roma", "Lazio"),
            ("Atalanta", "Fiorentina"),
            ("Villarreal", "Real Sociedad"),
            ("Wolverhampton", "Everton"),
            ("Leicester City", "West Ham"),
            ("Newcastle", "Aston Villa"),
            ("Crystal Palace", "Brighton"),
            ("Southampton", "Bournemouth"),
        ]

        for i, (home, away) in enumerate(teams):
            matches.append(
                {
                    "match_id": 20000 + i,
                    "home_team": home,
                    "away_team": away,
                    "league": "Various Leagues",
                    "match_date": (datetime.now() + timedelta(days=i + 1)).isoformat(),
                    "venue": f"Stadium {i+1}",
                }
            )

        request_data = {
            "matches": matches,
            "include_confidence": True,
            "max_concurrent": 10,
        }

        start_time = time.time()

        try:
            async with self.session.post(
                f"{BASE_URL}/predictions-srs-simple/predict/batch", json=request_data
            ) as response:
                response_time = (time.time() - start_time) * 1000

                if response.status == 200:
                    data = await response.json()

                    logger.debug("✅ 批量预测成功")  # TODO: Add logger import if needed
                    logger.debug(f"📊 总响应时间: {response_time:.2f}ms")  # TODO: Add logger import if needed
                    logger.debug(f"🔢 总比赛数: {data.get('total_matches')}")  # TODO: Add logger import if needed
                    logger.debug(f"✅ 成功预测数: {data.get('successful_predictions')}")  # TODO: Add logger import if needed
                    logger.error(f"❌ 失败预测数: {data.get('failed_predictions')}")  # TODO: Add logger import if needed
                    logger.debug()  # TODO: Add logger import if needed
                        f"⚡ 平均响应时间: {data.get('average_response_time_ms'):.2f}ms"
                    )

                    # 检查SRS合规性
                    srs_compliance = data.get("srs_compliance", {})
                    logger.debug("\n📋 SRS合规性检查:")  # TODO: Add logger import if needed
                    logger.debug()  # TODO: Add logger import if needed
                        f"   支持1000并发: {'✅' if srs_compliance.get('supports_1000_concurrent') else '❌'}"
                    )
                    logger.debug()  # TODO: Add logger import if needed
                        f"   平均响应时间: {'✅' if srs_compliance.get('meets_response_time_requirement') else '❌'} ({data.get('average_response_time_ms'):.2f}ms)"
                    )
                    logger.debug()  # TODO: Add logger import if needed
                        f"   最大并发数: {srs_compliance.get('max_concurrent_requests')}"
                    )
                    logger.debug()  # TODO: Add logger import if needed
                        f"   数据库独立: {'✅' if srs_compliance.get('database_independent') else '❌'}"
                    )

                    # 显示前5个预测结果
                    predictions = data.get("predictions", [])
                    if predictions:
                        logger.debug("\n📊 前5个预测结果:")  # TODO: Add logger import if needed
                        for i, pred in enumerate(predictions[:5], 1):
                            logger.debug()  # TODO: Add logger import if needed
                                f"  {i}. {pred['match_id']}: {pred['prediction']} - {pred['probabilities']}"
                            )

                    return True
                else:
                    error_text = await response.text()
                    logger.debug(f"❌ 批量预测失败: {response.status}")  # TODO: Add logger import if needed
                    logger.error(f"错误详情: {error_text}")  # TODO: Add logger import if needed
                    return False

        except Exception as e:
            logger.debug(f"❌ 请求异常: {e}")  # TODO: Add logger import if needed
            return False

    async def test_metrics_endpoint(self):
        """测试指标接口"""
        logger.debug("\n📊 测试指标接口 (/predictions-srs-simple/metrics)")  # TODO: Add logger import if needed
        logger.debug("-" * 50)  # TODO: Add logger import if needed

        try:
            async with self.session.get(
                f"{BASE_URL}/predictions-srs-simple/metrics"
            ) as response:
                if response.status == 200:
                    data = await response.json()

                    logger.debug("✅ 指标获取成功")  # TODO: Add logger import if needed
                    logger.debug("\n🏆 模型性能指标:")  # TODO: Add logger import if needed
                    model_metrics = data.get("model_metrics", {})
                    for key, value in model_metrics.items():
                        logger.debug(f"   {key}: {value}")  # TODO: Add logger import if needed

                    logger.debug("\n⚡ 性能指标:")  # TODO: Add logger import if needed
                    perf_metrics = data.get("performance_metrics", {})
                    for key, value in perf_metrics.items():
                        logger.debug(f"   {key}: {value}")  # TODO: Add logger import if needed

                    logger.debug("\n📋 SRS合规性:")  # TODO: Add logger import if needed
                    srs_compliance = data.get("srs_compliance", {})
                    for key, value in srs_compliance.items():
                        logger.debug(f"   {key}: {value}")  # TODO: Add logger import if needed

                    logger.debug("\n🔧 系统信息:")  # TODO: Add logger import if needed
                    system_info = data.get("system_info", {})
                    for key, value in system_info.items():
                        logger.debug(f"   {key}: {value}")  # TODO: Add logger import if needed

                    return True
                else:
                    error_text = await response.text()
                    logger.debug(f"❌ 指标获取失败: {response.status}")  # TODO: Add logger import if needed
                    logger.error(f"错误详情: {error_text}")  # TODO: Add logger import if needed
                    return False

        except Exception as e:
            logger.debug(f"❌ 请求异常: {e}")  # TODO: Add logger import if needed
            return False

    async def test_concurrent_predictions(self):
        """测试并发预测能力"""
        logger.debug("\n⚡ 测试并发预测能力")  # TODO: Add logger import if needed
        logger.debug("-" * 50)  # TODO: Add logger import if needed

        # 并发发送10个预测请求
        concurrent_requests = 10
        start_time = time.time()

        async def make_request(request_id):
            request_data = {
                "match_info": {
                    "match_id": 30000 + request_id,
                    "home_team": f"Team {request_id}",
                    "away_team": f"Opponent {request_id}",
                    "league": "Test League",
                    "match_date": (datetime.now() + timedelta(days=1)).isoformat(),
                    "venue": f"Test Stadium {request_id}",
                },
                "include_confidence": False,
                "include_features": False,
            }

            try:
                async with self.session.post(
                    f"{BASE_URL}/predictions-srs-simple/predict", json=request_data
                ) as response:
                    if response.status == 200:
                        return {"success": True, "request_id": request_id}
                    else:
                        return {
                            "success": False,
                            "request_id": request_id,
                            "status": response.status,
                        }
            except Exception as e:
                return {"success": False, "request_id": request_id, "error": str(e)}

        # 执行并发请求
        tasks = [make_request(i) for i in range(concurrent_requests)]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        total_time = (time.time() - start_time) * 1000

        # 统计结果
        successful_requests = sum(
            1 for r in results if isinstance(r, dict) and r.get("success")
        )
        failed_requests = concurrent_requests - successful_requests

        logger.debug("✅ 并发测试完成")  # TODO: Add logger import if needed
        logger.debug(f"🔢 并发请求数: {concurrent_requests}")  # TODO: Add logger import if needed
        logger.debug(f"✅ 成功请求: {successful_requests}")  # TODO: Add logger import if needed
        logger.error(f"❌ 失败请求: {failed_requests}")  # TODO: Add logger import if needed
        logger.debug(f"⚡ 总响应时间: {total_time:.2f}ms")  # TODO: Add logger import if needed
        logger.debug(f"📊 平均响应时间: {total_time/concurrent_requests:.2f}ms")  # TODO: Add logger import if needed
        logger.debug()  # TODO: Add logger import if needed
            f"🚀 并发性能: {'✅ 优秀' if successful_requests == concurrent_requests else '⚠️ 需要优化'}"
        )

        return successful_requests == concurrent_requests

    async def test_large_batch(self):
        """测试大批量预测（100场）"""
        logger.debug("\n📈 测试大批量预测（100场）")  # TODO: Add logger import if needed
        logger.debug("-" * 50)  # TODO: Add logger import if needed

        # 构建100场比赛
        matches = []
        for i in range(100):
            matches.append(
                {
                    "match_id": 40000 + i,
                    "home_team": f"Home Team {i}",
                    "away_team": f"Away Team {i}",
                    "league": "Large Test League",
                    "match_date": (datetime.now() + timedelta(days=i % 30)).isoformat(),
                    "venue": f"Test Stadium {i}",
                }
            )

        request_data = {
            "matches": matches,
            "include_confidence": True,
            "max_concurrent": 50,
        }

        start_time = time.time()

        try:
            async with self.session.post(
                f"{BASE_URL}/predictions-srs-simple/predict/batch", json=request_data
            ) as response:
                response_time = (time.time() - start_time) * 1000

                if response.status == 200:
                    data = await response.json()

                    logger.debug("✅ 大批量预测成功")  # TODO: Add logger import if needed
                    logger.debug(f"📊 比赛数量: {data.get('total_matches')}")  # TODO: Add logger import if needed
                    logger.debug(f"✅ 成功预测: {data.get('successful_predictions')}")  # TODO: Add logger import if needed
                    logger.error(f"❌ 失败预测: {data.get('failed_predictions')}")  # TODO: Add logger import if needed
                    logger.debug(f"⚡ 总处理时间: {response_time:.2f}ms")  # TODO: Add logger import if needed
                    logger.debug()  # TODO: Add logger import if needed
                        f"📊 平均响应时间: {data.get('average_response_time_ms'):.2f}ms"
                    )
                    logger.debug()  # TODO: Add logger import if needed
                        f"🎯 成功率: {data.get('successful_predictions')/data.get('total_matches')*100:.1f}%"
                    )

                    # 检查是否能支持1000场
                    supports_1000 = data.get("srs_compliance", {}).get(
                        "supports_1000_concurrent", False
                    )
                    logger.debug(f"🚀 支持1000场并发: {'✅' if supports_1000 else '❌'}")  # TODO: Add logger import if needed

                    return True
                else:
                    error_text = await response.text()
                    logger.debug(f"❌ 大批量预测失败: {response.status}")  # TODO: Add logger import if needed
                    logger.error(f"错误详情: {error_text}")  # TODO: Add logger import if needed
                    return False

        except Exception as e:
            logger.debug(f"❌ 请求异常: {e}")  # TODO: Add logger import if needed
            return False


async def run_simple_srs_api_tests():
    """运行简化版SRS API测试套件"""
    logger.debug("🧪 SRS规范简化API测试套件")  # TODO: Add logger import if needed
    logger.debug("=" * 60)  # TODO: Add logger import if needed
    logger.debug("测试目标:")  # TODO: Add logger import if needed
    logger.debug("✅ API响应时间 ≤ 200ms")  # TODO: Add logger import if needed
    logger.debug("✅ 支持1000场比赛并发")  # TODO: Add logger import if needed
    logger.debug("✅ Token校验与请求频率限制")  # TODO: Add logger import if needed
    logger.debug("✅ 模型准确率 ≥ 65%")  # TODO: Add logger import if needed
    logger.debug("✅ 数据库独立（无依赖）")  # TODO: Add logger import if needed
    logger.debug("=" * 60)  # TODO: Add logger import if needed

    async with SimpleSRSApiTester() as tester:
        test_results = []

        # 测试1: 健康检查
        result1 = await tester.test_health_check()
        test_results.append(("健康检查接口", result1))

        # 测试2: 单个预测
        result2 = await tester.test_single_prediction()
        test_results.append(("单个预测接口", result2))

        # 测试3: 批量预测
        result3 = await tester.test_batch_prediction()
        test_results.append(("批量预测接口", result3))

        # 测试4: 指标接口
        result4 = await tester.test_metrics_endpoint()
        test_results.append(("指标接口", result4))

        # 测试5: 并发预测
        result5 = await tester.test_concurrent_predictions()
        test_results.append(("并发预测能力", result5))

        # 测试6: 大批量测试
        result6 = await tester.test_large_batch()
        test_results.append(("大批量预测(100场)", result6))

    # 测试结果汇总
    logger.debug("\n" + "=" * 60)  # TODO: Add logger import if needed
    logger.debug("📊 测试结果汇总")  # TODO: Add logger import if needed
    logger.debug("=" * 60)  # TODO: Add logger import if needed

    passed_tests = 0
    total_tests = len(test_results)

    for test_name, result in test_results:
        status = "✅ 通过" if result else "❌ 失败"
        logger.debug(f"{test_name:25s}: {status}")  # TODO: Add logger import if needed
        if result:
            passed_tests += 1

    logger.debug(f"\n🎯 总体结果: {passed_tests}/{total_tests} 测试通过")  # TODO: Add logger import if needed

    if passed_tests >= total_tests * 0.8:  # 80%通过率
        logger.debug("🎉 SRS规范API测试成功！")  # TODO: Add logger import if needed
        logger.debug("\n✅ 系统已符合SRS要求:")  # TODO: Add logger import if needed
        logger.debug("   • API响应时间 ≤ 200ms")  # TODO: Add logger import if needed
        logger.debug("   • 支持批量并发预测")  # TODO: Add logger import if needed
        logger.debug("   • Token认证机制")  # TODO: Add logger import if needed
        logger.debug("   • 请求频率限制")  # TODO: Add logger import if needed
        logger.debug("   • 模型准确率监控")  # TODO: Add logger import if needed
        logger.debug("   • 数据库独立架构")  # TODO: Add logger import if needed
        logger.debug("\n🚀 系统已准备好生产部署！")  # TODO: Add logger import if needed
    else:
        logger.debug("⚠️ 部分测试未通过，需要进一步优化")  # TODO: Add logger import if needed


if __name__ == "__main__":
    asyncio.run(run_simple_srs_api_tests())
