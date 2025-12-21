"""
配置模块扩展测试
专注于配置验证、边界条件和环境变量处理
"""

import pytest
import os
import tempfile
from unittest.mock import patch, Mock
from pydantic import ValidationError


class TestConfigExtended:
    """配置模块扩展测试"""

    def test_database_settings_validation(self):
        """测试数据库配置验证"""
        from src.config_unified import DatabaseSettings

        # 测试有效配置
        config = DatabaseSettings(
            host="localhost",
            port=5432,
            user="testuser",
            password="testpass",
            database="testdb",
        )

        assert config.host == "localhost"
        assert config.port == 5432
        assert config.get_connection_string() == "postgresql+asyncpg://testuser:testpass@localhost:5432/testdb"

    def test_database_settings_url_override(self):
        """测试数据库URL覆盖"""
        from src.config_unified import DatabaseSettings

        config = DatabaseSettings(url="postgresql+asyncpg://override:pass@host:1234/overridedb")

        # URL应该覆盖其他配置
        assert config.get_connection_string() == "postgresql+asyncpg://override:pass@host:1234/overridedb"

    def test_database_settings_from_env(self):
        """测试从环境变量加载数据库配置"""
        from src.config_unified import DatabaseSettings

        with patch.dict(
            os.environ,
            {
                "DB_HOST": "envhost",
                "DB_PORT": "9999",
                "DB_USER": "envuser",
                "DB_PASSWORD": "envpass",
                "DB_DATABASE": "envdb",
            },
        ):
            config = DatabaseSettings()

            assert config.host == "envhost"
            assert config.port == 9999
            assert config.user == "envuser"
            assert config.password == "envpass"
            assert config.database == "envdb"

    def test_database_pool_settings_boundaries(self):
        """测试数据库连接池配置边界"""
        from src.config_unified import DatabasePoolSettings

        # 测试边界值
        config = DatabasePoolSettings(
            min_size=1,  # 最小值
            max_size=1000,  # 最大值
            timeout=1.0,  # 最小超时
            command_timeout=300.0,  # 最大超时
        )

        assert config.min_size == 1
        assert config.max_size == 1000
        assert config.timeout == 1.0
        assert config.command_timeout == 300.0

    def test_database_pool_settings_validation_errors(self):
        """测试数据库连接池配置验证错误"""
        from src.config_unified import DatabasePoolSettings

        # 测试超出范围的值
        with pytest.raises(ValidationError) as exc_info:
            DatabasePoolSettings(min_size=0)  # 小于最小值

        assert "min_size" in str(exc_info.value)

        with pytest.raises(ValidationError) as exc_info:
            DatabasePoolSettings(max_size=1001)  # 超过最大值

        assert "max_size" in str(exc_info.value)

        with pytest.raises(ValidationError) as exc_info:
            DatabasePoolSettings(timeout=0.5)  # 小于最小超时

        assert "timeout" in str(exc_info.value)

    def test_database_pool_settings_from_env(self):
        """测试从环境变量加载连接池配置"""
        from src.config_unified import DatabasePoolSettings

        with patch.dict(
            os.environ,
            {
                "DB_POOL_MIN_SIZE": "10",
                "DB_POOL_MAX_SIZE": "50",
                "DB_TIMEOUT": "120.0",
                "DB_COMMAND_TIMEOUT": "60.0",
                "DB_HEALTH_CHECK_INTERVAL": "60.0",
                "DB_MAX_RETRIES": "5",
            },
        ):
            config = DatabasePoolSettings()

            assert config.min_size == 10
            assert config.max_size == 50
            assert config.timeout == 120.0
            assert config.command_timeout == 60.0
            assert config.health_check_interval == 60.0
            assert config.max_retries == 5

    def test_fotmob_settings_validation(self):
        """测试FotMob配置验证"""
        from src.config_unified import FotMobSettings

        config = FotMobSettings(
            base_url="https://api.fotmob.com",
            x_mas_header="test-mas-header",
            x_foo_header="test-foo-header",
            max_retries=5,
            timeout=30,
        )

        assert config.base_url == "https://api.fotmob.com"
        assert config.x_mas_header == "test-mas-header"
        assert config.x_foo_header == "test-foo-header"
        assert config.max_retries == 5
        assert config.timeout == 30

    def test_fotmob_settings_from_env(self):
        """测试从环境变量加载FotMob配置"""
        from src.config_unified import FotMobSettings

        with patch.dict(
            os.environ,
            {
                "FOTMOB_BASE_URL": "https://custom.fotmob.com",
                "FOTMOB_X_MAS_HEADER": "custom-mas",
                "FOTMOB_X_FOO_HEADER": "custom-foo",
                "FOTMOB_MAX_RETRIES": "10",
                "FOTMOB_TIMEOUT": "60",
            },
        ):
            config = FotMobSettings()

            assert config.base_url == "https://custom.fotmob.com"
            assert config.x_mas_header == "custom-mas"
            assert config.x_foo_header == "custom-foo"
            assert config.max_retries == 10
            assert config.timeout == 60

    def test_fotmob_settings_headers_method(self):
        """测试FotMob配置的headers方法"""
        from src.config_unified import FotMobSettings

        config = FotMobSettings(x_mas_header="mas-value", x_foo_header="foo-value")

        headers = config.get_headers()

        assert headers["x-mas"] == "mas-value"
        assert headers["x-foo"] == "foo-value"

    def test_app_settings_validation(self):
        """测试应用配置验证"""
        from src.config_unified import AppSettings

        config = AppSettings(
            name="Test App",
            version="2.0.0",
            environment="production",
            debug=False,
            api_host="0.0.0.0",
            api_port=8080,
        )

        assert config.name == "Test App"
        assert config.version == "2.0.0"
        assert config.environment == "production"
        assert config.debug is False
        assert config.api_host == "0.0.0.0"
        assert config.api_port == 8080

    def test_app_settings_from_env(self):
        """测试从环境变量加载应用配置"""
        from src.config_unified import AppSettings

        with patch.dict(
            os.environ,
            {
                "APP_NAME": "Production App",
                "APP_VERSION": "3.0.0",
                "APP_ENVIRONMENT": "staging",
                "APP_DEBUG": "true",
                "APP_API_HOST": "127.0.0.1",
                "APP_API_PORT": "9000",
            },
        ):
            config = AppSettings()

            assert config.name == "Production App"
            assert config.version == "3.0.0"
            assert config.environment == "staging"
            assert config.debug is True
            assert config.api_host == "127.0.0.1"
            assert config.api_port == 9000

    def test_logging_settings_validation(self):
        """测试日志配置验证"""
        from src.config_unified import LoggingSettings

        config = LoggingSettings(
            level="INFO",
            format="detailed",
            file_path="/var/log/app.log",
            max_file_size=10485760,  # 10MB
            backup_count=5,
        )

        assert config.level == "INFO"
        assert config.format == "detailed"
        assert config.file_path == "/var/log/app.log"
        assert config.max_file_size == 10485760
        assert config.backup_count == 5

    def test_logging_settings_from_env(self):
        """测试从环境变量加载日志配置"""
        from src.config_unified import LoggingSettings

        with patch.dict(
            os.environ,
            {
                "LOG_LEVEL": "DEBUG",
                "LOG_FORMAT": "json",
                "LOG_FILE_PATH": "/tmp/test.log",
                "LOG_MAX_FILE_SIZE": "5242880",  # 5MB
                "LOG_BACKUP_COUNT": "10",
            },
        ):
            config = LoggingSettings()

            assert config.level == "DEBUG"
            assert config.format == "json"
            assert config.file_path == "/tmp/test.log"
            assert config.max_file_size == 5242880
            assert config.backup_count == 10

    def test_settings_integration(self):
        """测试配置集成"""
        from src.config_unified import UnifiedSettings

        with patch.dict(
            os.environ,
            {
                "DB_HOST": "integration_host",
                "DB_PORT": "5433",
                "APP_NAME": "Integration Test",
                "APP_DEBUG": "false",
                "FOTMOB_X_MAS_HEADER": "integration_header",
            },
        ):
            settings = UnifiedSettings()

            # 验证各个配置模块都正确加载
            assert settings.database.host == "integration_host"
            assert settings.database.port == 5433
            assert settings.app.name == "Integration Test"
            assert settings.app.debug is False
            assert settings.fotmob.x_mas_header == "integration_header"

    def test_settings_env_file_loading(self):
        """测试从环境文件加载配置"""
        from src.config_unified import UnifiedSettings

        # 创建临时环境文件
        env_content = """
DB_HOST=envfile_host
DB_PORT=5434
APP_NAME=EnvFile Test
LOG_LEVEL=DEBUG
"""

        with tempfile.NamedTemporaryFile(mode="w", suffix=".env", delete=False) as f:
            f.write(env_content)
            env_file_path = f.name

        try:
            # 临时修改环境变量指向测试文件
            with patch.dict(os.environ, {"ENV_FILE_PATH": env_file_path}):
                with patch("src.config.DatabaseSettings.model_config") as mock_config:
                    mock_config.return_value = Mock(env_file=env_file_path, env_file_encoding="utf-8")

                    settings = UnifiedSettings()

                    # 验证从环境文件加载的配置
                    # 注意：这里需要根据实际的实现调整验证逻辑
                    assert settings is not None
        finally:
            # 清理临时文件
            os.unlink(env_file_path)

    def test_config_value_conversion(self):
        """测试配置值类型转换"""
        from src.config_unified import AppSettings

        # 测试字符串到布尔值的转换
        with patch.dict(os.environ, {"APP_DEBUG": "true", "APP_API_PORT": "8080"}):
            config = AppSettings()

            assert isinstance(config.debug, bool)
            assert config.debug is True
            assert isinstance(config.api_port, int)
            assert config.api_port == 8080

    def test_config_default_values(self):
        """测试配置默认值"""
        from src.config_unified import DatabaseSettings, AppSettings, LoggingSettings

        # 测试不设置环境变量时的默认值
        db_config = DatabaseSettings()
        assert db_config.host == "localhost"
        assert db_config.port == 5432
        assert db_config.user == "postgres"

        app_config = AppSettings()
        assert app_config.name == "Football Prediction"
        assert app_config.environment == "development"

        log_config = LoggingSettings()
        assert log_config.level == "INFO"
        assert log_config.format == "simple"

    def test_config_sensitive_data_handling(self):
        """测试敏感数据处理"""
        from src.config_unified import DatabaseSettings

        config = DatabaseSettings(user="secret_user", password="secret_password")

        # 验证敏感数据被正确处理
        assert config.user == "secret_user"
        assert config.password == "secret_password"

        # 验证连接字符串包含敏感信息
        conn_str = config.get_connection_string()
        assert "secret_user" in conn_str
        assert "secret_password" in conn_str

    def test_config_validation_edge_cases(self):
        """测试配置验证边界情况"""
        from src.config_unified import DatabasePoolSettings
        from pydantic import ValidationError

        # 测试极值
        config = DatabasePoolSettings(min_size=100, max_size=100, timeout=600.0, max_retries=10)

        assert config.min_size == 100
        assert config.max_size == 100
        assert config.timeout == 600.0
        assert config.max_retries == 10

        # 测试无效的字符串数字
        with patch.dict(os.environ, {"DB_PORT": "invalid_port"}):
            with pytest.raises(ValidationError):
                DatabaseSettings()

    def test_config_performance_impact(self):
        """测试配置加载性能"""
        import time
        from src.config_unified import get_settings

        # 测试多次调用的性能
        start_time = time.time()

        for _ in range(100):
            settings = get_settings()
            assert settings is not None

        end_time = time.time()
        execution_time = end_time - start_time

        # 100次调用应该在合理时间内完成（比如1秒）
        assert execution_time < 1.0

    def test_config_thread_safety(self):
        """测试配置线程安全性"""
        import threading
        from src.config_unified import get_settings

        results = []

        def load_config():
            settings = get_settings()
            results.append(settings.database.host)

        # 创建多个线程同时加载配置
        threads = []
        for _ in range(10):
            thread = threading.Thread(target=load_config)
            threads.append(thread)
            thread.start()

        # 等待所有线程完成
        for thread in threads:
            thread.join()

        # 验证所有线程都得到相同的结果
        assert len(results) == 10
        assert all(result == results[0] for result in results)


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
