from unittest.mock import Mock, patch, mock_open
"""
配置管理模块测试
Configuration Management Module Tests

测试src/core/config.py中定义的配置管理功能。
Tests configuration management functionality defined in src/core/config.py.
"""

import pytest
import json
import os
import tempfile
from pathlib import Path

# 导入要测试的模块
try:
    from src.core.config import (
        Config,
        Settings,
        get_config,
        get_settings,
        HAS_PYDANTIC,
        SettingsClass,
    )

    CONFIG_AVAILABLE = True
except ImportError:
    CONFIG_AVAILABLE = False


@pytest.mark.skipif(not CONFIG_AVAILABLE, reason="Config module not available")
@pytest.mark.unit

class TestConfig:
    """Config类测试"""

    def setup_method(self):
        """每个测试方法前的设置"""
        # 创建临时目录用于测试
        self.temp_dir = tempfile.mkdtemp()
        self.config_dir = Path(self.temp_dir) / ".footballprediction"
        self.config_file = self.config_dir / "config.json"

    def teardown_method(self):
        """每个测试方法后的清理"""
        # 清理临时目录
        import shutil

        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_config_initialization_without_existing_file(self):
        """测试没有配置文件时的初始化"""
        with patch("src.core.config.Path.home") as mock_home:
            mock_home.return_value = Path(self.temp_dir)

            config = Config()

            assert config.config_dir == self.config_dir
            assert config.config_file == self.config_file
            assert config.config == {}

    def test_config_initialization_with_existing_file(self):
        """测试有配置文件时的初始化"""
        # 创建测试配置文件
        self.config_dir.mkdir(parents=True, exist_ok=True)
        test_config = {"database_url": "test_url", "api_port": 9000}
        with open(self.config_file, "w", encoding="utf-8") as f:
            json.dump(test_config, f)

        with patch("src.core.config.Path.home") as mock_home:
            mock_home.return_value = Path(self.temp_dir)

            config = Config()

            assert config.config == test_config

    def test_config_load_corrupted_file(self):
        """测试加载损坏的配置文件"""
        # 创建损坏的配置文件
        self.config_dir.mkdir(parents=True, exist_ok=True)
        with open(self.config_file, "w", encoding="utf-8") as f:
            f.write("invalid json content")

        with patch("src.core.config.Path.home") as mock_home:
            mock_home.return_value = Path(self.temp_dir)

            with patch("src.core.config.logging") as mock_logging:
                config = Config()

                # 配置应该为空字典
                assert config.config == {}
                # 应该记录警告日志
                mock_logging.warning.assert_called_once()

    def test_config_get_existing_key(self):
        """测试获取存在的配置项"""
        test_config = {"database_url": "test_url", "api_port": 9000}

        with patch("src.core.config.Path.home") as mock_home:
            mock_home.return_value = Path(self.temp_dir)
            # 模拟加载配置
            with patch.object(Config, "_load_config"):
                config = Config()
                config.config = test_config

                assert config.get("database_url") == "test_url"
                assert config.get("api_port") == 9000

    def test_config_get_nonexistent_key_with_default(self):
        """测试获取不存在的配置项（带默认值）"""
        test_config = {"database_url": "test_url"}

        with patch("src.core.config.Path.home") as mock_home:
            mock_home.return_value = Path(self.temp_dir)
            with patch.object(Config, "_load_config"):
                config = Config()
                config.config = test_config

                assert config.get("nonexistent", "default_value") == "default_value"
                assert config.get("nonexistent") is None

    def test_config_get_nonexistent_key_without_default(self):
        """测试获取不存在的配置项（不带默认值）"""
        test_config = {"database_url": "test_url"}

        with patch("src.core.config.Path.home") as mock_home:
            mock_home.return_value = Path(self.temp_dir)
            with patch.object(Config, "_load_config"):
                config = Config()
                config.config = test_config

                assert config.get("nonexistent") is None

    def test_config_set_value(self):
        """测试设置配置项"""
        test_config = {"database_url": "test_url"}

        with patch("src.core.config.Path.home") as mock_home:
            mock_home.return_value = Path(self.temp_dir)
            with patch.object(Config, "_load_config"):
                config = Config()
                config.config = test_config

                config.set("new_key", "new_value")
                assert config.config["new_key"] == "new_value"
                assert config.get("new_key") == "new_value"

    def test_config_set_overwrite_existing(self):
        """测试覆盖已存在的配置项"""
        test_config = {"database_url": "old_url"}

        with patch("src.core.config.Path.home") as mock_home:
            mock_home.return_value = Path(self.temp_dir)
            with patch.object(Config, "_load_config"):
                config = Config()
                config.config = test_config

                config.set("database_url", "new_url")
                assert config.config["database_url"] == "new_url"

    def test_config_save_creates_directory(self):
        """测试保存配置时创建目录"""
        test_config = {"database_url": "test_url"}

        with patch("src.core.config.Path.home") as mock_home:
            mock_home.return_value = Path(self.temp_dir)
            with patch.object(Config, "_load_config"):
                config = Config()
                config.config = test_config

                config.save()

                # 验证目录被创建
                assert self.config_dir.exists()
                assert self.config_dir.is_dir()

    def test_config_save_writes_file(self):
        """测试保存配置写入文件"""
        test_config = {"database_url": "test_url", "api_port": 9000}

        with patch("src.core.config.Path.home") as mock_home:
            mock_home.return_value = Path(self.temp_dir)
            with patch.object(Config, "_load_config"):
                config = Config()
                config.config = test_config

                config.save()

                # 验证文件被创建并包含正确内容
                assert self.config_file.exists()
                with open(self.config_file, "r", encoding="utf-8") as f:
                    saved_config = json.load(f)
                assert saved_config == test_config

    def test_config_save_with_unicode(self):
        """测试保存包含Unicode字符的配置"""
        test_config = {"chinese_key": "中文值", "emoji": "🚀"}

        with patch("src.core.config.Path.home") as mock_home:
            mock_home.return_value = Path(self.temp_dir)
            with patch.object(Config, "_load_config"):
                config = Config()
                config.config = test_config

                config.save()

                # 验证Unicode字符正确保存
                with open(self.config_file, "r", encoding="utf-8") as f:
                    saved_config = json.load(f)
                assert saved_config == test_config

    def test_config_get_string_conversion(self):
        """测试获取配置时的字符串转换"""
        test_config = {"numeric_key": 123}

        with patch("src.core.config.Path.home") as mock_home:
            mock_home.return_value = Path(self.temp_dir)
            with patch.object(Config, "_load_config"):
                config = Config()
                config.config = test_config

                # 应该保持原始类型
                assert config.get("numeric_key") == 123
                assert isinstance(config.get("numeric_key"), int)


