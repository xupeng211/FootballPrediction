# TODO: Consider creating a fixture for 46 repeated Mock creations

# TODO: Consider creating a fixture for 46 repeated Mock creations




import os
import sys
import tempfile
from pathlib import Path

import pytest

# 添加项目路径

from src.core.di import ServiceLifetime
from src.core.di_setup import (






        # 清理

    # ========================================
    # 基础创建和初始化测试
    # ========================================





    # ========================================
    # 初始化功能测试
    # ========================================











        # 创建空文件












    # ========================================
    # 服务注册功能测试
    # ========================================




            # 验证服务注册方法被调用




            # 验证导入错误被优雅处理 - MatchRepository实际不存在
                    # 如果没有抛出异常，测试通过

                # 验证警告日志被记录




            # 模拟导入错误 - 应该被日志记录而不是抛出异常


    # ========================================
    # 服务生命周期测试
    # ========================================






        # 应该不会抛出异常






        # 应该不会抛出异常




    # ========================================
    # 全局实例和便捷函数测试
    # ========================================







    # ========================================
    # 装饰器测试
    # ========================================





















            # 由于容器为None，应该不会调用注册方法
            # 测试通过表示没有抛出异常

    # ========================================
    # 配置文件创建测试
    # ========================================








    # ========================================
    # 边界条件和错误处理测试
    # ========================================






            # 测试None模块

            # 测试空模块
















            # 验证装饰器属性

            # 验证容器调用






            # 验证所有服务都被注册
"""""""
DI设置功能测试
Tests for DI setup functional module
专注于测试DI设置的实际功能。
"""""""
sys.path.insert(0, str(Path(__file__).parent.parent.parent))
sys.path.insert(0, "src")
    DISetup,
    configure_di,
    create_di_config,
    get_di_setup,
    register_service,
)
@pytest.mark.unit
class TestDISetupFunctional:
    """DI设置功能测试"""
    @pytest.fixture
    def setup_instance(self):
        """创建DISetup实例"""
        return DISetup(profile="test")
    @pytest.fixture
    def temp_config_file(self):
        """创建临时配置文件"""
        config_content = """""""
profiles:
  test:
    database:
      host: localhost
      port: 5432
    redis:
      host: localhost
      port: 6379
