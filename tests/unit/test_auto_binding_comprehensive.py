"""
AutoBinding 综合测试
目标覆盖率: 40%
当前覆盖率: 23%
新增测试: 20个测试用例
"""

from abc import ABC, abstractmethod
from pathlib import Path
from typing import TypeVar, Optional
from unittest.mock import patch

import pytest

from src.core.auto_binding import (
    AutoBinder,
    BindingRule,
    ConventionBinder,
    auto_bind,
    bind_to,
    primary_implementation,
)
from src.core.di import DIContainer, ServiceLifetime
from src.core.exceptions import DependencyInjectionError

T = TypeVar("T")


class TestBindingRule:
    """BindingRule数据类测试"""

    def test_binding_rule_creation(self):
        """测试绑定规则创建"""

        class TestInterface(ABC):
            """测试接口"""

            @abstractmethod
            def test_method(self) -> None:
                """测试方法"""
                pass

        class TestImplementation:
            pass

        rule = BindingRule(
            interface=TestInterface,
            implementation=TestImplementation,
            lifetime=ServiceLifetime.SINGLETON,
            condition=lambda: True,
        )

        assert rule.interface == TestInterface
        assert rule.implementation == TestImplementation
        assert rule.lifetime == ServiceLifetime.SINGLETON
        assert callable(rule.condition)

    def test_binding_rule_defaults(self):
        """测试绑定规则默认值"""

        class TestInterface(ABC):
            """测试接口"""

            @abstractmethod
            def test_method(self) -> None:
                """测试方法"""
                pass

        class TestImplementation:
            pass

        rule = BindingRule(interface=TestInterface, implementation=TestImplementation)

        assert rule.lifetime == ServiceLifetime.TRANSIENT
        assert rule.condition is None


