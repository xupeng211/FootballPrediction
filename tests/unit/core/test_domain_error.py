"""
测试领域异常类
"""

import pytest

from src.core.exceptions import (
    FootballPredictionError,
    DomainError,
    BusinessRuleError,
    ConfigError,
    DataError,
    ValidationError,
)


class TestDomainErrors:
    """测试领域异常类"""

    def test_domain_error_inheritance(self):
        """测试 DomainError 继承自 FootballPredictionError"""
        error = DomainError("Test error")
        assert isinstance(error, FootballPredictionError)
        assert str(error) == "Test error"

    def test_business_rule_error_inheritance(self):
        """测试 BusinessRuleError 继承自 DomainError"""
        error = BusinessRuleError("Business rule violation")
        assert isinstance(error, DomainError)
        assert isinstance(error, FootballPredictionError)
        assert str(error) == "Business rule violation"

    def test_config_error_inheritance(self):
        """测试 ConfigError 继承自 FootballPredictionError"""
        error = ConfigError("Configuration error")
        assert isinstance(error, FootballPredictionError)
        assert str(error) == "Configuration error"

    def test_data_error_inheritance(self):
        """测试 DataError 继承自 FootballPredictionError"""
        error = DataError("Data error")
        assert isinstance(error, FootballPredictionError)
        assert str(error) == "Data error"

    def test_validation_error_inheritance(self):
        """测试 ValidationError 继承自 FootballPredictionError"""
        error = ValidationError("Validation failed")
        assert isinstance(error, FootballPredictionError)
        assert str(error) == "Validation failed"

    def test_error_raising(self):
        """测试异常抛出"""
        with pytest.raises(DomainError):
            raise DomainError("Test domain error")

        with pytest.raises(BusinessRuleError):
            raise BusinessRuleError("Test business rule error")

    def test_error_with_none_message(self):
        """测试无消息的异常"""
        error = DomainError()
        assert isinstance(error, Exception)

    def test_error_with_attributes(self):
        """测试带属性的异常"""
        error = DomainError("Test")
        error.error_code = "DOMAIN_001"
        assert error.error_code == "DOMAIN_001"