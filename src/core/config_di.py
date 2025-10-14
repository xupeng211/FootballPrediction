from typing import Any, Dict, List, Optional, Union
"""
配置驱动的依赖注入
Configuration-driven Dependency Injection

通过配置文件管理依赖注入。
Manages dependency injection through configuration files.
"""

import json
import yaml  # type: ignore
from pathlib import Path
import logging
from dataclasses import dataclass, field

from .di import DIContainer, ServiceLifetime
from .auto_binding import AutoBinder
from .exceptions import DependencyInjectionError

logger = logging.getLogger(__name__)


@dataclass
class ServiceConfig:
    """服务配置"""

    name: str
    implementation: Optional[str] = None
    lifetime: str = "transient"  # singleton, scoped, transient
    factory: Optional[str] = None
    instance: Optional[str] = None
    dependencies: List[str] = field(default_factory=list)
    parameters: Dict[str, Any] = field(default_factory=dict[str, Any])
    enabled: bool = True
    condition: Optional[str] = None
@dataclass
class DIConfiguration:
    """依赖注入配置"""

    services: Dict[str, ServiceConfig] = field(default_factory=dict[str, Any])
    auto_scan: List[str] = field(default_factory=list)
    conventions: List[str] = field(default_factory=list)
    profiles: List[str] = field(default_factory=list)
    imports: List[str] = field(default_factory=list)


class ConfigurationBinder:
    """配置绑定器"""

    def __init__(self, container: DIContainer):
        self.container = container
        self.auto_binder = AutoBinder(container)
        self._config: Optional[DIConfiguration] = None
        self._active_profile: Optional[str] = None
    def load_from_file(self, config_path: Union[str, Path]) -> None:
        """从文件加载配置"""
        config_path = Path(config_path)

        if not config_path.exists():
            raise DependencyInjectionError(f"配置文件不存在: {config_path}")

        try:
            with open(config_path, "r", encoding="utf-8") as f:
                if config_path.suffix.lower() in [".yml", ".yaml"]:
                    _data = yaml.safe_load(f)
                elif config_path.suffix.lower() == ".json":
                    _data = json.load(f)
                else:
                    raise DependencyInjectionError(
                        f"不支持的配置文件格式: {config_path.suffix}"
                    )

            self._config = self._parse_config(_data)
            logger.info(f"加载配置文件: {config_path}")

        except (ValueError, TypeError, AttributeError, KeyError, RuntimeError) as e:
            raise DependencyInjectionError(f"加载配置文件失败: {e}") from e

    def load_from_dict(self, config_data: Dict[str, Any]) -> None:
        """从字典加载配置"""
        self._config = self._parse_config(config_data)
        logger.info("从字典加载配置")

    def set_active_profile(self, profile: str) -> None:
        """设置活动配置文件"""
        self._active_profile = profile
        logger.info(f"设置活动配置文件: {profile}")

    def apply_configuration(self) -> None:
        """应用配置"""
        if not self._config:
            raise DependencyInjectionError("未加载配置")

        logger.info("应用依赖注入配置")

        # 处理导入
        for import_path in self._config.imports:
            self._import_configuration(import_path)

        # 自动扫描
        for module_path in self._config.auto_scan:
            self.auto_binder.bind_from_assembly(module_path)

        # 应用约定
        for convention in self._config.conventions:
            self.auto_binder.bind_by_convention(convention)

        # 注册服务
        for service_name, service_config in self._config.services.items():
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

    def _parse_config(self, data: Dict[str, Any]) -> DIConfiguration:
        """解析配置"""
        _config = DIConfiguration()

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
                _config.services[service_name] = service_config

        # 解析自动扫描配置
        if "auto_scan" in data:
            _config.auto_scan = data["auto_scan"]

        # 解析约定配置
        if "conventions" in data:
            _config.conventions = data["conventions"]

        # 解析配置文件
        if "profiles" in data:
            _config.profiles = data["profiles"]

        # 解析导入
        if "imports" in data:
            _config.imports = data["imports"]

        return _config

    def _import_configuration(self, import_path: str) -> None:
        """导入配置"""
        try:
            import_path = Path(import_path)  # type: ignore

            if import_path.is_file():  # type: ignore
                binder = ConfigurationBinder(self.container)
                binder.load_from_file(import_path)
                binder.apply_configuration()
            else:
                logger.warning(f"导入路径不存在: {import_path}")

        except (ValueError, TypeError, AttributeError, KeyError, RuntimeError) as e:
            logger.error(f"导入配置失败 {import_path}: {e}")

    def _register_service(self, service_name: str, config: ServiceConfig) -> None:
        """注册服务"""
        try:
            # 获取服务类型
            service_type = self._get_type(service_name)

            if config.implementation:
                # 指定了实现类
                implementation_type = self._get_type(config.implementation)

                lifetime = self._parse_lifetime(config.lifetime)

                if lifetime == ServiceLifetime.SINGLETON:
                    self.container.register_singleton(service_type, implementation_type)
                elif lifetime == ServiceLifetime.SCOPED:
                    self.container.register_scoped(service_type, implementation_type)
                else:
                    self.container.register_transient(service_type, implementation_type)

                logger.debug(f"注册服务: {service_name} -> {config.implementation}")

            elif config.factory:
                # 使用工厂方法
                factory_func = self._get_factory(config.factory)
                lifetime = self._parse_lifetime(config.lifetime)

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

            else:
                # 没有指定实现，尝试自动绑定
                self.auto_binder.bind_interface_to_implementations(service_type)

        except (ValueError, TypeError, AttributeError, KeyError, RuntimeError) as e:
            logger.error(f"注册服务失败 {service_name}: {e}")

    def _get_type(self, type_name: str) -> Type[Any]:
        """获取类型"""
        # 尝试导入类型
        module_path, class_name = type_name.rsplit(".", 1)
        module = __import__(module_path, fromlist=[class_name])
        return getattr(module, class_name)  # type: ignore

    def _get_factory(self, factory_path: str) -> callable:  # type: ignore
        """获取工厂函数"""
        module_path, func_name = factory_path.rsplit(".", 1)
        module = __import__(module_path, fromlist=[func_name])
        return getattr(module, func_name)  # type: ignore

    def _parse_lifetime(self, lifetime_str: str) -> ServiceLifetime:
        """解析生命周期"""
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
        """评估条件"""
        # 简单的条件评估
        # 例如: "profile == 'development'" or "env['DEBUG'] is True"
        try:
            # 这里可以实现更复杂的条件评估逻辑
            if condition.startswith("profile =="):
                profile_name = condition.split("'")[1]
                return self._active_profile == profile_name

            # 添加更多条件评估...

            return True

        except (ValueError, TypeError, AttributeError, KeyError, RuntimeError) as e:
            logger.error(f"评估条件失败 {condition}: {e}")
            return False


