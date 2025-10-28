# TODO: Consider creating a fixture for 6 repeated Mock creations

# TODO: Consider creating a fixture for 6 repeated Mock creations

from unittest.mock import MagicMock, Mock, patch

"""
适配器工厂测试
Tests for Adapter Factory

测试src.adapters.factory模块的适配器工厂功能
"""

import json
import tempfile
from pathlib import Path

import pytest
import yaml

# 测试导入
try:
    from src.adapters.base import Adapter
    from src.adapters.factory import (
        AdapterConfig,
        AdapterFactory,
        AdapterGroupConfig,
        adapter_factory,
    )

    FACTORY_AVAILABLE = True
except ImportError as e:
    print(f"Import error: {e}")
    FACTORY_AVAILABLE = False
    AdapterFactory = None
    AdapterConfig = None
    AdapterGroupConfig = None
    adapter_factory = None


@pytest.mark.skipif(not FACTORY_AVAILABLE, reason="Factory module not available")
@pytest.mark.unit
class TestAdapterConfig:
    """适配器配置测试"""

    def test_adapter_config_creation(self):
        """测试：适配器配置创建"""
        _config = AdapterConfig(
            name="test_adapter",
            adapter_type="test",
            enabled=True,
            priority=100,
            parameters={"api_key": "test_key"},
            rate_limits={"requests_per_minute": 10},
            cache_config={"ttl": 300},
            retry_config={"max_retries": 3},
        )

        assert _config.name == "test_adapter"
        assert _config.adapter_type == "test"
        assert _config.enabled is True
        assert _config.priority == 100
        assert _config.parameters == {"api_key": "test_key"}
        assert _config.rate_limits == {"requests_per_minute": 10}
        assert _config.cache_config == {"ttl": 300}
        assert _config.retry_config == {"max_retries": 3}

    def test_adapter_config_defaults(self):
        """测试：适配器配置默认值"""
        _config = AdapterConfig(name="test", adapter_type="test")

        assert _config.enabled is True  # 默认启用
        assert _config.priority == 0  # 默认优先级
        assert _config.parameters == {}
        assert _config.rate_limits is None
        assert _config.cache_config is None
        assert _config.retry_config is None


@pytest.mark.skipif(not FACTORY_AVAILABLE, reason="Factory module not available")
class TestAdapterGroupConfig:
    """适配器组配置测试"""

    def test_adapter_group_config_creation(self):
        """测试：适配器组配置创建"""
        group = AdapterGroupConfig(
            name="test_group",
            adapters=["adapter1", "adapter2"],
            primary_adapter="adapter1",
            fallback_strategy="parallel",
        )

        assert group.name == "test_group"
        assert group.adapters == ["adapter1", "adapter2"]
        assert group.primary_adapter == "adapter1"
        assert group.fallback_strategy == "parallel"

    def test_adapter_group_config_defaults(self):
        """测试：适配器组配置默认值"""
        group = AdapterGroupConfig(name="test", adapters=["adapter1"])

        assert group.primary_adapter is None
        assert group.fallback_strategy == "sequential"


