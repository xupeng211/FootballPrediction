"""
核心异常处理增强测试
专注于提升核心异常模块的覆盖率
"""

import pytest
import traceback
from unittest.mock import patch


class TestBaseExceptions:
    """基础异常测试"""

    def test_football_prediction_exception(self):
        """测试足球预测基础异常"""
        from src.core.exceptions import FootballPredictionException

        # 测试基本异常
        exc = FootballPredictionException("Test error message")
        assert str(exc) == "Test error message"
        assert exc.error_code is None

        # 测试带错误码的异常
        exc_with_code = FootballPredictionException(
            "Error with code", error_code="FP001"
        )
        assert str(exc_with_code) == "Error with code"
        assert exc_with_code.error_code == "FP001"

        # 测试带详情的异常
        exc_with_details = FootballPredictionException(
            "Error with details",
            error_code="FP002",
            details={"field": "value", "context": "test"},
        )
        assert exc_with_details.details["field"] == "value"
        assert exc_with_details.details["context"] == "test"

    def test_validation_exception(self):
        """测试验证异常"""
        from src.core.exceptions import ValidationException

        # 测试基本验证异常
        exc = ValidationException("Validation failed")
        assert "Validation failed" in str(exc)
        assert exc.field is None

        # 测试带字段的验证异常
        exc_with_field = ValidationException(
            "Invalid field value", field="team_name", value="invalid_value"
        )
        assert exc_with_field.field == "team_name"
        assert exc_with_field.value == "invalid_value"

    def test_data_exception(self):
        """测试数据异常"""
        from src.core.exceptions import DataException

        # 测试基本数据异常
        exc = DataException("Data processing error")
        assert "Data processing error" in str(exc)
        assert exc.data_source is None

        # 测试带数据源的异常
        exc_with_source = DataException(
            "Database connection failed",
            data_source="postgresql",
            query="SELECT * FROM matches",
        )
        assert exc_with_source.data_source == "postgresql"
        assert "SELECT * FROM matches" in str(exc_with_source)


class TestPredictionExceptions:
    """预测相关异常测试"""

    def test_prediction_error_exception(self):
        """测试预测错误异常"""
        from src.core.exceptions import PredictionErrorException

        exc = PredictionErrorException(
            "Model prediction failed",
            model_name="xgboost_v2",
            input_data={"home_team": "Team A", "away_team": "Team B"},
        )
        assert "Model prediction failed" in str(exc)
        assert exc.model_name == "xgboost_v2"
        assert exc.input_data["home_team"] == "Team A"

    def test_model_not_found_exception(self):
        """测试模型未找到异常"""
        from src.core.exceptions import ModelNotFoundException

        exc = ModelNotFoundException(
            "Model file not found",
            model_name="neural_network_v1",
            expected_path="/models/neural_network_v1.pkl",
        )
        assert "Model file not found" in str(exc)
        assert exc.model_name == "neural_network_v1"
        assert exc.expected_path == "/models/neural_network_v1.pkl"

    def test_feature_extraction_exception(self):
        """测试特征提取异常"""
        from src.core.exceptions import FeatureExtractionException

        exc = FeatureExtractionException(
            "Feature extraction failed",
            feature_type="h2h_stats",
            match_data={"home_team": "Team A", "away_team": "Team B"},
        )
        assert "Feature extraction failed" in str(exc)
        assert exc.feature_type == "h2h_stats"
        assert exc.match_data["home_team"] == "Team A"


class TestAPIServiceExceptions:
    """API服务异常测试"""

    def test_external_api_exception(self):
        """测试外部API异常"""
        from src.core.exceptions import ExternalAPIException

        exc = ExternalAPIException(
            "External API call failed",
            service_name="fotmob",
            status_code=404,
            response_data={"error": "Not found"},
        )
        assert "External API call failed" in str(exc)
        assert exc.service_name == "fotmob"
        assert exc.status_code == 404
        assert exc.response_data["error"] == "Not found"

    def test_rate_limit_exception(self):
        """测试速率限制异常"""
        from src.core.exceptions import RateLimitException

        exc = RateLimitException(
            "Rate limit exceeded",
            service_name="external_api",
            retry_after=60,
            limit_type="requests_per_minute",
        )
        assert "Rate limit exceeded" in str(exc)
        assert exc.service_name == "external_api"
        assert exc.retry_after == 60
        assert exc.limit_type == "requests_per_minute"

    def test_authentication_exception(self):
        """测试认证异常"""
        from src.core.exceptions import AuthenticationException

        exc = AuthenticationException(
            "Authentication failed", auth_type="api_key", service="external_service"
        )
        assert "Authentication failed" in str(exc)
        assert exc.auth_type == "api_key"
        assert exc.service == "external_service"


