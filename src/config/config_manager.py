"""
配置管理器模块 - Phase 4B实现

提供配置管理和处理功能：
- 配置文件加载和解析
- 环境变量管理和验证
- 配置值类型转换和验证
- 配置缓存和热重载
- 多环境配置支持
- 配置安全加密
- 配置依赖注入集成
- 配置变更通知机制
"""

import base64
import json
import logging
import os
from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime
from functools import lru_cache
from typing import Any, Callable, Dict, List, Optional, Type, Union

import yaml

logger = logging.getLogger(__name__)


class ConfigSource(ABC):
    """抽象配置源"""

    @abstractmethod
    async def load(self) -> Dict[str, Any]:
        """加载配置数据"""
        pass

    @abstractmethod
    async def save(self, config: Dict[str, Any]) -> bool:
        """保存配置数据"""
        pass


class FileConfigSource(ConfigSource):
    """文件配置源"""

class EnvironmentConfigSource(ConfigSource):
    """环境变量配置源"""

@dataclass
class ConfigCache:
    """配置缓存"""

class ConfigValidator:
    """配置验证器"""

class ConfigManager:
    """配置管理器"""

# 默认配置工厂函数
# 配置管理器实例（单例模式）
_config_manager = None


    def __init__(self):
        self.sources: List[ConfigSource] = []
        self._config: Dict[str, Any] = {}
        self._watchers: List[Callable[[str, Any, Any], None]] = []
        self._cache = ConfigCache()
        self._validator = ConfigValidator()
        self._encryption_key = self._generate_encryption_key()

    def _convert_value(self, value: str) -> Union[str, int, float, bool]:
        """尝试转换值的类型"""
        # 布尔值
        if value.lower() in ("true", "false"):
            return value.lower() == "true"

        # 数字
        try:
            if "." in value:
                return float(value)
            else:
                return int(value)
        except ValueError:
            pass

        return value


@dataclass
# TODO: 方法 def get 过长(21行)，建议拆分
    def get(self, key: str, default: Any = None) -> Any:
        """获取配置值"""
        # 先检查缓存
        cached_value = self._cache.get(key)
        if cached_value is not None:
            return cached_value

        # 从配置中获取
        keys = key.split(".")
        value = self._config

        try:
            for k in keys:
                value = value[k]

            # 缓存结果
            self._cache.set(key, value)
            return value
        except (KeyError, TypeError):
            return default

    def set(self, key: str, value: Any) -> None:
        """设置配置值"""
        old_value = self.get(key)
        keys = key.split(".")
        config = self._config

        # 创建嵌套字典结构
        for k in keys[:-1]:
            if k not in config:
                config[k] = {}
            config = config[k]

        config[keys[-1]] = value

        # 清除缓存
        self._cache.clear()

        # 通知监听器
        self.notify_watchers(key, old_value, value)

    def clear(self) -> None:
        """清空缓存"""
        self._cache.clear()
        self._timestamps.clear()


class ConfigValidator:
    def add_rule(
        """TODO: 添加函数文档"""
        self, key: str, validator: Callable[[Any], bool], message: str
    ) -> None:
        """添加验证规则"""
        self.rules[key] = {"validator": validator, "message": message}

    def validate(self, config: Dict[str, Any]) -> bool:
        """验证配置"""
        self.errors = []

        for key, rule in self.rules.items():
            value = self._get_nested_value(config, key)

            try:
                if not rule["validator"](value):
                    self.errors.append(f"{key}: {rule['message']}")
            except Exception as e:
                self.errors.append(f"{key}: 验证错误 - {str(e)}")

        return len(self.errors) == 0

    def _get_nested_value(self, config: Dict[str, Any], key: str) -> Any:
        """获取嵌套配置值"""
        keys = key.split(".")
        value = config

        try:
            for k in keys:
                value = value[k]
            return value
        except (KeyError, TypeError):
            return None


class ConfigManager:
    def add_source(self, source: ConfigSource) -> None:
        """添加配置源"""
        if source not in self.sources:
            self.sources.append(source)

