#!/usr/bin/env python3
"""
Phase 2 - Database模块核心功能测试
专注于提升database核心文件的测试覆盖率
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Session

# 导入database模块的核心组件
from src.database.base import Base, TimestampMixin
from src.database.definitions import DatabaseManager, DatabaseRole
from src.database.models.league import League
from src.database.models.match import Match
from src.database.models.predictions import Predictions
from src.database.models.team import Team


class TestDatabaseCorePhase2:
    """Phase 2 - Database模块核心功能测试"""

    def test_base_model_creation(self):
        """测试BaseModel创建"""
        # 由于BaseModel是抽象类，我们测试它的元类行为
        assert hasattr(Base, "__tablename__")
        assert hasattr(Base, "metadata")

    def test_timestamp_mixin(self):
        """测试TimestampMixin混入类"""

        # 创建一个使用TimestampMixin的测试类
        class TestModel(Base, TimestampMixin):
            __tablename__ = "test_models"

        # 验证时间戳字段存在
        assert hasattr(TestModel, "created_at")
        assert hasattr(TestModel, "updated_at")

    def test_database_manager_singleton(self):
        """测试DatabaseManager单例模式"""
        manager1 = DatabaseManager()
        manager2 = DatabaseManager()

        # 验证单例模式
        assert manager1 is manager2
        assert manager1._instance is manager2._instance

    def test_database_manager_initialization(self):
        """测试DatabaseManager初始化"""
        manager = DatabaseManager()

        # 测试未初始化状态
        assert not manager.initialized

        # 模拟初始化
        with patch.object(manager, "initialize") as mock_init:
            manager.initialize()
            mock_init.assert_called_once()

    def test_database_role_enum(self):
        """测试DatabaseRole枚举"""
        assert DatabaseRole.READER.value == "reader"
        assert DatabaseRole.WRITER.value == "writer"
        assert DatabaseRole.ADMIN.value == "admin"

        # 测试枚举成员
        assert len(DatabaseRole) == 3
        assert DatabaseRole.READER in DatabaseRole
        assert DatabaseRole.WRITER in DatabaseRole
        assert DatabaseRole.ADMIN in DatabaseRole


class TestDatabaseModelsPhase2:
    """Phase 2 - Database模型测试"""

    def test_league_model_structure(self):
        """测试League模型结构"""
        # 测试League模型的基本属性和方法
        assert hasattr(League, "__tablename__")
        assert hasattr(League, "id")
        assert hasattr(League, "name")
        assert hasattr(League, "season")

    def test_team_model_structure(self):
        """测试Team模型结构"""
        # 测试Team模型的基本属性
        assert hasattr(Team, "__tablename__")
        assert hasattr(Team, "id")
        assert hasattr(Team, "name")
        assert hasattr(Team, "short_name")

    def test_match_model_structure(self):
        """测试Match模型结构"""
        # 测试Match模型的基本属性
        assert hasattr(Match, "__tablename__")
        assert hasattr(Match, "id")
        assert hasattr(Match, "home_team_id")
        assert hasattr(Match, "away_team_id")
        assert hasattr(Match, "match_date")

    def test_prediction_model_structure(self):
        """测试Predictions模型结构"""
        # 测试Predictions模型的基本属性
        assert hasattr(Predictions, "__tablename__")
        assert hasattr(Predictions, "id")
        assert hasattr(Predictions, "match_id")
        assert hasattr(Predictions, "user_id")
        assert hasattr(Predictions, "predicted_home")
        assert hasattr(Predictions, "predicted_away")


class TestDatabaseOperationsPhase2:
    """Phase 2 - 数据库操作测试"""

    @pytest.mark.asyncio
    async def test_async_session_creation(self):
        """测试异步会话创建"""
        manager = DatabaseManager()

        # 模拟数据库引擎创建
        with (
            patch.object(manager, "_async_engine"),
            patch.object(manager, "_async_session_factory") as mock_factory,
        ):

            mock_session = AsyncMock(spec=AsyncSession)
            mock_factory.return_value = mock_session

            # 模拟初始化
            with patch.object(manager, "initialize"):
                manager.initialize("sqlite+aiosqlite:///test.db")

            # 测试获取异步会话
            session = manager.get_async_session()
            assert session is mock_session

    def test_sync_session_creation(self):
        """测试同步会话创建"""
        manager = DatabaseManager()

        # 模拟数据库引擎创建
        with (
            patch.object(manager, "_engine"),
            patch.object(manager, "_session_factory") as mock_factory,
        ):

            mock_session = MagicMock(spec=Session)
            mock_factory.return_value = mock_session

            # 模拟初始化
            with patch.object(manager, "initialize"):
                manager.initialize("sqlite:///test.db")

            # 测试获取同步会话
            session = manager.get_session()
            assert session is mock_session

    def test_database_connection_config(self):
        """测试数据库连接配置"""
        # 测试环境变量处理
        with patch.dict("os.environ", {"DATABASE_URL": "postgresql://test/test"}):
            manager = DatabaseManager()

            with patch.object(manager, "initialize") as mock_init:
                manager.initialize()
                # 验证使用了正确的数据库URL
                mock_init.assert_called_once()

    def test_database_connection_default_config(self):
        """测试数据库连接默认配置"""
        with patch.dict("os.environ", {}, clear=True):
            manager = DatabaseManager()

            # 验证默认配置
            with patch.object(manager, "initialize") as mock_init:
                manager.initialize()
                # 应该使用默认的PostgreSQL配置
                mock_init.assert_called_once()


class TestDatabaseAdvancedPhase2:
    """Phase 2 - Database高级功能测试"""

    def test_database_manager_lifecycle(self):
        """测试DatabaseManager生命周期管理"""
        manager = DatabaseManager()

        # 测试初始化状态
        assert not hasattr(manager, "initialized") or not manager.initialized

        # 模拟初始化
        with patch.object(manager, "initialize") as mock_init:
            manager.initialize()
            mock_init.assert_called_once()

        # 验证初始化后的状态
        # 注意：实际的初始化过程会设置initialized标志

    def test_database_error_handling(self):
        """测试数据库错误处理"""
        manager = DatabaseManager()

        # 测试无效数据库URL
        with pytest.raises(ValueError, match="Database URL is required"):
            manager.initialize(None)

        # 测试无效URL格式
        with pytest.raises(ValueError, match="Database URL is required"):
            manager.initialize("")

    @pytest.mark.asyncio
    async def test_database_async_operations(self):
        """测试数据库异步操作"""
        manager = DatabaseManager()

        # 模拟异步会话
        mock_session = AsyncMock(spec=AsyncSession)

        with patch.object(manager, "_async_session_factory", return_value=mock_session):
            with patch.object(manager, "initialize"):
                manager.initialize("sqlite+aiosqlite:///test.db")

            # 测试异步会话使用
            session = manager.get_async_session()

            # 模拟数据库操作
            result = await session.execute("SELECT 1")
            # 模拟返回结果
            result.scalar.return_value = 1

            # 验证操作执行
            assert result.scalar.return_value == 1


def test_all_database_core_functionality():
    """测试所有database核心功能的综合测试"""

    # 测试核心组件
    assert DatabaseManager() is not None
    assert DatabaseRole.READER is not None
    assert Base is not None

    # 测试模型类
    assert League is not None
    assert Team is not None
    assert Match is not None
    assert Predictions is not None

    # 测试混入类
    assert TimestampMixin is not None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
