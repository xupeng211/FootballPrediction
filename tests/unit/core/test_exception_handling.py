"""
异常处理测试
测试所有自定义异常和错误处理逻辑
"""

import pytest
from datetime import datetime, timezone, timedelta
from typing import Any, Dict, List, Optional
import traceback
import logging


# 自定义异常类定义
class FootballPredictionError(Exception):
    """足球预测系统基础异常"""

    def __init__(
        self,
        message: str,
        error_code: Optional[str] = None,
        details: Optional[Dict] = None,
    ):
        super().__init__(message)
        self.error_code = error_code
        self.details = details or {}
        self.timestamp = datetime.now(timezone.utc)


class ValidationError(FootballPredictionError):
    """验证错误"""

    pass


class NotFoundError(FootballPredictionError):
    """资源未找到错误"""

    pass


class AuthenticationError(FootballPredictionError):
    """认证错误"""

    pass


class AuthorizationError(FootballPredictionError):
    """授权错误"""

    pass


class BusinessRuleError(FootballPredictionError):
    """业务规则错误"""

    pass


class DatabaseError(FootballPredictionError):
    """数据库错误"""

    pass


class ExternalServiceError(FootballPredictionError):
    """外部服务错误"""

    pass


class RateLimitError(FootballPredictionError):
    """速率限制错误"""

    def __init__(self, message: str, retry_after: Optional[int] = None, **kwargs):
        super().__init__(message, **kwargs)
        self.retry_after = retry_after


class TestCustomExceptions:
    """自定义异常测试"""

    def test_base_exception_creation(self):
        """测试基础异常创建"""
        message = "Test error message"
        error_code = "TEST_001"
        details = {"key": "value"}

        exc = FootballPredictionError(message, error_code, details)

        assert str(exc) == message
        assert exc.error_code == error_code
        assert exc.details == details
        assert isinstance(exc.timestamp, datetime)
        assert exc.timestamp.tzinfo == timezone.utc

    def test_validation_error(self):
        """测试验证错误"""
        exc = ValidationError("Invalid input", code="VAL001", field="email")

        assert isinstance(exc, FootballPredictionError)
        assert exc.error_code == "VAL001"
        assert exc.details["field"] == "email"

    def test_not_found_error(self):
        """测试未找到错误"""
        exc = NotFoundError("User not found", resource="user", id=123)

        assert exc.error_code == "NOT_FOUND"
        assert exc.details["resource"] == "user"
        assert exc.details["id"] == 123

    def test_authentication_error(self):
        """测试认证错误"""
        exc = AuthenticationError("Invalid credentials", attempt_count=3)

        assert exc.error_code is None  # 使用默认
        assert exc.details["attempt_count"] == 3

    def test_authorization_error(self):
        """测试授权错误"""
        exc = AuthorizationError(
            "Access denied", required_role="admin", user_role="user"
        )

        assert exc.details["required_role"] == "admin"
        assert exc.details["user_role"] == "user"

    def test_business_rule_error(self):
        """测试业务规则错误"""
        exc = BusinessRuleError(
            "Prediction deadline passed",
            rule="prediction_deadline",
            deadline="2024-01-01T14:00:00Z",
            current_time="2024-01-01T14:30:00Z",
        )

        assert exc.details["rule"] == "prediction_deadline"
        assert "deadline" in exc.details

    def test_database_error(self):
        """测试数据库错误"""
        original_error = Exception("Connection failed")
        exc = DatabaseError(
            "Database operation failed",
            original_error=str(original_error),
            query="SELECT * FROM users",
        )

        assert "original_error" in exc.details
        assert exc.details["query"] == "SELECT * FROM users"

    def test_external_service_error(self):
        """测试外部服务错误"""
        exc = ExternalServiceError(
            "API request failed",
            service="weather_api",
            status_code=503,
            response_time_ms=5000,
        )

        assert exc.details["service"] == "weather_api"
        assert exc.details["status_code"] == 503

    def test_rate_limit_error(self):
        """测试速率限制错误"""
        exc = RateLimitError(
            "Too many requests", retry_after=60, limit=100, window=3600
        )

        assert exc.retry_after == 60
        assert exc.details["limit"] == 100


