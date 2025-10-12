"""
测试 src/core/di.py 模块（依赖注入）
"""

import pytest
import sys
from unittest.mock import Mock, MagicMock, patch

# 确保模块可以导入
sys.path.insert(0, 'src')

try:
    from src.core.di import DIContainer, get_container, register_service
    DI_AVAILABLE = True
except ImportError:
    DI_AVAILABLE = False


@pytest.mark.skipif(not DI_AVAILABLE, reason="DI模块不可用")
class TestDIModule:
    """测试依赖注入模块"""

    def test_di_imports(self):
        """测试DI模块导入"""
        from src.core import di
        assert di is not None

    def test_container_creation(self):
        """测试容器创建"""
        container = DIContainer()
        assert container is not None

    def test_container_register(self):
        """测试服务注册"""
        container = DIContainer()

        # 创建一个简单的服务
        class TestService:
            def __init__(self):
                self.value = "test"

        # 注册服务
        container.register('test_service', TestService)

        # 验证服务已注册
        assert container.is_registered('test_service')

    def test_container_get_service(self):
        """测试获取服务"""
        container = DIContainer()

        class TestService:
            def __init__(self):
                self.value = "test"

        container.register('test_service', TestService)

        # 获取服务
        service = container.get('test_service')
        assert service is not None
        assert service.value == "test"

    def test_container_singleton(self):
        """测试单例模式"""
        container = DIContainer()

        class TestService:
            def __init__(self):
                self.value = "test"

        container.register('test_service', TestService, singleton=True)

        # 获取两次应该是同一个实例
        service1 = container.get('test_service')
        service2 = container.get('test_service')

        assert service1 is service2

    def test_get_global_container(self):
        """测试获取全局容器"""
        container = get_container()
        assert container is not None
        assert isinstance(container, DIContainer)

    def test_register_service_decorator(self):
        """测试服务注册装饰器"""
        @register_service('decorated_service')
        class DecoratedService:
            def __init__(self):
                self.name = "decorated"

        # 验证服务已注册到全局容器
        container = get_container()
        service = container.get('decorated_service')
        assert service is not None
        assert service.name == "decorated"

    def test_dependency_injection(self):
        """测试依赖注入"""
        container = DIContainer()

        class ServiceA:
            def __init__(self):
                self.name = "ServiceA"

        class ServiceB:
            def __init__(self, service_a: ServiceA):
                self.service_a = service_a
                self.name = "ServiceB"

        # 注册服务
        container.register('service_a', ServiceA)
        container.register('service_b', ServiceB)

        # 获取ServiceB，应该自动注入ServiceA
        service_b = container.get('service_b')
        assert service_b is not None
        assert service_b.service_a is not None
        assert service_b.service_a.name == "ServiceA"

    def test_container_clear(self):
        """测试清空容器"""
        container = DIContainer()

        class TestService:
            pass

        container.register('test_service', TestService)
        assert container.is_registered('test_service')

        # 清空容器
        container.clear()
        assert not container.is_registered('test_service')

    def test_container_has_method(self):
        """测试has方法"""
        container = DIContainer()

        # 未注册的服务
        assert not container.has('non_existent')

        # 注册服务后
        class TestService:
            pass

        container.register('test_service', TestService)
        assert container.has('test_service')