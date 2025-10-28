"""
核心模块异常测试
Core Module Exceptions Tests

测试src/core/exceptions.py中定义的所有异常类。
Tests all exception classes defined in src/core/exceptions.py.
"""

from typing import Type

import pytest

# 导入要测试的异常模块
try:
    from src.core.exceptions import (
        AdapterError,
        AuthenticationError,
        AuthorizationError,
        BacktestError,
        BusinessRuleError,
        CacheError,
        ConfigError,
        ConsistencyError,
        DatabaseError,
        DataError,
        DataProcessingError,
        DataQualityError,
        DependencyInjectionError,
        DomainError,
        FootballPredictionError,
        LineageError,
        ModelError,
        PipelineError,
        PredictionError,
        RateLimitError,
        ServiceError,
        ServiceLifecycleError,
        StreamingError,
        TaskExecutionError,
        TaskRetryError,
        TimeoutError,
        TrackingError,
        ValidationError,
    )

    EXCEPTIONS_AVAILABLE = True
except ImportError:
    EXCEPTIONS_AVAILABLE = False


@pytest.mark.skipif(not EXCEPTIONS_AVAILABLE, reason="Exceptions module not available")
@pytest.mark.unit
class TestCoreExceptions:
    """核心异常类测试"""

    def test_base_exception_creation(self):
        """测试基础异常创建"""
        error = FootballPredictionError("Base error message")
        assert str(error) == "Base error message"
        assert isinstance(error, Exception)
        assert isinstance(error, FootballPredictionError)

    @pytest.mark.parametrize(
        "exception_class,expected_message",
        [
            (ConfigError, "Configuration error"),
            (DataError, "Data processing error"),
            (ModelError, "Model error"),
            (PredictionError, "Prediction error"),
            (CacheError, "Cache error"),
            (DatabaseError, "Database error"),
            (ConsistencyError, "Consistency error"),
            (ValidationError, "Validation error"),
            (DataQualityError, "Data quality error"),
            (PipelineError, "Pipeline error"),
            (DomainError, "Domain error"),
            (BusinessRuleError, "Business rule error"),
            (ServiceLifecycleError, "Service lifecycle error"),
            (DependencyInjectionError, "Dependency injection error"),
            (LineageError, "Lineage error"),
            (TrackingError, "Tracking error"),
            (BacktestError, "Backtest error"),
            (DataProcessingError, "Data processing error"),
            (TaskExecutionError, "Task execution error"),
            (TaskRetryError, "Task retry error"),
            (AuthenticationError, "Authentication error"),
            (AuthorizationError, "Authorization error"),
            (RateLimitError, "Rate limit error"),
            (TimeoutError, "Timeout error"),
            (AdapterError, "Adapter error"),
            (StreamingError, "Streaming error"),
        ],
    )
    def test_specific_exception_creation(
        self, exception_class: Type[Exception], expected_message: str
    ):
        """测试具体异常类的创建"""
        error = exception_class(expected_message)
        assert str(error) == expected_message
        assert isinstance(error, Exception)
        assert isinstance(error, FootballPredictionError)

    def test_exception_inheritance_hierarchy(self):
        """测试异常继承层次结构"""
        # 测试直接继承自FootballPredictionError的异常
        direct_inheritance_exceptions = [
            ConfigError,
            ModelError,
            PredictionError,
            ServiceError,
            ValidationError,
            PipelineError,
            DomainError,
            ServiceLifecycleError,
            DependencyInjectionError,
            LineageError,
            TrackingError,
            BacktestError,
            TaskExecutionError,
            TaskRetryError,
            AuthenticationError,
            AuthorizationError,
            RateLimitError,
            TimeoutError,
            AdapterError,
            StreamingError,
        ]

        for exception_class in direct_inheritance_exceptions:
            error = exception_class("Test message")
            assert isinstance(error, FootballPredictionError)
            assert isinstance(error, Exception)

        # 测试继承自DataError的异常
        data_error_exceptions = [
            CacheError,
            DatabaseError,
            ConsistencyError,
            DataQualityError,
            DataProcessingError,
        ]

        for exception_class in data_error_exceptions:
            error = exception_class("Test message")
            assert isinstance(error, DataError)
            assert isinstance(error, FootballPredictionError)
            assert isinstance(error, Exception)

        # 测试继承自DomainError的异常
        domain_error_exceptions = [BusinessRuleError]

        for exception_class in domain_error_exceptions:
            error = exception_class("Test message")
            assert isinstance(error, DomainError)
            assert isinstance(error, FootballPredictionError)
            assert isinstance(error, Exception)

    def test_service_error_special_attributes(self):
        """测试ServiceError的特殊属性"""
        # 测试只有message的情况
        error1 = ServiceError("Service failed")
        assert error1.message == "Service failed"
        assert error1.service_name is None
        assert str(error1) == "Service failed"

        # 测试带service_name的情况
        error2 = ServiceError("Database connection failed", "UserService")
        assert error2.message == "Database connection failed"
        assert error2.service_name == "UserService"
        assert str(error2) == "Database connection failed"

    def test_exception_with_none_message(self):
        """测试None消息的异常"""
        # 大多数异常应该能处理None消息
        error = FootballPredictionError()
        assert str(error) == ""

        error_with_msg = ConfigError(None)
        assert str(error_with_msg) == "None"

    def test_exception_with_empty_message(self):
        """测试空消息的异常"""
        error = ConfigError("")
        assert str(error) == ""

    def test_exception_with_long_message(self):
        """测试长消息的异常"""
        long_message = (
            "This is a very long error message that might occur in production " * 10
        )
        error = PredictionError(long_message)
        assert str(error) == long_message

    def test_exception_chaining(self):
        """测试异常链"""
        try:
            try:
                raise ValueError("Original cause")
            except ValueError as e:
                raise DataError("Data processing failed") from e
        except DataError as e:
            assert e.__cause__ is not None
            assert isinstance(e.__cause__, ValueError)
            assert str(e.__cause__) == "Original cause"

    def test_exception_inheritance_verification(self):
        """验证异常继承关系"""
        # 验证所有异常都继承自FootballPredictionError
        all_exceptions = [
            ConfigError,
            DataError,
            ModelError,
            PredictionError,
            CacheError,
            ServiceError,
            DatabaseError,
            ConsistencyError,
            ValidationError,
            DataQualityError,
            PipelineError,
            DomainError,
            BusinessRuleError,
            ServiceLifecycleError,
            DependencyInjectionError,
            LineageError,
            TrackingError,
            BacktestError,
            DataProcessingError,
            TaskExecutionError,
            TaskRetryError,
            AuthenticationError,
            AuthorizationError,
            RateLimitError,
            TimeoutError,
            AdapterError,
            StreamingError,
        ]

        for exception_class in all_exceptions:
            assert issubclass(exception_class, FootballPredictionError)
            assert issubclass(exception_class, Exception)

    def test_multiple_inheritance_scenarios(self):
        """测试多重继承场景"""
        # 测试多层继承的异常
        cache_error = CacheError("Cache miss")
        assert isinstance(cache_error, CacheError)
        assert isinstance(cache_error, DataError)
        assert isinstance(cache_error, FootballPredictionError)
        assert isinstance(cache_error, Exception)

        business_error = BusinessRuleError("Invalid business rule")
        assert isinstance(business_error, BusinessRuleError)
        assert isinstance(business_error, DomainError)
        assert isinstance(business_error, FootballPredictionError)
        assert isinstance(business_error, Exception)

    def test_exception_performance_basic(self):
        """测试异常创建的基本性能"""
        import time

        start_time = time.time()
        for _ in range(1000):
            PredictionError("Performance test")
        end_time = time.time()

        # 创建1000个异常应该在合理时间内完成（小于1秒）
        assert end_time - start_time < 1.0

    def test_exception_equality(self):
        """测试异常相等性"""
        error1 = ConfigError("Config error")
        error2 = ConfigError("Config error")
        error3 = ConfigError("Different error")

        # 异常实例不应该相等（即使消息相同）
        assert error1 != error2
        assert error1 != error3
        assert error2 != error3

        # 但是类型应该相同
        assert type(error1) is type(error2)
        assert type(error1) is type(error3)

    def test_exception_hashability(self):
        """测试异常的可哈希性"""
        error = ConfigError("Config error")
        # 异常实例应该是可哈希的
        assert isinstance(hash(error), int)

    def test_exception_repr(self):
        """测试异常的repr表示"""
        error = ServiceError("Service unavailable", "AuthService")
        repr_str = repr(error)
        assert "ServiceError" in repr_str
        assert "Service unavailable" in repr_str

    def test_exception_with_special_characters(self):
        """测试包含特殊字符的异常消息"""
        special_messages = [
            "Error with unicode: 测试",
            "Error with emojis: ⚠️ ❌",
            "Error with newlines\nLine 2\nLine 3",
            "Error with tabs\tTabbed content",
            "Error with quotes: 'single' and \"double\"",
            "Error with backslashes: \\path\\to\\file",
        ]

        for message in special_messages:
            error = ValidationError(message)
            assert str(error) == message

    def test_domain_error_pass_statement(self):
        """测试DomainError和BusinessRuleError的pass语句"""
        # 这些异常类有pass语句，确保它们正常工作
        domain_error = DomainError("Domain logic error")
        business_error = BusinessRuleError("Business rule violation")

        assert str(domain_error) == "Domain logic error"
        assert str(business_error) == "Business rule violation"
        assert isinstance(domain_error, FootballPredictionError)
        assert isinstance(business_error, DomainError)

    @pytest.mark.parametrize(
        "exception_class",
        [
            ConfigError,
            DataError,
            ModelError,
            PredictionError,
            CacheError,
            ServiceError,
            DatabaseError,
            ConsistencyError,
            ValidationError,
            DataQualityError,
            PipelineError,
            DomainError,
            BusinessRuleError,
            ServiceLifecycleError,
            DependencyInjectionError,
            LineageError,
            TrackingError,
            BacktestError,
            DataProcessingError,
            TaskExecutionError,
            TaskRetryError,
            AuthenticationError,
            AuthorizationError,
            RateLimitError,
            TimeoutError,
            AdapterError,
            StreamingError,
        ],
    )
    def test_exception_catchability(self, exception_class: Type[Exception]):
        """测试所有异常的可捕获性"""
        error = exception_class("Test message")

        # 测试可以被特定异常类型捕获
        caught_specific = False
        try:
            raise error
        except exception_class:
            caught_specific = True

        assert caught_specific

        # 测试可以被基类异常捕获
        caught_base = False
        try:
            raise error
        except FootballPredictionError:
            caught_base = True

        assert caught_base

        # 测试可以被通用Exception捕获
        caught_general = False
        try:
            raise error
        except Exception:
            caught_general = True

        assert caught_general

    def test_error_inheritance(self):
        """测试异常继承关系（保留原有测试）"""
        assert issubclass(ConfigError, FootballPredictionError)
        assert issubclass(DataError, FootballPredictionError)
        assert issubclass(ModelError, FootballPredictionError)
        assert issubclass(PredictionError, FootballPredictionError)
        assert issubclass(CacheError, DataError)
        assert issubclass(CacheError, FootballPredictionError)
