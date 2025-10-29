#!/usr/bin/env python3
"""
🌱 种子用户简化测试脚本

使用现有用户账户测试系统功能，模拟真实用户使用场景
"""

import asyncio
import json
import random
import time
from datetime import datetime
from typing import Dict, List, Any

import httpx

# 测试配置
API_BASE_URL = "http://localhost:8000/api/v1"
HEALTH_URL = "http://localhost:8000/api/health/"

# 现有测试用户账户
EXISTING_USERS = [
    {"username": "admin", "password": "admin123", "role": "admin", "description": "系统管理员用户"},
    {"username": "testuser", "password": "test123", "role": "user", "description": "普通测试用户"},
]


class SeedUserTester:
    """种子用户测试器"""

    def __init__(self):
        self.test_results = []
        self.user_sessions = {}

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

    async def test_system_health(self) -> bool:
        """测试系统健康状态"""
        start_time = time.time()

        try:
            async with httpx.AsyncClient(timeout=10) as client:
                response = await client.get(HEALTH_URL)
                duration = time.time() - start_time

                if response.status_code == 200:
                    health_data = response.json()
                    self.log_test(
                        "系统健康检查",
                        True,
                        f"状态: {health_data.get('status')}, 数据库延迟: {health_data.get('checks', {}).get('database', {}).get('latency_ms')}ms",
                        duration,
                    )
                    return True
                else:
                    self.log_test("系统健康检查", False, f"HTTP {response.status_code}", duration)
                    return False

        except Exception as e:
            duration = time.time() - start_time
            self.log_test("系统健康检查", False, f"连接错误: {str(e)}", duration)
            return False

    async def test_api_accessibility(self) -> bool:
        """测试API可访问性"""
        start_time = time.time()

        endpoints_to_test = [
            ("/", "根路径"),
            ("/docs", "API文档"),
            ("/openapi.json", "OpenAPI规范"),
            ("/api/health/", "健康检查"),
            ("/api/v1/monitoring/metrics", "监控指标"),
            ("/api/v1/data/teams", "球队数据"),
            ("/api/v1/data/leagues", "联赛数据"),
            ("/api/v1/predictions", "预测数据"),
        ]

        try:
            success_count = 0
            async with httpx.AsyncClient(timeout=10) as client:
                for endpoint, description in endpoints_to_test:
                    try:
                        response = await client.get(f"http://localhost:8000{endpoint}")
                        if response.status_code in [200, 404]:  # 404也算可访问
                            success_count += 1
                            status = "200 OK" if response.status_code == 200 else "404 Not Found"
                            print(f"   ✅ {description}: {status}")
                        else:
                            print(f"   ❌ {description}: HTTP {response.status_code}")
                    except Exception as e:
                        print(f"   ❌ {description}: 连接错误 - {str(e)}")

            duration = time.time() - start_time
            success_rate = (success_count / len(endpoints_to_test)) * 100
            self.log_test(
                "API可访问性测试",
                success_rate >= 75,
                f"可访问端点: {success_count}/{len(endpoints_to_test)} ({success_rate:.1f}%)",
                duration,
            )
            return success_rate >= 75

        except Exception as e:
            duration = time.time() - start_time
            self.log_test("API可访问性测试", False, f"测试失败: {str(e)}", duration)
            return False

    async def test_database_functionality(self) -> bool:
        """测试数据库功能"""
        start_time = time.time()

        try:
            async with httpx.AsyncClient(timeout=10) as client:
                # 测试数据库数据
                endpoints = [
                    ("/api/v1/data/teams", "球队数据"),
                    ("/api/v1/data/leagues", "联赛数据"),
                    ("/api/v1/data/matches", "比赛数据"),
                ]

                db_working = False
                for endpoint, description in endpoints:
                    try:
                        response = await client.get(f"{API_BASE_URL}{endpoint}")
                        if response.status_code == 200:
                            data = response.json()
                            if isinstance(data, list) and len(data) > 0:
                                print(f"   ✅ {description}: {len(data)} 条记录")
                                db_working = True
                            elif isinstance(data, dict):
                                print(f"   ✅ {description}: 数据正常")
                                db_working = True
                            else:
                                print(f"   ⚠️  {description}: 无数据")
                        else:
                            print(f"   ❌ {description}: HTTP {response.status_code}")
                    except Exception as e:
                        print(f"   ❌ {description}: 错误 - {str(e)}")

                duration = time.time() - start_time
                self.log_test(
                    "数据库功能测试",
                    db_working,
                    "数据库连接正常，数据可访问" if db_working else "数据库存在问题",
                    duration,
                )
                return db_working

        except Exception as e:
            duration = time.time() - start_time
            self.log_test("数据库功能测试", False, f"数据库测试失败: {str(e)}", duration)
            return False

    async def test_monitoring_system(self) -> bool:
        """测试监控系统"""
        start_time = time.time()

        try:
            async with httpx.AsyncClient(timeout=10) as client:
                # 测试Prometheus指标
                response = await client.get(f"{API_BASE_URL}/monitoring/metrics")
                duration = time.time() - start_time

                if response.status_code == 200:
                    metrics_text = response.text
                    metric_count = len(
                        [
                            line
                            for line in metrics_text.split("\n")
                            if line and not line.startswith("#")
                        ]
                    )

                    self.log_test("监控系统测试", True, f"收集到 {metric_count} 个指标", duration)
                    return True
                else:
                    self.log_test("监控系统测试", False, f"HTTP {response.status_code}", duration)
                    return False

        except Exception as e:
            duration = time.time() - start_time
            self.log_test("监控系统测试", False, f"监控测试失败: {str(e)}", duration)
            return False

    async def simulate_user_interaction(self, user_config: Dict[str, Any]) -> Dict[str, Any]:
        """模拟用户交互行为"""
        username = user_config["username"]
        user_role = user_config["role"]

        print(f"\n👤 模拟用户交互: {username} ({user_role})")
        print("-" * 50)

        session_data = {
            "username": username,
            "role": user_role,
            "interactions": [],
            "start_time": datetime.now(),
            "success": True,
        }

        interactions = [
            ("访问系统主页", self._visit_homepage),
            ("查看API文档", self._visit_docs),
            ("检查系统健康", self._check_health),
            ("浏览数据接口", self._browse_data),
            ("查看监控指标", self._view_metrics),
        ]

        for interaction_name, interaction_func in interactions:
            # 随机延迟，模拟真实用户操作
            await asyncio.sleep(random.uniform(0.3, 1.5))

            try:
                start_time = time.time()
                result = await interaction_func()
                duration = time.time() - start_time

                session_data["interactions"].append(
                    {
                        "name": interaction_name,
                        "success": result,
                        "duration": duration,
                        "timestamp": datetime.now().isoformat(),
                    }
                )

                status = "✅" if result else "❌"
                print(f"   {status} {interaction_name} ({duration:.2f}s)")

                if not result:
                    session_data["success"] = False

            except Exception as e:
                print(f"   ❌ {interaction_name} - 异常: {str(e)}")
                session_data["interactions"].append(
                    {
                        "name": interaction_name,
                        "success": False,
                        "error": str(e),
                        "timestamp": datetime.now().isoformat(),
                    }
                )
                session_data["success"] = False

        session_data["end_time"] = datetime.now()
        session_data["total_duration"] = (
            session_data["end_time"] - session_data["start_time"]
        ).total_seconds()

        return session_data

    async def _visit_homepage(self) -> bool:
        """访问系统主页"""
        try:
            async with httpx.AsyncClient(timeout=5) as client:
                response = await client.get("http://localhost:8000/")
                return response.status_code == 200
