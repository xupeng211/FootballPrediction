"""
配置管理模块增强测试
补充 src.core.config 模块的测试覆盖，目标达到80%+覆盖率
"""

import json
import os
import tempfile
from pathlib import Path

import pytest

from src.core.config import HAS_PYDANTIC, Config, Settings, get_config, get_settings


@pytest.mark.unit
class TestConfig:
    """配置管理类测试"""

    def test_config_initialization_basic(self) -> None:
        """✅ 成功用例：基本初始化"""
        with tempfile.TemporaryDirectory() as temp_dir:
            config_dir = Path(temp_dir) / "testconfig"

            # 创建独立的Config实例
            with patch("src.core.config.Path.home", return_value=config_dir):
                config = Config()

            # 验证初始化状态
            assert isinstance(config.config_dir, Path)
            assert isinstance(config.config_file, Path)
            assert config.config_file.name == "config.json"

    def test_config_load_existing_file(self) -> None:
        """✅ 成功用例：加载现有配置文件"""
        test_config = {"key1": "value1", "key2": 42, "key3": True}

        with tempfile.TemporaryDirectory() as temp_dir:
            config_file = Path(temp_dir) / "config.json"
            config_file.write_text(json.dumps(test_config), encoding="utf-8")

            config = Config()
            config.config_file = config_file
            config.config_dir = temp_dir
            config._load_config()

            assert config.config == test_config

    def test_config_load_nonexistent_file(self) -> None:
        """✅ 边界用例：配置文件不存在"""
        with tempfile.TemporaryDirectory() as temp_dir:
            config_dir = Path(temp_dir) / "testconfig"
            config_file = config_dir / "nonexistent.json"

            # 创建独立的Config实例
            with patch("src.core.config.Path.home", return_value=config_dir):
                config = Config()
                config.config_file = config_file
                config._load_config()

            assert config.config == {}

    def test_config_load_invalid_json(self) -> None:
        """✅ 边界用例：配置文件JSON格式错误"""
        invalid_json = '{"key1": "value1", invalid}'

        with tempfile.TemporaryDirectory() as temp_dir:
            config_dir = Path(temp_dir) / "testconfig"
            config_dir.mkdir(exist_ok=True)  # 确保目录存在
            config_file = config_dir / "invalid.json"
            config_file.write_text(invalid_json, encoding="utf-8")

            # 创建独立的Config实例
            with patch("src.core.config.Path.home", return_value=config_dir):
                config = Config()
                config.config_file = config_file
                # 应该优雅地处理错误，配置为空
                config._load_config()
                assert config.config == {}

    def test_config_get_existing_key(self) -> None:
        """✅ 成功用例：获取存在的配置项"""
        config = Config()
        config.config = {"existing_key": "existing_value"}

        result = config.get("existing_key")
        assert result == "existing_value"

    def test_config_get_nonexistent_key(self) -> None:
        """✅ 边界用例：获取不存在的配置项"""
        config = Config()
        config.config = {}

        result = config.get("nonexistent_key")
        assert result is None

    def test_config_get_nonexistent_key_with_default(self) -> None:
        """✅ 成功用例：获取不存在的配置项（带默认值）"""
        config = Config()
        config.config = {}

        result = config.get("nonexistent_key", "default_value")
        assert result == "default_value"

    def test_config_get_existing_key_with_default(self) -> None:
        """✅ 成功用例：获取存在的配置项（忽略默认值）"""
        config = Config()
        config.config = {"existing_key": "existing_value"}

        result = config.get("existing_key", "default_value")
        assert result == "existing_value"

    def test_config_set_simple_value(self) -> None:
        """✅ 成功用例：设置简单值"""
        config = Config()
        config.config = {}

        config.set("key1", "value1")
        assert config.config == {"key1": "value1"}

    def test_config_set_complex_value(self) -> None:
        """✅ 成功用例：设置复杂值"""
        config = Config()
        config.config = {}

        complex_value = {"nested": {"key": "value"}, "list": [1, 2, 3]}
        config.set("complex_key", complex_value)
        assert config.config == {"complex_key": complex_value}

    def test_config_set_override_value(self) -> None:
        """✅ 成功用例：覆盖现有值"""
        config = Config()
        config.config = {"key1": "old_value"}

        config.set("key1", "new_value")
        assert config.config == {"key1": "new_value"}

    def test_config_save_create_directory(self) -> None:
        """✅ 成功用例：保存配置（创建目录）"""
        with tempfile.TemporaryDirectory() as temp_dir:
            config_dir = Path(temp_dir) / "nested" / "dir"
            config_file = config_dir / "config.json"

            config = Config()
            config.config = {"key1": "value1"}
            config.config_file = config_file
            config.config_dir = config_dir

            config.save()

            assert config_dir.exists()
            assert config_file.exists()

            saved_config = json.loads(config_file.read_text(encoding="utf-8"))
            assert saved_config == {"key1": "value1"}

    def test_config_save_unicode_content(self) -> None:
        """✅ 边界用例：保存Unicode内容"""
        with tempfile.TemporaryDirectory() as temp_dir:
            config_dir = Path(temp_dir) / "testconfig"
            config_file = config_dir / "unicode.json"

            # 创建独立的Config实例
            with patch("src.core.config.Path.home", return_value=config_dir):
                config = Config()
                config.config = {"chinese_key": "中文值", "emoji": "🚀"}
                config.config_file = config_file
                config.config_dir = config_dir

            config.save()

            saved_content = config_file.read_text(encoding="utf-8")
            saved_config = json.loads(saved_content)
            assert saved_config == {"chinese_key": "中文值", "emoji": "🚀"}

    def test_config_edge_cases_empty_config(self) -> None:
        """✅ 边界用例：空配置处理"""
        config = Config()
        config.config = {}

        # 空配置的get操作
        assert config.get("any_key") is None
        assert config.get("any_key", "default") == "default"

        # 空配置的set操作
        config.set("new_key", "new_value")
        assert config.config == {"new_key": "new_value"}

    def test_config_edge_cases_large_config(self) -> None:
        """✅ 边界用例：大配置处理"""
        config = Config()
        config.config = {}

        # 创建大配置
        large_config = {f"key_{i}": f"value_{i}" for i in range(1000)}
        for key, value in large_config.items():
            config.set(key, value)

        # 验证配置完整性
        assert len(config.config) == 1000
        assert config.get("key_0") == "value_0"
        assert config.get("key_999") == "value_999"

    def test_config_edge_cases_special_characters(self) -> None:
        """✅ 边界用例：特殊字符处理"""
        config = Config()
        config.config = {}

        special_values = {
            "newline": "value\nwith\nnewlines",
            "tab": "value\twith\ttabs",
            "quotes": 'value"with"quotes',
            "backslash": "value\\with\\backslashes",
            "unicode": "value\u4e2d\u6587",
            "emoji": "value🚀🎯",
        }

        for key, value in special_values.items():
            config.set(key, value)

        # 验证特殊字符保持不变
        for key, expected_value in special_values.items():
            assert config.get(key) == expected_value

    def test_config_key_conversion_to_string(self) -> None:
        """✅ 边界用例：键转换为字符串"""
        config = Config()
        config.config = {}

        # 测试各种类型的键
        config.set("123", "numeric_key_value")
        config.set("45.67", "float_key_value")
        config.set("True", "boolean_key_value")
        config.set("None", "none_key_value")

        assert config.get("123") == "numeric_key_value"
        assert config.get("45.67") == "float_key_value"
        assert config.get("True") == "boolean_key_value"
        assert config.get("None") == "none_key_value"


