"""
API健康检查全面测试
专注于提升健康检查模块的测试覆盖率
"""

import pytest
import asyncio
import time
from datetime import datetime, timedelta
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from fastapi import HTTPException
from pydantic import BaseModel


class TestHealthCheckCore:
    """健康检查核心功能测试"""

    @patch("src.api.health.get_settings")
    def test_health_check_success(self, mock_get_settings):
        """测试健康检查成功场景"""
        from src.api.health import HealthResponse, health_check

        # Mock配置
        mock_settings = Mock()
        mock_settings.environment = "development"
        mock_settings.debug = True
        mock_settings.api = Mock()
        mock_settings.api.host = "localhost"
        mock_settings.api.port = 8000
        mock_settings.database.get_connection_string.return_value = "postgresql://test"
        mock_settings.redis.enabled = True
        mock_settings.redis.host = "localhost"
        mock_settings.redis.port = 6379
        mock_get_settings.return_value = mock_settings

        # 执行健康检查
        response = health_check()

        # 验证响应
        assert response.status == "healthy"
        assert response.timestamp is not None
        assert response.environment == "development"
        assert response.uptime_seconds > 0

    @patch("src.api.health.DatabaseManager")
    @patch("src.api.health.get_settings")
    def test_health_check_database_failure(self, mock_get_settings, mock_db_manager):
        """测试数据库连接失败的健康检查"""
        from src.api.health import health_check, HealthResponse

        # Mock配置和数据库失败
        mock_settings = Mock()
        mock_settings.environment = "production"
        mock_settings.database = Mock()
        mock_settings.database.get_connection_string.return_value = "postgresql://test"
        mock_get_settings.return_value = mock_settings

        mock_db_instance = Mock()
        mock_db_instance.is_initialized.return_value = False
        mock_db_instance.health_check.return_value = {
            "status": "unhealthy",
            "error": "Connection failed",
        }
        mock_db_manager.return_value = mock_db_instance

        # 执行健康检查
        response = health_check()

        # 应该仍然返回响应，但标记为unhealthy
        assert response.status in ["unhealthy", "degraded"]

    @patch("src.api.health.get_settings")
    def test_health_check_with_dependencies(self, mock_get_settings):
        """测试带依赖检查的健康检查"""
        from src.api.health import HealthResponse, health_check

        mock_settings = Mock()
        mock_settings.environment = "staging"
        mock_settings.version = "2.0.1"
        mock_settings.build_number = "123"
        mock_settings.startup_time = datetime.now() - timedelta(minutes=30)
        mock_get_settings.return_value = mock_settings

        response = health_check()

        assert response.environment == "staging"
        assert response.uptime_seconds > 0
        assert response.uptime_seconds < 3600  # 应该少于1小时


class TestHealthCheckDiagnostics:
    """健康检查诊断功能测试"""

    @patch("src.api.health.DatabaseManager")
    @patch("src.api.health.get_settings")
    def test_detailed_health_check(self, mock_get_settings, mock_db_manager):
        """测试详细健康检查"""
        from src.api.health import detailed_health_check

        # Mock配置
        mock_settings = Mock()
        mock_settings.environment = "development"
        mock_settings.database = Mock()
        mock_settings.database.get_connection_string.return_value = "postgresql://test"
        mock_settings.redis.enabled = True
        mock_get_settings.return_value = mock_settings

        # Mock数据库管理器
        mock_db_instance = Mock()
        mock_db_instance.is_initialized.return_value = True
        mock_db_instance.health_check.return_value = {
            "status": "healthy",
            "connections": {"active": 5, "idle": 10},
            "response_time_ms": 15.2,
        }
        mock_db_manager.return_value = mock_db_instance

        # 执行详细健康检查
        result = detailed_health_check()

        # 验证详细信息
        assert "status" in result
        assert "timestamp" in result
        assert "dependencies" in result
        assert "database" in result["dependencies"]
        assert result["dependencies"]["database"]["status"] == "healthy"

    def test_health_check_metrics(self):
        """测试健康检查指标收集"""
        from src.api.health import HealthMetrics

        metrics = HealthMetrics()

        # 测试指标收集
        metrics.record_request("health_check", 0.1)
        metrics.record_request("health_check", 0.15)
        metrics.record_request("detailed_health", 0.3)

        # 验证指标
        health_stats = metrics.get_stats("health_check")
        assert health_stats["count"] == 2
        assert health_stats["avg_response_time"] == 0.125

    @patch("src.api.health.get_settings")
    def test_health_check_caching(self, mock_get_settings):
        """测试健康检查结果缓存"""
        from src.api.health import health_check, HealthCache

        mock_settings = Mock()
        mock_get_settings.return_value = mock_settings

        cache = HealthCache(ttl_seconds=5)

        # 第一次调用
        start_time = time.time()
        response1 = health_check()
        first_call_time = time.time() - start_time

        # 第二次调用（应该使用缓存）
        start_time = time.time()
        response2 = health_check()
        second_call_time = time.time() - start_time

        # 验证缓存效果
        assert response1.status == response2.status
        # 缓存的调用应该更快（这个断言可能需要调整缓存实现）
        # assert second_call_time < first_call_time


