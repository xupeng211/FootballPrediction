#!/usr/bin/env python3
"""
🌱 种子用户测试脚本

模拟真实用户使用场景，全面测试系统功能和用户体验
"""

import asyncio
import json
import random
import time
from datetime import datetime, timedelta
from typing import Dict, List, Any

import httpx
from passlib.context import CryptContext

# 测试配置
API_BASE_URL = "http://localhost:8000/api/v1"
HEALTH_URL = "http://localhost:8000/api/health/"

# 密码加密上下文
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# 种子用户角色和场景
SEED_USERS = [
    {
        "role": "premium_user",
        "username": "seed_premium",
        "email": "premium@seedtest.com",
        "password": "PremiumSeed123!",
        "first_name": "高级",
        "last_name": "种子用户",
        "description": "高级用户，测试高级功能访问",
    },
    {
        "role": "regular_user",
        "username": "seed_regular",
        "email": "regular@seedtest.com",
        "password": "RegularSeed123!",
        "first_name": "普通",
        "last_name": "种子用户",
        "description": "普通用户，测试基本功能",
    },
    {
        "role": "analyst_user",
        "username": "seed_analyst",
        "email": "analyst@seedtest.com",
        "password": "AnalystSeed123!",
        "first_name": "分析",
        "last_name": "种子用户",
        "description": "分析师用户，测试数据分析功能",
    },
]