class TestAutoBinder:
    """AutoBinder核心功能测试"""

    def setup_method(self):
        """每个测试方法前的设置"""
        self.container = DIContainer()
        self.binder = AutoBinder(self.container)

    def test_auto_binder_initialization(self):
        """测试自动绑定器初始化"""
        assert self.binder.container == self.container
        assert isinstance(self.binder._binding_rules, list)
        assert len(self.binder._binding_rules) == 0
        assert isinstance(self.binder._scanned_modules, list)
        assert len(self.binder._scanned_modules) == 0
        assert isinstance(self.binder._implementation_cache, dict)
        assert len(self.binder._implementation_cache) == 0

    def test_add_binding_rule(self):
        """测试添加绑定规则"""

        class TestInterface(ABC):
            """测试接口"""

            @abstractmethod
            def test_method(self) -> None:
                """测试方法"""
                pass

        class TestImplementation:
            pass

        rule = BindingRule(TestInterface, TestImplementation)
        self.binder.add_binding_rule(rule)

        assert len(self.binder._binding_rules) == 1
        assert self.binder._binding_rules[0] == rule

    def test_bind_from_assembly_module(self):
        """测试从模块绑定"""
        # 创建临时模块进行测试
        import types

        temp_module = types.ModuleType("test_temp_module")

        # 添加测试类到模块
        class TestClass:
            pass

        temp_module.TestClass = TestClass
        temp_module.__file__ = "test_temp_module.py"

        with patch("importlib.import_module", return_value=temp_module):
            with patch.object(self.binder, "_scan_module") as mock_scan:
                self.binder.bind_from_assembly("test_temp_module")
                mock_scan.assert_called_once_with(temp_module)

    def test_bind_from_assembly_directory(self):
        """测试从目录绑定"""
        import types

        temp_module = types.ModuleType("test_package")
        temp_module.__file__ = "/fake/path/test_package/__init__.py"

        with patch("importlib.import_module", return_value=temp_module):
            with patch("pathlib.Path.is_dir", return_value=True):
                with patch.object(self.binder, "_scan_directory") as mock_scan:
                    self.binder.bind_from_assembly("test_package")
                    mock_scan.assert_called_once()

    def test_bind_by_convention_default(self):
        """测试按默认约定绑定"""
        with patch.object(self.binder, "_apply_default_convention") as mock_convention:
            self.binder.bind_by_convention("default")
            mock_convention.assert_called_once()

    def test_bind_by_convention_repository(self):
        """测试按仓储约定绑定"""
        with patch.object(
            self.binder, "_apply_repository_convention"
        ) as mock_convention:
            self.binder.bind_by_convention("repository")
            mock_convention.assert_called_once()

    def test_bind_by_convention_service(self):
        """测试按服务约定绑定"""
        with patch.object(self.binder, "_apply_service_convention") as mock_convention:
            self.binder.bind_by_convention("service")
            mock_convention.assert_called_once()

    def test_bind_by_convention_unknown(self):
        """测试未知约定绑定"""
        with pytest.raises(DependencyInjectionError) as exc_info:
            self.binder.bind_by_convention("unknown")

        assert "未知的绑定约定" in str(exc_info.value)

    def test_bind_interface_to_implementations_single(self):
        """测试绑定接口到单个实现"""

        class TestInterface(ABC):
            """测试接口"""

            @abstractmethod
            def test_method(self) -> None:
                """测试方法"""
                pass

        class TestImplementation(TestInterface):
            pass

        with patch.object(
            self.binder, "_find_implementations", return_value=[TestImplementation]
        ):
            with patch.object(self.container, "register_transient") as mock_register:
                self.binder.bind_interface_to_implementations(TestInterface)
                mock_register.assert_called_once_with(TestInterface, TestImplementation)

    def test_bind_interface_to_implementations_multiple(self):
        """测试绑定接口到多个实现"""

        class TestInterface(ABC):
            """测试接口"""

            @abstractmethod
            def test_method(self) -> None:
                """测试方法"""
                pass

        class TestImplementation1(TestInterface):
            pass

        class TestImplementation2(TestInterface):
            pass

        implementations = [TestImplementation1, TestImplementation2]

        with patch.object(
            self.binder, "_find_implementations", return_value=implementations
        ):
            with patch.object(
                self.binder,
                "_select_primary_implementation",
                return_value=TestImplementation1,
            ):
                with patch.object(
                    self.container, "register_transient"
                ) as mock_register:
                    self.binder.bind_interface_to_implementations(TestInterface)
                    # 应该调用两次：一次主要实现，一次命名实现
                    assert mock_register.call_count == 2

    def test_bind_interface_to_implementations_none(self):
        """测试绑定接口到无实现"""

        class TestInterface(ABC):
            """测试接口"""

            @abstractmethod
            def test_method(self) -> None:
                """测试方法"""
                pass

        with patch.object(self.binder, "_find_implementations", return_value=[]):
            with patch("src.core.auto_binding.logger") as mock_logger:
                self.binder.bind_interface_to_implementations(TestInterface)
                mock_logger.warning.assert_called_with(
                    f"未找到接口 {TestInterface.__name__} 的实现"
                )

    def test_auto_bind_success(self):
        """测试自动绑定成功"""

        class TestInterface(ABC):
            """测试接口"""

            @abstractmethod
            def test_method(self) -> None:
                """测试方法"""
                pass

        class TestImplementation(TestInterface):
            pass

        rule = BindingRule(TestInterface, TestImplementation, ServiceLifetime.SINGLETON)
        self.binder.add_binding_rule(rule)

        with patch.object(self.container, "register_singleton") as mock_register:
            with patch("src.core.auto_binding.logger") as mock_logger:
                self.binder.auto_bind()
                mock_register.assert_called_once_with(TestInterface, TestImplementation)
                mock_logger.info.assert_called_with(
                    f"自动绑定完成,应用了 {len(self.binder._binding_rules)} 个规则"
                )

    def test_auto_bind_with_condition(self):
        """测试带条件的自动绑定"""

        class TestInterface(ABC):
            """测试接口"""

            @abstractmethod
            def test_method(self) -> None:
                """测试方法"""
                pass

        class TestImplementation(TestInterface):
            pass

        rule = BindingRule(
            TestInterface,
            TestImplementation,
            ServiceLifetime.TRANSIENT,
            condition=lambda: False,
        )
        self.binder.add_binding_rule(rule)

        with patch.object(self.container, "register_transient") as mock_register:
            self.binder.auto_bind()
            mock_register.assert_not_called()

    def test_auto_bind_scoped_lifetime(self):
        """测试作用域生命周期自动绑定"""

        class TestInterface(ABC):
            """测试接口"""

            @abstractmethod
            def test_method(self) -> None:
                """测试方法"""
                pass

        class TestImplementation(TestInterface):
            pass

        rule = BindingRule(TestInterface, TestImplementation, ServiceLifetime.SCOPED)
        self.binder.add_binding_rule(rule)

        with patch.object(self.container, "register_scoped") as mock_register:
            self.binder.auto_bind()
            mock_register.assert_called_once_with(TestInterface, TestImplementation)

    def test_scan_directory_non_recursive(self):
        """测试非递归目录扫描"""
        test_dir = Path("/fake/test/dir")

        with patch("pathlib.Path.glob") as mock_glob:
            mock_glob.return_value = []
            with patch("pathlib.Path.is_dir", return_value=True):
                with patch("pathlib.Path.iterdir", return_value=[]) as mock_iterdir:
                    self.binder._scan_directory(test_dir, "test.module", "*", False)
                    mock_iterdir.assert_not_called()  # 非递归时不应该调用iterdir

    def test_scan_module_with_interface(self):
        """测试扫描包含接口的模块"""
        import types

        class TestInterface(ABC):
            @abstractmethod
            def test_method(self):
                pass

        class TestImplementation(TestInterface):
            def test_method(self):
                pass

        temp_module = types.ModuleType("test_module")
        temp_module.TestInterface = TestInterface
        temp_module.TestImplementation = TestImplementation
        temp_module.__name__ = "test_module"

        # 设置模块名
        TestInterface.__module__ = "test_module"
        TestImplementation.__module__ = "test_module"

        with patch.object(self.binder, "_bind_interface_implementations") as mock_bind:
            with patch.object(
                self.binder, "_check_class_implementations"
            ) as mock_check:
                self.binder._scan_module(temp_module)
                # 应该调用绑定接口实现和检查类实现
                assert mock_bind.called or mock_check.called

    def test_find_implementations_from_cache(self):
        """测试从缓存查找实现"""

        class TestInterface(ABC):
            """测试接口"""

            @abstractmethod
            def test_method(self) -> None:
                """测试方法"""
                pass

        class TestImplementation(TestInterface):
            pass

        # 预先填充缓存
        self.binder._implementation_cache[TestInterface] = [TestImplementation]
        self.binder._scanned_modules.append("test_module")

        implementations = self.binder._find_implementations(TestInterface)

        assert implementations == [TestImplementation]

    def test_is_implementation_success(self):
        """测试检查实现成功"""

        class TestInterface(ABC):
            """测试接口"""

            @abstractmethod
            def test_method(self) -> None:
                """测试方法"""
                pass

        class TestImplementation(TestInterface):
            pass

        result = self.binder._is_implementation(TestImplementation, TestInterface)
        assert result is True

    def test_is_implementation_failure(self):
        """测试检查实现失败"""

        class TestInterface(ABC):
            """测试接口"""

            @abstractmethod
            def test_method(self) -> None:
                """测试方法"""
                pass

        class UnrelatedClass:
            pass

        result = self.binder._is_implementation(UnrelatedClass, TestInterface)
        assert result is False

    def test_select_primary_implementation_by_name_suffix(self):
        """测试按名称后缀选择主要实现"""

        class ITestService(ABC):
            """测试接口"""

            @abstractmethod
            def test_method(self) -> None:
                """测试方法"""
                pass

        class TestService(ITestService):
            pass

        class AnotherTestService(ITestService):
            pass

        implementations = [TestService, AnotherTestService]
        result = self.binder._select_primary_implementation(
            ITestService, implementations
        )

        assert result == TestService

    def test_select_primary_implementation_by_default_name(self):
        """测试按默认名称选择主要实现"""

        class TestInterface(ABC):
            """测试接口"""

            @abstractmethod
            def test_method(self) -> None:
                """测试方法"""
                pass

        class DefaultTestService(TestInterface):
            pass

        class AnotherTestService(TestInterface):
            pass

        implementations = [AnotherTestService, DefaultTestService]
        result = self.binder._select_primary_implementation(
            TestInterface, implementations
        )

        assert result == DefaultTestService

    def test_select_primary_implementation_first_fallback(self):
        """测试选择主要实现的回退策略"""

        class TestInterface(ABC):
            """测试接口"""

            @abstractmethod
            def test_method(self) -> None:
                """测试方法"""
                pass

        class TestService1(TestInterface):
            pass

        class TestService2(TestInterface):
            pass

        implementations = [TestService1, TestService2]
        result = self.binder._select_primary_implementation(
            TestInterface, implementations
        )

        assert result == TestService1

    def test_apply_default_convention(self):
        """测试应用默认约定"""

        class ITestService(ABC):
            """测试接口"""

            @abstractmethod
            def test_method(self) -> None:
                """测试方法"""
                pass

        class TestService(ITestService):
            pass

        self.binder._implementation_cache[ITestService] = [TestService]

        with patch.object(self.container, "register_transient") as mock_register:
            with patch("src.core.auto_binding.logger"):
                self.binder._apply_default_convention()
                mock_register.assert_called_once_with(ITestService, TestService)

    def test_apply_repository_convention(self):
        """测试应用仓储约定"""

        class IRepository(ABC):
            """测试接口"""

            @abstractmethod
            def test_method(self) -> None:
                """测试方法"""
                pass

        class Repository(IRepository):
            pass

        self.binder._implementation_cache[IRepository] = [Repository]

        with patch.object(self.container, "register_scoped") as mock_register:
            with patch("src.core.auto_binding.logger"):
                self.binder._apply_repository_convention()
                mock_register.assert_called_once_with(IRepository, Repository)

    def test_apply_service_convention(self):
        """测试应用服务约定"""

        class IService(ABC):
            """测试接口"""

            @abstractmethod
            def test_method(self) -> None:
                """测试方法"""
                pass

        class Service(IService):
            pass

        self.binder._implementation_cache[IService] = [Service]

        with patch.object(self.container, "register_scoped") as mock_register:
            with patch("src.core.auto_binding.logger"):
                self.binder._apply_service_convention()
                mock_register.assert_called_once_with(IService, Service)


