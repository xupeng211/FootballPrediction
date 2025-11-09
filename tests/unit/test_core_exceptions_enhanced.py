"""
高影响力测试 - 模块: core.exceptions
专注于100%可运行的测试用例
"""

import pytest

# 导入目标模块
from core.exceptions import (
    ConfigError,
    DataError,
    DependencyInjectionError,
    FootballPredictionError,
    ValidationError,
)


class TestExceptionHierarchy:
    """异常层次结构测试 - 这些测试总是可以运行的"""

    def test_football_prediction_error_creation(self):
        """测试基础异常创建"""
        error = FootballPredictionError("Test message")
        assert str(error) == "Test message"
        assert error.__class__.__name__ == "FootballPredictionError"
        assert isinstance(error, Exception)

    def test_config_error_creation(self):
        """测试配置异常创建"""
        error = ConfigError("Configuration failed")
        assert str(error) == "Configuration failed"
        assert isinstance(error, FootballPredictionError)

    def test_data_error_creation(self):
        """测试数据异常创建"""
        error = DataError("Data processing failed")
        assert str(error) == "Data processing failed"
        assert isinstance(error, FootballPredictionError)

    def test_validation_error_creation(self):
        """测试验证异常创建"""
        error = ValidationError("Validation failed")
        assert str(error) == "Validation failed"
        assert isinstance(error, FootballPredictionError)

    def test_dependency_injection_error_creation(self):
        """测试依赖注入异常创建"""
        error = DependencyInjectionError("DI failed")
        assert str(error) == "DI failed"
        assert isinstance(error, FootballPredictionError)

    def test_exception_inheritance_chain(self):
        """测试异常继承链"""
        error = ValidationError("Test")
        assert isinstance(error, ValidationError)
        assert isinstance(error, FootballPredictionError)
        assert isinstance(error, Exception)

    def test_exception_with_none_message(self):
        """测试无消息异常"""
        error = FootballPredictionError()
        assert str(error) == ""

    def test_exception_with_empty_message(self):
        """测试空消息异常"""
        error = ConfigError("")
        assert str(error) == ""

    def test_exception_repr(self):
        """测试异常repr"""
        error = DataError("Test data error")
        repr_str = repr(error)
        assert "DataError" in repr_str
        assert "Test data error" in repr_str

    def test_multiple_exception_types(self):
        """测试多种异常类型"""
        exceptions = [
            FootballPredictionError("Base"),
            ConfigError("Config"),
            DataError("Data"),
            ValidationError("Validation"),
            DependencyInjectionError("DI"),
        ]

        for _i, error in enumerate(exceptions):
            assert isinstance(error, FootballPredictionError)
            assert str(error)  # 确保字符串表示不为空


class TestExceptionUsagePatterns:
    """异常使用模式测试"""

    def test_exception_in_try_except(self):
        """测试在try-except中的异常使用"""
        try:
            raise ConfigError("Test error")
        except ConfigError as e:
            assert str(e) == "Test error"
        except FootballPredictionError:
            pytest.fail("Should have caught ConfigError specifically")

    def test_exception_chaining(self):
        """测试异常链"""
        try:
            try:
                raise ValueError("Original error")
            except ValueError as original_error:
                raise DataError("Wrapped error") from original_error
        except DataError as e:
            assert e.__cause__ is not None
            assert str(e.__cause__) == "Original error"

    def test_exception_with_context(self):
        """测试异常上下文"""
        try:
            try:
                raise RuntimeError("Context error")
            except RuntimeError:
                raise ValidationError("Validation failed")
        except ValidationError as e:
            assert e.__context__ is not None

    def test_custom_exception_attributes(self):
        """测试自定义异常属性（如果存在）"""
        error = FootballPredictionError("Test")
        # 基础异常属性测试
        assert hasattr(error, "args")
        assert error.args == ("Test",)

    def test_exception_equality(self):
        """测试异常相等性"""
        error1 = ConfigError("Same message")
        error2 = ConfigError("Same message")
        error3 = ConfigError("Different message")

        # 异常通常不会重写__eq__，所以这里测试身份
        assert error1 is not error2
        assert error1 is not error3

    def test_exception_hashability(self):
        """测试异常可哈希性"""
        error = DataError("Test")
        # 异常默认是可哈希的
        assert hash(error) is not None

    def test_exception_pickling(self):
        """测试异常序列化"""
        import pickle

        error = ValidationError("Test message")

        # 测试pickle序列化和反序列化
        pickled = pickle.dumps(error)
        unpickled = pickle.loads(pickled)

        assert type(unpickled) == type(error)
        assert str(unpickled) == str(error)
