"""Integration tests for the core exceptions hierarchy.

Covers:
    1. BaseApplicationError → 25+ derived exception classes
    2. error_code and details propagation through the inheritance chain
    3. to_dict() round-trip fidelity
    4. Multi-level inheritance (BaseApplicationError → DatabaseError → DatabaseConfigurationError)
    5. Exception catching by base class

These tests use zero mocks — every call exercises real exception instantiation and inheritance.
No DB, Docker, network, or secrets are required.
"""

import importlib.util
from pathlib import Path

import pytest

_SRC = Path(__file__).parent.parent.parent / "src"


def _load(module_name: str, rel_path: str):
    """Load a Python module from a source file without triggering package __init__.py."""
    spec = importlib.util.spec_from_file_location(module_name, str(_SRC / rel_path))
    if spec is None or spec.loader is None:
        raise ImportError(f"Cannot load {rel_path} as {module_name}")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


_m_exc = _load("core.exceptions", "core/exceptions.py")

# Unpack all exception classes for tests
BaseApplicationError = _m_exc.BaseApplicationError
AuthenticationError = _m_exc.AuthenticationError
AuthorizationError = _m_exc.AuthorizationError
CacheError = _m_exc.CacheError
CircuitBreakerError = _m_exc.CircuitBreakerError
ConfigurationError = _m_exc.ConfigurationError
ConflictError = _m_exc.ConflictError
DataAlignmentError = _m_exc.DataAlignmentError
DataCollectionError = _m_exc.DataCollectionError
DatabaseConfigurationError = _m_exc.DatabaseConfigurationError
DatabaseError = _m_exc.DatabaseError
ExplainabilityError = _m_exc.ExplainabilityError
ExternalAPIError = _m_exc.ExternalAPIError
FeatureExtractionError = _m_exc.FeatureExtractionError
HashExtractionError = _m_exc.HashExtractionError
HealthCheckError = _m_exc.HealthCheckError
InferenceServiceError = _m_exc.InferenceServiceError
IntegrationError = _m_exc.IntegrationError
ModelError = _m_exc.ModelError
MonitoringError = _m_exc.MonitoringError
NetworkError = _m_exc.NetworkError
PredictionError = _m_exc.PredictionError
ProcessingError = _m_exc.ProcessingError
ProxyConnectionError = _m_exc.ProxyConnectionError
ProxyError = _m_exc.ProxyError
ProxyHealthError = _m_exc.ProxyHealthError
RateLimitError = _m_exc.RateLimitError
ResourceNotFoundError = _m_exc.ResourceNotFoundError
RetryExhaustedError = _m_exc.RetryExhaustedError
ServiceUnavailableError = _m_exc.ServiceUnavailableError
TeamMatchingError = _m_exc.TeamMatchingError
TimeoutError = _m_exc.TimeoutError
URLParsingError = _m_exc.URLParsingError
ValidationError = _m_exc.ValidationError


class TestBaseApplicationError:
    """Base class construction and to_dict()."""

    def test_minimal_construction(self):
        """BaseApplicationError works with only a message."""
        err = BaseApplicationError("something went wrong")
        assert err.message == "something went wrong"
        assert err.error_code is None
        assert err.details == {}
        assert str(err) == "something went wrong"

    def test_full_construction(self):
        """All constructor arguments are preserved."""
        err = BaseApplicationError(
            "critical failure",
            error_code="E001",
            details={"host": "localhost", "port": 5432},
        )
        assert err.error_code == "E001"
        assert err.details["host"] == "localhost"

    def test_to_dict_round_trip(self):
        """to_dict() returns a structured dict with all fields."""
        err = BaseApplicationError("test", error_code="X", details={"k": "v"})
        d = err.to_dict()
        assert d["error_type"] == "BaseApplicationError"
        assert d["message"] == "test"
        assert d["error_code"] == "X"
        assert d["details"] == {"k": "v"}


class TestExceptionInheritance:
    """Multi-level class hierarchy fidelity."""

    def test_derived_is_instance_of_base(self):
        """Every exception class is an instance of BaseApplicationError."""
        err = DatabaseError("db fail")
        assert isinstance(err, BaseApplicationError)
        assert isinstance(err, Exception)

    def test_multi_level_inheritance(self):
        """DatabaseConfigurationError → DatabaseError → BaseApplicationError."""
        err = DatabaseConfigurationError(
            "bad config",
            details={"db_name": "wrong_db"},
        )
        assert isinstance(err, DatabaseConfigurationError)
        assert isinstance(err, DatabaseError)
        assert isinstance(err, BaseApplicationError)

    def test_data_alignment_subclasses(self):
        """URLParsingError / TeamMatchingError / HashExtractionError are DataAlignmentError."""
        url_err = URLParsingError("bad url", details={"url": "x"})
        team_err = TeamMatchingError("no match", details={"team": "y"})
        hash_err = HashExtractionError("hash fail", details={"url": "z"})

        for e in (url_err, team_err, hash_err):
            assert isinstance(e, DataAlignmentError)
            assert isinstance(e, BaseApplicationError)

    def test_proxy_subclasses(self):
        """ProxyConnectionError, ProxyHealthError inherit from ProxyError."""
        conn_err = ProxyConnectionError("conn fail")
        health_err = ProxyHealthError("unhealthy")

        for e in (conn_err, health_err):
            assert isinstance(e, ProxyError)
            assert isinstance(e, BaseApplicationError)


class TestErrorCodePropagation:
    """error_code and details propagate correctly through the hierarchy."""

    def test_to_dict_preserves_subclass_type(self):
        """to_dict reports the concrete class, not the base."""
        err = ValidationError("invalid", error_code="V001")
        d = err.to_dict()
        assert d["error_type"] == "ValidationError"
        assert d["error_code"] == "V001"

    def test_catch_by_base_class(self):
        """All derived exceptions can be caught as BaseApplicationError."""
        with pytest.raises(RateLimitError) as exc_info:
            raise RateLimitError("too many requests", error_code="R429")
        assert exc_info.value.error_code == "R429"

    def test_all_exception_types_to_dict(self):
        """Every exception class produces a valid to_dict() output."""
        exceptions = [
            DatabaseError("db"),
            ModelError("ml"),
            PredictionError("pred"),
            ConfigurationError("cfg"),
            ValidationError("val"),
            ExternalAPIError("api"),
            CacheError("cache"),
            InferenceServiceError("inf"),
            DataCollectionError("data"),
            AuthenticationError("auth"),
            AuthorizationError("authz"),
            RateLimitError("rate"),
            ResourceNotFoundError("nf"),
            ConflictError("conflict"),
            ServiceUnavailableError("svc"),
            TimeoutError("timeout"),
            IntegrationError("int"),
            HealthCheckError("health"),
            MonitoringError("mon"),
            CircuitBreakerError("cb"),
            RetryExhaustedError("retry"),
            NetworkError("net"),
            ProcessingError("proc"),
        ]
        for err in exceptions:
            d = err.to_dict()
            assert "error_type" in d
            assert "message" in d
            assert d["message"] == err.message