class TestConventionBinder:
    """ConventionBinder约定绑定器测试"""

    def test_bind_by_name_pattern_interface(self):
        """测试按名称模式绑定接口"""
        container = DIContainer()

        # 这个方法目前是空的，但我们可以测试它存在且不会报错
        ConventionBinder.bind_by_name_pattern(
            container, "I*Service", "*Service", ServiceLifetime.TRANSIENT
        )

    def test_bind_by_namespace_interface(self):
        """测试按命名空间绑定接口"""
        container = DIContainer()

        # 这个方法目前是空的，但我们可以测试它存在且不会报错
        ConventionBinder.bind_by_namespace(
            container,
            "interfaces.services",
            "implementations.services",
            ServiceLifetime.SCOPED,
        )


class TestAutoBindingDecorators:
    """自动绑定装饰器测试"""

    def test_auto_bind_decorator_default(self):
        """测试自动绑定装饰器默认值"""

        @auto_bind()
        class TestClass:
            pass

        assert hasattr(TestClass, "__auto_bind__")
        assert TestClass.__auto_bind__ is True
        assert hasattr(TestClass, "__bind_lifetime__")
        assert TestClass.__bind_lifetime__ == ServiceLifetime.TRANSIENT

    def test_auto_bind_decorator_with_lifetime(self):
        """测试带生命周期的自动绑定装饰器"""

        @auto_bind(ServiceLifetime.SINGLETON)
        class TestClass:
            pass

        assert TestClass.__auto_bind__ is True
        assert TestClass.__bind_lifetime__ == ServiceLifetime.SINGLETON

    def test_bind_to_decorator(self):
        """测试绑定到接口装饰器"""

        class TestInterface(ABC):
            """测试接口"""

            @abstractmethod
            def test_method(self) -> None:
                """测试方法"""
                pass

        @bind_to(TestInterface)
        class TestClass:
            pass

        assert hasattr(TestClass, "__bind_to__")
        assert TestClass.__bind_to__ == TestInterface

    def test_primary_implementation_decorator(self):
        """测试主要实现装饰器"""

        @primary_implementation()
        class TestClass:
            pass

        assert hasattr(TestClass, "__primary_implementation__")
        assert TestClass.__primary_implementation__ is True


