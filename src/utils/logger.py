"""
FootballPrediction V7.0 日志管理工具
提供统一的日志配置和管理
"""

import logging
import logging.handlers
import os
from pathlib import Path
from typing import Optional
from src.core.config import get_config

def setup_logger(
    name: str = 'football_prediction',
    log_file: Optional[str] = None,
    level: Optional[str] = None,
    config=None
) -> logging.Logger:
    """设置日志记录器"""

    if config is None:
        config = get_config()

    if level is None:
        level = config.logging.level

    # 创建logger
    logger = logging.getLogger(name)
    logger.setLevel(getattr(logging, level.upper()))

    # 避免重复添加handler
    if logger.handlers:
        return logger

    # 创建formatter
    formatter = logging.Formatter(config.logging.format)

    # 控制台handler
    console_handler = logging.StreamHandler()
    console_handler.setLevel(getattr(logging, level.upper()))
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    # 文件handler
    if log_file is None:
        log_file = config.logging.file_name

    log_path = config.paths.logs_dir / log_file
    log_path.parent.mkdir(parents=True, exist_ok=True)

    file_handler = logging.handlers.RotatingFileHandler(
        log_path,
        maxBytes=config.logging.max_bytes,
        backupCount=config.logging.backup_count,
        encoding='utf-8'
    )
    file_handler.setLevel(logging.DEBUG)  # 文件记录所有级别
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)

    return logger

def get_logger(name: str) -> logging.Logger:
    """获取logger实例"""
    return logging.getLogger(name)