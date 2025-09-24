"""
测试核心异常模块
"""

import pytest

from src.core.exceptions import (
    CacheError,
    ConfigError,
    ConsistencyError,
    DatabaseError,
    DataError,
    FootballPredictionError,
    ModelError,
    PredictionError,
)


class TestExceptionHierarchy:
    """测试异常类层次结构"""

    def test_football_prediction_error_base(self):
        """测试基础异常类"""
        error = FootballPredictionError("Test message")
        assert str(error) == "Test message"
        assert isinstance(error, Exception)

    def test_config_error_inherits_from_base(self):
        """测试ConfigError继承自基础异常"""
        error = ConfigError("Config error")
        assert isinstance(error, FootballPredictionError)
        assert isinstance(error, Exception)
        assert str(error) == "Config error"

    def test_data_error_inherits_from_base(self):
        """测试DataError继承自基础异常"""
        error = DataError("Data error")
        assert isinstance(error, FootballPredictionError)
        assert isinstance(error, Exception)
        assert str(error) == "Data error"

    def test_model_error_inherits_from_base(self):
        """测试ModelError继承自基础异常"""
        error = ModelError("Model error")
        assert isinstance(error, FootballPredictionError)
        assert isinstance(error, Exception)
        assert str(error) == "Model error"

    def test_prediction_error_inherits_from_base(self):
        """测试PredictionError继承自基础异常"""
        error = PredictionError("Prediction error")
        assert isinstance(error, FootballPredictionError)
        assert isinstance(error, Exception)
        assert str(error) == "Prediction error"

    def test_cache_error_inherits_from_data_error(self):
        """测试CacheError继承自DataError"""
        error = CacheError("Cache error")
        assert isinstance(error, DataError)
        assert isinstance(error, FootballPredictionError)
        assert isinstance(error, Exception)
        assert str(error) == "Cache error"

    def test_database_error_inherits_from_data_error(self):
        """测试DatabaseError继承自DataError"""
        error = DatabaseError("Database error")
        assert isinstance(error, DataError)
        assert isinstance(error, FootballPredictionError)
        assert isinstance(error, Exception)
        assert str(error) == "Database error"

    def test_consistency_error_inherits_from_data_error(self):
        """测试ConsistencyError继承自DataError"""
        error = ConsistencyError("Consistency error")
        assert isinstance(error, DataError)
        assert isinstance(error, FootballPredictionError)
        assert isinstance(error, Exception)
        assert str(error) == "Consistency error"


class TestExceptionUsage:
    """测试异常的实际使用场景"""

    def test_raise_and_catch_specific_exception(self):
        """测试抛出和捕获特定异常"""
        with pytest.raises(ConfigError) as exc_info:
            raise ConfigError("配置文件无效")

        assert str(exc_info.value) == "配置文件无效"

    def test_catch_base_exception(self):
        """测试通过基类捕获异常"""
        with pytest.raises(FootballPredictionError):
            raise DataError("数据处理失败")

    def test_catch_data_error_family(self):
        """测试捕获数据错误家族"""
        # CacheError应该能被DataError捕获
        with pytest.raises(DataError):
            raise CacheError("缓存连接失败")

        # DatabaseError应该能被DataError捕获
        with pytest.raises(DataError):
            raise DatabaseError("数据库连接失败")

        # ConsistencyError应该能被DataError捕获
        with pytest.raises(DataError):
            raise ConsistencyError("数据不一致")

    def test_exception_with_complex_message(self):
        """测试带复杂消息的异常"""
        error_details = {
            "error_code": 500,
            "message": "内部服务器错误",
            "timestamp": "2025-01-01T00:00:00Z",
        }
        error = ModelError(f"模型训练失败: {error_details}")

        assert "模型训练失败" in str(error)
        assert "500" in str(error)

    def test_exception_chaining(self):
        """测试异常链"""
        try:
            try:
                raise ValueError("原始错误")
            except ValueError as e:
                raise PredictionError("预测失败") from e
        except PredictionError as e:
            assert e.__cause__ is not None
            assert isinstance(e.__cause__, ValueError)
            assert str(e.__cause__) == "原始错误"