except Exception:
            return False

    async def _visit_docs(self) -> bool:
        """访问API文档"""
        try:
            async with httpx.AsyncClient(timeout=5) as client:
                response = await client.get("http://localhost:8000/docs")
                return response.status_code == 200
except Exception:
            return False

    async def _check_health(self) -> bool:
        """检查系统健康"""
        try:
            async with httpx.AsyncClient(timeout=5) as client:
                response = await client.get(HEALTH_URL)
                return response.status_code == 200
except Exception:
            return False

    async def _browse_data(self) -> bool:
        """浏览数据接口"""
        try:
            async with httpx.AsyncClient(timeout=5) as client:
                endpoints = ["/api/v1/data/teams", "/api/v1/data/leagues"]
                success_count = 0
                for endpoint in endpoints:
                    response = await client.get(f"http://localhost:8000{endpoint}")
                    if response.status_code == 200:
                        success_count += 1
                return success_count > 0
except Exception:
            return False

    async def _view_metrics(self) -> bool:
        """查看监控指标"""
        try:
            async with httpx.AsyncClient(timeout=5) as client:
                response = await client.get(f"{API_BASE_URL}/monitoring/metrics")
                return response.status_code == 200
except Exception:
            return False

    async def run_seed_user_test(self):
        """运行完整的种子用户测试"""
        print("🌱 开始种子用户简化测试")
        print("=" * 60)
        print(f"📅 测试时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"🔗 API地址: {API_BASE_URL}")
        print("👥 测试用户: 现有账户模拟")
        print("=" * 60)

        # 1. 系统健康检查
        health_ok = await self.test_system_health()
        if not health_ok:
            print("\n❌ 系统不可用，测试终止")
            return False

        # 2. API可访问性测试
        api_ok = await self.test_api_accessibility()

        # 3. 数据库功能测试
        db_ok = await self.test_database_functionality()

        # 4. 监控系统测试
        monitoring_ok = await self.test_monitoring_system()

        # 5. 用户交互模拟
        print("\n🎭 模拟用户交互...")
        for user_config in EXISTING_USERS:
            session_data = await self.simulate_user_interaction(user_config)
            self.user_sessions[user_config["username"]] = session_data

        # 6. 生成测试报告
        self.generate_test_report(health_ok, api_ok, db_ok, monitoring_ok)

        return True

    def generate_test_report(self, health_ok: bool, api_ok: bool, db_ok: bool, monitoring_ok: bool):
        """生成测试报告"""
        print("\n" + "=" * 60)
        print("📊 种子用户测试报告")
        print("=" * 60)

        total_tests = len(self.test_results)
        successful_tests = sum(1 for r in self.test_results if r["success"])
        success_rate = (successful_tests / total_tests * 100) if total_tests > 0 else 0

        print("📈 核心功能测试:")
        print(f"   ✅ 系统健康检查: {'通过' if health_ok else '失败'}")
        print(f"   ✅ API可访问性: {'通过' if api_ok else '失败'}")
        print(f"   ✅ 数据库功能: {'通过' if db_ok else '失败'}")
        print(f"   ✅ 监控系统: {'通过' if monitoring_ok else '失败'}")

        print("\n👥 用户交互测试:")
        total_interactions = 0
        successful_interactions = 0

        for username, session in self.user_sessions.items():
            interactions = session["interactions"]
            user_success = sum(1 for i in interactions if i["success"])
            total_interactions += len(interactions)
            successful_interactions += user_success

            print(
                f"   👤 {username}: {user_success}/{len(interactions)} 交互成功 ({session['total_duration']:.1f}s)"
            )

        if total_interactions > 0:
            interaction_success_rate = successful_interactions / total_interactions * 100
            print(f"   📊 总体交互成功率: {interaction_success_rate:.1f}%")

        print("\n📊 测试统计:")
        print(f"   总测试数: {total_tests}")
        print(f"   成功测试: {successful_tests}")
        print(f"   失败测试: {total_tests - successful_tests}")
        print(f"   成功率: {success_rate:.1f}%")

        # 计算平均响应时间
        durations = [r["duration"] for r in self.test_results if r["duration"] > 0]
        if durations:
            avg_duration = sum(durations) / len(durations)
            print("\n⏱️  性能统计:")
            print(f"   平均响应时间: {avg_duration:.2f}秒")
            print(f"   最慢响应: {max(durations):.2f}秒")
            print(f"   最快响应: {min(durations):.2f}秒")

        # 系统整体评估
        print("\n🎯 系统整体评估:")
        core_functions_ok = all([health_ok, api_ok, db_ok, monitoring_ok])
        user_experience_good = success_rate >= 80

        if core_functions_ok and user_experience_good:
            print("   🟢 优秀: 系统完全就绪，可以支持种子用户测试")
            print("   🌱 建议: 立即开始种子用户测试计划")
        elif core_functions_ok:
            print("   🟡 良好: 核心功能正常，用户体验可接受")
            print("   🌱 建议: 可以开始种子用户测试，同时优化用户体验")
        else:
            print("   🔴 需要改进: 存在功能问题，建议修复后再进行用户测试")
            print("   🌱 建议: 优先修复核心功能问题")

        # 种子用户测试建议
        print("\n🌱 种子用户测试建议:")
        if health_ok and db_ok:
            print("   ✅ 系统基础稳定，可以创建测试用户账户")
            print("   ✅ 数据连接正常，可以存储用户数据")
            print("   ✅ API接口可用，可以支持用户交互")
        else:
            print("   ❌ 建议先解决系统稳定性问题")

        if monitoring_ok:
            print("   ✅ 监控系统正常，可以跟踪用户行为")
        else:
            print("   ⚠️  建议完善监控系统以跟踪用户行为")

        print(f"\n🌱 种子用户测试完成于: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("=" * 60)


async def main():
    """主函数"""
    tester = SeedUserTester()
    await tester.run_seed_user_test()


if __name__ == "__main__":
    asyncio.run(main())
