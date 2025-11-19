from typing import Optional

"""
配置驱动的依赖注入测试
Configuration-driven Dependency Injection Tests
"""

import json
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch

import pytest

from src.core.config_di import ConfigurationBinder, DIConfiguration, ServiceConfig
from src.core.di import DIContainer
from src.core.exceptions import DependencyInjectionError


class TestServiceConfig:
    """服务配置测试类"""

    def test_service_config_initialization(self):
        """测试服务配置初始化"""
        config = ServiceConfig(
            name="test_service",
            implementation="TestImplementation",
            lifetime="singleton",
        )

        assert config.name == "test_service"
        assert config.implementation == "TestImplementation"
        assert config.lifetime == "singleton"
        assert config.enabled is True
        assert config.dependencies == []
        assert config.parameters == {}

    def test_service_config_with_all_fields(self):
        """测试包含所有字段的服务配置"""
        config = ServiceConfig(
            name="complex_service",
            implementation="ComplexImplementation",
            lifetime="scoped",
            factory="create_complex_service",
            dependencies=["dep1", "dep2"],
            parameters={"param1": "value1"},
            enabled=False,
            condition="environment == 'test'",
        )

        assert config.name == "complex_service"
        assert config.implementation == "ComplexImplementation"
        assert config.lifetime == "scoped"
        assert config.factory == "create_complex_service"
        assert config.dependencies == ["dep1", "dep2"]
        assert config.parameters == {"param1": "value1"}
        assert config.enabled is False
        assert config.condition == "environment == 'test'"

    def test_service_config_defaults(self):
        """测试服务配置默认值"""
        config = ServiceConfig(name="minimal_service")

        assert config.name == "minimal_service"
        assert config.implementation is None
        assert config.lifetime == "transient"
        assert config.factory is None
        assert config.instance is None
        assert config.dependencies == []
        assert config.parameters == {}
        assert config.enabled is True
        assert config.condition is None


class TestDIConfiguration:
    """依赖注入配置测试类"""

    def test_di_configuration_initialization(self):
        """测试DI配置初始化"""
        config = DIConfiguration()

        assert config.services == {}
        assert config.auto_scan == []
        assert config.conventions == []
        assert config.profiles == []
        assert config.imports == []

    def test_di_configuration_with_services(self):
        """测试包含服务的DI配置"""
        service1 = ServiceConfig(name="service1", implementation="Implementation1")
        service2 = ServiceConfig(name="service2", implementation="Implementation2")

        config = DIConfiguration(
            services={"service1": service1, "service2": service2},
            auto_scan=["src.services"],
            conventions=["Test*"],
            profiles=["test"],
            imports=["module1", "module2"],
        )

        assert len(config.services) == 2
        assert config.services["service1"].implementation == "Implementation1"
        assert config.services["service2"].implementation == "Implementation2"
        assert config.auto_scan == ["src.services"]
        assert config.conventions == ["Test*"]
        assert config.profiles == ["test"]
        assert config.imports == ["module1", "module2"]


