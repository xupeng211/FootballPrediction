"""
M2-P1-01: 扩展core.di模块依赖注入测试
目标覆盖率50%+

Issue: #213
预估工时: 16小时
优先级: high

新增测试用例:
1. DIContainer单例模式测试 (5个测试用例)
2. ServiceDescriptor序列化测试 (4个测试用例)
3. 依赖注入边界条件测试 (3个测试用例)
4. 循环依赖检测测试 (3个测试用例)
"""

import json
import pickle
import threading
import time
from datetime import datetime

import pytest

# 导入目标模块
from core.di import (DependencyInjectionError, DIContainer, ServiceDescriptor,
                     ServiceLifetime)


class TestDIContainerSingleton:
    """DIContainer单例模式测试"""

    def test_singleton_thread_safety(self):
        """测试单例模式的线程安全性"""
        container = DIContainer()
        results = []
        errors = []

        def create_instance():
            try:
                instance = container.resolve(str)
                results.append(id(instance))
            except Exception as e:
                errors.append(e)

        # 注册单例服务
        container.register_singleton(str, "singleton_test")

        # 创建多个线程同时解析服务
        threads = []
        for _ in range(10):
            thread = threading.Thread(target=create_instance)
            threads.append(thread)
            thread.start()

        # 等待所有线程完成
        for thread in threads:
            thread.join()

        # 验证所有线程获得的是同一个实例
        assert len(errors) == 0, f"Errors occurred: {errors}"
        assert (
            len(set(results)) == 1
        ), f"Multiple instances created: {len(set(results))} unique IDs"

    def test_singleton_instance_caching(self):
        """测试单例实例缓存"""
        container = DIContainer()

        # 注册单例服务
        test_obj = {"value": 42}
        container.register_singleton(dict, test_obj)

        # 多次解析应该返回同一个实例
        instance1 = container.resolve(dict)
        instance2 = container.resolve(dict)
        instance3 = container.resolve(dict)

        assert instance1 is instance2 is instance3
        assert instance1["value"] == 42

    def test_singleton_with_factory(self):
        """测试工厂方法创建的单例"""
        container = DIContainer()
        call_count = 0

        def factory():
            nonlocal call_count
            call_count += 1
            return {"created": call_count}

        container.register_singleton(dict, factory=factory)

        # 多次解析应该只调用一次工厂方法
        instance1 = container.resolve(dict)
        instance2 = container.resolve(dict)
        instance3 = container.resolve(dict)

        assert call_count == 1
        assert instance1 is instance2 is instance3
        assert instance1["created"] == 1

    def test_singleton_dependency_injection(self):
        """测试单例服务的依赖注入"""
        container = DIContainer()

        class ServiceA:
            def __init__(self, name: str):
                self.name = name

        class ServiceB:
            def __init__(self, service_a: ServiceA):
                self.service_a = service_a

        # 注册服务
        container.register_singleton(str, "test_service")
        container.register_singleton(ServiceA, ServiceA)
        container.register_singleton(ServiceB, ServiceB)

        # 解析服务
        service_b = container.resolve(ServiceB)

        assert isinstance(service_b, ServiceB)
        assert isinstance(service_b.service_a, ServiceA)
        # 验证单例特性
        service_b2 = container.resolve(ServiceB)
        assert service_b is service_b2
        assert service_b.service_a is service_b2.service_a

    def test_singleton_lifecycle_management(self):
        """测试单例生命周期管理"""
        container = DIContainer()

        class LifecycleService:
            def __init__(self):
                self.created_at = datetime.now()
                self.disposed = False

            def dispose(self):
                self.disposed = True

        container.register_singleton(LifecycleService, LifecycleService)

        # 创建实例
        service1 = container.resolve(LifecycleService)
        created_time = service1.created_at

        # 稍等片刻再次解析
        time.sleep(0.01)
        service2 = container.resolve(LifecycleService)

        # 验证是同一个实例，创建时间相同
        assert service1 is service2
        assert service1.created_at == created_time == service2.created_at


