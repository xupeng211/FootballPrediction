"""
增强的测试文件 - 目标覆盖率 95%
模块: core.exceptions
当前覆盖率: 90%
"""

import pytest
from unittest.mock import Mock, patch, AsyncMock, MagicMock
import asyncio
from datetime import datetime, timedelta

# 导入目标模块
from core.exceptions import *

class TestExceptions:
    """异常类测试"""

    def test_football_prediction_error(self):
        """测试基础异常"""
        error = FootballPredictionError("Test error")
        assert str(error) == "Test error"
        assert error.__class__.__name__ == "FootballPredictionError"

    def test_config_error(self):
        """测试配置异常"""
        error = ConfigError("Config error")
        assert str(error) == "Config error"

    def test_data_error(self):
        """测试数据异常"""
        error = DataError("Data error")
        assert str(error) == "Data error"

    def test_model_error(self):
        """测试模型异常"""
        error = ModelError("Model error")
        assert str(error) == "Model error"

    def test_prediction_error(self):
        """测试预测异常"""
        error = PredictionError("Prediction error")
        assert str(error) == "Prediction error"

    def test_cache_error(self):
        """测试缓存异常"""
        error = CacheError("Cache error")
        assert str(error) == "Cache error"

    def test_service_error(self):
        """测试服务异常"""
        error = ServiceError("Service error")
        assert str(error) == "Service error"

    def test_database_error(self):
        """测试数据库异常"""
        error = DatabaseError("Database error")
        assert str(error) == "Database error"

    def test_validation_error(self):
        """测试验证异常"""
        error = ValidationError("Validation error")
        assert str(error) == "Validation error"

    def test_dependency_injection_error(self):
        """测试依赖注入异常"""
        error = DependencyInjectionError("DI error")
        assert str(error) == "DI error"
