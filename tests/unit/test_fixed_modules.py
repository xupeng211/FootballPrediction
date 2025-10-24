"""测试已修复的模块"""

import pytest


@pytest.mark.unit

def test_database_base_model():
    """测试Database BaseModel"""
    from src.database.base import BaseModel, Base

    # 测试BaseModel可以导入和使用
    assert BaseModel is not None
    assert Base is not None

    # 测试BaseModel的方法
    class TestModel(BaseModel):
        name = "test"

    model = TestModel()
    assert model.to_dict() is not None
    assert "id" in model.to_dict()


def test_database_config():
    """测试DatabaseConfig"""
    from src.database.config import DatabaseConfig

    DatabaseConfig(database="test_db")
    assert _config.database == "test_db"
    assert _config._is_sqlite() is False  # 默认不是SQLite

    # 测试SQLite检测
    config_sqlite = DatabaseConfig(database="test.db")
    assert config_sqlite._is_sqlite() is True


def test_services_base_service():
    """测试BaseService"""
    from src.services.base_unified import BaseService

    # 创建具体实现
    class TestService(BaseService):
        async def _on_initialize(self):
            pass

        async def _on_start(self):
            pass

        async def _on_stop(self):
            pass

        async def _on_shutdown(self):
            pass

    service = TestService("test_service")
    assert service.name == "test_service"
    assert service.get_status() == "uninitialized"
    assert service.is_healthy() is False


def test_domain_models():
    """测试Domain Models"""
    from src.domain.models import Team, Match, Prediction

    # 测试占位符类
    team = Team()
    match = Match()
    prediction = Prediction()

    assert team is not None
    assert match is not None
    assert prediction is not None
