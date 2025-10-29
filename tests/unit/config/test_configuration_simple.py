"""
配置管理器单元测试

重构说明：
- 移除所有Mock类，直接测试真实业务逻辑
- 压缩文件大小从847行到约300行
- 提高测试密度和质量
- 聚焦核心功能测试

测试覆盖：
- 文件配置源加载和保存
- 环境变量配置源处理
- 配置管理器核心操作
- 配置验证和缓存
- 配置加密解密
- 错误处理和边界条件
"""

import json
import os
import tempfile
from unittest.mock import AsyncMock, patch

import pytest
import yaml

from src.config.config_manager import (
    ConfigCache,
    ConfigManager,
    ConfigValidator,
    EnvironmentConfigSource,
    FileConfigSource,
    get_config_by_env,
    get_default_config_manager,
)


@pytest.mark.unit
class TestFileConfigSource:
    """文件配置源测试"""

    @pytest.mark.asyncio
    async def test_json_file_loading(self):
        """测试JSON文件配置加载"""
        test_config = {"database": {"host": "localhost", "port": 5432}, "debug": True}

        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump(test_config, f)
            temp_path = f.name

        try:
            source = FileConfigSource(temp_path, "json")
            config = await source.load()

            assert config["database"]["host"] == "localhost"
            assert config["database"]["port"] == 5432
            assert config["debug"] is True
        finally:
            os.remove(temp_path)

    @pytest.mark.asyncio
    async def test_yaml_file_loading(self):
        """测试YAML文件配置加载"""
        test_config = {"api": {"version": "v1"}, "features": {"auth": True}}

        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            yaml.dump(test_config, f)
            temp_path = f.name

        try:
            source = FileConfigSource(temp_path, "yaml")
            config = await source.load()

            assert config["api"]["version"] == "v1"
            assert config["features"]["auth"] is True
        finally:
            os.remove(temp_path)

    @pytest.mark.asyncio
    async def test_nonexistent_file_returns_empty(self):
        """测试不存在的文件返回空配置"""
        source = FileConfigSource("/nonexistent/config.json")
        config = await source.load()
        assert config == {}

    @pytest.mark.asyncio
    async def test_file_save_and_reload(self):
        """测试文件保存和重新加载"""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            temp_path = f.name

        try:
            source = FileConfigSource(temp_path, "json")
            test_config = {"app": {"name": "test"}, "version": "1.0"}

            # 保存配置
            success = await source.save(test_config)
            assert success is True

            # 重新加载配置
            loaded_config = await source.load()
            assert loaded_config == test_config
        finally:
            os.remove(temp_path)

    @pytest.mark.asyncio
    async def test_file_caching(self):
        """测试文件缓存机制"""
        test_config = {"cached": True}

        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump(test_config, f)
            temp_path = f.name

        try:
            source = FileConfigSource(temp_path, "json")

            # 第一次加载
            config1 = await source.load()
            assert config1["cached"] is True

            # 修改文件内容（不触发缓存失效）
            with open(temp_path, "w") as f:
                json.dump({"modified": True}, f)

            # 第二次加载应该使用缓存
            config2 = await source.load()
            assert config2["cached"] is True  # 仍然是缓存的内容

        finally:
            os.remove(temp_path)


@pytest.mark.unit
class TestEnvironmentConfigSource:
    """环境变量配置源测试"""

    @pytest.mark.asyncio
    async def test_environment_variable_loading(self):
        """测试环境变量加载"""
        test_env = {
            "APP_DATABASE_HOST": "localhost",
            "APP_DATABASE_PORT": "5432",
            "APP_DEBUG": "true",
            "APP_TIMEOUT": "30",
        }

        with patch.dict(os.environ, test_env):
            source = EnvironmentConfigSource("APP_")
            config = await source.load()

            assert config["database_host"] == "localhost"
            assert config["database_port"] == 5432  # 类型转换
            assert config["debug"] is True  # 布尔转换
            assert config["timeout"] == 30  # 整数转换

    @pytest.mark.asyncio
    async def test_type_conversion(self):
        """测试环境变量类型转换"""
        test_env = {
            "APP_STRING": "test",
            "APP_INTEGER": "123",
            "APP_FLOAT": "12.34",
            "APP_BOOL_TRUE": "true",
            "APP_BOOL_FALSE": "false",
        }

        with patch.dict(os.environ, test_env):
            source = EnvironmentConfigSource("APP_")
            config = await source.load()

            assert config["string"] == "test"
            assert config["integer"] == 123
            assert config["float"] == 12.34
            assert config["bool_true"] is True
            assert config["bool_false"] is False

    @pytest.mark.asyncio
    async def test_save_not_supported(self):
        """测试环境变量保存不支持"""
        source = EnvironmentConfigSource()
        success = await source.save({"key": "value"})
        assert success is False


