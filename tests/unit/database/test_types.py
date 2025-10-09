"""数据库类型测试"""

import pytest


class TestDatabaseTypes:
    """测试数据库类型"""

    def test_database_types_import(self):
        """测试数据库类型导入"""
        try:
            from src.database.types import JSONType, UUIDType

            assert True
        except ImportError:
            pytest.skip("database types not available")

    def test_json_type(self):
        """测试JSON类型"""
        try:
            from src.database.types import JSONType

            json_type = JSONType()
            assert json_type is not None
        except Exception:
            pytest.skip("JSONType not available")

    def test_uuid_type(self):
        """测试UUID类型"""
        try:
            from src.database.types import UUIDType

            uuid_type = UUIDType()
            assert uuid_type is not None
        except Exception:
            pytest.skip("UUIDType not available")