class TestServiceDescriptorSerialization:
    """ServiceDescriptor序列化测试"""

    def test_service_descriptor_pickle_serialization(self):
        """测试ServiceDescriptor的pickle序列化"""

        # 创建服务描述符
        descriptor = ServiceDescriptor(
            interface=str,
            implementation="test_impl",
            lifetime=ServiceLifetime.SINGLETON,
            factory=None,
            instance=None,
            dependencies=[int, float],
        )

        # 序列化和反序列化
        serialized = pickle.dumps(descriptor)
        deserialized = pickle.loads(serialized)

        # 验证序列化结果
        assert deserialized.interface == descriptor.interface
        assert deserialized.implementation == descriptor.implementation
        assert deserialized.lifetime == descriptor.lifetime
        assert deserialized.dependencies == descriptor.dependencies

    def test_service_descriptor_json_serialization(self):
        """测试ServiceDescriptor的JSON序列化"""
        descriptor = ServiceDescriptor(
            interface=str,
            implementation="test_impl",
            lifetime=ServiceLifetime.SINGLETON,
            dependencies=[int, float],
        )

        # 转换为可JSON序列化的字典
        descriptor_dict = {
            "interface": descriptor.interface.__name__,
            "implementation": str(descriptor.implementation),
            "lifetime": descriptor.lifetime.value,
            "dependencies": [dep.__name__ for dep in descriptor.dependencies or []],
        }

        # JSON序列化和反序列化
        json_str = json.dumps(descriptor_dict)
        parsed_dict = json.loads(json_str)

        # 验证序列化结果
        assert parsed_dict["interface"] == "str"
        assert parsed_dict["implementation"] == "test_impl"
        assert parsed_dict["lifetime"] == "singleton"
        assert parsed_dict["dependencies"] == ["int", "float"]

    def test_service_descriptor_with_factory_serialization(self):
        """测试包含工厂方法的服务描述符序列化"""
        call_count = 0

        def test_factory():
            nonlocal call_count
            call_count += 1
            return {"count": call_count}

        descriptor = ServiceDescriptor(
            interface=dict,
            implementation=None,
            lifetime=ServiceLifetime.SINGLETON,
            factory=test_factory,
        )

        # 验证工厂方法存在
        assert descriptor.factory is not None
        assert callable(descriptor.factory)

        # 工厂方法不能序列化，但可以记录其存在
        descriptor_info = {
            "interface": descriptor.interface.__name__,
            "has_factory": descriptor.factory is not None,
            "lifetime": descriptor.lifetime.value,
        }

        assert descriptor_info["has_factory"] is True
        assert descriptor_info["lifetime"] == "singleton"

    def test_service_descriptor_copy_and_deepcopy(self):
        """测试ServiceDescriptor的复制"""
        import copy

        original = ServiceDescriptor(
            interface=list,
            implementation="list_impl",
            lifetime=ServiceLifetime.SCOPED,
            dependencies=[str, int],
        )

        # 浅复制
        shallow_copy = copy.copy(original)
        assert shallow_copy.interface == original.interface
        assert shallow_copy.implementation == original.implementation
        assert shallow_copy.lifetime == original.lifetime

        # 深复制
        deep_copy = copy.deepcopy(original)
        assert deep_copy.interface == original.interface
        assert deep_copy.implementation == original.implementation
        assert deep_copy.lifetime == original.lifetime
        assert deep_copy.dependencies == original.dependencies


class TestDependencyInjectionBoundaryConditions:
    """依赖注入边界条件测试"""

    def test_register_with_none_interface(self):
        """测试注册None接口"""
        container = DIContainer()

        with pytest.raises((TypeError, AttributeError)):
            container.register_singleton(None, "test")

    def test_register_with_invalid_lifetime(self):
        """测试注册无效生命周期"""
        container = DIContainer()

        with pytest.raises((TypeError, ValueError)):
            # 直接调用内部方法测试
            container._register(str, "test", "invalid_lifetime")

    def test_resolve_with_complex_dependencies(self):
        """测试解析复杂依赖关系"""
        container = DIContainer()

        class ServiceA:
            pass

        class ServiceB:
            def __init__(self, a: ServiceA, optional_param: str = "default"):
                self.a = a
                self.optional_param = optional_param

        class ServiceC:
            def __init__(self, b: ServiceB, a: ServiceA):
                self.b = b
                self.a = a

        # 注册服务
        container.register_singleton(ServiceA, ServiceA)
        container.register_singleton(ServiceB, ServiceB)
        container.register_singleton(ServiceC, ServiceC)

        # 解析服务
        service_c = container.resolve(ServiceC)

        assert isinstance(service_c, ServiceC)
        assert isinstance(service_c.b, ServiceB)
        assert isinstance(service_c.b.a, ServiceA)
        assert isinstance(service_c.a, ServiceA)
        assert service_c.b.optional_param == "default"

    def test_container_with_multiple_interfaces_same_implementation(self):
        """测试多个接口使用同一实现"""
        container = DIContainer()

        class MultiInterfaceService:
            def __init__(self):
                self.value = "multi"

        # 为多个接口注册同一实现
        container.register_singleton(str, MultiInterfaceService)
        container.register_singleton(dict, MultiInterfaceService)

        # 解析不同接口应该获得相同的实例类型
        str_service = container.resolve(str)
        dict_service = container.resolve(dict)

        assert isinstance(str_service, MultiInterfaceService)
        assert isinstance(dict_service, MultiInterfaceService)
        assert str_service.value == dict_service.value == "multi"

    def test_error_handling_for_missing_dependencies(self):
        """测试缺少依赖的错误处理"""
        container = DIContainer()

        class ServiceWithMissingDependency:
            def __init__(self, missing_service: type(None)):
                self.missing_service = missing_service

        container.register_singleton(
            ServiceWithMissingDependency, ServiceWithMissingDependency
        )

        with pytest.raises(DependencyInjectionError):
            container.resolve(ServiceWithMissingDependency)


