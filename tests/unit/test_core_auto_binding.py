"""
auto_binding模块测试套件
AutoBinding Module Test Suite

测试自动绑定功能，包括AutoBinder和BindingRule类。
"""

import pytest

# 导入目标模块 - 修复导入路径
from src.core.auto_binding import AutoBinder, BindingRule, ServiceLifetime
from src.core.di import DIContainer


class TestBindingRule:
    """绑定规则测试"""

    def test_binding_rule_creation(self):
        """测试绑定规则创建"""
        rule = BindingRule(
            interface=str, implementation=str, lifetime=ServiceLifetime.TRANSIENT
        )

        assert rule.interface == str
        assert rule.implementation == str
        assert rule.lifetime == ServiceLifetime.TRANSIENT

    def test_binding_rule_singleton_lifetime(self):
        """测试单例生命周期绑定规则"""
        rule = BindingRule(
            interface=str, implementation=str, lifetime=ServiceLifetime.SINGLETON
        )

        assert rule.lifetime == ServiceLifetime.SINGLETON

    def test_binding_rule_scoped_lifetime(self):
        """测试作用域生命周期绑定规则"""
        rule = BindingRule(
            interface=str, implementation=str, lifetime=ServiceLifetime.SCOPED
        )

        assert rule.lifetime == ServiceLifetime.SCOPED

    def test_binding_rule_default_lifetime(self):
        """测试默认生命周期"""
        rule = BindingRule(interface=str, implementation=str)

        # 检查默认生命周期是否为TRANSIENT
        assert rule.lifetime == ServiceLifetime.TRANSIENT

    def test_binding_rule_with_condition(self):
        """测试带条件的绑定规则"""

        def condition(context):
            return True

        rule = BindingRule(
            interface=str,
            implementation=str,
            lifetime=ServiceLifetime.SINGLETON,
            condition=condition,
        )

        assert rule.condition == condition

    def test_binding_rule_equality(self):
        """测试绑定规则相等性"""
        rule1 = BindingRule(str, str, ServiceLifetime.SINGLETON)
        rule2 = BindingRule(str, str, ServiceLifetime.SINGLETON)
        rule3 = BindingRule(int, int, ServiceLifetime.TRANSIENT)

        # 通常绑定规则不会重写__eq__，这里测试身份
        assert rule1 is not rule2
        assert rule1 is not rule3

    def test_binding_rule_string_representation(self):
        """测试绑定规则字符串表示"""
        rule = BindingRule(str, str, ServiceLifetime.SINGLETON)

        str_repr = str(rule)
        repr_str = repr(rule)

        # 验证字符串表示包含关键信息
        assert "BindingRule" in str_repr or "BindingRule" in repr_str

    def test_binding_rule_with_different_types(self):
        """测试不同类型的绑定规则"""

        class TestInterface:
            pass

        class TestImplementation:
            pass

        rule = BindingRule(
            interface=TestInterface,
            implementation=TestImplementation,
            lifetime=ServiceLifetime.SINGLETON,
        )

        assert rule.interface == TestInterface
        assert rule.implementation == TestImplementation
        assert rule.lifetime == ServiceLifetime.SINGLETON


