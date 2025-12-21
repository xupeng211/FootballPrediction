"""
核心异常模块测试
测试自定义异常类的功能和行为
"""

import pytest
from typing import Dict, Any

from src.core.exceptions import (
    BaseApplicationError,
    DatabaseError,
    ModelError,
    FeatureExtractionError,
    PredictionError,
    ConfigurationError,
    ValidationError,
    ExternalAPIError,
    CacheError,
    ExplainabilityError,
    InferenceServiceError,
    DataCollectionError,
    ProcessingError,
    AuthenticationError,
    AuthorizationError,
    RateLimitError,
    ResourceNotFoundError,
    ConflictError,
    ServiceUnavailableError,
    TimeoutError,
    IntegrationError,
    HealthCheckError,
    MonitoringError,
    CircuitBreakerError,
    RetryExhaustedError,
)


class TestBaseApplicationError:
    """基础应用异常测试"""

    def test_basic_initialization(self):
        """测试基础初始化"""
        message = "Test error message"
        error = BaseApplicationError(message)

        assert error.message == message
        assert error.error_code is None
        assert error.details == {}
        assert str(error) == message

    def test_full_initialization(self):
        """测试完整初始化"""
        message = "Test error with details"
        error_code = "TEST_001"
        details = {"key": "value", "number": 42}

        error = BaseApplicationError(message=message, error_code=error_code, details=details)

        assert error.message == message
        assert error.error_code == error_code
        assert error.details == details

    def test_to_dict_conversion(self):
        """测试转换为字典格式"""
        message = "Test error"
        error_code = "ERR_001"
        details = {"user_id": 123, "action": "test"}

        error = BaseApplicationError(message=message, error_code=error_code, details=details)

        result = error.to_dict()

        expected = {
            "error_type": "BaseApplicationError",
            "message": message,
            "error_code": error_code,
            "details": details,
        }

        assert result == expected

    def test_to_dict_with_minimal_data(self):
        """测试最小数据转换为字典"""
        message = "Minimal error"
        error = BaseApplicationError(message)

        result = error.to_dict()

        expected = {
            "error_type": "BaseApplicationError",
            "message": message,
            "error_code": None,
            "details": {},
        }

        assert result == expected

    def test_exception_inheritance(self):
        """测试异常继承"""
        error = BaseApplicationError("Test message")

        # 应该是Exception的实例
        assert isinstance(error, Exception)
        # 应该是BaseApplicationError的实例
        assert isinstance(error, BaseApplicationError)

    def test_exception_catching(self):
        """测试异常捕获"""
        message = "Caught error"

        try:
            raise BaseApplicationError(message)
        except BaseApplicationError as e:
            assert e.message == message
        except Exception:
            pytest.fail("应该能够捕获BaseApplicationError")


