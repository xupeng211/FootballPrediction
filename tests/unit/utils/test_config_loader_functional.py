"""
配置加载器测试
Test for config_loader module
"""

import pytest
import json
import tempfile
import os
from pathlib import Path
import sys

# 添加src到路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../../src"))

from src.utils.config_loader import load_config_from_file


@pytest.mark.unit
class TestConfigLoader:
    """配置加载器测试类"""

    def test_load_json_config_returns_dict(self):
        """测试：加载JSON配置返回字典"""
        # 创建临时JSON文件
        config_data = {
            "database": {"host": "localhost", "port": 5432, "name": "test_db"},
            "debug": True,
        }

        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump(config_data, f)
            temp_file = f.name

        try:
            # 测试加载配置
            result = load_config_from_file(temp_file)

            assert result == config_data
            assert result["database"]["host"] == "localhost"
            assert result["debug"] is True
        finally:
            os.unlink(temp_file)

    def test_load_yaml_config_returns_dict(self):
        """测试：加载YAML配置返回字典"""
        yaml_content = """
database:
  host: localhost
  port: 5432
  name: test_db
debug: true
"""

        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            f.write(yaml_content)
            temp_file = f.name

        try:
            # 测试加载配置
            result = load_config_from_file(temp_file)

            assert result["database"]["host"] == "localhost"
            assert result["database"]["port"] == 5432
            assert result["debug"] is True
        finally:
            os.unlink(temp_file)

    def test_load_nonexistent_file_returns_empty_dict(self):
        """测试：加载不存在的文件返回空字典"""
        result = load_config_from_file("/nonexistent/path/config.json")
        assert result == {}

    def test_load_unsupported_extension_returns_empty_dict(self):
        """测试：加载不支持的扩展名返回空字典"""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as f:
            f.write("some content")
            temp_file = f.name

        try:
            result = load_config_from_file(temp_file)
            assert result == {}
        finally:
            os.unlink(temp_file)

    def test_load_invalid_json_returns_empty_dict(self):
        """测试：加载无效JSON返回空字典"""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            f.write("{ invalid json }")
            temp_file = f.name

        try:
            result = load_config_from_file(temp_file)
            assert result == {}
        finally:
            os.unlink(temp_file)

    def test_load_empty_json_file_returns_empty_dict(self):
        """测试：加载空JSON文件返回空字典"""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            f.write("")
            temp_file = f.name

        try:
            result = load_config_from_file(temp_file)
            assert result == {}
        finally:
            os.unlink(temp_file)

    def test_load_empty_yaml_file_returns_empty_dict(self):
        """测试：加载空YAML文件返回空字典"""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yml", delete=False) as f:
            f.write("")
            temp_file = f.name

        try:
            result = load_config_from_file(temp_file)
            assert result == {}
        finally:
            os.unlink(temp_file)

    @pytest.mark.parametrize("extension", [".yaml", ".yml", ".json"])
    def test_load_config_with_different_extensions(self, extension):
        """测试：加载不同扩展名的配置文件"""
        if extension == ".json":
            content = '{"test": "value"}'
        else:  # yaml/yml
            content = "test: value\n"

        with tempfile.NamedTemporaryFile(mode="w", suffix=extension, delete=False) as f:
            f.write(content)
            temp_file = f.name

        try:
            result = load_config_from_file(temp_file)
            assert result["test"] == "value"
        finally:
            os.unlink(temp_file)

    def test_load_config_with_pathlib_path(self):
        """测试：使用Path对象加载配置"""
        config_data = {"test": "pathlib"}

        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump(config_data, f)
            temp_file = Path(f.name)

        try:
            result = load_config_from_file(str(temp_file))
            assert result == config_data
        finally:
            temp_file.unlink()
