"""SQL兼容性工具模块测试"""

import pytest
from sqlalchemy import Engine, create_engine, text
from sqlalchemy.ext.asyncio import AsyncEngine, create_async_engine

from src.database.sql_compatibility import (
    SQLCompatibilityHelper,
    CompatibleQueryBuilder,
    get_db_type_from_engine,
    create_compatible_query_builder
)


class TestSQLCompatibilityHelper:
    """测试SQL兼容性助手类"""

    def test_detect_database_type_from_url_sqlite(self):
        """测试从URL检测SQLite数据库"""
        # 测试标准SQLite URL
        assert SQLCompatibilityHelper.detect_database_type("sqlite:///test.db") == "sqlite"
        # 测试内存SQLite
        assert SQLCompatibilityHelper.detect_database_type("sqlite:///:memory:") == "sqlite"
        # 测试异步SQLite
        assert SQLCompatibilityHelper.detect_database_type("sqlite+aiosqlite:///test.db") == "sqlite"

    def test_detect_database_type_from_url_postgresql(self):
        """测试从URL检测PostgreSQL数据库"""
        # 测试标准PostgreSQL URL
        assert SQLCompatibilityHelper.detect_database_type("postgresql://user:pass@localhost/db") == "postgresql"
        # 测试psycopg2驱动
        assert SQLCompatibilityHelper.detect_database_type("postgresql+psycopg2://user:pass@localhost/db") == "postgresql"
        # 测试asyncpg驱动
        assert SQLCompatibilityHelper.detect_database_type("postgresql+asyncpg://user:pass@localhost/db") == "postgresql"

    def test_detect_database_type_from_url_mysql(self):
        """测试从URL检测MySQL数据库"""
        assert SQLCompatibilityHelper.detect_database_type("mysql://user:pass@localhost/db") == "mysql"
        assert SQLCompatibilityHelper.detect_database_type("mysql+pymysql://user:pass@localhost/db") == "mysql"
        assert SQLCompatibilityHelper.detect_database_type("mysql+aiomysql://user:pass@localhost/db") == "mysql"

    def test_detect_database_type_from_url_unknown(self):
        """测试未知数据库类型"""
        assert SQLCompatibilityHelper.detect_database_type("oracle://user:pass@localhost/db") == "unknown"
        assert SQLCompatibilityHelper.detect_database_type("mssql://user:pass@localhost/db") == "unknown"
        assert SQLCompatibilityHelper.detect_database_type("") == "unknown"

    def test_detect_database_type_from_engine(self):
        """测试从引擎对象检测数据库类型"""
        # 创建SQLite引擎
        sqlite_engine = create_engine("sqlite:///:memory:")
        assert SQLCompatibilityHelper.detect_database_type(sqlite_engine) == "sqlite"

    def test_get_interval_sql_postgresql(self):
        """测试PostgreSQL的间隔SQL"""
        # 测试小时间隔
        sql = SQLCompatibilityHelper.get_interval_sql("postgresql", "NOW()", 24, "hour")
        assert sql == "NOW() - INTERVAL '24 hour'"

        # 测试分钟间隔
        sql = SQLCompatibilityHelper.get_interval_sql("postgresql", "created_at", 30, "minute")
        assert sql == "created_at - INTERVAL '30 minute'"

        # 测试天间隔
        sql = SQLCompatibilityHelper.get_interval_sql("postgresql", "NOW()", 7, "day")
        assert sql == "NOW() - INTERVAL '7 day'"

        # 测试复数形式
        sql = SQLCompatibilityHelper.get_interval_sql("postgresql", "NOW()", 1, "hour")
        assert sql == "NOW() - INTERVAL '1 hour'"

    def test_get_interval_sql_sqlite(self):
        """测试SQLite的间隔SQL"""
        # 测试小时间隔
        sql = SQLCompatibilityHelper.get_interval_sql("sqlite", "datetime('now')", 24, "hour")
        assert sql == "datetime(datetime('now'), '-24 hours')"

        # 测试分钟间隔
        sql = SQLCompatibilityHelper.get_interval_sql("sqlite", "created_at", 30, "minute")
        assert sql == "datetime(created_at, '-30 minutes')"

        # 测试天间隔
        sql = SQLCompatibilityHelper.get_interval_sql("sqlite", "datetime('now')", 7, "day")
        assert sql == "datetime(datetime('now'), '-7 days')"

    def test_get_interval_sql_mysql(self):
        """测试MySQL的间隔SQL"""
        # 测试小时间隔
        sql = SQLCompatibilityHelper.get_interval_sql("mysql", "NOW()", 24, "hour")
        assert sql == "NOW() - INTERVAL '24 hour'"

        # 测试分钟间隔
        sql = SQLCompatibilityHelper.get_interval_sql("mysql", "created_at", 30, "minute")
        assert sql == "created_at - INTERVAL '30 minute'"

        # 测试天间隔
        sql = SQLCompatibilityHelper.get_interval_sql("mysql", "NOW()", 7, "day")
        assert sql == "NOW() - INTERVAL '7 day'"

    def test_get_interval_sql_unknown(self):
        """测试未知数据库类型的间隔SQL"""
        sql = SQLCompatibilityHelper.get_interval_sql("unknown", "NOW()", 24, "hour")
        # 应该返回PostgreSQL语法作为默认
        assert sql == "NOW() - INTERVAL '24 hour'"

    def test_get_epoch_extract_sql(self):
        """测试获取EPOCH提取SQL"""
        # PostgreSQL
        sql = SQLCompatibilityHelper.get_epoch_extract_sql("postgresql", "created_at")
        assert sql == "EXTRACT(EPOCH FROM created_at)"

        # SQLite
        sql = SQLCompatibilityHelper.get_epoch_extract_sql("sqlite", "created_at")
        assert "julianday" in sql
        assert "86400" in sql

        # MySQL（默认PostgreSQL）
        sql = SQLCompatibilityHelper.get_epoch_extract_sql("mysql", "created_at")
        assert sql == "EXTRACT(EPOCH FROM created_at)"

    def test_get_time_diff_sql(self):
        """测试时间差计算SQL"""
        # PostgreSQL
        sql = SQLCompatibilityHelper.get_time_diff_sql("postgresql", "time1", "time2")
        assert sql == "EXTRACT(EPOCH FROM (time1 - time2))"

        # SQLite
        sql = SQLCompatibilityHelper.get_time_diff_sql("sqlite", "time1", "time2")
        assert "julianday" in sql
        assert "86400" in sql

    def test_get_serial_primary_key_sql(self):
        """测试获取自增主键SQL"""
        # PostgreSQL
        sql = SQLCompatibilityHelper.get_serial_primary_key_sql("postgresql", "id")
        assert sql == "id SERIAL PRIMARY KEY"

        # SQLite
        sql = SQLCompatibilityHelper.get_serial_primary_key_sql("sqlite", "id")
        assert sql == "id INTEGER PRIMARY KEY AUTOINCREMENT"

        # MySQL（默认PostgreSQL）
        sql = SQLCompatibilityHelper.get_serial_primary_key_sql("mysql", "id")
        assert sql == "id SERIAL PRIMARY KEY"

    def test_get_current_timestamp_sql(self):
        """测试获取当前时间戳SQL"""
        # PostgreSQL
        assert SQLCompatibilityHelper.get_current_timestamp_sql("postgresql") == "NOW()"

        # SQLite
        assert SQLCompatibilityHelper.get_current_timestamp_sql("sqlite") == "datetime('now')"

        # MySQL（默认PostgreSQL）
        assert SQLCompatibilityHelper.get_current_timestamp_sql("mysql") == "NOW()"

    def test_create_error_logs_table_sql(self):
        """测试创建错误日志表SQL"""
        # PostgreSQL
        sql = SQLCompatibilityHelper.create_error_logs_table_sql("postgresql")
        assert "SERIAL PRIMARY KEY" in sql
        assert "TIMESTAMP DEFAULT NOW()" in sql

        # SQLite
        sql = SQLCompatibilityHelper.create_error_logs_table_sql("sqlite")
        assert "INTEGER PRIMARY KEY AUTOINCREMENT" in sql
        assert "datetime('now')" in sql

        # MySQL（默认PostgreSQL）
        sql = SQLCompatibilityHelper.create_error_logs_table_sql("mysql")
        assert "SERIAL PRIMARY KEY" in sql