class TestSpecificErrorTypes:
    """具体异常类型测试"""

    def test_database_error(self):
        """测试数据库错误"""
        error = DatabaseError(
            "Connection failed",
            error_code="DB_CONN_001",
            details={"host": "localhost", "port": 5432},
        )

        assert isinstance(error, BaseApplicationError)
        assert isinstance(error, DatabaseError)
        assert error.message == "Connection failed"
        assert error.error_code == "DB_CONN_001"
        assert error.details["host"] == "localhost"

    def test_model_error(self):
        """测试模型错误"""
        error = ModelError(
            "Model loading failed",
            details={"model_path": "/path/to/model.pkl", "reason": "File not found"},
        )

        assert isinstance(error, BaseApplicationError)
        assert isinstance(error, ModelError)
        assert "model_path" in error.details

    def test_prediction_error(self):
        """测试预测错误"""
        error = PredictionError(
            "Invalid input features",
            error_code="PRED_001",
            details={"features": [1, 2, 3], "expected_count": 10},
        )

        assert isinstance(error, BaseApplicationError)
        assert isinstance(error, PredictionError)
        assert error.error_code == "PRED_001"
        assert len(error.details["features"]) == 3

    def test_configuration_error(self):
        """测试配置错误"""
        error = ConfigurationError(
            "Missing required configuration",
            details={"missing_key": "DATABASE_URL", "config_file": ".env"},
        )

        assert isinstance(error, BaseApplicationError)
        assert isinstance(error, ConfigurationError)

    def test_validation_error(self):
        """测试验证错误"""
        error = ValidationError(
            "Input validation failed",
            details={
                "field": "email",
                "value": "invalid-email",
                "rule": "email_format",
            },
        )

        assert isinstance(error, BaseApplicationError)
        assert isinstance(error, ValidationError)

    def test_external_api_error(self):
        """测试外部API错误"""
        error = ExternalAPIError(
            "API rate limit exceeded",
            error_code="API_429",
            details={"api_name": "FotMob", "retry_after": 60},
        )

        assert isinstance(error, BaseApplicationError)
        assert isinstance(error, ExternalAPIError)

    def test_cache_error(self):
        """测试缓存错误"""
        error = CacheError(
            "Cache connection failed",
            details={"cache_type": "Redis", "host": "localhost:6379"},
        )

        assert isinstance(error, BaseApplicationError)
        assert isinstance(error, CacheError)

    def test_explainability_error(self):
        """测试可解释性错误"""
        error = ExplainabilityError(
            "SHAP calculation failed",
            details={"model_name": "xgboost_v2", "feature_count": 15},
        )

        assert isinstance(error, BaseApplicationError)
        assert isinstance(error, ExplainabilityError)

    def test_inference_service_error(self):
        """测试推理服务错误"""
        error = InferenceServiceError(
            "Service unavailable",
            error_code="INF_001",
            details={"service_name": "inference-v2", "timeout": 30},
        )

        assert isinstance(error, BaseApplicationError)
        assert isinstance(error, InferenceServiceError)

    def test_data_collection_error(self):
        """测试数据收集错误"""
        error = DataCollectionError(
            "Failed to fetch match data",
            details={"source": "FotMob", "match_id": "12345", "error": "HTTP 404"},
        )

        assert isinstance(error, BaseApplicationError)
        assert isinstance(error, DataCollectionError)

    def test_processing_error(self):
        """测试处理错误"""
        error = ProcessingError(
            "Feature processing failed",
            details={"stage": "normalization", "input_size": 1000},
        )

        assert isinstance(error, BaseApplicationError)
        assert isinstance(error, ProcessingError)

    def test_authentication_error(self):
        """测试认证错误"""
        error = AuthenticationError(
            "Invalid credentials",
            details={"username": "test_user", "ip_address": "192.168.1.1"},
        )

        assert isinstance(error, BaseApplicationError)
        assert isinstance(error, AuthenticationError)

    def test_authorization_error(self):
        """测试授权错误"""
        error = AuthorizationError(
            "Insufficient permissions",
            details={
                "user_id": 123,
                "required_permission": "admin",
                "user_permissions": ["user"],
            },
        )

        assert isinstance(error, BaseApplicationError)
        assert isinstance(error, AuthorizationError)

    def test_rate_limit_error(self):
        """测试速率限制错误"""
        error = RateLimitError(
            "Rate limit exceeded",
            details={"limit": 100, "window": "1h", "current_usage": 150},
        )

        assert isinstance(error, BaseApplicationError)
        assert isinstance(error, RateLimitError)

    def test_resource_not_found_error(self):
        """测试资源未找到错误"""
        error = ResourceNotFoundError(
            "Model not found",
            details={
                "resource_type": "model",
                "resource_id": "xgboost_v3",
                "search_path": "/models",
            },
        )

        assert isinstance(error, BaseApplicationError)
        assert isinstance(error, ResourceNotFoundError)

    def test_conflict_error(self):
        """测试冲突错误"""
        error = ConflictError(
            "Resource already exists",
            details={
                "resource_type": "user",
                "resource_id": "test@example.com",
                "conflict_field": "email",
            },
        )

        assert isinstance(error, BaseApplicationError)
        assert isinstance(error, ConflictError)

    def test_service_unavailable_error(self):
        """测试服务不可用错误"""
        error = ServiceUnavailableError(
            "Database service unavailable",
            details={
                "service_name": "PostgreSQL",
                "health_check": "failed",
                "retry_count": 3,
            },
        )

        assert isinstance(error, BaseApplicationError)
        assert isinstance(error, ServiceUnavailableError)

    def test_timeout_error(self):
        """测试超时错误"""
        error = TimeoutError(
            "Operation timed out",
            details={
                "operation": "model_training",
                "timeout_seconds": 300,
                "elapsed_seconds": 300,
            },
        )

        assert isinstance(error, BaseApplicationError)
        assert isinstance(error, TimeoutError)

    def test_integration_error(self):
        """测试集成错误"""
        error = IntegrationError(
            "Third-party service integration failed",
            details={
                "service": "PaymentGateway",
                "endpoint": "/api/v1/charge",
                "error": "Invalid API key",
            },
        )

        assert isinstance(error, BaseApplicationError)
        assert isinstance(error, IntegrationError)

    def test_health_check_error(self):
        """测试健康检查错误"""
        error = HealthCheckError(
            "Health check failed",
            details={
                "component": "Redis",
                "check_type": "connection",
                "error": "Connection refused",
            },
        )

        assert isinstance(error, BaseApplicationError)
        assert isinstance(error, HealthCheckError)

    def test_monitoring_error(self):
        """测试监控错误"""
        error = MonitoringError(
            "Metrics collection failed",
            details={
                "metric_type": "counter",
                "metric_name": "requests_total",
                "error": "Registry error",
            },
        )

        assert isinstance(error, BaseApplicationError)
        assert isinstance(error, MonitoringError)

    def test_circuit_breaker_error(self):
        """测试熔断器错误"""
        error = CircuitBreakerError(
            "Circuit breaker is open",
            details={
                "service": "ExternalAPI",
                "failure_count": 5,
                "threshold": 5,
                "timeout": 60,
            },
        )

        assert isinstance(error, BaseApplicationError)
        assert isinstance(error, CircuitBreakerError)

    def test_retry_exhausted_error(self):
        """测试重试耗尽错误"""
        error = RetryExhaustedError(
            "All retry attempts failed",
            details={
                "max_attempts": 3,
                "total_time": 15.5,
                "last_error": "Connection timeout",
            },
        )

        assert isinstance(error, BaseApplicationError)
        assert isinstance(error, RetryExhaustedError)