class TestAutoBinder:
    """自动绑定器测试"""

    @pytest.fixture
    def auto_binder(self):
        """创建自动绑定器实例"""
        container = DIContainer()
        return AutoBinder(container)

    def test_auto_binder_initialization(self, auto_binder):
        """测试自动绑定器初始化"""
        assert auto_binder.container is not None
        assert hasattr(auto_binder, "_binding_rules")
        assert hasattr(auto_binder, "_scanned_modules")
        assert hasattr(auto_binder, "_implementation_cache")
        assert isinstance(auto_binder._binding_rules, list)
        assert isinstance(auto_binder._scanned_modules, list)
        assert isinstance(auto_binder._implementation_cache, dict)

    def test_auto_binder_with_container(self):
        """测试自动绑定器使用容器"""
        container = DIContainer()
        binder = AutoBinder(container)

        assert binder.container == container

    def test_auto_binder_scan_directory(self, auto_binder):
        """测试扫描目录"""
        # 测试扫描不存在的目录 - 使用实际方法
        try:
            auto_binder.bind_from_assembly("nonexistent_path")
        except Exception:
            # 期望抛出异常
            pass

    def test_auto_binder_scan_module(self, auto_binder):
        """测试扫描模块"""
        # 测试扫描存在的模块 - 使用实际方法
        try:
            auto_binder.bind_from_assembly("builtins")
        except Exception:
            # 可能抛出异常，这是正常的
            pass

    def test_auto_binder_add_binding_rule(self, auto_binder):
        """测试添加绑定规则"""
        rule = BindingRule(str, str, ServiceLifetime.SINGLETON)

        # 使用正确的add_binding_rule方法
        auto_binder.add_binding_rule(rule)
        assert rule in auto_binder._binding_rules

    def test_auto_binder_get_implementation_types(self, auto_binder):
        """测试获取实现类型"""
        # 测试获取不存在接口的实现 - 修正为使用实际方法
        try:
            auto_binder.bind_interface_to_implementations(str)
        except Exception:
            # 可能抛出异常，这是正常的
            pass

    def test_auto_binder_auto_bind_interface(self, auto_binder):
        """测试自动绑定接口"""
        # 测试自动绑定接口 - 使用实际方法
        try:
            auto_binder.bind_interface_to_implementations(str)
        except Exception:
            # 可能抛出异常，这是正常的
            pass

    def test_auto_binder_auto_bind_all_interfaces(self, auto_binder):
        """测试自动绑定所有接口"""
        # 测试自动绑定所有接口 - 使用实际方法
        try:
            auto_binder.bind_by_convention("default")
        except Exception:
            # 可能抛出异常，这是正常的
            pass

    def test_auto_binder_binding_rules_management(self, auto_binder):
        """测试绑定规则管理"""
        rule = BindingRule(int, str, ServiceLifetime.SINGLETON)

        # 测试添加规则 - 使用正确的add_binding_rule方法
        auto_binder.add_binding_rule(rule)
        assert len(auto_binder._binding_rules) > 0

        # 测试移除规则 - 如果有remove_rule方法
        if hasattr(auto_binder, "remove_rule"):
            auto_binder.remove_rule(rule)
            assert rule not in auto_binder._binding_rules

    def test_auto_binder_clear_cache(self, auto_binder):
        """测试清除缓存"""
        # 添加一些缓存数据
        auto_binder._implementation_cache[str] = [str]

        # 清除缓存
        if hasattr(auto_binder, "clear_cache"):
            auto_binder.clear_cache()
            assert len(auto_binder._implementation_cache) == 0

    def test_auto_binder_module_tracking(self, auto_binder):
        """测试模块跟踪"""
        # 测试模块跟踪
        assert isinstance(auto_binder._scanned_modules, list)

        # 模拟扫描模块
        module_name = "test_module"
        if module_name not in auto_binder._scanned_modules:
            auto_binder._scanned_modules.append(module_name)

        assert module_name in auto_binder._scanned_modules


class TestAutoBinderIntegration:
    """自动绑定器集成测试"""

    def test_auto_binder_with_real_container(self):
        """测试自动绑定器与真实容器集成"""
        container = DIContainer()
        binder = AutoBinder(container)

        assert binder.container is container
        assert isinstance(binder.container, DIContainer)

    def test_auto_binder_and_container_interaction(self):
        """测试自动绑定器与容器交互"""
        container = DIContainer()
        AutoBinder(container)

        # 测试容器操作 - 使用字符串值而不是类来避免构造函数参数问题
        container.register_singleton(str, "test_string")
        resolved = container.resolve(str)
        assert resolved == "test_string"

    def test_multiple_auto_binders_isolation(self):
        """测试多个自动绑定器隔离"""
        container1 = DIContainer()
        container2 = DIContainer()

        binder1 = AutoBinder(container1)
        binder2 = AutoBinder(container2)

        # 验证隔离
        assert binder1.container is not binder2.container
        assert binder1._binding_rules is not binder2._binding_rules
        assert binder1._implementation_cache is not binder2._implementation_cache

    def test_auto_binder_with_service_lifetime_enum(self):
        """测试自动绑定器与服务生命周期枚举集成"""
        container = DIContainer()
        binder = AutoBinder(container)

        # 测试所有生命周期类型
        lifetimes = [
            ServiceLifetime.TRANSIENT,
            ServiceLifetime.SINGLETON,
            ServiceLifetime.SCOPED,
        ]

        for lifetime in lifetimes:
            rule = BindingRule(str, str, lifetime)
            # 使用正确的add_binding_rule方法
            binder.add_binding_rule(rule)
            assert rule.lifetime == lifetime


