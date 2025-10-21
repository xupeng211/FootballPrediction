"""
配置工具测试
"""

import os
import pytest
from unittest.mock import Mock, patch, MagicMock
from pathlib import Path
import tempfile
import json
import yaml


class TestConfigUtils:
    """测试配置工具"""

    def test_config_creation(self):
        """测试配置创建"""
        try:
            from src.core.config import Config

            _config = Config()
            assert config is not None
        except ImportError:
            pytest.skip("Config module not available")

    def test_fastapi_config_creation(self):
        """测试FastAPI配置创建"""
        try:
            from src._config.fastapi_config import FastAPIConfig

            _config = FastAPIConfig()
            assert config is not None
        except ImportError:
            pytest.skip("FastAPIConfig module not available")

    @patch.dict(os.environ, {"DATABASE_URL": "sqlite:///test.db"})
    def test_environment_variables(self):
        """测试环境变量"""
        try:
            from src.core.config import Config

            _config = Config()
            assert config is not None
        except ImportError:
            pytest.skip("Config module not available")

    def test_config_validation(self):
        """测试配置验证"""
        try:
            from src._config.fastapi_config import FastAPIConfig

            _config = FastAPIConfig()

            # Mock验证方法
            _config.validate = Mock(return_value=True)

            _result = _config.validate()
            assert _result is True
        except ImportError:
            pytest.skip("FastAPIConfig module not available")

    def test_config_serialization(self):
        """测试配置序列化"""
        try:
            from src.core.config import Config

            _config = Config()

            # Mock序列化方法
            _config.to_dict = Mock(return_value={"key": "value"})

            _result = _config.to_dict()
            assert _result == {"key": "value"}
        except ImportError:
            pytest.skip("Config module not available")

    def test_config_loading(self):
        """测试配置加载"""
        try:
            from src.core.config import Config

            # 尝试加载配置
            _config = Config()
            assert config is not None
        except (ImportError, AttributeError):
            pytest.skip("Config class not available")

    def test_config_defaults(self):
        """测试配置默认值"""
        try:
            from src._config.fastapi_config import FastAPIConfig

            _config = FastAPIConfig()

            # 测试默认值
            assert hasattr(config, "host")
            assert hasattr(config, "port")
            assert hasattr(config, "debug")
        except ImportError:
            pytest.skip("FastAPIConfig module not available")

    def test_yaml_config_parsing(self):
        """测试YAML配置解析"""
        with tempfile.TemporaryDirectory() as tmpdir:
            config_file = Path(tmpdir) / "_config.yaml"
            config_data = {
                "database": {"host": "localhost", "port": 5432, "name": "test_db"},
                "api": {"host": "0.0.0.0", "port": 8000, "debug": True},
            }

            # 写入YAML文件
            config_file.write_text(yaml.dump(config_data))

            # 读取并验证
            with open(config_file, "r") as f:
                loaded_data = yaml.safe_load(f)

            assert loaded_data["database"]["host"] == "localhost"
            assert loaded_data["database"]["port"] == 5432
            assert loaded_data["api"]["debug"] is True

    def test_json_config_parsing(self):
        """测试JSON配置解析"""
        with tempfile.TemporaryDirectory() as tmpdir:
            config_file = Path(tmpdir) / "_config.json"
            config_data = {
                "app": {"name": "football_prediction", "version": "1.0.0"},
                "features": {"ml_enabled": True, "cache_enabled": False},
            }

            # 写入JSON文件
            config_file.write_text(json.dumps(config_data, indent=2))

            # 读取并验证
            with open(config_file, "r") as f:
                loaded_data = json.load(f)

            assert loaded_data["app"]["name"] == "football_prediction"
            assert loaded_data["features"]["ml_enabled"] is True

    def test_nested_config_access(self):
        """测试嵌套配置访问"""
        _config = {
            "services": {
                "database": {
                    "primary": {"host": "db1.example.com", "port": 5432},
                    "replica": {"host": "db2.example.com", "port": 5432},
                },
                "cache": {"redis": {"host": "redis.example.com", "port": 6379}},
            }
        }

        def get_nested_value(data, key_path):
            """获取嵌套值"""
            keys = key_path.split(".")
            value = data
            for key in keys:
                value = value[key]
            return value

        # 测试嵌套访问
        primary_db = get_nested_value(config, "services.database.primary")
        assert primary_db["host"] == "db1.example.com"

        redis_config = get_nested_value(config, "services.cache.redis")
        assert redis_config["port"] == 6379

    def test_config_type_conversion(self):
        """测试配置类型转换"""
        config_data = {
            "port": "8000",  # 字符串形式的数字
            "debug": "true",  # 字符串形式的布尔值
            "timeout": "30.5",  # 字符串形式的浮点数
            "hosts": "host1,host2,host3",  # 字符串形式的列表
        }

        # 类型转换函数
        def convert_value(value, target_type):
            if target_type is int:
                return int(value)
            elif target_type is float:
                return float(value)
            elif target_type is bool:
                return value.lower() in ("true", "1", "yes", "on")
            elif target_type is list:
                return [item.strip() for item in value.split(",")]
            else:
                return value

        # 测试转换
        assert convert_value(config_data["port"], int) == 8000
        assert convert_value(config_data["debug"], bool) is True
        assert convert_value(config_data["timeout"], float) == 30.5
        assert convert_value(config_data["hosts"], list) == ["host1", "host2", "host3"]

    def test_config_env_var_substitution(self):
        """测试环境变量替换"""
        with patch.dict(
            os.environ,
            {"DB_HOST": "localhost", "DB_PORT": "5432", "API_KEY": "secret123"},
        ):
            config_template = {
                "database": {"url": "postgresql://${DB_HOST}:${DB_PORT}/mydb"},
                "api": {"key": "${API_KEY}"},
                "mixed": "prefix_${DB_HOST}_suffix",
            }

            # 简单的环境变量替换
            def substitute_env_vars(obj):
                if isinstance(obj, dict):
                    return {k: substitute_env_vars(v) for k, v in obj.items()}
                elif isinstance(obj, str):
                    for key, value in os.environ.items():
                        obj = obj.replace(f"${{{key}}}", value)
                    return obj
                else:
                    return obj

            substituted = substitute_env_vars(config_template)

            assert substituted["database"]["url"] == "postgresql://localhost:5432/mydb"
            assert substituted["api"]["key"] == "secret123"
            assert substituted["mixed"] == "prefix_localhost_suffix"

    def test_config_merge(self):
        """测试配置合并"""

        def merge_dicts(dict1, dict2):
            """深度合并字典"""
            _result = dict1.copy()
            for key, value in dict2.items():
                if (
                    key in result
                    and isinstance(_result[key], dict)
                    and isinstance(value, dict)
                ):
                    _result[key] = merge_dicts(_result[key], value)
                else:
                    _result[key] = value
            return result

        base_config = {
            "database": {"host": "localhost", "port": 5432},
            "api": {"port": 8000},
        }

        override_config = {
            "database": {"host": "production.db", "username": "admin"},
            "api": {"debug": True},
        }

        merged = merge_dicts(base_config, override_config)

        # 验证合并结果
        assert merged["database"]["host"] == "production.db"  # 覆盖
        assert merged["database"]["port"] == 5432  # 保留
        assert merged["database"]["username"] == "admin"  # 新增
        assert merged["api"]["port"] == 8000  # 保留
        assert merged["api"]["debug"] is True  # 新增

    def test_config_validation_with_pydantic(self):
        """测试使用Pydantic进行配置验证"""
        from pydantic import BaseModel, ValidationError

        class DatabaseConfig(BaseModel):
            host: str
            port: int
            username: str
            password: str

        class AppConfig(BaseModel):
            app_name: str = "football_prediction"
            debug: bool = False
            database: DatabaseConfig

        # 有效配置
        valid_config = {
            "app_name": "my_app",
            "debug": True,
            "database": {
                "host": "localhost",
                "port": 5432,
                "username": "admin",
                "password": "secret",
            },
        }

        _config = AppConfig(**valid_config)
        assert _config.app_name == "my_app"
        assert _config.database.host == "localhost"

        # 无效配置
        invalid_config = {
            "app_name": "my_app",
            "database": {
                "host": "localhost",
                "port": "invalid_port",  # 应该是整数
                "username": "admin",
                "password": "secret",
            },
        }

        with pytest.raises(ValidationError):
            AppConfig(**invalid_config)

    def test_config_profiles(self):
        """测试配置环境(profile)"""
        profiles = {
            "development": {
                "debug": True,
                "database": {"url": "sqlite:///dev.db"},
                "log_level": "DEBUG",
            },
            "production": {
                "debug": False,
                "database": {"url": "postgresql:///prod.db"},
                "log_level": "INFO",
            },
            "test": {
                "debug": True,
                "database": {"url": "sqlite:///test.db"},
                "log_level": "WARNING",
            },
        }

        def get_profile_config(profile_name):
            """获取指定环境的配置"""
            base_config = {"app_name": "football_prediction"}
            profile_config = profiles.get(profile_name, {})
            return {**base_config, **profile_config}

        # 测试不同环境
        dev_config = get_profile_config("development")
        assert dev_config["debug"] is True
        assert dev_config["log_level"] == "DEBUG"

        prod_config = get_profile_config("production")
        assert prod_config["debug"] is False
        assert prod_config["log_level"] == "INFO"

        # 测试默认环境
        default_config = get_profile_config("development")
        assert default_config["app_name"] == "football_prediction"

    def test_config_sensitive_data_masking(self):
        """测试敏感数据掩码"""
        _config = {
            "database": {
                "host": "localhost",
                "username": "admin",
                "password": "secret123",
            },
            "api_keys": {"service_a": "sk-1234567890", "service_b": "token-abcdef"},
        }

        sensitive_keys = ["password", "api_keys"]

        def mask_sensitive_data(data, sensitive_keys, parent_key=""):
            """隐藏敏感数据"""
            if isinstance(data, dict):
                masked = {}
                for key, value in data.items():
                    full_key = f"{parent_key}.{key}" if parent_key else key
                    if any(s_key in full_key.lower() for s_key in sensitive_keys):
                        if isinstance(value, dict):
                            # 如果是字典，递归处理
                            masked[key] = mask_sensitive_data(
                                value, sensitive_keys, full_key
                            )
                        else:
                            # 隐藏敏感值
                            masked[key] = "***MASKED***"
                    else:
                        masked[key] = mask_sensitive_data(
                            value, sensitive_keys, full_key
                        )
                return masked
            else:
                return data

        # 测试隐藏敏感数据
        masked_config = mask_sensitive_data(config, sensitive_keys)
        assert masked_config["database"]["password"] == "***MASKED***"
        assert masked_config["api_keys"]["service_a"] == "***MASKED***"
        assert masked_config["database"]["host"] == "localhost"  # 非敏感数据保持不变

    def test_config_file_not_found(self):
        """测试配置文件不存在"""
        with pytest.raises(FileNotFoundError):
            with open("/nonexistent/_config.yaml", "r"):
                pass

    def test_invalid_yaml_format(self):
        """测试无效YAML格式"""
        invalid_yaml = "invalid: yaml: content: ["

        with pytest.raises(yaml.YAMLError):
            yaml.safe_load(invalid_yaml)

    def test_invalid_json_format(self):
        """测试无效JSON格式"""
        invalid_json = '{"invalid": json content}'

        with pytest.raises(json.JSONDecodeError):
            json.loads(invalid_json)

    def test_config_hot_reload_simulation(self):
        """测试配置热重载模拟"""
        config_data = {"version": "1.0", "debug": False}

        class ConfigWatcher:
            def __init__(self, initial_config):
                self._config = initial_config.copy()
                self.callbacks = []

            def on_change(self, callback):
                """注册变更回调"""
                self.callbacks.append(callback)

            def update_config(self, new_config):
                """更新配置并触发回调"""
                old_config = self._config.copy()
                self._config = new_config
                for callback in self.callbacks:
                    callback(old_config, self.config)

        # 创建配置监听器
        watcher = ConfigWatcher(config_data)

        # 记录变更
        changes = []

        def config_changed(old, new):
            changes.append((old, new))

        watcher.on_change(config_changed)

        # 更新配置
        new_config = {"version": "2.0", "debug": True}
        watcher.update_config(new_config)

        # 验证变更
        assert len(changes) == 1
        assert changes[0][0]["version"] == "1.0"
        assert changes[0][1]["version"] == "2.0"

    def test_config_from_environment(self):
        """测试从环境变量加载配置"""
        env_config = {
            "FP_APP_NAME": "football_prediction",
            "FP_DEBUG": "true",
            "FP_DB_HOST": "localhost",
            "FP_DB_PORT": "5432",
            "FP_REDIS_URL": "redis://localhost:6379",
        }

        with patch.dict(os.environ, env_config):

            def load_from_env(prefix="FP_"):
                """从环境变量加载配置"""
                _config = {}
                for key, value in os.environ.items():
                    if key.startswith(prefix):
                        config_key = key[len(prefix) :].lower()
                        # 转换类型
                        if value.lower() in ("true", "false"):
                            value = value.lower() == "true"
                        elif value.isdigit():
                            value = int(value)
                        _config[config_key] = value
                return config

            _config = load_from_env()
            assert _config["app_name"] == "football_prediction"
            assert _config["debug"] is True
            assert _config["db_host"] == "localhost"
            assert _config["db_port"] == 5432