class TestExceptionHierarchy:
    """异常层次结构测试"""

    def test_all_exceptions_inherit_from_base(self):
        """测试所有异常都继承自基础异常"""
        exception_classes = [
            DatabaseError,
            ModelError,
            FeatureExtractionError,
            PredictionError,
            ConfigurationError,
            ValidationError,
            ExternalAPIError,
            CacheError,
            ExplainabilityError,
            InferenceServiceError,
            DataCollectionError,
            ProcessingError,
            AuthenticationError,
            AuthorizationError,
            RateLimitError,
            ResourceNotFoundError,
            ConflictError,
            ServiceUnavailableError,
            TimeoutError,
            IntegrationError,
            HealthCheckError,
            MonitoringError,
            CircuitBreakerError,
            RetryExhaustedError,
        ]

        for exception_class in exception_classes:
            # 创建异常实例
            try:
                raise exception_class("Test message")
            except BaseApplicationError as e:
                # 应该能够作为BaseApplicationError捕获
                assert isinstance(e, BaseApplicationError)
                assert isinstance(e, exception_class)
                assert e.message == "Test message"
            except Exception:
                pytest.fail(f"{exception_class.__name__} 应该继承自 BaseApplicationError")

    def test_exception_polymorphism(self):
        """测试异常多态性"""
        exceptions = [
            DatabaseError("DB error"),
            ModelError("Model error"),
            PredictionError("Prediction error"),
            ValidationError("Validation error"),
        ]

        for error in exceptions:
            # 所有异常都应该有相同的方法
            assert hasattr(error, "to_dict")
            assert hasattr(error, "message")
            assert hasattr(error, "error_code")
            assert hasattr(error, "details")

            # 应该都能转换为字典
            result = error.to_dict()
            assert isinstance(result, dict)
            assert "error_type" in result
            assert "message" in result

    def test_exception_serialization(self):
        """测试异常序列化"""
        import json

        error = PredictionError(
            "Test serialization",
            error_code="PRED_001",
            details={"features": [1, 2, 3], "confidence": 0.85},
        )

        # 转换为字典
        error_dict = error.to_dict()

        # 应该能够序列化为JSON
        json_str = json.dumps(error_dict)
        parsed_dict = json.loads(json_str)

        assert parsed_dict["error_type"] == "PredictionError"
        assert parsed_dict["message"] == "Test serialization"
        assert parsed_dict["error_code"] == "PRED_001"
        assert parsed_dict["details"]["features"] == [1, 2, 3]


