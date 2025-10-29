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
import time
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

    data: Dict[str, Any] = None
    timestamp: datetime = None
    ttl: int = 300  # 5分钟缓存


class ConfigValidator:
    """配置验证器"""


class ConfigManager:
    """配置管理器"""

    def __init__(self):
        self.sources: List[ConfigSource] = []
        self.cache: Optional[ConfigCache] = None
        self.validator = ConfigValidator()
        self._config: Dict[str, Any] = {}
        self._encryption_key = self._generate_encryption_key()

    def add_rule(self, key: str, validator: Callable) -> None:
        """添加验证规则"""
        self.rules[key] = validator

    def validate(self, config: Dict[str, Any]) -> List[str]:
        """验证配置"""
        errors = []
        for key, validator in self.rules.items():
            if key in config:
                try:
                    validator(config[key])
                except Exception as e:
                    errors.append(f"Config key '{key}' validation failed: {e}")
        return errors


class ConfigManager:
    def add_source(self, source: ConfigSource) -> None:
        """添加配置源"""
        self.sources.append(source)

    def get(self, key: str, default: Any = None) -> Any:
        """获取配置值"""
        return self._config.get(key, default)

    def set(self, key: str, value: Any) -> None:
        """设置配置值"""
        self._config[key] = value

    def _generate_encryption_key(self) -> str:
        """生成加密密钥"""
        return base64.b64encode(
            os.urandom(32)  # TODO: 将魔法数字 32 提取为常量
        ).decode()  # TODO: 将魔法数字 32 提取为常量

    # TODO: 方法 def _convert_value 过长(50行)，建议拆分
    # TODO: 方法 def _convert_value 过长(50行)，建议拆分
# TODO: 方法 def _convert_value 过长(50行)，建议拆分
    def _convert_value(self, value: str) -> Union[str, int, float, bool]:
        """尝试转换值的类型"""
        # 布尔值
        if value.lower() in ("true", "false"):
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


# 全局配置管理器实例
_global_config_manager = None

def get_config_manager() -> ConfigManager:
    """获取全局配置管理器实例"""
    global _global_config_manager
    if _global_config_manager is None:
        _global_config_manager = ConfigManager()
    return _global_config_manager


def get_default_config_manager() -> ConfigManager:
    """获取默认配置管理器实例（别名）"""
    return get_config_manager()


def get_config_by_env(env: Optional[str] = None) -> Dict[str, Any]:
    """根据环境获取配置"""
    if env is None:
        env = os.getenv("ENV", "development")

    config_manager = get_config_manager()

    # 根据环境返回不同的配置
    if env == "production":
        return {
            "database_url": os.getenv("DATABASE_URL", "postgresql+asyncpg://user:pass@localhost/football_prediction_prod"),
            "redis_url": os.getenv("REDIS_URL", "redis://localhost:6379/0"),
            "log_level": "INFO",
            "debug": False,
        }
    elif env == "test":
        return {
            "database_url": os.getenv("DATABASE_URL", "postgresql+asyncpg://user:pass@localhost/football_prediction_test"),
            "redis_url": os.getenv("REDIS_URL", "redis://localhost:6379/1"),
            "log_level": "DEBUG",
            "debug": True,
        }
    else:  # development
        return {
            "database_url": os.getenv("DATABASE_URL", "postgresql+asyncpg://postgres:postgres@localhost/football_prediction"),
            "redis_url": os.getenv("REDIS_URL", "redis://localhost:6379/0"),
            "log_level": "DEBUG",
            "debug": True,
        }


class ConfigCache:
    """配置缓存类"""

    def __init__(self, ttl: int = 300):
        self._cache = {}
        self._timestamps = {}
        self._ttl = ttl

    def get(self, key: str) -> Optional[Any]:
        """获取缓存值"""
        if key in self._cache:
            if time.time() - self._timestamps[key] < self._ttl:
                return self._cache[key]
            else:
                del self._cache[key]
                del self._timestamps[key]
        return None

    def set(self, key: str, value: Any) -> None:
        """设置缓存值"""
        self._cache[key] = value
        self._timestamps[key] = time.time()

    def clear(self) -> None:
        """清空缓存"""
        self._cache.clear()
        self._timestamps.clear()


class ConfigValidator:
    """配置验证器"""

    def __init__(self):
        self._rules = {}

    def add_rule(self, key: str, validator: Callable[[Any], bool]) -> None:
        """添加验证规则"""
        self._rules[key] = validator

    def validate(self, config: Dict[str, Any]) -> List[str]:
        """验证配置"""
        errors = []
        for key, validator in self._rules.items():
            if key in config and not validator(config[key]):
                errors.append(f"Invalid value for {key}")
        return errors
