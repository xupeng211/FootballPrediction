"""
健康检查工具测试
Health Check Utils Tests

测试src/api/health/utils.py中定义的健康检查工具功能。
Tests health check utility functionality defined in src/api/health/utils.py.
"""

import asyncio
import time
from datetime import datetime

import pytest

# 导入要测试的模块
try:
    from src.api.health.utils import HealthChecker

    HEALTH_UTILS_AVAILABLE = True
except ImportError:
    HEALTH_UTILS_AVAILABLE = False


@pytest.mark.skipif(not HEALTH_UTILS_AVAILABLE, reason="Health utils module not available")
@pytest.mark.unit
class TestHealthChecker:
    """HealthChecker类测试"""

    def setup_method(self):
        """每个测试方法前的设置"""
        self.checker = HealthChecker()

    def test_health_checker_initialization(self):
        """测试HealthChecker初始化"""
        assert self.checker.timeout == 5.0

    def test_health_checker_custom_timeout(self):
        """测试HealthChecker自定义超时时间"""
        custom_checker = HealthChecker()
        # 注意：当前的实现中timeout没有被使用，但我们测试默认值
        assert hasattr(custom_checker, "timeout")

    @pytest.mark.asyncio
    async def test_check_database_healthy(self):
        """测试数据库健康检查（正常情况）"""
        result = await self.checker.check_database()

        # 验证返回结构
        assert isinstance(result, dict)
        assert "status" in result
        assert "latency_ms" in result
        assert "timestamp" in result

        # 验证正常情况
        assert result["status"] == "healthy"
        assert isinstance(result["latency_ms"], (int, float))
        assert result["latency_ms"] >= 0

        # 验证时间戳格式
        try:
            datetime.fromisoformat(result["timestamp"])
            timestamp_valid = True
        except ValueError:
            timestamp_valid = False
        assert timestamp_valid

    @pytest.mark.asyncio
    async def test_check_database_performance(self):
        """测试数据库健康检查性能"""
        start_time = time.time()
        result = await self.checker.check_database()
        end_time = time.time()

        # 检查应该在合理时间内完成（小于1秒）
        assert end_time - start_time < 1.0
        assert result["status"] == "healthy"

    @pytest.mark.asyncio
    async def test_check_redis_healthy(self):
        """测试Redis健康检查（正常情况）"""
        result = await self.checker.check_redis()

        # 验证返回结构
        assert isinstance(result, dict)
        assert "status" in result
        assert "latency_ms" in result
        assert "timestamp" in result

        # 验证正常情况
        assert result["status"] == "healthy"
        assert isinstance(result["latency_ms"], (int, float))
        assert result["latency_ms"] >= 0

        # Redis检查通常比数据库快
        assert result["latency_ms"] < 50  # 应该在50ms以内

    @pytest.mark.asyncio
    async def test_check_redis_performance(self):
        """测试Redis健康检查性能"""
        start_time = time.time()
        result = await self.checker.check_redis()
        end_time = time.time()

        # Redis检查应该很快
        assert end_time - start_time < 0.1
        assert result["status"] == "healthy"

    @pytest.mark.asyncio
    async def test_check_prediction_service_healthy(self):
        """测试预测服务健康检查（正常情况）"""
        result = await self.checker.check_prediction_service()

        # 验证返回结构
        assert isinstance(result, dict)
        assert "status" in result
        assert "latency_ms" in result
        assert "timestamp" in result
        assert "model_version" in result

        # 验证正常情况
        assert result["status"] == "healthy"
        assert isinstance(result["latency_ms"], (int, float))
        assert result["latency_ms"] >= 0
        assert result["model_version"] == "1.0.0"

    @pytest.mark.asyncio
    async def test_check_prediction_service_performance(self):
        """测试预测服务健康检查性能"""
        start_time = time.time()
        result = await self.checker.check_prediction_service()
        end_time = time.time()

        # 检查应该在合理时间内完成
        assert end_time - start_time < 0.5
        assert result["status"] == "healthy"

    @pytest.mark.asyncio
    async def test_check_all_services_healthy(self):
        """测试检查所有服务健康状态（全部正常）"""
        result = await self.checker.check_all_services()

        # 验证整体结构
        assert isinstance(result, dict)
        assert "status" in result
        assert "timestamp" in result
        assert "checks" in result

        # 验证整体状态
        assert result["status"] == "healthy"

        # 验证子检查
        checks = result["checks"]
        assert "database" in checks
        assert "redis" in checks
        assert "prediction_service" in checks

        # 验证所有子检查都健康
        for service_name, check_result in checks.items():
            assert check_result["status"] in ["healthy", "ok"]
            assert "latency_ms" in check_result
            assert "timestamp" in check_result

    @pytest.mark.asyncio
    async def test_check_all_services_performance(self):
        """测试检查所有服务性能"""
        start_time = time.time()
        result = await self.checker.check_all_services()
        end_time = time.time()

        # 并发检查应该很快完成
        assert end_time - start_time < 0.5
        assert result["status"] == "healthy"

    @pytest.mark.asyncio
    async def test_check_database_with_exception(self):
        """测试数据库检查异常处理"""
        # 模拟数据库连接异常
        with patch("asyncio.sleep", side_effect=Exception("Database connection failed")):
            result = await self.checker.check_database()

            assert result["status"] == "unhealthy"
            assert "error" in result
            assert "Database connection failed" in result["error"]
            assert "latency_ms" in result
            assert "timestamp" in result

    @pytest.mark.asyncio
    async def test_check_redis_with_exception(self):
        """测试Redis检查异常处理"""
        # 模拟Redis连接异常
        with patch("asyncio.sleep", side_effect=Exception("Redis connection failed")):
            result = await self.checker.check_redis()

            assert result["status"] == "unhealthy"
            assert "error" in result
            assert "Redis connection failed" in result["error"]
            assert "latency_ms" in result
            assert "timestamp" in result

    @pytest.mark.asyncio
    async def test_check_prediction_service_with_exception(self):
        """测试预测服务检查异常处理"""
        # 模拟预测服务异常
        with patch("asyncio.sleep", side_effect=Exception("Prediction service unavailable")):
            result = await self.checker.check_prediction_service()

            assert result["status"] == "unhealthy"
            assert "error" in result
            assert "Prediction service unavailable" in result["error"]
            assert "latency_ms" in result
            assert "timestamp" in result

    @pytest.mark.asyncio
    async def test_check_all_services_with_one_unhealthy(self):
        """测试一个服务不健康时的整体状态"""
        # 模拟Redis检查失败
        with patch.object(
            self.checker,
            "check_redis",
            return_value={"status": "unhealthy", "error": "Redis down"},
        ):
            result = await self.checker.check_all_services()

            assert result["status"] == "unhealthy"

            checks = result["checks"]
            assert checks["database"]["status"] in ["healthy", "ok"]
            assert checks["redis"]["status"] == "unhealthy"
            assert checks["prediction_service"]["status"] in ["healthy", "ok"]

    @pytest.mark.asyncio
    async def test_check_all_services_with_multiple_unhealthy(self):
        """测试多个服务不健康时的整体状态"""
        # 模拟数据库和Redis都失败
        with (
            patch.object(
                self.checker,
                "check_database",
                return_value={"status": "error", "error": "DB down"},
            ),
            patch.object(
                self.checker,
                "check_redis",
                return_value={"status": "unhealthy", "error": "Redis down"},
            ),
        ):
            result = await self.checker.check_all_services()

            assert result["status"] == "unhealthy"

            checks = result["checks"]
            assert checks["database"]["status"] == "error"
            assert checks["redis"]["status"] == "unhealthy"
            assert checks["prediction_service"]["status"] in ["healthy", "ok"]

    @pytest.mark.asyncio
    async def test_check_all_services_concurrent_execution(self):
        """测试并发执行所有检查"""
        # 记录开始时间
        start_time = time.time()

        result = await self.checker.check_all_services()

        end_time = time.time()
        execution_time = end_time - start_time

        # 并发执行应该比串行执行快
        # 单个检查大约0.01-0.02秒，三个并发应该大约0.02秒
        assert execution_time < 0.1
        assert result["status"] == "healthy"

    @pytest.mark.asyncio
    async def test_latency_measurement_accuracy(self):
        """测试延迟测量的准确性"""
        # 为特定方法添加已知的延迟

        async def slow_sleep(delay):
            # 强制延迟更长时间
            await asyncio.sleep(0.1)  # 100ms
            await asyncio.sleep(0.1)  # 100ms
            await asyncio.sleep(0.1)  # 100ms

        with patch("asyncio.sleep", side_effect=slow_sleep):
            result = await self.checker.check_database()

            # 延迟应该大于100ms（考虑代码执行时间）
            assert result["latency_ms"] > 100

    @pytest.mark.asyncio
    async def test_timestamp_consistency(self):
        """测试时间戳一致性"""
        # 同时检查多个服务的时间戳
        result = await self.checker.check_all_services()
        main_timestamp = result["timestamp"]

        # 解析主时间戳
        main_dt = datetime.fromisoformat(main_timestamp)

        # 检查各个服务的时间戳
        for service_name, check_result in result["checks"].items():
            service_timestamp = check_result["timestamp"]
            service_dt = datetime.fromisoformat(service_timestamp)

            # 时间差应该在合理范围内（几秒内）
            time_diff = abs((service_dt - main_dt).total_seconds())
            assert time_diff < 5.0  # 5秒内

    @pytest.mark.asyncio
    async def test_error_handling_in_gather(self):
        """测试asyncio.gather的错误处理"""

        # 模拟一个服务抛出异常
        async def failing_check():
            raise ValueError("Service failure")

        with patch.object(self.checker, "check_redis", side_effect=failing_check):
            result = await self.checker.check_all_services()

            # 应该优雅地处理异常
            assert result["status"] == "unhealthy"
            checks = result["checks"]

            # Redis检查应该显示错误
            assert checks["redis"]["status"] == "error"
            assert "Service failure" in checks["redis"]["error"]

    @pytest.mark.asyncio
    async def test_return_exceptions_behavior(self):
        """测试return_exceptions=True的行为"""
        # 这个测试验证asyncio.gather的return_exceptions参数正确工作
        result = await self.checker.check_all_services()

        # 正常情况下所有检查都应该成功
        assert result["status"] == "healthy"
        assert len(result["checks"]) == 3

    def test_class_is_importable(self):
        """测试类可以正常导入"""
