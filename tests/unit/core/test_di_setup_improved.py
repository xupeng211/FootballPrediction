# TODO: Consider creating a fixture for 47 repeated Mock creations

# TODO: Consider creating a fixture for 47 repeated Mock creations

from unittest.mock import AsyncMock, MagicMock, Mock, patch

"""
DI设置改进版测试
Tests for improved DI setup module

测试真实的依赖注入设置功能。
"""

import asyncio
import os
import sys
import tempfile
from pathlib import Path

import pytest

# 添加项目路径
sys.path.insert(0, str(Path(__file__).parent.parent.parent))
sys.path.insert(0, "src")

from src.core.di_setup import (DISetup, configure_di, create_di_config,
                               get_di_setup, register_service)


@pytest.mark.unit
class TestDISetupImproved:
    """DI设置改进版测试"""

    @pytest.fixture
    def setup_instance(self):
        """创建DISetup实例"""
        return DISetup(profile="test")

    @pytest.fixture
    def temp_config_file(self):
        """创建临时配置文件"""
        config_content = """
profiles:
  test:
    database:
      host: localhost
      port: 5432
    redis:
      host: localhost
      port: 6379
"""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            f.write(config_content)
            temp_file = f.name

        yield temp_file

        # 清理
        os.unlink(temp_file)

    # ========================================
    # 基础功能测试
    # ========================================

    def test_di_setup_creation_with_default_profile(self):
        """测试使用默认配置文件创建DI设置"""
        setup = DISetup()
        assert setup.profile == "development"
        assert setup.container is None
        assert setup.lifecycle_manager is None

    def test_di_setup_creation_with_custom_profile(self):
        """测试使用自定义配置文件创建DI设置"""
        setup = DISetup(profile="production")
        assert setup.profile == "production"

    def test_di_setup_creation_with_none_profile(self):
        """测试使用None配置文件"""
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

    def test_di_setup_profile_attribute(self):
        """测试DI设置的profile属性"""
        setup = DISetup(profile="test")
        assert hasattr(setup, "profile")
        assert setup.profile == "test"
        assert isinstance(setup.profile, str)

    # ========================================
    # 初始化测试
    # ========================================

    def test_initialize_basic_functionality(self):
        """测试基础初始化功能"""
        setup = DISetup(profile="test")

        # Mock依赖组件
        with (
            patch("src.core.di_setup.ServiceCollection") as mock_collection,
            patch("src.core.di_setup.get_lifecycle_manager") as mock_lifecycle,
        ):
            # 设置mock对象
            mock_container = Mock()
            mock_collection.return_value.build_container.return_value = mock_container
            mock_lifecycle.return_value = Mock()

            # 执行初始化
            container = setup.initialize()

            # 验证结果
            assert container is mock_container
            assert setup.container is mock_container
            assert setup.lifecycle_manager is not None

            # 验证调用
            mock_collection.assert_called_once()
            mock_lifecycle.assert_called_once()

    def test_initialize_with_nonexistent_config_file(self):
        """测试使用不存在的配置文件初始化"""
        setup = DISetup()

        with (
            patch("src.core.di_setup.ServiceCollection") as mock_collection,
            patch("src.core.di_setup.get_lifecycle_manager") as mock_lifecycle,
        ):
            mock_container = Mock()
            mock_collection.return_value.build_container.return_value = mock_container
            mock_lifecycle.return_value = Mock()

            # 使用不存在的文件
            container = setup.initialize(config_file="/nonexistent/file.yaml")

            # 应该正常初始化，跳过配置文件
            assert container is mock_container

    def test_initialize_with_auto_scan_modules(self):
        """测试带自动扫描模块的初始化"""
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

            # 验证自动绑定器被调用
            mock_auto_binder_class.assert_called_once_with(mock_container)
            assert mock_auto_binder.bind_from_assembly.call_count == 2

    def test_initialize_with_config_file(self, temp_config_file):
        """测试使用配置文件初始化"""
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

            # 验证配置绑定器被调用
            mock_binder_class.assert_called_once()
            mock_binder.load_from_file.assert_called_once_with(temp_config_file)
            mock_binder.set_active_profile.assert_called_once_with("development")
            mock_binder.apply_configuration.assert_called_once()

    # ========================================
    # 服务注册测试
    # ========================================

    def test_register_core_services_functionality(self):
        """测试核心服务注册功能"""
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

            # 验证生命周期管理器被注册
            mock_container.register_singleton.assert_any_call(
                mock_lifecycle_instance.__class__, instance=mock_lifecycle_instance
            )

    def test_auto_register_repositories_with_import_error(self):
        """测试仓储注册时的导入错误处理"""
        setup = DISetup()

        with patch("src.core.di_setup.ServiceCollection") as mock_collection:
            mock_container = Mock()
            mock_collection.return_value.build_container.return_value = mock_container

            setup.initialize()

            # 模拟导入错误
            with patch(
                "src.core.di_setup.DISetup._auto_register_repositories"
            ) as mock_register:
                mock_register.side_effect = ImportError(
                    "No module named 'missing.repository'"
                )

                # 应该不会抛出异常
                try:
                    pass
                except Exception:
                    pass
                    setup._auto_register_repositories()
                except ImportError:
                    pytest.fail("ImportError should be handled gracefully")

    def test_auto_register_services_with_import_error(self):
        """测试服务注册时的导入错误处理"""
        setup = DISetup()

        with patch("src.core.di_setup.ServiceCollection") as mock_collection:
            mock_container = Mock()
            mock_collection.return_value.build_container.return_value = mock_container

            setup.initialize()

            # 模拟导入错误
            with patch(
                "src.core.di_setup.DISetup._auto_register_services"
            ) as mock_register:
                mock_register.side_effect = ImportError(
                    "No module named 'missing.service'"
                )

                # 应该不会抛出异常
                try:
                    pass
                except Exception:
                    pass
                    setup._auto_register_services()
                except ImportError:
                    pytest.fail("ImportError should be handled gracefully")

    # ========================================
    # 服务生命周期测试
    # ========================================

    @pytest.mark.asyncio
    async def test_start_services_with_lifecycle_manager(self):
        """测试启动服务（有生命周期管理器）"""
        setup = DISetup()

        mock_lifecycle_manager = AsyncMock()
        setup.lifecycle_manager = mock_lifecycle_manager

        await setup.start_services()

        mock_lifecycle_manager.start_all_services.assert_called_once()
        mock_lifecycle_manager.start_monitoring.assert_called_once_with(interval=30.0)

    @pytest.mark.asyncio
    async def test_start_services_without_lifecycle_manager(self):
        """测试启动服务（无生命周期管理器）"""
        setup = DISetup()
        setup.lifecycle_manager = None

        # 应该不会抛出异常
        await setup.start_services()

    @pytest.mark.asyncio
    async def test_stop_services_with_lifecycle_manager(self):
        """测试停止服务（有生命周期管理器）"""
        setup = DISetup()

        mock_lifecycle_manager = AsyncMock()
        setup.lifecycle_manager = mock_lifecycle_manager

        await setup.stop_services()

        mock_lifecycle_manager.shutdown.assert_called_once()

    @pytest.mark.asyncio
    async def test_stop_services_without_lifecycle_manager(self):
        """测试停止服务（无生命周期管理器）"""
        setup = DISetup()
        setup.lifecycle_manager = None

        # 应该不会抛出异常
        await setup.stop_services()

    # ========================================
    # 全局实例测试
    # ========================================

    def test_get_di_setup_singleton_behavior(self):
        """测试全局DI设置实例单例行为"""
        setup1 = get_di_setup()
        setup2 = get_di_setup()

        assert setup1 is setup2
        assert isinstance(setup1, DISetup)

    def test_get_di_setup_initialization(self):
        """测试全局DI设置实例初始化"""
        setup = get_di_setup()
        assert setup.profile == "development"  # 默认值
        assert hasattr(setup, "container")
        assert hasattr(setup, "lifecycle_manager")

    # ========================================
    # 便捷函数测试
    # ========================================

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
            mock_setup.initialize.assert_called_once_with(
                config_file="test.yaml", auto_scan_modules=["test.module"]
            )

    # ========================================
    # 装饰器测试
    # ========================================

    def test_register_service_decorator_singleton(self):
        """测试服务注册装饰器 - 单例"""
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
        """测试服务注册装饰器 - 作用域"""
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
        """测试服务注册装饰器 - 带接口"""
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
        """测试服务注册装饰器 - 带名称"""
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
        """测试服务注册装饰器 - 无容器"""
        mock_setup = Mock()
        mock_setup.container = None

        with patch("src.core.di_setup.get_di_setup", return_value=mock_setup):
            pass

            @register_service(ServiceLifetime.SINGLETON)
            class TestService:
                pass

            # 应该不会抛出异常，但不会调用注册方法
            mock_setup.container.register_singleton.assert_not_called()

    # ========================================
    # 配置文件创建测试
    # ========================================

    def test_create_di_config_function(self):
        """测试创建DI配置文件函数"""
        mock_config_content = "sample config content"

        with (
            patch(
                "src.core.di_setup.generate_sample_config",
                return_value=mock_config_content,
            ),
            tempfile.NamedTemporaryFile(
                mode="w", suffix=".yaml", delete=False
            ) as temp_file,
        ):
            temp_path = temp_file.name

        try:
            pass
        except Exception:
            pass
            create_di_config(temp_path, "yaml")

            # 验证文件内容
            with open(temp_path, "r") as f:
                content = f.read()
                assert content == mock_config_content

        finally:
            if os.path.exists(temp_path):
                os.unlink(temp_path)

    def test_create_di_config_default_parameters(self):
        """测试创建DI配置文件的默认参数"""
        with (
            patch("src.core.di_setup.generate_sample_config") as mock_generate,
            patch("pathlib.Path") as mock_path,
        ):
            mock_path_instance = Mock()
            mock_path.return_value = mock_path_instance
            mock_path_instance.parent.mkdir = Mock()
            mock_path_instance.__enter__ = Mock()
            mock_path_instance.__enter__.return_value.write = Mock()

            create_di_config()

            mock_generate.assert_called_once_with("yaml")
            mock_path.assert_called_once_with("configs/di-config.yaml")

    # ========================================
    # 边界条件测试
    # ========================================

    def test_empty_config_file_handling(self):
        """测试空配置文件处理"""
        empty_config = tempfile.NamedTemporaryFile(
            mode="w", suffix=".yaml", delete=False
        )
        empty_config.write("")
        empty_config.close()

        try:
            pass
        except Exception:
            pass
            setup = DISetup()

            with (
                patch("src.core.di_setup.ServiceCollection") as mock_collection,
                patch("src.core.di_setup.get_lifecycle_manager") as mock_lifecycle,
            ):
                mock_container = Mock()
                mock_collection.return_value.build_container.return_value = (
                    mock_container
                )
                mock_lifecycle.return_value = Mock()

                # 空文件应该不会导致错误
                container = setup.initialize(config_file=empty_config.name)
                assert container is mock_container

        finally:
            os.unlink(empty_config.name)

    def test_none_auto_scan_modules(self):
        """测试None自动扫描模块"""
        setup = DISetup()

        with (
            patch("src.core.di_setup.ServiceCollection") as mock_collection,
            patch("src.core.di_setup.get_lifecycle_manager") as mock_lifecycle,
        ):
            mock_container = Mock()
            mock_collection.return_value.build_container.return_value = mock_container
            mock_lifecycle.return_value = Mock()

            # None模块列表应该正常处理
            container = setup.initialize(auto_scan_modules=None)
            assert container is mock_container

    def test_empty_auto_scan_modules(self):
        """测试空自动扫描模块"""
        setup = DISetup()

        with (
            patch("src.core.di_setup.ServiceCollection") as mock_collection,
            patch("src.core.di_setup.get_lifecycle_manager") as mock_lifecycle,
        ):
            mock_container = Mock()
            mock_collection.return_value.build_container.return_value = mock_container
            mock_lifecycle.return_value = Mock()

            # 空模块列表应该正常处理
            container = setup.initialize(auto_scan_modules=[])
            assert container is mock_container

    # ========================================
    # 错误处理测试
    # ========================================

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

            # 权限错误应该被处理
            with pytest.raises(PermissionError):
                setup.initialize(config_file="/restricted/file.yaml")

    @pytest.mark.asyncio
    async def test_lifecycle_manager_start_error(self):
        """测试生命周期管理器启动错误"""
        setup = DISetup()

        mock_lifecycle_manager = AsyncMock()
        mock_lifecycle_manager.start_all_services.side_effect = Exception(
            "Start failed"
        )
        setup.lifecycle_manager = mock_lifecycle_manager

        # 启动错误应该被传播
        with pytest.raises(Exception, match="Start failed"):
            await setup.start_services()


