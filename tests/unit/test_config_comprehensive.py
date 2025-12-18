"""
配置管理全面测试
专注于提升配置模块的测试覆盖率，特别是未覆盖的部分
"""

import pytest
import os
import tempfile
from pathlib import Path
from unittest.mock import patch, Mock
from pydantic import ValidationError


class TestConfigCoreFunctionality:
    """配置核心功能测试"""

    def test_settings_creation_minimal(self):
        """测试最小配置创建"""
        from src.config import Settings, DatabaseConfig, APIConfig, RedisConfig

        # 测试最小必需配置
        db_config = DatabaseConfig(
            host="localhost",
            port=5432,
            name="test_db",
            user="test_user",
            password="test_pass",
        )

        api_config = APIConfig(host="0.0.0.0", port=8000)

        redis_config = RedisConfig(enabled=False)

        settings = Settings(database=db_config, api=api_config, redis=redis_config)

        assert settings.database.host == "localhost"
        assert settings.database.port == 5432
        assert settings.api.port == 8000
        assert settings.redis.enabled == False

    def test_settings_with_full_config(self):
        """测试完整配置创建"""
        from src.config import (
            Settings,
            DatabaseConfig,
            APIConfig,
            RedisConfig,
            FotMobConfig,
        )

        settings = Settings(
            environment="production",
            debug=False,
            database=DatabaseConfig(
                host="prod-db.example.com",
                port=5432,
                name="football_prediction",
                user="app_user",
                password="secure_password",
                pool_size=20,
                max_overflow=30,
                echo=False,
            ),
            api=APIConfig(host="0.0.0.0", port=8000, workers=4, reload=False),
            redis=RedisConfig(
                enabled=True,
                host="redis.example.com",
                port=6379,
                db=0,
                password="redis_password",
            ),
            fotmob=FotMobConfig(
                enabled=True,
                base_url="https://www.fotmob.com/api",
                x_mas_header="test_header",
                x_foo_header="test_foo",
            ),
        )

        assert settings.environment == "production"
        assert settings.debug == False
        assert settings.database.pool_size == 20
        assert settings.redis.enabled == True
        assert settings.fotmob.enabled == True

    def test_config_defaults(self):
        """测试配置默认值"""
        from src.config import get_settings

        # 测试默认设置
        with patch.dict(os.environ, {}, clear=True):
            settings = get_settings()

            assert settings.environment == "development"
            assert settings.debug == True
            assert settings.database.host == "localhost"
            assert settings.database.port == 5432
            assert settings.api.host == "0.0.0.0"
            assert settings.api.port == 8000
            assert settings.redis.enabled == True


class TestConfigEnvironmentVariables:
    """环境变量配置测试"""

    def test_database_env_variables(self):
        """测试数据库环境变量"""
        from src.config import get_settings

        env_vars = {
            "DB_HOST": "env-host",
            "DB_PORT": "5433",
            "DB_NAME": "env_db",
            "DB_USER": "env_user",
            "DB_PASSWORD": "env_pass",
            "DB_POOL_SIZE": "15",
        }

        with patch.dict(os.environ, env_vars):
            settings = get_settings()

            assert settings.database.host == "env-host"
            assert settings.database.port == 5433
            assert settings.database.name == "env_db"
            assert settings.database.user == "env_user"
            assert settings.database.password == "env_pass"
            assert settings.database.pool_size == 15

    def test_api_env_variables(self):
        """测试API环境变量"""
        from src.config import get_settings

        env_vars = {
            "API_HOST": "api-host",
            "API_PORT": "9000",
            "API_WORKERS": "8",
            "API_RELOAD": "false",
        }

        with patch.dict(os.environ, env_vars):
            settings = get_settings()

            assert settings.api.host == "api-host"
            assert settings.api.port == 9000
            assert settings.api.workers == 8
            assert settings.api.reload == False

    def test_redis_env_variables(self):
        """测试Redis环境变量"""
        from src.config import get_settings

        env_vars = {
            "REDIS_ENABLED": "false",
            "REDIS_HOST": "redis-host",
            "REDIS_PORT": "6380",
            "REDIS_DB": "1",
            "REDIS_PASSWORD": "redis_pass",
        }

        with patch.dict(os.environ, env_vars):
            settings = get_settings()

            assert settings.redis.enabled == False
            assert settings.redis.host == "redis-host"
            assert settings.redis.port == 6380
            assert settings.redis.db == 1
            assert settings.redis.password == "redis_pass"

    def test_fotmob_env_variables(self):
        """测试FotMob环境变量"""
        from src.config import get_settings

        env_vars = {
            "FOTMOB_ENABLED": "true",
            "FOTMOB_BASE_URL": "https://api.fotmob.test",
            "FOTMOB_X_MAS_HEADER": "test_mas_header",
            "FOTMOB_X_FOO_HEADER": "test_foo_header",
        }

        with patch.dict(os.environ, env_vars):
            settings = get_settings()

            assert settings.fotmob.enabled == True
            assert settings.fotmob.base_url == "https://api.fotmob.test"
            assert settings.fotmob.x_mas_header == "test_mas_header"
            assert settings.fotmob.x_foo_header == "test_foo_header"


