#!/usr/bin/env python3
"""
配置模块测试
测试 src.core.config 模块的功能
"""

import json
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch

import pytest

from src.core.config import Config


@pytest.mark.unit
class TestConfig:
    """配置管理类测试"""

    def setup_method(self):
        """每个测试方法前的设置"""
        # 使用临时目录进行测试
        self.temp_dir = Path(tempfile.mkdtemp())
        self.config_file = self.temp_dir / "config.json"

    def test_config_initialization_with_no_file(self):
        """测试没有配置文件时的初始化"""
        with patch("src.core.config.Path.home", return_value=self.temp_dir):
            config = Config()
            assert config.config_dir == self.temp_dir / ".footballprediction"
            assert config.config_file == self.config_dir / "config.json"
            assert config.config == {}

    def test_config_initialization_with_valid_file(self):
        """测试有有效配置文件时的初始化"""
        # 创建测试配置文件
        config_data = {"database_url": "postgresql://test", "debug": True}
        config_dir = self.temp_dir / ".footballprediction"
        config_dir.mkdir()
        config_file = config_dir / "config.json"

        with open(config_file, "w", encoding="utf-8") as f:
            json.dump(config_data, f)

        with patch("src.core.config.Path.home", return_value=self.temp_dir):
            config = Config()
            assert config.config == config_data

    def test_config_initialization_with_invalid_json(self):
        """测试配置文件包含无效JSON时的处理"""
        config_dir = self.temp_dir / ".footballprediction"
        config_dir.mkdir()
        config_file = config_dir / "config.json"

        # 写入无效JSON
        with open(config_file, "w", encoding="utf-8") as f:
            f.write('{"invalid": json}')

        with patch("src.core.config.Path.home", return_value=self.temp_dir):
            config = Config()
            # 应该回退到空配置
            assert config.config == {}

    def test_get_existing_key(self):
        """测试获取存在的配置项"""
        with patch("src.core.config.Path.home", return_value=self.temp_dir):
            config = Config()
            config.config = {"database_url": "postgresql://test"}

            result = config.get("database_url")
            assert result == "postgresql://test"

    def test_get_nonexistent_key_with_default(self):
        """测试获取不存在的配置项（带默认值）"""
        with patch("src.core.config.Path.home", return_value=self.temp_dir):
            config = Config()

            result = config.get("nonexistent", "default_value")
            assert result == "default_value"

    def test_get_nonexistent_key_no_default(self):
        """测试获取不存在的配置项（无默认值）"""
        with patch("src.core.config.Path.home", return_value=self.temp_dir):
            config = Config()

            result = config.get("nonexistent")
            assert result is None

    def test_set_new_key(self):
        """测试设置新配置项"""
        with patch("src.core.config.Path.home", return_value=self.temp_dir):
            config = Config()
            config.set("new_key", "new_value")

            assert config.config["new_key"] == "new_value"

    def test_set_existing_key(self):
        """测试覆盖已存在的配置项"""
        with patch("src.core.config.Path.home", return_value=self.temp_dir):
            config = Config()
            config.config = {"existing_key": "old_value"}
            config.set("existing_key", "new_value")

            assert config.config["existing_key"] == "new_value"

    def test_save_config_success(self):
        """测试成功保存配置"""
        config_dir = self.temp_dir / ".footballprediction"
        config_dir.mkdir()
        config_file = config_dir / "config.json"

        with patch("src.core.config.Path.home", return_value=self.temp_dir):
            config = Config()
            config.config = {"database_url": "postgresql://test"}

            # 模拟保存成功
            config.save()

            # 验证文件被创建并包含正确内容
            assert config_file.exists()
            with open(config_file, "r", encoding="utf-8") as f:
                saved_data = json.load(f)
            assert saved_data == {"database_url": "postgresql://test"}

    def test_save_config_create_directory(self):
        """测试保存配置时自动创建目录"""
        config_dir = self.temp_dir / ".footballprediction"
        config_file = config_dir / "config.json"

        with patch("src.core.config.Path.home", return_value=self.temp_dir):
            config = Config()
            config.config = {"test": "value"}

            # 确保目录不存在
            assert not config_dir.exists()

            config.save()

            # 验证目录和文件都被创建
            assert config_dir.exists()
            assert config_file.exists()

    def test_update_config(self):
        """测试批量更新配置"""
        with patch("src.core.config.Path.home", return_value=self.temp_dir):
            config = Config()
            config.config = {"existing": "value"}

            new_config = {"new_key": "new_value", "existing": "updated"}
            config.update(new_config)

            assert config.config == {"existing": "updated", "new_key": "new_value"}

    def test_delete_existing_key(self):
        """测试删除存在的配置项"""
        with patch("src.core.config.Path.home", return_value=self.temp_dir):
            config = Config()
            config.config = {"delete_me": "value", "keep_me": "value"}

            result = config.delete("delete_me")

            assert result is True
            assert "delete_me" not in config.config
            assert "keep_me" in config.config

    def test_delete_nonexistent_key(self):
        """测试删除不存在的配置项"""
        with patch("src.core.config.Path.home", return_value=self.temp_dir):
            config = Config()
            config.config = {"keep_me": "value"}

            result = config.delete("nonexistent")

            assert result is False
            assert config.config == {"keep_me": "value"}

    def test_clear_config(self):
        """测试清空所有配置"""
        with patch("src.core.config.Path.home", return_value=self.temp_dir):
            config = Config()
            config.config = {"key1": "value1", "key2": "value2"}

            config.clear()

            assert config.config == {}

    def test_has_key_existing(self):
        """测试检查配置项是否存在（存在的情况）"""
        with patch("src.core.config.Path.home", return_value=self.temp_dir):
            config = Config()
            config.config = {"existing_key": "value"}

            result = config.has("existing_key")
            assert result is True

    def test_has_key_nonexistent(self):
        """测试检查配置项是否存在（不存在的情况）"""
        with patch("src.core.config.Path.home", return_value=self.temp_dir):
            config = Config()

            result = config.has("nonexistent_key")
            assert result is False

    def test_get_all_keys(self):
        """测试获取所有配置项的键"""
        with patch("src.core.config.Path.home", return_value=self.temp_dir):
            config = Config()
            config.config = {"key1": "value1", "key2": "value2", "key3": "value3"}

            keys = config.get_all_keys()
            assert set(keys) == {"key1", "key2", "key3"}

    def test_config_file_permission_error_handling(self):
        """测试配置文件权限错误处理"""
        config_dir = self.temp_dir / ".footballprediction"
        config_dir.mkdir()
        config_dir / "config.json"

        with patch("src.core.config.Path.home", return_value=self.temp_dir):
            config = Config()
            config.config = {"test": "value"}

            # 模拟权限错误
            with patch(
                "builtins.open", side_effect=PermissionError("Permission denied")
            ):
                # 应该不抛出异常，只是静默失败
                config.save()
                # 配置仍然在内存中
                assert config.config == {"test": "value"}
