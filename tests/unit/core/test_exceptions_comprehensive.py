"""
核心异常模块综合测试
Comprehensive Tests for Core Exceptions

测试src.core.exceptions模块的所有异常类
"""

import pytest
from src.core.exceptions import (
    # 基础异常
    FootballPredictionError,

    # 配置和数据异常
    ConfigError,
    DataError,
    ModelError,
    PredictionError,

    # 数据相关异常（继承自DataError）
    CacheError,
    DatabaseError,
    ConsistencyError,
    ValidationError,
    DataQualityError,
    DataProcessingError,

    # 领域层异常
    DomainError,
    BusinessRuleError,

    # 系统异常
    PipelineError,
    ServiceLifecycleError,
    DependencyInjectionError,

    # 追踪异常
    LineageError,
    TrackingError,

    # 任务异常
    BacktestError,
    TaskExecutionError,
    TaskRetryError,

    # 安全异常
    AuthenticationError,
    AuthorizationError,
    RateLimitError,
    TimeoutError,

    # 架构异常
    AdapterError,
    StreamingError,
)


class TestFootballPredictionError:
    """基础异常类测试"""

    def test_basic_error_creation(self):
        """测试：创建基础异常"""
        error = FootballPredictionError("Test error")
        assert str(error) == "Test error"
        assert isinstance(error, Exception)

    def test_error_with_empty_message(self):
        """测试：空消息异常"""
        error = FootballPredictionError("")
        assert str(error) == ""

    def test_error_with_none_message(self):
        """测试：None消息异常"""
        error = FootballPredictionError(None)
        assert str(error) == "None"

    def test_error_with_long_message(self):
        """测试：长消息异常"""
        message = "A" * 1000
        error = FootballPredictionError(message)
        assert str(error) == message

    def test_error_repr(self):
        """测试：异常的repr表示"""
        error = FootballPredictionError("Test")
        assert repr(error).startswith("FootballPredictionError('Test')")

    def test_error_inheritance_chain(self):
        """测试：异常继承链"""
        assert issubclass(FootballPredictionError, Exception)
        assert FootballPredictionError.__mro__[0] == FootballPredictionError
        assert FootballPredictionError.__mro__[1] == Exception


class TestConfigError:
    """配置异常测试"""

    def test_config_error_creation(self):
        """测试：创建配置异常"""
        error = ConfigError("Invalid configuration")
        assert str(error) == "Invalid configuration"
        assert isinstance(error, FootballPredictionError)

    def test_config_error_inheritance(self):
        """测试：配置异常继承"""
        assert issubclass(ConfigError, FootballPredictionError)

    def test_config_error_with_details(self):
        """测试：带详细信息的配置异常"""
        error = ConfigError("Missing required field: 'database_url'")
        assert "database_url" in str(error)


class TestDataError:
    """数据异常测试"""

    def test_data_error_creation(self):
        """测试：创建数据异常"""
        error = DataError("Data processing failed")
        assert str(error) == "Data processing failed"
        assert isinstance(error, FootballPredictionError)

    def test_data_error_subclasses(self):
        """测试：数据异常子类"""
        # 直接继承自DataError的子类
        data_error_subclasses = [
            CacheError,
            DatabaseError,
            ConsistencyError,
            DataQualityError,
            DataProcessingError,
        ]

        for subclass in data_error_subclasses:
            assert issubclass(subclass, DataError)
            assert issubclass(subclass, FootballPredictionError)

        # ValidationError直接继承自FootballPredictionError
        assert issubclass(ValidationError, FootballPredictionError)
        assert not issubclass(ValidationError, DataError)

    def test_cache_error(self):
        """测试：缓存异常"""
        error = CacheError("Cache connection failed")
        assert str(error) == "Cache connection failed"
        assert isinstance(error, DataError)

    def test_database_error(self):
        """测试：数据库异常"""
        error = DatabaseError("Connection timeout")
        assert str(error) == "Connection timeout"
        assert isinstance(error, DataError)

    def test_consistency_error(self):
        """测试：一致性异常"""
        error = ConsistencyError("Data consistency check failed")
        assert str(error) == "Data consistency check failed"
        assert isinstance(error, DataError)

    def test_validation_error(self):
        """测试：验证异常"""
        error = ValidationError("Invalid email format")
        assert str(error) == "Invalid email format"
        assert isinstance(error, FootballPredictionError)

    def test_data_quality_error(self):
        """测试：数据质量异常"""
        error = DataQualityError("Missing values detected")
        assert str(error) == "Missing values detected"
        assert isinstance(error, DataError)

    def test_data_processing_error(self):
        """测试：数据处理异常"""
        error = DataProcessingError("Failed to parse CSV")
        assert str(error) == "Failed to parse CSV"
        assert isinstance(error, DataError)


