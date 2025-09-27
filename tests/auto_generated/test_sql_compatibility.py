"""
Auto-generated tests for src.database.sql_compatibility module
"""

import pytest
from unittest.mock import MagicMock
from src.database.sql_compatibility import (
    SQLCompatibilityHelper,
    CompatibleQueryBuilder,
    get_db_type_from_engine,
    create_compatible_query_builder
)


class TestSQLCompatibilityHelper:
    """测试SQL兼容性助手类"""

    def test_detect_database_type_sqlite_string(self):
        """测试从字符串检测SQLite数据库"""
        result = SQLCompatibilityHelper.detect_database_type("sqlite:///test.db")
        assert result == "sqlite"

    def test_detect_database_type_postgresql_string(self):
        """测试从字符串检测PostgreSQL数据库"""
        result = SQLCompatibilityHelper.detect_database_type("postgresql://user:pass@localhost/test")
        assert result == "postgresql"

    def test_detect_database_type_mysql_string(self):
        """测试从字符串检测MySQL数据库"""
        result = SQLCompatibilityHelper.detect_database_type("mysql://user:pass@localhost/test")
        assert result == "mysql"

    def test_detect_database_type_unknown_string(self):
        """测试未知数据库类型"""
        result = SQLCompatibilityHelper.detect_database_type("oracle://user:pass@localhost/test")
        assert result == "unknown"

    def test_detect_database_type_from_engine(self):
        """测试从SQLAlchemy引擎检测数据库类型"""
        mock_engine = MagicMock()
        mock_engine.url = "sqlite:///test.db"
        result = SQLCompatibilityHelper.detect_database_type(mock_engine)
        assert result == "sqlite"

    def test_get_interval_sql_postgresql(self):
        """测试PostgreSQL时间间隔SQL"""
        result = SQLCompatibilityHelper.get_interval_sql("postgresql")
        expected = "NOW() - INTERVAL '1 hour'"
        assert result == expected

    def test_get_interval_sql_sqlite(self):
        """测试SQLite时间间隔SQL"""
        result = SQLCompatibilityHelper.get_interval_sql("sqlite")
        expected = "datetime('now', '-1 hours')"
        assert result == expected

    def test_get_interval_sql_sqlite_custom_base(self):
        """测试SQLite自定义基准时间"""
        result = SQLCompatibilityHelper.get_interval_sql("sqlite", base_time="created_at")
        expected = "datetime(created_at, '-1 hours')"
        assert result == expected

    def test_get_interval_sql_custom_parameters(self):
        """测试自定义时间间隔参数"""
        result = SQLCompatibilityHelper.get_interval_sql(
            "postgresql",
            base_time="CURRENT_TIMESTAMP",
            interval_value=7,
            interval_unit="day"
        )
        expected = "CURRENT_TIMESTAMP - INTERVAL '7 day'"
        assert result == expected

    def test_get_epoch_extract_sql_postgresql(self):
        """测试PostgreSQL时间戳提取SQL"""
        result = SQLCompatibilityHelper.get_epoch_extract_sql("postgresql", "created_at")
        expected = "EXTRACT(EPOCH FROM created_at)"
        assert result == expected

    def test_get_epoch_extract_sql_sqlite(self):
        """测试SQLite时间戳提取SQL"""
        result = SQLCompatibilityHelper.get_epoch_extract_sql("sqlite", "created_at")
        expected = "((julianday(created_at) - julianday('1970 - 01 - 01 00:00:00')) * 86400)"
        assert result == expected

    def test_get_time_diff_sql_postgresql(self):
        """测试PostgreSQL时间差SQL"""
        result = SQLCompatibilityHelper.get_time_diff_sql("postgresql", "time1", "time2")
        expected = "EXTRACT(EPOCH FROM (time1 - time2))"
        assert result == expected

    def test_get_time_diff_sql_sqlite(self):
        """测试SQLite时间差SQL"""
        result = SQLCompatibilityHelper.get_time_diff_sql("sqlite", "time1", "time2")
        expected = "((julianday(time1) - julianday(time2)) * 86400)"
        assert result == expected

    def test_get_serial_primary_key_sql_postgresql(self):
        """测试PostgreSQL自增主键SQL"""
        result = SQLCompatibilityHelper.get_serial_primary_key_sql("postgresql")
        expected = "id SERIAL PRIMARY KEY"
        assert result == expected

    def test_get_serial_primary_key_sql_sqlite(self):
        """测试SQLite自增主键SQL"""
        result = SQLCompatibilityHelper.get_serial_primary_key_sql("sqlite")
        expected = "id INTEGER PRIMARY KEY AUTOINCREMENT"
        assert result == expected

    def test_get_serial_primary_key_sql_custom_column(self):
        """测试自定义列名的主键SQL"""
        result = SQLCompatibilityHelper.get_serial_primary_key_sql("postgresql", "user_id")
        expected = "user_id SERIAL PRIMARY KEY"
        assert result == expected

    def test_get_current_timestamp_sql_postgresql(self):
        """测试PostgreSQL当前时间戳SQL"""
        result = SQLCompatibilityHelper.get_current_timestamp_sql("postgresql")
        expected = "NOW()"
        assert result == expected

    def test_get_current_timestamp_sql_sqlite(self):
        """测试SQLite当前时间戳SQL"""
        result = SQLCompatibilityHelper.get_current_timestamp_sql("sqlite")
        expected = "datetime('now')"
        assert result == expected

    def test_create_error_logs_table_sql_postgresql(self):
        """测试PostgreSQL错误日志表创建SQL"""
        result = SQLCompatibilityHelper.create_error_logs_table_sql("postgresql")
        assert "SERIAL PRIMARY KEY" in result
        assert "DEFAULT NOW()" in result
        assert "error_logs" in result

    def test_create_error_logs_table_sql_sqlite(self):
        """测试SQLite错误日志表创建SQL"""
        result = SQLCompatibilityHelper.create_error_logs_table_sql("sqlite")
        assert "INTEGER PRIMARY KEY AUTOINCREMENT" in result
        assert "DEFAULT (datetime('now'))" in result
        assert "error_logs" in result

    def test_create_error_logs_table_sql_unknown(self):
        """测试未知数据库类型回退到PostgreSQL"""
        result = SQLCompatibilityHelper.create_error_logs_table_sql("unknown")
        assert "SERIAL PRIMARY KEY" in result


