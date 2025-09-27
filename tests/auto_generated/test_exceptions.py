"""
Auto-generated tests for src.core.exceptions module
"""

import pytest
from src.core.exceptions import (
    FootballPredictionError,
    ConfigError,
    DataError,
    ModelError,
    PredictionError,
    CacheError,
    DatabaseError,
    ConsistencyError,
    ValidationError,
    DataQualityError,
    PipelineError,
    LineageError,
    TrackingError,
    BacktestError,
    DataProcessingError,
    TaskExecutionError,
    TaskRetryError
)


class TestFootballPredictionError:
    """测试基础异常类"""

    def test_base_exception_creation(self):
        """测试基础异常创建"""
        exc = FootballPredictionError("Test message")
        assert str(exc) == "Test message"
        assert isinstance(exc, Exception)
        assert isinstance(exc, FootballPredictionError)

    def test_base_exception_inheritance(self):
        """测试基础异常继承"""
        exc = FootballPredictionError("Test")
        assert issubclass(FootballPredictionError, Exception)
        assert isinstance(exc, Exception)

    def test_base_exception_without_message(self):
        """测试无消息的基础异常"""
        exc = FootballPredictionError()
        assert isinstance(exc, FootballPredictionError)

    def test_base_exception_with_args(self):
        """测试带参数的基础异常"""
        exc = FootballPredictionError("Message", 123, {"key": "value"})
        assert exc.args[0] == "Message"
        assert exc.args[1] == 123
        assert exc.args[2] == {"key": "value"}


class TestConfigError:
    """测试配置异常"""

    def test_config_error_creation(self):
        """测试配置异常创建"""
        exc = ConfigError("Configuration failed")
        assert str(exc) == "Configuration failed"
        assert isinstance(exc, ConfigError)
        assert isinstance(exc, FootballPredictionError)

    def test_config_error_inheritance(self):
        """测试配置异常继承"""
        assert issubclass(ConfigError, FootballPredictionError)
        exc = ConfigError("Test")
        assert isinstance(exc, FootballPredictionError)

    @pytest.mark.parametrize("message", [
        "Database connection failed",
        "Missing required configuration",
        "Invalid configuration value",
        "Configuration file not found",
    ])
    def test_config_error_messages(self, message):
        """测试配置异常消息"""
        exc = ConfigError(message)
        assert str(exc) == message


class TestDataError:
    """测试数据异常"""

    def test_data_error_creation(self):
        """测试数据异常创建"""
        exc = DataError("Data processing failed")
        assert str(exc) == "Data processing failed"
        assert isinstance(exc, DataError)
        assert isinstance(exc, FootballPredictionError)

    def test_data_error_inheritance(self):
        """测试数据异常继承"""
        assert issubclass(DataError, FootballPredictionError)
        exc = DataError("Test")
        assert isinstance(exc, FootballPredictionError)


class TestModelError:
    """测试模型异常"""

    def test_model_error_creation(self):
        """测试模型异常创建"""
        exc = ModelError("Model training failed")
        assert str(exc) == "Model training failed"
        assert isinstance(exc, ModelError)
        assert isinstance(exc, FootballPredictionError)

    def test_model_error_inheritance(self):
        """测试模型异常继承"""
        assert issubclass(ModelError, FootballPredictionError)
        exc = ModelError("Test")
        assert isinstance(exc, FootballPredictionError)


class TestPredictionError:
    """测试预测异常"""

    def test_prediction_error_creation(self):
        """测试预测异常创建"""
        exc = PredictionError("Prediction generation failed")
        assert str(exc) == "Prediction generation failed"
        assert isinstance(exc, PredictionError)
        assert isinstance(exc, FootballPredictionError)

    def test_prediction_error_inheritance(self):
        """测试预测异常继承"""
        assert issubclass(PredictionError, FootballPredictionError)
        exc = PredictionError("Test")
        assert isinstance(exc, FootballPredictionError)


class TestCacheError:
    """测试缓存异常"""

    def test_cache_error_creation(self):
        """测试缓存异常创建"""
        exc = CacheError("Cache operation failed")
        assert str(exc) == "Cache operation failed"
        assert isinstance(exc, CacheError)
        assert isinstance(exc, DataError)
        assert isinstance(exc, FootballPredictionError)

    def test_cache_error_inheritance_chain(self):
        """测试缓存异常继承链"""
        assert issubclass(CacheError, DataError)
        assert issubclass(CacheError, FootballPredictionError)
        exc = CacheError("Test")
        assert isinstance(exc, DataError)
        assert isinstance(exc, FootballPredictionError)


class TestDatabaseError:
    """测试数据库异常"""

    def test_database_error_creation(self):
        """测试数据库异常创建"""
        exc = DatabaseError("Database operation failed")
        assert str(exc) == "Database operation failed"
        assert isinstance(exc, DatabaseError)
        assert isinstance(exc, DataError)
        assert isinstance(exc, FootballPredictionError)

    def test_database_error_inheritance_chain(self):
        """测试数据库异常继承链"""
        assert issubclass(DatabaseError, DataError)
        assert issubclass(DatabaseError, FootballPredictionError)
        exc = DatabaseError("Test")
        assert isinstance(exc, DataError)
        assert isinstance(exc, FootballPredictionError)


