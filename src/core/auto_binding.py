# mypy: ignore-errors
"""自动绑定系统
Auto Binding System.

提供接口到实现的自动绑定功能.
Provides automatic binding from interfaces to implementations.
"""

import importlib
import inspect
import logging
from dataclasses import dataclass
from pathlib import Path
from typing import TypeVar, Optional

from .di import DIContainer, ServiceLifetime
from .exceptions import DependencyInjectionError

T = TypeVar("T")
logger = logging.getLogger(__name__)


@dataclass
class BindingRule:
    """类文档字符串."""

    pass  # 添加pass语句
    """绑定规则"""

    interface: type
    implementation: type
    lifetime: ServiceLifetime = ServiceLifetime.TRANSIENT
    condition: "callable | None" = None


class AutoBinder:
    """类文档字符串."""

    pass  # 添加pass语句
    """自动绑定器"""

    def __init__(self, container: DIContainer):
        """函数文档字符串."""
        # 添加pass语句
        self.container = container
        self._binding_rules: list[BindingRule] = []
        self._scanned_modules: list[str] = []
        self._implementation_cache: dict[type, list[type]] = {}

    def add_binding_rule(self, rule: BindingRule) -> None:
        """添加绑定规则."""
        self._binding_rules.append(rule)
        logger.debug(
            f"添加绑定规则: {rule.interface.__name__} -> {rule.implementation.__name__}"
        )

    def bind_from_assembly(
        self, module_path: str, pattern: str = "*", recursive: bool = True
    ) -> None:
        """从程序集绑定."""
        logger.info(f"扫描模块 {module_path} 查找绑定")

        # 获取模块路径
        module = importlib.import_module(module_path)
        module_file = (
            Path(module.__file__).parent if hasattr(module, "__file__") else None
        )

        if module_file and module_file.is_dir():
            # 扫描目录中的所有Python文件
            self._scan_directory(module_file, module_path, pattern, recursive)
        else:
            # 扫描单个模块
            self._scan_module(module)

    def bind_by_convention(self, convention: str = "default") -> None:
        """按约定绑定."""
        if convention == "default":
            self._apply_default_convention()
        elif convention == "repository":
            self._apply_repository_convention()
        elif convention == "service":
            self._apply_service_convention()
        else:
            raise DependencyInjectionError(f"未知的绑定约定: {convention}")

    def bind_interface_to_implementations(self, interface: type[T]) -> None:
        """绑定接口到所有实现."""
        implementations = self._find_implementations(interface)

        if not implementations:
            logger.warning(f"未找到接口 {interface.__name__} 的实现")
            return None
        if len(implementations) == 1:
            # 只有一个实现,直接绑定
            self.container.register_transient(interface, implementations[0])
            logger.info(f"绑定 {interface.__name__} -> {implementations[0].name__}")
        else:
            # 多个实现,需要进一步选择
            primary = self._select_primary_implementation(interface, implementations)
            if primary:
                self.container.register_transient(interface, primary)
                logger.info(
                    f"绑定 {interface.__name__} -> {primary.__name__} (主要实现)"
                )

                # 注册其他实现为命名服务
                for impl in implementations:
                    if impl != primary:
                        self.container.register_transient(
                            interface,
                            impl,
                            factory=lambda i=impl: i,  # 工厂方法
                        )
                        logger.debug(
                            f"注册命名实现: {interface.__name__} -> {impl.__name__}"
                        )

    def auto_bind(self) -> None:
        """执行自动绑定."""
        logger.info("开始自动绑定")

        # 应用绑定规则
        for rule in self._binding_rules:
            if rule.condition is None or rule.condition():
                if rule.lifetime == ServiceLifetime.SINGLETON:
                    self.container.register_singleton(
                        rule.interface, rule.implementation
                    )
                elif rule.lifetime == ServiceLifetime.SCOPED:
                    self.container.register_scoped(rule.interface, rule.implementation)
                else:
                    self.container.register_transient(
                        rule.interface, rule.implementation
                    )

        logger.info(f"自动绑定完成,应用了 {len(self._binding_rules)} 个规则")

    def _scan_directory(
        self, directory: Path, module_prefix: str, pattern: str, recursive: bool
    ) -> None:
        """扫描目录."""
        for file_path in directory.glob(f"{pattern}.py"):
            if file_path.name.startswith("_"):
                continue

            # 计算模块名称
            relative_path = file_path.relative_to(directory.parent)
            module_name_parts = list(relative_path.parts)
            module_name_parts[-1] = module_name_parts[-1][:-3]  # 移除.py扩展名
            module_name = ".".join(module_name_parts)

            if module_name in self._scanned_modules:
                continue

            try:
                module = importlib.import_module(module_name)
                self._scan_module(module)
                self._scanned_modules.append(module_name)
            except (ValueError, TypeError, AttributeError, KeyError, RuntimeError) as e:
                logger.error(f"扫描模块失败 {module_name}: {e}")

        if recursive:
            for sub_dir in directory.iterdir():
                if sub_dir.is_dir() and not sub_dir.name.startswith("_"):
                    self._scan_directory(sub_dir, module_prefix, pattern, recursive)

    def _scan_module(self, module) -> None:
        """扫描模块."""
        for _name, obj in inspect.getmembers(module, inspect.isclass):
            # 跳过导入的类
            if obj.__module__ != module.__name__:
                continue

            # 检查是否是接口（抽象基类）
            if inspect.isabstract(obj):
                self._bind_interface_implementations(obj)
            else:
                # 检查是否实现了某个接口
                self._check_class_implementations(obj)

    def _bind_interface_implementations(self, interface: type) -> None:
        """绑定接口实现."""
        implementations = self._find_implementations(interface)

        if implementations:
            if len(implementations) == 1:
                self.container.register_transient(interface, implementations[0])
                logger.debug(
                    f"自动绑定: {interface.__name__} -> {implementations[0].__name__}"
                )
            else:
                # 选择默认实现
                default_impl = self._select_default_implementation(
                    interface, implementations
                )
                if default_impl:
                    self.container.register_transient(interface, default_impl)
                    logger.debug(
                        f"自动绑定: {interface.__name__} -> {default_impl.__name__}"
                    )

    def _check_class_implementations(self, cls: type) -> None:
        """检查类的实现."""
        # 获取类的所有父类
        bases = cls.__bases__

        for base in bases:
            if inspect.isabstract(base):
                # 这是一个接口的实现
                if base not in self._implementation_cache:
                    self._implementation_cache[base] = []
                self._implementation_cache[base].append(cls)

                # 如果这是第一个实现,自动绑定
                if len(self._implementation_cache[base]) == 1:
                    self.container.register_transient(base, cls)
                    logger.debug(f"自动绑定: {base.__name__} -> {cls.__name__}")

    def _find_implementations(self, interface: type) -> list[type]:
        """查找接口的实现."""
        implementations = []

        # 首先检查缓存
        if interface in self._implementation_cache:
            return self._implementation_cache[interface]

        # 扫描已加载的模块
        for module_name in self._scanned_modules:
            try:
                module = importlib.import_module(module_name)
                for _name, obj in inspect.getmembers(module, inspect.isclass):
                    if obj.__module__ != module_name:
                        continue

                    if self._is_implementation(obj, interface):
                        implementations.append(obj)
            except (ValueError, TypeError, AttributeError, KeyError, RuntimeError) as e:
                logger.error(f"查找实现失败 {module_name}: {e}")

        # 缓存结果
        self._implementation_cache[interface] = implementations
        return implementations

    def _is_implementation(self, cls: type, interface: type) -> bool:
        """检查是否是接口的实现."""
        try:
            return issubclass(cls, interface) and not inspect.isabstract(cls)
        except TypeError:
            return False

    def _select_primary_implementation(
        self, interface: type, implementations: list[type]
    ) -> type | None:
        """选择主要实现."""
        # 优先级规则：
        # 1. 类名以接口名结尾的
        # 2. 类名包含Default的
        # 3. 第一个实现

        interface_name = interface.__name__

        # 规则1:类名以接口名结尾
        for impl in implementations:
            if impl.__name__.endswith(interface_name):
                return impl

        # 规则2:类名包含Default
        for impl in implementations:
            if "Default" in impl.__name__:
                return impl

        # 规则3:第一个实现
        return implementations[0] if implementations else None

    def _select_default_implementation(
        self, interface: type, implementations: list[type]
    ) -> type | None:
        """选择默认实现."""
        return self._select_primary_implementation(interface, implementations)

    def _apply_default_convention(self) -> None:
        """应用默认约定."""
        # 默认约定:接口名以I开头,实现名去掉I
        for interface in self._implementation_cache:
            if interface.__name__.startswith("I"):
                default_name = interface.__name__[1:]
                for impl in self._implementation_cache[interface]:
                    if impl.__name__ == default_name:
                        self.container.register_transient(interface, impl)
                        logger.info(
                            f"按约定绑定: {interface.__name__} -> {impl.__name__}"
                        )
                        break

    def _apply_repository_convention(self) -> None:
        """应用仓储约定."""
        # 约定:IRepository -> Repository
        for interface in self._implementation_cache:
            if "Repository" in interface.__name__:
                for impl in self._implementation_cache[interface]:
                    if "Repository" in impl.__name__:
                        self.container.register_scoped(interface, impl)
                        logger.info(
                            f"仓储约定绑定: {interface.__name__} -> {impl.__name__}"
                        )
                        break

    def _apply_service_convention(self) -> None:
        """应用服务约定."""
        # 约定:IService -> Service
        for interface in self._implementation_cache:
            if interface.__name__.startswith("I") and "Service" in interface.__name__:
                for impl in self._implementation_cache[interface]:
                    if "Service" in impl.__name__:
                        self.container.register_scoped(interface, impl)
                        logger.info(
                            f"服务约定绑定: {interface.__name__} -> {impl.__name__}"
                        )
                        break


