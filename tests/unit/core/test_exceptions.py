"""
核心异常测试
"""

import pytest

from src.core.exceptions import (
    ConfigurationError,
    DataValidationError,
    FootballPredictionException,
    ServiceUnavailableError,
)


class TestCoreExceptions:
    """核心异常测试类"""

    def test_football_prediction_exception(self):
        """测试足球预测异常"""
        # 测试基本异常创建
        exception = FootballPredictionException("Test message")
        assert str(exception) == "Test message"

        # 测试带参数的异常
        exception_with_code = FootballPredictionException("Error", code=500)
        assert str(exception_with_code) == "Error"

    def test_data_validation_exception(self):
        """测试数据验证异常"""
        # 测试基本验证异常
        exception = DataValidationError("Validation failed")
        assert str(exception) == "Validation failed"

        # 测试带字段信息的异常
        exception_with_fields = DataValidationError(
            "Invalid data", field="email", value="invalid-email"
        )
        assert str(exception_with_fields) == "Invalid data"

    def test_configuration_error(self):
        """测试配置错误异常"""
        exception = ConfigurationError("Missing configuration")
        assert str(exception) == "Missing configuration"

        # 测试带配置键的异常
        exception_with_key = ConfigurationError(
            "Missing required config", config_key="DATABASE_URL"
        )
        assert str(exception_with_key) == "Missing required config"

    def test_service_unavailable_error(self):
        """测试服务不可用异常"""
        exception = ServiceUnavailableError("Service down")
        assert str(exception) == "Service down"

        # 测试带服务名称的异常
        exception_with_service = ServiceUnavailableError(
            "Service unavailable", service_name="database"
        )
        assert str(exception_with_service) == "Service unavailable"

    def test_exception_inheritance(self):
        """测试异常继承关系"""
        # 测试异常继承
        assert issubclass(DataValidationError, FootballPredictionException)
        assert issubclass(ConfigurationError, FootballPredictionException)
        assert issubclass(ServiceUnavailableError, FootballPredictionException)

    def test_exception_attributes(self):
        """测试异常属性"""
        # 测试FootballPredictionException属性
        exc = FootballPredictionException("Test", code=400, details="More info")

        if hasattr(exc, "code"):
            assert exc.code == 400
        if hasattr(exc, "details"):
            assert exc.details == "More info"

    def test_exception_raising(self):
        """测试异常抛出"""
        # 测试异常可以正常抛出和捕获
        with pytest.raises(FootballPredictionException):
            raise FootballPredictionException("Test exception")

        with pytest.raises(DataValidationError):
            raise DataValidationError("Invalid data")

    def test_custom_exception_handling(self):
        """测试自定义异常处理"""
        try:
            raise DataValidationError("Custom error")
        except FootballPredictionException as e:
            assert isinstance(e, DataValidationError)
            assert str(e) == "Custom error"

    def test_exceptions_module_import(self):
        """测试异常模块导入"""
        import src.core.exceptions

        assert src.core.exceptions is not None

        # 检查关键异常类是否存在
        assert hasattr(src.core.exceptions, "FootballPredictionException")
        assert hasattr(src.core.exceptions, "DataValidationError")
        assert hasattr(src.core.exceptions, "ConfigurationError")
        assert hasattr(src.core.exceptions, "ServiceUnavailableError")
