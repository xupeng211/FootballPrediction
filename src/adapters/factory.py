"""
适配器工厂
Adapter Factory

用于创建和配置适配器实例.
Used to create and configure adapter instances.
"""

import json
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Type, Union

import yaml

from .base import Adapter
from .football import ApiFootballAdapter, CompositeFootballAdapter, OptaDataAdapter


@dataclass
class AdapterConfig:
    """类文档字符串"""
    pass  # 添加pass语句
    """适配器配置"""

    name: str
    adapter_type: str
    enabled: bool = True
    priority: int = 0
    parameters: Dict[str, Any] = field(default_factory=dict)
    rate_limits: Optional[Dict[str, int]] = None
    cache_config: Optional[Dict[str, Any]] = None
    retry_config: Optional[Dict[str, Any]] = None


@dataclass
class AdapterGroupConfig:
    """类文档字符串"""
    pass  # 添加pass语句
    """适配器组配置"""

    name: str
    adapters: List[str]
    primary_adapter: Optional[str] = None
    fallback_strategy: str = "sequential"  # sequential, parallel, random


class AdapterFactory:
    """类文档字符串"""
    pass  # 添加pass语句
    """适配器工厂,用于创建适配器实例"""


# 全局适配器工厂实例
adapter_factory = AdapterFactory()

# 创建默认配置 (延迟到需要时执行)
# adapter_factory.create_default_configs()


