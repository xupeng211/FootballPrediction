import os
"""
SQL兼容性模块测试
SQL Compatibility Module Tests

测试src/database/sql_compatibility.py的主要功能
"""

import pytest
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from sqlalchemy import Engine, create_engine
from sqlalchemy.ext.asyncio import AsyncEngine


class TestSQLCompatibilityHelper:
    """测试SQL兼容性助手类"""

    def test_detect_database_type_sqlite(self):
        """测试检测SQLite数据库"""
        from src.database.sql_compatibility import SQLCompatibilityHelper

        # 测试字符串URL
        url = os.getenv("TEST_SQL_COMPATIBILITY_COMPLETE_URL_22")
        db_type = SQLCompatibilityHelper.detect_database_type(url)
        assert db_type == "sqlite"

        # 测试内存SQLite
        url = os.getenv("TEST_SQL_COMPATIBILITY_COMPLETE_URL_24")
        db_type = SQLCompatibilityHelper.detect_database_type(url)
        assert db_type == "sqlite"

        # 测试 SQLAlchemy Engine
        engine = create_engine("sqlite:///test.db")
        db_type = SQLCompatibilityHelper.detect_database_type(engine)
        assert db_type == "sqlite"

    def test_detect_database_type_postgresql(self):
        """测试检测PostgreSQL数据库"""
        from src.database.sql_compatibility import SQLCompatibilityHelper

        # 测试字符串URL
        url = os.getenv("TEST_SQL_COMPATIBILITY_COMPLETE_URL_38")
        db_type = SQLCompatibilityHelper.detect_database_type(url)
        assert db_type == "postgresql"

        # 测试 psycopg3 URL
        url = os.getenv("TEST_SQL_COMPATIBILITY_COMPLETE_URL_42")
        db_type = SQLCompatibilityHelper.detect_database_type(url)
        assert db_type == "postgresql"

    def test_detect_database_type_mysql(self):
        """测试检测MySQL数据库"""
        from src.database.sql_compatibility import SQLCompatibilityHelper

        # 测试字符串URL
        url = os.getenv("TEST_SQL_COMPATIBILITY_COMPLETE_URL_52")
        db_type = SQLCompatibilityHelper.detect_database_type(url)
        assert db_type == "mysql"

        # 测试 PyMySQL URL
        url = os.getenv("TEST_SQL_COMPATIBILITY_COMPLETE_URL_56")
        db_type = SQLCompatibilityHelper.detect_database_type(url)
        assert db_type == "mysql"

    def test_detect_database_type_unknown(self):
        """测试检测未知数据库"""
        from src.database.sql_compatibility import SQLCompatibilityHelper

        # 测试未知URL
        url = os.getenv("TEST_SQL_COMPATIBILITY_COMPLETE_URL_65")
        db_type = SQLCompatibilityHelper.detect_database_type(url)
        assert db_type == "unknown"

    def test_get_interval_sql_postgresql(self):
        """测试PostgreSQL时间间隔SQL"""
        from src.database.sql_compatibility import SQLCompatibilityHelper

        # 默认参数
        sql = SQLCompatibilityHelper.get_interval_sql("postgresql")
        assert sql == "NOW() - INTERVAL '1 hour'"

        # 自定义参数
        sql = SQLCompatibilityHelper.get_interval_sql(
            "postgresql",
            base_time = os.getenv("TEST_SQL_COMPATIBILITY_COMPLETE_BASE_TIME_79"),
            interval_value=7,
            interval_unit="day"
        )
        assert sql == "created_at - INTERVAL '7 day'"

        # 测试不同单位
        units = ["minute", "second", "month", "year"]
        for unit in units:
            sql = SQLCompatibilityHelper.get_interval_sql("postgresql", interval_unit=unit)
            assert f"INTERVAL '1 {unit}'" in sql

    def test_get_interval_sql_sqlite(self):
        """测试SQLite时间间隔SQL"""
        from src.database.sql_compatibility import SQLCompatibilityHelper

        # 默认参数
        sql = SQLCompatibilityHelper.get_interval_sql("sqlite")
        assert sql == "datetime('now', '-1 hours')"

        # 自定义参数
        sql = SQLCompatibilityHelper.get_interval_sql(
            "sqlite",
            base_time="'2023-01-01'",
            interval_value=5,
            interval_unit="day"
        )
        assert sql == "datetime('2023-01-01', '-5 days')"

        # 测试单位映射
        unit_map = {
            "hour": "hours",
            "day": "days",
            "minute": "minutes",
            "second": "seconds"
        }
        for unit, expected in unit_map.items():
            sql = SQLCompatibilityHelper.get_interval_sql("sqlite", interval_unit=unit)
            assert f"-1 {expected}" in sql

    def test_get_interval_sql_default(self):
        """测试默认时间间隔SQL"""
        from src.database.sql_compatibility import SQLCompatibilityHelper

        # 对于未知数据库，使用PostgreSQL语法
        sql = SQLCompatibilityHelper.get_interval_sql("unknown")
        assert sql == "NOW() - INTERVAL '1 hour'"

    def test_get_epoch_extract_sql_postgresql(self):
        """测试PostgreSQL EPOCH提取SQL"""
        from src.database.sql_compatibility import SQLCompatibilityHelper

        sql = SQLCompatibilityHelper.get_epoch_extract_sql("postgresql", "created_at")
        assert sql == "EXTRACT(EPOCH FROM created_at)"

        # 测试不同时间表达式
        expressions = ["NOW()", "updated_at", "timestamp_col"]
        for expr in expressions:
            sql = SQLCompatibilityHelper.get_epoch_extract_sql("postgresql", expr)
            assert f"EXTRACT(EPOCH FROM {expr})" == sql

    def test_get_epoch_extract_sql_sqlite(self):
        """测试SQLite EPOCH提取SQL"""
        from src.database.sql_compatibility import SQLCompatibilityHelper

        sql = SQLCompatibilityHelper.get_epoch_extract_sql("sqlite", "created_at")
        expected = os.getenv("TEST_SQL_COMPATIBILITY_COMPLETE_EXPECTED_146")1970 - 01 - 01 00:00:00')) * 86400)"
        assert sql == expected

        # 测试函数调用
        sql = SQLCompatibilityHelper.get_epoch_extract_sql("sqlite", "datetime('now')")
        assert "julianday(datetime('now'))" in sql

    def test_get_epoch_extract_sql_default(self):
        """测试默认EPOCH提取SQL"""
        from src.database.sql_compatibility import SQLCompatibilityHelper

        # 对于未知数据库，使用PostgreSQL语法
        sql = SQLCompatibilityHelper.get_epoch_extract_sql("unknown", "timestamp_col")
        assert sql == "EXTRACT(EPOCH FROM timestamp_col)"

    def test_get_random_function_sql(self):
        """测试随机函数SQL"""
        from src.database.sql_compatibility import SQLCompatibilityHelper

        # PostgreSQL
        sql = SQLCompatibilityHelper.get_random_function_sql("postgresql")
        assert sql == "RANDOM()"

        # SQLite
        sql = SQLCompatibilityHelper.get_random_function_sql("sqlite")
        assert sql == "RANDOM()"

        # MySQL
        sql = SQLCompatibilityHelper.get_random_function_sql("mysql")
        assert sql == "RAND()"

        # 默认
        sql = SQLCompatibilityHelper.get_random_function_sql("unknown")
        assert sql == "RANDOM()"

    def test_get_limit_offset_sql(self):
        """测试LIMIT OFFSET SQL"""
        from src.database.sql_compatibility import SQLCompatibilityHelper

        # 所有数据库应该使用相同的语法
        db_types = ["postgresql", "sqlite", "mysql", "unknown"]

        for db_type in db_types:
            sql = SQLCompatibilityHelper.get_limit_offset_sql(db_type, 10, 5)
            assert sql == "LIMIT 10 OFFSET 5"

            # 测试只有LIMIT
            sql = SQLCompatibilityHelper.get_limit_offset_sql(db_type, 100)
            assert sql == "LIMIT 100"

            # 测试只有OFFSET
            sql = SQLCompatibilityHelper.get_limit_offset_sql(db_type, offset=20)
            assert sql == "OFFSET 20"

    def test_get_full_text_search_sql(self):
        """测试全文搜索SQL"""
        from src.database.sql_compatibility import SQLCompatibilityHelper

        # PostgreSQL
        sql = SQLCompatibilityHelper.get_full_text_search_sql(
            "postgresql",
            "content",
            "search_term"
        )
        assert "to_tsvector" in sql
        assert "plainto_tsquery" in sql

        # SQLite
        sql = SQLCompatibilityHelper.get_full_text_search_sql(
            "sqlite",
            "content",
            "search_term"
        )
        assert "content LIKE" in sql
        assert "%search_term%" in sql

        # 默认
        sql = SQLCompatibilityHelper.get_full_text_search_sql(
            "unknown",
            "content",
            "search_term"
        )
        assert "content LIKE" in sql

    def test_get_regexp_match_sql(self):
        """测试正则匹配SQL"""
        from src.database.sql_compatibility import SQLCompatibilityHelper

        # PostgreSQL
        sql = SQLCompatibilityHelper.get_regexp_match_sql("postgresql", "column", "pattern")
        assert sql == "column ~ 'pattern'"

        # SQLite
        sql = SQLCompatibilityHelper.get_regexp_match_sql("sqlite", "column", "pattern")
        assert "REGEXP" in sql

        # MySQL
        sql = SQLCompatibilityHelper.get_regexp_match_sql("mysql", "column", "pattern")
        assert "REGEXP" in sql

    def test_get_group_concat_sql(self):
        """测试GROUP CONCAT SQL"""
        from src.database.sql_compatibility import SQLCompatibilityHelper

        # PostgreSQL
        sql = SQLCompatibilityHelper.get_group_concat_sql("postgresql", "column")
        assert "STRING_AGG" in sql
        assert sql == "STRING_AGG(column, ',')"

        # SQLite
        sql = SQLCompatibilityHelper.get_group_concat_sql("sqlite", "column")
        assert "GROUP_CONCAT" in sql
        assert sql == "GROUP_CONCAT(column)"

        # MySQL
        sql = SQLCompatibilityHelper.get_group_concat_sql("mysql", "column")
        assert "GROUP_CONCAT" in sql
        assert sql == "GROUP_CONCAT(column)"

    def test_get_json_extract_sql(self):
        """测试JSON提取SQL"""
        from src.database.sql_compatibility import SQLCompatibilityHelper

        # PostgreSQL
        sql = SQLCompatibilityHelper.get_json_extract_sql("postgresql", "column", "path")
        assert "column::json" in sql or "->" in sql

        # SQLite
        sql = SQLCompatibilityHelper.get_json_extract_sql("sqlite", "column", "path")
        assert "json_extract" in sql

        # MySQL
        sql = SQLCompatibilityHelper.get_json_extract_sql("mysql", "column", "path")
        assert "JSON_EXTRACT" in sql

    def test_get_table_info_query(self):
        """测试表信息查询SQL"""
        from src.database.sql_compatibility import SQLCompatibilityHelper

        # PostgreSQL
        sql = SQLCompatibilityHelper.get_table_info_query("postgresql", "table_name")
        assert "information_schema" in sql
        assert "table_name" in sql

        # SQLite
        sql = SQLCompatibilityHelper.get_table_info_query("sqlite", "table_name")
        assert "PRAGMA" in sql
        assert "table_info" in sql

        # MySQL
        sql = SQLCompatibilityHelper.get_table_info_query("mysql", "table_name")
        assert "information_schema" in sql
        assert "table_name" in sql

    def test_convert_sql_dialect(self):
        """测试SQL方言转换"""
        from src.database.sql_compatibility import SQLCompatibilityHelper

        # PostgreSQL到SQLite的转换
        pg_sql = os.getenv("TEST_SQL_COMPATIBILITY_COMPLETE_PG_SQL_302")1 day'"
        sqlite_sql = SQLCompatibilityHelper.convert_sql_dialect(pg_sql, "postgresql", "sqlite")
        assert "datetime" in sqlite_sql or "sqlite" in sqlite_sql.lower()

        # 测试不需要转换的情况
        simple_sql = os.getenv("TEST_SQL_COMPATIBILITY_COMPLETE_SIMPLE_SQL_310")
        converted = SQLCompatibilityHelper.convert_sql_dialect(simple_sql, "sqlite", "postgresql")
        # 应该保持原样或做最小改动