@pytest.mark.skipif(not FACTORY_AVAILABLE, reason="Factory module not available")
class TestAdapterFactory:
    """适配器工厂测试"""

    def test_factory_creation(self):
        """测试：工厂创建"""
        factory = AdapterFactory()
        assert factory is not None
        assert hasattr(factory, "_adapter_types")
        assert hasattr(factory, "_configs")
        assert hasattr(factory, "_group_configs")

    def test_register_adapter_type(self):
        """测试：注册适配器类型"""
        factory = AdapterFactory()

        # 创建模拟适配器类
        mock_adapter_class = Mock(spec=Adapter)

        # 注册适配器
        factory.register_adapter_type("test_adapter", mock_adapter_class)

        # 验证注册成功
        assert "test_adapter" in factory._adapter_types
        assert factory._adapter_types["test_adapter"] == mock_adapter_class

    def test_unregister_adapter_type(self):
        """测试：注销适配器类型"""
        factory = AdapterFactory()

        # 创建模拟适配器类
        mock_adapter_class = Mock(spec=Adapter)
        factory.register_adapter_type("test_adapter", mock_adapter_class)

        # 注销适配器
        factory.unregister_adapter_type("test_adapter")

        # 验证注销成功
        assert "test_adapter" not in factory._adapter_types

    def test_create_adapter_success(self):
        """测试：成功创建适配器"""
        factory = AdapterFactory()

        # 创建模拟适配器类
        mock_adapter_class = Mock()
        mock_adapter = Mock()
        mock_adapter_class.return_value = mock_adapter

        # 注册适配器类型
        factory.register_adapter_type("test_type", mock_adapter_class)

        # 创建配置
        _config = AdapterConfig(
            name="test",
            adapter_type="test_type",
            enabled=True,
            parameters={"param1": "value1"},
            priority=10,
        )

        # 创建适配器
        adapter = factory.create_adapter(_config)

        # 验证适配器被创建
        assert adapter is not None
        # 验证适配器类被调用
        assert mock_adapter_class.called

    def test_create_adapter_disabled(self):
        """测试：创建禁用的适配器"""
        factory = AdapterFactory()

        # 创建配置（禁用）
        _config = AdapterConfig(name="test", adapter_type="test_type", enabled=False)

        # 应该抛出异常
        with pytest.raises(ValueError, match="disabled"):
            factory.create_adapter(_config)

    def test_create_adapter_unknown_type(self):
        """测试：创建未知类型的适配器"""
        factory = AdapterFactory()

        # 创建配置（未知类型）
        _config = AdapterConfig(name="test", adapter_type="unknown_type", enabled=True)

        # 应该抛出异常
        with pytest.raises(ValueError, match="Unknown adapter type"):
            factory.create_adapter(_config)

    @patch.dict("os.environ", {"TEST_API_KEY": "secret_value"})
    def test_resolve_parameters_with_env_var(self):
        """测试：解析参数（包含环境变量）"""
        factory = AdapterFactory()

        parameters = {"api_key": "$TEST_API_KEY", "normal_param": "normal_value"}

        resolved = factory._resolve_parameters(parameters)

        assert resolved["api_key"] == "secret_value"
        assert resolved["normal_param"] == "normal_value"

    def test_resolve_parameters_missing_env_var(self):
        """测试：解析参数（缺少环境变量）"""
        factory = AdapterFactory()

        parameters = {"api_key": "$MISSING_VAR"}

        # 应该抛出异常
        with pytest.raises(
            ValueError, match="Environment variable MISSING_VAR not found"
        ):
            factory._resolve_parameters(parameters)

    def test_mask_sensitive_parameters(self):
        """测试：屏蔽敏感参数"""
        factory = AdapterFactory()

        parameters = {
            "api_key": "secret123",
            "password": "pass456",
            "normal_param": "normal_value",
            "token": "token789",
            "public_key": "public123",
        }

        masked = factory._mask_sensitive_parameters(parameters)

        assert masked["api_key"] == "***"
        assert masked["password"] == "***"
        assert masked["normal_param"] == "normal_value"
        assert masked["token"] == "***"
        # public_key包含"key"但可能不在敏感列表中，取决于实现
        # 实际实现只检查特定的敏感词

    def test_create_adapter_group(self):
        """测试：创建适配器组"""
        factory = AdapterFactory()

        # 创建子适配器配置
        child_config = AdapterConfig(
            name="child_adapter", adapter_type="test_type", enabled=True
        )
        factory._configs["child_adapter"] = child_config

        # 模拟create_adapter方法
        with patch.object(factory, "create_adapter") as mock_create:
            mock_composite = Mock()
            mock_composite.add_adapter = Mock()
            mock_create.return_value = mock_composite

            # 创建组配置
            group_config = AdapterGroupConfig(
                name="test_group",
                adapters=["child_adapter"],
                primary_adapter="child_adapter",
            )

            # 创建组
            group = factory.create_adapter_group(group_config)

            # 验证
            assert group is not None
            mock_create.assert_called()

    def test_load_config_from_json(self):
        """测试：从JSON文件加载配置"""
        factory = AdapterFactory()

        # 创建临时JSON文件
        config_data = {
            "adapters": [
                {
                    "name": "test_adapter",
                    "adapter_type": "test",
                    "enabled": True,
                    "priority": 100,
                    "parameters": {"api_key": "test"},
                }
            ],
            "adapter_groups": [
                {
                    "name": "test_group",
                    "adapters": ["test_adapter"],
                    "primary_adapter": "test_adapter",
                }
            ],
        }

        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump(config_data, f)
            temp_path = f.name

        try:
            # 加载配置
            factory.load_config_from_file(temp_path)

            # 验证配置加载
            assert "test_adapter" in factory._configs
            assert "test_group" in factory._group_configs

            _config = factory.get_config("test_adapter")
            assert _config.name == "test_adapter"
            assert _config.adapter_type == "test"

            group = factory.get_group_config("test_group")
            assert group.name == "test_group"
            assert group.adapters == ["test_adapter"]

        finally:
            Path(temp_path).unlink()

    def test_load_config_from_yaml(self):
        """测试：从YAML文件加载配置"""
        factory = AdapterFactory()

        # 创建临时YAML文件
        config_data = {
            "adapters": [
                {
                    "name": "yaml_adapter",
                    "adapter_type": "test",
                    "enabled": True,
                    "parameters": {"key": "value"},
                }
            ]
        }

        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            yaml.dump(config_data, f)
            temp_path = f.name

        try:
            # 加载配置
            factory.load_config_from_file(temp_path)

            # 验证配置加载
            assert "yaml_adapter" in factory._configs
            _config = factory.get_config("yaml_adapter")
            assert _config.name == "yaml_adapter"

        finally:
            Path(temp_path).unlink()

    def test_load_config_file_not_found(self):
        """测试：加载不存在的配置文件"""
        factory = AdapterFactory()

        # 应该抛出异常
        with pytest.raises(FileNotFoundError):
            factory.load_config_from_file("/nonexistent/path.json")

    def test_load_config_unsupported_format(self):
        """测试：加载不支持的配置文件格式"""
        factory = AdapterFactory()

        with tempfile.NamedTemporaryFile(suffix=".txt", delete=False) as f:
            f.write(b"test content")
            temp_path = f.name

        try:
            # 应该抛出异常
            with pytest.raises(ValueError, match="Unsupported config file format"):
                factory.load_config_from_file(temp_path)
        finally:
            Path(temp_path).unlink()

    def test_save_config_to_json(self):
        """测试：保存配置到JSON文件"""
        factory = AdapterFactory()

        # 添加配置
        _config = AdapterConfig(
            name="save_test",
            adapter_type="test",
            enabled=True,
            parameters={"api_key": "secret", "normal": "value"},
        )
        factory._configs["save_test"] = _config

        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            temp_path = f.name

        try:
            # 保存配置
            factory.save_config_to_file(temp_path)

            # 读取并验证
            with open(temp_path, "r") as f:
                saved_data = json.load(f)

            assert "adapters" in saved_data
            assert len(saved_data["adapters"]) == 1

            adapter_data = saved_data["adapters"][0]
            assert adapter_data["name"] == "save_test"
            assert adapter_data["parameters"]["api_key"] == "***"  # 应该被屏蔽
            assert adapter_data["parameters"]["normal"] == "value"

        finally:
            Path(temp_path).unlink()

    def test_get_config(self):
        """测试：获取配置"""
        factory = AdapterFactory()

        # 添加配置
        _config = AdapterConfig(name="test", adapter_type="test")
        factory._configs["test"] = _config

        # 获取配置
        retrieved = factory.get_config("test")
        assert retrieved is _config

        # 获取不存在的配置
        not_found = factory.get_config("nonexistent")
        assert not_found is None

    def test_get_group_config(self):
        """测试：获取组配置"""
        factory = AdapterFactory()

        # 添加组配置
        group = AdapterGroupConfig(name="test_group", adapters=["adapter1"])
        factory._group_configs["test_group"] = group

        # 获取配置
        retrieved = factory.get_group_config("test_group")
        assert retrieved is group

        # 获取不存在的配置
        not_found = factory.get_group_config("nonexistent")
        assert not_found is None

    def test_list_configs(self):
        """测试：列出所有配置"""
        factory = AdapterFactory()

        # 添加配置
        factory._configs["config1"] = AdapterConfig(name="c1", adapter_type="test")
        factory._configs["config2"] = AdapterConfig(name="c2", adapter_type="test")

        # 列出配置
        configs = factory.list_configs()
        assert set(configs) == {"config1", "config2"}

    def test_list_group_configs(self):
        """测试：列出所有组配置"""
        factory = AdapterFactory()

        # 添加组配置
        factory._group_configs["group1"] = AdapterGroupConfig(name="g1", adapters=[])
        factory._group_configs["group2"] = AdapterGroupConfig(name="g2", adapters=[])

        # 列出配置
        groups = factory.list_group_configs()
        assert set(groups) == {"group1", "group2"}

    def test_validate_config_unknown_type(self):
        """测试：验证配置（未知类型）"""
        factory = AdapterFactory()

        _config = AdapterConfig(name="test", adapter_type="unknown_type")
        errors = factory.validate_config(_config)

        assert len(errors) == 1
        assert "Unknown adapter type" in errors[0]

    def test_create_default_configs(self):
        """测试：创建默认配置"""
        factory = AdapterFactory()

        # 清空现有配置
        factory._configs.clear()
        factory._group_configs.clear()

        # 创建默认配置
        factory.create_default_configs()

        # 验证默认配置创建
        assert "api_football_main" in factory._configs
        assert "openweathermap_main" in factory._configs
        assert "football_sources" in factory._group_configs

        # 验证配置内容
        api_config = factory.get_config("api_football_main")
        assert api_config.adapter_type == "api-football"
        assert api_config.parameters["api_key"] == "$API_FOOTBALL_KEY"

        group_config = factory.get_group_config("football_sources")
        assert "api_football_main" in group_config.adapters


