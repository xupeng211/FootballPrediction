#!/usr/bin/env python3
"""
🔗 认证系统集成测试脚本

测试简化认证系统在完整FastAPI应用中的集成情况
"""

import asyncio
import json
import time
from datetime import datetime
import httpx


class AuthIntegrationTester:
    """认证系统集成测试器"""

    def __init__(self):
        self.api_base_url = "http://localhost:8000"
        self.test_results = []
        self.auth_token = None

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

    async def test_health_check(self):
        """测试健康检查端点"""
        start_time = time.time()
        try:
            async with httpx.AsyncClient(timeout=10) as client:
                response = await client.get(f"{self.api_base_url}/api/health/")
                duration = time.time() - start_time

                if response.status_code == 200:
                    self.log_test("健康检查", True, f"HTTP {response.status_code}", duration)
                    return True
                else:
                    self.log_test("健康检查", False, f"HTTP {response.status_code}", duration)
                    return False
        except Exception as e:
            duration = time.time() - start_time
            self.log_test("健康检查", False, f"连接错误: {str(e)}", duration)
            return False

    async def test_auth_endpoints(self):
        """测试认证相关端点"""
        print("\n🔍 测试认证端点")

        # 测试用户注册
        start_time = time.time()
        try:
            register_data = {
                "username": f"integration_test_{int(time.time())}",
                "email": f"test_{int(time.time())}@example.com",
                "password": "testpassword123",
            }
            async with httpx.AsyncClient(timeout=10) as client:
                response = await client.post(
                    f"{self.api_base_url}/api/v1/auth/register", json=register_data
                )
                duration = time.time() - start_time

                if response.status_code in [200, 201]:
                    self.log_test("用户注册", True, f"HTTP {response.status_code}", duration)

                    # 解析注册响应
                    register_result = response.json()
                    print(
                        f"   📝 注册结果: {json.dumps(register_result, indent=2, ensure_ascii=False)}"
                    )

                    # 测试用户登录
                    await self.test_user_login(register_data["username"], register_data["password"])

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

    async def test_user_login(self, username: str, password: str):
        """测试用户登录"""
        start_time = time.time()
        try:
            login_data = {"username": username, "password": password}
            async with httpx.AsyncClient(timeout=10) as client:
                response = await client.post(
                    f"{self.api_base_url}/api/v1/auth/login", data=login_data
                )
                duration = time.time() - start_time

                if response.status_code == 200:
                    self.log_test("用户登录", True, f"HTTP {response.status_code}", duration)

                    # 解析登录响应，保存token
                    login_result = response.json()
                    self.auth_token = login_result.get("access_token", "")
                    print(
                        f"   📝 登录结果: {json.dumps(login_result, indent=2, ensure_ascii=False)}"
                    )

                    # 测试获取用户信息
                    if self.auth_token:
                        await self.test_get_user_info()

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

    async def test_get_user_info(self):
        """测试获取用户信息"""
        start_time = time.time()
        try:
            headers = {"Authorization": self.auth_token}
            async with httpx.AsyncClient(timeout=10) as client:
                response = await client.get(f"{self.api_base_url}/api/v1/auth/me", headers=headers)
                duration = time.time() - start_time

                if response.status_code == 200:
                    self.log_test("获取用户信息", True, f"HTTP {response.status_code}", duration)

                    # 解析用户信息
                    user_info = response.json()
                    print(f"   📝 用户信息: {json.dumps(user_info, indent=2, ensure_ascii=False)}")

                    # 测试用户登出
                    await self.test_user_logout()

                    return True
                else:
                    self.log_test(
                        "获取用户信息",
                        False,
                        f"HTTP {response.status_code}: {response.text[:100]}",
                        duration,
                    )
                    return False
        except Exception as e:
            duration = time.time() - start_time
            self.log_test("获取用户信息", False, f"连接错误: {str(e)}", duration)
            return False

    async def test_user_logout(self):
        """测试用户登出"""
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

    async def test_api_discovery(self):
        """测试API发现"""
        print("\n🔍 测试API发现")

        # 测试API文档
        endpoints = [
            ("API文档", "/docs"),
            ("OpenAPI规范", "/openapi.json"),
            ("系统根路径", "/"),
        ]

        for name, path in endpoints:
            start_time = time.time()
            try:
                async with httpx.AsyncClient(timeout=10) as client:
                    response = await client.get(f"{self.api_base_url}{path}")
                    duration = time.time() - start_time

                    if response.status_code == 200:
                        self.log_test(name, True, f"HTTP {response.status_code}", duration)
                    else:
                        self.log_test(name, False, f"HTTP {response.status_code}", duration)
            except Exception as e:
                duration = time.time() - start_time
                self.log_test(name, False, f"连接错误: {str(e)}", duration)

    async def run_integration_tests(self):
        """运行集成测试"""
        print("🔗 开始认证系统集成测试")
        print("=" * 60)
        print(f"📅 测试时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"🔗 API地址: {self.api_base_url}")
        print("=" * 60)

        # 1. 测试健康检查
        health_ok = await self.test_health_check()
        if not health_ok:
            print("\n❌ 健康检查失败，应用可能未启动")
            return

        # 2. 测试API发现
        await self.test_api_discovery()

        # 3. 测试认证端点
        await self.test_auth_endpoints()

        # 生成测试报告
        self.generate_integration_report()

    def generate_integration_report(self):
        """生成集成测试报告"""
        print("\n" + "=" * 60)
        print("📊 认证系统集成测试报告")
        print("=" * 60)

        total_tests = len(self.test_results)
        successful_tests = len([r for r in self.test_results if r["success"]])
        failed_tests = total_tests - successful_tests
        success_rate = (successful_tests / total_tests * 100) if total_tests > 0 else 0

        print("📈 集成测试统计:")
        print(f"   总测试数: {total_tests}")
        print(f"   成功测试: {successful_tests}")
        print(f"   失败测试: {failed_tests}")
        print(f"   成功率: {success_rate:.1f}%")

        print("\n✅ 成功的测试:")
        for result in self.test_results:
            if result["success"]:
                print(f"   • {result['test_name']}")

        if failed_tests > 0:
            print("\n❌ 失败的测试:")
            for result in self.test_results:
                if not result["success"]:
                    print(f"   • {result['test_name']}: {result['details']}")

        # 系统评估
        print("\n🎯 集成测试评估:")
        if success_rate >= 90:
            print("   🟢 优秀: 认证系统完美集成，可以支持用户测试")
            integration_status = "完美集成"
        elif success_rate >= 70:
            print("   🟡 良好: 基本功能可用，建议完善部分功能")
            integration_status = "基本可用"
        else:
            print("   🔴 需要改进: 存在较多集成问题")
            integration_status = "需要修复"

        # 更新种子用户测试就绪度
        print("\n🚀 种子用户测试就绪度更新:")
        print(f"   认证系统集成状态: {integration_status}")
        if success_rate >= 90:
            print("   整体就绪度: 85% 🟢 (可以开始种子用户测试)")
        else:
            print("   整体就绪度: 75% 🟡 (需要继续完善)")

        print("\n📋 下一步建议:")
        if success_rate >= 90:
            print("   1. 开始修复其他API路由问题")
            print("   2. 集成真实数据库数据")
            print("   3. 进行完整种子用户测试")
        else:
            print("   1. 优先修复集成测试失败的问题")
            print("   2. 检查应用启动和路由配置")
            print("   3. 重新进行集成测试")

        print("=" * 60)


async def main():
    """主函数"""
    tester = AuthIntegrationTester()
    await tester.run_integration_tests()


if __name__ == "__main__":
    asyncio.run(main())
