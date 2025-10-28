"""
门面工厂
Facade Factory

用于创建和配置门面实例。
Used to create and configure facade instances.
"""

import json
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Type, Union

import yaml

from .base import SystemFacade
from .facades import (
    AnalyticsFacade,
    DataCollectionFacade,
    MainSystemFacade,
    NotificationFacade,
    PredictionFacade,
)


@dataclass
class FacadeConfig:
    """门面配置"""

    name: str
    facade_type: str
    enabled: bool = True
    auto_initialize: bool = True
    subsystems: List[str] = field(default_factory=list)
    parameters: Dict[str, Any] = field(default_factory=dict)
    environment: Optional[str] = None


class FacadeFactory:
    """门面工厂类"""

    # 注册的门面类型
    FACADE_TYPES: Dict[str, Type[SystemFacade]] = {
        "main": MainSystemFacade,
        "prediction": PredictionFacade,
        "data_collection": DataCollectionFacade,
        "analytics": AnalyticsFacade,
        "notification": NotificationFacade,
    }

    def __init__(self):
        self._config_cache: Dict[str, FacadeConfig] = {}
        self._instance_cache: Dict[str, SystemFacade] = {}
        self.default_environment = os.getenv("ENVIRONMENT", "development")

    def create_facade(
        self, facade_type: str, config: Optional[FacadeConfig] = None
    ) -> SystemFacade:
        """创建门面实例"""
        if facade_type not in self.FACADE_TYPES:
            raise ValueError(f"Unknown facade type: {facade_type}")

        facade_class = self.FACADE_TYPES[facade_type]
        facade = facade_class()

        # 应用配置
        if config:
            self._apply_config(facade, config)

        return facade

    def create_from_config(self, config: FacadeConfig) -> SystemFacade:
        """从配置创建门面"""
        if not config.enabled:
            raise ValueError(f"Facade {config.name} is disabled")

        return self.create_facade(config.facade_type, config)

    def create_all_from_configs(self) -> Dict[str, SystemFacade]:
        """从所有配置创建门面"""
        facades = {}
        for config in self._config_cache.values():
            if config.enabled:
                facade = self.create_from_config(config)
                facades[config.name] = facade
                self._instance_cache[config.name] = facade
        return facades

    def get_or_create(self, facade_name: str) -> SystemFacade:
        """获取或创建门面实例（单例模式）"""
        if facade_name in self._instance_cache:
            return self._instance_cache[facade_name]

        config = self._config_cache.get(facade_name)
        if not config:
            raise ValueError(f"No configuration found for facade: {facade_name}")

        facade = self.create_from_config(config)
        self._instance_cache[facade_name] = facade
        return facade

    def load_config_from_file(self, file_path: Union[str, Path]) -> None:
        """从文件加载门面配置"""
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

        # 解析门面配置
        if "facades" in data:
            for facade_data in data["facades"]:
                config = FacadeConfig(**facade_data)
                # 环境变量替换
                config = self._resolve_environment_variables(config)
                self._config_cache[config.name] = config

    def load_config_from_dict(self, data: Dict) -> None:
        """从字典加载门面配置"""
        if "facades" in data:
            for facade_data in data["facades"]:
                config = FacadeConfig(**facade_data)
                config = self._resolve_environment_variables(config)
                self._config_cache[config.name] = config

    def register_config(self, config: FacadeConfig) -> None:
        """注册门面配置"""
        config = self._resolve_environment_variables(config)
        self._config_cache[config.name] = config

    def get_config(self, name: str) -> Optional[FacadeConfig]:
        """获取门面配置"""
        return self._config_cache.get(name)

    def list_configs(self) -> List[str]:
        """列出所有配置"""
        return list(self._config_cache.keys())

    def list_facade_types(self) -> List[str]:
        """列出所有可用的门面类型"""
        return list(self.FACADE_TYPES.keys())

    def register_facade_type(self, name: str, facade_class: Type[SystemFacade]) -> None:
        """注册新的门面类型"""
        self.FACADE_TYPES[name] = facade_class

    def _apply_config(self, facade: SystemFacade, config: FacadeConfig) -> None:
        """应用配置到门面"""
        # 这里可以根据配置参数调整门面行为
        # 例如设置特定的参数值
        for key, value in config.parameters.items():
            if hasattr(facade, key):
                setattr(facade, key, value)

    def _resolve_environment_variables(self, config: FacadeConfig) -> FacadeConfig:
        """解析环境变量"""
        # 解析参数中的环境变量
        resolved_params = {}
        for key, value in config.parameters.items():
            if isinstance(value, str) and value.startswith("$"):
                env_var = value[1:]
                env_value = os.getenv(env_var)
                if env_value is not None:
                    # 尝试转换类型
                    resolved_params[key] = self._convert_type(env_value)
                else:
                    resolved_params[key] = value
            else:
                resolved_params[key] = value

        config.parameters = resolved_params

        # 设置环境
        if not config.environment:
            config.environment = self.default_environment

        return config

    def _convert_type(self, value: str) -> Union[str, int, float, bool]:
        """尝试转换字符串值到适当的类型"""
        # 布尔值
        if value.lower() in ["true", "false"]:
            return value.lower() == "true"

        # 整数
        try:
            return int(value)
        except ValueError:
            pass

        # 浮点数
        try:
            return float(value)
        except ValueError:
            pass

        # 默认返回字符串
        return value

    def create_default_configs(self) -> None:
        """创建默认配置"""
        # 主系统门面配置
        main_config = FacadeConfig(
            name="main_facade",
            facade_type="main",
            enabled=True,
            auto_initialize=True,
            parameters={
                "timeout": 30,
                "retry_attempts": 3,
                "enable_metrics": True,
            },
        )
        self._config_cache["main_facade"] = main_config

        # 预测门面配置
        prediction_config = FacadeConfig(
            name="prediction_facade",
            facade_type="prediction",
            enabled=True,
            auto_initialize=True,
            parameters={
                "default_model": "neural_network",
                "cache_ttl": 600,
                "batch_size": 100,
            },
        )
        self._config_cache["prediction_facade"] = prediction_config

        # 数据收集门面配置
        data_config = FacadeConfig(
            name="data_collection_facade",
            facade_type="data_collection",
            enabled=True,
            auto_initialize=True,
            parameters={
                "batch_size": 50,
                "enable_compression": True,
                "backup_enabled": True,
            },
        )
        self._config_cache["data_collection_facade"] = data_config

        # 分析门面配置
        analytics_config = FacadeConfig(
            name="analytics_facade",
            facade_type="analytics",
            enabled=True,
            auto_initialize=False,  # 按需初始化
            parameters={
                "retention_days": 90,
                "aggregation_interval": 3600,
            },
        )
        self._config_cache["analytics_facade"] = analytics_config

        # 通知门面配置
        notification_config = FacadeConfig(
            name="notification_facade",
            facade_type="notification",
            enabled=True,
            auto_initialize=True,
            parameters={
                "default_channel": "email",
                "queue_size": 1000,
                "retry_failed": True,
            },
        )
        self._config_cache["notification_facade"] = notification_config

    def save_config_to_file(self, file_path: Union[str, Path]) -> None:
        """保存配置到文件"""
        file_path = Path(file_path)

        data = {
            "facades": [
                {
                    "name": config.name,
                    "facade_type": config.facade_type,
                    "enabled": config.enabled,
                    "auto_initialize": config.auto_initialize,
                    "subsystems": config.subsystems,
                    "parameters": config.parameters,
                    "environment": config.environment,
                }
                for config in self._config_cache.values()
            ]
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

    def clear_cache(self) -> None:
        """清空实例缓存"""
        self._instance_cache.clear()

    def get_cached_instance(self, name: str) -> Optional[SystemFacade]:
        """获取缓存的实例"""
        return self._instance_cache.get(name)


# 全局门面工厂实例
facade_factory = FacadeFactory()

# 创建默认配置
facade_factory.create_default_configs()