"""""""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            f.write(config_content)
            temp_file = f.name
        yield temp_file
        os.unlink(temp_file)
    def test_di_setup_creation_default_profile(self):
        """测试默认配置文件创建"""
        setup = DISetup()
        assert setup.profile == "development"
        assert setup.container is None
        assert setup.lifecycle_manager is None
    def test_di_setup_creation_custom_profile(self):
        """测试自定义配置文件创建"""
        setup = DISetup(profile="production")
        assert setup.profile == "production"
    def test_di_setup_creation_environment_variable(self):
        """测试环境变量设置配置文件"""
        with patch.dict(os.environ, {"APP_PROFILE": "staging"}):
            pass
        with patch.dict(os.environ, {"APP_PROFILE": "staging"}):
            pass
        with patch.dict(os.environ, {"APP_PROFILE": "staging"}):
            pass
        with patch.dict(os.environ, {"APP_PROFILE": "staging"}):
            pass
        with patch.dict(os.environ, {"APP_PROFILE": "staging"}):
            setup = DISetup(profile=None)
            assert setup.profile == "staging"
    def test_di_setup_attributes(self):
        """测试DI设置属性"""
        setup = DISetup(profile="test")
        assert hasattr(setup, "profile")
        assert hasattr(setup, "container")
        assert hasattr(setup, "lifecycle_manager")
        assert isinstance(setup.profile, str)
    def test_initialize_basic_functionality(self):
        """测试基础初始化功能"""
        setup = DISetup(profile="test")
        with (
            patch("src.core.di_setup.ServiceCollection") as mock_collection,
            patch("src.core.di_setup.get_lifecycle_manager") as mock_lifecycle,
        ):
            mock_container = Mock()
            mock_collection.return_value.build_container.return_value = mock_container
            mock_lifecycle.return_value = Mock()
            container = setup.initialize()
            assert container is mock_container
            assert setup.container is mock_container
            assert setup.lifecycle_manager is not None
            mock_collection.assert_called_once()
            mock_lifecycle.assert_called_once()
    def test_initialize_with_nonexistent_config(self):
        """测试不存在配置文件的初始化"""
        setup = DISetup()
        with (
            patch("src.core.di_setup.ServiceCollection") as mock_collection,
            patch("src.core.di_setup.get_lifecycle_manager") as mock_lifecycle,
        ):
            mock_container = Mock()
            mock_collection.return_value.build_container.return_value = mock_container
            mock_lifecycle.return_value = Mock()
            container = setup.initialize(config_file="/nonexistent/file.yaml")
            assert container is mock_container
    def test_initialize_with_empty_config(self, temp_config_file):
        """测试空配置文件初始化"""
        setup = DISetup()
        with open(temp_config_file, "w") as f:
            f.write("")
        with (
            patch("src.core.di_setup.ConfigurationBinder") as mock_binder_class,
            patch("src.core.di_setup.get_lifecycle_manager") as mock_lifecycle,
        ):
            mock_container = Mock()
            mock_binder = Mock()
            mock_binder.container = mock_container
            mock_binder_class.return_value = mock_binder
            mock_lifecycle.return_value = Mock()
            container = setup.initialize(config_file=temp_config_file)
            assert container is mock_container
    def test_initialize_with_auto_scan(self):
        """测试自动扫描模块初始化"""
        setup = DISetup()
        modules = ["test.module1", "test.module2"]
        with (
            patch("src.core.di_setup.ServiceCollection") as mock_collection,
            patch("src.core.di_setup.AutoBinder") as mock_auto_binder_class,
            patch("src.core.di_setup.get_lifecycle_manager") as mock_lifecycle,
        ):
            mock_container = Mock()
            mock_collection.return_value.build_container.return_value = mock_container
            mock_auto_binder = Mock()
            mock_auto_binder_class.return_value = mock_auto_binder
            mock_lifecycle.return_value = Mock()
            setup.initialize(auto_scan_modules=modules)
            mock_auto_binder_class.assert_called_once_with(mock_container)
            assert mock_auto_binder.bind_from_assembly.call_count == 2
    def test_initialize_with_valid_config(self, temp_config_file):
        """测试有效配置文件初始化"""
        setup = DISetup()
        with (
            patch("src.core.di_setup.ConfigurationBinder") as mock_binder_class,
            patch("src.core.di_setup.get_lifecycle_manager") as mock_lifecycle,
        ):
            mock_container = Mock()
            mock_binder = Mock()
            mock_binder.container = mock_container
            mock_binder_class.return_value = mock_binder
            mock_lifecycle.return_value = Mock()
            setup.initialize(config_file=temp_config_file)
            mock_binder_class.assert_called_once()
            mock_binder.load_from_file.assert_called_once_with(temp_config_file)
            mock_binder.set_active_profile.assert_called_once_with("development")
            mock_binder.apply_configuration.assert_called_once()
    def test_register_core_services(self):
        """测试核心服务注册"""
        setup = DISetup()
        with (
            patch("src.core.di_setup.ServiceCollection") as mock_collection,
            patch("src.core.di_setup.get_lifecycle_manager") as mock_lifecycle,
        ):
            mock_container = Mock()
            mock_collection.return_value.build_container.return_value = mock_container
            mock_lifecycle_instance = Mock()
            mock_lifecycle.return_value = mock_lifecycle_instance
            setup.initialize()
            assert mock_container.register_singleton.called
    def test_auto_register_repositories_import_error_handling(self):
        """测试仓储注册导入错误处理"""
        setup = DISetup()
        with patch("src.core.di_setup.ServiceCollection") as mock_collection:
            mock_container = Mock()
            mock_collection.return_value.build_container.return_value = mock_container
            setup.initialize()
            with patch("src.core.di_setup.logger") as mock_logger:
                try:
                    pass
                except Exception:
                    pass
                    setup._auto_register_repositories()
                except ImportError:
                    pytest.fail("ImportError should be handled gracefully")
                mock_logger.warning.assert_called()
                warning_message = mock_logger.warning.call_args[0][0]
                assert "无法导入仓储类" in warning_message
    def test_auto_register_services_import_error_handling(self):
        """测试服务注册导入错误处理"""
        setup = DISetup()
        with patch("src.core.di_setup.ServiceCollection") as mock_collection:
            mock_container = Mock()
            mock_collection.return_value.build_container.return_value = mock_container
            setup.initialize()
            with patch(
                "src.core.di_setup.DISetup._auto_register_services"
            ) as mock_register:
                mock_register.side_effect = ImportError(
                    "No module named 'missing.service'"
                )
                with patch("src.core.di_setup.logger"):
                    try:
                        pass
                    except Exception:
                        pass
                        setup._auto_register_services()
                    except ImportError:
                        pytest.fail("ImportError should be handled gracefully")
    @pytest.mark.asyncio
    async def test_start_services_with_manager(self):
        """测试有生命周期管理器时启动服务"""
        setup = DISetup()
        mock_lifecycle_manager = AsyncMock()
        setup.lifecycle_manager = mock_lifecycle_manager
        await setup.start_services()
        mock_lifecycle_manager.start_all_services.assert_called_once()
        mock_lifecycle_manager.start_monitoring.assert_called_once_with(interval=30.0)
    @pytest.mark.asyncio
    async def test_start_services_without_manager(self):
        """测试无生命周期管理器时启动服务"""
        setup = DISetup()
        setup.lifecycle_manager = None
        await setup.start_services()
    @pytest.mark.asyncio
    async def test_stop_services_with_manager(self):
        """测试有生命周期管理器时停止服务"""
        setup = DISetup()
        mock_lifecycle_manager = AsyncMock()
        setup.lifecycle_manager = mock_lifecycle_manager
        await setup.stop_services()
        mock_lifecycle_manager.shutdown.assert_called_once()
    @pytest.mark.asyncio
    async def test_stop_services_without_manager(self):
        """测试无生命周期管理器时停止服务"""
        setup = DISetup()
        setup.lifecycle_manager = None
        await setup.stop_services()
    @pytest.mark.asyncio
    async def test_lifecycle_manager_error_propagation(self):
        """测试生命周期管理器错误传播"""
        setup = DISetup()
        mock_lifecycle_manager = AsyncMock()
        mock_lifecycle_manager.start_all_services.side_effect = Exception(
            "Start failed"
        )
        setup.lifecycle_manager = mock_lifecycle_manager
        with pytest.raises(Exception, match="Start failed"):
            await setup.start_services()
    def test_get_di_setup_singleton(self):
        """测试全局DI设置单例"""
        setup1 = get_di_setup()
        setup2 = get_di_setup()
        assert setup1 is setup2
        assert isinstance(setup1, DISetup)
    def test_get_di_setup_default_initialization(self):
        """测试全局DI设置默认初始化"""
        setup = get_di_setup()
        assert setup.profile == "development"
        assert hasattr(setup, "container")
        assert hasattr(setup, "lifecycle_manager")
    def test_configure_di_function(self):
        """测试配置DI便捷函数"""
        with patch("src.core.di_setup.DISetup") as mock_di_setup_class:
            mock_setup = Mock(spec=DISetup)
            mock_container = Mock()
            mock_setup.initialize.return_value = mock_container
            mock_di_setup_class.return_value = mock_setup
            container = configure_di(
                config_file="test.yaml",
                profile="production",
                auto_scan_modules=["test.module"],
            )
            assert container is mock_container
            mock_di_setup_class.assert_called_once_with("production")
            mock_setup.initialize.assert_called_once_with("test.yaml", ["test.module"])
    def test_register_service_decorator_singleton(self):
        """测试单例服务注册装饰器"""
        mock_container = Mock()
        mock_setup = Mock()
        mock_setup.container = mock_container
        with patch("src.core.di_setup.get_di_setup", return_value=mock_setup):
            pass
            @register_service(ServiceLifetime.SINGLETON)
            class TestService:
                pass
            mock_container.register_singleton.assert_called_once_with(TestService)
            assert hasattr(TestService, "__di_lifetime__")
            assert TestService.__di_lifetime__ == ServiceLifetime.SINGLETON
    def test_register_service_decorator_scoped(self):
        """测试作用域服务注册装饰器"""
        mock_container = Mock()
        mock_setup = Mock()
        mock_setup.container = mock_container
        with patch("src.core.di_setup.get_di_setup", return_value=mock_setup):
            pass
            @register_service(ServiceLifetime.SCOPED)
            class TestService:
                pass
            mock_container.register_scoped.assert_called_once_with(TestService)
    def test_register_service_decorator_with_interface(self):
        """测试带接口的服务注册装饰器"""
        mock_container = Mock()
        mock_setup = Mock()
        mock_setup.container = mock_container
        with patch("src.core.di_setup.get_di_setup", return_value=mock_setup):
            pass
            class ITestService:
                pass
            @register_service(ServiceLifetime.TRANSIENT, interface=ITestService)
            class TestService:
                pass
            mock_container.register_transient.assert_called_once_with(
                ITestService, TestService
            )
    def test_register_service_decorator_with_name(self):
        """测试带名称的服务注册装饰器"""
        mock_container = Mock()
        mock_setup = Mock()
        mock_setup.container = mock_container
        with patch("src.core.di_setup.get_di_setup", return_value=mock_setup):
            pass
            @register_service(ServiceLifetime.SINGLETON, name="custom_service")
            class TestService:
                pass
            mock_container.register_singleton.assert_called_once_with(TestService)
            assert TestService.__di_name__ == "custom_service"
    def test_register_service_decorator_no_container(self):
        """测试无容器时的服务注册装饰器"""
        mock_setup = Mock()
        mock_setup.container = None
        with patch("src.core.di_setup.get_di_setup", return_value=mock_setup):
            pass
            @register_service(ServiceLifetime.SINGLETON)
            class TestService:
                pass
    def test_create_di_config_basic(self):
        """测试基础DI配置文件创建"""
        mock_config_content = "sample config content"
        temp_path = tempfile.mktemp(suffix=".yaml")
        try:
            pass
        except Exception:
            pass
            with patch(
                "src.core.config_di.generate_sample_config",
                return_value=mock_config_content,
            ):
                create_di_config(temp_path, "yaml")
            with open(temp_path, "r") as f:
                content = f.read()
                assert content == mock_config_content
        finally:
            if os.path.exists(temp_path):
                os.unlink(temp_path)
    def test_create_di_config_default_params(self):
        """测试DI配置文件创建默认参数"""
        with (
            patch("src.core.config_di.generate_sample_config") as mock_generate,
            patch("src.core.di_setup.Path") as mock_path,
            patch("builtins.open", create=True) as mock_open,
        ):
            mock_path_instance = Mock()
            mock_path.return_value = mock_path_instance
            mock_path_instance.parent.mkdir = Mock()
            mock_file_handle = Mock()
            mock_open.return_value.__enter__.return_value = mock_file_handle
            create_di_config()
            mock_generate.assert_called_once_with("yaml")
            mock_path.assert_called_once_with("configs/di-config.yaml")
            mock_file_handle.write.assert_called_once()
    def test_config_file_permission_error(self):
        """测试配置文件权限错误"""
        setup = DISetup()
        with (
            patch("src.core.di_setup.ServiceCollection"),
            patch("src.core.di_setup.get_lifecycle_manager"),
            patch("pathlib.Path.exists", return_value=True),
            patch("src.core.di_setup.ConfigurationBinder") as mock_binder_class,
        ):
            mock_binder = Mock()
            mock_binder.load_from_file.side_effect = PermissionError(
                "Permission denied"
            )
            mock_binder_class.return_value = mock_binder
            with pytest.raises(PermissionError):
                setup.initialize(config_file="/restricted/file.yaml")
    def test_none_and_empty_modules_handling(self):
        """测试None和空模块处理"""
        setup = DISetup()
        with (
            patch("src.core.di_setup.ServiceCollection") as mock_collection,
            patch("src.core.di_setup.get_lifecycle_manager") as mock_lifecycle,
        ):
            mock_container = Mock()
            mock_collection.return_value.build_container.return_value = mock_container
            mock_lifecycle.return_value = Mock()
            container1 = setup.initialize(auto_scan_modules=None)
            assert container1 is mock_container
            container2 = setup.initialize(auto_scan_modules=[])
            assert container2 is mock_container