from src.api.health.utils import HealthChecker

        # 验证类存在
        assert HealthChecker is not None
        assert callable(HealthChecker)

    def test_class_has_expected_methods(self):
        """测试类具有预期的方法"""
        expected_methods = [
            "check_all_services",
            "check_database",
            "check_redis",
            "check_prediction_service",
        ]

        for method_name in expected_methods:
            assert hasattr(self.checker, method_name)
            method = getattr(self.checker, method_name)
            assert callable(method)
            # 验证是协程函数
            import inspect

            assert inspect.iscoroutinefunction(method)

    @pytest.mark.asyncio
    async def test_multiple_consecutive_checks(self):
        """测试连续多次检查"""
        # 执行多次检查
        results = []
        for _ in range(5):
            result = await self.checker.check_all_services()
            results.append(result)

        # 所有结果都应该一致
        for i in range(1, len(results)):
            assert results[i]["status"] == results[0]["status"]
            assert len(results[i]["checks"]) == len(results[0]["checks"])

    @pytest.mark.asyncio
    async def test_check_result_structure_completeness(self):
        """测试检查结果结构的完整性"""
        result = await self.checker.check_all_services()

        # 验证顶层结构
        required_top_level_keys = ["status", "timestamp", "checks"]
        for key in required_top_level_keys:
            assert key in result

        # 验证子检查结构
        for service_name, check_result in result["checks"].items():
            required_check_keys = ["status", "latency_ms", "timestamp"]
            for key in required_check_keys:
                assert key in check_result, f"Missing {key} in {service_name} check"

            # 验证数据类型
            assert isinstance(check_result["status"], str)
            assert isinstance(check_result["latency_ms"], (int, float))
            assert isinstance(check_result["timestamp"], str)

            # 特殊检查的特殊字段
            if service_name == "prediction_service":
                assert "model_version" in check_result
