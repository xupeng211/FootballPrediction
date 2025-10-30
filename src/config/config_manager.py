"""
配置管理器模块 - Phase 4B实现

提供配置管理和处理功能:
- 配置文件加载和解析
- 环境变量管理和验证
- 配置值类型转换和验证
- 多环境配置支持
"""

import base64
import logging
import os
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime
from typing import Optional, Union, Callable, Any, List, Dict

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

    def __init__(self, file_path: str):
        self.file_path = file_path

    async def load(self) -> Dict[str, Any]:
        """从文件加载配置"""
        try:
            with open(self.file_path, 'r') as f:
                content = f.read()
            # 简化处理：假设文件包含有效的Python字典
            return eval(content)  # 在实际环境中应该使用更安全的方法
        except Exception as e:
            logger.error(f"Failed to load config from {self.file_path}: {e}")
            return {}

    async def save(self, config: Dict[str, Any]) -> bool:
        """保存配置到文件"""
        try:
            with open(self.file_path, 'w') as f:
                f.write(str(config))
            return True
        except Exception as e:
            logger.error(f"Failed to save config to {self.file_path}: {e}")
            return False


class EnvironmentConfigSource(ConfigSource):
    """环境变量配置源"""

    async def load(self) -> Dict[str, Any]:
        """从环境变量加载配置"""
        return {
            key: value for key, value in os.environ.items()
        }

    async def save(self, config: Dict[str, Any]) -> bool:
        """保存配置到环境变量（只读）"""
        return False


@dataclass
class ConfigCache:
    """配置缓存"""
    data: Dict[str, Any] = None
    timestamp: datetime = None
    ttl: int = 300  # 5分钟缓存


class ConfigValidator:
    """配置验证器"""

    def __init__(self):
        self._rules: Dict[str, Callable[[Any], bool]] = {}

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


class ConfigManager:
    """配置管理器"""

    def __init__(self):
        self.sources: List[ConfigSource] = []
        self._config: Dict[str, Any] = {}
        self._validator = ConfigValidator()
        self._encryption_key = self._generate_encryption_key()

    def add_source(self, source: ConfigSource) -> None:
        """添加配置源"""
        self.sources.append(source)

    def get(self, key: str) -> Optional[Any]:
        """获取配置值"""
        return self._config.get(key)

    def set(self, key: str, value: Any) -> None:
        """设置配置值"""
        self._config[key] = value

    def _generate_encryption_key(self) -> str:
        """生成加密密钥"""
        return base64.b64encode(
            os.urandom(32)  # TODO: 将魔法数字 32 提取为常量
        ).decode()

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

    # 记录配置管理器状态
    logger.debug(
        f"Config manager {config_manager.__class__.__name__} initialized for environment: {env}"
    )

    # 根据环境返回不同的配置
    if env == "production":
        return {
            "database_url": os.getenv(
                "DATABASE_URL",
                "postgresql+asyncpg://user:pass@localhost/football_prediction_prod",
            ),
            "redis_url": os.getenv(
                "REDIS_URL", "redis://localhost:6379/0"  # TODO: 将魔法数字 6379 提取为常量
            ),
            "log_level": "INFO",
            "debug": False,
        }
    elif env == "test":
        return {
            "database_url": os.getenv(
                "DATABASE_URL",
                "postgresql+asyncpg://user:pass@localhost/football_prediction_test",
            ),
            "redis_url": os.getenv(
                "REDIS_URL", "redis://localhost:6379/1"  # TODO: 将魔法数字 6379 提取为常量
            ),
            "log_level": "DEBUG",
            "debug": True,
        }
    else:  # development
        return {
            "database_url": os.getenv(
                "DATABASE_URL",
                "postgresql+asyncpg://postgres:postgres@localhost/football_prediction",
            ),
            "redis_url": os.getenv(
                "REDIS_URL", "redis://localhost:6379/0"  # TODO: 将魔法数字 6379 提取为常量
            ),
            "log_level": "DEBUG",
            "debug": True,
        }