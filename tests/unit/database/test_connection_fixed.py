"""
数据库连接模块测试（修复版）
测试DatabaseManager和MultiUserDatabaseManager的功能
"""

import pytest
from unittest.mock import MagicMock, AsyncMock, patch


from src.database.connection import (
    DatabaseManager,
    MultiUserDatabaseManager,
    DatabaseRole,
    DATABASE_RETRY_CONFIG,
    get_database_manager,
    get_multi_user_database_manager,
    initialize_database,
    initialize_multi_user_database,
    initialize_test_database,
    get_async_db_session,
    get_reader_session,
    get_writer_session,
    get_admin_session,
    get_async_reader_session,
    get_async_writer_session,
    get_async_admin_session,
    get_session,
    get_async_session,
)
from src.database.config import DatabaseConfig


@pytest.mark.unit
class TestDatabaseRole:
    """数据库角色枚举测试"""

    def test_database_role_values(self):
        """测试数据库角色枚举值"""
        assert DatabaseRole.READER.value == "reader"
        assert DatabaseRole.WRITER.value == "writer"
        assert DatabaseRole.ADMIN.value == "admin"

    def test_database_role_is_string_enum(self):
        """测试数据库角色是字符串枚举"""
        assert isinstance(DatabaseRole.READER, str)
        assert DatabaseRole.READER == "reader"