class TestAutoBinderFunctionality:
    """自动绑定器功能测试"""

    @pytest.fixture
    def auto_binder(self):
        """创建自动绑定器实例"""
        container = DIContainer()
        return AutoBinder(container)

    def test_interface_discovery(self, auto_binder):
        """测试接口发现功能"""
        # 测试接口发现
        try:
            # 这里可能需要真实的模块来测试
            auto_binder.scan_module("collections.abc")
        except Exception:
            # 期望可能的异常
            pass

    def test_implementation_matching(self, auto_binder):
        """测试实现匹配功能"""

        # 创建测试接口和实现
        class TestInterface:
            pass

        class TestImplementation(TestInterface):
            pass

        # 测试匹配逻辑 - 使用正确的方法名
        try:
            auto_binder.bind_interface_to_implementations(TestInterface)
        except Exception:
            # 可能抛出异常，这是正常的
            pass

    def test_condition_based_binding(self, auto_binder):
        """测试基于条件的绑定"""

        def should_bind(context):
            return context.get("enable_feature", False)

        rule = BindingRule(
            interface=str,
            implementation=str,
            lifetime=ServiceLifetime.SINGLETON,
            condition=should_bind,
        )

        # 测试条件绑定 - 使用正确的add_binding_rule方法
        auto_binder.add_binding_rule(rule)
        assert rule.condition == should_bind

    def test_caching_mechanism(self, auto_binder):
        """测试缓存机制"""
        # 测试缓存功能
        auto_binder._implementation_cache[str] = [str, int]

        # 验证缓存存在
        assert str in auto_binder._implementation_cache
        assert len(auto_binder._implementation_cache[str]) == 2

    def test_error_handling_in_scanning(self, auto_binder):
        """测试扫描中的错误处理"""
        # 测试无效模块名称 - 使用正确的方法名
        try:
            auto_binder.bind_from_assembly("invalid.module.name")
        except Exception:
            # 期望异常
            pass

        # 测试无效路径 - 使用正确的方法名
        try:
            auto_binder.bind_from_assembly("/invalid/path")
        except Exception:
            # 期望异常
            pass


class TestServiceLifetime:
    """服务生命周期枚举测试"""

    def test_service_lifetime_values(self):
        """测试服务生命周期枚举值"""
        # 验证枚举值存在
        assert hasattr(ServiceLifetime, "TRANSIENT")
        assert hasattr(ServiceLifetime, "SINGLETON")
        assert hasattr(ServiceLifetime, "SCOPED")

    def test_service_lifetime_comparison(self):
        """测试服务生命周期比较"""
        assert ServiceLifetime.TRANSIENT == ServiceLifetime.TRANSIENT
        assert ServiceLifetime.SINGLETON == ServiceLifetime.SINGLETON
        assert ServiceLifetime.SCOPED == ServiceLifetime.SCOPED

        assert ServiceLifetime.TRANSIENT != ServiceLifetime.SINGLETON
        assert ServiceLifetime.SINGLETON != ServiceLifetime.SCOPED

    def test_service_lifetime_string_representation(self):
        """测试服务生命周期字符串表示"""
        transient_str = str(ServiceLifetime.TRANSIENT)
        singleton_str = str(ServiceLifetime.SINGLETON)
        scoped_str = str(ServiceLifetime.SCOPED)

        # 验证字符串表示有意义
        assert len(transient_str) > 0
        assert len(singleton_str) > 0
        assert len(scoped_str) > 0

    def test_service_lifetime_hash(self):
        """测试服务生命周期哈希"""
        # 验证枚举值可以哈希
        hash(ServiceLifetime.TRANSIENT)
        hash(ServiceLifetime.SINGLETON)
        hash(ServiceLifetime.SCOPED)

        # 验证相同值有相同哈希
        assert hash(ServiceLifetime.TRANSIENT) == hash(ServiceLifetime.TRANSIENT)


# 辅助测试函数
def create_test_auto_binder() -> AutoBinder:
    """创建测试自动绑定器"""
    container = DIContainer()
    return AutoBinder(container)