class TestExceptionUsagePatterns:
    """异常使用模式测试"""

    def test_error_context_enrichment(self):
        """测试错误上下文增强"""
        try:
            # 模拟一个可能失败的操作
            raise ValueError("Original error")
        except ValueError as e:
            # 包装为应用异常并添加上下文
            error = PredictionError(
                f"Feature processing failed: {str(e)}",
                error_code="FEAT_001",
                details={
                    "original_error": str(e),
                    "error_type": type(e).__name__,
                    "processing_stage": "feature_normalization",
                },
            )

            assert "Original error" in error.message
            assert error.details["original_error"] == "Original error"
            assert error.details["processing_stage"] == "feature_normalization"

    def test_error_chaining(self):
        """测试异常链"""
        try:
            # 第一层异常
            raise FileNotFoundError("Model file not found")
        except FileNotFoundError as e:
            try:
                # 第二层异常，使用raise from
                raise ModelError("Failed to load model") from e
            except ModelError as model_error:
                # 验证异常链
                assert model_error.__cause__ is e
                assert str(model_error.__cause__) == "Model file not found"

    def test_error_aggregation(self):
        """测试错误聚合"""
        errors = []

        # 收集多个错误
        for i in range(3):
            try:
                if i == 0:
                    raise ValidationError(f"Invalid field {i}")
                elif i == 1:
                    raise ValidationError(f"Missing field {i}")
                else:
                    raise ValidationError(f"Format error {i}")
            except ValidationError as e:
                errors.append(e.to_dict())

        # 聚合错误
        aggregated_error = ValidationError(
            "Multiple validation errors",
            details={"validation_errors": errors, "total_count": len(errors)},
        )

        assert aggregated_error.details["total_count"] == 3
        assert len(aggregated_error.details["validation_errors"]) == 3

    def test_error_recovery_scenarios(self):
        """测试错误恢复场景"""

        def safe_operation(might_fail: bool = True):
            """可能失败的安全操作"""
            if might_fail:
                raise DatabaseError("Connection failed", details={"retry_count": 0, "max_retries": 3})
            return "success"

        # 模拟重试逻辑
        max_attempts = 3
        last_error = None

        for attempt in range(max_attempts):
            try:
                # 最后一次尝试不失败
                result = safe_operation(might_fail=(attempt < max_attempts - 1))
                assert result == "success"
                break
            except DatabaseError as e:
                last_error = e
                e.details["retry_count"] = attempt + 1
                if attempt == max_attempts - 1:  # 最后一次尝试
                    raise RetryExhaustedError(
                        f"Operation failed after {max_attempts} attempts",
                        details={
                            "original_error": e.to_dict(),
                            "max_attempts": max_attempts,
                        },
                    )

        # 如果没有异常，测试通过
        assert True


if __name__ == "__main__":
    # 运行异常测试
    pytest.main([__file__, "-v", "-s"])
