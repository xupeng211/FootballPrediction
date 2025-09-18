"""
测试核心配置模块
"""

import json
import tempfile
from pathlib import Path
from unittest.mock import patch

from src.core.config import Config


class TestConfig:
    """测试Config类"""

    def setup_method(self):
        """每个测试方法前的设置"""
        self.temp_dir = tempfile.mkdtemp()
        self.config_dir = Path(self.temp_dir) / ".footballprediction"
        self.config_file = self.config_dir / "config.json"

    def test_config_init_creates_empty_config(self):
        """测试初始化创建空配置"""
        with patch("pathlib.Path.home", return_value=Path(self.temp_dir)):
            config = Config()
            assert config._config == {}
            assert config.config_dir == self.config_dir
            assert config.config_file == self.config_file

    def test_config_init_loads_existing_file(self):
        """测试初始化时加载现有配置文件"""
        # 创建配置文件
        self.config_dir.mkdir(parents=True, exist_ok=True)
        test_config = {"test_key": "test_value", "number": 42}
        with open(self.config_file, "w", encoding="utf-8") as f:
            json.dump(test_config, f)

        with patch("pathlib.Path.home", return_value=Path(self.temp_dir)):
            config = Config()
            assert config._config == test_config

    def test_config_init_handles_corrupt_file(self):
        """测试初始化时处理损坏的配置文件"""
        # 创建损坏的配置文件
        self.config_dir.mkdir(parents=True, exist_ok=True)
        with open(self.config_file, "w", encoding="utf-8") as f:
            f.write("invalid json {")

        with patch("pathlib.Path.home", return_value=Path(self.temp_dir)):
            with patch("logging.warning") as mock_warning:
                config = Config()
                assert config._config == {}
                mock_warning.assert_called_once()

    def test_get_existing_key(self):
        """测试获取存在的配置项"""
        with patch("pathlib.Path.home", return_value=Path(self.temp_dir)):
            config = Config()
            config._config = {"test_key": "test_value"}

            result = config.get("test_key")
            assert result == "test_value"

    def test_get_nonexistent_key_with_default(self):
        """测试获取不存在的配置项使用默认值"""
        with patch("pathlib.Path.home", return_value=Path(self.temp_dir)):
            config = Config()

            result = config.get("nonexistent", "default_value")
            assert result == "default_value"

    def test_get_nonexistent_key_without_default(self):
        """测试获取不存在的配置项不提供默认值"""
        with patch("pathlib.Path.home", return_value=Path(self.temp_dir)):
            config = Config()

            result = config.get("nonexistent")
            assert result is None

    def test_set_config_value(self):
        """测试设置配置项"""
        with patch("pathlib.Path.home", return_value=Path(self.temp_dir)):
            config = Config()

            config.set("test_key", "test_value")
            assert config._config["test_key"] == "test_value"

    def test_save_config_creates_directory(self):
        """测试保存配置时创建目录"""
        with patch("pathlib.Path.home", return_value=Path(self.temp_dir)):
            config = Config()
            config.set("test_key", "test_value")

            config.save()

            assert self.config_dir.exists()
            assert self.config_file.exists()

    def test_save_config_writes_correct_content(self):
        """测试保存配置写入正确内容"""
        with patch("pathlib.Path.home", return_value=Path(self.temp_dir)):
            config = Config()
            test_data = {"key1": "value1", "key2": 42, "key3": True}
            config._config = test_data

            config.save()

            # 验证文件内容
            with open(self.config_file, "r", encoding="utf-8") as f:
                saved_data = json.load(f)
            assert saved_data == test_data

    def test_save_and_load_integration(self):
        """测试保存和加载的集成测试"""
        with patch("pathlib.Path.home", return_value=Path(self.temp_dir)):
            # 创建第一个配置实例并保存
            config1 = Config()
            config1.set("test_key", "test_value")
            config1.set("number", 123)
            config1.save()

            # 创建第二个配置实例，应该加载之前保存的值
            config2 = Config()
            assert config2.get("test_key") == "test_value"
            assert config2.get("number") == 123


class TestGlobalConfig:
    """测试全局配置实例"""

    def test_global_config_instance_exists(self):
        """测试全局配置实例存在"""
        from src.core.config import config

        assert isinstance(config, Config)
