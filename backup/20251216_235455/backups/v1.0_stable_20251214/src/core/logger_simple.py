"""简化的日志管理工具
Simplified Logging Management Tool.
"""

import logging


def get_simple_logger(name: str, level: str = "INFO") -> logging.Logger:
    """获取简化日志器,避免循环依赖."""
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
