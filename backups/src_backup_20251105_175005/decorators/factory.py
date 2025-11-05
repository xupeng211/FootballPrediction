"""
装饰器工厂
Decorator Factory

用于创建和配置装饰器实例.
Used to create and configure decorator instances.
"""

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml

from .base import Component, Decorator, decorator_registry


@dataclass
class DecoratorConfig:
    """类文档字符串"""

    pass  # 添加pass语句
    """装饰器配置"""

    name: str
    decorator_type: str
    enabled: bool = True
    priority: int = 0
    parameters: dict[str, Any] = field(default_factory=dict)
    conditions: dict[str, Any] | None = None


@dataclass
class DecoratorChainConfig:
    """类文档字符串"""

    pass  # 添加pass语句
    """装饰器链配置"""

    name: str
    target_functions: list[str]
    decorators: list[DecoratorConfig]
    is_global: bool = False


class DecoratorFactory:
    """类文档字符串"""

    pass  # 添加pass语句
    """装饰器工厂,用于创建装饰器实例"""

    def __init__(self):
        """函数文档字符串"""
        # 添加pass语句
        self._config_cache: dict[str, DecoratorConfig] = {}
        self._chain_configs: dict[str, DecoratorChainConfig] = {}

    def create_decorator(
        self, decorator_type: str, component: Component, **kwargs
    ) -> Decorator:
        """创建装饰器实例"""
        # 获取装饰器类
        decorator_class = decorator_registry.get_decorator_class(decorator_type)
        if not decorator_class:
            raise ValueError(f"Unknown decorator type: {decorator_type}")

        # 创建实例
        return decorator_class(component, **kwargs)

    def create_from_config(
        self, config: DecoratorConfig, component: Component
    ) -> Decorator:
        """从配置创建装饰器实例"""
        if not config.enabled:
            raise ValueError(f"Decorator {config.name} is disabled")

        return self.create_decorator(
            config.decorator_type, component, name=config.name, **config.parameters
        )

    def create_chain(
        self, configs: list[DecoratorConfig], component: Component
    ) -> list[Decorator]:
        """创建装饰器链"""
        # 按优先级排序
        sorted_configs = sorted(configs, key=lambda x: x.priority)

        decorators = []
        for config in sorted_configs:
            if config.enabled:
                decorator = self.create_from_config(config, component)
                decorators.append(decorator)

        return decorators

    def load_config_from_file(self, file_path: str | Path) -> None:
        """从文件加载装饰器配置"""
        file_path = Path(file_path)

        if not file_path.exists():
            raise FileNotFoundError(f"Config file not found: {file_path}")

        # 根据文件扩展名选择解析器
        if file_path.suffix.lower() == ".yaml" or file_path.suffix.lower() == ".yml":
            with open(file_path, encoding="utf-8") as f:
                data = yaml.safe_load(f)
        elif file_path.suffix.lower() == ".json":
            with open(file_path, encoding="utf-8") as f:
                data = json.load(f)
        else:
            raise ValueError(f"Unsupported config file format: {file_path.suffix}")

        # 解析装饰器配置
        if "decorators" in data:
            for decorator_data in data["decorators"]:
                config = DecoratorConfig(**decorator_data)
                self._config_cache[config.name] = config

        # 解析装饰器链配置
        if "chains" in data:
            for chain_data in data["chains"]:
                chain_config = DecoratorChainConfig(**chain_data)
                self._chain_configs[chain_config.name] = chain_config

    def get_config(self, name: str) -> DecoratorConfig | None:
        """获取装饰器配置"""
        return self._config_cache.get(name)

    def get_chain_config(self, name: str) -> DecoratorChainConfig | None:
        """获取装饰器链配置"""
        return self._chain_configs.get(name)

    def list_configs(self) -> list[str]:
        """列出所有配置的装饰器"""
        return list(self._config_cache.keys())

    def list_chain_configs(self) -> list[str]:
        """列出所有配置的装饰器链"""
        return list(self._chain_configs.keys())

    def save_config_to_file(self, file_path: str | Path) -> None:
        """保存配置到文件"""
        file_path = Path(file_path)

        data = {
            "decorators": [
                {
                    "name": config.name,
                    "decorator_type": config.decorator_type,
                    "enabled": config.enabled,
                    "priority": config.priority,
                    "parameters": config.parameters,
                    "conditions": config.conditions,
                }
                for config in self._config_cache.values()
            ],
            "chains": [
                {
                    "name": chain.name,
                    "target_functions": chain.target_functions,
                    "decorators": [
                        {
                            "name": d.name,
                            "decorator_type": d.decorator_type,
                            "enabled": d.enabled,
                            "priority": d.priority,
                            "parameters": d.parameters,
                            "conditions": d.conditions,
                        }
                        for d in chain.decorators
                    ],
                    "global": chain.is_global,
                }
                for chain in self._chain_configs.values()
            ],
        }

        # 根据文件扩展名选择格式
        if file_path.suffix.lower() in [".yaml", ".yml"]:
            with open(file_path, "w", encoding="utf-8") as f:
                yaml.dump(data, f, default_flow_style=False, allow_unicode=True)
        elif file_path.suffix.lower() == ".json":
            with open(file_path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
        else:
            raise ValueError(f"Unsupported config file format: {file_path.suffix}")

    def create_default_configs(self) -> None:
        """创建默认配置"""
        # 日志装饰器配置
        logging_config = DecoratorConfig(
            name="default_logging",
            decorator_type="logging",
            parameters={
                "level": "INFO",
                "log_args": True,
                "log_result": True,
                "log_exception": True,
            },
            priority=100,
        )
        self._config_cache["default_logging"] = logging_config

        # 重试装饰器配置
        retry_config = DecoratorConfig(
            name="default_retry",
            decorator_type="retry",
            parameters={
                "max_attempts": 3,
                "delay": 1.0,
                "backoff_factor": 2.0,
                "max_delay": 60.0,
            },
            priority=90,
        )
        self._config_cache["default_retry"] = retry_config

        # 指标装饰器配置
        metrics_config = DecoratorConfig(
            name="default_metrics",
            decorator_type="metrics",
            parameters={
                "track_args": False,
            },
            priority=80,
        )
        self._config_cache["default_metrics"] = metrics_config

        # 缓存装饰器配置
        cache_config = DecoratorConfig(
            name="default_cache",
            decorator_type="cache",
            parameters={
                "ttl": 300,
                "cache_empty": False,
            },
            priority=70,
        )
        self._config_cache["default_cache"] = cache_config

        # 超时装饰器配置
        timeout_config = DecoratorConfig(
            name="default_timeout",
            decorator_type="timeout",
            parameters={
                "timeout_seconds": 30.0,
            },
            priority=60,
        )
        self._config_cache["default_timeout"] = timeout_config

        # 创建API装饰器链
        api_chain = DecoratorChainConfig(
            name="api_chain",
            target_functions=["api_*"],
            decorators=[
                logging_config,
                metrics_config,
                timeout_config,
            ],
        )
        self._chain_configs["api_chain"] = api_chain

        # 创建服务装饰器链
        service_chain = DecoratorChainConfig(
            name="service_chain",
            target_functions=["service_*"],
            decorators=[
                logging_config,
                retry_config,
                metrics_config,
            ],
        )
        self._chain_configs["service_chain"] = service_chain


class DecoratorBuilder:
    """类文档字符串"""

    pass  # 添加pass语句
    """装饰器构建器,使用构建器模式创建装饰器"""

    def __init__(self, decorator_type: str, component: Component):
        """函数文档字符串"""
        # 添加pass语句
        self.decorator_type = decorator_type
        self.component = component
        self.parameters: dict[str, Any] = {}
        self.name: str | None = None

    def with_name(self, name: str) -> "DecoratorBuilder":
        """设置装饰器名称"""
        self.name = name
        return self

    def with_parameter(self, key: str, value: Any) -> "DecoratorBuilder":
        """设置参数"""
        self.parameters[key] = value
        return self

    def with_parameters(self, **kwargs) -> "DecoratorBuilder":
        """批量设置参数"""
        self.parameters.update(kwargs)
        return self

    def build(self) -> Decorator:
        """构建装饰器实例"""
        factory = DecoratorFactory()
        return factory.create_decorator(
            self.decorator_type, self.component, name=self.name, **self.parameters
        )


# 全局装饰器工厂实例
decorator_factory = DecoratorFactory()

# 创建默认配置
decorator_factory.create_default_configs()