class TestConfigValidation:
    """配置验证测试"""

    def test_invalid_port_numbers(self):
        """测试无效端口号"""
        from src.config import DatabaseConfig, APIConfig, RedisConfig
        from pydantic import ValidationError

        # 测试数据库无效端口
        with pytest.raises(ValidationError):
            DatabaseConfig(
                host="localhost",
                port=70000,  # 无效端口
                name="test",
                user="test",
                password="test",
            )

        with pytest.raises(ValidationError):
            DatabaseConfig(
                host="localhost",
                port=-1,  # 无效端口
                name="test",
                user="test",
                password="test",
            )

        # 测试API无效端口
        with pytest.raises(ValidationError):
            APIConfig(host="localhost", port=70000)

        # 测试Redis无效端口
        with pytest.raises(ValidationError):
            RedisConfig(enabled=True, host="localhost", port=70000)

    def test_invalid_boolean_values(self):
        """测试无效布尔值"""
        from src.config import get_settings

        # 测试无效的布尔值环境变量
        invalid_env = {"REDIS_ENABLED": "maybe"}  # 不是true/false
        with patch.dict(os.environ, invalid_env):
            # 这应该使用默认值或者抛出错误
            try:
                settings = get_settings()
                # 如果没有抛出错误，应该使用默认值
                assert isinstance(settings.redis.enabled, bool)
            except (ValueError, ValidationError):
                # 预期的错误处理
                pass

    def test_required_fields_validation(self):
        """测试必需字段验证"""
        from src.config import DatabaseConfig, APIConfig
        from pydantic import ValidationError

        # 测试缺少必需字段
        with pytest.raises(ValidationError):
            DatabaseConfig()  # 缺少所有必需字段

        with pytest.raises(ValidationError):
            DatabaseConfig(
                host="localhost",
                # 缺少其他必需字段
            )

    def test_url_validation(self):
        """测试URL验证"""
        from src.config import FotMobConfig
        from pydantic import ValidationError

        # 测试无效URL
        with pytest.raises(ValidationError):
            FotMobConfig(enabled=True, base_url="not-a-valid-url")

        # 测试有效URL
        config = FotMobConfig(enabled=True, base_url="https://api.fotmob.com")
        assert config.base_url == "https://api.fotmob.com"


class TestConfigFileLoading:
    """配置文件加载测试"""

    def test_config_from_file(self):
        """测试从文件加载配置"""
        from src.config import load_config_from_file

        # 创建临时配置文件
        config_data = """
database:
  host: file-host
  port: 5432
  name: file_db
  user: file_user
  password: file_pass

api:
  host: 0.0.0.0
  port: 8000

environment: production
debug: false
"""

        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            f.write(config_data)
            config_file = f.name

        try:
            config = load_config_from_file(config_file)
            assert config.database.host == "file-host"
            assert config.environment == "production"
            assert config.debug == False
        finally:
            os.unlink(config_file)

    def test_config_file_not_found(self):
        """测试配置文件不存在"""
        from src.config import load_config_from_file

        with pytest.raises(FileNotFoundError):
            load_config_from_file("nonexistent_config.yaml")

    def test_invalid_config_file(self):
        """测试无效配置文件"""
        from src.config import load_config_from_file

        # 创建无效的YAML文件
        invalid_yaml = """
database:
  host: test
  port: "invalid_port"  # 字符串而不是数字
"""

        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            f.write(invalid_yaml)
            config_file = f.name

        try:
            with pytest.raises((ValidationError, ValueError)):
                load_config_from_file(config_file)
        finally:
            os.unlink(config_file)


