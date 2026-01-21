"""
FootballPrediction 日志管理工具
提供统一的日志配置和管理
"""

import logging
import logging.handlers
import os
from pathlib import Path
from typing import Optional


def setup_logger(
    name: str = 'football_prediction',
    log_file: Optional[str] = None,
    level: Optional[str] = None,
    config=None
) -> logging.Logger:
    """设置日志记录器"""

    # 使用 config_unified 或默认配置
    if config is None:
        try:
            from src.config_unified import get_settings
            settings = get_settings()
            log_level = settings.log_level
            logs_dir = Path("logs")
        except Exception:
            # 默认配置
            log_level = os.getenv("LOG_LEVEL", "INFO")
            logs_dir = Path("logs")
    else:
        log_level = level or config.logging.level
        logs_dir = config.paths.logs_dir

    if level is None:
        level = log_level

    # 创建logger
    logger = logging.getLogger(name)
    logger.setLevel(getattr(logging, level.upper()))

    # 避免重复添加handler
    if logger.handlers:
        return logger

    # 创建formatter
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

    # 控制台handler
    console_handler = logging.StreamHandler()
    console_handler.setLevel(getattr(logging, level.upper()))
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    # 文件handler
    if log_file is None:
        log_file = "football_prediction.log"

    log_path = logs_dir / log_file
    log_path.parent.mkdir(parents=True, exist_ok=True)

    file_handler = logging.handlers.RotatingFileHandler(
        log_path,
        maxBytes=10 * 1024 * 1024,  # 10MB
        backupCount=5,
        encoding='utf-8'
    )
    file_handler.setLevel(logging.DEBUG)  # 文件记录所有级别
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)

    return logger


def get_logger(name: str) -> logging.Logger:
    """获取logger实例"""
    return logging.getLogger(name)