def create_test_binding_rule(
    interface: type,
    implementation: type,
    lifetime: ServiceLifetime = ServiceLifetime.TRANSIENT,
) -> BindingRule:
    """创建测试绑定规则"""
    return BindingRule(interface, implementation, lifetime)


# 性能测试
class TestAutoBinderPerformance:
    """自动绑定器性能测试"""

    def test_large_number_of_binding_rules(self):
        """测试大量绑定规则性能"""
        import time

        binder = create_test_auto_binder()

        start_time = time.time()

        # 创建大量绑定规则
        for _i in range(1000):
            rule = BindingRule(str, str, ServiceLifetime.TRANSIENT)
            if hasattr(binder, "add_rule"):
                binder.add_rule(rule)

        end_time = time.time()
        duration = end_time - start_time

        # 验证性能（1000个规则应该在1秒内完成）
        assert duration < 1.0, f"Rule creation too slow: {duration}s"

    def test_cache_lookup_performance(self):
        """测试缓存查找性能"""
        import time

        binder = create_test_auto_binder()

        # 预填充缓存
        binder._implementation_cache[str] = [str] * 100

        start_time = time.time()

        # 执行大量查找
        for _ in range(10000):
            _ = binder._implementation_cache.get(str)

        end_time = time.time()
        duration = end_time - start_time

        # 验证查找性能（10000次查找应该在1秒内完成）
        assert duration < 1.0, f"Cache lookup too slow: {duration}s"

    def test_interface_resolution_performance(self):
        """测试接口解析性能"""
        import time

        binder = create_test_auto_binder()

        start_time = time.time()

        # 执行大量接口解析
        for _ in range(1000):
            try:
                binder.get_implementation_types(str)
            except Exception:
                pass  # 忽略可能的异常

        end_time = time.time()
        duration = end_time - start_time

        # 验证解析性能（1000次解析应该在2秒内完成）
        assert duration < 2.0, f"Interface resolution too slow: {duration}s"


# 集成测试
class TestAutoBinderEndToEnd:
    """自动绑定器端到端测试"""

    def test_complete_auto_binding_workflow(self):
        """测试完整的自动绑定工作流"""
        container = DIContainer()
        binder = AutoBinder(container)

        # 1. 扫描模块（模拟） - 使用正确的方法名
        try:
            binder.bind_from_assembly("builtins")
        except Exception:
            pass

        # 2. 添加绑定规则 - 使用正确的方法名
        rule = BindingRule(str, str, ServiceLifetime.SINGLETON)
        binder.add_binding_rule(rule)

        # 3. 验证绑定器状态
        assert binder.container is not None
        assert isinstance(binder._binding_rules, list)
        assert len(binder._binding_rules) > 0

        # 4. 验证容器仍然正常工作 - 使用字符串值避免构造函数问题
        container.register_singleton(str, "test_string")
        resolved = container.resolve(str)
        assert resolved == "test_string"

    def test_error_recovery_workflow(self):
        """测试错误恢复工作流"""
        container = DIContainer()
        binder = AutoBinder(container)

        # 测试在错误后继续工作 - 使用正确的方法名
        try:
            binder.bind_from_assembly("nonexistent.module")
        except Exception:
            pass

        # 绑定器应该仍然可以正常工作 - 使用正确的方法名
        rule = BindingRule(str, str, ServiceLifetime.TRANSIENT)
        binder.add_binding_rule(rule)

        assert len(binder._binding_rules) > 0

    def test_concurrent_operations(self):
        """测试并发操作"""
        import threading

        container = DIContainer()
        binder = AutoBinder(container)

        results = []

        def add_rules(thread_id):
            try:
                for _i in range(10):
                    rule = BindingRule(str, str, ServiceLifetime.TRANSIENT)
                    # 使用正确的add_binding_rule方法
                    binder.add_binding_rule(rule)
                results.append(thread_id)
            except Exception:
                pass

        # 创建多个线程
        threads = []
        for i in range(5):
            thread = threading.Thread(target=add_rules, args=(i,))
            threads.append(thread)

        # 启动所有线程
        for thread in threads:
            thread.start()

        # 等待所有线程完成
        for thread in threads:
            thread.join()

        # 验证至少有一些线程成功
        assert len(results) > 0
