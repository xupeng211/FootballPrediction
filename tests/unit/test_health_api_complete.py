"""
Health API 完整单元测试套件

遵循TDD原则，确保HealthCheckResponse与ServiceCheck schema严格对应
使用pytest-mock进行依赖隔离，验证所有逻辑分支
"""

import pytest
from datetime import datetime
from unittest.mock import Mock, AsyncMock, patch
from sqlalchemy.orm import Session

from fastapi import HTTPException
from fastapi.testclient import TestClient

from src.api.health import router, health_check, readiness_check, _check_database
from src.api.schemas import HealthCheckResponse, ServiceCheck
from src.database.connection import get_db_session


@pytest.fixture
def mock_db_session():
    """模拟数据库会话"""
    mock_session = Mock(spec=Session)
    mock_session.execute.return_value = Mock()
    return mock_session


@pytest.fixture
def client():
    """创建测试客户端"""
    return TestClient(router)


class TestHealthCheck:
    """健康检查端点完整测试套件"""

    @pytest.mark.asyncio
    async def test_health_check_success_response_format(self):
        """
        测试健康检查成功响应格式

        验证响应完全符合HealthCheckResponse schema
        """
        # 执行健康检查
        with patch('src.api.health.datetime') as mock_datetime:
            mock_datetime.utcnow.return_value.isoformat.return_value = "2024-01-01T00:00:00"

            response = await health_check()

        # 验证响应结构符合HealthCheckResponse schema
        assert response.status == "healthy"
        assert response.service == "football-prediction-api"
        assert response.version == "1.0.0"
        assert isinstance(response.timestamp, str)
        assert isinstance(response.checks, dict)

        # 验证各服务检查结构
        for service_name, check_result in response.checks.items():
            assert hasattr(check_result, 'status')
            assert hasattr(check_result, 'response_time_ms')
            assert hasattr(check_result, 'details')
            assert isinstance(check_result.details, dict)

    @pytest.mark.asyncio
    async def test_health_check_service_completeness(self):
        """
        测试健康检查包含所有必需的服务
        """
        response = await health_check()

        # 验证包含所有关键服务
        required_services = ["database", "redis", "filesystem"]
        for service in required_services:
            assert service in response.checks, f"缺少服务检查: {service}"

        # 验证每个服务都有必需字段
        for service in required_services:
            check = response.checks[service]
            assert isinstance(check.status, str)
            assert isinstance(check.response_time_ms, (int, float))
            assert isinstance(check.details, dict)

    @pytest.mark.asyncio
    async def test_health_check_response_time_validation(self):
        """
        测试响应时间字段的合理性
        """
        response = await health_check()

        # 验证总响应时间
        assert isinstance(response.response_time_ms, (int, float))
        assert response.response_time_ms >= 0

        # 验证各服务响应时间
        for service_check in response.checks.values():
            assert isinstance(service_check.response_time_ms, (int, float))
            assert service_check.response_time_ms >= 0

    @pytest.mark.asyncio
    async def test_health_check_timestamp_format(self):
        """
        测试时间戳格式符合ISO标准
        """
        with patch('src.api.health.datetime') as mock_datetime:
            test_time = datetime(2024, 1, 1, 12, 0, 0)
            mock_datetime.utcnow.return_value = test_time

            response = await health_check()

            # 验证时间戳格式
            assert response.timestamp == test_time.isoformat()
            # 验证时间戳可以被解析
            parsed_time = datetime.fromisoformat(response.timestamp)
            assert parsed_time == test_time


