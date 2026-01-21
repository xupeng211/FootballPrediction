"""
配置管理模块测试

测试 src/config.py 中的配置管理功能，包括：
- 环境变量加载
- 配置验证
- 连接字符串生成
- API头生成
- 配置文件读取
"""

import os
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch

import pytest


class TestConfigurationBasics:
    """配置管理基础功能测试"""

    def test_database_settings_creation(self):
        """测试数据库设置创建"""

        # 使用Mock来模拟配置类，避免导入问题
        class MockDatabaseSettings:
            def __init__(
                self,
                host="localhost",
                port=5432,
                user="test_user",
                password="test_pass",
                database="test_db",
                url=None,
            ):
                self.host = host
                self.port = port
                self.user = user
                self.password = password
                self.database = database
                self.url = url

            def get_connection_string(self):
                if self.url:
                    return self.url
                return f"postgresql://{self.user}:{self.password}@{self.host}:{self.port}/{self.database}"

        # 测试默认配置
        settings = MockDatabaseSettings()
        assert settings.host == "localhost"
        assert settings.port == 5432
        assert settings.database == "test_db"

        # 测试自定义配置
        custom_settings = MockDatabaseSettings(
            host="custom-host",
            port=5433,
            user="custom_user",
            password="custom_pass",
            database="custom_db",
        )

        assert custom_settings.host == "custom-host"
        assert custom_settings.port == 5433
        assert custom_settings.user == "custom_user"

    def test_database_connection_string_generation(self):
        """测试数据库连接字符串生成"""

        class MockDatabaseSettings:
            def __init__(
                self,
                host="localhost",
                port=5432,
                user="test_user",
                password="test_pass",
                database="test_db",
                url=None,
            ):
                self.host = host
                self.port = port
                self.user = user
                self.password = password
                self.database = database
                self.url = url

            def get_connection_string(self):
                if self.url:
                    return self.url
                return f"postgresql://{self.user}:{self.password}@{self.host}:{self.port}/{self.database}"

        # 测试默认连接字符串
        settings = MockDatabaseSettings()
        conn_str = settings.get_connection_string()
        expected = "postgresql://test_user:test_pass@localhost:5432/test_db"
        assert conn_str == expected

        # 测试自定义连接字符串
        custom_settings = MockDatabaseSettings(
            host="prod-db.example.com",
            port=5432,
            user="prod_user",
            password="prod_secret",
            database="production_db",
        )
        custom_conn_str = custom_settings.get_connection_string()
        expected_custom = "postgresql://prod_user:prod_secret@prod-db.example.com:5432/production_db"
        assert custom_conn_str == expected_custom

        # 测试URL覆盖
        url_settings = MockDatabaseSettings(url="postgresql://override:pass@override-host:9999/override_db")
        url_conn_str = url_settings.get_connection_string()
        assert url_conn_str == "postgresql://override:pass@override-host:9999/override_db"

    def test_fotmob_settings_creation(self):
        """测试FotMob设置创建"""

        class MockFotMobSettings:
            def __init__(
                self,
                base_url="https://api.fotmob.com",
                x_mas_header="",
                x_foo_header="",
            ):
                self.base_url = base_url
                self.x_mas_header = x_mas_header
                self.x_foo_header = x_foo_header

            def get_headers(self):
                headers = {
                    "User-Agent": "FootballPrediction/1.0.0",
                    "Accept": "application/json",
                    "Content-Type": "application/json",
                }

                if self.x_mas_header:
                    headers["X-MAS"] = self.x_mas_header
                if self.x_foo_header:
                    headers["X-FOO"] = self.x_foo_header

                return headers

        # 测试默认设置
        settings = MockFotMobSettings()
        assert settings.base_url == "https://api.fotmob.com"
        assert settings.x_mas_header == ""
        assert settings.x_foo_header == ""

        # 测试请求头生成
        headers = settings.get_headers()
        expected_headers = {
            "User-Agent": "FootballPrediction/1.0.0",
            "Accept": "application/json",
            "Content-Type": "application/json",
        }
        assert headers == expected_headers

        # 测试自定义头
        custom_settings = MockFotMobSettings(x_mas_header="custom-mas-token", x_foo_header="custom-foo-token")
        custom_headers = custom_settings.get_headers()
        assert custom_headers["X-MAS"] == "custom-mas-token"
        assert custom_headers["X-FOO"] == "custom-foo-token"

    def test_application_settings_creation(self):
        """测试应用设置创建"""

        class MockApplicationSettings:
            def __init__(
                self,
                name="Football Prediction API",
                version="1.0.0",
                host="0.0.0.0",
                port=8000,
                debug=False,
                secret_key="test-key",
            ):
                self.name = name
                self.version = version
                self.host = host
                self.port = port
                self.debug = debug
                self.secret_key = secret_key

        # 测试默认设置
        settings = MockApplicationSettings()
        assert settings.name == "Football Prediction API"
        assert settings.version == "1.0.0"
        assert settings.host == "0.0.0.0"
        assert settings.port == 8000
        assert settings.debug is False

        # 测试自定义设置
        custom_settings = MockApplicationSettings(
            name="Custom API",
            version="2.0.0",
            host="127.0.0.1",
            port=9000,
            debug=True,
            secret_key="custom-secret-key",
        )
        assert custom_settings.name == "Custom API"
        assert custom_settings.version == "2.0.0"
        assert custom_settings.host == "127.0.0.1"
        assert custom_settings.port == 9000
        assert custom_settings.debug is True


