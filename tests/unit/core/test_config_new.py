from typing import Optional

#!/usr/bin/env python3
"""
配置管理单元测试

测试 src.core.config 模块的功能
"""

import json
import os
import sys
import tempfile

import pytest

# 添加src目录到Python路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../.."))

from src.core.config import Config


class TestConfig:
    """配置管理测试类"""

    @pytest.fixture
    def config(self):
        """创建配置实例"""
        return Config()

    def test_config_initialization(self, config):
        """测试配置初始化"""
        assert config is not None
        assert hasattr(config, "get")
        assert hasattr(config, "set")
        assert hasattr(config, "load_from_file")
        assert hasattr(config, "load_from_dict")

    def test_get_config_value(self, config):
        """测试获取配置值"""
        # 测试默认值
        result = config.get("nonexistent_key", "default_value")
        assert result == "default_value"

        # 测试不存在的键（无默认值）
        result = config.get("nonexistent_key")
        assert result is None

    def test_set_config_value(self, config):
        """测试设置配置值"""
        config.set("test_key", "test_value")
        result = config.get("test_key")
        assert result == "test_value"

        # 测试覆盖现有值
        config.set("test_key", "new_value")
        result = config.get("test_key")
        assert result == "new_value"

    def test_load_from_dict(self, config):
        """测试从字典加载配置"""
        test_dict = {
            "database": {"host": "localhost", "port": 5432, "name": "test_db"},
            "api": {"timeout": 30, "retries": 3},
            "debug": True,
        }

        config.load_from_dict(test_dict)

        assert config.get("database.host") == "localhost"
        assert config.get("database.port") == 5432
        assert config.get("database.name") == "test_db"
        assert config.get("api.timeout") == 30
        assert config.get("api.retries") == 3
        assert config.get("debug") is True

    def test_load_from_file(self, config):
        """测试从文件加载配置"""
        # 创建临时配置文件
        test_config = {
            "app_name": "test_app",
            "version": "1.0.0",
            "settings": {"log_level": "INFO", "max_connections": 100},
        }

        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump(test_config, f)
            temp_file = f.name

        try:
            config.load_from_file(temp_file)

            assert config.get("app_name") == "test_app"
            assert config.get("version") == "1.0.0"
            assert config.get("settings.log_level") == "INFO"
            assert config.get("settings.max_connections") == 100
        finally:
            # 清理临时文件
            os.unlink(temp_file)

    def test_nested_config_access(self, config):
        """测试嵌套配置访问"""
        test_dict = {
            "database": {
                "primary": {"host": "localhost", "port": 5432},
                "secondary": {"host": "backup-server", "port": 5433},
            }
        }

        config.load_from_dict(test_dict)

        # 测试点号分隔的键访问
        assert config.get("database.primary.host") == "localhost"
        assert config.get("database.primary.port") == 5432
        assert config.get("database.secondary.host") == "backup-server"

    def test_config_types(self, config):
        """测试不同类型的配置值"""
        test_config = {
            "string_value": "test_string",
            "integer_value": 42,
            "float_value": 3.14,
            "boolean_value": True,
            "list_value": [1, 2, 3],
            "dict_value": {"nested": "value"},
            "none_value": None,
        }

        config.load_from_dict(test_config)

        assert config.get("string_value") == "test_string"
        assert config.get("integer_value") == 42
        assert config.get("float_value") == 3.14
        assert config.get("boolean_value") is True
        assert config.get("list_value") == [1, 2, 3]
        assert config.get("dict_value") == {"nested": "value"}
        assert config.get("none_value") is None

    def test_config_default_values(self, config):
        """测试默认值处理"""
        # 测试类型转换的默认值
        result = config.get("nonexistent_int", 42)
        assert result == 42

        result = config.get("nonexistent_bool", True)
        assert result is True

        result = config.get("nonexistent_list", [])
        assert result == []

    def test_error_handling(self, config):
        """测试错误处理"""
        # 测试加载不存在的文件
        with pytest.raises((FileNotFoundError, Exception)):
            config.load_from_file("nonexistent_file.json")

        # 测试无效JSON文件
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            f.write("invalid json content")
            invalid_file = f.name

        try:
            with pytest.raises((json.JSONDecodeError, Exception)):
                config.load_from_file(invalid_file)
        finally:
            os.unlink(invalid_file)

    def test_performance_large_config(self, config):
        """测试大配置性能"""
        import time

        # 创建大配置
        large_config = {f"key_{i}": f"value_{i}" for i in range(1000)}
        config.load_from_dict(large_config)

        # 测试读取性能
        start_time = time.time()
        for i in range(100):
            config.get(f"key_{i % 1000}")
        end_time = time.time()

        assert (end_time - start_time) < 2.0  # 应该在2秒内完成

    @pytest.mark.parametrize(
        "key,expected_default",
        [
            ("missing_string", "default"),
            ("missing_int", 0),
            ("missing_bool", False),
            ("missing_list", []),
        ],
    )
    def test_config_defaults_parametrized(self, config, key, expected_default):
        """参数化测试默认值"""
        result = config.get(key, expected_default)
        assert result == expected_default
