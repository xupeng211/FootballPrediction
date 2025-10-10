"""
核心配置模块测试
"""

import pytest
import json
import tempfile
from pathlib import Path
from unittest.mock import patch, MagicMock

from src.core.config import Config, Settings, HAS_PYDANTIC


class TestConfig:
    """配置管理类测试"""

    def test_config_init_without_file(self, tmp_path):
        """测试没有配置文件时的初始化"""
        with patch("src.core.config.Path.home", return_value=tmp_path):
            config = Config()
            assert isinstance(config._config, dict)
            assert len(config._config) == 0

    def test_config_init_with_file(self, tmp_path):
        """测试有配置文件时的初始化"""
        # 创建临时配置文件
        config_dir = tmp_path / ".footballprediction"
        config_dir.mkdir()
        config_file = config_dir / "config.json"
        test_config = {"test_key": "test_value", "number": 123}
        config_file.write_text(json.dumps(test_config), encoding="utf-8")

        with patch("src.core.config.Path.home", return_value=tmp_path):
            config = Config()
            assert config.get("test_key") == "test_value"
            assert config.get("number") == 123

    def test_config_load_invalid_json(self, tmp_path):
        """测试加载无效JSON文件"""
        config_dir = tmp_path / ".footballprediction"
        config_dir.mkdir()
        config_file = config_dir / "config.json"
        config_file.write_text("invalid json content", encoding="utf-8")

        with patch("src.core.config.Path.home", return_value=tmp_path):
            with patch("src.core.config.logging.warning") as mock_warning:
                config = Config()
                mock_warning.assert_called_once()
                assert isinstance(config._config, dict)

    def test_config_get_with_default(self, tmp_path):
        """测试获取配置项（带默认值）"""
        with patch("src.core.config.Path.home", return_value=tmp_path):
            config = Config()
            assert config.get("nonexistent_key") is None
            assert config.get("nonexistent_key", "default") == "default"
            assert config.get("nonexistent_key", 0) == 0

    def test_config_set_and_get(self, tmp_path):
        """测试设置和获取配置项"""
        with patch("src.core.config.Path.home", return_value=tmp_path):
            config = Config()
            config.set("key1", "value1")
            config.set("key2", 123)
            config.set("key3", {"nested": "value"})

            assert config.get("key1") == "value1"
            assert config.get("key2") == 123
            assert config.get("key3") == {"nested": "value"}

    def test_config_save(self, tmp_path):
        """测试保存配置"""
        with patch("src.core.config.Path.home", return_value=tmp_path):
            config = Config()
            config.set("test", "value")
            config.save()

            # 验证文件已创建并包含正确内容
            config_file = tmp_path / ".footballprediction" / "config.json"
            assert config_file.exists()
            saved_config = json.loads(config_file.read_text(encoding="utf-8"))
            assert saved_config == {"test": "value"}

    def test_config_save_creates_directory(self, tmp_path):
        """测试保存配置时创建目录"""
        config_dir = tmp_path / ".footballprediction"

        with patch("src.core.config.Path.home", return_value=tmp_path):
            config = Config()
            config.set("test", "value")
            config.save()

            assert config_dir.exists()
            assert config_dir.is_dir()

    def test_config_key_conversion(self, tmp_path):
        """测试键名转换为字符串"""
        with patch("src.core.config.Path.home", return_value=tmp_path):
            config = Config()
            config.set("123", "numeric_key")
            assert config.get("123") == "numeric_key"
            # 键会被自动转换为字符串
            assert config.get(123) == "numeric_key"

    def test_config_complex_types(self, tmp_path):
        """测试复杂数据类型的配置"""
        with patch("src.core.config.Path.home", return_value=tmp_path):
            config = Config()
            complex_data = {
                "list": [1, 2, 3],
                "dict": {"nested": "value"},
                "tuple": (1, 2, 3),
                "none": None,
                "bool": True,
            }
            config.set("complex", complex_data)
            config.save()

            # 重新加载验证数据持久化
            config2 = Config()
            loaded = config2.get("complex")
            assert loaded["list"] == [1, 2, 3]
            assert loaded["dict"] == {"nested": "value"}
            assert loaded["none"] is None
            assert loaded["bool"] is True


class TestSettings:
    """设置类测试"""

    def test_settings_init(self):
        """测试设置初始化"""
        settings = Settings()
        assert hasattr(settings, "database_url")

    def test_settings_database_url_default(self):
        """测试默认数据库URL"""
        settings = Settings()
        assert "sqlite+aiosqlite" in settings.database_url

    @pytest.mark.skipif(not HAS_PYDANTIC, reason="Pydantic not available")
    def test_settings_with_pydantic(self):
        """测试Pydantic集成"""
        settings = Settings()
        # 如果Pydantic可用，应该有字段验证
        assert settings.database_url is not None
        assert len(settings.database_url) > 0

    @pytest.mark.skipif(HAS_PYDANTIC, reason="Pydantic is available")
    def test_settings_without_pydantic(self):
        """测试没有Pydantic的情况"""
        settings = Settings()
        # 没有Pydantic时应该使用object基类
        assert settings.__class__.__bases__ == (object,)
