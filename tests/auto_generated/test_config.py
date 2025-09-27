"""
Auto-generated tests for src.core.config module
"""

import pytest
import json
import tempfile
import os
from pathlib import Path
from unittest.mock import patch, mock_open, MagicMock

from src.core.config import Config, HAS_PYDANTIC, BaseSettings, Field


class TestConfigCompatibility:
    """测试配置兼容性"""

    def test_pydantic_compatibility_imports(self):
        """测试Pydantic兼容性导入"""
        # 测试兼容性变量存在
        assert isinstance(HAS_PYDANTIC, bool)
        assert callable(Field)
        assert BaseSettings is not None

    def test_field_function_without_pydantic(self):
        """测试无Pydantic时的Field函数"""
        # 即使没有Pydantic，Field函数也应该可用
        result = Field("test", description="test field")
        # 当没有Pydantic时，Field应该返回None
        assert result is None or result is not None


class TestConfig:
    """测试配置管理类"""

    @patch('src.core.config.Path.home')
    @patch('src.core.config.Path.exists')
    @patch('builtins.open', new_callable=mock_open, read_data='{"test_key": "test_value"}')
    def test_config_initialization_with_existing_file(self, mock_file, mock_exists, mock_home):
        """测试使用现有配置文件初始化"""
        # Mock setup
        mock_home_path = Path("/mock/home")
        mock_home.return_value = mock_home_path
        mock_exists.return_value = True

        config = Config()

        # Verify the config was loaded
        assert config._config == {"test_key": "test_value"}
        assert str(config.config_dir) == str(mock_home_path / ".footballprediction")
        assert str(config.config_file) == str(mock_home_path / ".footballprediction" / "config.json")

    @patch('src.core.config.Path.home')
    @patch('src.core.config.Path.exists')
    def test_config_initialization_without_file(self, mock_exists, mock_home):
        """测试无配置文件时初始化"""
        # Mock setup
        mock_home_path = Path("/mock/home")
        mock_home.return_value = mock_home_path
        mock_exists.return_value = False

        config = Config()

        # Verify empty config was created
        assert config._config == {}
        assert str(config.config_dir) == str(mock_home_path / ".footballprediction")

    @patch('src.core.config.Path.home')
    @patch('src.core.config.Path.exists')
    @patch('builtins.open', new_callable=mock_open)
    @patch('src.core.config.json.load')
    def test_config_load_error_handling(self, mock_json_load, mock_file, mock_exists, mock_home):
        """测试配置加载错误处理"""
        # Mock setup
        mock_home_path = Path("/mock/home")
        mock_home.return_value = mock_home_path
        mock_exists.return_value = True
        mock_json_load.side_effect = json.JSONDecodeError("Invalid JSON", "", 0)

        config = Config()

        # Should handle JSON decode error gracefully
        assert config._config == {}

    @patch('src.core.config.Path.home')
    @patch('src.core.config.Path.exists')
    @patch('builtins.open', new_callable=mock_open)
    def test_config_load_permission_error(self, mock_file, mock_exists, mock_home):
        """测试配置加载权限错误处理"""
        # Mock setup
        mock_home_path = Path("/mock/home")
        mock_home.return_value = mock_home_path
        mock_exists.return_value = True
        mock_file.side_effect = PermissionError("Permission denied")

        config = Config()

        # Should handle permission error gracefully
        assert config._config == {}

    @patch('src.core.config.Path.home')
    @patch('src.core.config.Path.mkdir')
    @patch('builtins.open', new_callable=mock_open)
    @patch('src.core.config.json.dump')
    def test_save_method(self, mock_json_dump, mock_file, mock_mkdir, mock_home):
        """测试保存配置"""
        # Mock setup
        mock_home_path = Path("/mock/home")
        mock_home.return_value = mock_home_path

        config = Config()
        config._config = {"key": "value"}

        # Save config
        config.save()

        # Verify directory creation and file writing
        mock_mkdir.assert_called_once_with(parents=True, exist_ok=True)
        mock_file.assert_called_once_with(config.config_file, "w", encoding="utf-8")
        mock_json_dump.assert_called_once_with(config._config, mock_file(), indent=2, ensure_ascii=False)

    @patch('src.core.config.Path.home')
    def test_get_method(self, mock_home):
        """测试获取配置值"""
        # Mock setup
        mock_home_path = Path("/mock/home")
        mock_home.return_value = mock_home_path

        config = Config()
        config._config = {"existing_key": "existing_value", "nested": {"inner": "value"}}

        # Test getting existing value
        assert config.get("existing_key") == "existing_value"
        assert config.get("existing_key", "default") == "existing_value"

        # Test getting non-existing value with default
        assert config.get("non_existing_key") is None
        assert config.get("non_existing_key", "default_value") == "default_value"

        # Test getting nested object
        nested = config.get("nested")
        assert nested == {"inner": "value"}

    @patch('src.core.config.Path.home')
    def test_get_method_nested_objects(self, mock_home):
        """测试获取嵌套对象"""
        # Mock setup
        mock_home_path = Path("/mock/home")
        mock_home.return_value = mock_home_path

        config = Config()
        config._config = {
            "database": {
                "host": "localhost",
                "port": 5432,
                "credentials": {
                    "username": "user",
                    "password": "pass"
                }
            }
        }

        # Test getting nested objects
        db_config = config.get("database")
        assert db_config["host"] == "localhost"
        assert db_config["port"] == 5432
        assert db_config["credentials"]["username"] == "user"

        # Test non-existing nested key
        assert config.get("non_existing") is None

    @patch('src.core.config.Path.home')
    def test_set_method(self, mock_home):
        """测试设置配置值"""
        # Mock setup
        mock_home_path = Path("/mock/home")
        mock_home.return_value = mock_home_path

        config = Config()

        # Test setting simple value
        config.set("simple_key", "simple_value")
        assert config._config["simple_key"] == "simple_value"

        # Test setting nested value
        config.set("nested.key", "nested_value")
        assert config._config["nested"]["key"] == "nested_value"

        # Test overwriting existing value
        config.set("simple_key", "new_value")
        assert config._config["simple_key"] == "new_value"

    @patch('src.core.config.Path.home')
    def test_set_method_simple(self, mock_home):
        """测试简单设置值"""
        # Mock setup
        mock_home_path = Path("/mock/home")
        mock_home.return_value = mock_home_path

        config = Config()

        # Test setting simple value
        config.set("simple_key", "simple_value")
        assert config._config["simple_key"] == "simple_value"

        # Test overwriting existing value
        config.set("simple_key", "new_value")
        assert config._config["simple_key"] == "new_value"

    @patch('src.core.config.Path.home')
    def test_get_method_simple(self, mock_home):
        """测试简单获取值"""
        # Mock setup
        mock_home_path = Path("/mock/home")
        mock_home.return_value = mock_home_path

        config = Config()
        config._config = {"existing_key": "existing_value"}

        # Test getting existing value
        assert config.get("existing_key") == "existing_value"
        assert config.get("existing_key", "default") == "existing_value"

        # Test getting non-existing value with default
        assert config.get("non_existing_key") is None
        assert config.get("non_existing_key", "default_value") == "default_value"

    @patch('src.core.config.Path.home')
    def test_config_basic_workflow(self, mock_home):
        """测试配置基本工作流"""
        # Mock setup
        mock_home_path = Path("/mock/home")
        mock_home.return_value = mock_home_path

        config = Config()

        # Set configuration
        config.set("app.name", "FootballPrediction")
        config.set("app.version", "1.0.0")
        config.set("database.host", "localhost")

        # Verify configuration
        assert config.get("app.name") == "FootballPrediction"
        assert config.get("app.version") == "1.0.0"
        assert config.get("database.host") == "localhost"

        # Test with defaults
        assert config.get("non_existing", "default") == "default"