@pytest.mark.unit
class TestDatabaseManager:
    """数据库管理器测试"""

    @pytest.fixture
    def mock_config(self):
        """创建模拟配置"""
        return DatabaseConfig(
            host="localhost",
            port=5432,
            database="test_db",
            username="test_user",
            password="test_password",
            echo=False,
            pool_size=5,
            max_overflow=10,
            pool_timeout=30,
            pool_recycle=3600,
        )

    @pytest.fixture
    def db_manager(self):
        """创建数据库管理器实例"""
        manager = DatabaseManager()
        manager.logger = MagicMock()
        return manager

    # === 单例模式测试 ===

    def test_singleton_pattern(self, db_manager):
        """测试单例模式"""
        # 创建另一个实例
        manager2 = DatabaseManager()
        assert manager2 is db_manager

    # === 初始化测试 ===

    def test_initialize_with_config(self, db_manager, mock_config):
        """测试使用配置初始化"""
        with patch("src.database.connection.create_engine") as mock_create_engine:
            mock_engine = MagicMock()
            mock_create_engine.return_value = mock_engine

            with patch(
                "src.database.connection.create_async_engine"
            ) as mock_create_async_engine:
                mock_async_engine = MagicMock()
                mock_create_async_engine.return_value = mock_async_engine

                db_manager.initialize(mock_config)

                assert db_manager._config is not None
                assert db_manager._sync_engine is not None
                assert db_manager._async_engine is not None
                mock_create_engine.assert_called_once()
                mock_create_async_engine.assert_called_once()

    def test_initialize_without_config(self, db_manager):
        """测试不使用配置初始化"""
        with patch("src.database.connection.get_database_config") as mock_get_config:
            mock_config = MagicMock()
            mock_get_config.return_value = mock_config

            with patch("src.database.connection.create_engine") as mock_create_engine:
                mock_engine = MagicMock()
                mock_create_engine.return_value = mock_engine

                with patch(
                    "src.database.connection.create_async_engine"
                ) as mock_create_async_engine:
                    mock_async_engine = MagicMock()
                    mock_create_async_engine.return_value = mock_async_engine

                    db_manager.initialize()

                    mock_get_config.assert_called_once()
                    assert db_manager._config is not None

    # === 属性测试 ===

    def test_get_config(self, db_manager, mock_config):
        """测试获取配置"""
        db_manager._config = mock_config
        config = db_manager.get_config()
        assert config is mock_config

    def test_sync_engine_property(self, db_manager):
        """测试同步引擎属性"""
        mock_engine = MagicMock()
        db_manager._sync_engine = mock_engine
        assert db_manager.sync_engine is mock_engine

    def test_async_engine_property(self, db_manager):
        """测试异步引擎属性"""
        mock_engine = MagicMock()
        db_manager._async_engine = mock_engine
        assert db_manager.async_engine is mock_engine

    def test_engines_not_initialized(self, db_manager):
        """测试引擎未初始化时的行为"""
        db_manager._sync_engine = None
        db_manager._async_engine = None

        with pytest.raises(RuntimeError, match="数据库连接未初始化"):
            _ = db_manager.sync_engine

        with pytest.raises(RuntimeError, match="数据库连接未初始化"):
            _ = db_manager.async_engine

    # === 会话创建测试 ===

    def test_create_session(self, db_manager):
        """测试创建会话"""
        mock_engine = MagicMock()
        mock_session = MagicMock()
        mock_session_factory = MagicMock(return_value=mock_session)
        mock_engine.sessionmaker.return_value = mock_session_factory

        db_manager._sync_engine = mock_engine
        db_manager._sync_session_factory = mock_session_factory

        session = db_manager.create_session()
        assert session is mock_session

    def test_create_async_session(self, db_manager):
        """测试创建异步会话"""
        mock_engine = MagicMock()
        mock_session = MagicMock()
        mock_session_factory = MagicMock(return_value=mock_session)
        mock_engine.async_sessionmaker.return_value = mock_session_factory

        db_manager._async_engine = mock_engine
        db_manager._async_session_factory = mock_session_factory

        session = db_manager.create_async_session()
        assert session is mock_session

    def test_create_session_not_initialized(self, db_manager):
        """测试引擎未初始化时创建会话"""
        db_manager._sync_engine = None

        with pytest.raises(RuntimeError, match="同步引擎未初始化"):
            db_manager.create_session()

        db_manager._async_engine = None

        with pytest.raises(RuntimeError, match="异步引擎未初始化"):
            db_manager.create_async_session()

    # === 会话管理器测试 ===

    def test_get_session(self, db_manager):
        """测试获取会话上下文管理器"""
        mock_engine = MagicMock()
        mock_session = MagicMock()
        mock_session_factory = MagicMock(return_value=mock_session)
        mock_engine.sessionmaker.return_value = mock_session_factory

        db_manager._sync_engine = mock_engine
        db_manager._sync_session_factory = mock_session_factory

        # 使用patch来模拟sessionmaker
        with patch("src.database.connection.sessionmaker") as mock_sessionmaker_class:
            mock_sessionmaker_class.return_value = mock_session_factory

            with db_manager.get_session() as session:
                assert session is mock_session

    @pytest.mark.asyncio
    async def test_get_async_session(self, db_manager):
        """测试获取异步会话上下文管理器"""
        mock_engine = MagicMock()
        mock_session = MagicMock()
        mock_session_factory = MagicMock(return_value=mock_session)
        mock_engine.async_sessionmaker.return_value = mock_session_factory

        db_manager._async_engine = mock_engine
        db_manager._async_session_factory = mock_session_factory

        # 使用patch来模拟async_sessionmaker
        with patch(
            "src.database.connection.async_sessionmaker"
        ) as mock_async_sessionmaker_class:
            mock_async_sessionmaker_class.return_value = mock_session_factory

            async with db_manager.get_async_session() as session:
                assert session is mock_session

    # === 数据库操作测试 ===

    @pytest.mark.asyncio
    async def test_get_match(self, db_manager):
        """测试获取比赛信息"""
        mock_session = MagicMock()
        mock_result = MagicMock()
        mock_result.fetchone.return_value = {
            "id": 123,
            "home_team_id": 1,
            "away_team_id": 2,
            "home_score": 2,
            "away_score": 1,
        }
        mock_session.execute.return_value = mock_result

        with patch.object(db_manager, "get_session") as mock_get_session:
            mock_get_session.return_value.__enter__.return_value = mock_session

            result = await db_manager.get_match(123)

            assert result is not None
            assert result["id"] == 123
            assert result["home_score"] == 2

    @pytest.mark.asyncio
    async def test_get_match_not_found(self, db_manager):
        """测试获取不存在的比赛"""
        mock_session = MagicMock()
        mock_result = MagicMock()
        mock_result.fetchone.return_value = None
        mock_session.execute.return_value = mock_result

        with patch.object(db_manager, "get_session") as mock_get_session:
            mock_get_session.return_value.__enter__.return_value = mock_session

            result = await db_manager.get_match(999)

            assert result is None

    @pytest.mark.asyncio
    async def test_update_match(self, db_manager):
        """测试更新比赛信息"""
        mock_session = MagicMock()
        mock_session.commit.return_value = None
        mock_session.execute.return_value = MagicMock(rowcount=1)

        with patch.object(db_manager, "get_session") as mock_get_session:
            mock_get_session.return_value.__enter__.return_value = mock_session

            data = {"home_score": 3, "away_score": 1}
            result = await db_manager.update_match(123, data)

            assert result is True
            mock_session.execute.assert_called_once()
            mock_session.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_update_match_not_found(self, db_manager):
        """测试更新不存在的比赛"""
        mock_session = MagicMock()
        mock_session.commit.return_value = None
        mock_session.execute.return_value = MagicMock(rowcount=0)

        with patch.object(db_manager, "get_session") as mock_get_session:
            mock_get_session.return_value.__enter__.return_value = mock_session

            data = {"home_score": 3, "away_score": 1}
            result = await db_manager.update_match(999, data)

            assert result is False

    @pytest.mark.asyncio
    async def test_get_prediction(self, db_manager):
        """测试获取预测信息"""
        mock_session = MagicMock()
        mock_result = MagicMock()
        mock_result.fetchone.return_value = {
            "id": 1,
            "match_id": 123,
            "predicted_result": "home_win",
            "confidence": 0.85,
        }
        mock_session.execute.return_value = mock_result

        with patch.object(db_manager, "get_session") as mock_get_session:
            mock_get_session.return_value.__enter__.return_value = mock_session

            result = await db_manager.get_prediction(123)

            assert result is not None
            assert result["match_id"] == 123
            assert result["predicted_result"] == "home_win"

    # === 健康检查测试 ===

    def test_health_check_healthy(self, db_manager):
        """测试健康检查 - 健康"""
        mock_engine = MagicMock()
        mock_connection = MagicMock()
        mock_connection.connection.ping.return_value = True
        mock_engine.connect.return_value.__enter__.return_value = mock_connection
        db_manager._sync_engine = mock_engine

        result = db_manager.health_check()

        assert result is True

    def test_health_check_unhealthy(self, db_manager):
        """测试健康检查 - 不健康"""
        mock_engine = MagicMock()
        mock_connection = MagicMock()
        mock_connection.connection.ping.side_effect = Exception("Connection failed")
        mock_engine.connect.return_value.__enter__.return_value = mock_connection
        db_manager._sync_engine = mock_engine

        result = db_manager.health_check()

        assert result is False

    def test_health_check_no_engine(self, db_manager):
        """测试健康检查 - 无引擎"""
        db_manager._sync_engine = None

        result = db_manager.health_check()

        assert result is False

    @pytest.mark.asyncio
    async def test_async_health_check_healthy(self, db_manager):
        """测试异步健康检查 - 健康"""
        mock_engine = MagicMock()
        mock_connection = MagicMock()
        mock_connection.connection.ping = AsyncMock(return_value=True)
        mock_engine.connect.return_value.__aenter__.return_value = mock_connection
        db_manager._async_engine = mock_engine

        result = await db_manager.async_health_check()

        assert result is True

    @pytest.mark.asyncio
    async def test_health_check_with_retry_healthy(self, db_manager):
        """测试带重试的健康检查 - 健康"""
        with patch.object(db_manager, "async_health_check") as mock_health_check:
            mock_health_check.return_value = True

            result = await db_manager.health_check_with_retry()

            assert result is True
            mock_health_check.assert_called_once()

    @pytest.mark.asyncio
    async def test_health_check_with_retry_unhealthy(self, db_manager):
        """测试带重试的健康检查 - 不健康"""
        with patch.object(db_manager, "async_health_check") as mock_health_check:
            mock_health_check.return_value = False

            result = await db_manager.health_check_with_retry()

            assert result is False
            mock_health_check.assert_called_once()

    def test_health_check_sync_with_retry_healthy(self, db_manager):
        """测试同步带重试的健康检查 - 健康"""
        with patch.object(db_manager, "health_check") as mock_health_check:
            mock_health_check.return_value = True

            result = db_manager.health_check_sync_with_retry()

            assert result is True
            mock_health_check.assert_called_once()

    # === 关闭测试 ===

    @pytest.mark.asyncio
    async def test_close(self, db_manager):
        """测试关闭连接"""
        mock_sync_engine = MagicMock()
        mock_async_engine = MagicMock()
        db_manager._sync_engine = mock_sync_engine
        db_manager._async_engine = mock_async_engine

        await db_manager.close()

        mock_sync_engine.dispose.assert_called_once()
        mock_async_engine.dispose.assert_called_once()
        assert db_manager._sync_engine is None
        assert db_manager._async_engine is None


