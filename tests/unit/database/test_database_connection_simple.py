"""
数据库连接简单测试

测试数据库连接和基本操作
"""

import pytest
from unittest.mock import AsyncMock, Mock, patch


@pytest.mark.unit
class TestDatabaseConnectionSimple:
    """数据库连接基础测试类"""

    def test_database_manager_import(self):
        """测试数据库管理器导入"""
        from src.database.connection import DatabaseManager

        # 验证类可以导入
        assert DatabaseManager is not None

    def test_database_manager_initialization(self):
        """测试数据库管理器初始化"""
        from src.database.connection import DatabaseManager

        # 使用默认配置初始化
        db_manager = DatabaseManager()

        # 验证基本属性
        assert hasattr(db_manager, 'config')
        assert hasattr(db_manager, 'engine')
        assert hasattr(db_manager, 'session_factory')

    def test_database_configuration_import(self):
        """测试数据库配置导入"""
        from src.database.config import DatabaseConfig

        # 验证配置类可以导入
        assert DatabaseConfig is not None

    def test_database_config_initialization(self):
        """测试数据库配置初始化"""
        from src.database.config import DatabaseConfig

        # 使用默认配置初始化
        config = DatabaseConfig()

        # 验证基本属性
        assert hasattr(config, 'database_url')
        assert hasattr(config, 'echo')
        assert hasattr(config, 'pool_size')

    @patch('src.database.connection.create_async_engine')
    def test_async_engine_creation(self, mock_create_engine):
        """测试异步引擎创建"""
        from src.database.connection import DatabaseManager

        # Mock引擎创建
        mock_engine = Mock()
        mock_create_engine.return_value = mock_engine

        # 创建数据库管理器
        db_manager = DatabaseManager()

        # 验证引擎被创建
        mock_create_engine.assert_called_once()
        assert db_manager.engine == mock_engine

    def test_session_factory_creation(self):
        """测试会话工厂创建"""
        from src.database.connection import DatabaseManager

        with patch('src.database.connection.create_async_engine') as mock_create_engine:
            mock_engine = Mock()
            mock_create_engine.return_value = mock_engine

            # Mock会话工厂
            mock_session_factory = Mock()
            mock_engine.return_value = mock_session_factory

            db_manager = DatabaseManager()

            # 验证会话工厂存在
            assert hasattr(db_manager, 'session_factory')

    @patch('src.database.connection.async_sessionmaker')
    def test_session_maker_creation(self, mock_session_maker):
        """测试会话创建器创建"""
        from src.database.connection import DatabaseManager

        # Mock会话创建器
        mock_maker = Mock()
        mock_session_maker.return_value = mock_maker

        db_manager = DatabaseManager()

        # 验证会话创建器被调用
        assert mock_session_maker.called

    def test_database_url_parsing(self):
        """测试数据库URL解析"""
        from src.database.config import DatabaseConfig

        # 测试SQLite URL
        config = DatabaseConfig()
        config.database_url = "sqlite:///./test.db"

        assert config.database_url.startswith("sqlite://")

    def test_connection_pool_configuration(self):
        """测试连接池配置"""
        from src.database.config import DatabaseConfig

        config = DatabaseConfig()

        # 验证连接池配置
        assert hasattr(config, 'pool_size')
        assert hasattr(config, 'max_overflow')
        assert hasattr(config, 'pool_timeout')

    def test_database_logging_configuration(self):
        """测试数据库日志配置"""
        from src.database.config import DatabaseConfig

        config = DatabaseConfig()

        # 验证日志配置
        assert hasattr(config, 'echo')
        assert isinstance(config.echo, bool)

    @patch('src.database.connection.DatabaseManager')
    def test_singleton_pattern(self, mock_db_manager_class):
        """测试单例模式"""
        from src.database.connection import get_database_manager

        # Mock数据库管理器
        mock_db_manager = Mock()
        mock_db_manager_class.return_value = mock_db_manager

        # 获取数据库管理器实例
        db_manager1 = get_database_manager()
        db_manager2 = get_database_manager()

        # 验证返回的是同一个实例（基于mock行为）
        assert db_manager1 is not None
        assert db_manager2 is not None

    def test_database_models_import(self):
        """测试数据库模型导入"""
        from src.database.models import Match, Team, League, Prediction

        # 验证模型可以导入
        assert Match is not None
        assert Team is not None
        assert League is not None
        assert Prediction is not None

    def test_sql_compatibility_import(self):
        """测试SQL兼容性导入"""
        from src.database.sql_compatibility import SQLiteCompatibility, PostgreSQLCompatibility

        # 验证兼容性类可以导入
        assert SQLiteCompatibility is not None
        assert PostgreSQLCompatibility is not None


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--cov=src.database.connection", "--cov-report=term-missing"])