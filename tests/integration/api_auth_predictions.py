#!/usr/bin/env python3
"""
🔗 API集成测试：认证与预测服务集成

测试认证系统和预测服务的协同工作，验证：
1. 用户认证后的预测功能访问
2. JWT token在预测API中的验证
3. 权限控制与预测功能的结合
4. 完整的用户工作流：登录 → 预测 → 查询 → 验证
"""

import asyncio
import logging
import time
from datetime import datetime
from typing import Any

import httpx
import pytest

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class AuthPredictionIntegrationTester:
    """认证与预测服务集成测试器"""

    def __init__(self, base_url: str = "http://localhost:8000"):
        self.base_url = base_url
        self.test_results = []
        self.auth_token: str | None = None
        self.user_data: dict[str, Any] | None = None
        self.prediction_data: dict[str, Any] | None = None

    def log_test(
        self, test_name: str, success: bool, details: str = "", duration: float = 0
    ):
        """记录测试结果"""
        result = {
            "test_name": test_name,
            "success": success,
            "details": details,
            "duration": duration,
            "timestamp": datetime.now().isoformat(),
        }
        self.test_results.append(result)

        status_symbol = "✅" if success else "❌"
        logger.debug(f"{status_symbol} {test_name}")
        if details:
            logger.debug(f"   📝 {details}")
        if duration > 0:
            logger.debug(f"   ⏱️  耗时: {duration:.2f}秒")

    @pytest.mark.asyncio
    async def test_health_endpoints(self) -> bool:
        """测试健康检查端点"""
        start_time = time.time()
        try:
            async with httpx.AsyncClient() as client:
                # 测试认证健康检查
                auth_response = await client.get(f"{self.base_url}/auth/health")
                auth_healthy = auth_response.status_code == 200

                # 测试预测健康检查
                predictions_response = await client.get(
                    f"{self.base_url}/predictions/health"
                )
                predictions_healthy = predictions_response.status_code == 200

                success = auth_healthy and predictions_healthy
                duration = time.time() - start_time

                details = f"认证健康: {auth_healthy}, 预测健康: {predictions_healthy}"
                self.log_test("健康检查端点测试", success, details, duration)
                return success

        except Exception:
            duration = time.time() - start_time
            self.log_test("健康检查端点测试", False, f"异常: {str(e)}", duration)
            return False

    @pytest.mark.asyncio
    async def test_user_registration(self) -> bool:
        """测试用户注册"""
        start_time = time.time()
        try:
            user_data = {
                "username": f"testuser_{int(time.time())}",
                "email": f"test_{int(time.time())}@example.com",
                "password": "testpassword123",
                "full_name": "测试用户",
            }

            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self.base_url}/auth/register", json=user_data, timeout=10.0
                )

            success = response.status_code in [200, 201]
            duration = time.time() - start_time

            if success:
                self.user_data = user_data
                details = f"用户注册成功: {user_data['username']}"
            else:
                details = f"注册失败，状态码: {response.status_code}, 响应: {response.text[:100]}"

            self.log_test("用户注册测试", success, details, duration)
            return success

        except Exception:
            duration = time.time() - start_time
            self.log_test("用户注册测试", False, f"异常: {str(e)}", duration)
            return False

    @pytest.mark.asyncio
    async def test_user_login(self) -> bool:
        """测试用户登录"""
        start_time = time.time()
        try:
            if not self.user_data:
                raise Exception("用户数据不存在，请先注册")

            login_data = {
                "username": self.user_data["username"],
                "password": self.user_data["password"],
            }

            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self.base_url}/auth/login", json=login_data, timeout=10.0
                )

            success = response.status_code == 200
            duration = time.time() - start_time

            if success:
                token_data = response.json()
                self.auth_token = token_data.get("access_token")
                details = "登录成功，获得token"
            else:
                details = f"登录失败，状态码: {response.status_code}, 响应: {response.text[:100]}"

            self.log_test("用户登录测试", success, details, duration)
            return success

        except Exception:
            duration = time.time() - start_time
            self.log_test("用户登录测试", False, f"异常: {str(e)}", duration)
            return False

    @pytest.mark.asyncio
    async def test_unauthorized_prediction_access(self) -> bool:
        """测试未授权的预测API访问"""
        start_time = time.time()
        try:
            async with httpx.AsyncClient() as client:
                # 不带token访问预测API
                response = await client.get(f"{self.base_url}/predictions/")

            success = response.status_code == 401
            duration = time.time() - start_time
            details = f"未授权访问状态码: {response.status_code}"

            self.log_test("未授权预测访问测试", success, details, duration)
            return success

        except Exception:
            duration = time.time() - start_time
            self.log_test("未授权预测访问测试", False, f"异常: {str(e)}", duration)
            return False

    @pytest.mark.asyncio
    async def test_authorized_prediction_access(self) -> bool:
        """测试授权后的预测API访问"""
        start_time = time.time()
        try:
            if not self.auth_token:
                raise Exception("认证token不存在，请先登录")

            headers = {"Authorization": f"Bearer {self.auth_token}"}

            async with httpx.AsyncClient() as client:
                # 带token访问预测API
                response = await client.get(
                    f"{self.base_url}/predictions/", headers=headers
                )

            success = response.status_code == 200
            duration = time.time() - start_time
            details = f"授权访问状态码: {response.status_code}"

            if success:
                prediction_data = response.json()
                details += f", 返回数据: {str(prediction_data)[:100]}"

            self.log_test("授权预测访问测试", success, details, duration)
            return success

        except Exception:
            duration = time.time() - start_time
            self.log_test("授权预测访问测试", False, f"异常: {str(e)}", duration)
            return False

    @pytest.mark.asyncio
    async def test_create_prediction(self) -> bool:
        """测试创建预测"""
        start_time = time.time()
        try:
            if not self.auth_token:
                raise Exception("认证token不存在，请先登录")

            headers = {"Authorization": f"Bearer {self.auth_token}"}
            prediction_request = {"model_version": "default", "include_details": True}

            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self.base_url}/predictions/",
                    headers=headers,
                    json=prediction_request,
                )

            success = response.status_code in [200, 201]
            duration = time.time() - start_time
            details = f"创建预测状态码: {response.status_code}"

            if success:
                self.prediction_data = response.json()
                details += f", 预测ID: {self.prediction_data.get('match_id', 'N/A')}"

            self.log_test("创建预测测试", success, details, duration)
            return success

        except Exception:
            duration = time.time() - start_time
            self.log_test("创建预测测试", False, f"异常: {str(e)}", duration)
            return False

    @pytest.mark.asyncio
    async def test_batch_prediction(self) -> bool:
        """测试批量预测"""
        start_time = time.time()
        try:
            if not self.auth_token:
                raise Exception("认证token不存在，请先登录")

            headers = {"Authorization": f"Bearer {self.auth_token}"}
            batch_request = {
                "match_ids": [12345, 67890, 54321],
                "model_version": "default",
            }

            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self.base_url}/predictions/batch",
                    headers=headers,
                    json=batch_request,
                )

            success = response.status_code == 200
            duration = time.time() - start_time
            details = f"批量预测状态码: {response.status_code}"

            if success:
                batch_data = response.json()
                predictions_count = len(batch_data.get("predictions", []))
                details += f", 预测数量: {predictions_count}"

            self.log_test("批量预测测试", success, details, duration)
            return success

        except Exception:
            duration = time.time() - start_time
            self.log_test("批量预测测试", False, f"异常: {str(e)}", duration)
            return False

    @pytest.mark.asyncio
    async def test_prediction_verification(self) -> bool:
        """测试预测验证"""
        start_time = time.time()
        try:
            if not self.auth_token or not self.prediction_data:
                raise Exception("认证token或预测数据不存在")

            headers = {"Authorization": f"Bearer {self.auth_token}"}
            match_id = self.prediction_data.get("match_id", 12345)
            verification_data = {"actual_outcome": "home", "confidence": 0.8}

            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self.base_url}/predictions/{match_id}/verify",
                    headers=headers,
                    json=verification_data,
                )

            success = response.status_code == 200
            duration = time.time() - start_time
            details = f"预测验证状态码: {response.status_code}"

            if success:
                verification_result = response.json()
                details += f", 验证结果: {verification_result.get('accuracy', 'N/A')}"

            self.log_test("预测验证测试", success, details, duration)
            return success

        except Exception:
            duration = time.time() - start_time
            self.log_test("预测验证测试", False, f"异常: {str(e)}", duration)
            return False

    @pytest.mark.asyncio
    async def test_token_refresh(self) -> bool:
        """测试token刷新"""
        start_time = time.time()
        try:
            if not self.auth_token:
                raise Exception("认证token不存在，请先登录")

            headers = {"Authorization": f"Bearer {self.auth_token}"}

            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self.base_url}/auth/refresh", headers=headers
                )

            success = response.status_code == 200
            duration = time.time() - start_time
            details = f"Token刷新状态码: {response.status_code}"

            if success:
                token_data = response.json()
                new_token = token_data.get("access_token")
                if new_token:
                    self.auth_token = new_token
                    details += ", Token刷新成功"

            self.log_test("Token刷新测试", success, details, duration)
            return success

        except Exception:
            duration = time.time() - start_time
            self.log_test("Token刷新测试", False, f"异常: {str(e)}", duration)
            return False

    @pytest.mark.asyncio
    async def test_logout(self) -> bool:
        """测试用户登出"""
        start_time = time.time()
        try:
            if not self.auth_token:
                raise Exception("认证token不存在，请先登录")

            headers = {"Authorization": f"Bearer {self.auth_token}"}

            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self.base_url}/auth/logout", headers=headers
                )

            success = response.status_code == 200
            duration = time.time() - start_time
            details = f"登出状态码: {response.status_code}"

            self.log_test("用户登出测试", success, details, duration)

            if success:
                self.auth_token = None

            return success

        except Exception:
            duration = time.time() - start_time
            self.log_test("用户登出测试", False, f"异常: {str(e)}", duration)
            return False

    async def run_all_tests(self) -> dict[str, Any]:
        """运行所有集成测试"""
        logger.debug("🚀 开始API集成测试：认证与预测服务集成")
        logger.debug("=" * 60)

        test_methods = [
            self.test_health_endpoints,
            self.test_user_registration,
            self.test_user_login,
            self.test_unauthorized_prediction_access,
            self.test_authorized_prediction_access,
            self.test_create_prediction,
            self.test_batch_prediction,
            self.test_prediction_verification,
            self.test_token_refresh,
            self.test_logout,
        ]

        passed_tests = 0
        total_tests = len(test_methods)

        for test_method in test_methods:
            try:
                if await test_method():
                    passed_tests += 1
                logger.debug()  # 空行分)
            except Exception:
                logger.error(f"测试方法 {test_method.__name__} 执行异常: {e}")
                logger.debug()

        # 生成测试报告
        success_rate = (passed_tests / total_tests) * 100
        report = {
            "total_tests": total_tests,
            "passed_tests": passed_tests,
            "failed_tests": total_tests - passed_tests,
            "success_rate": success_rate,
            "test_results": self.test_results,
            "timestamp": datetime.now().isoformat(),
        }

        logger.debug("=" * 60)
        logger.debug("📊 测试完成！")
        logger.debug(f"总测试数: {total_tests}")
        logger.debug(f"通过测试: {passed_tests}")
        logger.debug(f"失败测试: {total_tests - passed_tests}")
        logger.debug(f"成功率: {success_rate:.1f}%")

        return report


