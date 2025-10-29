#!/usr/bin/env python3
"""
🧪 简化认证系统测试脚本

独立测试简化认证系统的功能，不依赖Docker容器
"""

import asyncio
import sys
import os
from datetime import datetime, timedelta

# 添加项目根目录到Python路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.api.simple_auth import SimpleAuthService, SimpleUser


class SimpleAuthTester:
    """简化认证系统测试器"""

    def __init__(self):
        self.service = SimpleAuthService()
        self.test_results = []

    def print_banner(self):
        """打印测试横幅"""
        print("🧪" + "=" * 60)
        print("🧪 简化认证系统测试")
        print("=" * 62)
        print(f"🎯 目标: 验证简化认证系统核心功能")
        print(f"📅 测试时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("🧪" + "=" * 60)

    def test_user_creation(self):
        """测试用户创建功能"""
        print("\n👤 测试1: 用户创建功能")

        try:
            user = SimpleUser(
                id=1,
                username="testuser",
                email="test@example.com",
                password="test123",
                role="user",
                is_active=True,
                created_at=datetime.now(),
            )

            print(f"✅ 用户创建成功")
            print(f"   用户名: {user.username}")
            print(f"   邮箱: {user.email}")
            print(f"   角色: {user.role}")
            print(f"   状态: {'激活' if user.is_active else '未激活'}")

            self.test_results.append(
                {"test": "user_creation", "status": "PASS", "message": "用户创建功能正常"}
            )
            return True

        except Exception as e:
            print(f"❌ 用户创建失败: {str(e)}")
            self.test_results.append(
                {"test": "user_creation", "status": "FAIL", "message": f"用户创建失败: {str(e)}"}
            )
            return False

    def test_user_storage(self):
        """测试用户存储功能"""
        print("\n💾 测试2: 用户存储功能")

        try:
            # 创建测试用户
            user = SimpleUser(
                id=2,
                username="storage_test",
                email="storage@test.com",
                password="test123",
                role="user",
                is_active=True,
                created_at=datetime.now(),
            )

            # 存储用户
            self.service.store_user(user)

            # 验证用户存储
            stored_user = self.service.get_user("storage_test")

            if stored_user is not None:
                print(f"✅ 用户存储成功")
                print(f"   存储用户名: {stored_user.username}")
                print(f"   存储邮箱: {stored_user.email}")

                self.test_results.append(
                    {"test": "user_storage", "status": "PASS", "message": "用户存储功能正常"}
                )
                return True
            else:
                print(f"❌ 用户存储失败：无法检索存储的用户")
                self.test_results.append(
                    {"test": "user_storage", "status": "FAIL", "message": "无法检索存储的用户"}
                )
                return False

        except Exception as e:
            print(f"❌ 用户存储异常: {str(e)}")
            self.test_results.append(
                {"test": "user_storage", "status": "FAIL", "message": f"用户存储异常: {str(e)}"}
            )
            return False

    def test_password_validation(self):
        """测试密码验证功能"""
        print("\n🔒 测试3: 密码验证功能")

        try:
            # 测试正确密码
            correct_result = self.service.verify_password("test123", "test123")
            print(f"✅ 正确密码验证: {correct_result}")

            # 测试错误密码
            incorrect_result = self.service.verify_password("test123", "wrong")
            print(f"✅ 错误密码验证: {incorrect_result}")

            if correct_result and not incorrect_result:
                print(f"✅ 密码验证功能正常")
                self.test_results.append(
                    {"test": "password_validation", "status": "PASS", "message": "密码验证功能正常"}
                )
                return True
            else:
                print(f"❌ 密码验证功能异常")
                self.test_results.append(
                    {"test": "password_validation", "status": "FAIL", "message": "密码验证逻辑错误"}
                )
                return False

        except Exception as e:
            print(f"❌ 密码验证异常: {str(e)}")
            self.test_results.append(
                {
                    "test": "password_validation",
                    "status": "FAIL",
                    "message": f"密码验证异常: {str(e)}",
                }
            )
            return False

    def test_token_generation(self):
        """测试令牌生成功能"""
        print("\n🎫 测试4: 令牌生成功能")

        try:
            user = SimpleUser(
                id=3,
                username="token_test",
                email="token@test.com",
                password="test123",
                role="user",
                is_active=True,
                created_at=datetime.now(),
            )

            token = self.service.generate_token(user)

            if token is not None and "Bearer" in token:
                print(f"✅ 令牌生成成功")
                print(f"   令牌前缀: {token[:20]}...")
                print(f"   令牌类型: Bearer")

                self.test_results.append(
                    {"test": "token_generation", "status": "PASS", "message": "令牌生成功能正常"}
                )
                return True
            else:
                print(f"❌ 令牌生成失败：令牌为空或格式错误")
                self.test_results.append(
                    {"test": "token_generation", "status": "FAIL", "message": "令牌为空或格式错误"}
                )
                return False

        except Exception as e:
            print(f"❌ 令牌生成异常: {str(e)}")
            self.test_results.append(
                {"test": "token_generation", "status": "FAIL", "message": f"令牌生成异常: {str(e)}"}
            )
            return False

    def test_token_validation(self):
        """测试令牌验证功能"""
        print("\n🔍 测试5: 令牌验证功能")

        try:
            user = SimpleUser(
                id=4,
                username="validation_test",
                email="validation@test.com",
                password="test123",
                role="user",
                is_active=True,
                created_at=datetime.now(),
            )

            # 生成令牌
            token = self.service.generate_token(user)

            # 验证有效令牌
            valid_user = self.service.verify_token(token)

            # 验证无效令牌
            invalid_user = self.service.verify_token("invalid_token")

            if valid_user is not None and invalid_user is None:
                print(f"✅ 令牌验证功能正常")
                print(f"   有效令牌验证: 通过")
                print(f"   无效令牌验证: 拒绝")
                print(f"   验证用户名: {valid_user.username}")

                self.test_results.append(
                    {"test": "token_validation", "status": "PASS", "message": "令牌验证功能正常"}
                )
                return True
            else:
                print(f"❌ 令牌验证功能异常")
                print(f"   有效令牌验证: {'通过' if valid_user else '失败'}")
                print(f"   无效令牌验证: {'拒绝' if invalid_user is None else '通过（错误）'}")

                self.test_results.append(
                    {"test": "token_validation", "status": "FAIL", "message": "令牌验证逻辑错误"}
                )
                return False

        except Exception as e:
            print(f"❌ 令牌验证异常: {str(e)}")
            self.test_results.append(
                {"test": "token_validation", "status": "FAIL", "message": f"令牌验证异常: {str(e)}"}
            )
            return False

    def test_complete_auth_flow(self):
        """测试完整认证流程"""
        print("\n🔄 测试6: 完整认证流程")

        try:
            # 步骤1: 创建用户
            user = SimpleUser(
                id=5,
                username="flow_test",
                email="flow@test.com",
                password="test123",
                role="user",
                is_active=True,
                created_at=datetime.now(),
            )

            # 步骤2: 存储用户
            self.service.store_user(user)

            # 步骤3: 生成令牌
            token = self.service.generate_token(user)

            # 步骤4: 验证令牌
            verified_user = self.service.verify_token(token)

            # 验证完整流程
            if (
                user.username == verified_user.username
                and user.email == verified_user.email
                and user.role == verified_user.role
            ):

                print(f"✅ 完整认证流程成功")
                print(f"   创建用户: {user.username}")
                print(f"   存储用户: 成功")
                print(f"   生成令牌: 成功")
                print(f"   验证令牌: 成功")
                print(f"   用户信息一致性: 通过")

                self.test_results.append(
                    {"test": "complete_auth_flow", "status": "PASS", "message": "完整认证流程正常"}
                )
                return True
            else:
                print(f"❌ 完整认证流程失败：用户信息不一致")
                self.test_results.append(
                    {"test": "complete_auth_flow", "status": "FAIL", "message": "用户信息不一致"}
                )
                return False

        except Exception as e:
            print(f"❌ 完整认证流程异常: {str(e)}")
            self.test_results.append(
                {
                    "test": "complete_auth_flow",
                    "status": "FAIL",
                    "message": f"完整认证流程异常: {str(e)}",
                }
            )
            return False

    def print_test_report(self):
        """打印测试报告"""
        print("\n" + "=" * 60)
        print("📊 简化认证系统测试报告")
        print("=" * 62)

        total_tests = len(self.test_results)
        passed_tests = sum(1 for result in self.test_results if result["status"] == "PASS")
        success_rate = (passed_tests / total_tests) * 100 if total_tests > 0 else 0

        print(f"🎯 总测试数: {total_tests}")
        print(f"✅ 通过测试: {passed_tests}")
        print(f"📈 成功率: {success_rate:.1f}%")

        print("\n📋 详细测试结果:")
        for result in self.test_results:
            status_icon = "✅" if result["status"] == "PASS" else "❌"
            print(f"  {status_icon} {result['test']}: {result['message']}")

        print("\n" + "=" * 60)

        if success_rate == 100:
            print("🎉 所有测试通过！简化认证系统功能正常！")
        else:
            print(f"⚠️ 部分测试失败，需要进一步检查。")

    def run_all_tests(self):
        """运行所有测试"""
        self.print_banner()

        tests = [
            self.test_user_creation,
            self.test_user_storage,
            self.test_password_validation,
            self.test_token_generation,
            self.test_token_validation,
            self.test_complete_auth_flow,
        ]

        passed_tests = 0
        for test in tests:
            if test():
                passed_tests += 1

        self.print_test_report()
        return passed_tests == len(tests)


async def main():
    """主测试函数"""
    tester = SimpleAuthTester()
    success = tester.run_all_tests()

    if success:
        print("\n🎉 简化认证系统测试完全成功！")
        print("✅ 认证系统已就绪，可以集成到主应用中")
    else:
        print("\n⚠️ 部分测试失败，需要修复问题")

    return success


if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)
