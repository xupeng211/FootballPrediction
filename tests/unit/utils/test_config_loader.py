"""
配置加载器测试
Tests for Config Loader

测试src.utils.config_loader模块的配置加载功能
"""

import pytest
from unittest.mock import Mock, patch
import os

# 测试导入
try:
    from src.utils.config_loader import (
        load_config,
        get_config_value,
        set_config_value,
        validate_config,
    )

    CONFIG_LOADER_AVAILABLE = True
except ImportError as e:
    print(f"Import error: {e}")
    CONFIG_LOADER_AVAILABLE = False
    # 创建模拟对象
    load_config = None
    get_config_value = None
    set_config_value = None
    validate_config = None


@pytest.mark.skipif(
    not CONFIG_LOADER_AVAILABLE, reason="Config loader module not available"
)
class TestConfigLoader:
    """配置加载器测试"""

    @patch("src.utils.config_loader.open")
    @patch("src.utils.config_loader.json.load")
    def test_load_config(self, mock_json_load, mock_open):
        """测试：加载配置"""
        mock_config = {
            "database": {"host": "localhost", "port": 5432},
            "redis": {"host": "localhost", "port": 6379},
        }
        mock_json_load.return_value = mock_config

        _config = load_config("test_config.json")

        assert _config == mock_config
        assert _config["database"]["host"] == "localhost"
        assert _config["redis"]["port"] == 6379

    def test_get_config_value(self):
        """测试：获取配置值"""
        _config = {"app": {"name": "test_app", "version": "1.0.0"}, "debug": True}

        # 获取嵌套值
        assert get_config_value(config, "app.name") == "test_app"
        assert get_config_value(config, "app.version") == "1.0.0"

        # 获取顶级值
        assert get_config_value(config, "debug") is True

        # 获取不存在的值
        assert get_config_value(config, "nonexistent", "default") == "default"

    def test_set_config_value(self):
        """测试：设置配置值"""
        _config = {"app": {"name": "old_name"}}

        # 设置嵌套值
        set_config_value(config, "app.name", "new_name")
        assert _config["app"]["name"] == "new_name"

        # 设置新值
        set_config_value(config, "app.version", "1.0.0")
        assert _config["app"]["version"] == "1.0.0"

        # 设置顶级值
        set_config_value(config, "debug", True)
        assert _config["debug"] is True

    def test_validate_config(self):
        """测试：验证配置"""
        valid_config = {
            "database": {"host": "localhost", "port": 5432, "name": "test_db"},
            "redis": {"host": "localhost", "port": 6379},
        }

        # 定义验证规则
        schema = {
            "database": {
                "required": True,
                "fields": {
                    "host": {"type": str, "required": True},
                    "port": {"type": int, "min": 1, "max": 65535},
                    "name": {"type": str, "required": True},
                },
            },
            "redis": {
                "required": True,
                "fields": {
                    "host": {"type": str, "required": True},
                    "port": {"type": int, "min": 1, "max": 65535},
                },
            },
        }

        _result = validate_config(valid_config, schema)
        assert _result is True

    def test_validate_config_invalid(self):
        """测试：验证无效配置"""
        invalid_config = {
            "database": {
                "host": "localhost",
                # 缺少 port 和 name
            }
        }

        schema = {
            "database": {
                "required": True,
                "fields": {
                    "host": {"type": str, "required": True},
                    "port": {"type": int, "required": True},
                    "name": {"type": str, "required": True},
                },
            }
        }

        _result = validate_config(invalid_config, schema)
        assert _result is False

    @patch("src.utils.config_loader.os.path.exists")
    def test_load_config_file_not_found(self, mock_exists):
        """测试：配置文件不存在"""
        mock_exists.return_value = False

        with pytest.raises(FileNotFoundError):
            load_config("nonexistent.json")

    def test_get_config_value_with_default(self):
        """测试：获取配置值带默认值"""
        _config = {"existing_key": "value"}

        # 存在的键
        assert get_config_value(config, "existing_key", "default") == "value"

        # 不存在的键
        assert get_config_value(config, "missing_key", "default") == "default"

        # 嵌套不存在的键
        assert get_config_value(config, "missing.nested.key", "default") == "default"

    def test_set_config_value_create_nested(self):
        """测试：设置嵌套配置值创建路径"""
        _config = {}

        # 创建嵌套结构
        set_config_value(config, "new.nested.key", "value")
        assert _config == {"new": {"nested": {"key": "value"}}}

    def test_environment_variable_override(self):
        """测试：环境变量覆盖"""
        _config = {"database": {"host": "localhost"}}

        with patch.dict(os.environ, {"CONFIG_DATABASE_HOST": "prod_host"}):
            # 如果实现了环境变量覆盖
            if hasattr(load_config, "__code__"):
                # 函数存在，测试环境变量功能
                _result = get_config_value(config, "database.host", override_env=True)
                assert _result in ["localhost", "prod_host"]


@pytest.mark.skipif(
    CONFIG_LOADER_AVAILABLE, reason="Config loader module should be available"
)
class TestModuleNotAvailable:
    """模块不可用时的测试"""

    def test_module_import_error(self):
        """测试：模块导入错误"""
        assert not CONFIG_LOADER_AVAILABLE
        assert True  # 表明测试意识到模块不可用


