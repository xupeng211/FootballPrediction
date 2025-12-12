"""配置驱动的依赖注入
Configuration-driven Dependency Injection.

通过配置文件管理依赖注入.
Manages dependency injection through configuration files.
"""

import importlib
import json
import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml

from .auto_binding import AutoBinder
from .di import DIContainer, ServiceLifetime
from .exceptions import DependencyInjectionError

logger = logging.getLogger(__name__)


@dataclass
class ServiceConfig:
    """类文档字符串."""

    pass  # 添加pass语句
    """服务配置"""

    name: str
    implementation: str | None = None
    lifetime: str = "transient"  # singleton, scoped, transient
    factory: str | None = None
    instance: str | None = None
    dependencies: list[str] = field(default_factory=list)
    parameters: dict[str, Any] = field(default_factory=dict)
    enabled: bool = True
    condition: str | None = None


@dataclass
class DIConfiguration:
    """类文档字符串."""

    pass  # 添加pass语句
    """依赖注入配置"""

    services: dict[str, ServiceConfig] = field(default_factory=dict)
    auto_scan: list[str] = field(default_factory=list)
    conventions: list[str] = field(default_factory=list)
    profiles: list[str] = field(default_factory=list)
    imports: list[str] = field(default_factory=list)


class ConfigurationBinder:
    """类文档字符串."""

    pass  # 添加pass语句
    """配置绑定器"""

    def __init__(self, container: DIContainer):
        """函数文档字符串."""
        # 添加pass语句
        self.container = container
        self.auto_binder = AutoBinder(container)
        self.config: DIConfiguration | None = None
        self._active_profile: str | None = None

    def load_from_file(self, config_path: str | Path) -> None:
        """从文件加载配置."""
        config_path = Path(config_path)

        if not config_path.exists():
            raise DependencyInjectionError(f"配置文件不存在: {config_path}")

        try:
            with open(config_path, encoding="utf-8") as f:
                if config_path.suffix.lower() in [".yml", ".yaml"]:
                    data = yaml.safe_load(f)
                elif config_path.suffix.lower() == ".json":
                    data = json.load(f)
                else:
                    raise DependencyInjectionError(
                        f"不支持的配置文件格式: {config_path.suffix}"
                    )

            # 处理空文件情况
            if data is None:
                data = {}

            self.config = self._parse_config(data)
            logger.info(f"加载配置文件: {config_path}")

        except (ValueError, AttributeError, KeyError, RuntimeError) as e:
            raise DependencyInjectionError(f"加载配置文件失败: {e}") from e

    def load_from_dict(self, config_data: dict[str, Any]) -> None:
        """从字典加载配置."""
        try:
            self.config = self._parse_config(config_data)
            logger.info("从字典加载配置")
        except (AttributeError, KeyError, TypeError) as e:
            raise DependencyInjectionError(f"解析配置失败: {e}") from e

    def set_active_profile(self, profile: str) -> None:
        """设置活动配置文件."""
        # 检查profile是否在配置的profiles列表中
        if self.config and profile not in self.config.profiles:
            raise DependencyInjectionError(f"配置文件不存在: {profile}")

        self._active_profile = profile
        logger.info(f"设置活动配置文件: {profile}")

    def bind_services(self) -> None:
        """绑定服务 - apply_configuration的别名."""
        self.apply_configuration()

    def auto_scan_and_bind(self) -> None:
        """自动扫描并绑定 - 委托给auto_binder."""
        if not self.config:
            return

        # 对每个自动扫描模块进行绑定
        for module_path in self.config.auto_scan:
            self.auto_binder.auto_scan_and_bind(module_path, recursive=True)

    def import_modules(self) -> None:
        """导入配置的模块."""
        if not self.config:
            return

        # 导入所有配置的模块
        for module_name in self.config.imports:
            try:
                importlib.import_module(module_name)
                logger.debug(f"导入模块: {module_name}")
            except (ValueError, AttributeError, KeyError, RuntimeError) as e:
                logger.error(f"导入模块失败 {module_name}: {e}")

    def apply_configuration(self) -> None:
        """应用配置."""
        if not self.config:
            raise DependencyInjectionError("未加载配置")

        logger.info("应用依赖注入配置")

        # 处理导入
        for import_path in self.config.imports:
            self._import_configuration(import_path)

        # 自动扫描
        for module_path in self.config.auto_scan:
            self.auto_binder.bind_from_assembly(module_path)

        # 应用约定
        for convention in self.config.conventions:
            self.auto_binder.bind_by_convention(convention)

        # 注册服务
        for service_name, service_config in self.config.services.items():
            if not service_config.enabled:
                logger.debug(f"跳过禁用的服务: {service_name}")
                continue

            # 检查配置文件条件
            if service_config.condition:
                if not self._evaluate_condition(service_config.condition):
                    logger.debug(f"服务条件不满足: {service_name}")
                    continue

            self._register_service(service_name, service_config)

        logger.info("配置应用完成")

    def _parse_config(self, data: dict[str, Any]) -> DIConfiguration:
        """解析配置."""
        config = DIConfiguration()

        # 解析服务配置
        if "services" in data:
            for service_name, service_data in data["services"].items():
                service_config = ServiceConfig(
                    name=service_name,
                    implementation=service_data.get("implementation"),
                    lifetime=service_data.get("lifetime", "transient"),
                    factory=service_data.get("factory"),
                    instance=service_data.get("instance"),
                    dependencies=service_data.get("dependencies", []),
                    parameters=service_data.get("parameters", {}),
                    enabled=service_data.get("enabled", True),
                    condition=service_data.get("condition"),
                )
                config.services[service_name] = service_config

        # 解析自动扫描配置
        if "auto_scan" in data:
            config.auto_scan = data["auto_scan"]

        # 解析约定配置
        if "conventions" in data:
            config.conventions = data["conventions"]

        # 解析配置文件
        if "profiles" in data:
            config.profiles = data["profiles"]

        # 解析导入
        if "imports" in data:
            config.imports = data["imports"]

        return config

    def _import_configuration(self, import_path: str) -> None:
        """导入配置."""
        try:
            import_path = Path(import_path)

            if import_path.is_file():
                binder = ConfigurationBinder(self.container)
                binder.load_from_file(import_path)
                binder.apply_configuration()
            else:
                logger.warning(f"导入路径不存在: {import_path}")

        except (ValueError, AttributeError, KeyError, RuntimeError) as e:
            logger.error(f"导入配置失败 {import_path}: {e}")

    def _register_service(self, service_name: str, config: ServiceConfig) -> None:
        """注册服务."""
        try:
            # 尝试获取服务类型，如果失败则使用实现类型
            service_type = None
            if "." in service_name:
                try:
                    service_type = self._get_type(service_name)
                except (ValueError, AttributeError, KeyError, RuntimeError):
                    # 如果服务名称不是有效的类型路径，记录警告并继续
                    logger.warning(f"服务名称 {service_name} 不是有效的类型路径，将使用实现类型")

            if config.implementation:
                # 指定了实现类
                try:
                    # 检查实现是否包含模块路径
                    if "." in config.implementation:
                        implementation_type = self._get_type(config.implementation)
                    else:
                        # 如果没有模块路径，无法解析类型，跳过此服务
                        logger.warning(f"实现 {config.implementation} 没有模块路径，跳过服务注册")
                        return

                    # 如果没有服务类型，使用实现类型
                    if service_type is None:
                        service_type = implementation_type

                    lifetime = self._parse_lifetime(config.lifetime)

                    if lifetime == ServiceLifetime.SINGLETON:
                        self.container.register_singleton(service_type, implementation_type)
                    elif lifetime == ServiceLifetime.SCOPED:
                        self.container.register_scoped(service_type, implementation_type)
                    else:
                        self.container.register_transient(service_type, implementation_type)

                    logger.debug(f"注册服务: {service_name} -> {config.implementation}")
                except DependencyInjectionError as e:
                    # 如果无法解析实现类型，跳过此服务
                    logger.warning(f"无法注册服务 {service_name}: {e}")
                    return

            elif config.factory:
                # 使用工厂方法
                try:
                    # 检查工厂是否包含模块路径
                    if "." in config.factory:
                        factory_func = self._get_factory(config.factory)
                    else:
                        # 如果没有模块路径，无法解析，跳过此服务
                        logger.warning(f"工厂 {config.factory} 没有模块路径，跳过服务注册")
                        return

                    lifetime = self._parse_lifetime(config.lifetime)

                    # 如果没有服务类型，尝试使用工厂的返回类型
                    if service_type is None:
                        # 调用工厂函数来获取返回类型
                        try:
                            temp_instance = factory_func()
                            service_type = type(temp_instance)
                            logger.debug(f"从工厂获取服务类型: {service_type}")
                        except Exception as e:
                            logger.error(f"无法调用工厂函数来获取类型: {e}")
                            raise DependencyInjectionError(
                                f"使用工厂方法注册服务时，无法获取服务类型: {e}"
                            )

                    if lifetime == ServiceLifetime.SINGLETON:
                        self.container.register_singleton(
                            service_type, factory=factory_func
                        )
                    elif lifetime == ServiceLifetime.SCOPED:
                        self.container.register_scoped(service_type, factory=factory_func)
                    else:
                        self.container.register_transient(
                            service_type, factory=factory_func
                        )

                    logger.debug(f"注册工厂服务: {service_name}")
                except DependencyInjectionError as e:
                    # 如果无法解析工厂，跳过此服务
                    logger.warning(f"无法注册服务 {service_name}: {e}")
                    return

            else:
                # 没有指定实现,尝试自动绑定
                if service_type is None:
                    raise DependencyInjectionError(
                        f"服务 {service_name} 既没有指定实现也没有指定工厂，且服务名称不是有效的类型路径"
                    )
                self.auto_binder.bind_interface_to_implementations(service_type)

        except (ValueError, AttributeError, KeyError, RuntimeError) as e:
            logger.error(f"注册服务失败 {service_name}: {e}")
            raise

    def _get_type(self, service_name: str) -> type:
        """获取类型."""
        # 尝试导入类型
        try:
            module_path, class_name = service_name.rsplit(".", 1)
        except ValueError:
            raise DependencyInjectionError(
                f"无效的类型路径: {service_name}，必须包含 '.' 分隔符"
            )

        try:
            module = importlib.import_module(module_path)
        except (ValueError, AttributeError, ImportError) as e:
            raise DependencyInjectionError(
                f"导入模块失败 {module_path}: {e}"
            ) from e

        try:
            return getattr(module, class_name)
        except AttributeError:
            raise DependencyInjectionError(
                f"模块 {module_path} 中没有找到属性 {class_name}"
            )

    def _get_factory(self, factory_path: str) -> callable:
        """获取工厂函数."""
        module_path, func_name = factory_path.rsplit(".", 1)
        module = importlib.import_module(module_path)
        return getattr(module, func_name)

    def _parse_lifetime(self, lifetime_str: str) -> ServiceLifetime:
        """解析生命周期."""
        lifetime_map = {
            "singleton": ServiceLifetime.SINGLETON,
            "scoped": ServiceLifetime.SCOPED,
            "transient": ServiceLifetime.TRANSIENT,
        }

        lifetime = lifetime_map.get(lifetime_str.lower())
        if not lifetime:
            raise DependencyInjectionError(f"未知的生命周期: {lifetime_str}")

        return lifetime

    def _evaluate_condition(self, condition: str) -> bool:
        """评估条件."""
        # 简单的条件评估
        # 例如: "profile == 'development'" or "env['DEBUG'] is True"
        try:
            # 这里可以实现更复杂的条件评估逻辑
            if condition.startswith("profile =="):
                profile_name = condition.split("'")[1]
                return self._active_profile == profile_name

            # 添加更多条件评估...

            return True

        except (ValueError, AttributeError, KeyError, RuntimeError) as e:
            logger.error(f"评估条件失败 {condition}: {e}")
            return False