class TestReadinessCheck:
    """就绪性检查完整测试套件"""

    @pytest.mark.asyncio
    async def test_readiness_check_all_healthy(self, mock_db_session):
        """
        测试所有服务健康时的就绪性检查
        """
        with patch('src.api.health._check_database') as mock_check_db:
            mock_check_db.return_value = {
                "healthy": True,
                "message": "数据库连接正常",
                "response_time_ms": 1.0
            }

            with patch('src.api.health.get_db_session', return_value=mock_db_session):
                response = await readiness_check(mock_db_session)

        # 验证响应结构
        assert response["ready"] is True
        assert "timestamp" in response
        assert "checks" in response
        assert "database" in response["checks"]
        # readiness check返回的是ServiceCheck转换后的格式，不是healthy字段
        assert response["checks"]["database"]["status"] == "healthy"

    @pytest.mark.asyncio
    async def test_readiness_check_database_unhealthy(self, mock_db_session):
        """
        测试数据库不健康时的就绪性检查
        """
        with patch('src.api.health._check_database') as mock_check_db:
            mock_check_db.return_value = {
                "healthy": False,
                "message": "数据库连接失败",
                "error": "Connection timeout"
            }

            with patch('src.api.health.get_db_session', return_value=mock_db_session):
                with pytest.raises(HTTPException) as exc_info:
                    await readiness_check(mock_db_session)

        # 验证HTTP异常
        assert exc_info.value.status_code == 503
        error_detail = exc_info.value.detail
        assert error_detail["ready"] is False
        assert "database" in error_detail["checks"]
        assert error_detail["checks"]["database"]["status"] == "unhealthy"

    @pytest.mark.asyncio
    async def test_readiness_check_database_exception(self, mock_db_session):
        """
        测试数据库检查抛出异常时的就绪性检查
        """
        with patch('src.api.health._check_database') as mock_check_db:
            mock_check_db.side_effect = Exception("数据库连接异常")

            with patch('src.api.health.get_db_session', return_value=mock_db_session):
                with pytest.raises(HTTPException) as exc_info:
                    await readiness_check(mock_db_session)

        # 验证异常处理
        assert exc_info.value.status_code == 503
        error_detail = exc_info.value.detail
        assert error_detail["ready"] is False
        assert "database" in error_detail["checks"]
        assert error_detail["checks"]["database"]["status"] == "unhealthy"
        assert "数据库连接异常" in error_detail["checks"]["database"]["details"]["error"]

    @pytest.mark.asyncio
    async def test_readiness_check_timestamp_format(self, mock_db_session):
        """
        测试就绪性检查的时间戳格式
        """
        with patch('src.api.health.datetime') as mock_datetime:
            test_time = datetime(2024, 1, 1, 12, 0, 0)
            mock_datetime.utcnow.return_value = test_time

            with patch('src.api.health._check_database') as mock_check_db:
                mock_check_db.return_value = {"healthy": True, "message": "正常"}

                with patch('src.api.health.get_db_session', return_value=mock_db_session):
                    response = await readiness_check(mock_db_session)

        assert response["timestamp"] == test_time.isoformat()


class TestDatabaseHealthCheck:
    """数据库健康检查详细测试"""

    @pytest.mark.asyncio
    async def test_check_database_success(self, mock_db_session):
        """
        测试数据库连接检查成功
        """
        # 模拟成功执行查询
        mock_db_session.execute.return_value = Mock()

        result = await _check_database(mock_db_session)

        # 验证返回结构
        assert result["healthy"] is True
        assert "数据库连接正常" in result["message"]
        assert result["response_time_ms"] >= 0  # 现在是真实测量的时间
        assert "error" not in result

    @pytest.mark.asyncio
    async def test_check_database_failure(self, mock_db_session):
        """
        测试数据库连接检查失败
        """
        # 模拟数据库异常
        mock_db_session.execute.side_effect = Exception("连接超时")

        result = await _check_database(mock_db_session)

        # 验证错误处理
        assert result["healthy"] is False
        assert "连接失败" in result["message"]
        assert "连接超时" in result["error"]
        assert result["response_time_ms"] == 0

    @pytest.mark.asyncio
    async def test_check_database_with_specific_error(self, mock_db_session):
        """
        测试数据库特定错误类型
        """
        # 模拟特定数据库错误
        mock_db_session.execute.side_effect = Exception("Connection refused")

        result = await _check_database(mock_db_session)

        # 验证特定错误信息被正确传递
        assert result["healthy"] is False
        assert "Connection refused" in result["error"]


