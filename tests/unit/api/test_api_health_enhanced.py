"""
API健康检查模块增强测试

专门针对src/api/health.py中未覆盖的代码路径进行测试，提升覆盖率从67%到85%+
主要覆盖：异常处理、错误日志、边界情况等场景
"""

from unittest.mock import Mock, patch

import pytest
from fastapi.exceptions import HTTPException
from sqlalchemy.exc import SQLAlchemyError

from src.api.health import (_check_database, _check_filesystem, health_check,
                            readiness_check)


class TestAPIHealthExceptionHandling:
    """测试API健康检查的异常处理场景"""

    @pytest.mark.asyncio
    @patch("src.api.health.get_db_session")
    @patch("src.api.health._check_database")
    @patch("src.api.health._check_redis")
    @patch("src.api.health._check_filesystem")
    async def test_health_check_service_failure_raises_exception(
        self, mock_fs, mock_redis, mock_db, mock_session
    ):
        """测试服务失败时抛出HTTPException (覆盖67-71行)"""
        from src.api.health import health_check

        # 模拟数据库检查失败
        mock_session.return_value = Mock()
        mock_db.return_value = {
            "healthy": False,
            "message": "Database connection failed",
        }
        mock_redis.return_value = {
            "status": "healthy",
            "response_time_ms": 3.0,
            "details": {"message": "Redis OK"},
        }
        mock_fs.return_value = {
            "status": "healthy",
            "response_time_ms": 1.0,
            "details": {"message": "Filesystem OK"},
        }

        # 验证抛出HTTPException
        with pytest.raises(HTTPException) as exc_info:
            await health_check()

        assert exc_info.value.status_code == 503
        assert exc_info.value.detail["status"] == "unhealthy"
        assert "failed_checks" in exc_info.value.detail
        assert "database" in exc_info.value.detail["failed_checks"]

    @pytest.mark.asyncio
    @patch("src.api.health.get_db_session")
    @patch("src.api.health._check_database")
    @patch("src.api.health.logger")
    async def test_health_check_unexpected_exception_handling(
        self, mock_logger, mock_db, mock_session
    ):
        """测试意外异常的处理 (覆盖75-84行)"""

        # 模拟意外异常
        mock_session.return_value = Mock()
        mock_db.side_effect = RuntimeError("Unexpected error")

        # 验证异常被捕获并重新抛出为HTTPException
        with pytest.raises(HTTPException) as exc_info:
            await health_check()

        # 验证错误日志被记录
        mock_logger.error.assert_called()

        # 验证返回的错误结构
        assert exc_info.value.status_code == 503
        assert exc_info.value.detail["status"] == "unhealthy"
        assert "error" in exc_info.value.detail

    @pytest.mark.asyncio
    @patch("src.api.health.logger")
    async def test_check_database_exception_handling(self, mock_logger):
        """测试数据库检查异常处理 (覆盖140-146行)"""
        from src.api.health import _check_database

        # 创建模拟的数据库session，抛出异常
        mock_db_session = Mock()
        mock_db_session.execute.side_effect = SQLAlchemyError("Connection failed")

        result = await _check_database(mock_db_session)

        # 验证异常被捕获并记录
        mock_logger.error.assert_called_with("数据库健康检查失败: Connection failed")

        # 验证返回错误状态
        assert result["status"] == "unhealthy"
        assert "数据库连接失败" in result["details"]["message"]
        assert "error" in result["details"]
        assert result["details"]["error"] == "Connection failed"

    @pytest.mark.asyncio
    async def test_check_redis_basic_functionality(self):
        """测试Redis检查基本功能 (覆盖149-154行)"""
        from src.api.health import _check_redis

        result = await _check_redis()

        # 验证返回状态（Redis可能不可用时返回unhealthy）
        assert result["status"] in ["healthy", "unhealthy"]
        # 检查消息包含Redis相关信息
        assert (
            "Redis" in result["details"]["message"]
            or "Redis连接失败" in result["details"]["message"]
        )

    @pytest.mark.asyncio
    @patch("src.api.health.logger")
    async def test_check_filesystem_exception_handling(self, mock_logger):
        """测试文件系统检查异常处理 (覆盖172, 175-177行)"""
        from src.api.health import _check_filesystem

        # 模拟文件系统异常
        with patch("os.path.exists", side_effect=OSError("Permission denied")):
            result = await _check_filesystem()

            # 验证异常被记录
            mock_logger.error.assert_called()

            # 验证返回错误状态
            assert result["status"] == "unhealthy"
            assert "文件系统检查失败" in result["details"]["message"]

    @pytest.mark.asyncio
    @patch("src.api.health.get_db_session")
    @patch("src.api.health._check_database")
    async def test_readiness_check_database_failure(self, mock_db, mock_session):
        """测试就绪检查中数据库服务失败的情况 (覆盖112-113行)"""
        from src.api.health import readiness_check

        # 模拟数据库检查失败
        mock_session.return_value = Mock()
        mock_db.return_value = {
            "healthy": False,
            "message": "Database connection failed",
        }

        # readiness_check会抛出HTTPException当服务失败时
        with pytest.raises(HTTPException) as exc_info:
            await readiness_check()

        # 验证异常详情
        assert exc_info.value.status_code == 503
        detail = exc_info.value.detail
        assert not detail["ready"]
        assert "checks" in detail
        assert detail["checks"]["database"]["healthy"] is False

    @pytest.mark.asyncio
    @patch("src.api.health.get_db_session")
    @patch("src.api.health._check_database")
    async def test_readiness_check_all_services_healthy(self, mock_db, mock_session):
        """测试所有服务都健康的就绪检查"""

        # 模拟数据库服务正常
        mock_session.return_value = Mock()
        mock_db.return_value = {
            "healthy": True,
            "status": "healthy",
            "response_time_ms": 5.0,
            "details": {"message": "Database OK"},
        }

        result = await readiness_check()

        # 验证就绪状态为True
        assert result["ready"]
        assert "checks" in result
        assert result["checks"]["database"]["healthy"]