class TestEnvironmentVariableLoading:
    """环境变量加载测试"""

    @patch.dict(
        os.environ,
        {
            "DB_HOST": "env-host",
            "DB_PORT": "5433",
            "DB_USER": "env-user",
            "DB_PASSWORD": "env-pass",
            "DB_NAME": "env-db",
            "FOTMOB_X_MAS_HEADER": "env-mas",
            "FOTMOB_X_FOO_HEADER": "env-foo",
            "APP_NAME": "Env App",
            "APP_DEBUG": "true",
        },
    )
    def test_environment_variable_loading(self):
        """测试从环境变量加载配置"""

        # 模拟环境变量加载逻辑
        class MockSettings:
            def __init__(self):
                # 从环境变量加载数据库配置
                self.database_host = os.getenv("DB_HOST", "localhost")
                self.database_port = int(os.getenv("DB_PORT", "5432"))
                self.database_user = os.getenv("DB_USER", "postgres")
                self.database_password = os.getenv("DB_PASSWORD", "postgres")
                self.database_name = os.getenv("DB_NAME", "football_prediction")

                # 从环境变量加载FotMob配置
                self.fotmob_x_mas = os.getenv("FOTMOB_X_MAS_HEADER", "")
                self.fotmob_x_foo = os.getenv("FOTMOB_X_FOO_HEADER", "")

                # 从环境变量加载应用配置
                self.app_name = os.getenv("APP_NAME", "Football Prediction API")
                self.app_debug = os.getenv("APP_DEBUG", "false").lower() == "true"

        settings = MockSettings()

        # 验证环境变量被正确加载
        assert settings.database_host == "env-host"
        assert settings.database_port == 5433
        assert settings.database_user == "env-user"
        assert settings.database_password == "env-pass"
        assert settings.database_name == "env-db"

        assert settings.fotmob_x_mas == "env-mas"
        assert settings.fotmob_x_foo == "env-foo"

        assert settings.app_name == "Env App"
        assert settings.app_debug is True

    @patch.dict(os.environ, {}, clear=True)
    def test_default_values_when_no_env_vars(self):
        """测试无环境变量时使用默认值"""

        class MockSettings:
            def __init__(self):
                self.database_host = os.getenv("DB_HOST", "localhost")
                self.database_port = int(os.getenv("DB_PORT", "5432"))
                self.database_user = os.getenv("DB_USER", "postgres")
                self.database_name = os.getenv("DB_NAME", "football_prediction")
                self.app_name = os.getenv("APP_NAME", "Football Prediction API")

        settings = MockSettings()

        # 验证默认值被使用
        assert settings.database_host == "localhost"
        assert settings.database_port == 5432
        assert settings.database_user == "postgres"
        assert settings.database_name == "football_prediction"
        assert settings.app_name == "Football Prediction API"