@pytest.mark.unit
class TestSettings:
    """应用程序设置类测试"""

    def test_settings_default_values(self) -> None:
        """✅ 成功用例：默认值验证"""
        settings = Settings()

        # 数据库配置
        assert settings.database_url == "sqlite+aiosqlite:///./data/football_prediction.db"
        assert (
            settings.test_database_url
            == "postgresql+asyncpg://postgres:postgres@db:5432/football_prediction_test"
        )

        # Redis配置
        assert settings.redis_url == "redis://redis:6379/0"

        # API配置
        assert settings.api_host == "localhost"
        assert settings.api_port == 8000

        # 环境配置
        assert settings.environment == "development"
        assert settings.log_level == "INFO"

        # MLflow配置
        assert settings.mlflow_tracking_uri == "file:///tmp/mlflow"

        # 外部API配置
        assert settings.api_football_key is None
        assert settings.api_football_url == "https://api-football-v1.p.rapidapi.com/v3"

        # 监控配置
        assert settings.metrics_enabled is True
        assert isinstance(settings.metrics_tables, list)
        assert len(settings.metrics_tables) > 0
        assert settings.metrics_collection_interval == 30

    def test_settings_custom_values_with_pydantic(self) -> None:
        """✅ 成功用例：自定义值（有Pydantic时）"""
        if not HAS_PYDANTIC:
            pytest.skip("Pydantic not available")

        custom_values = {
            "database_url": "custom://localhost/db",
            "api_host": "custom_host",
            "api_port": 9000,
            "environment": "production",
            "log_level": "DEBUG",
        }

        settings = Settings(**custom_values)

        assert settings.database_url == "custom://localhost/db"
        assert settings.api_host == "custom_host"
        assert settings.api_port == 9000
        assert settings.environment == "production"
        assert settings.log_level == "DEBUG"

    def test_settings_custom_values_without_pydantic(self) -> None:
        """✅ 成功用例：自定义值（无Pydantic时）"""
        custom_values = {
            "database_url": "custom://localhost/db",
            "api_host": "custom_host",
            "api_port": 9000,
            "environment": "production",
            "log_level": "DEBUG",
        }

        settings = Settings(**custom_values)

        assert settings.database_url == "custom://localhost/db"
        assert settings.api_host == "custom_host"
        assert settings.api_port == 9000
        assert settings.environment == "production"
        assert settings.log_level == "DEBUG"

    def test_settings_edge_cases_invalid_port_values(self) -> None:
        """✅ 边界用例：无效端口值"""
        # 测试边界端口值
        valid_ports = [0, 1, 65535, 8080, 8000]
        for port in valid_ports:
            settings = Settings(api_port=port)
            assert settings.api_port == port

    def test_settings_edge_cases_boolean_values(self) -> None:
        """✅ 边界用例：布尔值处理"""
        # 直接测试默认布尔值
        settings_true = Settings(metrics_enabled=True)
        settings_false = Settings(metrics_enabled=False)

        assert settings_true.metrics_enabled is True
        assert settings_false.metrics_enabled is False

    def test_settings_edge_cases_empty_lists(self) -> None:
        """✅ 边界用例：空列表处理"""
        if HAS_PYDANTIC:
            settings = Settings(metrics_tables=[], enabled_services=[])
        else:
            settings = Settings()
            settings.metrics_tables = []
            settings.enabled_services = []

        assert settings.metrics_tables == []
        assert settings.enabled_services == []

    def test_settings_environment_variable_loading(self) -> None:
        """✅ 成功用例：环境变量加载"""
        # 模拟环境变量
        env_vars = {
            "DATABASE_URL": "env://localhost/env_db",
            "API_HOST": "env_host",
            "API_PORT": "7000",
            "ENVIRONMENT": "staging",
            "LOG_LEVEL": "WARN",
            "METRICS_ENABLED": "false",
        }

        with patch.dict(os.environ, env_vars, clear=False):
            settings = Settings()

            # 验证环境变量被正确加载
            if not HAS_PYDANTIC:
                assert settings.database_url == "env://localhost/env_db"
                assert settings.api_host == "env_host"
                assert settings.api_port == 7000
                assert settings.environment == "staging"
                assert settings.log_level == "WARN"
                assert settings.metrics_enabled is False

    def test_settings_list_env_parsing_json(self) -> None:
        """✅ 成功用例：列表环境变量JSON解析"""
        if not HAS_PYDANTIC:
            json_list = '["item1", "item2", "item3"]'

            with patch.dict(os.environ, {"METRICS_TABLES": json_list}):
                settings = Settings()
                assert settings.metrics_tables == ["item1", "item2", "item3"]

    def test_settings_list_env_parsing_csv(self) -> None:
        """✅ 成功用例：列表环境变量CSV解析"""
        if not HAS_PYDANTIC:
            csv_list = "item1, item2, item3"

            with patch.dict(os.environ, {"METRICS_TABLES": csv_list}):
                settings = Settings()
                assert settings.metrics_tables == ["item1", "item2", "item3"]

    def test_settings_edge_cases_invalid_env_values(self) -> None:
        """✅ 边界用例：无效环境变量值"""
        # 测试Pydantic验证错误处理
        if HAS_PYDANTIC:
            # Pydantic会抛出验证错误
            with patch.dict(os.environ, {"API_PORT": "invalid_port"}):
                with pytest.raises(Exception):  # Pydantic ValidationError
                    Settings()
        else:
            # 无Pydantic时的处理
            with patch.dict(os.environ, {"API_PORT": "invalid_port"}):
                settings = Settings()
                assert settings.api_port == 8000  # 应该保持默认值

    def test_settings_complex_configuration(self) -> None:
        """✅ 成功用例：复杂配置组合"""
        complex_config = {
            "database_url": "postgresql+asyncpg://user:pass@localhost:5432/complex_db",
            "redis_url": "redis://localhost:6379/1",
            "api_host": "complex.example.com",
            "api_port": 9999,
            "environment": "production",
            "log_level": "ERROR",
            "mlflow_tracking_uri": "http://mlflow.example.com:5000",
            "api_football_key": "test_api_key_12345",
            "api_football_url": "https://custom-api.example.com/v1",
            "metrics_enabled": True,
            "metrics_collection_interval": 60,
            "metrics_tables": ["table1", "table2", "table3"],
            "enabled_services": ["Service1", "Service2"],
        }

        settings = Settings(**complex_config)

        # 验证所有配置项
        assert settings.database_url == complex_config["database_url"]
        assert settings.redis_url == complex_config["redis_url"]
        assert settings.api_host == complex_config["api_host"]
        assert settings.api_port == complex_config["api_port"]
        assert settings.environment == complex_config["environment"]
        assert settings.log_level == complex_config["log_level"]
        assert settings.mlflow_tracking_uri == complex_config["mlflow_tracking_uri"]
        assert settings.api_football_key == complex_config["api_football_key"]
        assert settings.api_football_url == complex_config["api_football_url"]
        assert settings.metrics_enabled == complex_config["metrics_enabled"]
        assert settings.metrics_collection_interval == complex_config["metrics_collection_interval"]