class TestAPIHealthEdgeCases:
    """测试API健康检查的边界情况"""

    @pytest.mark.asyncio
    async def test_liveness_check_basic(self):
        """测试存活性检查基础功能 (覆盖94行)"""
        from src.api.health import liveness_check

        result = await liveness_check()

        assert result["status"] == "alive"
        assert "timestamp" in result

    @pytest.mark.asyncio
    @patch("src.api.health.logger")
    async def test_database_check_with_none_session(self, mock_logger):
        """测试数据库session为None的情况"""

        result = await _check_database(None)

        # 验证异常被捕获和记录
        mock_logger.error.assert_called()
        assert result["status"] == "unhealthy"
        assert "数据库连接失败" in result["details"]["message"]

    @pytest.mark.asyncio
    async def test_filesystem_check_basic_functionality(self):
        """测试文件系统检查基本功能"""

        result = await _check_filesystem()

        # 验证返回结果结构
        assert isinstance(result, dict)
        assert "status" in result
        assert "details" in result


class TestAPIHealthResponseTime:
    """测试响应时间计算相关功能"""

    @pytest.mark.asyncio
    @patch("src.api.health.get_db_session")
    @patch("src.api.health._check_database")
    @patch("src.api.health._check_redis")
    @patch("src.api.health._check_filesystem")
    async def test_health_check_response_time_calculation(
        self, mock_fs, mock_redis, mock_db, mock_session
    ):
        """测试健康检查响应时间计算"""

        # 模拟所有服务正常
        mock_session.return_value = Mock()
        mock_db.return_value = {
            "status": "healthy",
            "response_time_ms": 5.0,
            "details": {"message": "Database OK"},
        }
        mock_redis.return_value = {
            "status": "healthy",
            "response_time_ms": 3.0,
            "details": {"message": "Redis OK"},
        }
        mock_fs.return_value = {
            "status": "healthy",
            "response_time_ms": 1.0,
            "details": {"message": "Filesystem OK"},
        }

        result = await health_check()

        # 验证响应时间字段存在
        assert "response_time_ms" in result
        assert isinstance(result["response_time_ms"], (int, float))
        assert result["response_time_ms"] >= 0