# Pytest测试用例
@pytest.mark.integration
@pytest.mark.asyncio
class TestAuthPredictionIntegration:
    """认证与预测服务集成测试"""

    @pytest.fixture
    async def tester(self):
        """创建测试器实例"""
        return AuthPredictionIntegrationTester()

    @pytest.mark.asyncio
    async def test_health_endpoints(self, tester):
        """测试健康检查端点"""
        result = await tester.test_health_endpoints()
        assert result, "健康检查端点测试失败"

    @pytest.mark.asyncio
    async def test_user_registration(self, tester):
        """测试用户注册"""
        result = await tester.test_user_registration()
        assert result, "用户注册测试失败"

    @pytest.mark.asyncio
    async def test_user_login(self, tester):
        """测试用户登录"""
        result = await tester.test_user_login()
        assert result, "用户登录测试失败"

    @pytest.mark.asyncio
    async def test_unauthorized_prediction_access(self, tester):
        """测试未授权的预测API访问"""
        result = await tester.test_unauthorized_prediction_access()
        assert result, "未授权预测访问测试失败"

    @pytest.mark.asyncio
    async def test_authorized_prediction_access(self, tester):
        """测试授权后的预测API访问"""
        result = await tester.test_authorized_prediction_access()
        assert result, "授权预测访问测试失败"

    @pytest.mark.asyncio
    async def test_create_prediction(self, tester):
        """测试创建预测"""
        result = await tester.test_create_prediction()
        assert result, "创建预测测试失败"

    @pytest.mark.asyncio
    async def test_batch_prediction(self, tester):
        """测试批量预测"""
        result = await tester.test_batch_prediction()
        assert result, "批量预测测试失败"

    @pytest.mark.asyncio
    async def test_prediction_verification(self, tester):
        """测试预测验证"""
        result = await tester.test_prediction_verification()
        assert result, "预测验证测试失败"

    @pytest.mark.asyncio
    async def test_token_refresh(self, tester):
        """测试token刷新"""
        result = await tester.test_token_refresh()
        assert result, "Token刷新测试失败"

    @pytest.mark.asyncio
    async def test_complete_workflow(self, tester):
        """测试完整工作流"""
        report = await tester.run_all_tests()
        assert (
            report["success_rate"] >= 80
        ), f"整体成功率不足80%: {report['success_rate']:.1f}%"


# 独立运行测试的主函数
async def main():
    """主函数：运行完整的集成测试"""
    tester = AuthPredictionIntegrationTester()
    report = await tester.run_all_tests()

    logger.debug("\n🎯 集成测试结果:")
    logger.debug(f"成功率: {report['success_rate']:.1f}%")

    if report["success_rate"] >= 80:
        logger.debug("🎉 集成测试通过！")
        return 0
    else:
        logger.debug("❌ 集成测试失败，成功率不足80%")
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    exit(exit_code)
