"""
AICultureKit 核心功能模块

提供系统核心功能，包括：
- 配置管理
- 日志系统
- 异常处理
- 基础工具类
"""

import logging
from pathlib import Path
from typing import Any, Dict


class Config:
    """配置管理类 - 提供统一的配置读写和持久化机制"""

    def __init__(self):
        # 配置文件存储在用户主目录下，避免权限问题
        self.config_dir = Path.home() / ".aiculturekit"
        self.config_file = self.config_dir / "config.json"
        self._config: Dict[str, Any] = {}
        self._load_config()

    def _load_config(self) -> None:
        """加载配置文件 - 自动处理文件不存在或格式错误的情况"""
        if self.config_file.exists():
            import json

            try:
                with open(self.config_file, "r", encoding="utf-8") as f:
                    self._config = json.load(f)
            except Exception as e:
                # 配置文件损坏时记录警告，但不中断程序执行
                logging.warning(f"配置文件加载失败: {e}")

    def get(self, key: str, default: Any = None) -> Any:
        """获取配置项 - 支持默认值，确保程序健壮性"""
        return self._config.get(key, default)

    def set(self, key: str, value: Any) -> None:
        """设置配置项 - 仅更新内存中的配置，需调用save()持久化"""
        self._config[key] = value

    def save(self) -> None:
        """保存配置到文件 - 自动创建目录，确保配置持久化"""
        import json

        # 确保配置目录存在，parents=True递归创建父目录
        self.config_dir.mkdir(parents=True, exist_ok=True)
        with open(self.config_file, "w", encoding="utf-8") as f:
            # ensure_ascii=False保证中文字符正确显示
            json.dump(self._config, f, ensure_ascii=False, indent=2)


class Logger:
    """日志管理类"""

    @staticmethod
    def setup_logger(name: str, level: str = "INFO") -> logging.Logger:
        """设置日志器"""
        logger = logging.getLogger(name)
        logger.setLevel(getattr(logging, level.upper()))

        if not logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter(
                "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
            )
            handler.setFormatter(formatter)
            logger.addHandler(handler)

        return logger


class AICultureKitError(Exception):
    """AICultureKit基础异常类"""

    pass


class ConfigError(AICultureKitError):
    """配置相关异常"""

    pass


class DataError(AICultureKitError):
    """数据处理异常"""

    pass


# 全局配置实例
config = Config()

# 默认日志器
logger = Logger.setup_logger("aiculturekit")

__all__ = [
    "Config",
    "Logger",
    "AICultureKitError",
    "ConfigError",
    "DataError",
    "config",
    "logger",
]