class TestConfigUtilityFunctions:
    """配置工具函数测试"""

    def test_get_connection_string(self):
        """测试数据库连接字符串生成"""
        from src.config import DatabaseConfig

        # 测试基本连接字符串
        db_config = DatabaseConfig(
            host="localhost",
            port=5432,
            name="test_db",
            user="test_user",
            password="test_pass",
        )

        connection_string = db_config.get_connection_string()
        expected = "postgresql://test_user:test_pass@localhost:5432/test_db"
        assert connection_string == expected

        # 测试带额外参数的连接字符串
        db_config_with_options = DatabaseConfig(
            host="localhost",
            port=5432,
            name="test_db",
            user="test_user",
            password="test_pass",
            ssl_mode="require",
        )

        connection_string = db_config_with_options.get_connection_string()
        assert "ssl_mode=require" in connection_string

    def test_is_development_environment(self):
        """测试开发环境判断"""
        from src.config import Settings, DatabaseConfig, APIConfig, RedisConfig

        # 测试开发环境
        dev_settings = Settings(
            environment="development",
            database=DatabaseConfig(
                host="localhost", port=5432, name="test", user="test", password="test"
            ),
            api=APIConfig(host="0.0.0.0", port=8000),
            redis=RedisConfig(enabled=False),
        )
        assert dev_settings.is_development() == True
        assert dev_settings.is_production() == False

        # 测试生产环境
        prod_settings = Settings(
            environment="production",
            database=DatabaseConfig(
                host="localhost", port=5432, name="test", user="test", password="test"
            ),
            api=APIConfig(host="0.0.0.0", port=8000),
            redis=RedisConfig(enabled=False),
        )
        assert prod_settings.is_development() == False
        assert prod_settings.is_production() == True

    def test_config_merge(self):
        """测试配置合并"""
        from src.config import merge_configs, DatabaseConfig

        base_config = DatabaseConfig(
            host="base-host",
            port=5432,
            name="base_db",
            user="base_user",
            password="base_pass",
        )

        override_config = {"host": "override-host", "port": 5433}

        merged_config = merge_configs(base_config, override_config)

        assert merged_config.host == "override-host"
        assert merged_config.port == 5433
        assert merged_config.name == "base_db"  # 保持原值
        assert merged_config.user == "base_user"  # 保持原值

    def test_config_export_dict(self):
        """测试配置导出为字典"""
        from src.config import Settings, DatabaseConfig, APIConfig, RedisConfig

        settings = Settings(
            environment="test",
            database=DatabaseConfig(
                host="localhost", port=5432, name="test", user="test", password="test"
            ),
            api=APIConfig(host="0.0.0.0", port=8000),
            redis=RedisConfig(enabled=False),
        )

        config_dict = settings.dict()
        assert config_dict["environment"] == "test"
        assert "database" in config_dict
        assert config_dict["database"]["host"] == "localhost"

        # 测试排除敏感信息
        config_dict_safe = settings.dict(exclude={"database": {"password"}})
        assert "password" not in config_dict_safe["database"]


class TestConfigEdgeCases:
    """配置边缘情况测试"""

    def test_empty_environment_variables(self):
        """测试空环境变量"""
        from src.config import get_settings

        # 测试空字符串环境变量
        env_vars = {
            "REDIS_ENABLED": "",  # 空字符串
            "DB_HOST": "",  # 空字符串
        }

        with patch.dict(os.environ, env_vars):
            settings = get_settings()
            # 应该使用默认值
            assert isinstance(settings.redis.enabled, bool)
            assert settings.database.host != ""

    def test_extreme_values(self):
        """测试极值配置"""
        from src.config import DatabaseConfig

        # 测试极值
        config = DatabaseConfig(
            host="localhost",
            port=65535,  # 最大有效端口
            name="test",
            user="test",
            password="test",
            pool_size=1000,  # 大值
            max_overflow=2000,  # 大值
        )

        assert config.port == 65535
        assert config.pool_size == 1000

    def test_unicode_in_config(self):
        """测试配置中的Unicode字符"""
        from src.config import Settings, DatabaseConfig, APIConfig, RedisConfig

        # 测试Unicode字符
        settings = Settings(
            environment="test",
            database=DatabaseConfig(
                host="localhost",
                port=5432,
                name="测试数据库",
                user="用户",
                password="密码",
            ),
            api=APIConfig(host="0.0.0.0", port=8000),
            redis=RedisConfig(enabled=False),
        )

        assert settings.database.name == "测试数据库"
        assert settings.database.user == "用户"

    def test_config_memory_usage(self):
        """测试配置内存使用"""
        from src.config import get_settings
        import sys

        # 测试配置对象大小
        settings = get_settings()
        config_size = sys.getsizeof(settings)

        # 配置对象不应该过大
        assert config_size < 10000  # 小于10KB


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
