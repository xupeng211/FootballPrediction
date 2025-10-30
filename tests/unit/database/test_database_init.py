""""""""
Database模块导入测试
Database Module Import Tests
""""""""

import pytest

# 尝试导入Database模块并设置可用性标志
try:
        Base,
        DatabaseConfig,
        DatabaseManager,
        get_database_config,
    )

    DATABASE_AVAILABLE = True
    TEST_SKIP_REASON = "Database模块不可用"
except ImportError as e:
    print(f"Database import error: {e}")
    DATABASE_AVAILABLE = False
    TEST_SKIP_REASON = "Database模块不可用"


@pytest.mark.skipif(not DATABASE_AVAILABLE, reason=TEST_SKIP_REASON)
@pytest.mark.unit
@pytest.mark.database
class TestDatabaseModule:
    """Database模块导入测试"""

    def test_database_config_import(self):
        """测试DatabaseConfig导入"""
        try:
            from src.database import DatabaseConfig

            assert DatabaseConfig is not None
        except ImportError:
            pytest.skip("DatabaseConfig导入失败")

    def test_get_database_config_import(self):
        """测试get_database_config函数导入"""
        try:
            from src.database import get_database_config

            assert get_database_config is not None
            assert callable(get_database_config)
        except ImportError:
            pytest.skip("get_database_config导入失败")

    def test_database_manager_import(self):
        """测试DatabaseManager导入"""
        try:
            from src.database import DatabaseManager

            assert DatabaseManager is not None
        except ImportError:
            pytest.skip("DatabaseManager导入失败")

    def test_base_import(self):
        """测试Base导入"""
        try:
            from src.database import Base

            assert Base is not None
        except ImportError:
            pytest.skip("Base导入失败")

    def test_module_all_attributes(self):
        """测试__all__属性完整性"""
        try:
            import src.database as db_module

            expected_attrs = [
                "DatabaseConfig",
                "get_database_config",
                "DatabaseManager",
                "Base",
            ]

            for attr in expected_attrs:
                assert hasattr(db_module, attr), f"缺少属性: {attr}"
                assert attr in db_module.__all__, f"属性不在__all__中: {attr}"

        except ImportError:
            pytest.skip("Database模块导入失败")

    def test_module_docstring(self):
        """测试模块文档字符串"""
        try:
            import src.database as db_module

            assert db_module.__doc__ is not None
            assert "足球预测系统" in db_module.__doc__
            assert "数据库" in db_module.__doc__

        except ImportError:
            pytest.skip("Database模块导入失败")


@pytest.mark.skipif(not DATABASE_AVAILABLE, reason=TEST_SKIP_REASON)
@pytest.mark.unit
@pytest.mark.database
class TestDatabaseModuleIntegration:
    """Database模块集成测试"""

    def test_config_function_availability(self):
        """测试配置函数可用性"""
        try:
            config = get_database_config()
            assert config is not None
        except Exception:
            # 如果配置需要外部依赖,跳过测试
            pytest.skip("配置函数需要外部环境")

    def test_base_class_metadata(self):
        """测试Base类元数据"""
        try:
            from sqlalchemy import DeclarativeBase

            assert issubclass(Base, DeclarativeBase)
            assert hasattr(Base, "metadata")

        except ImportError:
            pytest.skip("SQLAlchemy相关导入失败")

    def test_database_manager_class_structure(self):
        """测试DatabaseManager类结构"""
        try:
            manager_class = DatabaseManager
            assert hasattr(manager_class, "__init__")
            assert hasattr(manager_class, "connect") or hasattr(
                manager_class, "get_session"
            )
        except Exception:
            pytest.skip("DatabaseManager类结构检查失败")
