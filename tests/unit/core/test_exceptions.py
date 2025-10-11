"""
测试核心异常模块
"""

import pytest
from src.core.exceptions import (
    FootballPredictionError,
    ConfigError,
    DataError,
    ModelError,
    PredictionError,
    CacheError,
)


def test_football_prediction_error():
    """测试基础异常类"""
    error = FootballPredictionError("Test error")
    assert str(error) == "Test error"


def test_config_error():
    """测试配置错误"""
    error = ConfigError("Invalid configuration")
    assert str(error) == "Invalid configuration"
    assert isinstance(error, FootballPredictionError)


def test_data_error():
    """测试数据错误"""
    error = DataError("Data processing failed")
    assert str(error) == "Data processing failed"
    assert isinstance(error, FootballPredictionError)


def test_model_error():
    """测试模型错误"""
    error = ModelError("Model loading failed")
    assert str(error) == "Model loading failed"
    assert isinstance(error, FootballPredictionError)


def test_prediction_error():
    """测试预测错误"""
    error = PredictionError("Prediction computation failed")
    assert str(error) == "Prediction computation failed"
    assert isinstance(error, FootballPredictionError)


def test_cache_error():
    """测试缓存错误"""
    error = CacheError("Cache connection failed")
    assert str(error) == "Cache connection failed"
    assert isinstance(error, DataError)


def test_error_inheritance():
    """测试异常继承关系"""
    assert issubclass(ConfigError, FootballPredictionError)
    assert issubclass(DataError, FootballPredictionError)
    assert issubclass(ModelError, FootballPredictionError)
    assert issubclass(PredictionError, FootballPredictionError)
    assert issubclass(CacheError, DataError)
    assert issubclass(CacheError, FootballPredictionError)