class TestCompatibleQueryBuilder:
    """测试兼容性查询构建器"""

    def test_sqlite_builder(self):
        """测试SQLite查询构建器"""
        builder = CompatibleQueryBuilder("sqlite")

        # 测试错误统计查询
        query, params = builder.get_error_statistics_query(24)
        assert "datetime('now'" in query
        assert ":hours_param" in query
        assert params["hours_param"] == "-24"

        # 测试任务错误查询
        query, params = builder.get_task_errors_query(12)
        assert "GROUP BY task_name" in query
        assert params["hours_param"] == "-12"

        # 测试清理查询
        query, params = builder.get_cleanup_old_logs_query(7)
        assert "DELETE FROM error_logs" in query
        assert params["days_param"] == "-7"

    def test_postgresql_builder(self):
        """测试PostgreSQL查询构建器"""
        builder = CompatibleQueryBuilder("postgresql")

        # 测试错误统计查询
        query, params = builder.get_error_statistics_query(24)
        assert "NOW() - INTERVAL" in query
        assert ":hours_interval" in query
        assert params["hours_interval"] == "24 hours"

        # 测试任务错误查询
        query, params = builder.get_task_errors_query(12)
        assert "GROUP BY task_name" in query
        assert params["hours_interval"] == "12 hours"

        # 测试清理查询
        query, params = builder.get_cleanup_old_logs_query(7)
        assert "DELETE FROM error_logs" in query
        assert params["days_interval"] == "7 days"

    def test_deprecated_methods(self):
        """测试已弃用的方法"""
        builder = CompatibleQueryBuilder("sqlite")

        # 这些方法应该仍然工作，但会发出警告
        query = builder.build_error_statistics_query(24)
        assert "datetime('now'" in query

        query = builder.build_task_errors_query(12)
        assert "GROUP BY task_name" in query

        query = builder.build_cleanup_old_logs_query(7)
        assert "DELETE FROM error_logs" in query


