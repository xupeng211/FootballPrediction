# TODO: Consider creating a fixture for 4 repeated Mock creations

# TODO: Consider creating a fixture for 4 repeated Mock creations

from unittest.mock import patch, AsyncMock, MagicMock
"""数据库连接测试"""

import pytest
# from src.database.connection_mod import DatabaseManager


@pytest.mark.unit
@pytest.mark.database

class TestDatabaseManager:
    """数据库管理器测试"""

    @pytest.fixture
    def db_manager(self):
        """创建数据库管理器实例"""
        with (
            patch("src.database.connection.create_engine"),
            patch("src.database.connection.create_async_engine"),
            patch("src.database.connection.DatabaseConfig"),
        ):
            manager = DatabaseManager()
            # 手动设置必要的属性
            manager._sync_engine = MagicMock()
            manager._async_engine = MagicMock()
            return manager

    def test_get_async_session(self, db_manager):
        """测试获取异步会话"""
        with patch("src.database.connection.async_sessionmaker") as mock_factory:
            mock_session = MagicMock()
            mock_factory.return_value = mock_session
            db_manager._async_session_factory = mock_factory
            session = db_manager.get_async_session()
            assert session is not None

    def test_connection_health_check(self, db_manager):
        """测试连接健康检查"""
        with patch.object(db_manager, "_sync_engine") as mock_engine:
            # 模拟成功连接
            mock_conn = MagicMock()
            mock_engine.connect.return_value.__enter__.return_value = mock_conn
            health = db_manager.health_check()
            assert health is True

    def test_singleton_pattern(self):
        """测试单例模式"""
        manager1 = DatabaseManager()
        manager2 = DatabaseManager()
        assert manager1 is manager2