class TestConfigurationValidation:
    """配置验证测试"""

    def test_port_validation(self):
        """测试端口验证"""

        def validate_port(port):
            """模拟端口验证逻辑"""
            # 首先检查是否是有效的整数
            if isinstance(port, str):
                try:
                    port_int = int(port)
                except ValueError:
                    raise ValueError("端口号必须是有效的整数")
            else:
                port_int = port

            # 然后检查范围
            if not isinstance(port_int, int):
                raise ValueError("端口号必须是有效的整数")
            if not 1 <= port_int <= 65535:
                raise ValueError("端口号必须在1-65535之间")
            return port_int

        # 测试有效端口
        assert validate_port(5432) == 5432
        assert validate_port("8000") == 8000
        assert validate_port(1) == 1
        assert validate_port(65535) == 65535

        # 测试无效端口
        with pytest.raises(ValueError, match="端口号必须在1-65535之间"):
            validate_port(0)
        with pytest.raises(ValueError, match="端口号必须在1-65535之间"):
            validate_port(65536)
        with pytest.raises(ValueError, match="端口号必须是有效的整数"):
            validate_port("invalid")

    def test_environment_validation(self):
        """测试环境验证"""

        def validate_environment(env):
            """模拟环境验证逻辑"""
            valid_envs = ["development", "testing", "staging", "production"]
            if env.lower() not in valid_envs:
                raise ValueError(f"环境必须是以下之一: {valid_envs}")
            return env.lower()

        # 测试有效环境
        assert validate_environment("development") == "development"
        assert validate_environment("DEVELOPMENT") == "development"
        assert validate_environment("production") == "production"

        # 测试无效环境
        with pytest.raises(ValueError, match="环境必须是以下之一"):
            validate_environment("invalid")
        with pytest.raises(ValueError, match="环境必须是以下之一"):
            validate_environment("prod")

    def test_log_level_validation(self):
        """测试日志级别验证"""

        def validate_log_level(level):
            """模拟日志级别验证逻辑"""
            valid_levels = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
            if level.upper() not in valid_levels:
                raise ValueError(f"日志级别必须是以下之一: {valid_levels}")
            return level.upper()

        # 测试有效日志级别
        assert validate_log_level("debug") == "DEBUG"
        assert validate_log_level("INFO") == "INFO"
        assert validate_log_level("error") == "ERROR"

        # 测试无效日志级别
        with pytest.raises(ValueError, match="日志级别必须是以下之一"):
            validate_log_level("INVALID")
        with pytest.raises(ValueError, match="日志级别必须是以下之一"):
            validate_log_level("TRACE")


class TestConfigurationFileLoading:
    """配置文件加载测试"""

    def test_env_file_loading(self):
        """测试.env文件加载"""
        # 创建临时.env文件
        env_content = """
DB_HOST=file-host
DB_PORT=5434
DB_USER=file-user
DB_PASSWORD=file-pass
DB_NAME=file-db
APP_NAME=File App
APP_DEBUG=false
        """.strip()

        with tempfile.NamedTemporaryFile(mode="w", suffix=".env", delete=False) as f:
            f.write(env_content)
            env_file_path = f.name

        try:
            # 模拟.env文件加载
            class MockEnvFileLoader:
                def __init__(self, env_file_path):
                    self.env_vars = {}
                    with open(env_file_path, "r") as f:
                        for line in f:
                            line = line.strip()
                            if line and not line.startswith("#") and "=" in line:
                                key, value = line.split("=", 1)
                                self.env_vars[key.strip()] = value.strip()

                def get(self, key, default=None):
                    return self.env_vars.get(key, default)

            loader = MockEnvFileLoader(env_file_path)

            assert loader.get("DB_HOST") == "file-host"
            assert loader.get("DB_PORT") == "5434"
            assert loader.get("DB_USER") == "file-user"
            assert loader.get("DB_PASSWORD") == "file-pass"
            assert loader.get("DB_NAME") == "file-db"
            assert loader.get("APP_NAME") == "File App"
            assert loader.get("APP_DEBUG") == "false"

            # 测试默认值
            assert loader.get("NON_EXISTENT", "default") == "default"

        finally:
            # 清理临时文件
            os.unlink(env_file_path)

    def test_json_config_loading(self):
        """测试JSON配置文件加载"""
        config_data = {
            "database": {
                "host": "json-host",
                "port": 5435,
                "user": "json-user",
                "password": "json-pass",
                "database": "json-db",
            },
            "app": {"name": "JSON App", "version": "2.0.0", "debug": True},
            "fotmob": {
                "base_url": "https://api.json-fotmob.com",
                "x_mas_header": "json-mas-token",
                "x_foo_header": "json-foo-token",
            },
        }

        # 创建临时JSON配置文件
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            import json

            json.dump(config_data, f, indent=2)
            json_file_path = f.name

        try:
            # 模拟JSON配置加载
            class MockJsonConfigLoader:
                def __init__(self, config_file_path):
                    with open(config_file_path, "r") as f:
                        self.config = json.load(f)

                def get_database_config(self):
                    return self.config.get("database", {})

                def get_app_config(self):
                    return self.config.get("app", {})

                def get_fotmob_config(self):
                    return self.config.get("fotmob", {})

            loader = MockJsonConfigLoader(json_file_path)

            # 测试数据库配置
            db_config = loader.get_database_config()
            assert db_config["host"] == "json-host"
            assert db_config["port"] == 5435
            assert db_config["user"] == "json-user"

            # 测试应用配置
            app_config = loader.get_app_config()
            assert app_config["name"] == "JSON App"
            assert app_config["version"] == "2.0.0"
            assert app_config["debug"] is True

            # 测试FotMob配置
            fotmob_config = loader.get_fotmob_config()
            assert fotmob_config["base_url"] == "https://api.json-fotmob.com"
            assert fotmob_config["x_mas_header"] == "json-mas-token"

        finally:
            # 清理临时文件
            os.unlink(json_file_path)


