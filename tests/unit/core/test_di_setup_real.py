"""
DI设置真实模块测试
Tests for real DI setup module

测试真实的依赖注入设置功能。
"""

import pytest
import tempfile
import os
from pathlib import Path
from unittest.mock import Mock, patch, AsyncMock
import sys

# 添加项目路径
sys.path.insert(0, str(Path(__file__).parent.parent.parent))
sys.path.insert(0, "src")

from src.core.di_setup import DISetup, get_di_setup, configure_di, register_service
from src.core.di import DIContainer, ServiceLifetime
from src.core.service_lifecycle import ServiceLifecycleManager
from src.core.config_di import ConfigurationBinder


class TestDISetupReal:
    """真实DI设置模块测试"""

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
            setup = DISetup(profile=None)
            assert setup.profile == "staging"

    # ========================================
    # 初始化测试
    # ========================================

    @patch("src.core.di_setup.ServiceCollection")
    @patch("src.core.di_setup.ServiceLifecycleManager")
    def test_initialize_without_config_file(self, mock_lifecycle, mock_collection):
        """测试无配置文件的初始化"""
        mock_container = Mock(spec=DIContainer)
        mock_collection.return_value.build_container.return_value = mock_container
        mock_lifecycle.return_value = Mock(spec=ServiceLifecycleManager)

        setup = DISetup()
        container = setup.initialize()

        assert container is mock_container
        assert setup.container is mock_container
        assert setup.lifecycle_manager is mock_lifecycle.return_value

        mock_collection.assert_called_once()
        mock_container.register_singleton.assert_called()

    @patch("src.core.di_setup.ConfigurationBinder")
    @patch("src.core.di_setup.ServiceLifecycleManager")
    def test_initialize_with_config_file(self, mock_lifecycle, mock_binder_class):
        """测试有配置文件的初始化"""
        temp_config = tempfile.NamedTemporaryFile(
            mode="w", suffix=".yaml", delete=False
        )
        temp_config.write(
            """
test:
  database:
    host: localhost
""".encode()
        )
        temp_config.close()

        try:
            mock_container = Mock(spec=DIContainer)
            mock_binder = Mock(spec=ConfigurationBinder)
            mock_binder.container = mock_container
            mock_binder_class.return_value = mock_binder
            mock_lifecycle.return_value = Mock(spec=ServiceLifecycleManager)

            setup = DISetup()
            container = setup.initialize(config_file=temp_config.name)

            assert container is mock_container
            mock_binder_class.assert_called_once_with(DIContainer())
            mock_binder.load_from_file.assert_called_once_with(temp_config.name)
            mock_binder.set_active_profile.assert_called_once_with("test")
            mock_binder.apply_configuration.assert_called_once()

        finally:
            os.unlink(temp_config.name)

    @patch("src.core.di_setup.ServiceCollection")
    def test_initialize_with_auto_scan(self, mock_collection):
        """测试带自动扫描的初始化"""
        mock_container = Mock(spec=DIContainer)
        mock_collection.return_value.build_container.return_value = mock_container
        mock_auto_binder = Mock()

        with patch("src.core.di_setup.AutoBinder") as mock_auto_binder_class:
            mock_auto_binder_class.return_value = mock_auto_binder

            setup = DISetup()
            container = setup.initialize(
                config_file=None, auto_scan_modules=["test.module1", "test.module2"]
            )

            assert container is mock_container
            mock_auto_binder_class.assert_called_once_with(mock_container)
            assert mock_auto_binder.bind_from_assembly.call_count == 2

    # ========================================
    # 核心服务注册测试
    # ========================================

    @patch("src.core.di_setup.ServiceCollection")
    @patch("src.core.di_setup.ServiceLifecycleManager")
    def test_register_core_services(self, mock_lifecycle, mock_collection):
        """测试核心服务注册"""
        mock_container = Mock(spec=DIContainer)
        mock_collection.return_value.build_container.return_value = mock_container
        mock_lifecycle.return_value = Mock(spec=ServiceLifecycleManager)

        setup = DISetup()
        setup.initialize()

        # 验证生命周期管理器被注册为单例
        mock_container.register_singleton.assert_any_call(
            ServiceLifecycleManager, instance=mock_lifecycle.return_value
        )

    @patch("src.core.di_setup.ServiceCollection")
    @patch("src.core.di_setup.ServiceLifecycleManager")
    @patch("src.core.di_setup.MatchRepository")
    @patch("src.core.di_setup.PredictionRepository")
    @patch("src.core.di_setup.UserRepository")
    def test_auto_register_repositories(
        self,
        mock_user_repo,
        mock_pred_repo,
        mock_match_repo,
        mock_lifecycle,
        mock_collection,
    ):
        """测试自动注册仓储"""
        mock_container = Mock(spec=DIContainer)
        mock_collection.return_value.build_container.return_value = mock_container
        mock_lifecycle.return_value = Mock(spec=ServiceLifecycleManager)

        setup = DISetup()
        setup.initialize()

        # 验证仓储被注册
        calls = mock_container.register_scoped.call_args_list
        assert len(calls) >= 3  # 至少3个仓储

    @patch("src.core.di_setup.ServiceCollection")
    @patch("src.core.di_setup.ServiceLifecycleManager")
    @patch("src.core.di_setup.DatabaseService")
    @patch("src.core.di_setup.PredictionService")
    @patch("src.core.di_setup.CacheService")
    def test_auto_register_services(
        self,
        mock_cache_service,
        mock_pred_service,
        mock_db_service,
        mock_lifecycle,
        mock_collection,
    ):
        """测试自动注册业务服务"""
        mock_container = Mock(spec=DIContainer)
        mock_collection.return_value.build_container.return_value = mock_container
        mock_lifecycle.return_value = Mock(spec=ServiceLifecycleManager)

        setup = DISetup()
        setup.initialize()

        # 验证业务服务被注册
        mock_container.register_singleton.assert_any_call(mock_db_service)
        mock_container.register_scoped.assert_any_call(mock_pred_service)
        mock_container.register_singleton.assert_any_call(mock_cache_service)

    # ========================================
    # 服务生命周期测试
    # ========================================

    @patch("src.core.di_setup.ServiceCollection")
    @patch("src.core.di_setup.ServiceLifecycleManager")
    async def test_start_services(self, mock_lifecycle, mock_collection):
        """测试启动服务"""
        mock_container = Mock(spec=DIContainer)
        mock_collection.return_value.build_container.return_value = mock_container
        mock_lifecycle_instance = AsyncMock(spec=ServiceLifecycleManager)
        mock_lifecycle.return_value = mock_lifecycle_instance

        setup = DISetup()
        setup.initialize()

        await setup.start_services()

        mock_lifecycle_instance.start_all_services.assert_called_once()
        mock_lifecycle_instance.start_monitoring.assert_called_once_with(interval=30.0)

    @patch("src.core.di_setup.ServiceCollection")
    @patch("src.core.di_setup.ServiceLifecycleManager")
    async def test_stop_services(self, mock_lifecycle, mock_collection):
        """测试停止服务"""
        mock_container = Mock(spec=DIContainer)
        mock_collection.return_value.build_container.return_value = mock_container
        mock_lifecycle_instance = AsyncMock(spec=ServiceLifecycleManager)
        mock_lifecycle.return_value = mock_lifecycle_instance

        setup = DISetup()
        setup.initialize()

        await setup.stop_services()

        mock_lifecycle_instance.shutdown.assert_called_once()

    # ========================================
    # 全局实例测试
    # ========================================

    def test_get_di_setup_singleton(self):
        """测试全局DI设置实例单例"""
        setup1 = get_di_setup()
        setup2 = get_di_setup()

        assert setup1 is setup2
        assert isinstance(setup1, DISetup)

    def test_get_di_setup_initialization(self):
        """测试全局DI设置实例初始化"""
        setup = get_di_setup()
        assert setup.profile == "development"  # 默认值

    # ========================================
    # 便捷函数测试
    # ========================================

    @patch("src.core.di_setup.DISetup")
    def test_configure_di_function(self, mock_di_setup_class):
        """测试配置DI便捷函数"""
        mock_setup = Mock(spec=DISetup)
        mock_container = Mock(spec=DIContainer)
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

    @patch("src.core.di_setup.get_di_setup")
    def test_register_service_decorator_singleton(self, mock_get_di_setup):
        """测试服务注册装饰器 - 单例"""
        mock_container = Mock(spec=DIContainer)
        mock_setup = Mock()
        mock_setup.container = mock_container
        mock_get_di_setup.return_value = mock_setup

        @register_service(ServiceLifetime.SINGLETON)
        class TestService:
            pass

        mock_container.register_singleton.assert_called_once_with(TestService)
        assert hasattr(TestService, "__di_lifetime__")
        assert TestService.__di_lifetime__ == ServiceLifetime.SINGLETON

    @patch("src.core.di_setup.get_di_setup")
    def test_register_service_decorator_scoped(self, mock_get_di_setup):
        """测试服务注册装饰器 - 作用域"""
        mock_container = Mock(spec=DIContainer)
        mock_setup = Mock()
        mock_setup.container = mock_container
        mock_get_di_setup.return_value = mock_setup

        @register_service(ServiceLifetime.SCOPED)
        class TestService:
            pass

        mock_container.register_scoped.assert_called_once_with(TestService)

    @patch("src.core.di_setup.get_di_setup")
    def test_register_service_decorator_with_interface(self, mock_get_di_setup):
        """测试服务注册装饰器 - 带接口"""
        mock_container = Mock(spec=DIContainer)
        mock_setup = Mock()
        mock_setup.container = mock_container
        mock_get_di_setup.return_value = mock_setup

        class ITestService:
            pass

        @register_service(ServiceLifetime.TRANSIENT, interface=ITestService)
        class TestService:
            pass

        mock_container.register_transient.assert_called_once_with(
            ITestService, TestService
        )

    @patch("src.core.di_setup.get_di_setup")
    def test_register_service_decorator_with_name(self, mock_get_di_setup):
        """测试服务注册装饰器 - 带名称"""
        mock_container = Mock(spec=DIContainer)
        mock_setup = Mock()
        mock_setup.container = mock_container
        mock_get_di_setup.return_value = mock_setup

        @register_service(ServiceLifetime.SINGLETON, name="custom_service")
        class TestService:
            pass

        mock_container.register_singleton.assert_called_once_with(TestService)
        assert TestService.__di_name__ == "custom_service"

    @patch("src.core.di_setup.get_di_setup")
    def test_register_service_decorator_no_container(self, mock_get_di_setup):
        """测试服务注册装饰器 - 无容器"""
        mock_setup = Mock()
        mock_setup.container = None
        mock_get_di_setup.return_value = mock_setup

        @register_service(ServiceLifetime.SINGLETON)
        class TestService:
            pass

        # 应该不会抛出异常
        mock_container.register_singleton.assert_not_called()

    # ========================================
    # 错误处理测试
    # ========================================

    def test_import_error_handling_in_repositories(self):
        """测试仓储导入错误处理"""
        with patch(
            "src.core.di_setup.DISetup._register_core_services"
        ) as mock_register:
            setup = DISetup()

            # 模拟ImportError
            def side_effect():
                from unittest.mock import MagicMock

                raise ImportError("No module named 'missing.module'")

            setup._auto_register_repositories = side_effect

            # 应该不会抛出异常，只是记录警告
            try:
                setup._auto_register_repositories()
            except ImportError:
                pytest.fail("ImportError should be handled gracefully")

    def test_import_error_handling_in_services(self):
        """测试服务导入错误处理"""
        with patch(
            "src.core.di_setup.DISetup._register_core_services"
        ) as mock_register:
            setup = DISetup()

            # 模拟ImportError
            def side_effect():
                raise ImportError("No module named 'missing.service'")

            setup._auto_register_services = side_effect

            # 应该不会抛出异常，只是记录警告
            try:
                setup._auto_register_services()
            except ImportError:
                pytest.fail("ImportError should be handled gracefully")

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
            setup = DISetup()
            # 空文件应该不会导致错误
            container = setup.initialize(config_file=empty_config.name)
            assert container is not None
        finally:
            os.unlink(empty_config.name)

    def test_nonexistent_config_file(self):
        """测试不存在的配置文件"""
        setup = DISetup()

        # 不存在的文件应该跳过配置加载
        container = setup.initialize(config_file="/nonexistent/file.yaml")
        assert container is not None

    def test_empty_auto_scan_modules(self):
        """测试空的自动扫描模块列表"""
        setup = DISetup()

        # 空的模块列表应该正常处理
        container = setup.initialize(auto_scan_modules=[])
        assert container is not None

    # ========================================
    # 配置创建测试
    # ========================================

    @patch("src.core.di_setup.Path")
    @patch("src.core.di_setup.generate_sample_config")
    def test_create_di_config(self, mock_generate_config, mock_path):
        """测试创建DI配置文件"""
        mock_generate_config.return_value = "sample config content"
        mock_path_instance = Mock()
        mock_path.return_value = mock_path_instance

        from src.core.di_setup import create_di_config

        create_di_config("test_config.yaml", "yaml")

        mock_generate_config.assert_called_once_with("yaml")
        mock_path_instance.parent.mkdir.assert_called_once_with(
            parents=True, exist_ok=True
        )
        mock_path_instance.__enter__.return_value.write.assert_called_once_with(
            "sample config content"
        )

    @patch("src.core.di_setup.create_di_config")
    def test_create_di_config_default_parameters(self, mock_create):
        """测试创建DI配置文件的默认参数"""
        from src.core.di_setup import create_di_config

        create_di_config()

        mock_create.assert_called_once_with("configs/di-config.yaml", "yaml")


class TestDISetupIntegration:
    """DI设置集成测试"""

    @patch("src.core.di_setup.ServiceCollection")
    @patch("src.core.di_setup.ServiceLifecycleManager")
    def test_full_initialization_flow(self, mock_lifecycle, mock_collection):
        """测试完整初始化流程"""
        mock_container = Mock(spec=DIContainer)
        mock_collection.return_value.build_container.return_value = mock_container
        mock_lifecycle_instance = AsyncMock(spec=ServiceLifecycleManager)
        mock_lifecycle.return_value = mock_lifecycle_instance

        setup = DISetup(profile="test")
        container = setup.initialize()

        # 验证初始化步骤
        assert setup.container is container
        assert setup.lifecycle_manager is mock_lifecycle_instance
        assert mock_container.register_singleton.call_count >= 1
        assert mock_container.register_scoped.call_count >= 1

        # 测试服务启动和停止
        import asyncio

        asyncio.run(setup.start_services())
        asyncio.run(setup.stop_services())

        mock_lifecycle_instance.start_all_services.assert_called_once()
        mock_lifecycle_instance.start_monitoring.assert_called_once()
        mock_lifecycle_instance.shutdown.assert_called_once()