@pytest.mark.unit
class TestMultiUserDatabaseManager:
    """多用户数据库管理器测试"""

    @pytest.fixture
    def multi_db_manager(self):
        """创建多用户数据库管理器实例"""
        manager = MultiUserDatabaseManager()
        manager.logger = MagicMock()
        return manager

    # === 单例模式测试 ===

    def test_singleton_pattern(self, multi_db_manager):
        """测试单例模式"""
        manager2 = MultiUserDatabaseManager()
        assert manager2 is multi_db_manager

    # === 初始化测试 ===

    def test_initialize(self, multi_db_manager):
        """测试初始化"""
        with patch("src.database.connection.get_database_config") as mock_get_config:
            mock_base_config = MagicMock()
            mock_get_config.return_value = mock_base_config

            # Mock每个角色的配置
            with patch.object(
                multi_db_manager, "_create_config_for_role"
            ) as mock_create_config:
                mock_reader_config = MagicMock()
                mock_writer_config = MagicMock()
                mock_admin_config = MagicMock()
                mock_create_config.side_effect = [
                    mock_reader_config,
                    mock_writer_config,
                    mock_admin_config,
                ]

                # Mock每个角色的管理器
                with patch(
                    "src.database.connection.DatabaseManager"
                ) as mock_manager_class:
                    mock_manager = MagicMock()
                    mock_manager_class.return_value = mock_manager

                    multi_db_manager.initialize()

                    assert mock_manager_class.call_count == 3

    # === 管理器获取测试 ===

    def test_get_manager(self, multi_db_manager):
        """测试获取管理器"""
        mock_manager = MagicMock()
        multi_db_manager._managers[DatabaseRole.READER] = mock_manager

        manager = multi_db_manager.get_manager(DatabaseRole.READER)
        assert manager is mock_manager

    def test_get_manager_not_initialized(self, multi_db_manager):
        """测试获取未初始化的管理器"""
        with pytest.raises(ValueError, match="角色 reader 的管理器未初始化"):
            multi_db_manager.get_manager(DatabaseRole.READER)

    # === 会话管理测试 ===

    def test_get_session(self, multi_db_manager):
        """测试获取会话"""
        mock_manager = MagicMock()
        mock_session = MagicMock()
        mock_manager.get_session.return_value.__enter__.return_value = mock_session
        multi_db_manager._managers[DatabaseRole.READER] = mock_manager

        with multi_db_manager.get_session(DatabaseRole.READER) as session:
            assert session is mock_session

    @pytest.mark.asyncio
    async def test_get_async_session(self, multi_db_manager):
        """测试获取异步会话"""
        mock_manager = MagicMock()
        mock_session = MagicMock()
        mock_manager.get_async_session.return_value.__aenter__.return_value = (
            mock_session
        )
        multi_db_manager._managers[DatabaseRole.READER] = mock_manager

        async with multi_db_manager.get_async_session(DatabaseRole.READER) as session:
            assert session is mock_session

    # === 偃康检查测试 ===

    def test_health_check(self, multi_db_manager):
        """测试健康检查"""
        mock_manager1 = MagicMock()
        mock_manager2 = MagicMock()
        mock_manager1.health_check.return_value = True
        mock_manager2.health_check.return_value = False
        multi_db_manager._managers[DatabaseRole.READER] = mock_manager1
        multi_db_manager._managers[DatabaseRole.WRITER] = mock_manager2

        health = multi_db_manager.health_check()

        assert health["reader"] is True
        assert health["writer"] is False

    def test_health_check_no_role(self, multi_db_manager):
        """测试健康检查（无角色）"""
        health = multi_db_manager.health_check()

        expected = {"reader": False, "writer": False, "admin": False}
        assert health == expected

    @pytest.mark.asyncio
    async def test_async_health_check(self, multi_db_manager):
        """测试异步健康检查"""
        mock_manager1 = MagicMock()
        mock_manager2 = MagicMock()
        mock_manager1.async_health_check = AsyncMock(return_value=True)
        mock_manager2.async_health_check = AsyncMock(return_value=False)
        multi_db_manager._managers[DatabaseRole.READER] = mock_manager1
        multi_db_manager._managers[DatabaseRole.WRITER] = mock_manager2

        health = await multi_db_manager.async_health_check()

        assert health["reader"] is True
        assert health["writer"] is False

    # === 关闭测试 ===

    @pytest.mark.asyncio
    async def test_close(self, multi_db_manager):
        """测试关闭连接"""
        mock_manager1 = MagicMock()
        mock_manager2 = MagicMock()
        mock_manager1.close = AsyncMock()
        mock_manager2.close = AsyncMock()
        multi_db_manager._managers[DatabaseRole.READER] = mock_manager1
        multi_db_manager._managers[DatabaseRole.WRITER] = mock_manager2

        await multi_db_manager.close()

        mock_manager1.close.assert_called_once()
        mock_manager2.close.assert_called_once()

    # === 权限测试 ===

    def test_get_role_permissions(self, multi_db_manager):
        """测试获取角色权限"""
        permissions = multi_db_manager.get_role_permissions(DatabaseRole.READER)
        assert "username" in permissions
        assert "password" in permissions
        assert "schema" in permissions