class TestDatabaseExceptions:
    """数据库异常测试"""

    def test_connection_exception(self):
        """测试连接异常"""
        from src.core.exceptions import DatabaseConnectionException

        exc = DatabaseConnectionException(
            "Database connection failed",
            database_config={"host": "localhost", "port": 5432},
            original_exception=ConnectionError("Connection refused"),
        )
        assert "Database connection failed" in str(exc)
        assert exc.database_config["host"] == "localhost"
        assert isinstance(exc.original_exception, ConnectionError)

    def test_query_exception(self):
        """测试查询异常"""
        from src.core.exceptions import DatabaseQueryException

        exc = DatabaseQueryException(
            "Query execution failed",
            query="SELECT * FROM matches WHERE date > '2024-01-01'",
            parameters={"limit": 100},
        )
        assert "Query execution failed" in str(exc)
        assert "SELECT * FROM matches" in str(exc)
        assert exc.parameters["limit"] == 100

    def test_transaction_exception(self):
        """测试事务异常"""
        from src.core.exceptions import DatabaseTransactionException

        exc = DatabaseTransactionException(
            "Transaction rollback", operation="insert_match", transaction_id="txn_12345"
        )
        assert "Transaction rollback" in str(exc)
        assert exc.operation == "insert_match"
        assert exc.transaction_id == "txn_12345"


class TestUtilityFunctions:
    """异常处理工具函数测试"""

    def test_format_exception_message(self):
        """测试异常消息格式化"""
        from src.core.exceptions import format_exception_message

        # 测试基本异常
        try:
            raise ValueError("Test error")
        except ValueError as e:
            formatted = format_exception_message(e)
            assert "ValueError" in formatted
            assert "Test error" in formatted

        # 测试带参数的异常
        try:
            raise KeyError("missing_key", {"key": "value"})
        except KeyError as e:
            formatted = format_exception_message(e)
            assert "KeyError" in formatted
            assert "missing_key" in formatted

    def test_create_error_response(self):
        """测试错误响应创建"""
        from src.core.exceptions import create_error_response

        # 测试基本错误响应
        response = create_error_response(
            error_code="VAL001", message="Validation failed", status_code=400
        )
        assert response["error_code"] == "VAL001"
        assert response["message"] == "Validation failed"
        assert response["status_code"] == 400
        assert "timestamp" in response

        # 测试带详情的错误响应
        response_with_details = create_error_response(
            error_code="DATA001",
            message="Data error",
            details={"field": "team_name", "value": "invalid"},
        )
        assert response_with_details["details"]["field"] == "team_name"
        assert response_with_details["details"]["value"] == "invalid"

    def test_log_exception(self):
        """测试异常日志记录"""
        from src.core.exceptions import log_exception
        import logging

        # 创建测试日志记录器
        test_logger = logging.getLogger("test_logger")
        test_logger.setLevel(logging.DEBUG)

        # 捕获日志输出
        with patch.object(test_logger, "error") as mock_error:
            try:
                raise ValueError("Test logging")
            except ValueError as e:
                log_exception(e, test_logger, context="test_context")

            # 验证日志调用
            mock_error.assert_called_once()
            call_args = mock_error.call_args[0][0]
            assert "ValueError" in call_args
            assert "Test logging" in call_args

    def test_exception_chain(self):
        """测试异常链"""
        from src.core.exceptions import FootballPredictionException

        try:
            try:
                raise ValueError("Original error")
            except ValueError as e:
                raise FootballPredictionException("Wrapped error") from e
        except FootballPredictionException as e:
            assert str(e) == "Wrapped error"
            assert e.__cause__.__class__.__name__ == "ValueError"
            assert str(e.__cause__) == "Original error"


class TestExceptionHandlingPatterns:
    """异常处理模式测试"""

    def test_retry_mechanism(self):
        """测试重试机制"""
        from src.core.exceptions import retry_with_backoff
        import time

        call_count = 0

        def failing_function():
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise ConnectionError("Temporary failure")
            return "success"

        # 测试重试成功
        result = retry_with_backoff(
            failing_function, max_attempts=3, backoff_factor=0.1
        )
        assert result == "success"
        assert call_count == 3

        # 测试重试失败
        call_count = 0

        def always_failing():
            nonlocal call_count
            call_count += 1
            raise ConnectionError("Always fails")

        with pytest.raises(ConnectionError):
            retry_with_backoff(always_failing, max_attempts=2, backoff_factor=0.1)
        assert call_count == 2

    def test_circuit_breaker(self):
        """测试熔断器模式"""
        from src.core.exceptions import CircuitBreaker

        def failing_service():
            raise ConnectionError("Service down")

        # 创建熔断器
        breaker = CircuitBreaker(
            failure_threshold=3,
            recovery_timeout=1.0,
            expected_exception=ConnectionError,
        )

        # 前两次失败应该打开熔断器
        with pytest.raises(ConnectionError):
            breaker.call(failing_service)
        with pytest.raises(ConnectionError):
            breaker.call(failing_service)

        # 第三次失败应该触发熔断
        with pytest.raises(ConnectionError):
            breaker.call(failing_service)

        # 熔断器打开后，应该快速失败
        with pytest.raises(ConnectionError):
            breaker.call(failing_service)

        assert breaker.is_open()

    def test_fallback_mechanism(self):
        """测试降级机制"""
        from src.core.exceptions import with_fallback

        def primary_service():
            raise ConnectionError("Primary service down")

        def fallback_service():
            return "fallback_response"

        # 测试降级成功
        result = with_fallback(primary_service, fallback_service, ConnectionError)
        assert result == "fallback_response"

        # 测试主服务成功
        def working_service():
            return "primary_response"

        result = with_fallback(working_service, fallback_service, ConnectionError)
        assert result == "primary_response"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