@pytest.mark.skipif(not CONFIG_AVAILABLE, reason="Config module not available")
class TestSettings:
    """Settings类测试"""

    def test_settings_initialization_with_pydantic(self):
        """测试使用Pydantic的Settings初始化"""
        if not HAS_PYDANTIC:
            pytest.skip("Pydantic not available")

        settings = Settings()

        # 验证默认值
        assert (
            settings.database_url == "sqlite+aiosqlite:///./data/football_prediction.db"
        )
        assert (
            settings.test_database_url
            == "postgresql+asyncpg://postgres:postgres@db:5432/football_prediction_test"
        )
        assert settings.redis_url == "redis://redis:6379/0"
        assert settings.api_host == "localhost"
        assert settings.api_port == 8000
        assert settings.environment == "development"
        assert settings.log_level == "INFO"
        assert settings.mlflow_tracking_uri == "file:///tmp/mlflow"
        assert settings.api_football_key is None
        assert settings.api_football_url == "https://api-football-v1.p.rapidapi.com/v3"
        assert settings.metrics_enabled is True
        assert isinstance(settings.metrics_tables, list)
        assert "matches" in settings.metrics_tables
        assert settings.metrics_collection_interval == 30
        assert settings.missing_data_defaults_path is None
        assert settings.missing_data_defaults_json is None
        assert isinstance(settings.enabled_services, list)
        assert "ContentAnalysisService" in settings.enabled_services

    def test_settings_initialization_without_pydantic(self):
        """测试不使用Pydantic的Settings初始化"""
        if HAS_PYDANTIC:
            pytest.skip("Pydantic is available")

        settings = Settings()

        # 验证默认值（不使用Pydantic时）
        assert (
            settings.database_url == "sqlite+aiosqlite:///./data/football_prediction.db"
        )
        assert settings.redis_url == "redis://redis:6379/0"
        assert settings.api_host == "localhost"
        assert settings.api_port == 8000

    def test_settings_with_kwargs(self):
        """测试使用kwargs初始化Settings"""
        settings = Settings(
            database_url="custom_url", api_port=9000, environment="production"
        )

        assert settings.database_url == "custom_url"
        assert settings.api_port == 9000
        assert settings.environment == "production"

    def test_settings_from_env_variables(self):
        """测试从环境变量加载配置"""
        # 设置环境变量
        env_vars = {
            "DATABASE_URL": "env://database",
            "API_PORT": "9000",
            "ENVIRONMENT": "production",
            "LOG_LEVEL": "DEBUG",
            "METRICS_ENABLED": "false",
            "METRICS_TABLES": '["table1", "table2"]',
            "ENABLED_SERVICES": "service1,service2,service3",
        }

        with patch.dict(os.environ, env_vars):
            settings = Settings()

            assert settings.database_url == "env://database"
            assert settings.api_port == 9000
            assert settings.environment == "production"
            assert settings.log_level == "DEBUG"
            assert settings.metrics_enabled is False
            assert "table1" in settings.metrics_tables
            assert "service1" in settings.enabled_services

    def test_settings_invalid_env_port(self):
        """测试无效的环境变量端口值"""
        with patch.dict(os.environ, {"API_PORT": "invalid_port"}):
        with patch.dict(os.environ, {"API_PORT": "invalid_port"}):
        with patch.dict(os.environ, {"API_PORT": "invalid_port"}):
            settings = Settings()
            # 应该保持默认值
            assert settings.api_port == 8000

    def test_settings_invalid_env_metrics_enabled(self):
        """测试无效的metrics_enabled环境变量"""
        with patch.dict(os.environ, {"METRICS_ENABLED": "invalid_value"}):
        with patch.dict(os.environ, {"METRICS_ENABLED": "invalid_value"}):
        with patch.dict(os.environ, {"METRICS_ENABLED": "invalid_value"}):
            settings = Settings()
            # 应该保持默认值
            assert settings.metrics_enabled is True

    def test_settings_parse_list_env_json(self):
        """测试解析JSON格式的列表环境变量"""
        list_value = '["item1", "item2", "item3"]'

        settings = Settings()
        result = settings._parse_list_env(list_value)

        assert result == ["item1", "item2", "item3"]

    def test_settings_parse_list_env_comma_separated(self):
        """测试解析逗号分隔的列表环境变量"""
        list_value = "item1, item2, item3"

        settings = Settings()
        result = settings._parse_list_env(list_value)

        assert result == ["item1", "item2", "item3"]

    def test_settings_parse_list_env_empty(self):
        """测试解析空列表环境变量"""
        settings = Settings()

        # 空字符串
        result = settings._parse_list_env("")
        assert result == []

        # 只有空白字符
        result = settings._parse_list_env("   ")
        assert result == []

    def test_settings_parse_list_env_with_whitespace(self):
        """测试解析包含空白字符的列表环境变量"""
        list_value = " item1 , item2 ,  item3  "

        settings = Settings()
        result = settings._parse_list_env(list_value)

        assert result == ["item1", "item2", "item3"]

    def test_settings_parse_list_env_invalid_json(self):
        """测试解析无效JSON的列表环境变量"""
        list_value = '[item1, "incomplete json'

        settings = Settings()
        result = settings._parse_list_env(list_value)

        # 应该回退到逗号分隔解析
        assert result == ["[item1", '"incomplete json']

    def test_settings_metrics_tables_default(self):
        """测试metrics_tables的默认值"""
        settings = Settings()

        expected_tables = [
            "matches",
            "teams",
            "leagues",
            "odds",
            "features",
            "raw_match_data",
            "raw_odds_data",
            "raw_scores_data",
            "data_collection_logs",
        ]

        assert settings.metrics_tables == expected_tables

    def test_settings_enabled_services_default(self):
        """测试enabled_services的默认值"""
        settings = Settings()

        expected_services = [
            "ContentAnalysisService",
            "UserProfileService",
            "DataProcessingService",
        ]

        assert settings.enabled_services == expected_services


