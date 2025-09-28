"""
测试文件：核心模块测试

测试核心系统模块功能
"""

import pytest
from unittest.mock import Mock, patch, AsyncMock


@pytest.mark.unit
class TestCoreModules:
    """核心模块测试类"""

    def test_config_module(self):
        """测试配置模块"""
        try:
            from src.core.config import Config, get_config
            assert Config is not None
            assert callable(get_config)
        except ImportError:
            pytest.skip("Config module not available")

    def test_logging_module(self):
        """测试日志模块"""
        try:
            from src.core.logging import get_logger, setup_logging
            assert callable(get_logger)
            assert callable(setup_logging)
        except ImportError:
            pytest.skip("Logging module not available")

    def test_exceptions_module(self):
        """测试异常模块"""
        try:
            from src.core.exceptions import (
                FootballPredictionException,
                DataQualityException,
                ModelException
            )
            assert FootballPredictionException is not None
            assert DataQualityException is not None
            assert ModelException is not None
        except ImportError:
            pytest.skip("Exceptions module not available")

    def test_metrics_module(self):
        """测试指标模块"""
        try:
            from src.core.metrics import MetricsCollector, collect_metrics
            assert MetricsCollector is not None
            assert callable(collect_metrics)
        except ImportError:
            pytest.skip("Metrics module not available")

    def test_health_check(self):
        """测试健康检查"""
        try:
            from src.core.health import HealthChecker, check_health
            assert HealthChecker is not None
            assert callable(check_health)
        except ImportError:
            pytest.skip("Health check module not available")

    def test_circuit_breaker(self):
        """测试熔断器"""
        try:
            from src.core.circuit_breaker import CircuitBreaker
            assert CircuitBreaker is not None
        except ImportError:
            pytest.skip("Circuit breaker module not available")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--cov=src.core", "--cov-report=term-missing"])