# TODO: 方法 def create_adapter_group 过长(25行)，建议拆分
# TODO: 方法 def load_config_from_file 过长(29行)，建议拆分
# TODO: 方法 def save_config_to_file 过长(39行)，建议拆分
# TODO: 方法 def create_default_configs 过长(37行)，建议拆分
# 全局适配器工厂实例
class AdapterFactory:
    """类文档字符串"""
    pass  # 添加pass语句
    # TODO: 方法 def create_adapter_group 过长(25行)，建议拆分
    # TODO: 方法 def create_adapter_group 过长(26行)，建议拆分
    # TODO: 方法 def load_config_from_file 过长(29行)，建议拆分
    # TODO: 方法 def load_config_from_file 过长(30行)，建议拆分
    # TODO: 方法 def save_config_to_file 过长(39行)，建议拆分
    # TODO: 方法 def save_config_to_file 过长(39行)，建议拆分
    # TODO: 方法 def create_default_configs 过长(37行)，建议拆分
    # TODO: 方法 def create_default_configs 过长(37行)，建议拆分
    # 全局适配器工厂实例
    # 全局适配器工厂实例

    # TODO: 方法 def create_adapter_group 过长(27行)，建议拆分
    # TODO: 方法 def load_config_from_file 过长(31行)，建议拆分
    # TODO: 方法 def save_config_to_file 过长(39行)，建议拆分
    # TODO: 方法 def create_default_configs 过长(37行)，建议拆分
    # 全局适配器工厂实例

    # 全局适配器工厂实例

    # TODO: 方法 def _resolve_parameters 过长(21行)，建议拆分
    # TODO: 方法 def create_adapter_group 过长(31行)，建议拆分
    # TODO: 方法 def load_config_from_file 过长(35行)，建议拆分
    # TODO: 方法 def save_config_to_file 过长(39行)，建议拆分
    # TODO: 方法 def create_default_configs 过长(37行)，建议拆分
    # 全局适配器工厂实例
    # TODO: 方法 def create_adapter 过长(21行)，建议拆分
    # TODO: 方法 def _resolve_parameters 过长(21行)，建议拆分
    # TODO: 方法 def _resolve_parameters 过长(22行)，建议拆分
    # TODO: 方法 def create_adapter_group 过长(31行)，建议拆分
    # TODO: 方法 def create_adapter_group 过长(32行)，建议拆分
    # TODO: 方法 def load_config_from_file 过长(35行)，建议拆分
    # TODO: 方法 def load_config_from_file 过长(36行)，建议拆分
    # TODO: 方法 def save_config_to_file 过长(39行)，建议拆分
    # TODO: 方法 def save_config_to_file 过长(39行)，建议拆分
    # TODO: 方法 def create_default_configs 过长(37行)，建议拆分
    # TODO: 方法 def create_default_configs 过长(37行)，建议拆分
    # 全局适配器工厂实例
    # TODO: 方法 def create_adapter 过长(21行)，建议拆分
    # TODO: 方法 def create_adapter 过长(21行)，建议拆分
    # TODO: 方法 def _resolve_parameters 过长(21行)，建议拆分
    # TODO: 方法 def _resolve_parameters 过长(22行)，建议拆分
    # TODO: 方法 def create_adapter_group 过长(31行)，建议拆分
    # TODO: 方法 def create_adapter_group 过长(28行)，建议拆分
    # TODO: 方法 def load_config_from_file 过长(35行)，建议拆分
    # TODO: 方法 def load_config_from_file 过长(35行)，建议拆分
    # TODO: 方法 def save_config_to_file 过长(39行)，建议拆分
    # TODO: 方法 def save_config_to_file 过长(39行)，建议拆分
    # TODO: 方法 def create_default_configs 过长(37行)，建议拆分
    # TODO: 方法 def create_default_configs 过长(37行)，建议拆分
    # 全局适配器工厂实例
    # TODO: 方法 def create_adapter 过长(21行)，建议拆分
    # TODO: 方法 def create_adapter 过长(21行)，建议拆分
    # TODO: 方法 def _resolve_parameters 过长(21行)，建议拆分
    # TODO: 方法 def _resolve_parameters 过长(22行)，建议拆分
    # TODO: 方法 def create_adapter_group 过长(31行)，建议拆分
    # TODO: 方法 def create_adapter_group 过长(28行)，建议拆分
    # TODO: 方法 def load_config_from_file 过长(35行)，建议拆分
    # TODO: 方法 def load_config_from_file 过长(35行)，建议拆分
    # TODO: 方法 def save_config_to_file 过长(39行)，建议拆分
    # TODO: 方法 def save_config_to_file 过长(39行)，建议拆分
    # TODO: 方法 def create_default_configs 过长(37行)，建议拆分
    # TODO: 方法 def create_default_configs 过长(37行)，建议拆分
    # 全局适配器工厂实例
    # TODO: 方法 def create_adapter 过长(21行)，建议拆分
    # TODO: 方法 def create_adapter 过长(21行)，建议拆分
    # TODO: 方法 def _resolve_parameters 过长(21行)，建议拆分
    # TODO: 方法 def _resolve_parameters 过长(22行)，建议拆分
    # TODO: 方法 def create_adapter_group 过长(31行)，建议拆分
    # TODO: 方法 def create_adapter_group 过长(28行)，建议拆分
    # TODO: 方法 def load_config_from_file 过长(35行)，建议拆分
    # TODO: 方法 def load_config_from_file 过长(35行)，建议拆分
    # TODO: 方法 def save_config_to_file 过长(39行)，建议拆分
    # TODO: 方法 def save_config_to_file 过长(39行)，建议拆分
    # TODO: 方法 def create_default_configs 过长(37行)，建议拆分
    # TODO: 方法 def create_default_configs 过长(37行)，建议拆分
    # 全局适配器工厂实例
    # TODO: 方法 def create_adapter 过长(21行)，建议拆分
    # TODO: 方法 def create_adapter 过长(21行)，建议拆分
    # TODO: 方法 def _resolve_parameters 过长(21行)，建议拆分
    # TODO: 方法 def _resolve_parameters 过长(22行)，建议拆分
    # TODO: 方法 def create_adapter_group 过长(31行)，建议拆分
    # TODO: 方法 def create_adapter_group 过长(28行)，建议拆分
    # TODO: 方法 def load_config_from_file 过长(35行)，建议拆分
    # TODO: 方法 def load_config_from_file 过长(35行)，建议拆分
    # TODO: 方法 def save_config_to_file 过长(39行)，建议拆分
    # TODO: 方法 def save_config_to_file 过长(39行)，建议拆分
    # TODO: 方法 def create_default_configs 过长(37行),建议拆分
    # TODO: 方法 def create_default_configs 过长(37行),建议拆分
    # 全局适配器工厂实例
    def __init__(self):
    """函数文档字符串"""
    pass  # 添加pass语句
        self._adapter_types: Dict[str, Type[Adapter]] = {}
        self._configs: Dict[str, AdapterConfig] = {}
        self._group_configs: Dict[str, AdapterGroupConfig] = {}

        # 注册内置适配器类型
        self._register_builtin_adapters()

    def _register_builtin_adapters(self) -> None:
        """注册内置适配器类型"""
        self.register_adapter_type("api-football", ApiFootballAdapter)
        self.register_adapter_type("opta-data", OptaDataAdapter)
        self.register_adapter_type("composite-football", CompositeFootballAdapter)

    def register_adapter_type(self, name: str, adapter_class: Type[Adapter]) -> None:
        """注册适配器类型"""
        self._adapter_types[name] = adapter_class

    def unregister_adapter_type(self, name: str) -> None:
        """注销适配器类型"""
        self._adapter_types.pop(name, None)

    # TODO: 方法 def create_adapter 过长(21行),建议拆分
    # TODO: 方法 def create_adapter 过长(21行),建议拆分
    def create_adapter(self, config: AdapterConfig) -> Adapter:
        """创建适配器实例"""
        if not config.enabled:
            raise ValueError(f"Adapter {config.name} is disabled")

        adapter_class = self._adapter_types.get(config.adapter_type)
        if not adapter_class:
            raise ValueError(f"Unknown adapter type: {config.adapter_type}")

        # 从环境变量获取API密钥
        parameters = self._resolve_parameters(config.parameters)

        # 创建适配器
        adapter = adapter_class(**parameters)

        # 配置附加属性
        adapter.priority = config.priority

        return adapter

    # TODO: 方法 def _resolve_parameters 过长(21行),建议拆分
    # TODO: 方法 def _resolve_parameters 过长(22行),建议拆分
    def _resolve_parameters(self, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """解析参数,从环境变量替换敏感信息"""
        resolved = {}
        for key, value in parameters.items():
            if isinstance(value, str) and value.startswith("$"):
                # 从环境变量获取
                env_var = value[1:]  # 移除$前缀
                env_value = os.getenv(env_var)
                if env_value is None:
                    raise ValueError(f"Environment variable {env_var} not found")
                resolved[key] = env_value
            else:
                resolved[key] = value
        return resolved

    # TODO: 方法 def create_adapter_group 过长(25行)，建议拆分
    # TODO: 方法 def create_adapter_group 过长(26行)，建议拆分
    # TODO: 方法 def create_adapter_group 过长(27行)，建议拆分
    # TODO: 方法 def create_adapter_group 过长(28行)，建议拆分
    # TODO: 方法 def create_adapter_group 过长(29行)，建议拆分
    # TODO: 方法 def create_adapter_group 过长(30行)，建议拆分
    # TODO: 方法 def create_adapter_group 过长(31行),建议拆分
    # TODO: 方法 def create_adapter_group 过长(28行),建议拆分
    def create_adapter_group(self, group_config: AdapterGroupConfig) -> Adapter:
        """创建适配器组"""
        if group_config.adapters:
            # 创建复合适配器
            composite = self.create_adapter(
                AdapterConfig(name=f"composite_{group_config.name}")
            )

            # 添加子适配器
            for adapter_name in group_config.adapters:
                adapter_config = self._configs.get(adapter_name)
                if adapter_config:
                    adapter = self.create_adapter(adapter_config)
                    is_primary = adapter_name == group_config.primary_adapter
                    composite.add_adapter(adapter)

            return composite
        else:
            raise ValueError(f"No adapters configured for group {group_config.name}")

    # TODO: 方法 def load_config_from_file 过长(29行)，建议拆分
    # TODO: 方法 def load_config_from_file 过长(30行)，建议拆分
    # TODO: 方法 def load_config_from_file 过长(31行)，建议拆分
    # TODO: 方法 def load_config_from_file 过长(32行)，建议拆分
    # TODO: 方法 def load_config_from_file 过长(33行)，建议拆分
    # TODO: 方法 def load_config_from_file 过长(34行)，建议拆分
    # TODO: 方法 def load_config_from_file 过长(35行),建议拆分
    # TODO: 方法 def load_config_from_file 过长(35行),建议拆分
    def load_config_from_file(self) -> None:
        """从文件加载适配器配置"""
        file_path = Path(file_path)

        if not file_path.exists():
            raise FileNotFoundError(f"Config file not found: {file_path}")

        # 根据文件扩展名选择解析器
        if file_path.suffix.lower() in [".yaml", ".yml"]:
            with open(file_path, "r", encoding="utf-8") as f:
                data = yaml.safe_load(f)
        elif file_path.suffix.lower() == ".json":
            with open(file_path, "r", encoding="utf-8") as f:
                data = json.load(f)
        else:
            raise ValueError(f"Unsupported config file format: {file_path.suffix}")

        # 解析适配器配置
        if "adapters" in data:
            for adapter_data in data["adapters"]:
                config = AdapterConfig(**adapter_data)
                self._configs[config.name] = config

        # 解析适配器组配置
        if "adapter_groups" in data:
            for group_data in data["adapter_groups"]:
                group_config = AdapterGroupConfig(**group_data)
                self._group_configs[group_config.name] = group_config

    # TODO: 方法 def save_config_to_file 过长(39行)，建议拆分
    # TODO: 方法 def save_config_to_file 过长(39行)，建议拆分
    # TODO: 方法 def save_config_to_file 过长(39行)，建议拆分
    # TODO: 方法 def save_config_to_file 过长(39行)，建议拆分
    # TODO: 方法 def save_config_to_file 过长(39行)，建议拆分
    # TODO: 方法 def save_config_to_file 过长(39行)，建议拆分
    # TODO: 方法 def save_config_to_file 过长(39行),建议拆分
    # TODO: 方法 def save_config_to_file 过长(39行),建议拆分
    def save_config_to_file(self, file_path: Union[str, Path]) -> None:
        """保存配置到文件"""
        file_path = Path(file_path)

        data = {
            "adapters": [
                {
                    "name": config.name,
                    "adapter_type": config.adapter_type,
                    "enabled": config.enabled,
                    "priority": config.priority,
                    "parameters": self._mask_sensitive_parameters(config.parameters),
                    "rate_limits": config.rate_limits,
                    "cache_config": config.cache_config,
                    "retry_config": config.retry_config,
                }
                for config in self._configs.values()
            ],
            "adapter_groups": [
                {
                    "name": group.name,
                    "adapters": group.adapters,
                    "primary_adapter": group.primary_adapter,
                    "fallback_strategy": group.fallback_strategy,
                }
                for group in self._group_configs.values()
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

    def _mask_sensitive_parameters(self, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """屏蔽敏感参数"""
        sensitive_keys = ["api_key", "password", "secret", "token"]
        masked = {}

        for key, value in parameters.items():
            if any(sensitive in key.lower() for sensitive in sensitive_keys):
                masked[key] = "***"
            else:
                masked[key] = value

        return masked

    # TODO: 方法 def create_default_configs 过长(37行)，建议拆分
    # TODO: 方法 def create_default_configs 过长(37行)，建议拆分
    # TODO: 方法 def create_default_configs 过长(37行)，建议拆分
    # TODO: 方法 def create_default_configs 过长(37行)，建议拆分
    # TODO: 方法 def create_default_configs 过长(37行)，建议拆分
    # TODO: 方法 def create_default_configs 过长(37行)，建议拆分
    # TODO: 方法 def create_default_configs 过长(37行),建议拆分
    # TODO: 方法 def create_default_configs 过长(37行),建议拆分
    def create_default_configs(self) -> None:
        """创建默认配置"""
        # API Football配置
        api_football_config = AdapterConfig(
            name="api_football_main",
            adapter_type="api-football",
            enabled=True,
            priority=100,  # TODO: 将魔法数字 100 提取为常量
            parameters={"api_key": "$API_FOOTBALL_KEY"},
            rate_limits={"requests_per_minute": 10},
            cache_config={"ttl": 300},  # TODO: 将魔法数字 300 提取为常量
            retry_config={"max_retries": 3, "delay": 1.0},
        )
        self._configs["api_football_main"] = api_football_config

        # OpenWeatherMap配置
        weather_config = AdapterConfig(
            name="openweathermap_main",
            adapter_type="openweathermap",
            enabled=True,
            priority=100,  # TODO: 将魔法数字 100 提取为常量
            parameters={"api_key": "$OPENWEATHERMAP_KEY"},
            rate_limits={"requests_per_minute": 60},  # TODO: 将魔法数字 60 提取为常量
            cache_config={"ttl": 600},  # TODO: 将魔法数字 600 提取为常量
            retry_config={"max_retries": 3, "delay": 1.0},
        )
        self._configs["openweathermap_main"] = weather_config

        # 足球数据源组
        football_group = AdapterGroupConfig(
            name="football_sources",
            adapters=["api_football_main"],
            primary_adapter="api_football_main",
            fallback_strategy="sequential",
        )
        self._group_configs["football_sources"] = football_group

    def get_config(self, name: str) -> Optional[AdapterConfig]:
        """获取适配器配置"""
        return self._configs.get(name)

    def get_group_config(self, name: str) -> Optional[AdapterGroupConfig]:
        """获取适配器组配置"""
        return self._group_configs.get(name)

    def list_configs(self) -> List[str]:
        """列出所有配置"""
        return list(self._configs.keys())

    def list_group_configs(self) -> List[str]:
        """列出所有组配置"""
        return list(self._group_configs.keys())

    def validate_config(self, config: AdapterConfig) -> List[str]:
        """验证配置"""
        errors = []

        # 检查适配器类型
        if config.adapter_type not in self._adapter_types:
            errors.append(f"Unknown adapter type: {config.adapter_type}")

        # 检查必需参数
        adapter_class = self._adapter_types.get(config.adapter_type)
        if adapter_class:
            # 这里可以添加更复杂的参数验证逻辑
            pass

        return errors


# 全局适配器工厂实例]