class TestDomainErrors:
    """领域层异常测试"""

    def test_domain_error(self):
        """测试：领域异常"""
        error = DomainError("Domain rule violation")
        assert str(error) == "Domain rule violation"
        assert isinstance(error, FootballPredictionError)

    def test_business_rule_error(self):
        """测试：业务规则异常"""
        error = BusinessRuleError("Business rule not satisfied")
        assert str(error) == "Business rule not satisfied"
        assert isinstance(error, DomainError)
        assert isinstance(error, FootballPredictionError)

    def test_model_error(self):
        """测试：模型异常"""
        error = ModelError("Model loading failed")
        assert str(error) == "Model loading failed"
        assert isinstance(error, FootballPredictionError)

    def test_prediction_error(self):
        """测试：预测异常"""
        error = PredictionError("Prediction computation failed")
        assert str(error) == "Prediction computation failed"
        assert isinstance(error, FootballPredictionError)


class TestSystemErrors:
    """系统异常测试"""

    def test_pipeline_error(self):
        """测试：管道异常"""
        error = PipelineError("Pipeline stage failed")
        assert str(error) == "Pipeline stage failed"
        assert isinstance(error, FootballPredictionError)

    def test_service_lifecycle_error(self):
        """测试：服务生命周期异常"""
        error = ServiceLifecycleError("Service startup failed")
        assert str(error) == "Service startup failed"
        assert isinstance(error, FootballPredictionError)

    def test_dependency_injection_error(self):
        """测试：依赖注入异常"""
        error = DependencyInjectionError("Circular dependency detected")
        assert str(error) == "Circular dependency detected"
        assert isinstance(error, FootballPredictionError)


class TestTrackingErrors:
    """追踪异常测试"""

    def test_lineage_error(self):
        """测试：数据血缘异常"""
        error = LineageError("Cannot trace data lineage")
        assert str(error) == "Cannot trace data lineage"
        assert isinstance(error, FootballPredictionError)

    def test_tracking_error(self):
        """测试：追踪异常"""
        error = TrackingError("Tracking ID not found")
        assert str(error) == "Tracking ID not found"
        assert isinstance(error, FootballPredictionError)


class TestTaskErrors:
    """任务异常测试"""

    def test_backtest_error(self):
        """测试：回测异常"""
        error = BacktestError("Backtest configuration invalid")
        assert str(error) == "Backtest configuration invalid"
        assert isinstance(error, FootballPredictionError)

    def test_task_execution_error(self):
        """测试：任务执行异常"""
        error = TaskExecutionError("Task execution timed out")
        assert str(error) == "Task execution timed out"
        assert isinstance(error, FootballPredictionError)

    def test_task_retry_error(self):
        """测试：任务重试异常"""
        error = TaskRetryError("Max retry attempts exceeded")
        assert str(error) == "Max retry attempts exceeded"
        assert isinstance(error, FootballPredictionError)


class TestSecurityErrors:
    """安全异常测试"""

    def test_authentication_error(self):
        """测试：认证异常"""
        error = AuthenticationError("Invalid credentials")
        assert str(error) == "Invalid credentials"
        assert isinstance(error, FootballPredictionError)

    def test_authorization_error(self):
        """测试：授权异常"""
        error = AuthorizationError("Access denied")
        assert str(error) == "Access denied"
        assert isinstance(error, FootballPredictionError)

    def test_rate_limit_error(self):
        """测试：限流异常"""
        error = RateLimitError("Rate limit exceeded")
        assert str(error) == "Rate limit exceeded"
        assert isinstance(error, FootballPredictionError)

    def test_timeout_error(self):
        """测试：超时异常"""
        error = TimeoutError("Operation timed out")
        assert str(error) == "Operation timed out"
        assert isinstance(error, FootballPredictionError)


class TestArchitectureErrors:
    """架构异常测试"""

    def test_adapter_error(self):
        """测试：适配器异常"""
        error = AdapterError("Adapter not found")
        assert str(error) == "Adapter not found"
        assert isinstance(error, FootballPredictionError)

    def test_streaming_error(self):
        """测试：流式处理异常"""
        error = StreamingError("Stream connection lost")
        assert str(error) == "Stream connection lost"
        assert isinstance(error, FootballPredictionError)