class ConfigurationBuilder:
    """类文档字符串."""

    pass  # 添加pass语句
    """配置构建器"""

    def __init__(self):
        """函数文档字符串."""
        # 添加pass语句
        self.config = DIConfiguration()

    def add_service(
        self,
        name: str,
        implementation: str | None = None,
        lifetime: str = "transient",
        **kwargs,
    ) -> "ConfigurationBuilder":
        """添加服务配置."""
        service_config = ServiceConfig(
            name=name, implementation=implementation, lifetime=lifetime, **kwargs
        )
        self.config.services[name] = service_config
        return self

    def add_auto_scan(self, module_path: str) -> "ConfigurationBuilder":
        """添加自动扫描."""
        self.config.auto_scan.append(module_path)
        return self

    def add_convention(self, convention: str) -> "ConfigurationBuilder":
        """添加约定."""
        self.config.conventions.append(convention)
        return self

    def add_import(self, import_path: str) -> "ConfigurationBuilder":
        """添加导入."""
        self.config.imports.append(import_path)
        return self

    def build(self) -> DIConfiguration:
        """构建配置."""
        return self.config


def create_config_from_file(config_path: str | Path) -> DIConfiguration:
    """从文件创建配置."""
    binder = ConfigurationBinder(DIContainer())
    binder.load_from_file(config_path)
    return binder.config