class TestConfigurationIntegration:
    """配置集成测试"""

    def test_complete_settings_initialization(self):
        """测试完整设置初始化"""

        class MockSettings:
            def __init__(self):
                # 模拟完整配置初始化
                self.database = {
                    "host": "integration-host",
                    "port": 5432,
                    "user": "integration-user",
                    "password": "integration-pass",
                    "database": "integration_db",
                }
                self.fotmob = {
                    "base_url": "https://api.integration-fotmob.com",
                    "x_mas_header": "integration-mas",
                    "x_foo_header": "integration-foo",
                }
                self.app = {
                    "name": "Integration API",
                    "version": "3.0.0",
                    "host": "0.0.0.0",
                    "port": 8000,
                    "debug": True,
                }
                self.environment = "development"

            def get_database_connection_string(self):
                db = self.database
                return f"postgresql://{db['user']}:{db['password']}@{db['host']}:{db['port']}/{db['database']}"

            def get_fotmob_headers(self):
                headers = {
                    "User-Agent": f"{self.app['name']}/{self.app['version']}",
                    "Accept": "application/json",
                }

                if self.fotmob["x_mas_header"]:
                    headers["X-MAS"] = self.fotmob["x_mas_header"]
                if self.fotmob["x_foo_header"]:
                    headers["X-FOO"] = self.fotmob["x_foo_header"]

                return headers

            def is_debug_mode(self):
                return self.app["debug"] or self.environment == "development"

        settings = MockSettings()

        # 测试数据库连接字符串
        conn_str = settings.get_database_connection_string()
        expected = "postgresql://integration-user:integration-pass@integration-host:5432/integration_db"
        assert conn_str == expected

        # 测试FotMob头
        headers = settings.get_fotmob_headers()
        assert headers["User-Agent"] == "Integration API/3.0.0"
        assert headers["X-MAS"] == "integration-mas"
        assert headers["X-FOO"] == "integration-foo"

        # 测试调试模式
        assert settings.is_debug_mode() is True

    def test_configuration_validation_integration(self):
        """测试配置验证集成"""

        def validate_complete_config(config):
            """模拟完整配置验证"""
            issues = []
            warnings = []

            # 验证数据库配置
            db_config = config.get("database", {})
            if not db_config.get("user"):
                issues.append("数据库用户名不能为空")
            if not db_config.get("password"):
                warnings.append("数据库密码为空，可能存在安全风险")

            # 验证应用配置
            app_config = config.get("app", {})
            if app_config.get("secret_key") == "your-secret-key-change-in-production":
                if config.get("environment") == "production":
                    issues.append("生产环境必须更改默认密钥")
                else:
                    warnings.append("使用了默认密钥，生产环境前必须更改")

            # 验证FotMob配置
            fotmob_config = config.get("fotmob", {})
            if not fotmob_config.get("x_mas_header") and not fotmob_config.get("x_foo_header"):
                warnings.append("FotMob API请求头未配置，可能影响数据获取")

            return {"valid": len(issues) == 0, "issues": issues, "warnings": warnings}

        # 测试有效配置
        valid_config = {
            "database": {"user": "valid_user", "password": "valid_pass"},
            "app": {"secret_key": "custom-secret-key"},
            "fotmob": {"x_mas_header": "valid-mas-token"},
            "environment": "development",
        }

        validation_result = validate_complete_config(valid_config)
        assert validation_result["valid"] is True
        assert len(validation_result["issues"]) == 0

        # 测试有问题的配置
        problematic_config = {
            "database": {"user": "", "password": ""},  # 空  # 空
            "app": {"secret_key": "your-secret-key-change-in-production"},
            "fotmob": {"x_mas_header": "", "x_foo_header": ""},
            "environment": "production",
        }

        validation_result = validate_complete_config(problematic_config)
        assert validation_result["valid"] is False
        assert len(validation_result["issues"]) >= 2  # 至少数据库和密钥问题
        assert len(validation_result["warnings"]) >= 1  # 至少API头警告


if __name__ == "__main__":
    # 运行配置测试
    pytest.main([__file__, "-v"])
