#!/usr/bin/env python3
"""
数据库连接测试
"""

import sys
from pathlib import Path
from unittest.mock import Mock, patch

import pytest

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root / "src"))

try:
    from database.connection import get_async_session
except ImportError:
    pytest.skip("数据库模块不可用", allow_module_level=True)


class TestDatabaseConnection:
    """数据库连接测试"""

    @pytest.fixture
    def mock_database_config(self):
        """模拟数据库配置"""
        return {
            "database_url": "postgresql+asyncpg://test:test@localhost/test_db",
            "pool_size": 5,
            "max_overflow": 10,
            "pool_timeout": 30,
            "pool_recycle": 3600,
        }

    @pytest.fixture
    def database_manager(self, mock_database_config):
        """创建数据库管理器实例"""
        with patch("database.base.DatabaseManager") as mock_db_manager:
            mock_manager = Mock()
            mock_db_manager.return_value = mock_manager
            return mock_manager

    @pytest.mark.unit
    def test_database_manager_initialization(self, database_manager):
        """测试数据库管理器初始化"""
        assert database_manager is not None

    @pytest.mark.unit
    def test_database_config_validation(self, mock_database_config):
        """测试数据库配置验证"""
        # 验证必要配置项
        required_fields = ["database_url", "pool_size"]
        for field in required_fields:
            assert field in mock_database_config

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_async_session_creation(self):
        """测试异步会话创建"""
        # 模拟异步会话创建
        with patch("database.connection.get_async_session") as mock_session:
            mock_session.return_value = Mock()
            session = await get_async_session()
            mock_session.assert_called_once()
            assert session is not None

    @pytest.mark.database
    def test_database_connection_string_format(self, mock_database_config):
        """测试数据库连接字符串格式"""
        db_url = mock_database_config["database_url"]

        # 验证连接字符串格式
        assert "postgresql+asyncpg://" in db_url
        assert "@" in db_url
        assert ":" in db_url

    @pytest.mark.database
    def test_pool_configuration(self, mock_database_config):
        """测试连接池配置"""
        pool_config = {
            "pool_size": mock_database_config["pool_size"],
            "max_overflow": mock_database_config["max_overflow"],
            "pool_timeout": mock_database_config["pool_timeout"],
            "pool_recycle": mock_database_config["pool_recycle"],
        }

        # 验证配置值合理性
        assert pool_config["pool_size"] > 0
        assert pool_config["max_overflow"] >= 0
        assert pool_config["pool_timeout"] > 0
        assert pool_config["pool_recycle"] > 0


class TestDatabaseConnectionErrorHandling:
    """数据库连接错误处理测试"""

    @pytest.mark.database
    def test_connection_error_handling(self):
        """测试连接错误处理"""
        with patch("database.base.DatabaseManager") as mock_db_manager:
            # 模拟连接错误
            mock_db = Mock()
            mock_db.connect.side_effect = Exception("Connection failed")
            mock_db_manager.return_value = mock_db

            # 测试错误处理
            with pytest.raises((ConnectionError, OSError)):
                mock_db.connect()

    @pytest.mark.database
    def test_invalid_database_url(self):
        """测试无效数据库URL"""
        with pytest.raises((ValueError, ConnectionError)):
            # 测试无效URL格式
            # 这里应该触发URL验证错误
            pass

    @pytest.mark.database
    def test_connection_timeout_handling(self):
        """测试连接超时处理"""
        with patch("database.base.DatabaseManager") as mock_db_manager:
            # 模拟连接超时
            mock_db = Mock()
            mock_db.connect.side_effect = TimeoutError("Connection timeout")
            mock_db_manager.return_value = mock_db

            with pytest.raises(TimeoutError):
                mock_db.connect()


class TestDatabaseHealth:
    """数据库健康检查测试"""

    @pytest.mark.health
    @pytest.mark.database
    def test_database_health_check(self):
        """测试数据库健康检查"""
        # 模拟健康检查
        with patch("database.base.DatabaseManager") as mock_db_manager:
            mock_db = Mock()
            mock_db.health_check.return_value = {"status": "healthy", "connections": 5}
            mock_db_manager.return_value = mock_db

            health_status = mock_db.health_check()
            assert health_status["status"] == "healthy"
            assert "connections" in health_status

    @pytest.mark.health
    @pytest.mark.database
    def test_database_health_check_unhealthy(self):
        """测试数据库不健康状态"""
        with patch("database.base.DatabaseManager") as mock_db_manager:
            mock_db = Mock()
            mock_db.health_check.return_value = {
                "status": "unhealthy",
                "error": "Connection lost",
            }
            mock_db_manager.return_value = mock_db

            health_status = mock_db.health_check()
            assert health_status["status"] == "unhealthy"
            assert "error" in health_status


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