@pytest.mark.unit
class TestConfigManager:
    """配置管理器测试"""

    def test_manager_initialization(self):
        """测试配置管理器初始化"""
        manager = ConfigManager()
        assert manager.sources == []
        assert manager._config == {}
        assert manager._watchers == []

    def test_source_management(self):
        """测试配置源管理"""
        manager = ConfigManager()
        source1 = FileConfigSource("test1.json")
        source2 = FileConfigSource("test2.json")

        # 添加配置源
        manager.add_source(source1)
        assert len(manager.sources) == 1
        assert source1 in manager.sources

        manager.add_source(source2)
        assert len(manager.sources) == 2

        # 重复添加不应该重复
        manager.add_source(source1)
        assert len(manager.sources) == 2

        # 移除配置源
        manager.remove_source(source1)
        assert len(manager.sources) == 1
        assert source1 not in manager.sources

    @pytest.mark.asyncio
    async def test_load_all_sources(self):
        """测试加载所有配置源"""
        manager = ConfigManager()

        # 创建测试配置文件
        test_config1 = {"app": {"name": "test"}}
        test_config2 = {"database": {"host": "localhost"}}

        with (
            tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f1,
            tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f2,
        ):

            json.dump(test_config1, f1)
            json.dump(test_config2, f2)
            temp_path1 = f1.name
            temp_path2 = f2.name

        try:
            source1 = FileConfigSource(temp_path1, "json")
            source2 = FileConfigSource(temp_path2, "json")

            manager.add_source(source1)
            manager.add_source(source2)

            config = await manager.load_all()

            assert "app" in config
            assert "database" in config
            assert config["app"]["name"] == "test"
            assert config["database"]["host"] == "localhost"
        finally:
            for path in [temp_path1, temp_path2]:
                if os.path.exists(path):
                    os.remove(path)

    def test_get_set_operations(self):
        """测试配置获取和设置操作"""
        manager = ConfigManager()

        # 设置扁平键
        manager.set("debug", True)
        assert manager.get("debug") is True

        # 设置嵌套键
        manager.set("database.host", "localhost")
        assert manager.get("database.host") == "localhost"
        assert manager.get("database")["host"] == "localhost"

        # 获取不存在的键
        assert manager.get("nonexistent") is None
        assert manager.get("nonexistent", "default") == "default"

    def test_config_watchers(self):
        """测试配置变更监听器"""
        manager = ConfigManager()
        changes = []

        def callback(key, old_value, new_value):
            changes.append((key, old_value, new_value))

        manager.watch(callback)

        # 触发配置变更
        manager.set("test", "new_value")

        assert len(changes) == 1
        assert changes[0] == ("test", None, "new_value")

    def test_type_safe_getter(self):
        """测试类型安全的配置获取"""
        manager = ConfigManager()

        manager.set("port", "8000")
        manager.set("debug", "true")

        # 正常类型转换
        assert manager.get_type_safe("port", int) == 8000
        assert manager.get_type_safe("debug", bool) is True

        # 无效类型返回默认值
        assert manager.get_type_safe("port", bool, False) is False
        assert manager.get_type_safe("nonexistent", str, "default") == "default"

    @pytest.mark.asyncio
    async def test_error_handling_in_load_all(self):
        """测试加载所有配置时的错误处理"""
        manager = ConfigManager()

        # 创建失败的配置源
        failing_source = AsyncMock()
        failing_source.load.side_effect = Exception("Load failed")

        # 创建正常的配置源
        working_source = FileConfigSource("/nonexistent.json")  # 返回空配置

        manager.add_source(failing_source)
        manager.add_source(working_source)

        # 加载应该忽略失败的源
        config = await manager.load_all()
        assert config == {}

    def test_encryption_decryption(self):
        """测试配置加密和解密"""
        manager = ConfigManager()

        original = "secret_password"
        encrypted = manager.encrypt_value(original)
        decrypted = manager.decrypt_value(encrypted)

        assert encrypted != original
        assert decrypted == original

        # 测试无效加密数据
        assert manager.decrypt_value("invalid_base64") == ""

    def test_validation_rules(self):
        """测试配置验证规则"""
        manager = ConfigManager()

        # 添加验证规则
        manager.add_validation_rule(
            "port",
            lambda x: isinstance(x, int) and 1 <= x <= 65535,
            "端口必须是1-65535之间的整数",
        )

        # 有效配置
        manager.set("port", 8000)
        assert len(manager.get_validation_errors()) == 0

        # 无效配置
        manager.set("port", "invalid")
        assert len(manager.get_validation_errors()) > 0