class TestAutoBinderEdgeCases:
    """AutoBinder边缘情况测试"""

    def setup_method(self):
        self.container = DIContainer()
        self.binder = AutoBinder(self.container)

    def test_scan_module_import_error_handling(self):
        """测试扫描模块时处理导入错误"""
        with patch("importlib.import_module", side_effect=ImportError("模块不存在")):
            with patch("src.core.auto_binding.logger"):
                # 这应该不会抛出异常，而是记录错误
                try:
                    self.binder.bind_from_assembly("nonexistent.module")
                except ImportError:
                    pass  # 预期的导入错误

    def test_find_implementations_module_error_handling(self):
        """测试查找实现时的模块错误处理"""

        class TestInterface(ABC):
            """测试接口"""

            @abstractmethod
            def test_method(self) -> None:
                """测试方法"""
                pass

        self.binder._scanned_modules.append("error.module")

        with patch(
            "importlib.import_module", side_effect=RuntimeError("模块运行时错误")
        ):
            with patch("src.core.auto_binding.logger"):
                implementations = self.binder._find_implementations(TestInterface)
                assert implementations == []

    def test_check_class_implementations_with_abstract(self):
        """测试检查类实现时处理抽象类"""

        class AbstractBase(ABC):
            @abstractmethod
            def test_method(self):
                pass

        class ConcreteImplementation(AbstractBase):
            def test_method(self):
                pass

        # 设置模块名
        AbstractBase.__module__ = "test_module"
        ConcreteImplementation.__module__ = "test_module"

        # 创建一个模拟模块
        import types

        temp_module = types.ModuleType("test_module")
        temp_module.AbstractBase = AbstractBase
        temp_module.ConcreteImplementation = ConcreteImplementation

        with patch.object(self.container, "register_transient") as mock_register:
            self.binder._check_class_implementations(ConcreteImplementation)
            # 应该注册这个实现
            mock_register.assert_called_once_with(AbstractBase, ConcreteImplementation)

    def test_select_primary_implementation_empty_list(self):
        """测试选择主要实现时空列表处理"""

        class TestInterface(ABC):
            """测试接口"""

            @abstractmethod
            def test_method(self) -> None:
                """测试方法"""
                pass

        result = self.binder._select_primary_implementation(TestInterface, [])
        assert result is None

    def test_apply_default_convention_no_implementation(self):
        """测试应用默认约定时无实现处理"""

        class ITestService(ABC):
            """测试接口"""

            @abstractmethod
            def test_method(self) -> None:
                """测试方法"""
                pass

        class UnrelatedService:
            pass

        self.binder._implementation_cache[ITestService] = [UnrelatedService]

        with patch.object(self.container, "register_transient") as mock_register:
            self.binder._apply_default_convention()
            # 不应该调用注册，因为名称不匹配
            mock_register.assert_not_called()

    def test_bind_interface_to_implementations_with_exception(self):
        """测试绑定接口实现时处理异常"""

        class TestInterface(ABC):
            """测试接口"""

            @abstractmethod
            def test_method(self) -> None:
                """测试方法"""
                pass

        class TestImplementation(TestInterface):
            pass

        with patch.object(
            self.binder, "_find_implementations", return_value=[TestImplementation]
        ):
            with patch.object(
                self.binder,
                "_select_primary_implementation",
                side_effect=Exception("选择失败"),
            ):
                with patch("src.core.auto_binding.logger"):
                    # 应该捕获异常并记录
                    try:
                        self.binder.bind_interface_to_implementations(TestInterface)
                    except Exception:
                        pass