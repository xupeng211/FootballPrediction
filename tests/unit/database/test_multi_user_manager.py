"""
多用户数据库管理器测试
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from src.database.config import DatabaseConfig
from src.database.connection.core.enums import DatabaseRole
from src.database.connection.managers.multi_user_manager import MultiUserDatabaseManager


@pytest.fixture
def multi_user_manager():
    """创建多用户管理器实例"""
    return MultiUserDatabaseManager()


@pytest.fixture
def role_configs():
    """创建角色配置"""
    return {
        DatabaseRole.READER: DatabaseConfig(
            host="localhost",
            port=5432,
            database="test_db",
            username="reader_user",
            password="reader_pass",
            echo=False
        ),
        DatabaseRole.WRITER: DatabaseConfig(
            host="localhost",
            port=5432,
            database="test_db",
            username="writer_user",
            password="writer_pass",
            echo=False
        ),
        DatabaseRole.ADMIN: DatabaseConfig(
            host="localhost",
            port=5432,
            database="test_db",
            username="admin_user",
            password="admin_pass",
            echo=False
        )
    }


class TestMultiUserDatabaseManager:
    """测试多用户数据库管理器"""

    def test_init(self, multi_user_manager):
        """测试初始化"""
        assert multi_user_manager._managers == {}
        assert multi_user_manager._configs == {}
        assert multi_user_manager._default_role == DatabaseRole.READER

    @pytest.mark.asyncio
    async def test_initialize_role_connections(self, multi_user_manager, role_configs):
        """测试初始化角色连接"""
        with patch('src.database.connection.managers.database_manager.DatabaseManager') as mock_db_manager_class:
            # 设置模拟
            mock_manager = MagicMock()
            mock_manager.health_check.return_value = {"status": "healthy"}
            mock_db_manager_class.return_value = mock_manager

            # 初始化连接
            await multi_user_manager.initialize_role_connections(role_configs)

            # 验证
            assert len(multi_user_manager._managers) == 3
            assert DatabaseRole.READER in multi_user_manager._managers
            assert DatabaseRole.WRITER in multi_user_manager._managers
            assert DatabaseRole.ADMIN in multi_user_manager._managers

            # 验证每个角色都有对应的配置
            for role in role_configs:
                assert role in multi_user_manager._configs
                assert multi_user_manager._configs[role] == role_configs[role]

    def test_get_manager(self, multi_user_manager, role_configs):
        """测试获取管理器"""
        # 手动添加管理器
        mock_manager = MagicMock()
        multi_user_manager._managers[DatabaseRole.READER] = mock_manager

        # 获取管理器
        manager = multi_user_manager.get_manager(DatabaseRole.READER)
        assert manager == mock_manager

        # 使用默认角色
        manager = multi_user_manager.get_manager()
        assert manager == mock_manager

        # 角色未初始化
        with pytest.raises(ValueError, match="未初始化"):
            multi_user_manager.get_manager(DatabaseRole.WRITER)

    def test_get_session(self, multi_user_manager):
        """测试获取会话"""
        # 设置模拟管理器和会话
        mock_manager = MagicMock()
        mock_session = MagicMock()
        mock_manager.get_session.return_value.__enter__.return_value = mock_session
        multi_user_manager._managers[DatabaseRole.READER] = mock_manager

        # 获取会话
        with multi_user_manager.get_session(DatabaseRole.READER) as session:
            assert session == mock_session

        # 验证调用
        mock_manager.get_session.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_async_session(self, multi_user_manager):
        """测试获取异步会话"""
        # 设置模拟管理器和会话
        mock_manager = MagicMock()
        mock_session = AsyncMock()
        mock_manager.get_async_session.return_value.__aenter__.return_value = mock_session
        multi_user_manager._managers[DatabaseRole.READER] = mock_manager

        # 获取会话
        async with multi_user_manager.get_async_session(DatabaseRole.READER) as session:
            assert session == mock_session

        # 验证调用
        mock_manager.get_async_session.assert_called_once()

    def test_set_default_role(self, multi_user_manager):
        """测试设置默认角色"""
        # 添加管理器
        mock_manager = MagicMock()
        multi_user_manager._managers[DatabaseRole.WRITER] = mock_manager

        # 设置默认角色
        multi_user_manager.set_default_role(DatabaseRole.WRITER)

        # 验证
        assert multi_user_manager._default_role == DatabaseRole.WRITER

        # 角色未初始化
        with pytest.raises(ValueError, match="未初始化"):
            multi_user_manager.set_default_role(DatabaseRole.ADMIN)

    def test_get_default_role(self, multi_user_manager):
        """测试获取默认角色"""
        assert multi_user_manager.get_default_role() == DatabaseRole.READER

        # 修改默认角色
        multi_user_manager._default_role = DatabaseRole.WRITER
        assert multi_user_manager.get_default_role() == DatabaseRole.WRITER

    def test_check_permission(self, multi_user_manager):
        """测试检查权限"""
        # 添加管理器
        mock_manager = MagicMock()
        multi_user_manager._managers[DatabaseRole.READER] = mock_manager

        # 检查权限
        assert multi_user_manager.check_permission(DatabaseRole.READER, "select") is True
        assert multi_user_manager.check_permission(DatabaseRole.READER, "insert") is False

        # 角色未初始化
        assert multi_user_manager.check_permission(DatabaseRole.WRITER, "select") is False

    def test_get_role_config(self, multi_user_manager, role_configs):
        """测试获取角色配置"""
        # 添加配置
        multi_user_manager._configs = role_configs

        # 获取配置
        config = multi_user_manager.get_role_config(DatabaseRole.READER)
        assert config == role_configs[DatabaseRole.READER]

        # 角色不存在
        config = multi_user_manager.get_role_config(DatabaseRole.READER)
        assert config == role_configs[DatabaseRole.READER]

    def test_list_initialized_roles(self, multi_user_manager):
        """测试列出已初始化的角色"""
        # 初始为空
        assert multi_user_manager.list_initialized_roles() == []

        # 添加角色
        multi_user_manager._managers[DatabaseRole.READER] = MagicMock()
        multi_user_manager._managers[DatabaseRole.WRITER] = MagicMock()

        # 验证
        roles = multi_user_manager.list_initialized_roles()
        assert DatabaseRole.READER in roles
        assert DatabaseRole.WRITER in roles
        assert len(roles) == 2

    def test_close_all_connections(self, multi_user_manager):
        """测试关闭所有连接"""
        # 添加模拟管理器
        mock_manager1 = MagicMock()
        mock_manager2 = MagicMock()
        multi_user_manager._managers = {
            DatabaseRole.READER: mock_manager1,
            DatabaseRole.WRITER: mock_manager2
        }

        # 关闭连接
        multi_user_manager.close_all_connections()

        # 验证
        mock_manager1.close.assert_called_once()
        mock_manager2.close.assert_called_once()
        assert len(multi_user_manager._managers) == 0
        assert len(multi_user_manager._configs) == 0

    def test_get_all_health_status(self, multi_user_manager):
        """测试获取所有健康状态"""
        # 添加模拟管理器
        mock_manager1 = MagicMock()
        mock_manager1.health_check.return_value = {"status": "healthy"}
        mock_manager2 = MagicMock()
        mock_manager2.health_check.return_value = {"status": "degraded"}

        multi_user_manager._managers = {
            DatabaseRole.READER: mock_manager1,
            DatabaseRole.WRITER: mock_manager2
        }

        # 获取健康状态
        health_status = multi_user_manager.get_all_health_status()

        # 验证
        assert health_status["default_role"] == DatabaseRole.READER.value
        assert "roles" in health_status
        assert health_status["roles"]["reader"]["status"] == "healthy"
        assert health_status["roles"]["writer"]["status"] == "degraded"
        assert health_status["overall_status"] == "degraded"

    def test_get_connection_statistics(self, multi_user_manager):
        """测试获取连接统计"""
        # 添加模拟管理器
        mock_manager = MagicMock()
        mock_manager.get_pool_status.return_value = {
            "sync": {"size": 5},
            "async": {"size": 10}
        }
        multi_user_manager._managers[DatabaseRole.READER] = mock_manager

        # 获取统计信息
        stats = multi_user_manager.get_connection_statistics()

        # 验证
        assert "roles" in stats
        assert "total_connections" in stats
        assert stats["total_connections"] == 15  # 5 + 10
        assert stats["roles"]["reader"]["sync"]["size"] == 5
        assert stats["roles"]["reader"]["async"]["size"] == 10

    def test_database_role_permissions(self):
        """测试数据库角色权限"""
        # 读者权限
        reader_permissions = DatabaseRole.get_permissions(DatabaseRole.READER)
        assert reader_permissions["select"] is True
        assert reader_permissions["insert"] is False
        assert reader_permissions["update"] is False
        assert reader_permissions["delete"] is False
        assert reader_permissions["create"] is False
        assert reader_permissions["drop"] is False

        # 写者权限
        writer_permissions = DatabaseRole.get_permissions(DatabaseRole.WRITER)
        assert writer_permissions["select"] is True
        assert writer_permissions["insert"] is True
        assert writer_permissions["update"] is True
        assert writer_permissions["delete"] is False
        assert writer_permissions["create"] is False
        assert writer_permissions["drop"] is False

        # 管理员权限
        admin_permissions = DatabaseRole.get_permissions(DatabaseRole.ADMIN)
        assert admin_permissions["select"] is True
        assert admin_permissions["insert"] is True
        assert admin_permissions["update"] is True
        assert admin_permissions["delete"] is True
        assert admin_permissions["create"] is True
        assert admin_permissions["drop"] is True

    def test_database_role_has_permission(self):
        """测试数据库角色权限检查"""
        # 读者
        reader_role = DatabaseRole.READER
        assert reader_role.has_permission("select") is True
        assert reader_role.has_permission("insert") is False

        # 写者
        writer_role = DatabaseRole.WRITER
        assert writer_role.has_permission("select") is True
        assert writer_role.has_permission("insert") is True
        assert writer_role.has_permission("delete") is False

        # 管理员
        admin_role = DatabaseRole.ADMIN
        assert admin_role.has_permission("drop") is True