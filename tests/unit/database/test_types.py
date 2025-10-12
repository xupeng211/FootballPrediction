"""
数据库类型测试
Tests for Database Types

测试src.database.types模块的功能
"""

import json
import pytest
from unittest.mock import Mock, MagicMock

from src.database.types import SQLiteCompatibleJSONB, CompatibleJSON, get_json_type


class TestSQLiteCompatibleJSONB:
    """SQLite兼容的JSONB类型测试"""

    def test_type_creation(self):
        """测试：类型创建"""
        json_type = SQLiteCompatibleJSONB()
        assert json_type is not None
        assert json_type.impl is not None
        assert json_type.cache_ok is True

    def test_load_dialect_impl_with_mock(self):
        """测试：使用Mock测试方言加载"""
        json_type = SQLiteCompatibleJSONB()

        # Mock PostgreSQL dialect
        pg_dialect = Mock()
        pg_dialect.name = "postgresql"
        pg_type_descriptor = Mock()
        pg_dialect.type_descriptor.return_value = pg_type_descriptor

        # 测试PostgreSQL
        result = json_type.load_dialect_impl(pg_dialect)
        pg_dialect.type_descriptor.assert_called_once()
        assert result is not None

        # Mock SQLite dialect
        sqlite_dialect = Mock()
        sqlite_dialect.name = "sqlite"
        text_type_descriptor = Mock()
        sqlite_dialect.type_descriptor.return_value = text_type_descriptor

        # 测试SQLite
        result = json_type.load_dialect_impl(sqlite_dialect)
        sqlite_dialect.type_descriptor.assert_called_once()
        assert result is not None

    def test_process_bind_param_none(self):
        """测试：处理绑定参数（None值）"""
        json_type = SQLiteCompatibleJSONB()
        dialect = Mock()
        dialect.name = "sqlite"

        result = json_type.process_bind_param(None, dialect)
        assert result is None

    def test_process_bind_param_postgresql(self):
        """测试：处理绑定参数（PostgreSQL）"""
        json_type = SQLiteCompatibleJSONB()
        dialect = Mock()
        dialect.name = "postgresql"

        # 测试字典
        data = {"key": "value"}
        result = json_type.process_bind_param(data, dialect)
        assert result == data

        # 测试列表
        data_list = [1, 2, 3]
        result = json_type.process_bind_param(data_list, dialect)
        assert result == data_list

    def test_process_bind_param_sqlite(self):
        """测试：处理绑定参数（SQLite）"""
        json_type = SQLiteCompatibleJSONB()
        dialect = Mock()
        dialect.name = "sqlite"

        # 测试字典
        data = {"key": "value", "number": 123}
        result = json_type.process_bind_param(data, dialect)
        assert isinstance(result, str)
        parsed = json.loads(result)
        assert parsed == data

        # 测试列表
        data_list = [1, 2, 3]
        result = json_type.process_bind_param(data_list, dialect)
        assert isinstance(result, str)
        parsed = json.loads(result)
        assert parsed == data_list

    def test_process_result_value_none(self):
        """测试：处理结果值（None）"""
        json_type = SQLiteCompatibleJSONB()
        dialect = Mock()

        result = json_type.process_result_value(None, dialect)
        assert result is None

    def test_process_result_value_postgresql(self):
        """测试：处理结果值（PostgreSQL）"""
        json_type = SQLiteCompatibleJSONB()
        dialect = Mock()
        dialect.name = "postgresql"

        data = {"key": "value"}
        result = json_type.process_result_value(data, dialect)
        assert result == data

    def test_process_result_value_sqlite(self):
        """测试：处理结果值（SQLite）"""
        json_type = SQLiteCompatibleJSONB()
        dialect = Mock()
        dialect.name = "sqlite"

        # 测试有效JSON字符串
        json_str = '{"key": "value"}'
        result = json_type.process_result_value(json_str, dialect)
        assert result == {"key": "value"}

        # 测试无效JSON字符串
        invalid_str = "not a json"
        result = json_type.process_result_value(invalid_str, dialect)
        assert result == invalid_str

    def test_unicode_handling(self):
        """测试：Unicode处理"""
        json_type = SQLiteCompatibleJSONB()
        dialect = Mock()
        dialect.name = "sqlite"

        data = {"中文": "测试", "emoji": "😀"}
        result = json_type.process_bind_param(data, dialect)

        # 应该保持Unicode字符
        parsed = json.loads(result)
        assert parsed == data

    def test_empty_structures(self):
        """测试：空结构处理"""
        json_type = SQLiteCompatibleJSONB()
        dialect = Mock()
        dialect.name = "sqlite"

        # 空字典
        empty_dict = {}
        bound = json_type.process_bind_param(empty_dict, dialect)
        result = json_type.process_result_value(bound, dialect)
        assert result == {}

        # 空列表
        empty_list = []
        bound = json_type.process_bind_param(empty_list, dialect)
        result = json_type.process_result_value(bound, dialect)
        assert result == []