def create_config_from_dict(config_data: dict[str, Any]) -> DIConfiguration:
    """从字典创建配置."""
    binder = ConfigurationBinder(DIContainer())
    binder.load_from_dict(config_data)
    return binder.config


# 示例配置生成器
def generate_sample_config(output_format: str = "yaml") -> str:
    """生成示例配置."""
    if output_format.lower() == "yaml":
        return """# 依赖注入配置"
services:
  # 数据库服务
  database_service:
    implementation: src.services.database.DatabaseService
    lifetime: singleton

  # 仓储服务
  user_repository:
    implementation: src.database.repositories.UserRepository
    lifetime: scoped

  match_repository:
    implementation: src.database.repositories.MatchRepository
    lifetime: scoped

  # 业务服务
  prediction_service:
    implementation: src.services.prediction.PredictionService
    lifetime: scoped
    dependencies:
      - match_repository
      - user_repository
    parameters:
      max_predictions_per_day: 10

  # 使用工厂
  cache_service:
    factory: src.factories.create_cache_service
    lifetime: singleton
    condition: "profile == 'production'"

# 自动扫描的模块
auto_scan:
  - src.services
  - src.repositories
  - src.domain.services

# 绑定约定
conventions:
  - repository
  - service
  - default

# 配置文件
profiles:
  - development
  - production
  - testing

# 导入其他配置文件
imports:
  - configs/di-services.yaml
  - configs/di-repositories.yaml
"""
    else:  # JSON
        return """{"
  "services": {
    "database_service": {
      "implementation": "src.services.database.DatabaseService",
      "lifetime": "singleton"
    },
    "user_repository": {
      "implementation": "src.database.repositories.UserRepository",
      "lifetime": "scoped"
    },
    "prediction_service": {
      "implementation": "src.services.prediction.PredictionService",
      "lifetime": "scoped",
      "dependencies": ["match_repository", "user_repository"],
      "parameters": {
        "max_predictions_per_day": 10
      }
    }
  },
  "auto_scan": [
    "src.services",
    "src.repositories"
  ],
  "conventions": [
    "repository",
    "service"
  ],
  "profiles": [
    "development",
    "production"
  ]
}"""
