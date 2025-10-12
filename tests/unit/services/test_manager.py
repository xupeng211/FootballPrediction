"""
服务管理器测试
Tests for Service Manager
"""

import pytest
from unittest.mock import Mock, AsyncMock, patch, MagicMock

from src.services.manager import (
    ServiceManager,
    service_manager,
    _SERVICE_FACTORIES,
    _ensure_default_services,
)
from src.services.base_unified import BaseService


class TestServiceManager:
    """服务管理器测试"""

    @pytest.fixture
    def manager(self):
        """创建服务管理器实例"""
        return ServiceManager()

    @pytest.fixture
    def mock_service(self):
        """创建模拟服务"""
        service = Mock(spec=BaseService)
        service.name = "TestService"
        service.initialize = AsyncMock(return_value=True)
        service.shutdown = AsyncMock()
        return service

    def test_manager_initialization(self, manager):
        """测试：管理器初始化"""
        assert isinstance(manager._services, dict)
        assert len(manager._services) == 0
        assert manager.logger is not None

    def test_register_service_new(self, manager, mock_service):
        """测试：注册新服务"""
        # When
        manager.register_service("test_service", mock_service)

        # Then
        assert "test_service" in manager._services
        assert manager._services["test_service"] == mock_service

    def test_register_service_duplicate_same(self, manager, mock_service):
        """测试：注册相同服务（重复）"""
        # Given
        manager.register_service("test_service", mock_service)

        # When
        manager.register_service("test_service", mock_service)

        # Then
        # 应该只有一个服务
        assert len(manager._services) == 1
        assert manager._services["test_service"] == mock_service

    def test_register_service_duplicate_same_class(self, manager):
        """测试：注册相同类的不同实例"""
        # Given
        service1 = Mock(spec=BaseService)
        service1.__class__ = Mock
        service2 = Mock(spec=BaseService)
        service2.__class__ = Mock

        # When
        manager.register_service("test_service", service1)
        manager.register_service("test_service", service2)

        # Then
        # 应该跳过第二次注册
        assert manager._services["test_service"] == service1

    def test_register_service_replace(self, manager):
        """测试：替换已注册的服务"""

        # Given
        class OldService:
            pass

        class NewService:
            pass

        service1 = Mock(spec=BaseService)
        service1.__class__ = OldService
        service2 = Mock(spec=BaseService)
        service2.__class__ = NewService

        manager.register_service("test_service", service1)

        # When
        manager.register_service("test_service", service2)

        # Then
        assert manager._services["test_service"] == service2

    def test_get_service_exists(self, manager, mock_service):
        """测试：获取存在的服务"""
        # Given
        manager.register_service("test_service", mock_service)

        # When
        result = manager.get_service("test_service")

        # Then
        assert result == mock_service

    def test_get_service_not_exists(self, manager):
        """测试：获取不存在的服务"""
        # When
        result = manager.get_service("nonexistent")

        # Then
        assert result is None

    def test_list_services(self, manager):
        """测试：获取所有服务列表"""
        # Given
        service1 = Mock(spec=BaseService)
        service2 = Mock(spec=BaseService)
        manager.register_service("service1", service1)
        manager.register_service("service2", service2)

        # When
        result = manager.list_services()

        # Then
        assert isinstance(result, dict)
        assert len(result) == 2
        assert "service1" in result
        assert "service2" in result
        # 应该是副本，不是原字典
        assert result is not manager._services

    def test_services_property(self, manager):
        """测试：services属性"""
        # Given
        service = Mock(spec=BaseService)
        manager.register_service("test", service)

        # When
        services = manager.services

        # Then
        assert services is manager._services  # 属性应该返回原字典
        assert "test" in services

    @pytest.mark.asyncio
    async def test_initialize_all_success(self, manager):
        """测试：成功初始化所有服务"""
        # Given
        service1 = Mock(spec=BaseService)
        service1.name = "Service1"
        service1.initialize = AsyncMock(return_value=True)
        service2 = Mock(spec=BaseService)
        service2.name = "Service2"
        service2.initialize = AsyncMock(return_value=True)

        manager.register_service("service1", service1)
        manager.register_service("service2", service2)

        # When
        result = await manager.initialize_all()

        # Then
        assert result is True
        service1.initialize.assert_called_once()
        service2.initialize.assert_called_once()

    @pytest.mark.asyncio
    async def test_initialize_all_partial_failure(self, manager):
        """测试：部分服务初始化失败"""
        # Given
        service1 = Mock(spec=BaseService)
        service1.name = "Service1"
        service1.initialize = AsyncMock(return_value=True)
        service2 = Mock(spec=BaseService)
        service2.name = "Service2"
        service2.initialize = AsyncMock(return_value=False)

        manager.register_service("service1", service1)
        manager.register_service("service2", service2)

        # When
        result = await manager.initialize_all()

        # Then
        assert result is False
        # 两个服务都应该尝试初始化
        service1.initialize.assert_called_once()
        service2.initialize.assert_called_once()

    @pytest.mark.asyncio
    async def test_initialize_all_exception(self, manager):
        """测试：初始化时抛出异常"""
        # Given
        service = Mock(spec=BaseService)
        service.name = "ErrorService"
        service.initialize = AsyncMock(side_effect=RuntimeError("Init error"))

        manager.register_service("error_service", service)

        # When
        result = await manager.initialize_all()

        # Then
        assert result is False
        service.initialize.assert_called_once()

    @pytest.mark.asyncio
    async def test_initialize_all_empty(self, manager):
        """测试：初始化空服务列表"""
        # When
        result = await manager.initialize_all()

        # Then
        assert result is True

    @pytest.mark.asyncio
    async def test_shutdown_all_success(self, manager):
        """测试：成功关闭所有服务"""
        # Given
        service1 = Mock(spec=BaseService)
        service1.name = "Service1"
        service1.shutdown = AsyncMock()
        service2 = Mock(spec=BaseService)
        service2.name = "Service2"
        service2.shutdown = AsyncMock()

        manager.register_service("service1", service1)
        manager.register_service("service2", service2)

        # When
        await manager.shutdown_all()

        # Then
        service1.shutdown.assert_called_once()
        service2.shutdown.assert_called_once()

    @pytest.mark.asyncio
    async def test_shutdown_all_exception(self, manager):
        """测试：关闭时抛出异常"""
        # Given
        service1 = Mock(spec=BaseService)
        service1.name = "Service1"
        service1.shutdown = AsyncMock()
        service2 = Mock(spec=BaseService)
        service2.name = "ErrorService"
        service2.shutdown = AsyncMock(side_effect=RuntimeError("Shutdown error"))

        manager.register_service("service1", service1)
        manager.register_service("error_service", service2)

        # When
        await manager.shutdown_all()

        # Then
        # 即使有异常，两个服务都应该尝试关闭
        service1.shutdown.assert_called_once()
        service2.shutdown.assert_called_once()

    @pytest.mark.asyncio
    async def test_shutdown_all_empty(self, manager):
        """测试：关闭空服务列表"""
        # When - 不应该抛出异常
        await manager.shutdown_all()

        # Then - 正常完成
        assert True