# TODO: 方法 def remove_source 过长(39行)，建议拆分
    def remove_source(self, source: ConfigSource) -> None:
        """移除配置源"""
        if source in self.sources:
            self.sources.remove(source)

    async def load_all(self) -> Dict[str, Any]:
        """加载所有配置源"""
        merged_config = {}

        for source in self.sources:
            try:
                source_config = await source.load()
                merged_config.update(source_config)
            except Exception as e:
                logger.error(f"Failed to load from source: {e}")
                continue

        self._config = merged_config

        # 验证配置
        if not self._validator.validate(merged_config):
            logger.warning(f"Configuration validation failed: {self._validator.errors}")

        return self._config

    async def save_all(self) -> bool:
        """保存配置到所有可写源"""
        success_count = 0

        for source in self.sources:
            try:
                if await source.save(self._config):
                    success_count += 1
            except Exception as e:
                logger.error(f"Failed to save to source: {e}")
                continue

        return success_count > 0

    def watch(self, callback: Callable[[str, Any, Any], None]) -> None:
        """添加配置变更监听器"""
        self._watchers.append(callback)

    def notify_watchers(self, key: str, old_value: Any, new_value: Any) -> None:
        """通知配置变更监听器"""
        for callback in self._watchers:
            try:
                callback(key, old_value, new_value)
            except Exception as e:
                logger.error(f"Watcher callback error: {e}")

    def encrypt_value(self, value: str) -> str:
        """加密配置值"""
        try:
            encoded = value.encode()
            key_bytes = self._encryption_key.encode()

            encrypted = bytearray()
            for i, byte in enumerate(encoded):
                key_byte = key_bytes[i % len(key_bytes)]
                encrypted.append(byte ^ key_byte)

            return base64.b64encode(encrypted).decode()
        except Exception:
            return ""

    def decrypt_value(self, encrypted_value: str) -> str:
        """解密配置值"""
        try:
            decoded = base64.b64decode(encrypted_value)
            key_bytes = self._encryption_key.encode()

            decrypted = bytearray()
            for i, byte in enumerate(decoded):
                key_byte = key_bytes[i % len(key_bytes)]
                decrypted.append(byte ^ key_byte)

            return decrypted.decode()
        except Exception:
            return ""

    def add_validation_rule(
        """TODO: 添加函数文档"""
        self, key: str, validator: Callable[[Any], bool], message: str
    ) -> None:
        """添加配置验证规则"""
        self._validator.add_rule(key, validator, message)

    def get_validation_errors(self) -> List[str]:
        """获取验证错误"""
        return self._validator.errors.copy()

    def _generate_encryption_key(self) -> str:
        """生成加密密钥"""
        # 简化实现 - 生产环境应该使用更安全的方式
        import secrets

        return secrets.token_hex(32)  # TODO: 将魔法数字 32 提取为常量

    @lru_cache(maxsize=1000)  # TODO: 将魔法数字 1000 提取为常量
    def get_type_safe(self, key: str, value_type: Type, default: Any = None) -> Any:
        """类型安全的配置获取"""
        value = self.get(key, default)

        if value is None:
            return default

        try:
            return value_type(value)
        except (ValueError, TypeError):
            return default


# 默认配置工厂函数
def get_default_config_manager() -> ConfigManager:
    """获取默认配置管理器"""
    manager = ConfigManager()

    # 添加环境变量源
    env_source = EnvironmentConfigSource("FOOTBALLPREDICTION_")
    manager.add_source(env_source)

    return manager


def get_development_config() -> Dict[str, Any]:
    """获取开发环境配置"""
    return {
        "debug": True,
        "database": {
            "host": "localhost",
            "port": 5432,  # TODO: 将魔法数字 5432 提取为常量
            "name": "football_prediction_dev",
        },
        "api": {"host": "localhost", "port": 8000, "cors_origins": ["*"]},  # TODO: 将魔法数字 8000 提取为常量
        "logging": {"level": "DEBUG", "format": "detailed"},
    }


def get_production_config() -> Dict[str, Any]:
    """获取生产环境配置"""
    return {
        "debug": False,
        "database": {
            "host": os.getenv("DB_HOST", "localhost"),
            "port": int(os.getenv("DB_PORT", "5432")),  # TODO: 将魔法数字 5432 提取为常量
            "name": os.getenv("DB_NAME", "football_prediction"),
        },
        "api": {
            "host": os.getenv("API_HOST", "0.0.0.0"),
            "port": int(os.getenv("API_PORT", "8000")),  # TODO: 将魔法数字 8000 提取为常量
            "cors_origins": os.getenv("CORS_ORIGINS", "").split(","),
        },
        "logging": {"level": "INFO", "format": "json"},
        "security": {"secret_key": os.getenv("SECRET_KEY", ""), "jwt_expiration": 3600},  # TODO: 将魔法数字 3600 提取为常量
    }


def get_config_by_env(env: str = "development") -> Dict[str, Any]:
    """根据环境获取配置"""
    if env == "production":
        return get_production_config()
    elif env == "development":
        return get_development_config()
    else:
        return get_development_config()


# 配置管理器实例（单例模式）
def get_config_manager() -> ConfigManager:
    """获取全局配置管理器实例"""
    global _config_manager
    if _config_manager is None:
        _config_manager = get_default_config_manager()
    return _config_manager