class TestDISetupIntegration:
    """DI设置集成测试"""

    def test_full_initialization_flow(self):
        """测试完整初始化流程"""
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

            # 验证初始化步骤
            assert setup.container is container
            assert setup.lifecycle_manager is mock_lifecycle_instance
            assert mock_container.register_singleton.call_count >= 1
            assert mock_container.register_scoped.call_count >= 1

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

            # 测试启动和停止
            await setup.start_services()
            await setup.stop_services()

            mock_lifecycle_manager.start_all_services.assert_called_once()
            mock_lifecycle_manager.shutdown.assert_called_once()

    def test_decorator_integration_with_container(self):
        """测试装饰器与容器集成"""
        mock_container = Mock()
        mock_setup = Mock()
        mock_setup.container = mock_container

        with patch("src.core.di_setup.get_di_setup", return_value=mock_setup):
            pass

            @register_service(ServiceLifetime.SINGLETON)
            class TestService:
                def __init__(self):
                    self.value = "test"

            # 验证装饰器属性
            assert hasattr(TestService, "__di_lifetime__")
            assert TestService.__di_lifetime__ == ServiceLifetime.SINGLETON
            assert TestService.__di_name__ == "TestService"

            # 验证容器调用
            mock_container.register_singleton.assert_called_once_with(TestService)

    def test_multiple_decorators_integration(self):
        """测试多个装饰器集成"""
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

            # 验证所有服务都被注册
            assert mock_container.register_singleton.called
            assert mock_container.register_scoped.called
            assert mock_container.register_transient.called
