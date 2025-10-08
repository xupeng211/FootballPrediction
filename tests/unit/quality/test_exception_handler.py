"""
数据质量测试 - 异常处理器
"""

from unittest.mock import AsyncMock, MagicMock

import pytest

from src.data.quality.exception_handler import (
    DataQualityException,
    DataQualityExceptionHandler,
)


@pytest.mark.unit
class TestExceptionHandler:
    """ExceptionHandler测试"""

    @pytest.fixture
    def handler(self):
        """创建处理器实例"""
        handler = DataQualityExceptionHandler()
        handler.logger = MagicMock()
        return handler

    @pytest.fixture
    def sample_exception(self):
        """示例异常"""
        return ValueError("Invalid data format")

    @pytest.fixture
    def custom_exception(self):
        """自定义数据质量异常"""
        return DataQualityException(
            message="Null values detected",
            category=ExceptionCategory.DATA_VALIDATION,
            severity=ExceptionSeverity.HIGH,
            context={"column": "score", "null_count": 10},
        )

    def test_handler_initialization(self, handler):
        """测试处理器初始化"""
        assert handler is not None
        assert handler.logger is not None
        assert hasattr(handler, "exception_rules")
        assert hasattr(handler, "recovery_strategies")

    def test_handle_exception(self, handler, sample_exception):
        """测试处理异常"""
        result = handler.handle_exception(
            exception=sample_exception,
            context={"module": "data_processor", "function": "validate_data"},
        )

        assert result["handled"] is True
        assert result["exception_type"] == "ValueError"
        assert result["message"] == "Invalid data format"
        assert "timestamp" in result

    def test_handle_custom_exception(self, handler, custom_exception):
        """测试处理自定义异常"""
        result = handler.handle_exception(custom_exception)

        assert result["category"] == ExceptionCategory.DATA_VALIDATION
        assert result["severity"] == ExceptionSeverity.HIGH
        assert result["context"]["column"] == "score"
        assert result["recovery_strategy"] is not None

    def test_register_exception_rule(self, handler):
        """测试注册异常规则"""

        def null_handler(exception, context):
            return {"action": "fill_nulls", "value": 0}

        # 注册规则
        handler.register_exception_rule(
            exception_type=ValueError,
            handler_func=null_handler,
            condition=lambda e: "null" in str(e).lower(),
        )

        # 验证规则已注册
        assert ValueError in handler.exception_rules

    def test_apply_recovery_strategy(self, handler):
        """测试应用恢复策略"""
        # 模拟数据错误
        data = {"scores": [1, None, 3, None, 5]}
        exception = ValueError("Null values in scores")

        # 注册恢复策略
        def recover_nulls(exception, context):
            if "null" in str(exception).lower():
                data = context["data"]
                for i, val in enumerate(data["scores"]):
                    if val is None:
                        data["scores"][i] = 0
                return {"action": "filled_nulls", "data": data}

        # 应用策略
        result = handler.apply_recovery_strategy(
            exception=exception, context={"data": data}, strategy=recover_nulls
        )

        assert result["action"] == "filled_nulls"
        assert result["data"]["scores"] == [1, 0, 3, 0, 5]

    def test_exception_categorization(self, handler):
        """测试异常分类"""
        # 数据验证异常
        e1 = ValueError("Invalid data type")
        category1 = handler.categorize_exception(e1)
        assert category1 == ExceptionCategory.DATA_VALIDATION

        # 连接异常
        e2 = ConnectionError("Database connection failed")
        category2 = handler.categorize_exception(e2)
        assert category2 == ExceptionCategory.CONNECTIVITY

        # 权限异常
        e3 = PermissionError("Access denied")
        category3 = handler.categorize_exception(e3)
        assert category3 == ExceptionCategory.PERMISSION

        # 超时异常
        e4 = TimeoutError("Operation timed out")
        category4 = handler.categorize_exception(e4)
        assert category4 == ExceptionCategory.TIMEOUT

    def test_exception_severity_assessment(self, handler):
        """测试异常严重程度评估"""
        # 关键系统错误
        e1 = RuntimeError("System crash")
        severity1 = handler.assess_severity(e1)
        assert severity1 == ExceptionSeverity.CRITICAL

        # 数据问题
        e2 = ValueError("Missing required field")
        severity2 = handler.assess_severity(e2)
        assert severity2 == ExceptionSeverity.HIGH

        # 警告级别
        e3 = UserWarning("Deprecated feature used")
        severity3 = handler.assess_severity(e3)
        assert severity3 == ExceptionSeverity.LOW

    @pytest.mark.asyncio
    async def test_async_exception_handling(self, handler):
        """测试异步异常处理"""

        async def failing_function():
            raise ValueError("Async operation failed")

        # 使用装饰器处理异常
        @handler.async_exception_handler
        async def wrapped_function():
            await failing_function()

        result = await wrapped_function()
        assert result["success"] is False
        assert "error" in result

    def test_exception_retry_mechanism(self, handler):
        """测试异常重试机制"""
        attempts = []

        def flaky_function():
            attempts.append(1)
            if len(attempts) < 3:
                raise ConnectionError("Temporary failure")
            return "success"

        # 使用重试装饰器
        @handler.retry(max_attempts=3, delay=0)
        def wrapped_function():
            return flaky_function()

        result = wrapped_function()
        assert result == "success"
        assert len(attempts) == 3

    @pytest.mark.asyncio
    async def test_exception_aggregation(self, handler):
        """测试异常聚合"""
        exceptions = [
            ValueError("Null value in row 1"),
            ValueError("Null value in row 2"),
            ValueError("Null value in row 3"),
            ConnectionError("DB connection failed"),
        ]

        aggregated = handler.aggregate_exceptions(exceptions)

        assert isinstance(aggregated, dict)
        assert aggregated["ValueError"]["count"] == 3
        assert aggregated["ConnectionError"]["count"] == 1
        assert "most_common" in aggregated

    def test_exception_context_builder(self, handler):
        """测试异常上下文构建"""
        context = handler.build_exception_context(
            module="data_processor",
            function="process_data",
            line_number=42,
            variables={"data_size": 1000, "batch_id": "B001"},
            additional_info={"processing_time": 5.2},
        )

        assert context["module"] == "data_processor"
        assert context["function"] == "process_data"
        assert context["line_number"] == 42
        assert context["variables"]["data_size"] == 1000

    def test_exception_logging(self, handler, custom_exception):
        """测试异常日志记录"""
        # 处理异常
        handler.handle_exception(custom_exception)

        # 验证日志被调用
        handler.logger.error.assert_called()

        # 获取日志参数
        call_args = handler.logger.error.call_args[0]
        assert "DataQualityException" in call_args[0]

    def test_exception_notification(self, handler, custom_exception):
        """测试异常通知"""
        # Mock通知器
        mock_notifier = MagicMock()
        mock_notifier.send = AsyncMock(return_value=True)
        handler.add_notifier(mock_notifier)

        # 异步通知
        async def test_notification():
            result = await handler.notify_exception(custom_exception)
            return result

        # 运行异步测试
        import asyncio

        result = asyncio.run(test_notification())
        assert result is True
        mock_notifier.send.assert_called_once()

    def test_exception_metrics(self, handler):
        """测试异常指标收集"""
        # 处理多个异常
        exceptions = [
            ValueError("Error 1"),
            ValueError("Error 2"),
            RuntimeError("Critical error"),
            ValueError("Error 3"),
        ]

        for exc in exceptions:
            handler.handle_exception(exc)

        # 获取指标
        metrics = handler.get_exception_metrics()

        assert metrics["total_exceptions"] == 4
        assert metrics["by_type"]["ValueError"] == 3
        assert metrics["by_type"]["RuntimeError"] == 1
        assert "by_severity" in metrics
        assert "resolution_time" in metrics

    def test_exception_recovery_templates(self, handler):
        """测试异常恢复模板"""
        # 使用预定义的恢复模板
        data = {"scores": [1, None, 3]}
        exception = ValueError("Null values detected")

        # 应用模板恢复
        recovered_data = handler.apply_template_recovery(
            exception=exception, template="fill_nulls", data=data, fill_value=0
        )

        assert recovered_data["scores"] == [1, 0, 3]

    def test_exception_pattern_matching(self, handler):
        """测试异常模式匹配"""
        # 注册模式
        handler.register_exception_pattern(
            pattern=r"Null value in (.*)",
            category=ExceptionCategory.DATA_VALIDATION,
            action="log_and_continue",
        )

        # 测试匹配
        exception = ValueError("Null value in column 'score'")
        match = handler.match_exception_pattern(exception)

        assert match is not None
        assert match["category"] == ExceptionCategory.DATA_VALIDATION
        assert match["action"] == "log_and_continue"

    @pytest.mark.asyncio
    async def test_exception_circuit_breaker(self, handler):
        """测试异常熔断器"""
        # 配置熔断器
        handler.configure_circuit_breaker(
            failure_threshold=3, recovery_timeout=1, expected_exception=ValueError
        )

        # 触发失败
        for _ in range(3):
            try:
                handler.circuit_breaker.call(
                    lambda: (_ for _ in ()).throw(ValueError("Test error"))
                )
            except ValueError:
                pass

        # 熔断器应该打开
        assert handler.circuit_breaker.state == "open"

    def test_exception_benchmarking(self, handler):
        """测试异常处理性能基准"""
        import time

        # 模拟大量异常
        start_time = time.time()
        for i in range(1000):
            exception = ValueError(f"Error {i}")
            handler.handle_exception(exception)
        end_time = time.time()

        processing_time = end_time - start_time

        # 验证性能
        assert processing_time < 1.0  # 应该在1秒内完成
        assert handler.get_exception_metrics()["total_exceptions"] == 1000

    def test_exception_report_generation(self, handler):
        """测试异常报告生成"""
        # 处理一些异常
        handler.handle_exception(ValueError("Test error 1"))
        handler.handle_exception(RuntimeError("Critical error"))
        handler.handle_exception(ValueError("Test error 2"))

        # 生成报告
        report = handler.generate_exception_report(format="dict", include_details=True)

        assert "summary" in report
        assert "exceptions" in report
        assert "recommendations" in report
        assert report["summary"]["total"] == 3

    def test_exception_learning(self, handler):
        """测试异常学习和优化"""
        # 历史异常数据
        historical_exceptions = [
            {
                "type": "ValueError",
                "pattern": "Null in column",
                "resolution": "fill_nulls",
            },
            {
                "type": "ValueError",
                "pattern": "Null in column",
                "resolution": "fill_nulls",
            },
            {"type": "ConnectionError", "pattern": "Timeout", "resolution": "retry"},
        ]

        # 学习模式
        learned_patterns = handler.learn_from_exceptions(historical_exceptions)

        assert isinstance(learned_patterns, dict)
        assert "ValueError:Null in column" in learned_patterns
        assert (
            learned_patterns["ValueError:Null in column"]["resolution"] == "fill_nulls"
        )

    def test_exception_handler_config(self, handler):
        """测试异常处理器配置"""
        # 更新配置
        handler.update_config(
            {
                "max_retry_attempts": 5,
                "default_severity": "medium",
                "enable_notifications": True,
                "log_format": "json",
            }
        )

        # 验证配置
        assert handler.config["max_retry_attempts"] == 5
        assert handler.config["default_severity"] == "medium"
        assert handler.config["enable_notifications"] is True

    @pytest.mark.asyncio
    async def test_exception_health_check(self, handler):
        """测试异常处理器健康检查"""
        # 模拟健康检查
        health = await handler.health_check()

        assert "status" in health
        assert "metrics" in health
        assert "recent_errors" in health
        assert health["status"] in ["healthy", "degraded", "unhealthy"]