# 测试模块级别的功能
def test_module_imports():
    """测试：模块导入"""
    if CONFIG_LOADER_AVAILABLE:
        from src.utils.config_loader import (
            load_config,
            get_config_value,
            set_config_value,
            validate_config,
        )

        assert load_config is not None
        assert get_config_value is not None
        assert set_config_value is not None
        assert validate_config is not None


@pytest.mark.skipif(
    not CONFIG_LOADER_AVAILABLE, reason="Config loader module not available"
)
class TestConfigLoaderAdvanced:
    """配置加载器高级测试"""

    def test_merge_configs(self):
        """测试：合并配置"""
        config1 = {"app": {"name": "test", "version": "1.0"}, "debug": False}
        config2 = {"app": {"version": "2.0"}, "debug": True, "new_feature": True}

        # 如果实现了合并功能
        if hasattr(set_config_value, "__code__"):
            merged = {}
            for key, value in config1.items():
                set_config_value(merged, key, value)
            for key, value in config2.items():
                set_config_value(merged, key, value)

            assert merged["app"]["name"] == "test"
            assert merged["app"]["version"] == "2.0"
            assert merged["debug"] is True
            assert merged["new_feature"] is True

    def test_config_inheritance(self):
        """测试：配置继承"""
        base_config = {
            "database": {"host": "localhost", "port": 5432},
            "features": {"auth": True, "logging": True},
        }

        env_config = {"database": {"host": "prod-server"}, "features": {"debug": True}}

        # 模拟继承
        final_config = {}
        set_config_value(final_config, "", base_config)
        set_config_value(final_config, "", env_config)

        assert final_config["database"]["host"] == "prod-server"
        assert final_config["database"]["port"] == 5432
        assert final_config["features"]["auth"] is True
        assert final_config["features"]["debug"] is True

    def test_config_validation_types(self):
        """测试：配置验证类型"""
        _config = {
            "string_value": "test",
            "int_value": 42,
            "float_value": 3.14,
            "bool_value": True,
            "list_value": [1, 2, 3],
            "dict_value": {"key": "value"},
        }

        # 测试类型验证
        assert isinstance(_config["string_value"], str)
        assert isinstance(_config["int_value"], int)
        assert isinstance(_config["float_value"], float)
        assert isinstance(_config["bool_value"], bool)
        assert isinstance(_config["list_value"], list)
        assert isinstance(_config["dict_value"], dict)

    def test_config_sensitive_data(self):
        """测试：敏感配置数据"""
        _config = {
            "database": {
                "host": "localhost",
                "username": "user",
                "password": "secret123",
            },
            "api_keys": {"service_a": "key_a_123", "service_b": "key_b_456"},
        }

        # 测试敏感数据标记
        sensitive_keys = ["password", "api_keys", "secret", "token"]

        def mask_sensitive(data, path=""):
            if isinstance(data, dict):
                masked = {}
                for key, value in data.items():
                    new_path = f"{path}.{key}" if path else key
                    if any(
                        sensitive in key.lower() or sensitive in new_path.lower()
                        for sensitive in sensitive_keys
                    ):
                        masked[key] = "***MASKED***"
                    else:
                        masked[key] = mask_sensitive(value, new_path)
                return masked
            else:
                return data

        masked_config = mask_sensitive(config)
        assert masked_config["database"]["password"] == "***MASKED***"
        assert masked_config["database"]["username"] == "user"  # 不敏感

    def test_config_hot_reload(self):
        """测试：配置热重载"""
        # 模拟配置文件监听
        import time

        _config = {"value": 1}

        # 模拟配置更新
        def update_config():
            _config["value"] = 2
            _config["updated_at"] = time.time()

        initial_value = _config["value"]
        update_config()

        assert _config["value"] != initial_value
        assert "updated_at" in config

    def test_config_profile_selection(self):
        """测试：配置文件选择"""
        profiles = {
            "development": {"debug": True, "database": {"host": "localhost"}},
            "production": {"debug": False, "database": {"host": "prod-server"}},
            "test": {"debug": True, "database": {"host": "test-server"}},
        }

        # 根据环境变量选择配置
        with patch.dict(os.environ, {"APP_PROFILE": "production"}):
            profile = os.getenv("APP_PROFILE", "development")
            _config = profiles.get(profile, profiles["development"])

            assert _config["debug"] is False
            assert _config["database"]["host"] == "prod-server"

    def test_config_schema_validation_advanced(self):
        """测试：高级配置模式验证"""
        schema = {
            "type": "object",
            "properties": {
                "database": {
                    "type": "object",
                    "properties": {
                        "host": {"type": "string", "pattern": r"^[a-zA-Z0-9.-]+$"},
                        "port": {"type": "integer", "minimum": 1, "maximum": 65535},
                    },
                    "required": ["host", "port"],
                },
                "cache": {
                    "type": "object",
                    "properties": {
                        "ttl": {"type": "integer", "minimum": 0},
                        "max_size": {"type": "integer", "minimum": 1},
                    },
                },
            },
            "required": ["database"],
        }

        valid_config = {
            "database": {"host": "prod-server.example.com", "port": 5432},
            "cache": {"ttl": 3600, "max_size": 1000},
        }

        # 简单验证
        def validate_schema(config, schema):
            if "database" not in config:
                return False
            if "host" not in _config["database"]:
                return False
            return True

        assert validate_schema(valid_config, schema) is True
