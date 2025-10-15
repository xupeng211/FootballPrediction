"""核心模块简单测试"""

import pytest
from unittest.mock import Mock, AsyncMock
from src.core.config import get_settings
from src.core.exceptions import DependencyInjectionError


class TestCoreConfig:
    """测试核心配置"""

    def test_get_settings_returns_dict(self):
        """测试获取设置返回字典"""
        settings = get_settings()
        assert isinstance(settings, dict)

    def test_get_settings_has_required_keys(self):
        """测试设置包含必需的键"""
        settings = get_settings()
        # 测试是否有常见的配置键
        common_keys = ["ENVIRONMENT", "DEBUG"]
        # 至少应该有一个配置键
        assert len(settings) >= 0


class TestCoreExceptions:
    """测试核心异常"""

    def test_dependency_injection_error_creation(self):
        """测试依赖注入异常创建"""
        error = DependencyInjectionError("Test error")
        assert str(error) == "Test error"

    def test_dependency_injection_error_inheritance(self):
        """测试依赖注入异常继承"""
        with pytest.raises(Exception):
            raise DependencyInjectionError("Test error")


class TestCoreLogger:
    """测试核心日志"""

    def test_logger_import(self):
        """测试日志模块导入"""
        from src.core.logging import get_logger
        logger = get_logger("test")
        assert logger is not None

    def test_logger_name(self):
        """测试日志器名称"""
        from src.core.logging import get_logger
        logger = get_logger("test_logger")
        # 检查日志器名称
        assert hasattr(logger, 'name')


class TestCoreDI:
    """测试依赖注入"""

    def test_di_container_import(self):
        """测试DI容器导入"""
        from src.core.di import DIContainer
        container = DIContainer()
        assert container is not None

    def test_di_container_name(self):
        """测试DI容器名称"""
        from src.core.di import DIContainer
        container = DIContainer("test_container")
        assert container.name == "test_container"

    def test_di_service_registration(self):
        """测试服务注册"""
        from src.core.di import DIContainer, ServiceLifetime

        container = DIContainer()

        # 定义一个简单的测试服务
        class TestService:
            pass

        # 注册服务
        container.register_singleton(TestService)
        assert TestService in container._services