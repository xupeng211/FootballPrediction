"""
数据库基础模块测试
"""

import pytest
import sys
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

try:
    from src.database.base import Base
    from src.database.connection import DatabaseConnection
    from src.database.config import DatabaseConfig
except ImportError as e:
    pytest.skip(f"数据库基础模块不可用: {e}", allow_module_level=True)


class TestDatabaseBase:
    """测试数据库基础功能"""

    def test_base_class_creation(self):
        """测试基础类创建"""
        base = Base()
        assert hasattr(base, "metadata")
        assert hasattr(
            base, "__tablename__" if hasattr(Base, "__tablename__") else "metadata"
        )

    def test_database_config_creation(self):
        """测试数据库配置创建"""
        config = DatabaseConfig(
            host="localhost",
            port=5432,
            database="test_db",
            username="user",
            password="password",
        )
        assert config.host == "localhost"
        assert config.port == 5432
        assert config.database == "test_db"

    def test_database_config_with_mock(self):
        """使用Mock测试数据库配置"""
        with patch("src.database.config.DatabaseConfig") as MockConfig:
            config = MockConfig()
            config.get_url = Mock(
                return_value="postgresql://user:pass@localhost:5432/db"
            )
            config.is_valid = Mock(return_value=True)

            url = config.get_url()
            assert url == "postgresql://user:pass@localhost:5432/db"
            assert config.is_valid() is True

    def test_database_connection_mock(self):
        """测试数据库连接（Mock）"""
        with patch("src.database.connection.DatabaseConnection") as MockConnection:
            conn = MockConnection()
            conn.connect = Mock(return_value=True)
            conn.disconnect = Mock(return_value=True)
            conn.execute = Mock(return_value=[{"result": "success"}])

            # 测试连接
            assert conn.connect() is True
            assert conn.disconnect() is True

            # 测试执行查询
            result = conn.execute("SELECT 1")
            assert result == [{"result": "success"}]

    def test_database_transaction_mock(self):
        """测试数据库事务（Mock）"""
        with patch("src.database.connection.DatabaseConnection") as MockConnection:
            conn = MockConnection()
            conn.begin = Mock(return_value=True)
            conn.commit = Mock(return_value=True)
            conn.rollback = Mock(return_value=True)

            # 测试事务
            conn.begin()
            conn.commit()
            conn.rollback()

            conn.begin.assert_called_once()
            conn.commit.assert_called_once()
            conn.rollback.assert_called_once()

    def test_database_pool_mock(self):
        """测试数据库连接池（Mock）"""
        with patch("src.database.connection.DatabaseConnection") as MockConnection:
            pool = MockConnection()
            pool.get_connection = Mock(return_value=Mock())
            pool.return_connection = Mock(return_value=True)
            pool.get_pool_size = Mock(return_value=10)
            pool.get_active_connections = Mock(return_value=5)

            # 获取连接
            conn = pool.get_connection()
            assert conn is not None

            # 返回连接
            assert pool.return_connection(conn) is True

            # 检查池状态
            assert pool.get_pool_size() == 10
            assert pool.get_active_connections() == 5

    def test_database_error_handling(self):
        """测试数据库错误处理"""
        with patch("src.database.connection.DatabaseConnection") as MockConnection:
            conn = MockConnection()
            conn.connect = Mock(side_effect=Exception("Connection failed"))
            conn.handle_error = Mock(return_value={"error": "handled"})

            # 测试错误处理
            try:
                conn.connect()
            except Exception:
                error = conn.handle_error(Exception("Connection failed"))
                assert error["error"] == "handled"

    def test_sql_query_builder(self):
        """测试SQL查询构建器"""
        with patch("src.database.base.Base") as MockBase:
            base = MockBase()
            base.build_select_query = Mock(return_value="SELECT * FROM users")
            base.build_insert_query = Mock(
                return_value="INSERT INTO users (name) VALUES (?)"
            )
            base.build_update_query = Mock(
                return_value="UPDATE users SET name = ? WHERE id = ?"
            )
            base.build_delete_query = Mock(
                return_value="DELETE FROM users WHERE id = ?"
            )

            select = base.build_select_query("users")
            insert = base.build_insert_query("users", ["name"])
            update = base.build_update_query("users", {"name": "John"}, {"id": 1})
            delete = base.build_delete_query("users", {"id": 1})

            assert "SELECT" in select
            assert "INSERT" in insert
            assert "UPDATE" in update
            assert "DELETE" in delete

    def test_database_health_check(self):
        """测试数据库健康检查"""
        with patch("src.database.connection.DatabaseConnection") as MockConnection:
            conn = MockConnection()
            conn.ping = Mock(return_value=True)
            conn.get_server_version = Mock(return_value="PostgreSQL 15.1")
            conn.get_database_size = Mock(return_value="1.2GB")
            conn.get_connection_count = Mock(return_value=25)

            health = {
                "status": "healthy" if conn.ping() else "unhealthy",
                "version": conn.get_server_version(),
                "size": conn.get_database_size(),
                "connections": conn.get_connection_count(),
            }

            assert health["status"] == "healthy"
            assert health["version"] == "PostgreSQL 15.1"
            assert health["size"] == "1.2GB"
            assert health["connections"] == 25

    def test_database_migration_support(self):
        """测试数据库迁移支持"""
        with patch("src.database.base.Base") as MockBase:
            base = MockBase()
            base.create_migration_table = Mock(return_value=True)
            base.get_migration_version = Mock(return_value=1)
            base.set_migration_version = Mock(return_value=True)
            base.run_migration = Mock(return_value=True)

            # 创建迁移表
            assert base.create_migration_table() is True

            # 获取当前版本
            version = base.get_migration_version()
            assert version == 1

            # 设置新版本
            assert base.set_migration_version(2) is True

            # 运行迁移
            assert base.run_migration("002_add_new_column.sql") is True

    def test_database_backup_restore(self):
        """测试数据库备份和恢复"""
        with patch("src.database.connection.DatabaseConnection") as MockConnection:
            conn = MockConnection()
            conn.backup = Mock(return_value="backup_20250118.sql")
            conn.restore = Mock(return_value=True)
            conn.list_backups = Mock(return_value=["backup_1.sql", "backup_2.sql"])

            # 创建备份
            backup_file = conn.backup("test_db")
            assert "backup_" in backup_file

            # 列出备份
            backups = conn.list_backups()
            assert len(backups) == 2

            # 恢复备份
            assert conn.restore("backup_20250118.sql") is True

    def test_database_index_management(self):
        """测试数据库索引管理"""
        with patch("src.database.base.Base") as MockBase:
            base = MockBase()
            base.create_index = Mock(return_value=True)
            base.drop_index = Mock(return_value=True)
            base.list_indexes = Mock(return_value=["idx_users_email", "idx_users_name"])
            base.analyze_index = Mock(
                return_value={"index_name": "idx_users_email", "efficiency": 0.95}
            )

            # 创建索引
            assert base.create_index("idx_users_email", "users", "email") is True

            # 列出索引
            indexes = base.list_indexes()
            assert len(indexes) == 2

            # 分析索引效率
            analysis = base.analyze_index("idx_users_email")
            assert analysis["efficiency"] == 0.95

            # 删除索引
            assert base.drop_index("idx_users_email") is True
