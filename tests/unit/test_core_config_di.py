"""
增强的测试文件 - 目标覆盖率 50%
模块: core.config_di
当前覆盖率: 31%
"""

from unittest.mock import Mock

import pytest

# 导入目标模块
from src.core.di import (
    DIContainer,
    ServiceDescriptor,
    ServiceLifetime,
)


class TestDIContainer:
    """依赖注入容器测试"""

    def test_service_lifetime_enum(self):
        """测试服务生命周期枚举"""
        assert ServiceLifetime.SINGLETON is not None
        assert ServiceLifetime.SCOPED is not None
        assert ServiceLifetime.TRANSIENT is not None

    def test_service_descriptor_creation(self):
        """测试服务描述符创建"""
        descriptor = ServiceDescriptor(str, "test_service", ServiceLifetime.SINGLETON)
        assert descriptor.interface is str
        assert descriptor.implementation == "test_service"
        assert descriptor.lifetime == ServiceLifetime.SINGLETON

    def test_di_container_creation(self):
        """测试DI容器创建"""
        container = DIContainer()
        assert container is not None
        assert len(container.get_registered_services()) == 0

    def test_register_singleton(self):
        """测试注册单例服务"""
        container = DIContainer()
        container.register_singleton(str, "test_string")

        resolved = container.resolve(str)
        assert resolved == "test_string"

    def test_register_scoped(self):
        """测试注册作用域服务"""
        container = DIContainer()
        container.register_scoped(str, "scoped_string")

        resolved = container.resolve(str)
        assert resolved == "scoped_string"

    def test_register_transient(self):
        """测试注册瞬态服务"""
        container = DIContainer()
        container.register_transient(str, "transient_string")

        resolved = container.resolve(str)
        assert resolved == "transient_string"

    def test_container_with_class(self):
        """测试容器注册类"""
        container = DIContainer()
        container.register_singleton(Mock, Mock)

        resolved = container.resolve(Mock)
        assert isinstance(resolved, Mock)

    def test_resolve_unregistered_service(self):
        """测试解析未注册服务"""
        container = DIContainer()

        with pytest.raises((ValueError, KeyError)):
            container.resolve(int)