class TestExceptionHandling:
    """异常处理逻辑测试"""

    def test_exception_chaining(self):
        """测试异常链"""

        def level_3():
            raise ValueError("Level 3 error")

        def level_2():
            try:
                level_3()
            except ValueError as e:
                raise ValidationError("Validation failed") from e

        def level_1():
            try:
                level_2()
            except ValidationError as e:
                raise BusinessRuleError("Business rule violated") from e

        with pytest.raises(BusinessRuleError) as exc_info:
            level_1()

        # 检查异常链
        exc = exc_info.value
        assert isinstance(exc, BusinessRuleError)
        assert exc.__cause__.__class__.__name__ == "ValidationError"
        assert exc.__cause__.__cause__.__class__.__name__ == "ValueError"

    def test_exception_context_manager(self):
        """测试异常上下文管理器"""

        class ErrorHandler:
            def __init__(self):
                self.errors = []

            def __enter__(self):
                return self

            def __exit__(self, exc_type, exc_val, exc_tb):
                if exc_type is not None:
                    self.errors.append(
                        {
                            "type": exc_type.__name__,
                            "message": str(exc_val),
                            "traceback": traceback.format_exception(
                                exc_type, exc_val, exc_tb
                            ),
                        }
                    )
                    return True  # 抑制异常
                return False

        handler = ErrorHandler()

        with handler:
            raise ValueError("Test error")

        assert len(handler.errors) == 1
        assert handler.errors[0]["type"] == "ValueError"
        assert handler.errors[0]["message"] == "Test error"
        assert "Traceback" in handler.errors[0]["traceback"][0]

    def test_exception_retry_logic(self):
        """测试异常重试逻辑"""
        call_count = 0

        def flaky_function():
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise ExternalServiceError("Service unavailable", service="test")
            return "success"

        def retry_wrapper(func, max_retries=3, delay=0):
            last_exception = None
            for attempt in range(max_retries):
                try:
                    return func()
                except ExternalServiceError as e:
                    last_exception = e
                    if attempt < max_retries - 1:
                        continue
                    raise
            raise last_exception

        _result = retry_wrapper(flaky_function)
        assert _result == "success"
        assert call_count == 3

    def test_exception_fallback(self):
        """测试异常回退机制"""

        def primary_operation():
            raise DatabaseError("Primary DB down")

        def fallback_operation():
            return "fallback_result"

        def execute_with_fallback(primary, fallback):
            try:
                return primary()
            except DatabaseError:
                return fallback()
            except Exception:
                raise

        _result = execute_with_fallback(primary_operation, fallback_operation)
        assert _result == "fallback_result"

    def test_exception_aggregation(self):
        """测试异常聚合"""
        errors = []

        def process_item(item):
            if item == "invalid":
                raise ValidationError(f"Invalid item: {item}")
            return item.upper()

        def process_batch(items):
            results = []
            for item in items:
                try:
                    results.append(process_item(item))
                except ValidationError as e:
                    errors.append(e)
            return results

        items = ["good", "invalid", "also_good", "invalid"]
        results = process_batch(items)

        assert len(results) == 2  # 只有有效项被处理
        assert "GOOD" in results
        assert "ALSO_GOOD" in results
        assert len(errors) == 2  # 两个无效项

    def test_timeout_exception(self):
        """测试超时异常"""
        import asyncio

        async def slow_operation(delay):
            await asyncio.sleep(delay)
            return "done"

        async def with_timeout(operation, timeout_sec):
            try:
                return await asyncio.wait_for(operation(), timeout_sec)
            except asyncio.TimeoutError:
                raise ExternalServiceError(
                    "Operation timed out", timeout_seconds=timeout_sec
                )

        async def test():
            # 这个应该成功
            _result = await with_timeout(lambda: slow_operation(0.1), 1.0)
            assert _result == "done"

            # 这个应该超时
            with pytest.raises(ExternalServiceError) as exc_info:
                await with_timeout(lambda: slow_operation(2.0), 0.1)
            assert exc_info.value.details["timeout_seconds"] == 0.1

        # 运行异步测试
        asyncio.run(test())


