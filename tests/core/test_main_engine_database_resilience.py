#!/usr/bin/env python3
"""
主引擎数据库连接测试
Main Engine Database Connection Tests

测试主引擎的数据库连接功能：
1. 数据库连接初始化
2. 数据库错误处理
3. Schema 初始化
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
import psycopg2
from psycopg2.extras import RealDictCursor

from src.core.main_engine_v5 import initialize_database_schema
from src.core.exceptions import DatabaseError


class TestMainEngineDatabaseResilience:
    """主引擎数据库连接测试"""

    def test_database_schema_initialization_success(self):
        """测试数据库 Schema 初始化成功"""
        with patch("src.core.main_engine_v5.get_settings") as mock_settings, patch("psycopg2.connect") as mock_connect:

            # 模拟配置
            settings_mock = Mock()
            settings_mock.database = Mock()
            settings_mock.database.host = "localhost"
            settings_mock.database.port = 5432
            settings_mock.database.name = "test_db"
            settings_mock.database.user = "test_user"
            settings_mock.database.password.get_secret_value.return_value = "test_pass"
            mock_settings.return_value = settings_mock

            # 模拟数据库连接和游标
            mock_conn = Mock()
            mock_cursor = Mock()
            mock_conn.cursor.return_value = mock_cursor
            mock_connect.return_value = mock_conn

            # 模拟表不存在
            mock_cursor.fetchone.return_value = [False]

            result = initialize_database_schema()

            # 验证连接被正确调用
            mock_connect.assert_called_once()
            mock_cursor.execute.assert_called()
            mock_conn.commit.assert_called()
            mock_conn.close.assert_called()
            assert result is True

    def test_database_schema_already_exists(self):
        """测试数据库 Schema 已存在的情况"""
        with patch("src.core.main_engine_v5.get_settings") as mock_settings, patch("psycopg2.connect") as mock_connect:

            # 模拟配置
            settings_mock = Mock()
            settings_mock.database = Mock()
            settings_mock.database.host = "localhost"
            settings_mock.database.port = 5432
            settings_mock.database.name = "test_db"
            settings_mock.database.user = "test_user"
            settings_mock.database.password.get_secret_value.return_value = "test_pass"
            mock_settings.return_value = settings_mock

            # 模拟数据库连接和游标
            mock_conn = Mock()
            mock_cursor = Mock()
            mock_conn.cursor.return_value = mock_cursor
            mock_connect.return_value = mock_conn

            # 模拟表已存在
            mock_cursor.fetchone.return_value = [True]

            result = initialize_database_schema()

            # 验证连接被正确调用
            mock_connect.assert_called_once()
            mock_cursor.execute.assert_called()
            mock_conn.close.assert_called()
            assert result is True

    def test_database_connection_failure(self):
        """测试数据库连接失败"""
        with patch("src.core.main_engine_v5.get_settings") as mock_settings, patch("psycopg2.connect") as mock_connect:

            # 模拟配置
            settings_mock = Mock()
            settings_mock.database = Mock()
            settings_mock.database.host = "localhost"
            settings_mock.database.port = 5432
            settings_mock.database.name = "test_db"
            settings_mock.database.user = "test_user"
            settings_mock.database.password.get_secret_value.return_value = "test_pass"
            mock_settings.return_value = settings_mock

            # 模拟连接失败
            mock_connect.side_effect = psycopg2.OperationalError("Connection failed")

            with pytest.raises(Exception):
                initialize_database_schema()

    def test_database_cursor_operation_failure(self):
        """测试数据库游标操作失败"""
        with patch("src.core.main_engine_v5.get_settings") as mock_settings, patch("psycopg2.connect") as mock_connect:

            # 模拟配置
            settings_mock = Mock()
            settings_mock.database = Mock()
            settings_mock.database.host = "localhost"
            settings_mock.database.port = 5432
            settings_mock.database.name = "test_db"
            settings_mock.database.user = "test_user"
            settings_mock.database.password.get_secret_value.return_value = "test_pass"
            mock_settings.return_value = settings_mock

            # 模拟数据库连接
            mock_conn = Mock()
            mock_connect.return_value = mock_conn

            # 模拟游标操作失败
            mock_conn.cursor.side_effect = psycopg2.Error("Cursor creation failed")

            with pytest.raises(Exception):
                initialize_database_schema()

    def test_database_sql_execution_failure(self):
        """测试 SQL 执行失败"""
        with patch("src.core.main_engine_v5.get_settings") as mock_settings, patch("psycopg2.connect") as mock_connect:

            # 模拟配置
            settings_mock = Mock()
            settings_mock.database = Mock()
            settings_mock.database.host = "localhost"
            settings_mock.database.port = 5432
            settings_mock.database.name = "test_db"
            settings_mock.database.user = "test_user"
            settings_mock.database.password.get_secret_value.return_value = "test_pass"
            mock_settings.return_value = settings_mock

            # 模拟数据库连接和游标
            mock_conn = Mock()
            mock_cursor = Mock()
            mock_conn.cursor.return_value.__enter__.return_value = mock_cursor
            mock_connect.return_value = mock_conn

            # 模拟表不存在
            mock_cursor.fetchone.return_value = [False]

            # 模拟 SQL 执行失败
            mock_cursor.execute.side_effect = psycopg2.Error("SQL execution failed")

            with pytest.raises(Exception):
                initialize_database_schema()

    def test_database_configuration_validation(self):
        """测试数据库配置验证"""
        with patch("src.core.main_engine_v5.get_settings") as mock_settings, patch("psycopg2.connect") as mock_connect:

            # 测试空配置
            settings_mock = Mock()
            settings_mock.database = Mock()
            settings_mock.database.host = None
            settings_mock.database.port = 5432
            settings_mock.database.name = "test_db"
            settings_mock.database.user = "test_user"
            settings_mock.database.password.get_secret_value.return_value = "test_pass"
            mock_settings.return_value = settings_mock

            # 模拟连接失败
            mock_connect.side_effect = psycopg2.OperationalError("Invalid configuration")

            with pytest.raises(Exception):
                initialize_database_schema()

    def test_database_connection_timeout(self):
        """测试数据库连接超时"""
        with patch("src.core.main_engine_v5.get_settings") as mock_settings, patch("psycopg2.connect") as mock_connect:

            # 模拟配置
            settings_mock = Mock()
            settings_mock.database = Mock()
            settings_mock.database.host = "slow-server"
            settings_mock.database.port = 5432
            settings_mock.database.name = "test_db"
            settings_mock.database.user = "test_user"
            settings_mock.database.password.get_secret_value.return_value = "test_pass"
            mock_settings.return_value = settings_mock

            # 模拟连接超时
            mock_connect.side_effect = psycopg2.OperationalError("Connection timeout")

            with pytest.raises(Exception):
                initialize_database_schema()