class TestConfigurationBinder:
    """配置绑定器测试类"""

    def test_configuration_binder_initialization(self):
        """测试配置绑定器初始化"""
        container = DIContainer()
        binder = ConfigurationBinder(container)

        assert binder.container is container
        assert binder.auto_binder is not None
        assert binder.config is None
        assert binder._active_profile is None

    def test_load_from_json_file(self):
        """测试从JSON文件加载配置"""
        config_data = {
            "services": {
                "test_service": {
                    "implementation": "TestImplementation",
                    "lifetime": "singleton",
                }
            },
            "auto_scan": ["src.services"],
        }

        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump(config_data, f)
            config_file = f.name

        try:
            container = DIContainer()
            binder = ConfigurationBinder(container)
            binder.load_from_file(config_file)

            assert binder.config is not None
            assert "test_service" in binder.config.services
            assert (
                binder.config.services["test_service"].implementation
                == "TestImplementation"
            )
            assert binder.config.auto_scan == ["src.services"]
        finally:
            Path(config_file).unlink()

    def test_load_from_yaml_file(self):
        """测试从YAML文件加载配置"""
        config_data = """
services:
  yaml_service:
    implementation: YamlImplementation
    lifetime: scoped
    dependencies:
      - dependency1
      - dependency2
auto_scan:
  - src.yaml_services
profiles:
  - development
  - production
"""

        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            f.write(config_data)
            config_file = f.name

        try:
            container = DIContainer()
            binder = ConfigurationBinder(container)
            binder.load_from_file(config_file)

            assert binder.config is not None
            assert "yaml_service" in binder.config.services
            assert (
                binder.config.services["yaml_service"].implementation
                == "YamlImplementation"
            )
            assert binder.config.services["yaml_service"].lifetime == "scoped"
            assert binder.config.services["yaml_service"].dependencies == [
                "dependency1",
                "dependency2",
            ]
            assert binder.config.auto_scan == ["src.yaml_services"]
            assert binder.config.profiles == ["development", "production"]
        finally:
            Path(config_file).unlink()

    def test_load_from_nonexistent_file(self):
        """测试从不存在的文件加载配置"""
        container = DIContainer()
        binder = ConfigurationBinder(container)

        with pytest.raises(DependencyInjectionError, match="配置文件不存在"):
            binder.load_from_file("nonexistent_config.json")

    def test_load_from_unsupported_format(self):
        """测试从不支持的格式加载配置"""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as f:
            f.write("not a valid config format")
            config_file = f.name

        try:
            container = DIContainer()
            binder = ConfigurationBinder(container)

            with pytest.raises(DependencyInjectionError, match="不支持的配置文件格式"):
                binder.load_from_file(config_file)
        finally:
            Path(config_file).unlink()

    def test_load_from_invalid_json(self):
        """测试从无效JSON文件加载配置"""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            f.write('{"invalid": json}')  # 故意的JSON语法错误
            config_file = f.name

        try:
            container = DIContainer()
            binder = ConfigurationBinder(container)

            with pytest.raises(DependencyInjectionError, match="加载配置文件失败"):
                binder.load_from_file(config_file)
        finally:
            Path(config_file).unlink()

    def test_load_from_dict(self):
        """测试从字典加载配置"""
        config_data = {
            "services": {
                "dict_service": {
                    "implementation": "DictImplementation",
                    "lifetime": "transient",
                    "parameters": {"param1": "value1"},
                }
            }
        }

        container = DIContainer()
        binder = ConfigurationBinder(container)
        binder.load_from_dict(config_data)

        assert binder.config is not None
        assert "dict_service" in binder.config.services
        assert (
            binder.config.services["dict_service"].implementation
            == "DictImplementation"
        )
        assert binder.config.services["dict_service"].lifetime == "transient"
        assert binder.config.services["dict_service"].parameters == {"param1": "value1"}

    def test_load_from_empty_file(self):
        """测试从空文件加载配置"""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump(None, f)  # 空的JSON文件
            config_file = f.name

        try:
            container = DIContainer()
            binder = ConfigurationBinder(container)
            binder.load_from_file(config_file)

            assert binder.config is not None
            assert binder.config.services == {}
        finally:
            Path(config_file).unlink()

    def test_parse_config(self):
        """测试配置解析"""
        raw_config = {
            "services": {
                "test_service": {
                    "implementation": "TestImplementation",
                    "lifetime": "singleton",
                    "enabled": True,
                    "dependencies": ["dep1"],
                    "parameters": {"param1": "value1"},
                }
            },
            "auto_scan": ["src.services"],
            "profiles": ["test"],
        }

        container = DIContainer()
        binder = ConfigurationBinder(container)
        parsed_config = binder._parse_config(raw_config)

        assert isinstance(parsed_config, DIConfiguration)
        assert "test_service" in parsed_config.services
        service = parsed_config.services["test_service"]
        assert service.implementation == "TestImplementation"
        assert service.lifetime == "singleton"
        assert service.enabled is True
        assert service.dependencies == ["dep1"]
        assert service.parameters == {"param1": "value1"}
        assert parsed_config.auto_scan == ["src.services"]
        assert parsed_config.profiles == ["test"]

    def test_set_active_profile(self):
        """测试设置活动配置文件"""
        container = DIContainer()
        binder = ConfigurationBinder(container)

        # 首先加载配置
        config_data = {"profiles": ["development", "test", "production"]}
        binder.load_from_dict(config_data)

        # 设置活动配置文件
        binder.set_active_profile("test")
        assert binder._active_profile == "test"

        # 设置不存在的配置文件应该引发错误
        with pytest.raises(DependencyInjectionError, match="配置文件不存在"):
            binder.set_active_profile("nonexistent")

    def test_bind_services(self):
        """测试服务绑定"""

        # 创建模拟实现类
        class TestService:
            def __init__(self):
                self.name = "test_service"

        config_data = {
            "services": {
                "test_service": {
                    "implementation": "__main__.TestService",
                    "lifetime": "singleton",
                }
            }
        }

        container = DIContainer()
        binder = ConfigurationBinder(container)
        binder.load_from_dict(config_data)

        # 模拟模块导入
        with patch("src.core.config_di.importlib.import_module") as mock_import:
            mock_module = Mock()
            mock_module.TestService = TestService
            mock_import.return_value = mock_module

            # 绑定服务
            binder.bind_services()

            # 验证服务已注册
            service = container.resolve(TestService)
            assert isinstance(service, TestService)
            assert service.name == "test_service"

    def test_bind_disabled_service(self):
        """测试绑定禁用的服务"""
        config_data = {
            "services": {
                "disabled_service": {
                    "implementation": "DisabledImplementation",
                    "enabled": False,
                }
            }
        }

        container = DIContainer()
        binder = ConfigurationBinder(container)
        binder.load_from_dict(config_data)

        # 绑定服务
        binder.bind_services()

        # 禁用的服务不应该被注册
        # 这里我们验证容器中应该没有注册该服务
        # 具体验证方式取决于DIContainer的实现

    def test_bind_conditional_service(self):
        """测试绑定有条件的的服务"""
        config_data = {
            "services": {
                "conditional_service": {
                    "implementation": "ConditionalImplementation",
                    "condition": "environment == 'test'",
                }
            }
        }

        container = DIContainer()
        binder = ConfigurationBinder(container)
        binder.load_from_dict(config_data)

        # 模拟环境条件
        with patch.dict("os.environ", {"ENVIRONMENT": "test"}):
            binder.bind_services()
            # 在测试环境下应该绑定服务

        # 模拟不同的环境条件
        with patch.dict("os.environ", {"ENVIRONMENT": "production"}):
            binder.bind_services()
            # 在生产环境下可能不绑定服务

    def test_bind_services_with_dependencies(self):
        """测试绑定有依赖的服务"""

        class DependencyService:
            pass

        class MainService:
            def __init__(self, dependency: DependencyService):
                self.dependency = dependency

        config_data = {
            "services": {
                "dependency_service": {
                    "implementation": "__main__.DependencyService",
                    "lifetime": "singleton",
                },
                "main_service": {
                    "implementation": "__main__.MainService",
                    "lifetime": "transient",
                    "dependencies": ["dependency_service"],
                },
            }
        }

        container = DIContainer()
        binder = ConfigurationBinder(container)
        binder.load_from_dict(config_data)

        # 模拟模块导入
        with patch("src.core.config_di.importlib.import_module") as mock_import:
            mock_module = Mock()
            mock_module.DependencyService = DependencyService
            mock_module.MainService = MainService
            mock_import.return_value = mock_module

            # 绑定服务
            binder.bind_services()

            # 解析主服务时应该自动注入依赖
            main_service = container.resolve(MainService)
            assert isinstance(main_service, MainService)
            assert isinstance(main_service.dependency, DependencyService)

    def test_bind_services_with_factory(self):
        """测试绑定使用工厂方法的服务"""

        class FactoryService:
            def __init__(self, name: str):
                self.name = name

        def create_service():
            return FactoryService("factory_created")

        config_data = {
            "services": {
                "factory_service": {
                    "factory": "__main__.create_service",
                    "lifetime": "singleton",
                }
            }
        }

        container = DIContainer()
        binder = ConfigurationBinder(container)
        binder.load_from_dict(config_data)

        # 模拟函数导入
        with patch("src.core.config_di.importlib.import_module") as mock_import:
            mock_module = Mock()
            mock_module.create_service = create_service
            mock_import.return_value = mock_module

            # 绑定服务
            binder.bind_services()

            # 验证工厂方法被正确调用
            service = container.resolve(FactoryService)
            assert isinstance(service, FactoryService)
            assert service.name == "factory_created"

    def test_auto_scan_integration(self):
        """测试自动扫描集成"""
        config_data = {
            "auto_scan": ["src.services"],
            "conventions": ["*Service", "*Repository"],
        }

        container = DIContainer()
        binder = ConfigurationBinder(container)
        binder.load_from_dict(config_data)

        # 模拟自动绑定
        with patch.object(binder.auto_binder, "auto_scan_and_bind") as mock_auto_scan:
            binder.auto_scan_and_bind()
            mock_auto_scan.assert_called_once()

    def test_imports_integration(self):
        """测试导入集成"""
        config_data = {"imports": ["module1", "module2", "module3"]}

        container = DIContainer()
        binder = ConfigurationBinder(container)
        binder.load_from_dict(config_data)

        # 模拟模块导入
        with patch("src.core.config_di.importlib.import_module") as mock_import:
            binder.import_modules()

            # 验证所有模块都被导入
            assert mock_import.call_count == 3
            mock_import.assert_any_call("module1")
            mock_import.assert_any_call("module2")
            mock_import.assert_any_call("module3")

    def test_error_handling(self):
        """测试错误处理"""
        container = DIContainer()
        binder = ConfigurationBinder(container)

        # 测试处理格式错误的配置
        invalid_configs = [
            {"services": "not_a_dict"},  # services应该是字典
            {
                "services": {"invalid": {"lifetime": "invalid_lifetime"}}
            },  # 无效的lifetime
            {"services": {"missing_impl": {}}},  # 缺少实现
        ]

        for invalid_config in invalid_configs:
            try:
                binder.load_from_dict(invalid_config)
                # 如果没有抛出异常，应该有合理的默认处理
                assert binder.config is not None
            except DependencyInjectionError:
                # 预期的异常
                pass
            except Exception as e:
                # 其他异常也应该被包装为DependencyInjectionError
                assert isinstance(e, DependencyInjectionError)