class TestConsistencyError:
    """测试一致性异常"""

    def test_consistency_error_creation(self):
        """测试一致性异常创建"""
        exc = ConsistencyError("Data consistency check failed")
        assert str(exc) == "Data consistency check failed"
        assert isinstance(exc, ConsistencyError)
        assert isinstance(exc, DataError)
        assert isinstance(exc, FootballPredictionError)

    def test_consistency_error_inheritance_chain(self):
        """测试一致性异常继承链"""
        assert issubclass(ConsistencyError, DataError)
        assert issubclass(ConsistencyError, FootballPredictionError)
        exc = ConsistencyError("Test")
        assert isinstance(exc, DataError)
        assert isinstance(exc, FootballPredictionError)


class TestValidationError:
    """测试验证异常"""

    def test_validation_error_creation(self):
        """测试验证异常创建"""
        exc = ValidationError("Validation failed")
        assert str(exc) == "Validation failed"
        assert isinstance(exc, ValidationError)
        assert isinstance(exc, FootballPredictionError)

    def test_validation_error_inheritance(self):
        """测试验证异常继承"""
        assert issubclass(ValidationError, FootballPredictionError)
        exc = ValidationError("Test")
        assert isinstance(exc, FootballPredictionError)


class TestDataQualityError:
    """测试数据质量异常"""

    def test_data_quality_error_creation(self):
        """测试数据质量异常创建"""
        exc = DataQualityError("Data quality check failed")
        assert str(exc) == "Data quality check failed"
        assert isinstance(exc, DataQualityError)
        assert isinstance(exc, DataError)
        assert isinstance(exc, FootballPredictionError)

    def test_data_quality_error_inheritance_chain(self):
        """测试数据质量异常继承链"""
        assert issubclass(DataQualityError, DataError)
        assert issubclass(DataQualityError, FootballPredictionError)
        exc = DataQualityError("Test")
        assert isinstance(exc, DataError)
        assert isinstance(exc, FootballPredictionError)


class TestPipelineError:
    """测试管道异常"""

    def test_pipeline_error_creation(self):
        """测试管道异常创建"""
        exc = PipelineError("Pipeline execution failed")
        assert str(exc) == "Pipeline execution failed"
        assert isinstance(exc, PipelineError)
        assert isinstance(exc, FootballPredictionError)

    def test_pipeline_error_inheritance(self):
        """测试管道异常继承"""
        assert issubclass(PipelineError, FootballPredictionError)
        exc = PipelineError("Test")
        assert isinstance(exc, FootballPredictionError)


class TestLineageError:
    """测试血缘异常"""

    def test_lineage_error_creation(self):
        """测试血缘异常创建"""
        exc = LineageError("Lineage tracking failed")
        assert str(exc) == "Lineage tracking failed"
        assert isinstance(exc, LineageError)
        assert isinstance(exc, FootballPredictionError)

    def test_lineage_error_inheritance(self):
        """测试血缘异常继承"""
        assert issubclass(LineageError, FootballPredictionError)
        exc = LineageError("Test")
        assert isinstance(exc, FootballPredictionError)


class TestTrackingError:
    """测试追踪异常"""

    def test_tracking_error_creation(self):
        """测试追踪异常创建"""
        exc = TrackingError("Tracking operation failed")
        assert str(exc) == "Tracking operation failed"
        assert isinstance(exc, TrackingError)
        assert isinstance(exc, FootballPredictionError)

    def test_tracking_error_inheritance(self):
        """测试追踪异常继承"""
        assert issubclass(TrackingError, FootballPredictionError)
        exc = TrackingError("Test")
        assert isinstance(exc, FootballPredictionError)


class TestBacktestError:
    """测试回测异常"""

    def test_backtest_error_creation(self):
        """测试回测异常创建"""
        exc = BacktestError("Backtest execution failed")
        assert str(exc) == "Backtest execution failed"
        assert isinstance(exc, BacktestError)
        assert isinstance(exc, FootballPredictionError)

    def test_backtest_error_inheritance(self):
        """测试回测异常继承"""
        assert issubclass(BacktestError, FootballPredictionError)
        exc = BacktestError("Test")
        assert isinstance(exc, FootballPredictionError)


class TestDataProcessingError:
    """测试数据处理异常"""

    def test_data_processing_error_creation(self):
        """测试数据处理异常创建"""
        exc = DataProcessingError("Data processing failed")
        assert str(exc) == "Data processing failed"
        assert isinstance(exc, DataProcessingError)
        assert isinstance(exc, DataError)
        assert isinstance(exc, FootballPredictionError)

    def test_data_processing_error_inheritance_chain(self):
        """测试数据处理异常继承链"""
        assert issubclass(DataProcessingError, DataError)
        assert issubclass(DataProcessingError, FootballPredictionError)
        exc = DataProcessingError("Test")
        assert isinstance(exc, DataError)
        assert isinstance(exc, FootballPredictionError)