class TestExceptionChaining:
    """异常链测试"""

    def test_exception_with_cause(self):
        """测试：带原因的异常"""
        try:
            try:
                raise ValueError("Original error")
            except ValueError as e:
                raise DataError("Data processing failed") from e
        except DataError as data_error:
            assert str(data_error) == "Data processing failed"
            assert data_error.__cause__ is not None
            assert isinstance(data_error.__cause__, ValueError)

    def test_exception_context(self):
        """测试：异常上下文"""
        try:
            try:
                raise ValueError("Original error")
            except ValueError:
                raise DataError("Data processing failed")
        except DataError as data_error:
            assert str(data_error) == "Data processing failed"
            # Note: __context__ is automatically set when exception is raised

    def test_multiple_exception_levels(self):
        """测试：多级异常"""
        try:
            try:
                try:
                    raise ConnectionError("Database connection failed")
                except ConnectionError as e:
                    raise DatabaseError("Query failed") from e
            except DatabaseError as e:
                raise PipelineError("ETL pipeline failed") from e
        except PipelineError as pipeline_error:
            assert str(pipeline_error) == "ETL pipeline failed"
            assert pipeline_error.__cause__.__cause__ is not None
            assert isinstance(pipeline_error.__cause__.__cause__, ConnectionError)


class TestExceptionEdgeCases:
    """异常边界情况测试"""

    def test_exception_with_unicode_message(self):
        """测试：Unicode消息异常"""
        message = "错误信息：测试中文字符"
        error = FootballPredictionError(message)
        assert str(error) == message

    def test_exception_with_special_characters(self):
        """测试：特殊字符消息异常"""
        message = "Error: \n\t\r\"'\\"
        error = FootballPredictionError(message)
        assert str(error) == message

    def test_exception_pickling(self):
        """测试：异常序列化"""
        import pickle

        error = ConfigError("Test config error")
        pickled = pickle.dumps(error)
        unpickled = pickle.loads(pickled)

        assert isinstance(unpickled, ConfigError)
        assert str(unpickled) == "Test config error"

    def test_exception_with_args(self):
        """测试：带多个参数的异常"""
        # Note: Python exceptions can take multiple args
        error = FootballPredictionError("Error 1", "Error 2")
        assert str(error) == "('Error 1', 'Error 2')"

    def test_exception_dict_usage(self):
        """测试：异常在字典中的使用"""
        errors = {
            "config": ConfigError("Config missing"),
            "data": DataError("Data corrupted"),
            "model": ModelError("Model not loaded"),
        }

        assert isinstance(errors["config"], ConfigError)
        assert isinstance(errors["data"], DataError)
        assert isinstance(errors["model"], ModelError)

    def test_exception_in_list_comprehension(self):
        """测试：列表推导中的异常"""
        try:
            errors = [ConfigError(f"Error {i}") for i in range(3)]
            assert len(errors) == 3
            assert all(isinstance(e, ConfigError) for e in errors)
        except Exception as e:
            pytest.fail(f"List comprehension failed: {e}")


class TestExceptionBestPractices:
    """异常最佳实践测试"""

    def test_specific_exception_handling(self):
        """测试：具体异常处理"""
        try:
            raise ValidationError("Invalid input")
        except ValidationError:
            # Handle specific validation error
            caught = True
        except FootballPredictionError:
            # Handle other prediction errors
            caught = False

        assert caught is True

    def test_exception_hierarchy_respect(self):
        """测试：异常层次结构尊重"""
        # CacheError should be caught by DataError handler
        try:
            raise CacheError("Cache miss")
        except DataError:
            caught = True
        except Exception:
            caught = False

        assert caught is True

    def test_exception_message_formatting(self):
        """测试：异常消息格式化"""
        field = "email"
        value = "invalid-email"
        error = ValidationError(f"Field '{field}' has invalid value: {value}")

        assert field in str(error)
        assert value in str(error)
        assert str(error) == "Field 'email' has invalid value: invalid-email"

    def test_exception_with_context_info(self):
        """测试：带上下文信息的异常"""
        context = {
            "user_id": 123,
            "action": "predict",
            "timestamp": "2023-01-01T12:00:00Z"
        }

        error = PredictionError(
            f"Prediction failed for user {context['user_id']} "
            f"during {context['action']}"
        )

        assert "user 123" in str(error)
        assert "during predict" in str(error)