class TestErrorRecovery:
    """错误恢复测试"""

    def test_circuit_breaker_pattern(self):
        """测试断路器模式"""

        class CircuitBreaker:
            def __init__(self, failure_threshold=3, timeout=60):
                self.failure_threshold = failure_threshold
                self.timeout = timeout
                self.failure_count = 0
                self.last_failure_time = None
                self.state = "closed"  # closed, open, half-open

            def call(self, func, *args, **kwargs):
                if self.state == "open":
                    if datetime.now() - self.last_failure_time > timedelta(
                        seconds=self.timeout
                    ):
                        self.state = "half-open"
                    else:
                        raise ExternalServiceError("Circuit breaker is open")

                try:
                    _result = func(*args, **kwargs)
                    if self.state == "half-open":
                        self.state = "closed"
                        self.failure_count = 0
                    return result
                except Exception:
                    self.failure_count += 1
                    self.last_failure_time = datetime.now()

                    if self.failure_count >= self.failure_threshold:
                        self.state = "open"
                    raise

        # 创建一个会失败的服务
        failure_count = 0

        def unreliable_service():
            nonlocal failure_count
            failure_count += 1
            if failure_count <= 3:
                raise ExternalServiceError("Service error")
            return "success"

        breaker = CircuitBreaker(failure_threshold=3, timeout=1)

        # 前三次失败
        for i in range(3):
            with pytest.raises(ExternalServiceError):
                breaker.call(unreliable_service)

        # 断路器应该打开
        assert breaker.state == "open"

        # 下一次调用应该立即失败
        with pytest.raises(ExternalServiceError) as exc_info:
            breaker.call(unreliable_service)
        assert "Circuit breaker is open" in str(exc_info.value)

    def test_graceful_degradation(self):
        """测试优雅降级"""

        class FeatureService:
            def __init__(self):
                self.features = {
                    "advanced": lambda: "advanced_result",
                    "basic": lambda: "basic_result",
                    "minimal": lambda: "minimal_result",
                }

            def get_feature(self, feature_name, fallback=True):
                if feature_name in self.features:
                    try:
                        return self.features[feature_name]()
                    except Exception:
                        if fallback:
                            # 尝试降级到更简单的功能
                            fallback_order = ["advanced", "basic", "minimal"]
                            current_index = fallback_order.index(feature_name)
                            if current_index < len(fallback_order) - 1:
                                return self.get_feature(
                                    fallback_order[current_index + 1], fallback=False
                                )
                        raise
                else:
                    raise NotFoundError(f"Feature {feature_name} not found")

        service = FeatureService()

        # 正常情况
        assert service.get_feature("advanced") == "advanced_result"

        # 模拟高级功能失败
        def failing_advanced():
            raise ExternalServiceError("Advanced feature unavailable")

        service.features["advanced"] = failing_advanced

        # 应该降级到基本功能
        assert service.get_feature("advanced") == "basic_result"

        # 模拟基本功能也失败
        def failing_basic():
            raise DatabaseError("Database unavailable")

        service.features["basic"] = failing_basic

        # 应该降级到最小功能
        assert service.get_feature("advanced") == "minimal_result"

    def test_error_notification(self):
        """测试错误通知"""
        notifications = []

        class NotificationService:
            @staticmethod
            def send_error_notification(error: Exception, context: Dict = None):
                notifications.append(
                    {
                        "error": str(error),
                        "type": error.__class__.__name__,
                        "context": context or {},
                        "timestamp": datetime.now(timezone.utc),
                    }
                )

        def operation_with_monitoring(operation):
            try:
                return operation()
            except Exception as e:
                NotificationService.send_error_notification(
                    e, {"operation": operation.__name__}
                )
                raise

        # 执行会失败的操作
        def failing_operation():
            raise ValueError("Something went wrong")

        with pytest.raises(ValueError):
            operation_with_monitoring(failing_operation)

        # 验证通知被发送
        assert len(notifications) == 1
        assert notifications[0]["type"] == "ValueError"
        assert notifications[0]["error"] == "Something went wrong"
        assert notifications[0]["context"]["operation"] == "failing_operation"