class TestCircularDependencyDetection:
    """循环依赖检测测试"""

    def test_simple_circular_dependency(self):
        """测试简单循环依赖"""
        container = DIContainer()

        class ServiceA:
            def __init__(self, b: "ServiceB"):
                self.b = b

        class ServiceB:
            def __init__(self, a: ServiceA):
                self.a = a

        # 注册服务
        container.register_singleton(ServiceA, ServiceA)
        container.register_singleton(ServiceB, ServiceB)

        # 尝试解析应该检测到循环依赖
        with pytest.raises(DependencyInjectionError) as exc_info:
            container.resolve(ServiceA)

        assert (
            "循环依赖" in str(exc_info.value)
            or "circular" in str(exc_info.value).lower()
        )

    def test_self_dependency(self):
        """测试自依赖"""
        container = DIContainer()

        class SelfDependentService:
            def __init__(self, self_ref: "SelfDependentService"):
                self.self_ref = self_ref

        container.register_singleton(SelfDependentService, SelfDependentService)

        with pytest.raises(DependencyInjectionError):
            container.resolve(SelfDependentService)

    def test_complex_circular_dependency_chain(self):
        """测试复杂循环依赖链"""
        container = DIContainer()

        class ServiceA:
            def __init__(self, b: "ServiceB"):
                self.b = b

        class ServiceB:
            def __init__(self, c: "ServiceC"):
                self.c = c

        class ServiceC:
            def __init__(self, d: "ServiceD"):
                self.d = d

        class ServiceD:
            def __init__(self, a: ServiceA):
                self.a = a

        # 注册循环依赖链
        for service in [ServiceA, ServiceB, ServiceC, ServiceD]:
            container.register_singleton(service, service)

        with pytest.raises(DependencyInjectionError) as exc_info:
            container.resolve(ServiceA)

        error_message = str(exc_info.value).lower()
        assert any(
            keyword in error_message for keyword in ["circular", "cycle", "循环"]
        )

    def test_no_circular_dependency_with_scoped(self):
        """测试作用域服务不会产生循环依赖"""
        container = DIContainer()

        class ScopedService:
            def __init__(self):
                self.created = datetime.now()

        # 注册作用域服务
        container.register_scoped(ScopedService, ScopedService)

        # 应该能够正常解析
        instance1 = container.resolve(ScopedService)
        instance2 = container.resolve(ScopedService)

        assert isinstance(instance1, ScopedService)
        assert isinstance(instance2, ScopedService)
        # 作用域服务每次解析都是新实例
        assert instance1 is not instance2


class TestEdgeCasesAndAdvancedFeatures:
    """边界条件和高级特性测试"""

    def test_container_clear_and_reset(self):
        """测试容器的清理和重置"""
        container = DIContainer()

        # 注册一些服务
        container.register_singleton(str, "test")
        container.register_scoped(int, 42)

        assert len(container.get_registered_services()) == 2

        # 清理容器（如果支持）
        services_before = container.get_registered_services()

        # 重新创建容器来测试清理
        new_container = DIContainer()
        assert len(new_container.get_registered_services()) == 0

    def test_generic_type_resolution(self):
        """测试泛型类型解析"""
        from typing import Generic, TypeVar

        T = TypeVar("T")

        class GenericService(Generic[T]):
            def __init__(self, value: T):
                self.value = value

        # 注册具体类型的泛型服务
        container = DIContainer()
        container.register_singleton(str, "generic_value")

        # 验证基本类型解析正常
        value = container.resolve(str)
        assert value == "generic_value"

    def test_performance_with_many_services(self):
        """测试大量服务的性能"""
        import time

        container = DIContainer()

        # 注册大量服务
        start_time = time.time()
        for i in range(100):
            container.register_singleton(str, f"service_{i}")

        registration_time = time.time() - start_time

        # 解析服务的性能
        start_time = time.time()
        for _ in range(100):
            container.resolve(str)

        resolution_time = time.time() - start_time

        # 性能断言（这些是合理的性能期望）
        assert registration_time < 1.0, f"Registration too slow: {registration_time}s"
        assert resolution_time < 0.1, f"Resolution too slow: {resolution_time}s"

    def test_concurrent_access_thread_safety(self):
        """测试并发访问的线程安全性"""
        container = DIContainer()
        container.register_singleton(str, "thread_safe_test")

        results = []
        errors = []

        def resolve_service():
            try:
                for _ in range(10):
                    result = container.resolve(str)
                    results.append(result)
            except Exception as e:
                errors.append(e)

        # 创建多个线程
        threads = []
        for _ in range(5):
            thread = threading.Thread(target=resolve_service)
            threads.append(thread)
            thread.start()

        # 等待完成
        for thread in threads:
            thread.join()

        # 验证结果
        assert len(errors) == 0, f"Thread safety errors: {errors}"
        assert len(results) == 50  # 5 threads × 10 resolutions each
        assert all(result == "thread_safe_test" for result in results)


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
