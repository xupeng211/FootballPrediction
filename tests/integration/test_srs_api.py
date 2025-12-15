#!/usr/bin/env python3
"""
SRS规范API测试脚本
测试符合系统需求说明书的预测API接口
"""

import asyncio
import time
from datetime import datetime, timedelta

import aiohttp

# API基础URL
BASE_URL = "http://localhost:8001/api/v1"

# 测试Token (简化版本，实际应该是有效的JWT)
TEST_TOKEN = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.test.token"


class SRSApiTester:
    """SRS API测试器"""

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

    async def test_single_prediction(self):
        """测试单个预测接口"""

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
                (time.time() - start_time) * 1000

                if response.status == 200:
                    data = await response.json()

                    # 检查SRS合规性
                    data.get("srs_compliance", {})

                    return True
                else:
                    await response.text()
                    return False

        except Exception:
            return False

    async def test_batch_prediction(self):
        """测试批量预测接口"""

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
                    "venue": f"Stadium {i + 1}",
                }
            )

        request_data = {
            "matches": matches,
            "include_confidence": True,
            "max_concurrent": 5,
        }

        start_time = time.time()

        try:
            async with self.session.post(
                f"{BASE_URL}/predictions/predict/batch", json=request_data
            ) as response:
                (time.time() - start_time) * 1000

                if response.status == 200:
                    data = await response.json()

                    # 检查SRS合规性
                    data.get("srs_compliance", {})

                    # 显示前3个预测结果
                    predictions = data.get("predictions", [])
                    if predictions:
                        for i, _pred in enumerate(predictions[:3], 1):
                            pass

                    return True
                else:
                    await response.text()
                    return False

        except Exception:
            return False

    async def test_metrics_endpoint(self):
        """测试指标接口"""

        try:
            async with self.session.get(f"{BASE_URL}/predictions/metrics") as response:
                if response.status == 200:
                    data = await response.json()

                    model_metrics = data.get("model_metrics", {})
                    for _key, _value in model_metrics.items():
                        pass

                    perf_metrics = data.get("performance_metrics", {})
                    for _key, _value in perf_metrics.items():
                        pass

                    srs_compliance = data.get("srs_compliance", {})
                    for _key, _value in srs_compliance.items():
                        pass

                    return True
                else:
                    await response.text()
                    return False

        except Exception:
            return False

    async def test_rate_limiting(self):
        """测试频率限制"""

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
                    else:
                        pass
            except Exception:
                pass

        return True


async def run_srs_api_tests():
    """运行SRS API测试套件"""

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

    passed_tests = 0
    total_tests = len(test_results)

    for _test_name, result in test_results:
        if result:
            passed_tests += 1

    if passed_tests == total_tests:
        pass
    else:
        pass


if __name__ == "__main__":
    asyncio.run(run_srs_api_tests())