@pytest.mark.unit
class TestDataQualityException:
    """DataQualityException测试"""

    def test_custom_exception_creation(self):
        """测试创建自定义异常"""
        exc = DataQualityException(
            message="Test error",
            category=ExceptionCategory.DATA_VALIDATION,
            severity=ExceptionSeverity.MEDIUM,
            context={"test": True},
        )

        assert exc.message == "Test error"
        assert exc.category == ExceptionCategory.DATA_VALIDATION
        assert exc.severity == ExceptionSeverity.MEDIUM
        assert exc.context["test"] is True

    def test_custom_exception_to_dict(self):
        """测试自定义异常转字典"""
        exc = DataQualityException(
            message="Test error",
            category=ExceptionCategory.DATA_VALIDATION,
            severity=ExceptionSeverity.MEDIUM,
        )

        exc_dict = exc.to_dict()

        assert exc_dict["message"] == "Test error"
        assert exc_dict["category"] == "DATA_VALIDATION"
        assert exc_dict["severity"] == "MEDIUM"
        assert "timestamp" in exc_dict

    def test_custom_exception_from_dict(self):
        """测试从字典创建自定义异常"""
        data = {
            "message": "Test error",
            "category": "DATA_VALIDATION",
            "severity": "MEDIUM",
            "context": {"test": True},
        }

        exc = DataQualityException.from_dict(data)

        assert exc.message == "Test error"
        assert exc.category == ExceptionCategory.DATA_VALIDATION
        assert exc.severity == ExceptionSeverity.MEDIUM