class ConfigurationBuilder:
    """配置构建器"""

    def __init__(self):
        self._config = DIConfiguration()

    def add_service(
        self,
        name: str,
        implementation: Optional[str] ] = None,
        lifetime: str = "transient",
        **kwargs,
    ) -> "ConfigurationBuilder":
        """添加服务配置"""
        service_config = ServiceConfig(
            name=name, implementation=implementation, lifetime=lifetime, **kwargs
        )
        self._config.services[name] = service_config
        return self

    def add_auto_scan(self, module_path: str) -> "ConfigurationBuilder":
        """添加自动扫描"""
        self._config.auto_scan.append(module_path)
        return self

    def add_convention(self, convention: str) -> "ConfigurationBuilder":
        """添加约定"""
        self._config.conventions.append(convention)
        return self

    def add_import(self, import_path: str) -> "ConfigurationBuilder":
        """添加导入"""
        self._config.imports.append(import_path)
        return self

    def build(self) -> DIConfiguration:
        """构建配置"""
        return self._config  # type: ignore


def create_config_from_file(config_path: Union[str, Path]) -> DIConfiguration:
    """从文件创建配置"""
    binder = ConfigurationBinder(DIContainer())
    binder.load_from_file(config_path)
    return binder._config  # type: ignore


def create_config_from_dict(config_data: Dict[str, Any]) -> DIConfiguration:
    """从字典创建配置"""
    binder = ConfigurationBinder(DIContainer())
    binder.load_from_dict(config_data)
    return binder._config  # type: ignore


# 示例配置生成器
def generate_sample_config(format: str = "yaml") -> str:
    """生成示例配置"""
    if format.lower() == "yaml":
        return """# 依赖注入配置
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
        return """{
  "services": {
    "database_service": {
      "implementation": "src.services.database.DatabaseService",
      "lifetime": "singleton"
    ",
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
