"""
统一日志访问接口

提供 get_logger(name, level) 以兼容各处引用（例如监控与脚本）。
"""

import logging
from typing import Optional, cast

from .logger import Logger as _BaseLogger


def get_logger(name: str, level: Optional[str] = "INFO") -> logging.Logger:
    """获取指定名称的日志器。

    Args:
        name: 日志器名称（一般为 __name__）。
        level: 日志级别，默认为 "INFO"。

    Returns:
        logging.Logger: 已配置处理器与格式的日志器。
    """
    # 复用现有的标准化配置，确保输出一致
    return _BaseLogger.setup_logger(name, level or "INFO")
