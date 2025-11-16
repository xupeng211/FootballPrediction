#!/usr/bin/env python3
"""
🔍 API集成测试：数据一致性验证

测试API数据的一致性，包括：
1. 预测创建后的数据存储和检索一致性
2. 用户会话状态维护
3. 缓存数据的一致性
4. 并发操作的数据一致性
5. 数据格式和约束的一致性验证
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


class DataConsistencyTester:
    """API数据一致性测试器"""

    def __init__(self, base_url: str = "http://localhost:8000"):
        self.base_url = base_url
        self.test_results = []
        self.auth_token: str | None = None
        self.test_data: dict[str, Any] = {}
        self.consistency_errors: list[str] = []

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

        if details:
            pass
        if duration > 0:
            pass

    def log_consistency_error(self, error_msg: str):
        """记录一致性错误"""
        self.consistency_errors.append(error_msg)
        logger.error(f"数据一致性错误: {error_msg}")

    async def setup_test_user(self) -> bool:
        """设置测试用户"""
        start_time = time.time()
        try:
            # 注册测试用户
            user_data = {
                "username": f"consistency_test_{int(time.time())}",
                "email": f"consistency_{int(time.time())}@example.com",
                "password": "testpassword123",
                "full_name": "一致性测试用户",
            }

            async with httpx.AsyncClient() as client:
                register_response = await client.post(
                    f"{self.base_url}/auth/register", json=user_data, timeout=10.0
                )

                if register_response.status_code not in [200, 201]:
                    raise Exception(f"用户注册失败: {register_response.status_code}")

                # 登录获取token
                login_response = await client.post(
                    f"{self.base_url}/auth/login",
                    json={
                        "username": user_data["username"],
                        "password": user_data["password"],
                    },
                    timeout=10.0,
                )

                if login_response.status_code != 200:
                    raise Exception(f"用户登录失败: {login_response.status_code}")

                token_data = login_response.json()
                self.auth_token = token_data.get("access_token")
                self.test_data["user"] = user_data

            duration = time.time() - start_time
            self.log_test("测试用户设置", True, "测试用户创建和登录成功", duration)
            return True

        except Exception as e:
            duration = time.time() - start_time
            self.log_test("测试用户设置", False, f"异常: {str(e)}", duration)
            return False

    @pytest.mark.asyncio

    async def test_prediction_creation_consistency(self) -> bool:
        """测试预测创建的数据一致性"""
        start_time = time.time()
        try:
            if not self.auth_token:
                raise Exception("认证token不存在")

            headers = {"Authorization": f"Bearer {self.auth_token}"}

            # 创建预测请求
            prediction_request = {"model_version": "default", "include_details": True}

            async with httpx.AsyncClient() as client:
                # 发送创建请求
                create_response = await client.post(
                    f"{self.base_url}/predictions/",
                    headers=headers,
                    json=prediction_request,
                )

                if create_response.status_code not in [200, 201]:
                    raise Exception(f"创建预测失败: {create_response.status_code}")

                created_prediction = create_response.json()
                match_id = created_prediction.get("match_id")

                if not match_id:
                    raise Exception("创建的预测缺少match_id")

                # 立即查询验证数据一致性
                get_response = await client.get(
                    f"{self.base_url}/predictions/{match_id}", headers=headers
                )

                if get_response.status_code != 200:
                    raise Exception(f"查询预测失败: {get_response.status_code}")

                retrieved_prediction = get_response.json()

                # 验证数据一致性
                consistency_checks = [
                    (
                        "match_id一致性",
                        created_prediction.get("match_id")
                        == retrieved_prediction.get("match_id"),
                    ),
                    (
                        "model_version一致性",
                        created_prediction.get("model_version")
                        == retrieved_prediction.get("model_version"),
                    ),
                    (
                        "概率和接近1.0",
                        abs(
                            (
                                created_prediction.get("home_win_prob", 0)
                                + created_prediction.get("draw_prob", 0)
                                + created_prediction.get("away_win_prob", 0)
                            )
                            - 1.0
                        )
                        < 0.01,
                    ),
                    (
                        "置信度在有效范围内",
                        0 <= created_prediction.get("confidence", 0) <= 1,
                    ),
                    (
                        "预测结果有效",
                        created_prediction.get("predicted_outcome")
                        in ["home", "draw", "away"],
                    ),
                ]

                failed_checks = [
                    check_name
                    for check_name, passed in consistency_checks
                    if not passed
                ]

                if failed_checks:
                    error_msg = f"数据一致性检查失败: {', '.join(failed_checks)}"
                    self.log_consistency_error(error_msg)
                    raise Exception(error_msg)

                # 保存测试数据
                self.test_data["prediction"] = created_prediction
                self.test_data["retrieved_prediction"] = retrieved_prediction

            duration = time.time() - start_time
            details = f"预测ID: {match_id}, 所有一致性检查通过"
            self.log_test("预测创建一致性", True, details, duration)
            return True

        except Exception as e:
            duration = time.time() - start_time
            self.log_test("预测创建一致性", False, f"异常: {str(e)}", duration)
            return False

    @pytest.mark.asyncio

    async def test_batch_prediction_consistency(self) -> bool:
        """测试批量预测的数据一致性"""
        start_time = time.time()
        try:
            if not self.auth_token:
                raise Exception("认证token不存在")

            headers = {"Authorization": f"Bearer {self.auth_token}"}

            # 创建批量预测请求
            batch_request = {
                "match_ids": [11111, 22222, 33333],
                "model_version": "default",
            }

            async with httpx.AsyncClient() as client:
                # 发送批量创建请求
                batch_response = await client.post(
                    f"{self.base_url}/predictions/batch",
                    headers=headers,
                    json=batch_request,
                )

                if batch_response.status_code != 200:
                    raise Exception(f"批量创建预测失败: {batch_response.status_code}")

                batch_result = batch_response.json()
                predictions = batch_result.get("predictions", [])
                total_count = batch_result.get("total", 0)

                # 验证批量数据一致性
                consistency_checks = [
                    (
                        "返回数量匹配",
                        len(predictions) == len(batch_request["match_ids"]),
                    ),
                    ("总数匹配", total_count == len(predictions)),
                    (
                        "所有预测都有match_id",
                        all(
                            p.get("match_id") in batch_request["match_ids"]
                            for p in predictions
                        ),
                    ),
                    (
                        "模型版本一致",
                        all(
                            p.get("model_version") == batch_request["model_version"]
                            for p in predictions
                        ),
                    ),
                    (
                        "概率和都接近1.0",
                        all(
                            abs(
                                (
                                    p.get("home_win_prob", 0)
                                    + p.get("draw_prob", 0)
                                    + p.get("away_win_prob", 0)
                                )
                                - 1.0
                            )
                            < 0.01
                            for p in predictions
                        ),
                    ),
                ]

                failed_checks = [
                    check_name
                    for check_name, passed in consistency_checks
                    if not passed
                ]

                if failed_checks:
                    error_msg = f"批量预测一致性检查失败: {', '.join(failed_checks)}"
                    self.log_consistency_error(error_msg)
                    raise Exception(error_msg)

                # 保存测试数据
                self.test_data["batch_predictions"] = predictions

            duration = time.time() - start_time
            details = f"批量预测数量: {len(predictions)}, 所有一致性检查通过"
            self.log_test("批量预测一致性", True, details, duration)
            return True

        except Exception as e:
            duration = time.time() - start_time
            self.log_test("批量预测一致性", False, f"异常: {str(e)}", duration)
            return False

    @pytest.mark.asyncio

    async def test_history_data_consistency(self) -> bool:
        """测试历史数据的一致性"""
        start_time = time.time()
        try:
            if not self.auth_token:
                raise Exception("认证token不存在")

            headers = {"Authorization": f"Bearer {self.auth_token}"}

            async with httpx.AsyncClient() as client:
                # 获取预测历史
                history_response = await client.get(
                    f"{self.base_url}/predictions/history", headers=headers
                )

                if history_response.status_code != 200:
                    raise Exception(f"获取历史数据失败: {history_response.status_code}")

                history_data = history_response.json()
                predictions = history_data.get("predictions", [])

                # 验证历史数据一致性
                consistency_checks = [
                    ("历史数据是列表", isinstance(predictions, list)),
                    (
                        "每个预测都有必要字段",
                        all(
                            all(
                                key in p
                                for key in [
                                    "match_id",
                                    "predicted_outcome",
                                    "confidence",
                                ]
                            )
                            for p in predictions
                        ),
                    ),
                    (
                        "预测结果有效",
                        all(
                            p.get("predicted_outcome") in ["home", "draw", "away"]
                            for p in predictions
                        ),
                    ),
                    (
                        "置信度范围有效",
                        all(0 <= p.get("confidence", 0) <= 1 for p in predictions),
                    ),
                ]

                failed_checks = [
                    check_name
                    for check_name, passed in consistency_checks
                    if not passed
                ]

                if failed_checks:
                    error_msg = f"历史数据一致性检查失败: {', '.join(failed_checks)}"
                    self.log_consistency_error(error_msg)
                    raise Exception(error_msg)

                # 保存测试数据
                self.test_data["history"] = history_data

            duration = time.time() - start_time
            details = f"历史预测数量: {len(predictions)}, 所有一致性检查通过"
            self.log_test("历史数据一致性", True, details, duration)
            return True

        except Exception as e:
            duration = time.time() - start_time
            self.log_test("历史数据一致性", False, f"异常: {str(e)}", duration)
            return False

    @pytest.mark.asyncio

    async def test_concurrent_operations_consistency(self) -> bool:
        """测试并发操作的数据一致性"""
        start_time = time.time()
        try:
            if not self.auth_token:
                raise Exception("认证token不存在")

            headers = {"Authorization": f"Bearer {self.auth_token}"}

            # 并发创建多个预测
            async def create_prediction_async(
                match_id: int,
            ) -> dict[str, Any] | None:
                async with httpx.AsyncClient() as client:
                    response = await client.post(
                        f"{self.base_url}/predictions/",
                        headers=headers,
                        json={"model_version": "default", "include_details": True},
                    )
                    if response.status_code in [200, 201]:
                        return response.json()
                    return None

            # 启动并发任务
            match_ids = [10001, 10002, 10003, 10004, 10005]
            tasks = [create_prediction_async(mid) for mid in match_ids]
            results = await asyncio.gather(*tasks, return_exceptions=True)

            # 过滤成功的结果
            successful_predictions = [r for r in results if isinstance(r, dict)]
            failed_operations = [r for r in results if isinstance(r, Exception)]

            # 验证并发操作一致性
            consistency_checks = [
                ("大部分操作成功", len(successful_predictions) >= len(match_ids) * 0.8),
                (
                    "没有重复的match_id",
                    len({p.get("match_id") for p in successful_predictions})
                    == len(successful_predictions),
                ),
                (
                    "所有预测都有有效数据",
                    all(
                        all(
                            key in p
                            for key in ["match_id", "predicted_outcome", "confidence"]
                        )
                        for p in successful_predictions
                    ),
                ),
            ]

            failed_checks = [
                check_name for check_name, passed in consistency_checks if not passed
            ]

            if failed_checks:
                error_msg = f"并发操作一致性检查失败: {', '.join(failed_checks)}"
                self.log_consistency_error(error_msg)
                # 对于并发测试，我们记录错误但不一定失败
                logger.warning(error_msg)

            duration = time.time() - start_time
            details = f"成功: {len(successful_predictions)}/{len(match_ids)}, 失败: {len(failed_operations)}"
            self.log_test("并发操作一致性", len(failed_checks) == 0, details, duration)
            return len(failed_checks) == 0

        except Exception as e:
            duration = time.time() - start_time
            self.log_test("并发操作一致性", False, f"异常: {str(e)}", duration)
            return False

    @pytest.mark.asyncio

    async def test_data_format_consistency(self) -> bool:
        """测试数据格式的一致性"""
        start_time = time.time()
        try:
            # 测试不同API端点返回的数据格式一致性
            endpoints_to_test = [
                "/predictions/",
                "/predictions/history",
                "/predictions/recent",
            ]

            headers = {"Authorization": f"Bearer {self.auth_token}"}
            format_errors = []

            async with httpx.AsyncClient() as client:
                for endpoint in endpoints_to_test:
                    try:
                        response = await client.get(
                            f"{self.base_url}{endpoint}", headers=headers, timeout=5.0
                        )

                        if response.status_code == 200:
                            data = response.json()

                            # 验证响应格式
                            if endpoint == "/predictions/":
                                # 根端点应该有基本信息
                                if not isinstance(data, dict):
                                    format_errors.append(
                                        f"{endpoint}: 响应不是字典格式"
                                    )
                            elif endpoint in [
                                "/predictions/history",
                                "/predictions/recent",
                            ]:
                                # 列表端点应该有predictions数组
                                if (
                                    not isinstance(data, dict)
                                    or "predictions" not in data
                                ):
                                    format_errors.append(
                                        f"{endpoint}: 缺少predictions字段"
                                    )
                                elif not isinstance(data.get("predictions"), list):
                                    format_errors.append(
                                        f"{endpoint}: predictions不是数组格式"
                                    )

                    except Exception as e:
                        logger.warning(f"测试端点 {endpoint} 时异常: {e}")

            success = len(format_errors) == 0
            duration = time.time() - start_time
            details = f"测试端点数: {len(endpoints_to_test)}, 格式错误数: {len(format_errors)}"

            if format_errors:
                details += f", 错误: {'; '.join(format_errors[:2])}"

            self.log_test("数据格式一致性", success, details, duration)
            return success

        except Exception as e:
            duration = time.time() - start_time
            self.log_test("数据格式一致性", False, f"异常: {str(e)}", duration)
            return False

    async def run_all_consistency_tests(self) -> dict[str, Any]:
        """运行所有数据一致性测试"""

        # 首先设置测试用户
        if not await self.setup_test_user():
            return {
                "total_tests": 0,
                "passed_tests": 0,
                "failed_tests": 0,
                "success_rate": 0,
                "consistency_errors": ["测试用户设置失败"],
                "timestamp": datetime.now().isoformat(),
            }

        test_methods = [
            ("预测创建一致性", self.test_prediction_creation_consistency),
            ("批量预测一致性", self.test_batch_prediction_consistency),
            ("历史数据一致性", self.test_history_data_consistency),
            ("并发操作一致性", self.test_concurrent_operations_consistency),
            ("数据格式一致性", self.test_data_format_consistency),
        ]

        passed_tests = 0
        total_tests = len(test_methods)

        for test_name, test_method in test_methods:
            try:
                if await test_method():
                    passed_tests += 1
                await asyncio.sleep(0.1)  # 避免请求过快
            except Exception as e:
                logger.error(f"测试方法 {test_name} 执行异常: {e}")

        # 生成测试报告
        success_rate = (passed_tests / total_tests) * 100
        report = {
            "total_tests": total_tests,
            "passed_tests": passed_tests,
            "failed_tests": total_tests - passed_tests,
            "success_rate": success_rate,
            "consistency_errors": self.consistency_errors,
            "test_results": self.test_results,
            "test_data_summary": {
                "has_user": "user" in self.test_data,
                "has_prediction": "prediction" in self.test_data,
                "has_batch_predictions": "batch_predictions" in self.test_data,
                "has_history": "history" in self.test_data,
            },
            "timestamp": datetime.now().isoformat(),
        }

        if self.consistency_errors:
            for _error in self.consistency_errors:
                pass

        return report


# Pytest测试用例
@pytest.mark.integration
@pytest.mark.asyncio
class TestDataConsistency:
    """API数据一致性集成测试"""

    @pytest.fixture
    async def consistency_tester(self):
        """创建数据一致性测试器实例"""
        return DataConsistencyTester()

    @pytest.mark.asyncio

    async def test_prediction_creation_consistency(self, consistency_tester):
        """测试预测创建的数据一致性"""
        await consistency_tester.setup_test_user()
        result = await consistency_tester.test_prediction_creation_consistency()
        assert result, "预测创建一致性测试失败"

    @pytest.mark.asyncio

    async def test_batch_prediction_consistency(self, consistency_tester):
        """测试批量预测的数据一致性"""
        await consistency_tester.setup_test_user()
        result = await consistency_tester.test_batch_prediction_consistency()
        assert result, "批量预测一致性测试失败"

    @pytest.mark.asyncio

    async def test_history_data_consistency(self, consistency_tester):
        """测试历史数据的一致性"""
        await consistency_tester.setup_test_user()
        result = await consistency_tester.test_history_data_consistency()
        assert result, "历史数据一致性测试失败"

    @pytest.mark.asyncio

    async def test_data_format_consistency(self, consistency_tester):
        """测试数据格式的一致性"""
        await consistency_tester.setup_test_user()
        result = await consistency_tester.test_data_format_consistency()
        assert result, "数据格式一致性测试失败"

    @pytest.mark.asyncio

    async def test_all_consistency_checks(self, consistency_tester):
        """测试所有一致性检查"""
        report = await consistency_tester.run_all_consistency_tests()
        assert (
            report["success_rate"] >= 80
        ), f"一致性测试成功率不足80%: {report['success_rate']:.1f}%"
        assert (
            len(report["consistency_errors"]) == 0
        ), f"发现一致性错误: {report['consistency_errors']}"


# 独立运行测试的主函数
async def main():
    """主函数：运行完整的数据一致性测试"""
    tester = DataConsistencyTester()
    report = await tester.run_all_consistency_tests()

    if report["success_rate"] >= 80 and len(report["consistency_errors"]) == 0:
        return 0
    else:
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    exit(exit_code)
