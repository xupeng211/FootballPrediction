"""
数据库连接模块增强测试

专门针对src/database/connection.py中未覆盖的代码路径进行测试，提升覆盖率从63%到80%+
主要覆盖：异步会话、异常处理、连接管理等场景
"""

from unittest.mock import Mock, patch

import pytest

pytestmark = pytest.mark.integration

from sqlalchemy.exc import DisconnectionError, SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Session

# 尝试导入 DatabaseManager
try:
    from src.database.connection import DatabaseManager
except ImportError:
    # 如果导入失败，DatabaseManager 将在运行时定义
    pass


def get_test_config():
    """获取测试用的数据库配置"""
    from src.database.config import DatabaseConfig

    return DatabaseConfig(
        host="localhost",
        port=5432,
        database="test_db",
        username="test_user",
        password="test_pass",
    )


class TestDatabaseConnectionExceptionHandling:
    """测试数据库连接的异常处理场景"""

    def test_create_session_without_initialization(self):
        """测试未初始化时创建会话抛出异常 (覆盖120行)"""
        from src.database.connection import DatabaseManager

        # 创建一个全新的实例，不使用单例
        manager = DatabaseManager()
        # 确保session_factory未初始化
        manager._session_factory = None

        with pytest.raises(RuntimeError) as exc_info:
            manager.create_session()

        assert "数据库连接未初始化" in str(exc_info.value)
        assert "请先调用 initialize()" in str(exc_info.value)

    def test_create_async_session_without_initialization(self):
        """测试未初始化时创建异步会话抛出异常 (覆盖125-127行)"""

        # 创建一个全新的实例，不使用单例
        manager = DatabaseManager()
        # 确保async_session_factory未初始化
        manager._async_session_factory = None

        with pytest.raises(RuntimeError) as exc_info:
            manager.create_async_session()

        assert "数据库连接未初始化" in str(exc_info.value)
        assert "请先调用 initialize()" in str(exc_info.value)

    @patch("src.database.connection.logger")
    def test_get_session_with_exception_rollback(self, mock_logger):
        """测试会话异常时的回滚处理 (覆盖139-148行)"""

        # 创建模拟的数据库管理器
        manager = DatabaseManager()

        # 模拟会话和异常
        mock_session = Mock(spec=Session)
        mock_session.commit.side_effect = SQLAlchemyError("Commit failed")

        with patch.object(manager, "create_session", return_value=mock_session):
            with pytest.raises(SQLAlchemyError):
                with manager.get_session():
                    # 模拟在会话中发生异常
                    pass

            # 验证回滚和关闭被调用
            mock_session.rollback.assert_called_once()
            mock_session.close.assert_called_once()
            mock_logger.error.assert_called_once()
            assert "数据库操作失败" in str(mock_logger.error.call_args[0][0])

    def test_get_session_successful_commit(self):
        """测试会话成功提交的情况"""

        manager = DatabaseManager()
        mock_session = Mock(spec=Session)

        with patch.object(manager, "create_session", return_value=mock_session):
            with manager.get_session():
                # 正常操作，不抛出异常
                pass

            # 验证提交和关闭被调用
            mock_session.commit.assert_called_once()
            mock_session.close.assert_called_once()
            # 不应该调用回滚
            mock_session.rollback.assert_not_called()

    @patch("src.database.connection.create_engine")
    def test_sync_engine_creation_failure(self, mock_create_engine):
        """测试同步引擎创建失败 (覆盖160-169行)"""

        # 模拟引擎创建失败
        mock_create_engine.side_effect = Exception("Engine creation failed")

        manager = DatabaseManager()
        config = get_test_config()

        with pytest.raises(Exception) as exc_info:
            manager.initialize(config)

        assert "Engine creation failed" in str(exc_info.value)

    @patch("src.database.connection.create_async_engine")
    def test_async_engine_creation_failure(self, mock_create_async):
        """测试异步引擎创建失败 (覆盖173-179行)"""

        # 模拟异步引擎创建失败
        mock_create_async.side_effect = Exception("Async engine creation failed")

        manager = DatabaseManager()
        config = get_test_config()

        # 先成功创建同步引擎
        with patch("src.database.connection.create_engine"):
            with pytest.raises(Exception):
                manager.initialize(config)

    def test_health_check_with_disconnection_error(self):
        """测试健康检查时的连接断开错误 (覆盖194-195行)"""

        manager = DatabaseManager()

        # 模拟create_session时抛出连接错误，因为health_check调用的是create_session
        with patch.object(
            manager,
            "create_session",
            side_effect=DisconnectionError("Connection lost", None, None),
        ):
            result = manager.health_check()

            assert not result  # 健康检查应该返回False

    def test_health_check_with_general_exception(self):
        """测试健康检查时的一般异常"""

        manager = DatabaseManager()

        # 模拟create_session时抛出一般异常，因为health_check调用的是create_session
        with patch.object(
            manager, "create_session", side_effect=Exception("General error")
        ):
            result = manager.health_check()

            assert not result  # 健康检查应该返回False


