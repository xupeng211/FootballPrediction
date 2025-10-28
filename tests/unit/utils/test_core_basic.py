"""
核心模块基础测试
"""

import pytest

from src.core.exceptions import (
    AdapterError,
    CacheError,
    ConfigError,
    DatabaseError,
    DataError,
    FootballPredictionError,
    ModelError,
    PredictionError,
    StreamingError,
    ValidationError,
)


@pytest.mark.unit
class TestExceptions:
    """异常类测试"""

    def test_base_exception(self):
        """测试基础异常"""
        error = FootballPredictionError("Test error")
        assert str(error) == "Test error"
        assert isinstance(error, Exception)

    def test_config_error(self):
        """测试配置错误"""
        error = ConfigError("Missing config")
        assert str(error) == "Missing config"
        assert isinstance(error, FootballPredictionError)

    def test_data_error(self):
        """测试数据错误"""
        error = DataError("Invalid data")
        assert str(error) == "Invalid data"
        assert isinstance(error, FootballPredictionError)

    def test_model_error(self):
        """测试模型错误"""
        error = ModelError("Model not found")
        assert str(error) == "Model not found"
        assert isinstance(error, FootballPredictionError)

    def test_prediction_error(self):
        """测试预测错误"""
        error = PredictionError("Prediction failed")
        assert str(error) == "Prediction failed"
        assert isinstance(error, FootballPredictionError)

    def test_cache_error(self):
        """测试缓存错误"""
        error = CacheError("Cache miss")
        assert str(error) == "Cache miss"
        assert isinstance(error, DataError)

    def test_database_error(self):
        """测试数据库错误"""
        error = DatabaseError("Connection failed")
        assert str(error) == "Connection failed"
        assert isinstance(error, DataError)

    def test_validation_error(self):
        """测试验证错误"""
        error = ValidationError("Invalid input")
        assert str(error) == "Invalid input"
        assert isinstance(error, FootballPredictionError)

    def test_streaming_error(self):
        """测试流处理错误"""
        error = StreamingError("Stream error")
        assert str(error) == "Stream error"
        assert isinstance(error, FootballPredictionError)

    def test_adapter_error(self):
        """测试适配器错误"""
        error = AdapterError("Adapter not found")
        assert str(error) == "Adapter not found"
        assert isinstance(error, FootballPredictionError)

    def test_exception_with_context(self):
        """测试带上下文的异常"""
        context = {"field": "email", "value": "invalid"}
        error = ValidationError("Invalid email format", context=context)
        assert str(error) == "Invalid email format"
        assert error.context == context

    def test_exception_chaining(self):
        """测试异常链"""
        try:
            try:
                raise ValueError("Original error")
            except ValueError as e:
                raise DataError("Data processing failed") from e
        except DataError as e:
            assert str(e) == "Data processing failed"
            assert e.__cause__ is not None
            assert str(e.__cause__) == "Original error"