@pytest.mark.unit
class TestModuleFunctions:
    """模块函数测试"""

    def test_get_database_manager(self):
        """测试获取数据库管理器"""
        manager = get_database_manager()
        assert isinstance(manager, DatabaseManager)

    def test_get_multi_user_database_manager(self):
        """测试获取多用户数据库管理器"""
        manager = get_multi_user_database_manager()
        assert isinstance(manager, MultiUserDatabaseManager)

    def test_initialize_database(self):
        """测试初始化数据库"""
        with patch("src.database.connection.get_database_manager") as mock_get_manager:
            mock_manager = MagicMock()
            mock_get_manager.return_value = mock_manager

            initialize_database()

            mock_manager.initialize.assert_called_once()

    def test_initialize_multi_user_database(self):
        """测试初始化多用户数据库"""
        with patch(
            "src.database.connection.get_multi_user_database_manager"
        ) as mock_get_manager:
            mock_manager = MagicMock()
            mock_get_manager.return_value = mock_manager

            initialize_multi_user_database()

            mock_manager.initialize.assert_called_once()

    def test_initialize_test_database(self):
        """测试初始化测试数据库"""
        with patch("src.database.connection.get_database_manager") as mock_get_manager:
            mock_manager = MagicMock()
            mock_get_manager.return_value = mock_manager

            initialize_test_database()

            mock_manager.initialize.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_async_db_session(self):
        """测试获取异步数据库会话"""
        with patch("src.database.connection.get_database_manager") as mock_get_manager:
            mock_manager = MagicMock()
            mock_session = MagicMock()
            mock_manager.get_async_session.return_value.__aenter__.return_value = (
                mock_session
            )
            mock_get_manager.return_value = mock_manager

            async with get_async_db_session() as session:
                assert session is mock_session

    def test_get_reader_session(self):
        """测试获取读者会话"""
        with patch(
            "src.database.connection.get_multi_user_database_manager"
        ) as mock_get_manager:
            mock_manager = MagicMock()
            mock_session = MagicMock()
            mock_manager.get_session.return_value.__enter__.return_value = mock_session
            mock_get_manager.return_value = mock_manager

            with get_reader_session() as session:
                assert session is mock_session

    def test_get_writer_session(self):
        """测试获取写者会话"""
        with patch(
            "src.database.connection.get_multi_user_database_manager"
        ) as mock_get_manager:
            mock_manager = MagicMock()
            mock_session = MagicMock()
            mock_manager.get_session.return_value.__enter__.return_value = mock_session
            mock_get_manager.return_value = mock_manager

            with get_writer_session() as session:
                assert session is mock_session

    def test_get_admin_session(self):
        """测试获取管理员会话"""
        with patch(
            "src.database.connection.get_multi_user_database_manager"
        ) as mock_get_manager:
            mock_manager = MagicMock()
            mock_session = MagicMock()
            mock_manager.get_session.return_value.__enter__.return_value = mock_session
            mock_get_manager.return_value = mock_manager

            with get_admin_session() as session:
                assert session is mock_session

    @pytest.mark.asyncio
    async def test_get_async_reader_session(self):
        """测试获取异步读者会话"""
        with patch(
            "src.database.connection.get_multi_user_database_manager"
        ) as mock_get_manager:
            mock_manager = MagicMock()
            mock_session = MagicMock()
            mock_manager.get_async_session.return_value.__aenter__.return_value = (
                mock_session
            )
            mock_get_manager.return_value = mock_manager

            async with get_async_reader_session() as session:
                assert session is mock_session

    @pytest.mark.asyncio
    async def test_get_async_writer_session(self):
        """测试获取异步写者会话"""
        with patch(
            "src.database.connection.get_multi_user_database_manager"
        ) as mock_get_manager:
            mock_manager = MagicMock()
            mock_session = MagicMock()
            mock_manager.get_async_session.return_value.__aenter__.return_value = (
                mock_session
            )
            mock_get_manager.return_value = mock_manager

            async with get_async_writer_session() as session:
                assert session is mock_session

    @pytest.mark.asyncio
    async def test_get_async_admin_session(self):
        """测试获取异步管理员会话"""
        with patch(
            "src.database.connection.get_multi_user_database_manager"
        ) as mock_get_manager:
            mock_manager = MagicMock()
            mock_session = MagicMock()
            mock_manager.get_async_session.return_value.__aenter__.return_value = (
                mock_session
            )
            mock_get_manager.return_value = mock_manager

            async with get_async_admin_session() as session:
                assert session is mock_session

    def test_get_session_with_role(self):
        """测试获取指定角色的会话"""
        with patch(
            "src.database.connection.get_multi_user_database_manager"
        ) as mock_get_manager:
            mock_manager = MagicMock()
            mock_session = MagicMock()
            mock_manager.get_session.return_value.__enter__.return_value = mock_session
            mock_get_manager.return_value = mock_manager

            with get_session(role=DatabaseRole.READER) as session:
                assert session is mock_session

    @pytest.mark.asyncio
    async def test_get_async_session_with_role(self):
        """测试获取指定角色的异步会话"""
        with patch(
            "src.database.connection.get_multi_user_database_manager"
        ) as mock_get_manager:
            mock_manager = MagicMock()
            mock_session = MagicMock()
            mock_manager.get_async_session.return_value.__aenter__.return_value = (
                mock_session
            )
            mock_get_manager.return_value = mock_manager

            async with get_async_session(role=DatabaseRole.READER) as session:
                assert session is mock_session


@pytest.mark.unit
class TestDatabaseRetryConfig:
    """数据库重试配置测试"""

    def test_database_retry_config_values(self):
        """测试数据库重试配置值"""
        assert DATABASE_RETRY_CONFIG.max_attempts == 5
        assert DATABASE_RETRY_CONFIG.base_delay == 1.0
        assert DATABASE_RETRY_CONFIG.max_delay == 30.0
        assert DATABASE_RETRY_CONFIG.exponential_base == 2.0
        assert DATABASE_RETRY_CONFIG.jitter is True
        assert len(DATABASE_RETRY_CONFIG.retryable_exceptions) == 3
