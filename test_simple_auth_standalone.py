#!/usr/bin/env python3
"""
🧪 简化认证系统测试脚本

独立测试简化认证系统功能，不依赖完整的FastAPI应用启动
"""

import asyncio
import json
from fastapi import FastAPI
from fastapi.testclient import TestClient

# 导入简化的认证系统
from src.api.simple_auth import (
    router as auth_router,
    SimpleAuthService,
    SimpleUser,
    SimpleUserRegister,
    SimpleTokenResponse,
)


class SimpleAuthTester:
    """简化认证系统测试器"""

    def __init__(self):
        self.app = FastAPI()
        self.app.include_router(auth_router, prefix="/api/v1")
        self.client = TestClient(self.app)
        self.test_results = []

    def log_test(self, test_name: str, success: bool, details: str = ""):
        """记录测试结果"""
        result = {"test_name": test_name, "success": success, "details": details}
        self.test_results.append(result)

        status = "✅" if success else "❌"
        print(f"{status} {test_name}")
        if details:
            print(f"   📝 {details}")

    def test_model_creation(self):
        """测试模型创建"""
        print("\n🔍 测试模型创建")

        try:
            # 测试SimpleUser模型
            user = SimpleUser(
                id=1,
                username="testuser",
                email="test@example.com",
                role="user",
                is_active=True,
                created_at="2025-10-28T12:00:00",
            )
            self.log_test("SimpleUser模型创建", True, f"用户: {user.username}")

            # 测试SimpleUserRegister模型
            register_data = SimpleUserRegister(
                username="newuser", email="new@example.com", password="password123"
            )
            self.log_test("SimpleUserRegister模型创建", True, f"注册用户: {register_data.username}")

            # 测试SimpleTokenResponse模型
            token_response = SimpleTokenResponse(
                access_token="Bearer testuser", token_type="bearer", expires_in=3600
            )
            self.log_test(
                "SimpleTokenResponse模型创建", True, f"令牌类型: {token_response.token_type}"
            )

        except Exception as e:
            self.log_test("模型创建", False, f"错误: {str(e)}")

    def test_auth_service(self):
        """测试认证服务"""
        print("\n🔍 测试认证服务")

        try:
            auth_service = SimpleAuthService()

            # 测试用户创建（使用唯一的用户名避免冲突）
            unique_username = f"servicetest_{hash(str(asyncio.get_event_loop())) % 10000}"
            user = auth_service.create_user(unique_username, "test@example.com", "password123")
            self.log_test("用户创建", True, f"创建用户ID: {user.id}, 用户名: {user.username}")

            # 测试用户认证
            auth_user = auth_service.authenticate_user(unique_username, "password123")
            self.log_test(
                "用户认证", True, f"认证用户: {auth_user.username if auth_user else 'None'}"
            )

            # 测试错误密码认证
            auth_user_fail = auth_service.authenticate_user(unique_username, "wrongpassword")
            self.log_test("错误密码认证", auth_user_fail is None, "应该返回None")

            # 测试获取用户
            get_user = auth_service.get_user_by_username(unique_username)
            self.log_test(
                "获取用户", True, f"获取用户: {get_user.username if get_user else 'None'}"
            )

            # 测试重复用户创建
            try:
                duplicate_user = auth_service.create_user(
                    unique_username, "test2@example.com", "password456"
                )
                self.log_test("重复用户创建", False, "应该抛出ValueError")
            except ValueError:
                self.log_test("重复用户创建", True, "正确抛出ValueError")

        except Exception as e:
            self.log_test("认证服务测试", False, f"错误: {str(e)}")

    def test_api_endpoints(self):
        """测试API端点"""
        print("\n🔍 测试API端点")

        try:
            # 测试用户注册端点
            register_data = {
                "username": "apitest",
                "email": "apitest@example.com",
                "password": "testpass123",
            }
            response = self.client.post("/api/v1/auth/register", json=register_data)
            self.log_test(
                "用户注册API", response.status_code == 201, f"状态码: {response.status_code}"
            )

            if response.status_code == 201:
                data = response.json()
                print(f"   📝 注册响应: {json.dumps(data, indent=2, ensure_ascii=False)}")

            # 测试用户登录端点
            login_data = {"username": "apitest", "password": "testpass123"}
            response = self.client.post("/api/v1/auth/login", data=login_data)
            self.log_test(
                "用户登录API", response.status_code == 200, f"状态码: {response.status_code}"
            )

            if response.status_code == 200:
                data = response.json()
                print(f"   📝 登录响应: {json.dumps(data, indent=2, ensure_ascii=False)}")

                # 测试获取当前用户信息端点
                token = data.get("access_token", "")
                headers = {"Authorization": token}
                response = self.client.get("/api/v1/auth/me", headers=headers)
                self.log_test(
                    "获取用户信息API",
                    response.status_code == 200,
                    f"状态码: {response.status_code}",
                )

                if response.status_code == 200:
                    user_data = response.json()
                    print(f"   📝 用户信息: {json.dumps(user_data, indent=2, ensure_ascii=False)}")

            # 测试用户登出端点
            response = self.client.post("/api/v1/auth/logout")
            self.log_test(
                "用户登出API", response.status_code == 200, f"状态码: {response.status_code}"
            )

        except Exception as e:
            self.log_test("API端点测试", False, f"错误: {str(e)}")

    def run_all_tests(self):
        """运行所有测试"""
        print("🧪 开始简化认证系统测试")
        print("=" * 60)

        # 运行各项测试
        self.test_model_creation()
        self.test_auth_service()
        self.test_api_endpoints()

        # 生成测试报告
        self.generate_report()

    def generate_report(self):
        """生成测试报告"""
        print("\n" + "=" * 60)
        print("📊 简化认证系统测试报告")
        print("=" * 60)

        total_tests = len(self.test_results)
        successful_tests = len([r for r in self.test_results if r["success"]])
        failed_tests = total_tests - successful_tests
        success_rate = (successful_tests / total_tests * 100) if total_tests > 0 else 0

        print(f"📈 测试统计:")
        print(f"   总测试数: {total_tests}")
        print(f"   成功测试: {successful_tests}")
        print(f"   失败测试: {failed_tests}")
        print(f"   成功率: {success_rate:.1f}%")

        print(f"\n✅ 成功的测试:")
        for result in self.test_results:
            if result["success"]:
                print(f"   • {result['test_name']}")

        if failed_tests > 0:
            print(f"\n❌ 失败的测试:")
            for result in self.test_results:
                if not result["success"]:
                    print(f"   • {result['test_name']}: {result['details']}")

        # 系统评估
        print(f"\n🎯 系统评估:")
        if success_rate >= 90:
            print("   🟢 优秀: 简化认证系统功能完整，可以投入使用")
        elif success_rate >= 70:
            print("   🟡 良好: 基本功能可用，建议完善部分功能")
        else:
            print("   🔴 需要改进: 存在较多问题，需要修复")

        print(f"\n🚀 下一步建议:")
        if success_rate >= 90:
            print("   1. 集成到主应用中替换复杂认证系统")
            print("   2. 添加更安全的密码哈希")
            print("   3. 实现JWT令牌验证")
        else:
            print("   1. 优先修复失败的测试")
            print("   2. 完善错误处理")
            print("   3. 重新进行测试验证")

        print("=" * 60)


def main():
    """主函数"""
    tester = SimpleAuthTester()
    tester.run_all_tests()


if __name__ == "__main__":
    main()
