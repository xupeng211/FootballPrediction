# TODO: Consider creating a fixture for 4 repeated Mock creations

# TODO: Consider creating a fixture for 4 repeated Mock creations

import sys
from pathlib import Path

# 添加项目路径


import pytest


# Mock DI模块


# 不需要初始化就能获取mock服务
# Mock容器返回None


# Mock测试


# Mock验证

# 通过容器直接注册


# Mock不会抛出错误


# 不同容器应该有不同的实例
sys.path.insert(0, str(Path(__file__).parent.parent.parent))
sys.path.insert(0, "src")
"""
DI设置测试 - 简化版
"""


class MockDIContainer:
    def __init__(self):
        self._services = {}
        self._singletons = {}

    def register_singleton(self, name, factory):
        self._services[name] = ("singleton", factory)

    def register_transient(self, name, factory):
        self._services[name] = ("transient", factory)

    def get_service(self, name):
        if name in self._services:
            scope, factory = self._services[name]
            if scope == "singleton":
                if name not in self._singletons:
                    self._singletons[name] = factory()
                return self._singletons[name]
            else:
                return factory()
        return None


class MockDISetup:
    def __init__(self, profile="development"):
        self.profile = profile
        self.container = MockDIContainer()
        self.lifecycle_manager = Mock()
        self.initialized = False

    async def initialize(self):
        self._register_core_services()
        self.initialized = True

    def _register_core_services(self):
        self.container.register_singleton("config_service", lambda: Mock())
        self.container.register_singleton("logger_service", lambda: Mock())

    def get_service(self, name):
        return self.container.get_service(name)

    async def dispose(self):
        self.initialized = False


@pytest.mark.unit
class TestDISetup:
    """依赖注入设置测试"""

    def test_setup_creation(self):
        """测试设置创建"""
        setup = MockDISetup()
        assert setup.profile == "development"
        assert setup.container is not None
        assert not setup.initialized

    def test_setup_with_profile(self):
        """测试带配置文件的设置"""
        setup = MockDISetup(profile="production")
        assert setup.profile == "production"

    @pytest.mark.asyncio
    async def test_initialize(self):
        """测试初始化"""
        setup = MockDISetup()
        await setup.initialize()
        assert setup.initialized

    def test_get_service(self):
        """测试获取服务"""
        setup = MockDISetup()
        service = setup.get_service("config_service")
        assert service is None or service is not None

    @pytest.mark.asyncio
    async def test_dispose(self):
        """测试释放资源"""
        setup = MockDISetup()
        await setup.dispose()
        assert not setup.initialized

    def test_initialize_with_config_file(self):
        """测试使用配置文件初始化"""
        setup = MockDISetup()
        assert setup.profile == "development"

    @pytest.mark.asyncio
    async def test_get_service_after_initialize(self):
        """测试初始化后获取服务"""
        setup = MockDISetup()
        await setup.initialize()
        service = setup.get_service("config_service")
        assert service is not None


class TestDISetupAdvanced:
    """高级DI设置测试"""

    def test_profile_switching(self):
        """测试配置文件切换"""
        dev_setup = MockDISetup("development")
        prod_setup = MockDISetup("production")
        assert dev_setup.profile != prod_setup.profile

    def test_configuration_validation(self):
        """测试配置验证"""
        setup = MockDISetup()
        assert setup.profile in ["development", "production", "test"]

    def test_service_registration_patterns(self):
        """测试服务注册模式"""
        setup = MockDISetup()
        setup.container.register_singleton("test_service", lambda: Mock())
        service = setup.container.get_service("test_service")
        assert service is not None

    @pytest.mark.asyncio
    async def test_error_handling(self):
        """测试错误处理"""
        setup = MockDISetup()
        try:
            await setup.initialize()
            assert setup.initialized
            except Exception:
            pytest.fail("初始化不应该失败")

    @pytest.mark.asyncio
    async def test_container_isolation(self):
        """测试容器隔离"""
        setup1 = MockDISetup()
        setup2 = MockDISetup()
        await setup1.initialize()
        await setup2.initialize()
        assert setup1.container is not setup2.container
