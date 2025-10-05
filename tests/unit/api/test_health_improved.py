"""
测试健康检查API端点（改进版）
"""

from unittest.mock import MagicMock

import pytest
from sqlalchemy.orm import Session

from src.api.health import _check_database, _optional_check_skipped, get_system_health


class TestHealthCheckUtils:
    """测试健康检查工具函数"""

    def test_optional_check_skipped(self):
        """测试可选检查跳过响应"""
        result = _optional_check_skipped("test-service")
        expected = {
            "healthy": True,
            "status": "skipped",
            "response_time_ms": 0.0,
            "details": {"message": "test-service check skipped in minimal mode"},
        }
        assert result == expected

    def test_get_system_health(self):
        """测试获取系统健康状态"""
        result = get_system_health()
        assert "status" in result
        assert "timestamp" in result
        assert "service" in result
        assert "version" in result
        assert "services" in result
        assert result["status"] == "healthy"
        assert result["service"] == "football-prediction-api"


class TestDatabaseHealthCheck:
    """测试数据库健康检查"""

    @pytest.fixture
    def mock_db_session(self):
        """模拟数据库会话"""
        session = MagicMock(spec=Session)
        return session

    @pytest.mark.asyncio
    async def test_check_database_success(self, mock_db_session):
        """测试数据库健康检查成功"""
        mock_db_session.execute.return_value = MagicMock()

        result = await _check_database(mock_db_session)

        assert result["healthy"] is True
        assert result["status"] == "healthy"
        assert "response_time_ms" in result
        mock_db_session.execute.assert_called_once()


# 以下测试需要重构，暂时跳过
@pytest.mark.skip(reason="需要重构Redis集成测试")
class TestRedisHealthCheck:
    """测试Redis健康检查"""


@pytest.mark.skip(reason="需要重构文件系统集成测试")
class TestFilesystemHealthCheck:
    """测试文件系统健康检查"""


@pytest.mark.skip(reason="需要重构健康端点集成测试")
class TestHealthEndpoints:
    """测试健康检查端点"""