class TestCompatibleQueryBuilder:
    """测试兼容性查询构建器"""

    def test_init(self):
        """测试初始化"""
        builder = CompatibleQueryBuilder("postgresql")
        assert builder.db_type == "postgresql"
        assert isinstance(builder.helper, SQLCompatibilityHelper)

    def test_build_error_statistics_query_postgresql(self):
        """测试PostgreSQL错误统计查询"""
        builder = CompatibleQueryBuilder("postgresql")
        result = builder.build_error_statistics_query(24)
        assert "COUNT(*) as total_errors" in result
        assert "error_logs" in result
        assert "INTERVAL" in result

    def test_build_error_statistics_query_sqlite(self):
        """测试SQLite错误统计查询"""
        builder = CompatibleQueryBuilder("sqlite")
        result = builder.build_error_statistics_query(24)
        assert "COUNT(*) as total_errors" in result
        assert "error_logs" in result
        assert "datetime('now', '-24 hours')" in result

    def test_build_task_errors_query_postgresql(self):
        """测试PostgreSQL任务错误查询"""
        builder = CompatibleQueryBuilder("postgresql")
        result = builder.build_task_errors_query(12)
        assert "task_name" in result
        assert "COUNT(*) as error_count" in result
        assert "INTERVAL" in result

    def test_build_task_errors_query_sqlite(self):
        """测试SQLite任务错误查询"""
        builder = CompatibleQueryBuilder("sqlite")
        result = builder.build_task_errors_query(12)
        assert "task_name" in result
        assert "COUNT(*) as error_count" in result
        assert "datetime('now', '-12 hours')" in result

    def test_build_type_errors_query_postgresql(self):
        """测试PostgreSQL错误类型查询"""
        builder = CompatibleQueryBuilder("postgresql")
        result = builder.build_type_errors_query(6)
        assert "error_type" in result
        assert "COUNT(*) as error_count" in result
        assert "INTERVAL" in result

    def test_build_type_errors_query_sqlite(self):
        """测试SQLite错误类型查询"""
        builder = CompatibleQueryBuilder("sqlite")
        result = builder.build_type_errors_query(6)
        assert "error_type" in result
        assert "COUNT(*) as error_count" in result
        assert "datetime('now', '-6 hours')" in result

    def test_build_cleanup_old_logs_query_postgresql(self):
        """测试PostgreSQL清理旧日志查询"""
        builder = CompatibleQueryBuilder("postgresql")
        result = builder.build_cleanup_old_logs_query(30)
        assert "DELETE FROM error_logs" in result
        assert "INTERVAL" in result

    def test_build_cleanup_old_logs_query_sqlite(self):
        """测试SQLite清理旧日志查询"""
        builder = CompatibleQueryBuilder("sqlite")
        result = builder.build_cleanup_old_logs_query(30)
        assert "DELETE FROM error_logs" in result
        assert "datetime('now', '-30 days')" in result

    def test_build_task_delay_query_postgresql(self):
        """测试PostgreSQL任务延迟查询"""
        builder = CompatibleQueryBuilder("postgresql")
        result = builder.build_task_delay_query()
        assert "task_name" in result
        assert "AVG(EXTRACT(EPOCH FROM (NOW() - created_at)))" in result
        assert "INTERVAL" in result

    def test_build_task_delay_query_sqlite(self):
        """测试SQLite任务延迟查询"""
        builder = CompatibleQueryBuilder("sqlite")
        result = builder.build_task_delay_query()
        assert "task_name" in result
        assert "AVG((julianday('now') - julianday(created_at)) * 86400)" in result
        assert "datetime('now', '-1 hour')" in result


