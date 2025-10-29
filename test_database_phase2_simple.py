#!/usr/bin/env python3
"""
Phase 2 - Database模块简化测试
专注于实际可测试的database核心功能
"""

import pytest
from unittest.mock import MagicMock, patch
import os

# 导入database模块的核心组件
from src.database.base import Base, TimestampMixin, BaseModel
from src.database.definitions import DatabaseManager, DatabaseRole
from src.database.models.league import League
from src.database.models.team import Team
from src.database.models.match import Match
from src.database.models.predictions import Predictions


class TestDatabaseSimplePhase2:
    """Phase 2 - Database模块简化核心功能测试"""

    def test_base_class_exists(self):
        """测试基础类存在"""
        assert Base is not None
        assert hasattr(Base, "metadata")

    def test_base_model_class(self):
        """测试BaseModel类"""
        assert BaseModel is not None
        assert hasattr(BaseModel, "id")
        assert hasattr(BaseModel, "to_dict")
        assert hasattr(BaseModel, "from_dict")
        assert hasattr(BaseModel, "update_from_dict")
        assert hasattr(BaseModel, "__repr__")

    def test_timestamp_mixin_class(self):
        """测试TimestampMixin类"""
        assert TimestampMixin is not None
        assert hasattr(TimestampMixin, "created_at")
        assert hasattr(TimestampMixin, "updated_at")

    def test_database_manager_singleton(self):
        """测试DatabaseManager单例模式"""
        manager1 = DatabaseManager()
        manager2 = DatabaseManager()

        # 验证单例模式
        assert manager1 is manager2
        assert hasattr(manager1, "_instance")

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

    def test_database_models_exist(self):
        """测试数据库模型类存在"""
        # 测试模型类可以正常导入
        assert League is not None
        assert Team is not None
        assert Match is not None
        assert Predictions is not None

        # 测试模型类继承自BaseModel
        assert issubclass(League, BaseModel)
        assert issubclass(Team, BaseModel)
        assert issubclass(Match, BaseModel)
        assert issubclass(Predictions, BaseModel)

    def test_database_models_have_tablenames(self):
        """测试模型类有表名"""
        assert hasattr(League, "__tablename__")
        assert hasattr(Team, "__tablename__")
        assert hasattr(Match, "__tablename__")
        assert hasattr(Predictions, "__tablename__")

        assert League.__tablename__ == "leagues"

    def test_database_manager_methods(self):
        """测试DatabaseManager方法存在"""
        manager = DatabaseManager()

        # 测试方法存在
        assert hasattr(manager, "initialize")
        assert hasattr(manager, "get_async_session")
        assert hasattr(manager, "get_session")

    def test_database_config_environment(self):
        """测试数据库配置环境变量"""
        # 测试环境变量处理
        with patch.dict(os.environ, {"DATABASE_URL": "postgresql://test/test"}):
            manager = DatabaseManager()
            assert manager is not None

    def test_database_connection_default_config(self):
        """测试数据库连接默认配置"""
        with patch.dict(os.environ, {}, clear=True):
            manager = DatabaseManager()
            assert manager is not None

    def test_base_model_methods_functionality(self):
        """测试BaseModel方法功能"""
        # 由于BaseModel是抽象类，我们测试它的类方法
        assert hasattr(BaseModel, "to_dict")
        assert hasattr(BaseModel, "from_dict")
        assert hasattr(BaseModel, "update_from_dict")
        assert hasattr(BaseModel, "__repr__")

    def test_database_imports(self):
        """测试database模块导入"""
        # 测试所有核心组件可以正常导入
        from src.database import base, definitions, models

        assert base is not None
        assert definitions is not None
        assert models is not None


def test_all_database_simple_functionality():
    """测试所有database简化功能的综合测试"""

    # 测试核心组件
    assert DatabaseManager() is not None
    assert DatabaseRole.READER is not None
    assert Base is not None
    assert BaseModel is not None
    assert TimestampMixin is not None

    # 测试模型类
    assert League is not None
    assert Team is not None
    assert Match is not None
    assert Predictions is not None

    print("✅ 所有database简化功能测试通过")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
