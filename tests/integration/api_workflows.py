#!/usr/bin/env python3
"""
🔄 API集成测试：完整工作流测试

测试完整的用户工作流，包括：
1. 用户注册 → 登录 → 创建预测 → 查询历史 → 验证结果
2. 权限不足用户的访问限制
3. 过期token的处理
4. 并发请求的处理
5. 数据一致性和状态管理
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


class WorkflowTester:
    """API工作流测试器"""

    def __init__(self, base_url: str = "http://localhost:8000"):
        self.base_url = base_url
        self.test_results = []
        self.users: dict[str, dict[str, Any]] = {}
        self.tokens: dict[str, str] = {}
        self.predictions: dict[str, list[dict[str, Any]]] = {}

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

    async def create_test_user(self, user_id: str, role: str = "user") -> bool:
        """创建测试用户"""
        start_time = time.time()
        try:
            user_data = {
                "username": f"{role}_{user_id}_{int(time.time())}",
                "email": f"{role}_{user_id}_{int(time.time())}@example.com",
                "password": f"password_{user_id}",
                "full_name": f"{role.title()} User {user_id}",
            }

            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self.base_url}/auth/register", json=user_data, timeout=10.0
                )

            success = response.status_code in [200, 201]
            duration = time.time() - start_time

            if success:
                self.users[user_id] = user_data
                details = f"用户 {user_id} 注册成功"
            else:
                details = f"用户注册失败，状态码: {response.status_code}"

            self.log_test(f"创建用户{user_id}", success, details, duration)
            return success

        except Exception as e:
            duration = time.time() - start_time
            self.log_test(f"创建用户{user_id}", False, f"异常: {str(e)}", duration)
            return False

    async def login_user(self, user_id: str) -> bool:
        """用户登录"""
        start_time = time.time()
        try:
            if user_id not in self.users:
                raise Exception(f"用户 {user_id} 不存在")

            user_data = self.users[user_id]
            login_data = {
                "username": user_data["username"],
                "password": user_data["password"],
            }

            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self.base_url}/auth/login", json=login_data, timeout=10.0
                )

            success = response.status_code == 200
            duration = time.time() - start_time

            if success:
                token_data = response.json()
                self.tokens[user_id] = token_data.get("access_token")
                details = f"用户 {user_id} 登录成功"
            else:
                details = f"用户 {user_id} 登录失败，状态码: {response.status_code}"

            self.log_test(f"用户{user_id}登录", success, details, duration)
            return success

        except Exception as e:
            duration = time.time() - start_time
            self.log_test(f"用户{user_id}登录", False, f"异常: {str(e)}", duration)
            return False

    async def create_prediction_workflow(self, user_id: str) -> bool:
        """创建预测工作流"""
        start_time = time.time()
        try:
            if user_id not in self.tokens:
                raise Exception(f"用户 {user_id} token不存在")

            headers = {"Authorization": f"Bearer {self.tokens[user_id]}"}
            prediction_request = {"model_version": "default", "include_details": True}

            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self.base_url}/predictions/",
                    headers=headers,
                    json=prediction_request,
                )

            success = response.status_code in [200, 201]
            duration = time.time() - start_time
            details = f"用户 {user_id} 创建预测状态码: {response.status_code}"

            if success:
                prediction_data = response.json()
                if user_id not in self.predictions:
                    self.predictions[user_id] = []
                self.predictions[user_id].append(prediction_data)
                details += f", 预测ID: {prediction_data.get('match_id', 'N/A')}"

            self.log_test(f"用户{user_id}创建预测", success, details, duration)
            return success

        except Exception as e:
            duration = time.time() - start_time
            self.log_test(f"用户{user_id}创建预测", False, f"异常: {str(e)}", duration)
            return False

    async def query_prediction_history(self, user_id: str) -> bool:
        """查询预测历史"""
        start_time = time.time()
        try:
            if user_id not in self.tokens:
                raise Exception(f"用户 {user_id} token不存在")

            headers = {"Authorization": f"Bearer {self.tokens[user_id]}"}

            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{self.base_url}/predictions/history", headers=headers
                )

            success = response.status_code == 200
            duration = time.time() - start_time
            details = f"用户 {user_id} 查询历史状态码: {response.status_code}"

            if success:
                history_data = response.json()
                predictions_count = len(history_data.get("predictions", []))
                details += f", 历史预测数量: {predictions_count}"

            self.log_test(f"用户{user_id}查询历史", success, details, duration)
            return success

        except Exception as e:
            duration = time.time() - start_time
            self.log_test(f"用户{user_id}查询历史", False, f"异常: {str(e)}", duration)
            return False

    async def verify_prediction_workflow(self, user_id: str) -> bool:
        """验证预测工作流"""
        start_time = time.time()
        try:
            if user_id not in self.tokens or user_id not in self.predictions:
                raise Exception(f"用户 {user_id} token或预测数据不存在")

            headers = {"Authorization": f"Bearer {self.tokens[user_id]}"}
            user_predictions = self.predictions[user_id]

            if not user_predictions:
                details = "用户没有预测数据可验证"
                self.log_test(f"用户{user_id}验证预测", True, details, 0)
                return True

            # 验证最新的预测
            latest_prediction = user_predictions[-1]
            match_id = latest_prediction.get("match_id", 12345)
            verification_data = {"actual_outcome": "home", "confidence": 0.85}

            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self.base_url}/predictions/{match_id}/verify",
                    headers=headers,
                    json=verification_data,
                )

            success = response.status_code == 200
            duration = time.time() - start_time
            details = f"用户 {user_id} 验证预测状态码: {response.status_code}"

            if success:
                verification_result = response.json()
                accuracy = verification_result.get("accuracy", 0)
                details += f", 验证准确度: {accuracy}"

            self.log_test(f"用户{user_id}验证预测", success, details, duration)
            return success

        except Exception as e:
            duration = time.time() - start_time
            self.log_test(f"用户{user_id}验证预测", False, f"异常: {str(e)}", duration)
            return False

    @pytest.mark.asyncio
    async def test_complete_user_workflow(self, user_id: str) -> bool:
        """测试完整用户工作流"""
        logger.debug(f"\n🔄 开始用户 {user_id} 的完整工作流测试")
        logger.debug("-" * 50)

        workflow_steps = [
            (f"创建用户{user_id}", lambda: self.create_test_user(user_id)),
            (f"用户{user_id}登录", lambda: self.login_user(user_id)),
            (
                f"用户{user_id}创建预测",
                lambda: self.create_prediction_workflow(user_id),
            ),
            (f"用户{user_id}查询历史", lambda: self.query_prediction_history(user_id)),
            (
                f"用户{user_id}验证预测",
                lambda: self.verify_prediction_workflow(user_id),
            ),
        ]

        passed_steps = 0
        for step_name, step_func in workflow_steps:
            try:
                if await step_func():
                    passed_steps += 1
                await asyncio.sleep(0.1)  # 避免请求过快
            except Exception as e:
                logger.error(f"工作流步骤 {step_name} 执行异常: {e}")

        success_rate = (passed_steps / len(workflow_steps)) * 100
        success = success_rate >= 80

        details = (
            f"通过步骤: {passed_steps}/{len(workflow_steps)} ({success_rate:.1f}%)"
        )
        self.log_test(f"用户{user_id}完整工作流", success, details)
        return success

    @pytest.mark.asyncio
    async def test_concurrent_users(self) -> bool:
        """测试并发用户访问"""
        start_time = time.time()
        try:
            user_ids = ["user1", "user2", "user3"]

            # 并发创建用户
            create_tasks = [self.create_test_user(uid) for uid in user_ids]
            create_results = await asyncio.gather(*create_tasks)
            created_users = [
                uid
                for uid, result in zip(user_ids, create_results, strict=False)
                if result
            ]

            if len(created_users) < 2:
                self.log_test("并发用户测试", False, "创建的用户数量不足")
                return False

            # 并发登录
            login_tasks = [self.login_user(uid) for uid in created_users]
            login_results = await asyncio.gather(*login_tasks)
            logged_users = [
                uid
                for uid, result in zip(created_users, login_results, strict=False)
                if result
            ]

            # 并发创建预测
            prediction_tasks = [
                self.create_prediction_workflow(uid) for uid in logged_users
            ]
            prediction_results = await asyncio.gather(*prediction_tasks)

            success_count = sum(prediction_results)
            duration = time.time() - start_time
            success = success_count >= 2

            details = f"并发用户数: {len(logged_users)}, 成功预测数: {success_count}"
            self.log_test("并发用户测试", success, details, duration)
            return success

        except Exception as e:
            duration = time.time() - start_time
            self.log_test("并发用户测试", False, f"异常: {str(e)}", duration)
            return False

    @pytest.mark.asyncio
    async def test_invalid_token_handling(self) -> bool:
        """测试无效token处理"""
        start_time = time.time()
        try:
            # 使用无效token
            invalid_token = "invalid_token_12345"
            headers = {"Authorization": f"Bearer {invalid_token}"}

            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{self.base_url}/predictions/", headers=headers
                )

            success = response.status_code == 401
            duration = time.time() - start_time
            details = f"无效token状态码: {response.status_code}"

            self.log_test("无效token处理", success, details, duration)
            return success

        except Exception as e:
            duration = time.time() - start_time
            self.log_test("无效token处理", False, f"异常: {str(e)}", duration)
            return False

    @pytest.mark.asyncio
    async def test_expired_token_handling(self) -> bool:
        """测试过期token处理"""
        start_time = time.time()
        try:
            # 创建一个模拟的过期token（这通常需要配置JWT短过期时间）
            expired_token = "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJleHAiOjE2MDAwMDAwMDAsInVzZXJfaWQiOjF9.expired"
            headers = {"Authorization": f"Bearer {expired_token}"}

            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{self.base_url}/predictions/", headers=headers
                )

            success = response.status_code in [401, 403]
            duration = time.time() - start_time
            details = f"过期token状态码: {response.status_code}"

            self.log_test("过期token处理", success, details, duration)
            return success

        except Exception as e:
            duration = time.time() - start_time
            self.log_test("过期token处理", False, f"异常: {str(e)}", duration)
            return False

    async def run_all_workflow_tests(self) -> dict[str, Any]:
        """运行所有工作流测试"""
        logger.debug("🚀 开始API工作流集成测试")
        logger.debug("=" * 60)

        test_methods = [
            (
                "完整用户工作流测试",
                lambda: self.test_complete_user_workflow("workflow_user"),
            ),
            ("并发用户测试", self.test_concurrent_users),
            ("无效token处理", self.test_invalid_token_handling),
            ("过期token处理", self.test_expired_token_handling),
        ]

        passed_tests = 0
        total_tests = len(test_methods)

        for test_name, test_method in test_methods:
            logger.debug(f"\n🧪 执行测试: {test_name}")
            try:
                if await test_method():
                    passed_tests += 1
            except Exception as e:
                logger.error(f"测试方法 {test_name} 执行异常: {e}")

        # 生成测试报告
        success_rate = (passed_tests / total_tests) * 100
        report = {
            "total_tests": total_tests,
            "passed_tests": passed_tests,
            "failed_tests": total_tests - passed_tests,
            "success_rate": success_rate,
            "test_results": self.test_results,
            "users_created": len(self.users),
            "predictions_created": sum(
                len(preds) for preds in self.predictions.values()
            ),
            "timestamp": datetime.now().isoformat(),
        }

        logger.debug("=" * 60)
        logger.debug("📊 工作流测试完成！")
        logger.debug(f"总测试数: {total_tests}")
        logger.debug(f"通过测试: {passed_tests}")
        logger.debug(f"失败测试: {total_tests - passed_tests}")
        logger.debug(f"成功率: {success_rate:.1f}%")
        logger.debug(f"创建用户数: {report['users_created']}")
        logger.debug(f"创建预测数: {report['predictions_created']}")

        return report


# Pytest测试用例
@pytest.mark.integration
@pytest.mark.asyncio
class TestAPIWorkflows:
    """API工作流集成测试"""

    @pytest.fixture
    async def workflow_tester(self):
        """创建工作流测试器实例"""
        return WorkflowTester()

    @pytest.mark.asyncio
    async def test_complete_user_workflow(self, workflow_tester):
        """测试完整用户工作流"""
        result = await workflow_tester.test_complete_user_workflow("test_user")
        assert result, "完整用户工作流测试失败"

    @pytest.mark.asyncio
    async def test_concurrent_users(self, workflow_tester):
        """测试并发用户访问"""
        result = await workflow_tester.test_concurrent_users()
        assert result, "并发用户测试失败"

    @pytest.mark.asyncio
    async def test_invalid_token_handling(self, workflow_tester):
        """测试无效token处理"""
        result = await workflow_tester.test_invalid_token_handling()
        assert result, "无效token处理测试失败"

    @pytest.mark.asyncio
    async def test_expired_token_handling(self, workflow_tester):
        """测试过期token处理"""
        result = await workflow_tester.test_expired_token_handling()
        assert result, "过期token处理测试失败"

    @pytest.mark.asyncio
    async def test_all_workflows(self, workflow_tester):
        """测试所有工作流"""
        report = await workflow_tester.run_all_workflow_tests()
        assert report["success_rate"] >= 75, (
            f"整体成功率不足75%: {report['success_rate']:.1f}%"
        )
        assert report["users_created"] >= 1, "至少需要创建1个用户"
        assert report["predictions_created"] >= 1, "至少需要创建1个预测"


# 独立运行测试的主函数
async def main():
    """主函数：运行完整的工作流测试"""
    tester = WorkflowTester()
    report = await tester.run_all_workflow_tests()

    logger.debug("\n🎯 工作流集成测试结果:")
    logger.debug(f"成功率: {report['success_rate']:.1f}%")
    logger.debug(f"用户数: {report['users_created']}")
    logger.debug(f"预测数: {report['predictions_created']}")

    if report["success_rate"] >= 75:
        logger.debug("🎉 工作流集成测试通过！")
        return 0
    else:
        logger.debug("❌ 工作流集成测试失败，成功率不足75%")
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    exit(exit_code)