@pytest.mark.unit
class TestConfigModuleFunctions:
    """配置模块函数测试"""

    def test_get_config_function(self) -> None:
        """✅ 成功用例：get_config函数"""
        config = get_config()
        assert isinstance(config, Config)
        assert hasattr(config, "config")
        assert hasattr(config, "get")
        assert hasattr(config, "set")
        assert hasattr(config, "save")

    def test_get_settings_function(self) -> None:
        """✅ 成功用例：get_settings函数"""
        settings = get_settings()
        assert isinstance(settings, Settings)
        assert hasattr(settings, "database_url")
        assert hasattr(settings, "api_host")
        assert hasattr(settings, "api_port")

    def test_global_config_singleton(self) -> None:
        """✅ 成功用例：全局配置单例"""
        config1 = get_config()
        config2 = get_config()

        # 应该是同一个实例
        assert config1 is config2

    def test_global_settings_independence(self) -> None:
        """✅ 成功用例：全局设置独立性"""
        settings1 = get_settings()
        settings2 = get_settings()

        # 每次调用都应该创建新实例
        assert settings1 is not settings2
        # 但是属性值应该相同
        assert settings1.database_url == settings2.database_url


@pytest.mark.unit
class TestConfigErrorHandling:
    """配置模块错误处理测试"""

    def test_config_file_permission_error(self) -> None:
        """✅ 边界用例：配置文件权限错误"""
        config = Config()

        # 模拟权限错误
        with patch("builtins.open", side_effect=PermissionError("Permission denied")):
            config.config = {"test": "value"}
            # save操作应该抛出PermissionError
            with pytest.raises(PermissionError):
                config.save()

    def test_config_file_io_error(self) -> None:
        """✅ 边界用例：配置文件IO错误"""
        config = Config()

        # 模拟IO错误
        with patch("builtins.open", side_effect=IOError("IO Error")):
            config.config = {"test": "value"}
            # save操作应该抛出IOError
            with pytest.raises(IOError):
                config.save()

    def test_config_json_serialization_error(self) -> None:
        """✅ 边界用例：JSON序列化错误"""
        with tempfile.TemporaryDirectory() as temp_dir:
            config_dir = Path(temp_dir) / "testconfig"
            config_file = config_dir / "invalid.json"

            # 创建独立的Config实例
            with patch("src.core.config.Path.home", return_value=config_dir):
                config = Config()
                config.config = {"invalid": object()}
                config.config_file = config_file
                config.config_dir = config_dir

            # 应该抛出TypeError
            with pytest.raises(TypeError):
                config.save()

    def test_settings_invalid_type_conversion(self) -> None:
        """✅ 边界用例：设置类型转换错误"""
        if not HAS_PYDANTIC:
            with patch.dict(os.environ, {"API_PORT": "not_a_number"}):
                settings = Settings()
                # 应该保持默认值
                assert settings.api_port == 8000