class ConventionBinder:
    """类文档字符串."""

    pass  # 添加pass语句
    """约定绑定器"""

    @staticmethod
    def bind_by_name_pattern(
        container: DIContainer,
        interface_pattern: str,
        implementation_pattern: str,
        lifetime: ServiceLifetime = ServiceLifetime.TRANSIENT,
    ) -> None:
        """按名称模式绑定."""
        # 这里可以实现更复杂的名称模式匹配

    @staticmethod
    def bind_by_namespace(
        container: DIContainer,
        interface_namespace: str,
        implementation_namespace: str,
        lifetime: ServiceLifetime = ServiceLifetime.TRANSIENT,
    ) -> None:
        """按命名空间绑定."""
        # 这里可以实现命名空间绑定


# 装饰器用于标记自动绑定
def auto_bind(lifetime: ServiceLifetime = ServiceLifetime.TRANSIENT):
    """函数文档字符串."""
    pass  # 添加pass语句
    """自动绑定装饰器"""

    def decorator(cls: type[T]) -> type[T]:
        # 将类标记为可自动绑定
        cls.__auto_bind__ = True
        cls.__bind_lifetime__ = lifetime
        return cls

    return decorator


def bind_to(interface: type[T]):
    """函数文档字符串."""
    pass  # 添加pass语句
    """绑定到接口装饰器"""

    def decorator(cls: type[T]) -> type[T]:
        # 将类标记为接口的实现
        cls.__bind_to__ = interface
        return cls

    return decorator


def primary_implementation():
    """函数文档字符串."""
    pass  # 添加pass语句
    """主要实现装饰器"""

    def decorator(cls) -> type:
        # 将类标记为主要实现
        cls.__primary_implementation__ = True
        return cls

    return decorator