class TestUtilityFunctions:
    """测试工具函数"""

    def test_get_db_type_from_engine(self):
        """测试从引擎获取数据库类型"""
        sqlite_engine = create_engine("sqlite:///:memory:")
        db_type = get_db_type_from_engine(sqlite_engine)
        assert db_type == "sqlite"

    def test_create_compatible_query_builder(self):
        """测试创建兼容性查询构建器"""
        sqlite_engine = create_engine("sqlite:///:memory:")
        builder = create_compatible_query_builder(sqlite_engine)
        assert isinstance(builder, CompatibleQueryBuilder)
        assert builder.db_type == "sqlite"


class TestSQLCompatibilityHelperEdgeCases:
    """测试SQL兼容性助手的边界情况"""

    def test_empty_url(self):
        """测试空URL"""
        assert SQLCompatibilityHelper.detect_database_type("") == "unknown"

    def test_none_url(self):
        """测试None URL"""
        # 这种情况应该抛出异常或返回unknown
        with pytest.raises((TypeError, AttributeError)):
            SQLCompatibilityHelper.detect_database_type(None)

    def test_malformed_url(self):
        """测试格式错误的URL"""
        assert SQLCompatibilityHelper.detect_database_type("not-a-url") == "unknown"
        assert SQLCompatibilityHelper.detect_database_type("://missing-protocol") == "unknown"

    def test_zero_interval(self):
        """测试零间隔"""
        sql = SQLCompatibilityHelper.get_interval_sql("postgresql", "NOW()", 0, "hour")
        assert "0 hour" in sql

    def test_negative_interval(self):
        """测试负间隔（虽然在函数内部已经处理了负号）"""
        sql = SQLCompatibilityHelper.get_interval_sql("postgresql", "NOW()", -1, "hour")
        # 函数应该正确处理负值
        assert "'-1 hour'" in sql

    def test_large_interval_values(self):
        """测试大的间隔值"""
        sql = SQLCompatibilityHelper.get_interval_sql("postgresql", "NOW()", 999999, "day")
        assert "999999 day" in sql

    def test_unusual_interval_units(self):
        """测试不常见的间隔单位"""
        # 测试月、年等
        sql = SQLCompatibilityHelper.get_interval_sql("postgresql", "NOW()", 6, "month")
        assert "6 month" in sql

        sql = SQLCompatibilityHelper.get_interval_sql("postgresql", "NOW()", 2, "year")
        assert "2 year" in sql