class TestCompatibleQueryBuilder:
    """测试兼容查询构建器"""

    def test_query_builder_initialization(self):
        """测试查询构建器初始化"""
        from src.database.sql_compatibility import CompatibleQueryBuilder

        builder = CompatibleQueryBuilder("sqlite")
        assert builder.db_type == "sqlite"

        builder = CompatibleQueryBuilder("postgresql")
        assert builder.db_type == "postgresql"

    def test_query_builder_select(self):
        """测试构建SELECT查询"""
        from src.database.sql_compatibility import CompatibleQueryBuilder

        builder = CompatibleQueryBuilder("sqlite")
        query = builder.select("users", ["id", "name"]).build()
        assert "SELECT id, name FROM users" in query

        # 带WHERE条件
        query = builder.select("users").where("id", "=", 1).build()
        assert "SELECT * FROM users" in query
        assert "WHERE id = 1" in query

    def test_query_builder_insert(self):
        """测试构建INSERT查询"""
        from src.database.sql_compatibility import CompatibleQueryBuilder

        builder = CompatibleQueryBuilder("sqlite")
        query = builder.insert("users", {"name": "John", "email": "john@example.com"}).build()
        assert "INSERT INTO users" in query
        assert "name" in query
        assert "email" in query
        assert "John" in query

    def test_query_builder_update(self):
        """测试构建UPDATE查询"""
        from src.database.sql_compatibility import CompatibleQueryBuilder

        builder = CompatibleQueryBuilder("sqlite")
        query = builder.update("users", {"name": "Jane"}).where("id", "=", 1).build()
        assert "UPDATE users SET name = Jane" in query
        assert "WHERE id = 1" in query

    def test_query_builder_delete(self):
        """测试构建DELETE查询"""
        from src.database.sql_compatibility import CompatibleQueryBuilder

        builder = CompatibleQueryBuilder("sqlite")
        query = builder.delete("users").where("id", "=", 1).build()
        assert "DELETE FROM users WHERE id = 1" in query

    def test_query_builder_order_by(self):
        """测试ORDER BY子句"""
        from src.database.sql_compatibility import CompatibleQueryBuilder

        builder = CompatibleQueryBuilder("sqlite")
        query = builder.select("users").order_by("name", "ASC").build()
        assert "ORDER BY name ASC" in query

        # 多字段排序
        query = builder.select("users").order_by("name", "ASC").order_by("id", "DESC").build()
        assert "name ASC" in query
        assert "id DESC" in query

    def test_query_builder_group_by(self):
        """测试GROUP BY子句"""
        from src.database.sql_compatibility import CompatibleQueryBuilder

        builder = CompatibleQueryBuilder("sqlite")
        query = builder.select("users", ["role", "COUNT(*)"]).group_by("role").build()
        assert "GROUP BY role" in query

    def test_query_builder_limit_offset(self):
        """测试LIMIT和OFFSET"""
        from src.database.sql_compatibility import CompatibleQueryBuilder

        builder = CompatibleQueryBuilder("sqlite")
        query = builder.select("users").limit(10).offset(5).build()
        assert "LIMIT 10" in query
        assert "OFFSET 5" in query

    def test_query_builder_joins(self):
        """测试JOIN操作"""
        from src.database.sql_compatibility import CompatibleQueryBuilder

        builder = CompatibleQueryBuilder("sqlite")
        query = builder.select("users").join("orders", "users.id = orders.user_id").build()
        assert "JOIN orders ON users.id = orders.user_id" in query

        # LEFT JOIN
        query = builder.select("users").left_join("orders", "users.id = orders.user_id").build()
        assert "LEFT JOIN orders" in query

    def test_query_builder_complex_query(self):
        """测试复杂查询构建"""
        from src.database.sql_compatibility import CompatibleQueryBuilder

        builder = CompatibleQueryBuilder("postgresql")
        query = (builder
                 .select("users", ["users.name", "COUNT(orders.id) as order_count"])
                 .join("orders", "users.id = orders.user_id")
                 .where("users.created_at", ">", "NOW() - INTERVAL '30 day'")
                 .group_by("users.id", "users.name")
                 .having("COUNT(orders.id)", ">", 5)
                 .order_by("order_count", "DESC")
                 .limit(10)
                 .build())

        assert "SELECT users.name" in query
        assert "JOIN orders" in query
        assert "GROUP BY" in query
        assert "HAVING" in query
        assert "ORDER BY" in query
        assert "LIMIT 10" in query