@pytest.mark.skipif(not CONFIG_AVAILABLE, reason="Config module not available")
class TestGlobalFunctions:
    """全局函数测试"""

    def test_get_config_singleton(self):
        """测试get_config返回单例"""
        config1 = get_config()
        config2 = get_config()

        assert config1 is config2
        assert isinstance(config1, Config)

    def test_get_settings_returns_instance(self):
        """测试get_settings返回Settings实例"""
        settings = get_settings()

        assert isinstance(settings, Settings)

    def test_get_settings_different_instances(self):
        """测试get_settings每次返回新实例"""
        settings1 = get_settings()
        settings2 = get_settings()

        # 应该是不同的实例（除非实现了单例模式）
        assert isinstance(settings1, Settings)
        assert isinstance(settings2, Settings)


@pytest.mark.skipif(not CONFIG_AVAILABLE, reason="Config module not available")
class TestPydanticCompatibility:
    """Pydantic兼容性测试"""

    def test_has_pydantic_flag(self):
        """测试HAS_PYDANTIC标志"""
        # 只验证标志存在，具体值取决于环境
        assert isinstance(HAS_PYDANTIC, bool)

    def test_settings_class_type(self):
        """测试SettingsClass类型"""
        if HAS_PYDANTIC:
            # 应该是BaseSettings类
            from pydantic_settings import BaseSettings

            assert SettingsClass is BaseSettings
        else:
            # 应该是object类
            assert SettingsClass is object

    @pytest.mark.skipif(not HAS_PYDANTIC, reason="Pydantic not available")
    def test_pydantic_settings_model_config(self):
        """测试Pydantic设置的model_config"""
        settings = Settings()

        # 检查是否有model_config属性
        if hasattr(settings, "model_config"):
            config = settings.model_config
            assert "env_file" in config
            assert config["env_file"] == ".env"
            assert config["extra"] == "allow"

    @pytest.mark.skipif(not HAS_PYDANTIC, reason="Pydantic not available")
    def test_pydantic_settings_validation(self):
        """测试Pydantic设置验证"""
        # Pydantic会自动验证类型
        settings = Settings()

        # 这些属性应该有正确的类型
        assert isinstance(settings.database_url, str)
        assert isinstance(settings.api_port, int)
        assert isinstance(settings.metrics_enabled, bool)
        assert isinstance(settings.metrics_tables, list)
        assert isinstance(settings.enabled_services, list)