class TestDISetupIntegrationFunctional:
    """DI设置功能集成测试"""
    def test_full_initialization_integration(self):
        """测试完整初始化集成"""
        setup = DISetup(profile="test")
        with (
            patch("src.core.di_setup.ServiceCollection") as mock_collection,
            patch("src.core.di_setup.get_lifecycle_manager") as mock_lifecycle,
        ):
            mock_container = Mock()
            mock_collection.return_value.build_container.return_value = mock_container
            mock_lifecycle_instance = Mock()
            mock_lifecycle.return_value = mock_lifecycle_instance
            container = setup.initialize()
            assert setup.container is container
            assert setup.lifecycle_manager is mock_lifecycle_instance
            assert mock_container.register_singleton.called
    @pytest.mark.asyncio
    async def test_service_lifecycle_integration(self):
        """测试服务生命周期集成"""
        setup = DISetup(profile="test")
        mock_lifecycle_manager = AsyncMock()
        with (
            patch("src.core.di_setup.ServiceCollection") as mock_collection,
            patch(
                "src.core.di_setup.get_lifecycle_manager",
                return_value=mock_lifecycle_manager,
            ),
        ):
            mock_container = Mock()
            mock_collection.return_value.build_container.return_value = mock_container
            setup.initialize()
            await setup.start_services()
            await setup.stop_services()
            mock_lifecycle_manager.start_all_services.assert_called_once()
            mock_lifecycle_manager.shutdown.assert_called_once()
    def test_decorator_container_integration(self):
        """测试装饰器容器集成"""
        mock_container = Mock()
        mock_setup = Mock()
        mock_setup.container = mock_container
        with patch("src.core.di_setup.get_di_setup", return_value=mock_setup):
            pass
            @register_service(ServiceLifetime.SINGLETON)
            class TestService:
                def __init__(self):
                    self.value = "test"
            assert hasattr(TestService, "__di_lifetime__")
            assert TestService.__di_lifetime__ == ServiceLifetime.SINGLETON
            assert TestService.__di_name__ == "TestService"
            mock_container.register_singleton.assert_called_once_with(TestService)
    def test_multiple_services_integration(self):
        """测试多服务集成"""
        mock_container = Mock()
        mock_setup = Mock()
        mock_setup.container = mock_container
        with patch("src.core.di_setup.get_di_setup", return_value=mock_setup):
            pass
            @register_service(ServiceLifetime.SINGLETON)
            class ServiceA:
                pass
            @register_service(ServiceLifetime.SCOPED)
            class ServiceB:
                pass
            @register_service(ServiceLifetime.TRANSIENT)
            class ServiceC:
                pass
            assert mock_container.register_singleton.called
            assert mock_container.register_scoped.called
            assert mock_container.register_transient.called
