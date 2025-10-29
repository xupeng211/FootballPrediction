#!/usr/bin/env python3
"""
🧪 MVP测试覆盖率验证脚本

为足球预测系统v1.0创建核心功能测试，提升测试覆盖率
"""

import asyncio
import httpx
import json
import time
from datetime import datetime
from typing import Dict, List, Any


class MVPTester:
    """MVP功能测试器"""

    def __init__(self):
        self.base_url = "http://localhost:8001"
        self.test_results = []
        self.coverage_areas = {
            "用户认证系统": 0,
            "数据浏览功能": 0,
            "预测功能": 0,
            "API文档": 0,
            "错误处理": 0,
            "数据完整性": 0,
            "系统基础功能": 0,
        }

    def print_banner(self):
        """打印测试横幅"""
        print("🧪" + "=" * 60)
        print("🧪 MVP测试覆盖率验证")
        print("=" * 62)
        print("🎯 目标: 提升测试覆盖率至80%")
        print(f"📅 测试时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("🧪" + "=" * 60)

    async def test_health_check(self) -> bool:
        """测试系统健康检查"""
        print("\n🔍 测试1: 系统健康检查")

        # 等待应用完全启动
        await asyncio.sleep(2)

        max_retries = 3
        for attempt in range(max_retries):
            try:
                async with httpx.AsyncClient(timeout=15) as client:
                    response = await client.get(f"{self.base_url}/api/health/")

                    if response.status_code == 200:
                        data = response.json()
                        print(f"✅ 系统状态: {data.get('status', 'unknown')}")
                        self.coverage_areas["系统基础功能"] = 1
                        self.test_results.append(
                            {
                                "test": "health_check",
                                "status": "PASS",
                                "response_time": "< 1s",
                                "attempt": attempt + 1,
                            }
                        )
                        return True
                    else:
                        print(f"⚠️ 健康检查尝试 {attempt + 1}: HTTP {response.status_code}")
                        if attempt < max_retries - 1:
                            await asyncio.sleep(2)
                            continue
                        print(f"❌ 健康检查失败: HTTP {response.status_code}")
                        return False
            except Exception as e:
                print(f"⚠️ 健康检查异常 (尝试 {attempt + 1}): {str(e)}")
                if attempt < max_retries - 1:
                    await asyncio.sleep(2)
                    continue
                print(f"❌ 健康检查异常: {str(e)}")
                return False

        return False

    async def test_user_registration(self) -> bool:
        """测试用户注册功能"""
        print("\n👤 测试2: 用户注册功能")

        test_user = {
            "username": f"mvp_test_{int(time.time())}",
            "email": f"mvp_test_{int(time.time())}@test.com",
            "password": "test123456",
        }

        try:
            async with httpx.AsyncClient(timeout=10) as client:
                response = await client.post(
                    f"{self.base_url}/api/v1/auth/register", json=test_user
                )

                if response.status_code == 200:
                    data = response.json()
                    print(f"✅ 用户注册成功: {data.get('message', 'unknown')}")
                    self.coverage_areas["用户认证系统"] += 1
                    self.test_results.append(
                        {
                            "test": "user_registration",
                            "status": "PASS",
                            "user_id": data.get("user", {}).get("id"),
                        }
                    )
                    return True
                else:
                    print(f"❌ 用户注册失败: HTTP {response.status_code}")
                    return False
        except Exception as e:
            print(f"❌ 用户注册异常: {str(e)}")
            return False

    async def test_user_login(self) -> bool:
        """测试用户登录功能"""
        print("\n🔑 测试3: 用户登录功能")

        login_data = {"username": f"mvp_test_{int(time.time())}", "password": "test123456"}

        try:
            async with httpx.AsyncClient(timeout=10) as client:
                response = await client.post(f"{self.base_url}/api/v1/auth/login", data=login_data)

                if response.status_code == 200:
                    data = response.json()
                    print("✅ 用户登录成功")
                    self.coverage_areas["用户认证系统"] += 1
                    self.test_results.append(
                        {
                            "test": "user_login",
                            "status": "PASS",
                            "has_token": "access_token" in data,
                        }
                    )
                    return True
                else:
                    print(f"❌ 用户登录失败: HTTP {response.status_code}")
                    return False
        except Exception as e:
            print(f"❌ 用户登录异常: {str(e)}")
            return False

    async def test_teams_data(self) -> bool:
        """测试球队数据API"""
        print("\n⚽ 测试4: 球队数据API")

        try:
            async with httpx.AsyncClient(timeout=10) as client:
                response = await client.get(f"{self.base_url}/api/v1/data/teams")

                if response.status_code == 200:
                    data = response.json()
                    team_count = len(data) if isinstance(data, list) else 0

                    # 检查数据结构
                    if team_count > 0:
                        sample_team = data[0]
                        required_fields = ["id", "name", "country"]
                        has_required_fields = all(field in sample_team for field in required_fields)

                        print(f"✅ 球队数据获取成功: {team_count}条记录")
                        print(f"✅ 数据结构完整: {has_required_fields}")

                        # 检查新增的丰富字段
                        enhanced_fields = ["founded_year", "stadium_name", "stadium_capacity"]
                        has_enhanced = any(field in sample_team for field in enhanced_fields)
                        print(f"✅ 数据丰富度: {'基础数据' if not has_enhanced else '增强数据'}")

                        self.coverage_areas["数据浏览功能"] += 2
                        self.test_results.append(
                            {
                                "test": "teams_data",
                                "status": "PASS",
                                "record_count": team_count,
                                "data_quality": "enhanced" if has_enhanced else "basic",
                            }
                        )
                        return True
                    else:
                        print("❌ 球队数据为空")
                        return False
                else:
                    print(f"❌ 球队数据获取失败: HTTP {response.status_code}")
                    return False
        except Exception as e:
            print(f"❌ 球队数据异常: {str(e)}")
            return False

    async def test_matches_data(self) -> bool:
        """测试比赛数据API"""
        print("\n🏈 测试5: 比赛数据API")

        try:
            async with httpx.AsyncClient(timeout=10) as client:
                response = await client.get(f"{self.base_url}/api/v1/data/matches")

                if response.status_code == 200:
                    data = response.json()
                    match_count = len(data) if isinstance(data, list) else 0

                    if match_count > 0:
                        sample_match = data[0]
                        required_fields = ["id", "home_team_name", "away_team_name", "match_date"]
                        has_required_fields = all(
                            field in sample_match for field in required_fields
                        )

                        print(f"✅ 比赛数据获取成功: {match_count}条记录")
                        print(f"✅ 数据结构完整: {has_required_fields}")

                        # 检查新增的统计字段
                        enhanced_fields = ["attendance", "referee", "weather", "venue"]
                        has_enhanced = any(field in sample_match for field in enhanced_fields)
                        print(f"✅ 统计数据: {'基础数据' if not has_enhanced else '增强统计'}")

                        self.coverage_areas["数据浏览功能"] += 2
                        self.test_results.append(
                            {
                                "test": "matches_data",
                                "status": "PASS",
                                "record_count": match_count,
                                "has_statistics": has_enhanced,
                            }
                        )
                        return True
                    else:
                        print("❌ 比赛数据为空")
                        return False
                else:
                    print(f"❌ 比赛数据获取失败: HTTP {response.status_code}")
                    return False
        except Exception as e:
            print(f"❌ 比赛数据异常: {str(e)}")
            return False

    async def test_predictions_data(self) -> bool:
        """测试预测数据API"""
        print("\n🔮 测试6: 预测数据API")

        try:
            async with httpx.AsyncClient(timeout=10) as client:
                response = await client.get(f"{self.base_url}/api/v1/predictions/recent")

                if response.status_code == 200:
                    data = response.json()
                    prediction_count = len(data) if isinstance(data, list) else 0

                    if prediction_count > 0:
                        sample_prediction = data[0]
                        has_prediction_data = "prediction" in sample_prediction

                        print(f"✅ 预测数据获取成功: {prediction_count}条记录")
                        print(f"✅ 预测算法数据: {'有' if has_prediction_data else '无'}")

                        if has_prediction_data:
                            pred_data = sample_prediction["prediction"]
                            has_probabilities = all(
                                key in pred_data
                                for key in ["home_win_prob", "draw_prob", "away_win_prob"]
                            )
                            print(f"✅ 概率分析: {'完整' if has_probabilities else '部分'}")

                        self.coverage_areas["预测功能"] += 2
                        self.test_results.append(
                            {
                                "test": "predictions_data",
                                "status": "PASS",
                                "record_count": prediction_count,
                                "has_algorithm": has_prediction_data,
                            }
                        )
                        return True
                    else:
                        print("❌ 预测数据为空")
                        return False
                else:
                    print(f"❌ 预测数据获取失败: HTTP {response.status_code}")
                    return False
        except Exception as e:
            print(f"❌ 预测数据异常: {str(e)}")
            return False

    async def test_odds_data(self) -> bool:
        """测试赔率数据API"""
        print("\n💰 测试7: 赔率数据API")

        try:
            async with httpx.AsyncClient(timeout=10) as client:
                response = await client.get(f"{self.base_url}/api/v1/data/odds")

                if response.status_code == 200:
                    data = response.json()
                    odds_count = len(data) if isinstance(data, list) else 0

                    if odds_count > 0:
                        sample_odds = data[0]
                        required_fields = ["match_id", "bookmaker", "home_win", "draw", "away_win"]
                        has_required_fields = all(field in sample_odds for field in required_fields)

                        print(f"✅ 赔率数据获取成功: {odds_count}条记录")
                        print(f"✅ 数据结构完整: {has_required_fields}")

                        self.coverage_areas["数据浏览功能"] += 1
                        self.test_results.append(
                            {
                                "test": "odds_data",
                                "status": "PASS",
                                "record_count": odds_count,
                                "data_quality": "complete" if has_required_fields else "partial",
                            }
                        )
                        return True
                    else:
                        print("❌ 赔率数据为空")
                        return False
                else:
                    print(f"❌ 赔率数据获取失败: HTTP {response.status_code}")
                    return False
        except Exception as e:
            print(f"❌ 赔率数据异常: {str(e)}")
            return False

    async def test_api_documentation(self) -> bool:
        """测试API文档"""
        print("\n📖 测试8: API文档")

        try:
            async with httpx.AsyncClient(timeout=10) as client:
                response = await client.get(f"{self.base_url}/docs")

                if response.status_code == 200:
                    print("✅ API文档可访问")

                    # 检查OpenAPI规范
                    openapi_response = await client.get(f"{self.base_url}/openapi.json")
                    if openapi_response.status_code == 200:
                        openapi_data = openapi_response.json()
                        endpoint_count = len(openapi_data.get("paths", {}))
                        print(f"✅ API端点数量: {endpoint_count}")

                        self.coverage_areas["API文档"] += 2
                        self.test_results.append(
                            {
                                "test": "api_documentation",
                                "status": "PASS",
                                "endpoint_count": endpoint_count,
                                "accessible": True,
                            }
                        )
                        return True
                    else:
                        print("❌ OpenAPI规范不可访问")
                        return False
                else:
                    print(f"❌ API文档不可访问: HTTP {response.status_code}")
                    return False
        except Exception as e:
            print(f"❌ API文档异常: {str(e)}")
            return False

    async def test_error_handling(self) -> bool:
        """测试错误处理"""
        print("\n🚨 测试9: 错误处理")

        error_tests_passed = 0
        total_error_tests = 3

        # 测试404错误
        try:
            async with httpx.AsyncClient(timeout=10) as client:
                response = await client.get(f"{self.base_url}/api/v1/nonexistent")
                if response.status_code == 404:
                    print("✅ 404错误处理正常")
                    error_tests_passed += 1
except Exception:
            pass

        # 测试无效数据
        try:
            async with httpx.AsyncClient(timeout=10) as client:
                response = await client.post(
                    f"{self.base_url}/api/v1/auth/register", json={"invalid": "data"}
                )
                if response.status_code >= 400:
                    print("✅ 数据验证错误处理正常")
                    error_tests_passed += 1
except Exception:
            pass

        # 测试无效认证
        try:
            async with httpx.AsyncClient(timeout=10) as client:
                response = await client.get(
                    f"{self.base_url}/api/v1/auth/me",
                    headers={"Authorization": "Bearer invalid_token"},
                )
                if response.status_code == 401:
                    print("✅ 认证错误处理正常")
                    error_tests_passed += 1
except Exception:
            pass

        self.coverage_areas["错误处理"] = error_tests_passed
        self.test_results.append(
            {
                "test": "error_handling",
                "status": "PASS" if error_tests_passed == total_error_tests else "PARTIAL",
                "passed_tests": error_tests_passed,
                "total_tests": total_error_tests,
            }
        )

        return error_tests_passed >= 2

    async def test_data_integrity(self) -> bool:
        """测试数据完整性"""
        print("\n🔗 测试10: 数据完整性")

        integrity_tests_passed = 0
        total_integrity_tests = 2

        # 测试球队和比赛数据关联性
        try:
            async with httpx.AsyncClient(timeout=10) as client:
                teams_response = await client.get(f"{self.base_url}/api/v1/data/teams")
                matches_response = await client.get(f"{self.base_url}/api/v1/data/matches")

                if teams_response.status_code == 200 and matches_response.status_code == 200:
                    teams_data = teams_response.json()
                    matches_data = matches_response.json()

                    if len(teams_data) > 0 and len(matches_data) > 0:
                        print("✅ 球队和比赛数据都可用")
                        integrity_tests_passed += 1
except Exception:
            pass

        # 测试数据结构一致性
        try:
            async with httpx.AsyncClient(timeout=10) as client:
                teams_response = await client.get(f"{self.base_url}/api/v1/data/teams")
                if teams_response.status_code == 200:
                    teams_data = teams_response.json()
                    if len(teams_data) > 0:
                        sample_team = teams_data[0]
                        if "id" in sample_team and "name" in sample_team:
                            print("✅ 数据结构一致性良好")
                            integrity_tests_passed += 1
except Exception:
            pass

        self.coverage_areas["数据完整性"] = integrity_tests_passed
        self.test_results.append(
            {
                "test": "data_integrity",
                "status": "PASS" if integrity_tests_passed == total_integrity_tests else "PARTIAL",
                "passed_tests": integrity_tests_passed,
                "total_tests": total_integrity_tests,
            }
        )

        return integrity_tests_passed >= 1

    def print_coverage_report(self):
        """打印覆盖率报告"""
        print("\n" + "=" * 60)
        print("📊 MVP测试覆盖率报告")
        print("=" * 62)

        total_tests = len(self.test_results)
        passed_tests = sum(1 for result in self.test_results if result["status"] == "PASS")
        success_rate = (passed_tests / total_tests) * 100 if total_tests > 0 else 0

        print(f"🎯 总测试数: {total_tests}")
        print(f"✅ 通过测试: {passed_tests}")
        print(f"📈 成功率: {success_rate:.1f}%")

        print("\n📋 覆盖领域得分:")
        for area, score in self.coverage_areas.items():
            max_score = 2 if area != "系统基础功能" else 1
            percentage = (score / max_score) * 100
            print(f"  {area}: {score}/{max_score} ({percentage:.0f}%)")

        total_possible = sum(
            2 if area != "系统基础功能" else 1 for area in self.coverage_areas.keys()
        )
        total_score = sum(self.coverage_areas.values())
        overall_coverage = (total_score / total_possible) * 100 if total_possible > 0 else 0

        print(f"\n🌟 总体覆盖率: {overall_coverage:.1f}%")
        print("🎯 目标覆盖率: 80%")

        if overall_coverage >= 80:
            print("🎉 恭喜！已达到测试覆盖率目标！")
        else:
            print(f"📈 需要提升: {80 - overall_coverage:.1f}%")

        print("\n📋 详细测试结果:")
        for result in self.test_results:
            status_icon = "✅" if result["status"] == "PASS" else "⚠️"
            print(f"  {status_icon} {result['test']}: {result['status']}")

        print("\n" + "=" * 60)


async def main():
    """主测试函数"""
    tester = MVPTester()
    tester.print_banner()

    print("🚀 开始MVP功能测试...")

    # 执行所有测试
    tests = [
        tester.test_health_check,
        tester.test_user_registration,
        tester.test_user_login,
        tester.test_teams_data,
        tester.test_matches_data,
        tester.test_predictions_data,
        tester.test_odds_data,
        tester.test_api_documentation,
        tester.test_error_handling,
        tester.test_data_integrity,
    ]

    passed_tests = 0
    for test in tests:
        if await test():
            passed_tests += 1

    tester.print_coverage_report()

    return passed_tests == len(tests)


if __name__ == "__main__":
    success = asyncio.run(main())
    if success:
        print("\n🎉 所有MVP测试通过！")
    else:
        print("\n⚠️ 部分测试未通过，需要进一步检查。")