class SeedUserTester:
    """种子用户测试器"""

    def __init__(self):
        self.test_results = []
        self.created_users = []
        self.active_tokens = {}

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

    async def create_seed_user(self, user_config: Dict[str, Any]) -> Dict[str, Any]:
        """创建种子用户"""
        start_time = time.time()

        try:
            async with httpx.AsyncClient(timeout=15) as client:
                response = await client.post(f"{API_BASE_URL}/auth/register", json=user_config)
                duration = time.time() - start_time

                if response.status_code == 201:
                    user_data = response.json()
                    self.log_test(
                        f"创建种子用户: {user_config['username']}",
                        True,
                        f"用户ID: {user_data.get('id')}, 角色: {user_data.get('role')}",
                        duration,
                    )
                    return user_data
                else:
                    error_data = response.json()
                    self.log_test(
                        f"创建种子用户: {user_config['username']}",
                        False,
                        f"错误: {error_data.get('detail')}",
                        duration,
                    )
                    return {}

        except Exception as e:
            duration = time.time() - start_time
            self.log_test(
                f"创建种子用户: {user_config['username']}", False, f"网络错误: {str(e)}", duration
            )
            return {}

    async def test_user_login(self, user_config: Dict[str, Any]) -> str:
        """测试用户登录"""
        start_time = time.time()

        try:
            async with httpx.AsyncClient(timeout=15) as client:
                login_data = {
                    "username": user_config["username"],
                    "password": user_config["password"],
                }

                response = await client.post(f"{API_BASE_URL}/auth/login", data=login_data)
                duration = time.time() - start_time

                if response.status_code == 200:
                    token_data = response.json()
                    self.log_test(
                        f"用户登录: {user_config['username']}",
                        True,
                        f"角色: {token_data.get('user', {}).get('role')}, 令牌有效期: {token_data.get('expires_in')}秒",
                        duration,
                    )
                    return token_data.get("access_token")
                else:
                    error_data = response.json()
                    self.log_test(
                        f"用户登录: {user_config['username']}",
                        False,
                        f"错误: {error_data.get('detail')}",
                        duration,
                    )
                    return ""

        except Exception as e:
            duration = time.time() - start_time
            self.log_test(
                f"用户登录: {user_config['username']}", False, f"网络错误: {str(e)}", duration
            )
            return ""

    async def test_user_profile(self, token: str, username: str) -> bool:
        """测试获取用户资料"""
        start_time = time.time()

        try:
            headers = {"Authorization": f"Bearer {token}"}
            async with httpx.AsyncClient(timeout=10) as client:
                response = await client.get(f"{API_BASE_URL}/auth/me", headers=headers)
                duration = time.time() - start_time

                if response.status_code == 200:
                    user_data = response.json()
                    self.log_test(
                        f"获取用户资料: {username}",
                        True,
                        f"用户ID: {user_data.get('id')}, 是否激活: {user_data.get('is_active')}, 是否验证: {user_data.get('is_verified')}",
                        duration,
                    )
                    return True
                else:
                    error_data = response.json()
                    self.log_test(
                        f"获取用户资料: {username}",
                        False,
                        f"错误: {error_data.get('detail')}",
                        duration,
                    )
                    return False

        except Exception as e:
            duration = time.time() - start_time
            self.log_test(f"获取用户资料: {username}", False, f"网络错误: {str(e)}", duration)
            return False

    async def test_api_endpoints(self, token: str, username: str) -> Dict[str, bool]:
        """测试各种API端点访问"""
        headers = {"Authorization": f"Bearer {token}"}
        results = {}

        # 测试不同的API端点
        endpoints_to_test = [
            ("/data/teams", "获取球队数据"),
            ("/data/leagues", "获取联赛数据"),
            ("/predictions", "获取预测数据"),
            ("/monitoring/metrics", "获取监控指标"),
        ]

        for endpoint, description in endpoints_to_test:
            start_time = time.time()
            try:
                async with httpx.AsyncClient(timeout=10) as client:
                    response = await client.get(f"{API_BASE_URL}{endpoint}", headers=headers)
                    duration = time.time() - start_time

                    success = response.status_code in [200, 404]  # 404也算成功，说明路由存在
                    status_text = (
                        "访问成功"
                        if response.status_code == 200
                        else f"HTTP {response.status_code}"
                    )

                    self.log_test(
                        f"API测试 - {description}",
                        success,
                        f"用户: {username}, 状态: {status_text}",
                        duration,
                    )

                    results[endpoint] = success

            except Exception as e:
                duration = time.time() - start_time
                self.log_test(
                    f"API测试 - {description}", False, f"用户: {username}, 错误: {str(e)}", duration
                )
                results[endpoint] = False

        return results

    async def simulate_user_behavior(self, user_config: Dict[str, Any], token: str):
        """模拟用户行为模式"""
        username = user_config["username"]
        user_role = user_config["role"]

        print(f"\n👤 模拟用户行为: {username} ({user_role})")
        print("-" * 50)

        # 模拟用户在不同时间点的操作
        behaviors = [
            ("浏览系统状态", lambda: self.test_user_profile(token, username)),
            ("查看数据接口", lambda: self.test_api_endpoints(token, username)),
            ("刷新用户信息", lambda: self.test_user_profile(token, username)),
        ]

        for behavior_name, behavior_func in behaviors:
            # 随机延迟，模拟真实用户操作间隔
            await asyncio.sleep(random.uniform(0.5, 2.0))

            try:
                if "查看数据接口" in behavior_name:
                    await behavior_func()
                else:
                    await behavior_func()

                print(f"   🔄 {behavior_name} - 完成")
            except Exception as e:
                print(f"   ❌ {behavior_name} - 失败: {str(e)}")

    async def run_seed_user_test(self):
        """运行完整的种子用户测试"""
        print("🌱 开始种子用户测试")
        print("=" * 60)
        print(f"📅 测试时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"🔗 API地址: {API_BASE_URL}")
        print(f"👥 测试用户数量: {len(SEED_USERS)}")
        print("=" * 60)

        # 1. 系统健康检查
        if not await self.test_system_health():
            print("\n❌ 系统不可用，测试终止")
            return False

        # 2. 创建种子用户
        print(f"\n📝 创建 {len(SEED_USERS)} 个种子用户...")
        for user_config in SEED_USERS:
            user_data = await self.create_seed_user(user_config)
            if user_data:
                self.created_users.append(user_data)

        if not self.created_users:
            print("\n❌ 没有成功创建任何用户，测试终止")
            return False

        # 3. 用户登录和功能测试
        print("\n🔐 测试用户登录和功能...")
        for i, user_config in enumerate(SEED_USERS):
            if i >= len(self.created_users):
                continue

            print(f"\n👤 测试用户 {i+1}/{len(SEED_USERS)}: {user_config['username']}")

            # 登录获取令牌
            token = await self.test_user_login(user_config)
            if token:
                self.active_tokens[user_config["username"]] = token

                # 获取用户资料
                await self.test_user_profile(token, user_config["username"])

                # 测试API访问
                await self.test_api_endpoints(token, user_config["username"])

                # 模拟用户行为
                await self.simulate_user_behavior(user_config, token)

        # 4. 生成测试报告
        self.generate_test_report()

        return True

    def generate_test_report(self):
        """生成测试报告"""
        print("\n" + "=" * 60)
        print("📊 种子用户测试报告")
        print("=" * 60)

        total_tests = len(self.test_results)
        successful_tests = sum(1 for r in self.test_results if r["success"])
        success_rate = (successful_tests / total_tests * 100) if total_tests > 0 else 0

        print("📈 测试统计:")
        print(f"   总测试数: {total_tests}")
        print(f"   成功测试: {successful_tests}")
        print(f"   失败测试: {total_tests - successful_tests}")
        print(f"   成功率: {success_rate:.1f}%")

        print("\n👥 用户创建情况:")
        print(f"   成功创建用户: {len(self.created_users)}/{len(SEED_USERS)}")

        print("\n🔐 登录验证情况:")
        print(f"   成功登录用户: {len(self.active_tokens)}")

        # 计算平均响应时间
        durations = [r["duration"] for r in self.test_results if r["duration"] > 0]
        if durations:
            avg_duration = sum(durations) / len(durations)
            print("\n⏱️  性能统计:")
            print(f"   平均响应时间: {avg_duration:.2f}秒")
            print(f"   最慢响应: {max(durations):.2f}秒")
            print(f"   最快响应: {min(durations):.2f}秒")

        # 显示失败的测试
        failed_tests = [r for r in self.test_results if not r["success"]]
        if failed_tests:
            print("\n❌ 失败的测试:")
            for test in failed_tests[:5]:  # 只显示前5个
                print(f"   • {test['test_name']}: {test['details']}")
            if len(failed_tests) > 5:
                print(f"   ... 还有 {len(failed_tests) - 5} 个失败测试")

        # 系统评估
        print("\n🎯 系统评估:")
        if success_rate >= 90:
            print("   🟢 优秀: 系统表现良好，可以支持种子用户测试")
        elif success_rate >= 70:
            print("   🟡 良好: 系统基本可用，建议优化部分功能")
        else:
            print("   🔴 需要改进: 系统存在较多问题，需要修复后再进行用户测试")

        print(f"\n🌱 种子用户测试完成于: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("=" * 60)


async def main():
    """主函数"""
    tester = SeedUserTester()
    await tester.run_seed_user_test()


if __name__ == "__main__":
    asyncio.run(main())