@pytest.mark.skipif(not CONFIG_AVAILABLE, reason="Config module not available")
class TestConfigErrorHandling:
    """配置错误处理测试"""

    def test_config_permission_error_on_save(self):
        """测试保存时的权限错误处理"""
        with patch("src.core.config.Path.home") as mock_home:
            mock_home.return_value = Path(self.temp_dir)
            with patch.object(Config, "_load_config"):
                config = Config()
                config.config = {"test": "value"}

                # 模拟权限错误
                with patch(
                    "builtins.open", side_effect=PermissionError("Permission denied")
                ):
                    with pytest.raises(PermissionError):
                        config.save()

    def test_config_file_not_found_on_load(self):
        """测试加载时文件不存在的情况"""
        with patch("src.core.config.Path.home") as mock_home:
            mock_home.return_value = Path(self.temp_dir)

            config = Config()

            # 文件不存在时应该初始化为空配置
            assert config.config == {}

    def test_config_json_decode_error(self):
        """测试JSON解析错误"""
        # 创建包含无效JSON的文件
        self.config_dir.mkdir(parents=True, exist_ok=True)
        with open(self.config_file, "w", encoding="utf-8") as f:
            f.write('{"invalid": json content}')

        with patch("src.core.config.Path.home") as mock_home:
            mock_home.return_value = Path(self.temp_dir)

            with patch("src.core.config.logging") as mock_logging:
                config = Config()

                # 应该记录警告并初始化空配置
                assert config.config == {}
                mock_logging.warning.assert_called_once()


@pytest.mark.skipif(not CONFIG_AVAILABLE, reason="Config module not available")
class TestConfigIntegration:
    """配置集成测试"""

    def test_config_persistence_workflow(self):
        """测试配置持久化工作流"""
        with patch("src.core.config.Path.home") as mock_home:
            mock_home.return_value = Path(self.temp_dir)

            # 创建配置
            config1 = Config()
            config1.set("database_url", "test_db_url")
            config1.set("api_port", 9000)
            config1.save()

            # 创建新的配置实例，应该能读取保存的配置
            config2 = Config()

            assert config2.get("database_url") == "test_db_url"
            assert config2.get("api_port") == 9000

    def test_config_with_settings_integration(self):
        """测试Config与Settings的集成"""
        with patch("src.core.config.Path.home") as mock_home:
            mock_home.return_value = Path(self.temp_dir)

            config = Config()
            settings = get_settings()

            # 两者应该都能正常工作
            assert isinstance(config, Config)
            assert isinstance(settings, Settings)

            # 设置应该有合理的默认值
            assert hasattr(settings, "database_url")
            assert hasattr(settings, "api_port")

    def test_environment_override_file_config(self):
        """测试环境变量覆盖文件配置"""
        # 创建配置文件
        self.config_dir.mkdir(parents=True, exist_ok=True)
        file_config = {"api_port": 8000, "environment": "development"}
        with open(self.config_file, "w", encoding="utf-8") as f:
            json.dump(file_config, f)

        # 设置环境变量
        env_vars = {"API_PORT": "9000", "ENVIRONMENT": "production"}

        with patch("src.core.config.Path.home") as mock_home:
            mock_home.return_value = Path(self.temp_dir)
            with patch.dict(os.environ, env_vars):
                settings = Settings()

                # 环境变量应该覆盖文件配置
                assert settings.api_port == 9000
                assert settings.environment == "production"