class TestTaskExecutionError:
    """测试任务执行异常"""

    def test_task_execution_error_creation(self):
        """测试任务执行异常创建"""
        exc = TaskExecutionError("Task execution failed")
        assert str(exc) == "Task execution failed"
        assert isinstance(exc, TaskExecutionError)
        assert isinstance(exc, FootballPredictionError)

    def test_task_execution_error_inheritance(self):
        """测试任务执行异常继承"""
        assert issubclass(TaskExecutionError, FootballPredictionError)
        exc = TaskExecutionError("Test")
        assert isinstance(exc, FootballPredictionError)


class TestTaskRetryError:
    """测试任务重试异常"""

    def test_task_retry_error_creation(self):
        """测试任务重试异常创建"""
        exc = TaskRetryError("Task retry failed")
        assert str(exc) == "Task retry failed"
        assert isinstance(exc, TaskRetryError)
        assert isinstance(exc, FootballPredictionError)

    def test_task_retry_error_inheritance(self):
        """测试任务重试异常继承"""
        assert issubclass(TaskRetryError, FootballPredictionError)
        exc = TaskRetryError("Test")
        assert isinstance(exc, FootballPredictionError)


class TestExceptionHierarchy:
    """测试异常层次结构"""

    def test_complete_inheritance_chain(self):
        """测试完整继承链"""
        # 测试所有异常都是FootballPredictionError的子类
        exceptions = [
            ConfigError, DataError, ModelError, PredictionError,
            CacheError, DatabaseError, ConsistencyError, ValidationError,
            DataQualityError, PipelineError, LineageError, TrackingError,
            BacktestError, DataProcessingError, TaskExecutionError, TaskRetryError
        ]

        for exc_class in exceptions:
            assert issubclass(exc_class, FootballPredictionError)

        # 测试DataError的子类
        data_error_subclasses = [
            CacheError, DatabaseError, ConsistencyError,
            DataQualityError, DataProcessingError
        ]

        for exc_class in data_error_subclasses:
            assert issubclass(exc_class, DataError)

    def test_exception_catching(self):
        """测试异常捕获"""
        # 测试基类可以捕获所有子类异常
        try:
            raise ConfigError("Config error")
        except FootballPredictionError:
            pass  # 应该被捕获
        else:
            pytest.fail("FootballPredictionError should catch ConfigError")

        # 测试DataError可以捕获其子类
        try:
            raise DatabaseError("Database error")
        except DataError:
            pass  # 应该被捕获
        else:
            pytest.fail("DataError should catch DatabaseError")

    def test_exception_specificity(self):
        """测试异常特异性"""
        # 测试特定异常不会被更通用的异常错误捕获
        with pytest.raises(ConfigError):
            raise ConfigError("Config error")

        with pytest.raises(DataError):
            raise DatabaseError("Database error")

        # 确保异常类型检查正确工作
        assert ConfigError != DataError
        assert issubclass(DatabaseError, DataError)
        assert not issubclass(ConfigError, DataError)

    def test_exception_with_context(self):
        """测试带上下文的异常"""
        try:
            try:
                raise ValueError("Original error")
            except ValueError as e:
                raise ConfigError("Configuration failed") from e
        except ConfigError as exc:
            assert str(exc) == "Configuration failed"
            assert exc.__cause__ is not None
            assert isinstance(exc.__cause__, ValueError)

    def test_exception_raising_patterns(self):
        """测试异常抛出模式"""
        # 测试直接抛出
        with pytest.raises(FootballPredictionError):
            raise FootballPredictionError("Direct raise")

        # 测试条件抛出
        condition = False
        if not condition:
            with pytest.raises(FootballPredictionError):
                raise FootballPredictionError("Conditional raise")

        # 测试重新抛出
        try:
            raise ConfigError("Original")
        except ConfigError:
            with pytest.raises(ConfigError):
                raise  # 重新抛出

    def test_exception_creation_with_various_args(self):
        """测试使用各种参数创建异常"""
        # 无参数
        exc1 = FootballPredictionError()
        assert isinstance(exc1, FootballPredictionError)

        # 单个字符串参数
        exc2 = FootballPredictionError("Error message")
        assert str(exc2) == "Error message"

        # 多个参数
        exc3 = FootballPredictionError("Error", 123, {"key": "value"})
        assert exc3.args[0] == "Error"
        assert exc3.args[1] == 123
        assert exc3.args[2] == {"key": "value"}

        # 关键字参数
        exc4 = FootballPredictionError("Error with kwargs", code=500)
        assert exc4.args[0] == "Error with kwargs"

    def test_exception_equality(self):
        """测试异常相等性"""
        exc1 = ConfigError("Same message")
        exc2 = ConfigError("Same message")
        exc3 = ConfigError("Different message")

        # 异常实例通常不相等，即使消息相同
        assert exc1 != exc2
        assert exc1 != exc3
        assert exc2 != exc3

        # 但类型相同
        assert type(exc1) == type(exc2)
        assert type(exc1) == type(exc3)