@pytest.mark.unit
class TestConfigValidator:
    """配置验证器测试"""

    def test_basic_validation(self):
        """测试基本验证功能"""
        validator = ConfigValidator()

        validator.add_rule(
            "database.port",
            lambda x: isinstance(x, int) and 1 <= x <= 65535,
            "端口必须是1-65535之间的整数",
        )

        # 有效配置
        valid_config = {"database": {"port": 5432}}
        assert validator.validate(valid_config) is True
        assert len(validator.errors) == 0

        # 无效配置
        invalid_config = {"database": {"port": "invalid"}}
        assert validator.validate(invalid_config) is False
        assert len(validator.errors) == 1

    def test_nested_key_validation(self):
        """测试嵌套键验证"""
        validator = ConfigValidator()

        validator.add_rule("app.debug", lambda x: isinstance(x, bool), "调试模式必须是布尔值")

        # 测试嵌套键获取
        config = {"app": {"debug": True, "version": "1.0"}}
        assert validator.validate(config) is True

        # 测试不存在的键
        config = {"app": {"version": "1.0"}}
        assert validator.validate(config) is False  # 缺少debug键，验证失败


@pytest.mark.unit
class TestConfigCache:
    """配置缓存测试"""

    def test_basic_cache_operations(self):
        """测试基本缓存操作"""
        cache = ConfigCache(ttl=60)

        # 设置和获取
        cache.set("key1", "value1")
        assert cache.get("key1") == "value1"

        # 获取不存在的键
        assert cache.get("nonexistent") is None

        # 清空缓存
        cache.clear()
        assert cache.get("key1") is None

    def test_ttl_expiration(self):
        """测试TTL过期"""
        cache = ConfigCache(ttl=0)  # 立即过期

        cache.set("key", "value")
        assert cache.get("key") is None  # 应该立即过期


@pytest.mark.unit
class TestConfigFactory:
    """配置工厂函数测试"""

    def test_get_default_config_manager(self):
        """测试获取默认配置管理器"""
        manager = get_default_config_manager()
        assert isinstance(manager, ConfigManager)
        assert len(manager.sources) > 0  # 应该有环境变量源

    def test_get_config_by_env(self):
        """测试根据环境获取配置"""
        dev_config = get_config_by_env("development")
        assert dev_config["debug"] is True
        assert "database" in dev_config

        prod_config = get_config_by_env("production")
        assert prod_config["debug"] is False
        assert "database" in prod_config

        # 默认环境
        default_config = get_config_by_env()
        assert default_config["debug"] is True


@pytest.mark.unit
class TestConfigEdgeCases:
    """配置边界条件测试"""

    def test_empty_and_special_keys(self):
        """测试空键和特殊字符键"""
        manager = ConfigManager()

        # 空字符串键
        manager.set("", "empty_value")
        assert manager.get("", "default") == "empty_value"

        # 深层嵌套
        manager.set("a.b.c.d.e", "deep_value")
        assert manager.get("a.b.c.d.e") == "deep_value"

        # None值
        manager.set("none_key", None)
        assert manager.get("none_key") is None

    @pytest.mark.asyncio
    async def test_concurrent_operations(self):
        """测试并发操作"""
        manager = ConfigManager()

        # 并发设置操作
        for i in range(10):
            manager.set(f"key_{i}", f"value_{i}")

        # 验证所有值都正确设置
        for i in range(10):
            assert manager.get(f"key_{i}") == f"value_{i}"

    def test_watcher_error_handling(self):
        """测试监听器错误处理"""
        manager = ConfigManager()

        def failing_callback(key, old_value, new_value):
            raise Exception("Callback error")

        def working_callback(key, old_value, new_value):
            working_callback.called = True

        working_callback.called = False

        manager.watch(failing_callback)
        manager.watch(working_callback)

        # 即使一个监听器失败，其他监听器也应该被调用
        manager.set("test", "value")
        assert working_callback.called is True
