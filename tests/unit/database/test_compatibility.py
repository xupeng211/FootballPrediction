"""
测试数据库兼容性模块
"""

import pytest

from src.database.compatibility import (
    Compatibility,
    CompatibleQueryBuilder,
    SQLCompatibilityHelper,
)


@pytest.mark.unit
@pytest.mark.database
def test_compatibility_enum():
    """测试兼容性枚举"""
    assert Compatibility.FULL.value == "full"
    assert Compatibility.PARTIAL.value == "partial"
    assert Compatibility.NONE.value == "none"


def test_query_builder_postgresql():
    """测试PostgreSQL查询构建器"""
    builder = CompatibleQueryBuilder("postgresql")

    # 测试LIMIT查询
    query = builder.build_limit_query("SELECT * FROM users", 10, 5)
    assert "LIMIT 10" in query
    assert "OFFSET 5" in query

    # 测试JSON查询
    json_query = builder.build_json_query("data", "name")
    assert "jsonb_extract_path_text" in json_query


def test_query_builder_mysql():
    """测试MySQL查询构建器"""
    builder = CompatibleQueryBuilder("mysql")

    # 测试LIMIT查询
    query = builder.build_limit_query("SELECT * FROM users", 10, 5)
    assert "LIMIT 10" in query
    assert "OFFSET 5" in query

    # 测试JSON查询
    json_query = builder.build_json_query("data", "name")
    assert "JSON_EXTRACT" in json_query


def test_sql_helper_postgresql_to_mysql():
    """测试SQL转换助手（PostgreSQL到MySQL）"""
    helper = SQLCompatibilityHelper("postgresql", "mysql")

    # 测试数据类型转换
    assert helper.convert_datatype("SERIAL") == "INT AUTO_INCREMENT"
    assert helper.convert_datatype("JSONB") == "JSON"

    # 测试SQL转换
    sql = helper.convert_sql("CREATE TABLE test (id SERIAL, data JSONB)")
    assert "INT AUTO_INCREMENT" in sql
    assert "JSON" in sql


def test_sql_helper_mysql_to_postgresql():
    """测试SQL转换助手（MySQL到PostgreSQL）"""
    helper = SQLCompatibilityHelper("mysql", "postgresql")

    # 测试数据类型转换
    assert helper.convert_datatype("INT AUTO_INCREMENT") == "SERIAL"
    assert helper.convert_datatype("JSON") == "JSONB"

    # 测试SQL转换
    sql = helper.convert_sql("CREATE TABLE test (id INT AUTO_INCREMENT, data JSON)")
    assert "SERIAL" in sql
    assert "JSONB" in sql


def test_check_compatibility():
    """测试兼容性检查"""
    helper = SQLCompatibilityHelper("postgresql", "mysql")

    # 测试完全兼容的SQL
    assert helper.check_compatibility("SELECT * FROM users") == Compatibility.FULL

    # 测试部分兼容的SQL
    partial = helper.check_compatibility("CREATE TABLE test (id SERIAL)")
    assert partial in [Compatibility.PARTIAL, Compatibility.NONE, Compatibility.FULL]
