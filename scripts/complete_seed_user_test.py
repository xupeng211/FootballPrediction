#!/usr/bin/env python3
"""
🌱 完整种子用户测试脚本

模拟真实种子用户的使用场景，测试完整的用户旅程
"""

import asyncio
import json
import time
import random
from datetime import datetime, timedelta
import httpx


class SeedUserTester:
    """种子用户测试器"""

    def __init__(self):
        self.api_base_url = "http://localhost:8000"
        self.test_results = []
        self.auth_token = None
        self.user_data = {}
        self.test_scenarios = []

    def log_test(self, test_name: str, success: bool, details: str = "", duration: float = 0):
        """记录测试结果"""
        result = {
            "test_name": test_name,
            "success": success,
            "details": details,
            "duration": duration,
            "timestamp": datetime.now().isoformat(),
        }
        self.test_results.append(result)

        status = "✅" if success else "❌"
        print(f"{status} {test_name}")
        if details:
            print(f"   📝 {details}")
        if duration > 0:
            print(f"   ⏱️  耗时: {duration:.2f}秒")

    async def register_test_user(self):
        """注册测试用户"""
        print("\n👤 步骤1: 用户注册")

        # 生成唯一的测试用户数据
        timestamp = int(time.time())
        self.user_data = {
            "username": f"seed_user_{timestamp}",
            "email": f"seed_user_{timestamp}@example.com",
            "password": "test_password_123",
        }

        start_time = time.time()
        try:
            async with httpx.AsyncClient(timeout=10) as client:
                response = await client.post(
                    f"{self.api_base_url}/api/v1/auth/register", json=self.user_data
                )
                duration = time.time() - start_time

                if response.status_code in [200, 201]:
                    self.log_test("用户注册", True, f"HTTP {response.status_code}", duration)
                    register_result = response.json()
                    print(
                        f"   📝 注册结果: {json.dumps(register_result, indent=2, ensure_ascii=False)}"
                    )
                    return True
                else:
                    self.log_test(
                        "用户注册",
                        False,
                        f"HTTP {response.status_code}: {response.text[:100]}",
                        duration,
                    )
                    return False
        except Exception as e:
            duration = time.time() - start_time
            self.log_test("用户注册", False, f"连接错误: {str(e)}", duration)
            return False

    async def login_test_user(self):
        """登录测试用户"""
        print("\n🔐 步骤2: 用户登录")

        start_time = time.time()
        try:
            login_data = {
                "username": self.user_data["username"],
                "password": self.user_data["password"],
            }
            async with httpx.AsyncClient(timeout=10) as client:
                response = await client.post(
                    f"{self.api_base_url}/api/v1/auth/login", data=login_data
                )
                duration = time.time() - start_time

                if response.status_code == 200:
                    self.log_test("用户登录", True, f"HTTP {response.status_code}", duration)
                    login_result = response.json()
                    self.auth_token = login_result.get("access_token", "")
                    print(
                        f"   📝 登录结果: {json.dumps(login_result, indent=2, ensure_ascii=False)}"
                    )
                    return True
                else:
                    self.log_test(
                        "用户登录",
                        False,
                        f"HTTP {response.status_code}: {response.text[:100]}",
                        duration,
                    )
                    return False
        except Exception as e:
            duration = time.time() - start_time
            self.log_test("用户登录", False, f"连接错误: {str(e)}", duration)
            return False

    async def explore_football_data(self):
        """探索足球数据"""
        print("\n⚽ 步骤3: 探索足球数据")

        data_endpoints = [
            ("获取球队列表", "/api/v1/data/teams"),
            ("获取联赛列表", "/api/v1/data/leagues"),
            ("获取比赛列表", "/api/v1/data/matches"),
            ("获取赔率信息", "/api/v1/data/odds"),
        ]

        headers = {"Authorization": self.auth_token} if self.auth_token else {}
        success_count = 0

        for name, endpoint in data_endpoints:
            start_time = time.time()
            try:
                async with httpx.AsyncClient(timeout=10) as client:
                    response = await client.get(f"{self.api_base_url}{endpoint}", headers=headers)
                    duration = time.time() - start_time

                    if response.status_code == 200:
                        self.log_test(name, True, f"HTTP {response.status_code}", duration)
                        success_count += 1

                        # 分析数据质量
                        data = response.json()
                        if isinstance(data, list):
                            print(f"   📊 {name}: 获取到 {len(data)} 条记录")
                            if data and len(data) > 0:
                                first_item = data[0]
                                print(
                                    f"   📋 示例数据: {json.dumps(first_item, indent=2, ensure_ascii=False)}"
                                )
                        elif isinstance(data, dict):
                            print(f"   📊 {name}: 获取到数据对象")
                            print(f"   📋 数据键: {list(data.keys())}")
                    else:
                        self.log_test(
                            name,
                            False,
                            f"HTTP {response.status_code}: {response.text[:100]}",
                            duration,
                        )
            except Exception as e:
                duration = time.time() - start_time
                self.log_test(name, False, f"连接错误: {str(e)}", duration)

        print(f"\n   📈 数据探索结果: {success_count}/{len(data_endpoints)} 成功")
        return success_count == len(data_endpoints)

    async def test_prediction_features(self):
        """测试预测功能"""
        print("\n🔮 步骤4: 测试预测功能")

        prediction_endpoints = [
            ("预测系统健康检查", "/api/v1/predictions/health"),
            ("获取最近预测", "/api/v1/predictions/recent"),
        ]

        headers = {"Authorization": self.auth_token} if self.auth_token else {}
        success_count = 0

        for name, endpoint in prediction_endpoints:
            start_time = time.time()
            try:
                async with httpx.AsyncClient(timeout=10) as client:
                    response = await client.get(f"{self.api_base_url}{endpoint}", headers=headers)
                    duration = time.time() - start_time

                    if response.status_code == 200:
                        self.log_test(name, True, f"HTTP {response.status_code}", duration)
                        success_count += 1

                        data = response.json()
                        print(f"   📊 {name}: {json.dumps(data, indent=2, ensure_ascii=False)}")
                    else:
                        self.log_test(
                            name,
                            False,
                            f"HTTP {response.status_code}: {response.text[:100]}",
                            duration,
                        )
            except Exception as e:
                duration = time.time() - start_time
                self.log_test(name, False, f"连接错误: {str(e)}", duration)

        # 尝试创建一个预测（如果API支持）
        try:
            start_time = time.time()
            prediction_data = {
                "match_id": 1,
                "predicted_home_score": 2,
                "predicted_away_score": 1,
                "confidence": 0.75,
            }
            async with httpx.AsyncClient(timeout=10) as client:
                response = await client.post(
                    f"{self.api_base_url}/api/v1/predictions/1/predict",
                    json=prediction_data,
                    headers=headers,
                )
                duration = time.time() - start_time

                if response.status_code in [200, 201]:
                    self.log_test("创建预测", True, f"HTTP {response.status_code}", duration)
                    success_count += 1
                    print(
                        f"   📊 预测创建结果: {json.dumps(response.json(), indent=2, ensure_ascii=False)}"
                    )
                else:
                    self.log_test(
                        "创建预测",
                        False,
                        f"HTTP {response.status_code}: {response.text[:100]}",
                        duration,
                    )
        except Exception as e:
            self.log_test("创建预测", False, f"预测功能测试失败: {str(e)}")

        print("\n   📈 预测功能结果: 测试完成")
        return success_count >= 2  # 至少健康检查和最近预测成功

    async def test_monitoring_system(self):
        """测试监控系统"""
        print("\n📊 步骤5: 测试监控系统")

        monitoring_endpoints = [
            ("Prometheus指标", "/api/v1/metrics/prometheus"),
            ("事件系统状态", "/api/v1/events/health"),
            ("观察者系统状态", "/api/v1/observers/status"),
            ("CQRS系统状态", "/api/v1/cqrs/system/status"),
        ]

        headers = {"Authorization": self.auth_token} if self.auth_token else {}
        success_count = 0

        for name, endpoint in monitoring_endpoints:
            start_time = time.time()
            try:
                async with httpx.AsyncClient(timeout=10) as client:
                    response = await client.get(f"{self.api_base_url}{endpoint}", headers=headers)
                    duration = time.time() - start_time

                    if response.status_code == 200:
                        self.log_test(name, True, f"HTTP {response.status_code}", duration)
                        success_count += 1

                        if "prometheus" in name:
                            # Prometheus指标通常很长，只显示前几行
                            response.text[:200]
                            print(f"   📊 {name}: Prometheus指标格式正常")
                        else:
                            data = response.json()
                            print(f"   📊 {name}: {json.dumps(data, indent=2, ensure_ascii=False)}")
                    else:
                        self.log_test(
                            name,
                            False,
                            f"HTTP {response.status_code}: {response.text[:100]}",
                            duration,
                        )
            except Exception as e:
                duration = time.time() - start_time
                self.log_test(name, False, f"连接错误: {str(e)}", duration)

        print(f"\n   📈 监控系统结果: {success_count}/{len(monitoring_endpoints)} 成功")
        return success_count >= 2  # 至少一半监控系统正常

    async def simulate_user_behavior(self):
        """模拟用户行为"""
        print("\n🎭 步骤6: 模拟真实用户行为")

        behaviors = [
            ("浏览API文档", "/docs"),
            ("检查系统健康", "/api/health/"),
            ("查看功能状态", "/api/v1/features/health"),
            ("获取用户信息", "/api/v1/auth/me"),
        ]

        headers = {"Authorization": self.auth_token} if self.auth_token else {}
        success_count = 0

        for name, endpoint in behaviors:
            start_time = time.time()
            try:
                async with httpx.AsyncClient(timeout=10) as client:
                    response = await client.get(f"{self.api_base_url}{endpoint}", headers=headers)
                    duration = time.time() - start_time

                    if response.status_code == 200:
                        self.log_test(name, True, f"HTTP {response.status_code}", duration)
                        success_count += 1

                        if "me" in endpoint:
                            user_info = response.json()
                            print(
                                f"   👤 用户信息: {json.dumps(user_info, indent=2, ensure_ascii=False)}"
                            )
                    else:
                        self.log_test(
                            name,
                            False,
                            f"HTTP {response.status_code}: {response.text[:100]}",
                            duration,
                        )
            except Exception as e:
                duration = time.time() - start_time
                self.log_test(name, False, f"连接错误: {str(e)}", duration)

        # 模拟用户会话持续时间（随机延迟）
        session_duration = random.uniform(1, 3)
        print(f"\n   ⏱️  模拟用户会话持续时间: {session_duration:.1f}秒")
        await asyncio.sleep(session_duration)

        print(f"\n   📈 用户行为模拟: {success_count}/{len(behaviors)} 成功")
        return success_count >= 3

    async def logout_user(self):
        """用户登出"""
        print("\n🚪 步骤7: 用户登出")

        start_time = time.time()
        try:
            async with httpx.AsyncClient(timeout=10) as client:
                response = await client.post(f"{self.api_base_url}/api/v1/auth/logout")
                duration = time.time() - start_time

                if response.status_code == 200:
                    self.log_test("用户登出", True, f"HTTP {response.status_code}", duration)
                    return True
                else:
                    self.log_test(
                        "用户登出",
                        False,
                        f"HTTP {response.status_code}: {response.text[:100]}",
                        duration,
                    )
                    return False
        except Exception as e:
            duration = time.time() - start_time
            self.log_test("用户登出", False, f"连接错误: {str(e)}", duration)
            return False

    async def run_complete_seed_user_test(self):
        """运行完整的种子用户测试"""
        print("🌱 开始完整种子用户测试")
        print("=" * 60)
        print(f"📅 测试时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"🔗 API地址: {self.api_base_url}")
        print("=" * 60)

        test_results = {}

        # 执行测试步骤
        test_results["registration"] = await self.register_test_user()
        test_results["login"] = await self.login_test_user()
        test_results["data_exploration"] = await self.explore_football_data()
        test_results["prediction_features"] = await self.test_prediction_features()
        test_results["monitoring_system"] = await self.test_monitoring_system()
        test_results["user_behavior"] = await self.simulate_user_behavior()
        test_results["logout"] = await self.logout_user()

        # 生成种子用户测试报告
        self.generate_seed_user_report(test_results)

    def generate_seed_user_report(self, test_results):
        """生成种子用户测试报告"""
        print("\n" + "=" * 60)
        print("📊 种子用户测试报告")
        print("=" * 60)

        total_tests = len(self.test_results)
        successful_tests = len([r for r in self.test_results if r["success"]])
        failed_tests = total_tests - successful_tests
        success_rate = (successful_tests / total_tests * 100) if total_tests > 0 else 0

        print("📈 测试统计:")
        print(f"   总测试数: {total_tests}")
        print(f"   成功测试: {successful_tests}")
        print(f"   失败测试: {failed_tests}")
        print(f"   成功率: {success_rate:.1f}%")

        # 用户旅程测试结果
        print("\n🎯 用户旅程测试结果:")
        journey_steps = [
            ("用户注册", test_results["registration"]),
            ("用户登录", test_results["login"]),
            ("数据探索", test_results["data_exploration"]),
            ("预测功能", test_results["prediction_features"]),
            ("监控系统", test_results["monitoring_system"]),
            ("用户行为", test_results["user_behavior"]),
            ("用户登出", test_results["logout"]),
        ]

        completed_steps = 0
        for step_name, success in journey_steps:
            status = "✅" if success else "❌"
            print(f"   {status} {step_name}")
            if success:
                completed_steps += 1

        journey_completion = (completed_steps / len(journey_steps)) * 100
        print(
            f"\n   用户旅程完成率: {completed_steps}/{len(journey_steps)} ({journey_completion:.1f}%)"
        )

        # 失败的测试
        if failed_tests > 0:
            print("\n❌ 失败的测试:")
            for result in self.test_results:
                if not result["success"]:
                    print(f"   • {result['test_name']}: {result['details']}")

        # 性能统计
        durations = [r["duration"] for r in self.test_results if r["duration"] > 0]
        if durations:
            avg_duration = sum(durations) / len(durations)
            print("\n⏱️  性能统计:")
            print(f"   平均响应时间: {avg_duration:.2f}秒")
            print(f"   最慢响应: {max(durations):.2f}秒")
            print(f"   最快响应: {min(durations):.2f}秒")

        # 系统评估
        print("\n🎯 种子用户测试评估:")
        if success_rate >= 85 and journey_completion >= 80:
            print("   🟢 优秀: 系统完全支持种子用户测试，用户体验良好")
            system_status = "优秀"
            deployment_ready = True
        elif success_rate >= 70 and journey_completion >= 70:
            print("   🟡 良好: 系统基本支持种子用户测试，存在少量问题")
            system_status = "良好"
            deployment_ready = True
        elif success_rate >= 60 and journey_completion >= 60:
            print("   🟡 一般: 系统可以支持基础种子用户测试，需要改进")
            system_status = "一般"
            deployment_ready = False
        else:
            print("   🔴 需要改进: 系统存在较多问题，不建议进行种子用户测试")
            system_status = "需要改进"
            deployment_ready = False

        # 用户体验评分
        ux_score = success_rate * 0.4 + journey_completion * 0.6
        print(f"\n🎨 用户体验评分: {ux_score:.1f}/100")

        # 最终建议
        print("\n🚀 最终建议:")
        if deployment_ready:
            print("   ✨ 系统已准备好进行种子用户测试")
            print("   📋 建议的种子用户测试计划:")
            print("      1. 邀请5-10名种子用户")
            print("      2. 重点关注用户注册和数据探索功能")
            print("      3. 收集用户反馈和改进建议")
            print("      4. 监控系统性能和稳定性")
        else:
            print("   🔧 建议优先修复以下问题:")
            failed_critical = [
                r
                for r in self.test_results
                if not r["success"]
                and any(keyword in r["test_name"] for keyword in ["注册", "登录", "数据"])
            ]
            if failed_critical:
                print("      关键功能问题:")
                for result in failed_critical:
                    print(f"      • {result['test_name']}: {result['details']}")

            print("   📋 修复建议:")
            print("      1. 优先修复核心功能问题")
            print("      2. 提升API稳定性")
            print("      3. 改善错误处理")
            print("      4. 重新进行种子用户测试")

        print("\n🎊 种子用户测试完成!")
        print(f"   系统状态: {system_status}")
        print(f"   测试时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("=" * 60)


async def main():
    """主函数"""
    tester = SeedUserTester()
    await tester.run_complete_seed_user_test()


if __name__ == "__main__":
    asyncio.run(main())
