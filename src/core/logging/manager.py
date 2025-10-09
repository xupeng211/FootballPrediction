"""
日志管理器
Logging Manager
"""




class LoggerManager:
    """日志管理器"""

    _loggers: Dict[str, StructuredLogger] = {}
    _config: Dict[str, Any] = {}

    @classmethod
    def configure(
        cls,
        level: LogLevel = LogLevel.INFO,
        enable_json: bool = True,
        log_dir: str = "logs",
        **kwargs,
    ):
        """配置日志系统"""
        cls._config = {
            "level": level,
            "enable_json": enable_json,
            "log_dir": log_dir,
            **kwargs,
        }

        # 确保日志目录存在
        os.makedirs(log_dir, exist_ok=True)

    @classmethod
    def get_logger(
        cls, name: str, category: LogCategory = LogCategory.API, **kwargs
    ) -> StructuredLogger:
        """获取日志器"""
        key = f"{name}:{category.value}"

        if key not in cls._loggers:
            # 合并配置
            config = cls._config.copy()
            config.update(kwargs)

            # 创建日志器 - 过滤掉不支持的参数
            supported_params = {
                "level",
                "enable_json",
                "enable_console",
                "enable_file",
                "log_file",
            }
            filtered_config = {k: v for k, v in config.items() if k in supported_params}

            cls._loggers[key] = StructuredLogger(
                name=name, category=category, **filtered_config
            )

        return cls._loggers[key]

    @classmethod
    def get_all_loggers(cls) -> Dict[str, StructuredLogger]:
        """获取所有日志器"""
        return cls._loggers.copy()

    @classmethod
    def shutdown(cls):
        """关闭日志系统"""
        for logger in cls._loggers.values():
            for handler in logger.logger.handlers:
                handler.close()
        cls._loggers.clear()


# 便捷函数
def get_logger(name: str, category: LogCategory = LogCategory.API) -> StructuredLogger:
    """获取日志器的便捷函数"""
    return LoggerManager.get_logger(name, category)
import os

from .loggers import StructuredLogger

