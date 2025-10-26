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

import os
import json
import yaml
from typing import Dict, Any, List, Optional, Union, Type, Callable
from datetime import datetime, timedelta
from pathlib import Path
from dataclasses import dataclass, field
from abc import ABC, abstractmethod
import asyncio
from functools import lru_cache
import logging
import base64
import hashlib

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

    def __init__(self, file_path: str, format: str = "json"):
        self.file_path = file_path
        self.format = format.lower()
        self._cache: dict = {}
        self._last_modified = None

    async def load(self) -> Dict[str, Any]:
        """从文件加载配置"""
        try:
            if not os.path.exists(self.file_path):
                return {}

            # 检查文件修改时间
            current_modified = os.path.getmtime(self.file_path)
            if self._last_modified == current_modified and self._cache:
                return self._cache

            with open(self.file_path, "r", encoding="utf-8") as f:
                if self.format == "json":
                    data = json.load(f)
                elif self.format == "yaml":
                    data = yaml.safe_load(f) or {}
                else:
                    data = {}

            self._cache = data
            self._last_modified = current_modified
            return data

        except Exception as e:
            logger.error(f"Failed to load config from {self.file_path}: {e}")
            return {}

    async def save(self, config: Dict[str, Any]) -> bool:
        """保存配置到文件"""
        try:
            os.makedirs(os.path.dirname(self.file_path), exist_ok=True)

            with open(self.file_path, "w", encoding="utf-8") as f:
                if self.format == "json":
                    json.dump(config, f, indent=2, ensure_ascii=False)
                elif self.format == "yaml":
                    yaml.dump(config, f, default_flow_style=False, allow_unicode=True)
                else:
                    return False

            self._cache = config
            self._last_modified = os.path.getmtime(self.file_path)
            return True

        except Exception as e:
            logger.error(f"Failed to save config to {self.file_path}: {e}")
            return False


class EnvironmentConfigSource(ConfigSource):
    """环境变量配置源"""

    def __init__(self, prefix: str = "APP_"):
        self.prefix = prefix.upper()
        self._cache: dict = {}

    async def load(self) -> Dict[str, Any]:
        """从环境变量加载配置"""
        config = {}

        for key, value in os.environ.items():
            if key.startswith(self.prefix):
                config_key = key[len(self.prefix) :].lower()

                # 尝试转换类型
                converted_value = self._convert_value(value)
                config[config_key] = converted_value

        self._cache = config
        return config

    async def save(self, config: Dict[str, Any]) -> bool:
        """保存配置到环境变量（只读实现）"""
        # 环境变量通常不通过程序保存
        return False

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
class ConfigCache:
    """配置缓存"""

    def __init__(self, ttl: int = 300):  # 5分钟TTL
        self._cache: Dict[str, Any] = {}
        self._timestamps: Dict[str, float] = {}
        self.ttl = ttl

    def get(self, key: str) -> Optional[Any]:
        """获取缓存值"""
        if key not in self._cache:
            return None

        timestamp = self._timestamps[key]
        if datetime.utcnow().timestamp() - timestamp > self.ttl:
            del self._cache[key]
            del self._timestamps[key]
            return None

        return self._cache[key]

    def set(self, key: str, value: Any) -> None:
        """设置缓存值"""
        self._cache[key] = value
        self._timestamps[key] = datetime.utcnow().timestamp()

    def clear(self) -> None:
        """清空缓存"""
        self._cache.clear()
        self._timestamps.clear()


class ConfigValidator:
    """配置验证器"""

    def __init__(self):
        self.rules: Dict[str, Dict[str, Any]] = {}
        self.errors: List[str] = []

    def add_rule(
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
    """配置管理器"""

    def __init__(self):
        self.sources: List[ConfigSource] = []
        self._config: Dict[str, Any] = {}
        self._watchers: List[Callable[[str, Any, Any], None]] = []
        self._cache = ConfigCache()
        self._validator = ConfigValidator()
        self._encryption_key = self._generate_encryption_key()

    def add_source(self, source: ConfigSource) -> None:
        """添加配置源"""
        if source not in self.sources:
            self.sources.append(source)

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

        return secrets.token_hex(32)

    @lru_cache(maxsize=1000)
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
            "port": 5432,
            "name": "football_prediction_dev",
        },
        "api": {"host": "localhost", "port": 8000, "cors_origins": ["*"]},
        "logging": {"level": "DEBUG", "format": "detailed"},
    }


def get_production_config() -> Dict[str, Any]:
    """获取生产环境配置"""
    return {
        "debug": False,
        "database": {
            "host": os.getenv("DB_HOST", "localhost"),
            "port": int(os.getenv("DB_PORT", "5432")),
            "name": os.getenv("DB_NAME", "football_prediction"),
        },
        "api": {
            "host": os.getenv("API_HOST", "0.0.0.0"),
            "port": int(os.getenv("API_PORT", "8000")),
            "cors_origins": os.getenv("CORS_ORIGINS", "").split(","),
        },
        "logging": {"level": "INFO", "format": "json"},
        "security": {"secret_key": os.getenv("SECRET_KEY", ""), "jwt_expiration": 3600},
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
_config_manager = None


def get_config_manager() -> ConfigManager:
    """获取全局配置管理器实例"""
    global _config_manager
    if _config_manager is None:
        _config_manager = get_default_config_manager()
    return _config_manager