class TestDatabaseConnectionAdvancedScenarios:
    """测试数据库连接的高级场景"""

    @patch("src.database.connection.create_engine")
    @patch("src.database.connection.create_async_engine")
    def test_initialize_with_custom_config(self, mock_async_engine, mock_sync_engine):
        """测试使用自定义配置初始化"""

        # 创建模拟引擎
        mock_sync_engine.return_value = Mock()
        mock_async_engine.return_value = Mock()

        manager = DatabaseManager()
        config = get_test_config()
        config.host = "custom-host"
        config.database = "custom-db"

        manager.initialize(config)

        # 验证引擎创建被调用
        mock_sync_engine.assert_called_once()
        mock_async_engine.assert_called_once()

        # 验证配置URL被正确传递
        call_args = mock_sync_engine.call_args[0]
        assert "custom-host" in str(call_args[0])
        assert "custom-db" in str(call_args[0])

    def test_multiple_session_creation(self):
        """测试多次创建会话"""

        with patch("src.database.connection.create_engine") as mock_engine:
            with patch("src.database.connection.create_async_engine"):
                # 模拟会话工厂
                mock_session_factory = Mock()
                mock_session1 = Mock(spec=Session)
                mock_session2 = Mock(spec=Session)
                mock_session_factory.side_effect = [mock_session1, mock_session2]

                mock_engine.return_value = Mock()

                manager = DatabaseManager()
                config = get_test_config()
                manager.initialize(config)

                # 替换会话工厂
                manager._session_factory = mock_session_factory

                # 创建多个会话
                session1 = manager.create_session()
                session2 = manager.create_session()

                assert session1 is mock_session1
                assert session2 is mock_session2
                assert mock_session_factory.call_count == 2

    def test_async_session_creation_after_initialization(self):
        """测试初始化后创建异步会话"""

        with patch("src.database.connection.create_engine"):
            with patch("src.database.connection.create_async_engine"):
                mock_async_session_factory = Mock()
                mock_async_session = Mock(spec=AsyncSession)
                mock_async_session_factory.return_value = mock_async_session

                manager = DatabaseManager()
                config = get_test_config()
                manager.initialize(config)

                # 替换异步会话工厂
                manager._async_session_factory = mock_async_session_factory

                # 创建异步会话
                session = manager.create_async_session()

                assert session is mock_async_session
                mock_async_session_factory.assert_called_once()


class TestDatabaseManagerSingleton:
    """测试数据库管理器单例模式相关功能"""

    def test_get_database_manager_returns_same_instance(self):
        """测试获取数据库管理器返回同一实例"""
        from src.database.connection import get_database_manager

        manager1 = get_database_manager()
        manager2 = get_database_manager()

        assert manager1 is manager2

    def test_database_manager_properties_access(self):
        """测试数据库管理器属性访问 (覆盖242-243, 256-257行)"""

        with patch("src.database.connection.create_engine") as mock_sync_engine:
            with patch(
                "src.database.connection.create_async_engine"
            ) as mock_async_engine:
                mock_sync_instance = Mock()
                mock_async_instance = Mock()
                mock_sync_engine.return_value = mock_sync_instance
                mock_async_engine.return_value = mock_async_instance

                manager = DatabaseManager()
                config = get_test_config()
                manager.initialize(config)

                # 访问同步引擎属性
                sync_engine = manager.sync_engine
                assert sync_engine is mock_sync_instance

                # 访问异步引擎属性
                async_engine = manager.async_engine
                assert async_engine is mock_async_instance

    def test_database_manager_uninitialized_properties(self):
        """测试未初始化时访问引擎属性 (覆盖106-107, 113-114行)"""

        # 创建一个全新的实例，不使用单例
        manager = DatabaseManager()
        # 确保引擎未初始化
        manager._sync_engine = None
        manager._async_engine = None

        # 访问未初始化的同步引擎应该抛出异常
        with pytest.raises(RuntimeError) as exc_info:
            _ = manager.sync_engine

        assert "数据库连接未初始化" in str(exc_info.value)

        # 访问未初始化的异步引擎也应该抛出异常
        with pytest.raises(RuntimeError) as exc_info:
            _ = manager.async_engine

        assert "数据库连接未初始化" in str(exc_info.value)


class TestDatabaseConnectionEdgeCases:
    """测试数据库连接的边界情况"""

    def test_session_context_manager_exception_in_user_code(self):
        """测试用户代码中抛出异常时的会话处理"""

        manager = DatabaseManager()
        mock_session = Mock(spec=Session)

        with patch.object(manager, "create_session", return_value=mock_session):
            with pytest.raises(ValueError):
                with manager.get_session():
                    # 用户代码中抛出异常
                    raise ValueError("User error")

            # 验证会话被正确回滚和关闭
            mock_session.rollback.assert_called_once()
            mock_session.close.assert_called_once()
            # 不应该调用commit
            mock_session.commit.assert_not_called()

    @patch("src.database.connection.logger")
    def test_session_commit_exception_logging(self, mock_logger):
        """测试会话提交异常的日志记录"""

        manager = DatabaseManager()
        mock_session = Mock(spec=Session)
        commit_error = SQLAlchemyError("Commit constraint violation")
        mock_session.commit.side_effect = commit_error

        with patch.object(manager, "create_session", return_value=mock_session):
            with pytest.raises(SQLAlchemyError):
                with manager.get_session():
                    pass

            # 验证错误日志包含具体异常信息
            mock_logger.error.assert_called_once()
            logged_message = mock_logger.error.call_args[0][0]
            assert "数据库操作失败" in logged_message
            assert "Commit constraint violation" in logged_message
