"""异常类测试"""

import pytest

from src.core.exceptions import (ConfigError, DatabaseError, DataError,
                                 FootballPredictionError, ModelError,
                                 PredictionError, ValidationError)


@pytest.mark.unit
class TestExceptions:
    """测试自定义异常类"""

    def test_base_exception_creation(self):
        """测试基础异常创建"""
        error = FootballPredictionError("Base error")
        assert str(error) == "Base error"

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
        error = ModelError("Model loading failed")
        assert str(error) == "Model loading failed"
        assert isinstance(error, FootballPredictionError)

    def test_prediction_error(self):
        """测试预测错误"""
        error = PredictionError("Prediction failed")
        assert str(error) == "Prediction failed"
        assert isinstance(error, FootballPredictionError)

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