class TestUtilityFunctions:
    """测试工具函数"""

    def test_get_db_type_from_engine(self):
        """测试从引擎获取数据库类型"""
        from src.database.sql_compatibility import get_db_type_from_engine

        # 测试SQLite引擎
        engine = create_engine("sqlite:///test.db")
        db_type = get_db_type_from_engine(engine)
        assert db_type == "sqlite"

        # 测试模拟的PostgreSQL引擎
        mock_engine = Mock()
        mock_engine.url = os.getenv("TEST_SQL_COMPATIBILITY_COMPLETE_URL_38")
        db_type = get_db_type_from_engine(mock_engine)
        assert db_type == "postgresql"

    def test_create_compatible_query_builder(self):
        """测试创建兼容查询构建器"""
        from src.database.sql_compatibility import create_compatible_query_builder

        # 测试SQLite
        engine = create_engine("sqlite:///test.db")
        builder = create_compatible_query_builder(engine)
        assert builder.db_type == "sqlite"

        # 测试模拟的PostgreSQL引擎
        mock_engine = Mock()
        mock_engine.url = os.getenv("TEST_SQL_COMPATIBILITY_COMPLETE_URL_38")
        builder = create_compatible_query_builder(mock_engine)
        assert builder.db_type == "postgresql"


class TestSQLCompatibilityEdgeCases:
    """测试SQL兼容性边界情况"""

    def test_empty_inputs(self):
        """测试空输入"""
        from src.database.sql_compatibility import SQLCompatibilityHelper

        # 空URL
        db_type = SQLCompatibilityHelper.detect_database_type("")
        assert db_type == "unknown"

        # 空的时间表达式
        sql = SQLCompatibilityHelper.get_epoch_extract_sql("postgresql", "")
        assert sql == "EXTRACT(EPOCH FROM )"

    def test_special_characters(self):
        """测试特殊字符处理"""
        from src.database.sql_compatibility import SQLCompatibilityHelper

        # 包含特殊字符的搜索词
        sql = SQLCompatibilityHelper.get_full_text_search_sql(
            "sqlite",
            "content",
            "test's & \"quotes\""
        )
        # 应该正确处理转义
        assert "LIKE" in sql

    def test_invalid_intervals(self):
        """测试无效的时间间隔"""
        from src.database.sql_compatibility import SQLCompatibilityHelper

        # 负数间隔
        sql = SQLCompatibilityHelper.get_interval_sql("postgresql", interval_value=-1)
        assert "-1 hour" in sql

        # 零间隔
        sql = SQLCompatibilityHelper.get_interval_sql("postgresql", interval_value=0)
        assert "0 hour" in sql

    def test_large_values(self):
        """测试大值处理"""
        from src.database.sql_compatibility import SQLCompatibilityHelper

        # 大的LIMIT值
        sql = SQLCompatibilityHelper.get_limit_offset_sql("postgresql", 1000000)
        assert "LIMIT 1000000" in sql

        # 大的时间间隔
        sql = SQLCompatibilityHelper.get_interval_sql("postgresql", interval_value=36500)
        assert "36500" in sql  # 100年

    def test_unicode_handling(self):
        """测试Unicode处理"""
        from src.database.sql_compatibility import SQLCompatibilityHelper

        # Unicode搜索词
        unicode_term = "测试搜索"
        sql = SQLCompatibilityHelper.get_full_text_search_sql(
            "sqlite",
            "content",
            unicode_term
        )
        assert unicode_term in sql

    def test_complex_joins(self):
        """测试复杂JOIN操作"""
        from src.database.sql_compatibility import CompatibleQueryBuilder

        builder = CompatibleQueryBuilder("sqlite")

        # 多表JOIN
        query = (builder
                 .select("users")
                 .join("profiles", "users.id = profiles.user_id")
                 .left_join("orders", "users.id = orders.user_id")
                 .right_join("payments", "orders.id = payments.order_id")
                 .build())

        assert "JOIN profiles" in query
        assert "LEFT JOIN orders" in query
        assert "RIGHT JOIN payments" in query

    def test_nested_conditions(self):
        """测试嵌套条件"""
        from src.database.sql_compatibility import CompatibleQueryBuilder

        builder = CompatibleQueryBuilder("postgresql")

        # 构建复杂WHERE条件（模拟）
        query = (builder
                 .select("users")
                 .where("age", ">=", 18)
                 .build())

        assert "WHERE age >= 18" in query


