"""
Health API综合测试
直接测试健康检查模块，提升覆盖率
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime
import time
import os
import asyncio
from fastapi import HTTPException, status


class TestHealthCheckBasic:
    """基础健康检查测试"""

    @pytest.mark.asyncio
    async def test_health_check_success(self):
        """测试健康检查成功"""
        # Mock所有依赖
        with patch('src.api.health.get_database_manager') as mock_db_manager, \
             patch('src.api.health._check_redis') as mock_redis, \
             patch('src.api.health._check_kafka') as mock_kafka, \
             patch('src.api.health._check_mlflow') as mock_mlflow, \
             patch('src.api.health._check_filesystem') as mock_filesystem:

            # 设置mock返回值
            mock_db_manager.return_value.get_session.return_value.__enter__.return_value = MagicMock()

            with patch('src.api.health._check_database') as mock_check_db:
                mock_check_db.return_value = {
                    "healthy": True,
                    "status": "healthy",
                    "response_time_ms": 5,
                    "details": {"message": "数据库连接正常"}
                }
                mock_redis.return_value = {
                    "healthy": True,
                    "status": "healthy",
                    "response_time_ms": 2
                }
                mock_kafka.return_value = {
                    "healthy": True,
                    "status": "healthy",
                    "response_time_ms": 10
                }
                mock_mlflow.return_value = {
                    "healthy": True,
                    "status": "healthy",
                    "response_time_ms": 15
                }
                mock_filesystem.return_value = {
                    "status": "healthy",
                    "response_time_ms": 1
                }

                # 导入并执行测试
                try:
                    from src.api.health import health_check
                    with patch.dict(os.environ, {'MINIMAL_HEALTH_MODE': 'false', 'FAST_FAIL': 'false'}):
                        result = await health_check()

                        assert result["status"] == "healthy"
                        assert "timestamp" in result
                        assert "service" in result
                        assert "version" in result
                        assert "uptime" in result
                        assert "checks" in result
                        assert result["service"] == "football-prediction-api"
                except ImportError:
                    pytest.skip("health module not available")

    @pytest.mark.asyncio
    async def test_health_check_minimal_mode(self):
        """测试最小模式健康检查"""
        with patch.dict(os.environ, {'MINIMAL_HEALTH_MODE': 'true'}):
            try:
                from src.api.health import health_check, _optional_check_skipped, _collect_database_health

                with patch('src.api.health._collect_database_health') as mock_db:
                    mock_db.return_value = {
                        "healthy": True,
                        "status": "healthy",
                        "response_time_ms": 5
                    }

                    result = await health_check()

                    assert result["mode"] == "minimal"
                    assert result["checks"]["database"]["status"] == "skipped"
                    for service in ["redis", "kafka", "mlflow", "filesystem"]:
                        assert result["checks"][service]["status"] == "skipped"
            except ImportError:
                pytest.skip("health module not available")

    @pytest.mark.asyncio
    async def test_health_check_failure(self):
        """测试健康检查失败"""
        try:
            from src.api.health import health_check

            with patch('src.api.health._collect_database_health') as mock_db:
                mock_db.return_value = {
                    "healthy": False,
                    "status": "unhealthy",
                    "response_time_ms": 0,
                    "details": {"message": "数据库连接失败"}
                }

                with patch.dict(os.environ, {'MINIMAL_HEALTH_MODE': 'false', 'FAST_FAIL': 'false'}):
                    with pytest.raises(HTTPException) as exc_info:
                        await health_check()

                    assert exc_info.value.status_code == 503
                    assert exc_info.value.detail["status"] == "unhealthy"
        except ImportError:
            pytest.skip("health module not available")

    @pytest.mark.asyncio
    async def test_liveness_check(self):
        """测试存活性检查"""
        try:
            from src.api.health import liveness_check
            result = await liveness_check()

            assert result["status"] == "alive"
            assert "timestamp" in result
        except ImportError:
            pytest.skip("liveness_check not available")

    @pytest.mark.asyncio
    async def test_readiness_check_success(self):
        """测试就绪性检查成功"""
        try:
            from src.api.health import readiness_check, _collect_database_health

            with patch('src.api.health._collect_database_health') as mock_db, \
                 patch('src.api.health._check_redis') as mock_redis, \
                 patch('src.api.health._check_kafka') as mock_kafka, \
                 patch('src.api.health._check_mlflow') as mock_mlflow:

                mock_db.return_value = {"healthy": True}
                mock_redis.return_value = {"healthy": True}
                mock_kafka.return_value = {"healthy": True}
                mock_mlflow.return_value = {"healthy": True}

                with patch.dict(os.environ, {'MINIMAL_HEALTH_MODE': 'false', 'FAST_FAIL': 'false'}):
                    result = await readiness_check()

                    assert result["ready"] is True
                    assert "timestamp" in result
                    assert "checks" in result
        except ImportError:
            pytest.skip("readiness_check not available")

    @pytest.mark.asyncio
    async def test_readiness_check_failure(self):
        """测试就绪性检查失败"""
        try:
            from src.api.health import readiness_check, _collect_database_health

            with patch('src.api.health._collect_database_health') as mock_db:
                mock_db.return_value = {"healthy": False}

                with patch.dict(os.environ, {'MINIMAL_HEALTH_MODE': 'false', 'FAST_FAIL': 'false'}):
                    with pytest.raises(HTTPException) as exc_info:
                        await readiness_check()

                    assert exc_info.value.status_code == 503
                    assert exc_info.value.detail["ready"] is False
        except ImportError:
            pytest.skip("readiness_check not available")


class TestServiceCheckFunctions:
    """服务检查函数测试"""

    @pytest.mark.asyncio
    async def test_check_database_success(self):
        """测试数据库检查成功"""
        try:
            from src.api.health import _check_database
            mock_db = MagicMock()

            with patch('src.api.health.text') as mock_text:
                mock_text.return_value = MagicMock()
                result = await _check_database(mock_db)

                assert result["healthy"] is True
                assert result["status"] == "healthy"
                assert "数据库连接正常" in result["details"]["message"]
        except ImportError:
            pytest.skip("_check_database not available")

    @pytest.mark.asyncio
    async def test_check_database_failure(self):
        """测试数据库检查失败"""
        try:
            from src.api.health import _check_database
            mock_db = MagicMock()
            mock_db.execute.side_effect = Exception("Connection failed")

            result = await _check_database(mock_db)

            assert result["healthy"] is False
            assert result["status"] == "unhealthy"
            assert "Connection failed" in result["details"]["message"]
        except ImportError:
            pytest.skip("_check_database not available")

    @pytest.mark.asyncio
    async def test_check_redis_success(self):
        """测试Redis检查成功"""
        try:
            from src.api.health import _check_redis, ServiceCheckError

            with patch('src.api.health.RedisManager') as mock_redis_manager, \
                 patch('src.api.health._redis_circuit_breaker') as mock_breaker:

                mock_manager = MagicMock()
                mock_manager.aping = AsyncMock(return_value=True)
                mock_manager.get_info = AsyncMock(return_value={
                    "version": "6.2.0",
                    "connected_clients": 10,
                    "used_memory_human": "1.5M"
                })
                mock_redis_manager.return_value = mock_manager

                mock_breaker.call = AsyncMock(return_value={
                    "healthy": True,
                    "status": "healthy",
                    "response_time_ms": 5,
                    "details": {"message": "Redis连接正常"}
                })
                mock_breaker.state = os.getenv("TEST_HEALTH_COMPREHENSIVE_STATE_236")

                result = await _check_redis()

                assert result["healthy"] is True
                assert result["status"] == "healthy"
                assert result["circuit_state"] == "closed"
        except ImportError:
            pytest.skip("_check_redis not available")

    @pytest.mark.asyncio
    async def test_check_redis_failure(self):
        """测试Redis检查失败"""
        try:
            from src.api.health import _check_redis

            with patch('src.api.health._redis_circuit_breaker') as mock_breaker:
                mock_breaker.call = AsyncMock(side_effect=Exception("Redis timeout"))
                mock_breaker.state = "open"

                result = await _check_redis()

                assert result["healthy"] is False
                assert result["status"] == "unhealthy"
                assert "Redis timeout" in result["details"]["error"]
                assert result["circuit_state"] == "open"
        except ImportError:
            pytest.skip("_check_redis not available")

    @pytest.mark.asyncio
    async def test_check_kafka_success(self):
        """测试Kafka检查成功"""
        try:
            from src.api.health import _check_kafka

            with patch('src.api.health.FootballKafkaProducer') as mock_producer_class, \
                 patch('src.api.health.StreamConfig') as mock_config, \
                 patch('src.api.health.asyncio.to_thread') as mock_to_thread, \
                 patch('src.api.health._kafka_circuit_breaker') as mock_breaker:

                mock_producer = MagicMock()
                mock_producer.health_check.return_value = True
                mock_producer.get_producer_config.return_value = {
                    "bootstrap.servers": "localhost:9092"
                }
                mock_producer.producer.list_topics.return_value = MagicMock()
                mock_producer.producer.list_topics.return_value.topics = {
                    "test_topic": MagicMock(),
                    "predictions": MagicMock()
                }

                def mock_run_check():
                    mock_producer_class.return_value = mock_producer
                    return {
                        "healthy": True,
                        "status": "healthy",
                        "details": {
                            "message": "Kafka连接正常",
                            "bootstrap_servers": "localhost:9092",
                            "topics": ["test_topic", "predictions"]
                        }
                    }

                mock_to_thread.side_effect = mock_run_check
                mock_breaker.call = AsyncMock(side_effect=lambda func: func())
                mock_breaker.state = os.getenv("TEST_HEALTH_COMPREHENSIVE_STATE_236")

                result = await _check_kafka()

                assert result["healthy"] is True
                assert result["status"] == "healthy"
                assert "Kafka连接正常" in result["details"]["message"]
        except ImportError:
            pytest.skip("_check_kafka not available")

    @pytest.mark.asyncio
    async def test_check_mlflow_success(self):
        """测试MLflow检查成功"""
        try:
            from src.api.health import _check_mlflow

            with patch('src.api.health.MlflowClient') as mock_client_class, \
                 patch('src.api.health.mlflow') as mock_mlflow, \
                 patch('src.api.health.get_settings') as mock_settings, \
                 patch('src.api.health.asyncio.to_thread') as mock_to_thread, \
                 patch('src.api.health._mlflow_circuit_breaker') as mock_breaker:

                mock_client = MagicMock()
                mock_client.list_experiments.return_value = [
                    MagicMock(), MagicMock(), MagicMock()
                ]
                mock_client_class.return_value = mock_client

                mock_settings_instance = MagicMock()
                mock_settings_instance.mlflow_tracking_uri = "http://localhost:5000"
                mock_settings.return_value = mock_settings_instance

                mock_mlflow.get_tracking_uri.return_value = "http://localhost:5000"

                def mock_run_check():
                    return {
                        "healthy": True,
                        "status": "healthy",
                        "details": {
                            "message": "MLflow连接正常",
                            "tracking_uri": "http://localhost:5000",
                            "experiments": 3
                        }
                    }

                mock_to_thread.side_effect = mock_run_check
                mock_breaker.call = AsyncMock(side_effect=lambda func: func())
                mock_breaker.state = os.getenv("TEST_HEALTH_COMPREHENSIVE_STATE_236")

                result = await _check_mlflow()

                assert result["healthy"] is True
                assert result["status"] == "healthy"
                assert "MLflow连接正常" in result["details"]["message"]
                assert result["details"]["experiments"] == 3
        except ImportError:
            pytest.skip("_check_mlflow not available")

    @pytest.mark.asyncio
    async def test_check_filesystem_success(self):
        """测试文件系统检查成功"""
        try:
            from src.api.health import _check_filesystem

            with patch('src.api.health.os') as mock_os:
                mock_os.path.exists.return_value = True
                mock_os.makedirs.return_value = None

                result = await _check_filesystem()

                assert result["status"] == "healthy"
                assert "文件系统正常" in result["details"]["message"]
                assert result["details"]["log_directory"] == "logs"
        except ImportError:
            pytest.skip("_check_filesystem not available")

    @pytest.mark.asyncio
    async def test_check_filesystem_create_directory(self):
        """测试文件系统检查创建目录"""
        try:
            from src.api.health import _check_filesystem

            with patch('src.api.health.os') as mock_os:
                mock_os.path.exists.return_value = False
                mock_os.makedirs.return_value = None

                result = await _check_filesystem()

                assert result["status"] == "healthy"
                mock_os.makedirs.assert_called_once_with("logs")
        except ImportError:
            pytest.skip("_check_filesystem not available")


class TestHealthCheckUtilities:
    """健康检查工具函数测试"""

    def test_service_check_error(self):
        """测试服务检查错误类"""
        try:
            from src.api.health import ServiceCheckError

            # 测试基本错误
            error = ServiceCheckError("Test error")
            assert str(error) == "Test error"
            assert error.details == {}

            # 测试带详情的错误
            details = {"code": 500, "service": "redis"}
            error = ServiceCheckError("Service unavailable", details=details)
            assert error.details == details
            assert error.details["code"] == 500
        except ImportError:
            pytest.skip("ServiceCheckError not available")

    def test_optional_checks_enabled(self):
        """测试可选检查启用状态"""
        try:
            from src.api.health import _optional_checks_enabled, FAST_FAIL, MINIMAL_HEALTH_MODE

            # 保存原始值
            original_fast_fail = FAST_FAIL
            original_minimal = MINIMAL_HEALTH_MODE

            # 测试不同组合
            test_cases = [
                (True, True, False),  # FAST_FAIL=true, MINIMAL=true -> False
                (True, False, True),  # FAST_FAIL=true, MINIMAL=false -> True
                (False, True, False), # FAST_FAIL=false, MINIMAL=true -> False
                (False, False, False) # FAST_FAIL=false, MINIMAL=false -> False
            ]

            for fast_fail, minimal, expected in test_cases:
                import src.api.health as health_module
                health_module.FAST_FAIL = fast_fail
                health_module.MINIMAL_HEALTH_MODE = minimal
                assert _optional_checks_enabled() == expected

            # 恢复原始值
            import src.api.health as health_module
            health_module.FAST_FAIL = original_fast_fail
            health_module.MINIMAL_HEALTH_MODE = original_minimal
        except ImportError:
            pytest.skip("_optional_checks_enabled not available")

    def test_optional_check_skipped(self):
        """测试可选检查跳过响应"""
        try:
            from src.api.health import _optional_check_skipped

            result = _optional_check_skipped("test_service")

            assert result["healthy"] is True
            assert result["status"] == "skipped"
            assert result["response_time_ms"] == 0.0
            assert "test_service check skipped" in result["details"]["message"]
        except ImportError:
            pytest.skip("_optional_check_skipped not available")

    def test_get_system_health(self):
        """测试获取系统健康状态"""
        try:
            from src.api.health import get_system_health

            result = get_system_health()

            assert result["status"] == "healthy"
            assert "timestamp" in result
            assert "service" in result
            assert "version" in result
            assert "services" in result
            assert result["service"] == "football-prediction-api"

            # 检查服务列表
            services = result["services"]
            assert "database" in services
            assert "redis" in services
            assert "filesystem" in services
            assert all(s["healthy"] for s in services.values())
        except ImportError:
            pytest.skip("get_system_health not available")

    @pytest.mark.asyncio
    async def test_check_database_health_interface(self):
        """测试数据库健康检查接口"""
        try:
            from src.api.health import check_database_health, _check_database
            mock_db = MagicMock()

            with patch('src.api.health._check_database') as mock_internal:
                mock_internal.return_value = {
                    "healthy": True,
                    "status": "healthy",
                    "response_time_ms": 5
                }

                result = await check_database_health(mock_db)

                assert result["healthy"] is True
                mock_internal.assert_called_once_with(mock_db)
        except ImportError:
            pytest.skip("check_database_health not available")

    @pytest.mark.asyncio
    async def test_get_async_session(self):
        """测试获取异步会话"""
        try:
            from src.api.health import get_async_session

            session = await get_async_session()

            # 应该返回一个AsyncMock
            assert hasattr(session, '__class__')
            from unittest.mock import AsyncMock
            assert isinstance(session, AsyncMock)
        except ImportError:
            pytest.skip("get_async_session not available")


class TestHealthCheckIntegration:
    """健康检查集成测试"""

    @pytest.mark.asyncio
    async def test_collect_database_health(self):
        """测试收集数据库健康状态"""
        try:
            from src.api.health import _collect_database_health, get_database_manager

            with patch('src.api.health.get_database_manager') as mock_manager, \
                 patch('src.api.health._check_database') as mock_check:

                mock_manager_instance = MagicMock()
                mock_manager.return_value = mock_manager_instance
                mock_session = MagicMock()
                mock_manager_instance.get_session.return_value.__enter__.return_value = mock_session

                mock_check.return_value = {
                    "healthy": True,
                    "status": "healthy",
                    "response_time_ms": 10
                }

                result = await _collect_database_health()

                assert result["healthy"] is True
                mock_check.assert_called_once_with(mock_session)
        except ImportError:
            pytest.skip("_collect_database_health not available")

    @pytest.mark.asyncio
    async def test_health_check_with_multiple_failures(self):
        """测试多个服务失败的健康检查"""
        try:
            from src.api.health import health_check

            with patch('src.api.health._collect_database_health') as mock_db, \
                 patch('src.api.health._check_redis') as mock_redis:

                mock_db.return_value = {"healthy": False, "status": "unhealthy"}
                mock_redis.return_value = {"healthy": False, "status": "unhealthy"}

                with patch.dict(os.environ, {'MINIMAL_HEALTH_MODE': 'false', 'FAST_FAIL': 'false'}):
                    with pytest.raises(HTTPException) as exc_info:
                        await health_check()

                    detail = exc_info.value.detail
                    assert detail["status"] == "unhealthy"
                    assert "database" in detail["failed_checks"]
                    assert "redis" in detail["failed_checks"]
        except ImportError:
            pytest.skip("health_check not available")

    @pytest.mark.asyncio
    async def test_health_check_response_time_calculation(self):
        """测试健康检查响应时间计算"""
        try:
            from src.api.health import health_check

            with patch('src.api.health._collect_database_health') as mock_db, \
                 patch('src.api.health.time.time') as mock_time:

                # 模拟时间流逝
                mock_time.side_effect = [1000.0, 1000.1]  # 100ms响应时间

                mock_db.return_value = {"healthy": True, "status": "healthy"}

                with patch.dict(os.environ, {'MINIMAL_HEALTH_MODE': 'false', 'FAST_FAIL': 'false'}):
                    result = await health_check()

                    assert "response_time_ms" in result
                    # 应该是100ms（0.1秒 * 1000）
                    assert result["response_time_ms"] == 100.0
        except ImportError:
            pytest.skip("health_check not available")