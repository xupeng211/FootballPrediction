"""
数据库连接模块简化测试
测试DatabaseManager和MultiUserDatabaseManager的核心功能
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
        db_manager._session_factory = mock_session_factory  # 使用正确的属性名

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
        db_manager._session_factory = None

        with pytest.raises(RuntimeError, match="数据库连接未初始化"):
            db_manager.create_session()

        db_manager._async_session_factory = None

        with pytest.raises(RuntimeError, match="数据库连接未初始化"):
            db_manager.create_async_session()

    # === 数据库操作测试 ===

    @pytest.mark.asyncio
    async def test_get_match(self, db_manager):
        """测试获取比赛信息"""
        # 先初始化 async_session_factory 以避免运行时错误
        db_manager._async_session_factory = MagicMock()

        mock_session = AsyncMock()

        # 创建模拟的 match 对象
        mock_match = MagicMock()

        # 创建模拟的列对象
        mock_table = MagicMock()
        mock_column1 = MagicMock()
        mock_column1.name = "id"
        mock_column2 = MagicMock()
        mock_column2.name = "home_team_id"
        mock_column3 = MagicMock()
        mock_column3.name = "away_team_id"
        mock_column4 = MagicMock()
        mock_column4.name = "home_score"
        mock_column5 = MagicMock()
        mock_column5.name = "away_score"

        mock_table.columns = [
            mock_column1,
            mock_column2,
            mock_column3,
            mock_column4,
            mock_column5,
        ]
        mock_match.__table__ = mock_table

        # 设置属性
        mock_match.id = 123
        mock_match.home_team_id = 1
        mock_match.away_team_id = 2
        mock_match.home_score = 2
        mock_match.away_score = 1

        # Mock session.execute 返回结果对象
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_match
        mock_session.execute.return_value = mock_result

        with patch.object(db_manager, "get_async_session") as mock_get_session:
            mock_get_session.return_value.__aenter__.return_value = mock_session

            result = await db_manager.get_match(123)

            assert result is not None
            assert result["id"] == 123
            assert result["home_score"] == 2

    @pytest.mark.asyncio
    async def test_get_match_not_found(self, db_manager):
        """测试获取不存在的比赛"""
        # 先初始化 async_session_factory 以避免运行时错误
        db_manager._async_session_factory = MagicMock()

        mock_session = AsyncMock()
        # Mock execute 返回结果对象
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_session.execute.return_value = mock_result

        with patch.object(db_manager, "get_async_session") as mock_get_session:
            mock_get_session.return_value.__aenter__.return_value = mock_session

            result = await db_manager.get_match(999)

            assert result is None

    @pytest.mark.asyncio
    async def test_update_match(self, db_manager):
        """测试更新比赛信息"""
        # 先初始化 async_session_factory 以避免运行时错误
        db_manager._async_session_factory = MagicMock()

        mock_session = AsyncMock()
        mock_result = MagicMock()
        mock_result.rowcount = 1
        mock_session.execute.return_value = mock_result

        with patch.object(db_manager, "get_async_session") as mock_get_session:
            mock_get_session.return_value.__aenter__.return_value = mock_session

            data = {"home_score": 3, "away_score": 1}
            result = await db_manager.update_match(123, data)

            assert result is True
            mock_session.execute.assert_called_once()
            mock_session.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_update_match_not_found(self, db_manager):
        """测试更新不存在的比赛"""
        # 先初始化 async_session_factory 以避免运行时错误
        db_manager._async_session_factory = MagicMock()

        mock_session = AsyncMock()
        mock_result = MagicMock()
        mock_result.rowcount = 0
        mock_session.execute.return_value = mock_result

        with patch.object(db_manager, "get_async_session") as mock_get_session:
            mock_get_session.return_value.__aenter__.return_value = mock_session

            data = {"home_score": 3, "away_score": 1}
            result = await db_manager.update_match(999, data)

            assert result is False

    @pytest.mark.asyncio
    async def test_get_prediction(self, db_manager):
        """测试获取预测信息"""
        # 先初始化 async_session_factory 以避免运行时错误
        db_manager._async_session_factory = MagicMock()

        mock_session = AsyncMock()

        # 创建模拟的 prediction 对象
        mock_prediction = MagicMock()

        # 创建模拟的列对象
        mock_table = MagicMock()
        mock_column1 = MagicMock()
        mock_column1.name = "id"
        mock_column2 = MagicMock()
        mock_column2.name = "match_id"
        mock_column3 = MagicMock()
        mock_column3.name = "predicted_result"
        mock_column4 = MagicMock()
        mock_column4.name = "confidence"

        mock_table.columns = [mock_column1, mock_column2, mock_column3, mock_column4]
        mock_prediction.__table__ = mock_table

        # 设置属性
        mock_prediction.id = 1
        mock_prediction.match_id = 123
        mock_prediction.predicted_result = "home_win"
        mock_prediction.confidence = 0.85

        # Mock session.execute 返回结果对象
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_prediction
        mock_session.execute.return_value = mock_result

        with patch.object(db_manager, "get_async_session") as mock_get_session:
            mock_get_session.return_value.__aenter__.return_value = mock_session

            result = await db_manager.get_prediction(123)

            assert result is not None
            assert result["match_id"] == 123
            assert result["predicted_result"] == "home_win"

    # === 健康检查测试 ===

    def test_health_check_healthy(self, db_manager):
        """测试健康检查 - 健康"""
        # Mock session factory
        mock_session = MagicMock()
        mock_session.execute.return_value = MagicMock()
        db_manager._session_factory = MagicMock(return_value=mock_session)

        # 设置 sync engine
        db_manager._sync_engine = MagicMock()

        result = db_manager.health_check()

        assert result is True

    def test_health_check_unhealthy(self, db_manager):
        """测试健康检查 - 不健康"""
        # Mock session factory that raises exception
        mock_session = MagicMock()
        mock_session.execute.side_effect = Exception("Database error")
        db_manager._session_factory = MagicMock(return_value=mock_session)

        # 设置 sync engine
        db_manager._sync_engine = MagicMock()

        result = db_manager.health_check()

        assert result is False

    def test_health_check_no_engine(self, db_manager):
        """测试健康检查 - 无引擎"""
        db_manager._sync_engine = None
        db_manager._session_factory = None

        result = db_manager.health_check()

        assert result is False

    @pytest.mark.asyncio
    async def test_async_health_check_healthy(self, db_manager):
        """测试异步健康检查 - 健康"""
        # 模拟异步session
        mock_session = AsyncMock()
        mock_session.execute = AsyncMock()
        mock_session.close = AsyncMock()

        # 模拟 create_async_session 返回模拟的session
        db_manager.create_async_session = MagicMock(return_value=mock_session)

        result = await db_manager.async_health_check()

        assert result is True
        mock_session.execute.assert_called_once()
        mock_session.close.assert_called_once()

    @pytest.mark.asyncio
    async def test_health_check_with_retry_healthy(self, db_manager):
        """测试带重试的健康检查 - 健康"""
        # 模拟异步session
        mock_session = AsyncMock()
        mock_session.execute = AsyncMock()
        mock_session.close = AsyncMock()

        # 模拟 create_async_session 返回模拟的session
        db_manager.create_async_session = MagicMock(return_value=mock_session)

        result = await db_manager.health_check_with_retry()

        assert result is True
        mock_session.execute.assert_called_once()
        mock_session.close.assert_called_once()

    @pytest.mark.asyncio
    async def test_health_check_with_retry_unhealthy(self, db_manager):
        """测试带重试的健康检查 - 不健康"""
        # 模拟 create_async_session 抛出异常
        db_manager.create_async_session = MagicMock(
            side_effect=Exception("Database error")
        )

        result = await db_manager.health_check_with_retry()

        assert result is False

    def test_health_check_sync_with_retry_healthy(self, db_manager):
        """测试同步带重试的健康检查 - 健康"""
        # 模拟同步session
        mock_session = MagicMock()
        mock_session.execute = MagicMock()
        mock_session.close = MagicMock()

        # 模拟 create_session 返回模拟的session
        db_manager.create_session = MagicMock(return_value=mock_session)

        result = db_manager.health_check_sync_with_retry()

        assert result is True
        mock_session.execute.assert_called_once()
        mock_session.close.assert_called_once()

    # === 关闭测试 ===

    @pytest.mark.asyncio
    async def test_close(self, db_manager):
        """测试关闭连接"""
        mock_sync_engine = MagicMock()
        mock_async_engine = AsyncMock()  # 需要AsyncMock因为dispose会被await
        db_manager._sync_engine = mock_sync_engine
        db_manager._async_engine = mock_async_engine
        db_manager._session_factory = MagicMock()
        db_manager._async_session_factory = MagicMock()

        await db_manager.close()

        mock_sync_engine.dispose.assert_called_once()
        mock_async_engine.dispose.assert_called_once()
        # close方法不将引擎设置为None，只是调用dispose


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
            mock_base_config.host = "localhost"
            mock_base_config.port = 5432
            mock_base_config.database = "test_db"
            mock_base_config.password = "password"
            mock_base_config.pool_size = 5
            mock_base_config.max_overflow = 10
            mock_base_config.pool_timeout = 30
            mock_base_config.pool_recycle = 3600
            mock_base_config.async_pool_size = 5
            mock_base_config.async_max_overflow = 10
            mock_base_config.echo = False
            mock_base_config.echo_pool = False
            mock_get_config.return_value = mock_base_config

            # Mock DatabaseManager类
            with patch("src.database.connection.DatabaseManager") as mock_manager_class:
                mock_manager = MagicMock()
                mock_manager_class.return_value = mock_manager

                multi_db_manager.initialize()

                # 验证为每个角色创建了管理器
                assert mock_manager_class.call_count == 3
                assert len(multi_db_manager._managers) == 3

                # 验证每个管理器都被初始化了一次
                assert mock_manager.initialize.call_count == 3

                # 验证三个角色都有管理器
                assert DatabaseRole.READER in multi_db_manager._managers
                assert DatabaseRole.WRITER in multi_db_manager._managers
                assert DatabaseRole.ADMIN in multi_db_manager._managers

    # === 管理器获取测试 ===

    def test_get_manager(self, multi_db_manager):
        """测试获取管理器"""
        mock_manager = MagicMock()
        multi_db_manager._managers[DatabaseRole.READER] = mock_manager

        manager = multi_db_manager.get_manager(DatabaseRole.READER)
        assert manager is mock_manager

    def test_get_manager_not_initialized(self, multi_db_manager):
        """测试获取未初始化的管理器"""
        # 先清空管理器
        multi_db_manager._managers = {}
        with pytest.raises(
            RuntimeError,
            match="数据库角色 reader 的管理器未初始化，请先调用 initialize",
        ):
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

    # === 健康检查测试 ===

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
        # 先清空管理器
        multi_db_manager._managers = {}
        health = multi_db_manager.health_check()

        # 当没有管理器时，应该返回空字典
        assert health == {}

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
        assert "description" in permissions
        assert "permissions" in permissions
        assert "use_cases" in permissions
        # 检查权限描述
        assert "只读用户" in permissions["description"]
        assert "SELECT" in permissions["permissions"]


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
        with patch("src.database.connection._db_manager") as mock_manager:
            initialize_database()

            # initialize 方法应该被调用
            mock_manager.initialize.assert_called_once()

    def test_initialize_multi_user_database(self):
        """测试初始化多用户数据库"""
        with patch("src.database.connection._multi_db_manager") as mock_manager:
            initialize_multi_user_database()

            # initialize 方法应该被调用
            mock_manager.initialize.assert_called_once()

    def test_initialize_test_database(self):
        """测试初始化测试数据库"""
        # Mock所有外部依赖
        with patch("src.database.connection.get_database_config") as mock_get_config:
            with patch("src.database.connection.create_engine") as mock_create_engine:
                with patch("src.database.connection.sessionmaker") as mock_sessionmaker:
                    # Mock Base from the correct module
                    with patch("src.database.base.Base") as mock_base:
                        mock_config = MagicMock()
                        mock_config.sync_url = "sqlite:///:memory:"
                        mock_config.echo = False
                        mock_config.echo_pool = False
                        mock_get_config.return_value = mock_config

                        mock_engine = MagicMock()
                        mock_create_engine.return_value = mock_engine
                        mock_factory = MagicMock()
                        mock_sessionmaker.return_value = mock_factory

                        initialize_test_database()

                        # 验证调用
                        mock_create_engine.assert_called_once_with(
                            mock_config.sync_url,
                            echo=mock_config.echo,
                            echo_pool=mock_config.echo_pool,
                        )
                        mock_sessionmaker.assert_called_once()
                        mock_base.metadata.create_all.assert_called_once_with(
                            bind=mock_engine
                        )


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