class TestSQLCompatibilityIntegration:
    """测试SQL兼容性集成场景"""

    def test_migrate_query_between_databases(self):
        """测试在数据库间迁移查询"""
        from src.database.sql_compatibility import SQLCompatibilityHelper

        # PostgreSQL查询
        pg_query = """
        SELECT id, name, created_at
        FROM users
        WHERE created_at > NOW() - INTERVAL '7 day'
        ORDER BY RANDOM()
        LIMIT 10
        """

        # 转换为SQLite
        sqlite_elements = []
        sqlite_elements.append(SQLCompatibilityHelper.get_interval_sql("sqlite", interval_value=7, interval_unit="day"))
        sqlite_elements.append(SQLCompatibilityHelper.get_random_function_sql("sqlite"))

        # 验证转换后的元素
        assert any("datetime" in elem for elem in sqlite_elements)
        assert any("RANDOM()" in elem for elem in sqlite_elements)

    def test_build_full_text_search(self):
        """测试构建全文搜索查询"""
        from src.database.sql_compatibility import CompatibleQueryBuilder

        # PostgreSQL全文搜索
        builder = CompatibleQueryBuilder("postgresql")
        search_sql = SQLCompatibilityHelper.get_full_text_search_sql(
            "postgresql",
            "title || ' ' || content",
            "search term"
        )

        assert "to_tsvector" in search_sql
        assert "plainto_tsquery" in search_sql

        # SQLite LIKE搜索
        builder = CompatibleQueryBuilder("sqlite")
        search_sql = SQLCompatibilityHelper.get_full_text_search_sql(
            "sqlite",
            "content",
            "search term"
        )

        assert "LIKE" in search_sql
        assert "%search term%" in search_sql

    def test_date_time_operations(self):
        """测试日期时间操作"""
        from src.database.sql_compatibility import SQLCompatibilityHelper

        db_types = ["postgresql", "sqlite", "mysql"]

        for db_type in db_types:
            # 时间间隔
            interval_sql = SQLCompatibilityHelper.get_interval_sql(
                db_type,
                interval_value=1,
                interval_unit="hour"
            )

            # EPOCH提取
            epoch_sql = SQLCompatibilityHelper.get_epoch_extract_sql(
                db_type,
                "timestamp_col"
            )

            # 验证生成的SQL是有效的
            assert len(interval_sql) > 0
            assert len(epoch_sql) > 0

    def test_aggregation_functions(self):
        """测试聚合函数"""
        from src.database.sql_compatibility import SQLCompatibilityHelper

        db_types = ["postgresql", "sqlite", "mysql"]

        for db_type in db_types:
            # GROUP CONCAT
            concat_sql = SQLCompatibilityHelper.get_group_concat_sql(db_type, "column")
            assert len(concat_sql) > 0

            # 随机函数
            random_sql = SQLCompatibilityHelper.get_random_function_sql(db_type)
            assert len(random_sql) > 0

    def test_json_operations(self):
        """测试JSON操作"""
        from src.database.sql_compatibility import SQLCompatibilityHelper

        db_types = ["postgresql", "sqlite", "mysql"]

        for db_type in db_types:
            json_sql = SQLCompatibilityHelper.get_json_extract_sql(
                db_type,
                "json_column",
                "$.path.to.field"
            )
            assert len(json_sql) > 0

    def test_cross_database_compatibility(self):
        """测试跨数据库兼容性"""
        from src.database.sql_compatibility import SQLCompatibilityHelper

        # 构建一个查询，在不同数据库中使用不同的语法
        base_query = os.getenv("TEST_SQL_COMPATIBILITY_COMPLETE_BASE_QUERY_670")

        db_specific_clauses = {}
        for db_type in ["postgresql", "sqlite", "mysql"]:
            # 为每种数据库生成时间条件
            time_clause = f"created_at > {SQLCompatibilityHelper.get_interval_sql(db_type, interval_value=1, interval_unit='day')}"
            db_specific_clauses[db_type] = base_query + time_clause

        # 验证每种数据库都有适当的语法
        assert "INTERVAL" in db_specific_clauses["postgresql"]
        assert "datetime" in db_specific_clauses["sqlite"]
        assert len(db_specific_clauses["mysql"]) > 0


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])