@pytest.mark.skipif(not FACTORY_AVAILABLE, reason="Factory module not available")
class TestGlobalAdapterFactory:
    """全局适配器工厂测试"""

    def test_global_factory_exists(self):
        """测试：全局工厂实例存在"""
        assert adapter_factory is not None
        assert isinstance(adapter_factory, AdapterFactory)

    def test_global_factory_has_configs(self):
        """测试：全局工厂有默认配置"""
        # 应该有默认配置
        configs = adapter_factory.list_configs()
        assert len(configs) > 0

        groups = adapter_factory.list_group_configs()
        assert len(groups) > 0


@pytest.mark.skipif(FACTORY_AVAILABLE, reason="Factory module should be available")
class TestModuleNotAvailable:
    """模块不可用时的测试"""

    def test_module_import_error(self):
        """测试：模块导入错误"""
        assert not FACTORY_AVAILABLE
        assert True  # Basic assertion - consider enhancing


# 测试模块级别的功能
def test_module_imports():
    """测试：模块导入"""
    if FACTORY_AVAILABLE:
        from src.adapters.factory import (
            AdapterConfig,
            AdapterFactory,
            AdapterGroupConfig,
        )

        assert AdapterFactory is not None
        assert AdapterConfig is not None
        assert AdapterGroupConfig is not None


def test_dataclass_fields():
    """测试：数据类字段"""
    if FACTORY_AVAILABLE:
        # 验证AdapterConfig字段
        fields = AdapterConfig.__dataclass_fields__
        expected_fields = [
            "name",
            "adapter_type",
            "enabled",
            "priority",
            "parameters",
            "rate_limits",
            "cache_config",
            "retry_config",
        ]

        for field in expected_fields:
            assert field in fields

        # 验证AdapterGroupConfig字段
        group_fields = AdapterGroupConfig.__dataclass_fields__
        expected_group_fields = [
            "name",
            "adapters",
            "primary_adapter",
            "fallback_strategy",
        ]

        for field in expected_group_fields:
            assert field in group_fields