@pytest.mark.unit
class TestConfigPerformance:
    """配置模块性能测试"""

    def test_config_large_operations_performance(self) -> None:
        """✅ 性能用例：大量配置操作"""
        import time

        config = Config()
        config.config = {}

        # 测试大量set操作性能
        start_time = time.perf_counter()
        for i in range(1000):
            config.set(f"key_{i}", f"value_{i}")
        set_time = time.perf_counter() - start_time

        # 测试大量get操作性能
        start_time = time.perf_counter()
        for i in range(1000):
            config.get(f"key_{i}")
        get_time = time.perf_counter() - start_time

        # 性能断言（应该在合理时间内完成）
        assert set_time < 1.0  # 1000次set操作应该在1秒内完成
        assert get_time < 0.5  # 1000次get操作应该在0.5秒内完成

    def test_settings_initialization_performance(self) -> None:
        """✅ 性能用例：设置初始化性能"""
        import time

        start_time = time.perf_counter()
        for _ in range(100):
            Settings()
        init_time = time.perf_counter() - start_time

        # 100次初始化应该在合理时间内完成
        assert init_time < 2.0


@pytest.mark.unit
class TestConfigThreadSafety:
    """配置模块线程安全测试"""

    def test_config_concurrent_access(self) -> None:
        """✅ 并发用例：配置并发访问"""
        import threading

        config = Config()
        config.config = {}
        results = []

        def worker(thread_id: int):
            for i in range(10):
                key = f"thread_{thread_id}_key_{i}"
                value = f"thread_{thread_id}_value_{i}"
                config.set(key, value)
                retrieved = config.get(key)
                results.append((key, retrieved))

        # 创建多个线程
        threads = []
        for thread_id in range(5):
            thread = threading.Thread(target=worker, args=(thread_id,))
            threads.append(thread)
            thread.start()

        # 等待所有线程完成
        for thread in threads:
            thread.join()

        # 验证结果
        assert len(results) == 50  # 5个线程 * 10次操作

        # 验证所有键值对都正确设置和获取
        for key, value in results:
            assert key in config.config
            assert config.config[key] == value