class TestCompatibleJSON:
    """兼容JSON类型测试"""

    def test_type_creation(self):
        """测试：类型创建"""
        json_type = CompatibleJSON()
        assert json_type is not None
        assert json_type.impl is not None
        assert json_type.cache_ok is True

    def test_load_dialect_impl_with_mock(self):
        """测试：使用Mock测试方言加载"""
        json_type = CompatibleJSON()

        # Mock PostgreSQL dialect
        pg_dialect = Mock()
        pg_dialect.name = "postgresql"
        pg_type_descriptor = Mock()
        pg_dialect.type_descriptor.return_value = pg_type_descriptor

        result = json_type.load_dialect_impl(pg_dialect)
        pg_dialect.type_descriptor.assert_called_once()
        assert result is not None

    def test_process_bind_param_with_mock(self):
        """测试：处理绑定参数"""
        json_type = CompatibleJSON()
        dialect = Mock()

        # 测试None
        result = json_type.process_bind_param(None, dialect)
        assert result is None

        # 测试非None值
        data = {"test": "data"}
        result = json_type.process_bind_param(data, dialect)
        assert result is not None

    def test_process_result_value_with_mock(self):
        """测试：处理结果值"""
        json_type = CompatibleJSON()
        dialect = Mock()

        # 测试None
        result = json_type.process_result_value(None, dialect)
        assert result is None

        # 测试非None值
        data = {"test": "data"}
        result = json_type.process_result_value(data, dialect)
        assert result is not None


class TestUtilityFunctions:
    """工具函数测试"""

    def test_get_json_type_with_jsonb(self):
        """测试：获取JSON类型（使用JSONB）"""
        json_type = get_json_type(use_jsonb=True)
        assert isinstance(json_type, SQLiteCompatibleJSONB)

    def test_get_json_type_without_jsonb(self):
        """测试：获取JSON类型（不使用JSONB）"""
        json_type = get_json_type(use_jsonb=False)
        assert isinstance(json_type, CompatibleJSON)

    def test_get_json_type_default(self):
        """测试：获取JSON类型（默认）"""
        json_type = get_json_type()
        assert isinstance(json_type, SQLiteCompatibleJSONB)


class TestJSONTypeIntegration:
    """JSON类型集成测试"""

    def test_serialization_round_trip(self):
        """测试：序列化往返"""
        json_type = SQLiteCompatibleJSONB()
        sqlite_dialect = Mock()
        sqlite_dialect.name = "sqlite"

        # 原始数据
        original_data = {
            "string": "test",
            "number": 42,
            "boolean": True,
            "null": None,
            "list": [1, 2, 3],
            "nested": {"key": "value"},
        }

        # 绑定参数（Python -> 数据库）
        bound = json_type.process_bind_param(original_data, sqlite_dialect)
        assert isinstance(bound, str)

        # 结果值（数据库 -> Python）
        result = json_type.process_result_value(bound, sqlite_dialect)
        assert result == original_data

    def test_invalid_json_handling(self):
        """测试：无效JSON处理"""
        json_type = SQLiteCompatibleJSONB()
        sqlite_dialect = Mock()
        sqlite_dialect.name = "sqlite"

        # 无效字符串作为输入
        invalid_input = "not a json string"
        bound = json_type.process_bind_param(invalid_input, sqlite_dialect)

        # 应该被包装成JSON字符串
        assert bound == '"not a json string"'

    def test_special_characters(self):
        """测试：特殊字符处理"""
        json_type = SQLiteCompatibleJSONB()
        sqlite_dialect = Mock()
        sqlite_dialect.name = "sqlite"

        data = {
            "quotes": 'Single "and" double quotes',
            "backslashes": r"\n\t\r\\",
            "special": "!@#$%^&*()",
        }

        # 序列化
        bound = json_type.process_bind_param(data, sqlite_dialect)

        # 反序列化
        result = json_type.process_result_value(bound, sqlite_dialect)
        assert result == data