class TestLivenessCheck:
    """存活性检查测试"""

    @pytest.mark.asyncio
    async def test_liveness_check_basic_response(self):
        """
        测试存活性检查基本响应
        """
        from src.api.health import liveness_check

        with patch('src.api.health.datetime') as mock_datetime:
            test_time = datetime(2024, 1, 1, 12, 0, 0)
            mock_datetime.utcnow.return_value = test_time

            response = await liveness_check()

        # 验证响应结构
        assert response["status"] == "alive"
        assert response["timestamp"] == test_time.isoformat()
        assert len(response) == 2  # 只包含这两个字段


class TestHealthCheckIntegration:
    """健康检查集成测试"""

    @pytest.mark.asyncio
    async def test_all_health_endpoints_consistency(self, mock_db_session):
        """
        测试所有健康检查端点的一致性
        """
        with patch('src.api.health.datetime') as mock_datetime:
            test_time = datetime(2024, 1, 1, 12, 0, 0)
            mock_datetime.utcnow.return_value = test_time

            # 获取各端点响应
            health_response = await health_check()

            with patch('src.api.health._check_database') as mock_check_db:
                mock_check_db.return_value = {"healthy": True, "message": "正常"}
                readiness_response = await readiness_check(mock_db_session)

            from src.api.health import liveness_check
            liveness_response = await liveness_check()

        # 验证时间戳一致性
        assert health_response.timestamp == test_time.isoformat()
        assert readiness_response["timestamp"] == test_time.isoformat()
        assert liveness_response["timestamp"] == test_time.isoformat()

        # 验证状态一致性
        assert health_response.status == "healthy"
        assert readiness_response["ready"] is True
        assert liveness_response["status"] == "alive"

    @pytest.mark.asyncio
    async def test_error_logging_on_database_failure(self, mock_db_session):
        """
        测试数据库失败时的错误日志记录
        """
        with patch('src.api.health.logger') as mock_logger:
            mock_db_session.execute.side_effect = Exception("数据库错误")

            result = await _check_database(mock_db_session)

            # 验证错误被正确记录
            mock_logger.error.assert_called_once()
            assert "数据库健康检查失败" in str(mock_logger.error.call_args)


class TestSchemaValidation:
    """Schema验证测试"""

    def test_service_check_schema_validation(self):
        """
        测试ServiceCheck schema验证
        """
        # 测试有效数据
        valid_data = {
            "status": "healthy",
            "response_time_ms": 1.5,
            "details": {"message": "服务正常"}
        }
        service_check = ServiceCheck(**valid_data)
        assert service_check.status == "healthy"
        assert service_check.response_time_ms == 1.5

        # 测试无效数据
        invalid_data = {
            "status": "healthy",
            # 缺少必需字段
        }
        with pytest.raises(ValueError):
            ServiceCheck(**invalid_data)

    def test_health_check_response_schema_validation(self):
        """
        测试HealthCheckResponse schema验证
        """
        # 创建测试用的ServiceCheck
        checks = {
            "database": ServiceCheck(
                status="healthy",
                response_time_ms=1.0,
                details={"message": "正常"}
            )
        }

        # 测试有效数据
        valid_data = {
            "status": "healthy",
            "timestamp": "2024-01-01T00:00:00",
            "service": "test-service",
            "version": "1.0.0",
            "response_time_ms": 5.0,
            "checks": checks
        }

        health_response = HealthCheckResponse(**valid_data)
        assert health_response.status == "healthy"
        assert health_response.service == "test-service"
        assert len(health_response.checks) == 1


if __name__ == "__main__":
    # 运行测试
    pytest.main([__file__, "-v", "--tb=short"])