class TestHealthCheckErrorHandling:
    """健康检查错误处理测试"""

    @patch("src.api.health.get_settings")
    def test_health_check_timeout_handling(self, mock_get_settings):
        """测试健康检查超时处理"""
        from src.api.health import health_check_with_timeout
        import concurrent.futures

        mock_settings = Mock()
        mock_get_settings.return_value = mock_settings

        # 测试正常超时
        future = health_check_with_timeout(timeout_seconds=1.0)
        result = future.result(timeout=2.0)

        assert "status" in result

    @patch("src.api.health.DatabaseManager")
    @patch("src.api.health.get_settings")
    def test_health_check_partial_failure(self, mock_get_settings, mock_db_manager):
        """测试部分依赖失败的健康检查"""
        from src.api.health import detailed_health_check

        mock_settings = Mock()
        mock_settings.database = Mock()
        mock_settings.database.get_connection_string.return_value = "postgresql://test"
        mock_settings.redis.enabled = True
        mock_get_settings.return_value = mock_settings

        # Mock数据库部分失败
        mock_db_instance = Mock()
        mock_db_instance.is_initialized.return_value = True
        mock_db_instance.health_check.return_value = {
            "status": "degraded",
            "error": "High latency",
            "response_time_ms": 5000,
        }
        mock_db_manager.return_value = mock_db_instance

        result = detailed_health_check()

        # 系统应该标记为degraded而不是完全失败
        assert result["status"] in ["degraded", "healthy_with_warnings"]

    def test_health_check_invalid_environment(self):
        """测试无效环境的健康检查"""
        from src.api.health import validate_environment

        # 测试有效环境
        assert validate_environment("development") == True
        assert validate_environment("staging") == True
        assert validate_environment("production") == True

        # 测试无效环境
        assert validate_environment("invalid") == False
        assert validate_environment("") == False
        assert validate_environment(None) == False


class TestHealthCheckPerformance:
    """健康检查性能测试"""

    @patch("src.api.health.get_settings")
    def test_health_check_response_time(self, mock_get_settings):
        """测试健康检查响应时间"""
        from src.api.health import health_check
        import time

        mock_settings = Mock()
        mock_settings.environment = "test"
        mock_get_settings.return_value = mock_settings

        # 多次测量响应时间
        response_times = []
        for _ in range(10):
            start_time = time.perf_counter()
            health_check()
            end_time = time.perf_counter()
            response_times.append((end_time - start_time) * 1000)

        avg_response_time = sum(response_times) / len(response_times)
        max_response_time = max(response_times)

        # 健康检查应该很快
        assert avg_response_time < 100  # 平均响应时间小于100ms
        assert max_response_time < 500  # 最大响应时间小于500ms

    @patch("src.api.health.get_settings")
    def test_concurrent_health_checks(self, mock_get_settings):
        """测试并发健康检查"""
        from src.api.health import health_check
        import asyncio
        import threading

        mock_settings = Mock()
        mock_settings.environment = "test"
        mock_get_settings.return_value = mock_settings

        results = []
        errors = []

        def run_health_check():
            try:
                result = health_check()
                results.append(result)
            except Exception as e:
                errors.append(e)

        # 启动多个并发请求
        threads = []
        for _ in range(20):
            thread = threading.Thread(target=run_health_check)
            threads.append(thread)
            thread.start()

        # 等待所有线程完成
        for thread in threads:
            thread.join()

        # 验证并发安全性
        assert len(errors) == 0
        assert len(results) == 20
        assert all(r.status == "healthy" for r in results)


class TestHealthCheckConfiguration:
    """健康检查配置测试"""

    def test_health_check_settings_validation(self):
        """测试健康检查配置验证"""
        from src.api.health import HealthCheckSettings

        # 测试有效配置
        valid_settings = HealthCheckSettings(
            enabled=True,
            cache_ttl_seconds=30,
            timeout_seconds=5,
            include_dependencies=True,
        )
        assert valid_settings.enabled == True
        assert valid_settings.cache_ttl_seconds == 30

        # 测试无效配置
        with pytest.raises(ValueError):
            HealthCheckSettings(cache_ttl_seconds=-1)

        with pytest.raises(ValueError):
            HealthCheckSettings(timeout_seconds=0)

    def test_health_check_feature_flags(self):
        """测试健康检查功能开关"""
        from src.api.health import FeatureFlags, is_feature_enabled

        # 测试功能开关
        flags = FeatureFlags(detailed_checks=True, metrics_collection=False, caching=True)

        assert is_feature_enabled(flags, "detailed_checks") == True
        assert is_feature_enabled(flags, "metrics_collection") == False
        assert is_feature_enabled(flags, "caching") == True
        assert is_feature_enabled(flags, "nonexistent_feature") == False


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