class TestGlobalServiceManager:
    """测试全局服务管理器"""

    def test_global_manager_exists(self):
        """测试：全局管理器存在"""
        from src.services.manager import service_manager

        assert service_manager is not None
        assert isinstance(service_manager, ServiceManager)

    def test_service_factories(self):
        """测试：服务工厂字典"""
        assert isinstance(_SERVICE_FACTORIES, dict)
        assert "ContentAnalysisService" in _SERVICE_FACTORIES
        assert "UserProfileService" in _SERVICE_FACTORIES
        assert "DataProcessingService" in _SERVICE_FACTORIES

    @patch("src.services.manager.get_settings")
    def test_ensure_default_services_no_enabled(self, mock_get_settings):
        """测试：没有启用服务"""
        # Given
        mock_settings = Mock()
        mock_settings.enabled_services = []
        mock_get_settings.return_value = mock_settings

        ServiceManager()

        # When
        _ensure_default_services()

        # Then
        # 全局管理器应该被使用
        from src.services.manager import service_manager

        assert isinstance(service_manager, ServiceManager)

    @patch("src.services.manager.get_settings")
    def test_ensure_default_services_with_enabled(self, mock_get_settings):
        """测试：有启用的服务"""
        # Given
        mock_settings = Mock()
        mock_settings.enabled_services = ["ContentAnalysisService"]
        mock_get_settings.return_value = mock_settings

        # 创建新的管理器实例来测试
        manager = ServiceManager()

        # Patch the global service_manager
        with patch("src.services.manager.service_manager", manager):
            # When
            _ensure_default_services()

            # Then
            assert "ContentAnalysisService" in manager.services

    @patch("src.services.manager.get_settings")
    def test_ensure_default_services_unknown_service(self, mock_get_settings):
        """测试：未知服务名称"""
        # Given
        mock_settings = Mock()
        mock_settings.enabled_services = ["UnknownService"]
        mock_get_settings.return_value = mock_settings

        manager = ServiceManager()

        with patch("src.services.manager.service_manager", manager):
            # When
            _ensure_default_services()

            # Then
            assert len(manager.services) == 0

    @patch("src.services.manager.get_settings")
    def test_ensure_default_services_none_settings(self, mock_get_settings):
        """测试：settings为None或enabled_services为None"""
        # Given
        mock_settings = Mock()
        mock_settings.enabled_services = None
        mock_get_settings.return_value = mock_settings

        manager = ServiceManager()

        with patch("src.services.manager.service_manager", manager):
            # When
            _ensure_default_services()

            # Then
            # 不应该抛出异常
            assert len(manager.services) == 0

    @patch("src.services.manager.get_settings")
    def test_ensure_default_services_already_registered(self, mock_get_settings):
        """测试：服务已注册"""
        # Given
        mock_settings = Mock()
        mock_settings.enabled_services = ["ContentAnalysisService"]
        mock_get_settings.return_value = mock_settings

        manager = ServiceManager()
        # 预先注册服务
        manager.register_service("ContentAnalysisService", Mock())

        with patch("src.services.manager.service_manager", manager):
            # When
            _ensure_default_services()

            # Then
            # 只应该有一个服务
            assert len(manager.services) == 1


class TestServiceManagerIntegration:
    """服务管理器集成测试"""

    @pytest.mark.asyncio
    async def test_full_lifecycle(self):
        """测试：完整的生命周期"""
        # Given
        manager = ServiceManager()
        service = Mock(spec=BaseService)
        service.name = "TestService"
        service.initialize = AsyncMock(return_value=True)
        service.shutdown = AsyncMock()

        # When
        manager.register_service("test", service)
        init_result = await manager.initialize_all()
        await manager.shutdown_all()

        # Then
        assert init_result is True
        service.initialize.assert_called_once()
        service.shutdown.assert_called_once()

    def test_multiple_services_same_type(self):
        """测试：多个相同类型的服务"""
        # Given
        manager = ServiceManager()
        service1 = Mock(spec=BaseService)
        service1.__class__ = Mock
        service2 = Mock(spec=BaseService)
        service2.__class__ = Mock

        # When
        manager.register_service("service1", service1)
        manager.register_service("service2", service2)

        # Then
        assert len(manager.services) == 2
        assert manager.get_service("service1") == service1
        assert manager.get_service("service2") == service2