class TestUtilityFunctions:
    """测试工具函数"""

    def test_get_db_type_from_engine_success(self):
        """测试成功从引擎获取数据库类型"""
        mock_engine = MagicMock()
        mock_engine.url = "postgresql://localhost/test"
        result = get_db_type_from_engine(mock_engine)
        assert result == "postgresql"

    def test_get_db_type_from_engine_failure(self):
        """测试从引擎获取数据库类型失败"""
        mock_engine = MagicMock()
        mock_engine.url = "postgresql://localhost/test"
        # 模拟检测失败
        with pytest.raises(Exception):
            raise Exception("Detection failed")

        # 测试默认回退值
        with patch('src.database.sql_compatibility.SQLCompatibilityHelper.detect_database_type') as mock_detect:
            mock_detect.side_effect = Exception("Detection failed")
            result = get_db_type_from_engine(mock_engine)
            assert result == "postgresql"  # 默认值

    def test_create_compatible_query_builder(self):
        """测试创建兼容性查询构建器"""
        mock_engine = MagicMock()
        mock_engine.url = "sqlite:///test.db"
        result = create_compatible_query_builder(mock_engine)
        assert isinstance(result, CompatibleQueryBuilder)
        assert result.db_type == "sqlite"

    @pytest.mark.parametrize("db_type,url,expected", [
        ("sqlite", "sqlite:///test.db", True),
        ("postgresql", "postgresql://localhost/test", True),
        ("mysql", "mysql://localhost/test", True),
        ("oracle", "oracle://localhost/test", False)
    ])
    def test_database_detection_comprehensive(self, db_type, url, expected):
        """测试数据库检测的综合用例"""
        result = SQLCompatibilityHelper.detect_database_type(url)
        if expected:
            assert result == db_type
        else:
            assert result == "unknown"

    @pytest.mark.parametrize("unit,expected_sqlite", [
        ("hour", "hours"),
        ("day", "days"),
        ("minute", "minutes"),
        ("second", "seconds"),
        ("week", "week"),  # 不在映射中的单位
    ])
    def test_interval_unit_mapping(self, unit, expected_sqlite):
        """测试时间间隔单位映射"""
        result = SQLCompatibilityHelper.get_interval_sql("sqlite", interval_unit=unit)
        assert f"'{expected_sqlite}'" in result