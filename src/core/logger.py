from typing import cast, Any, Optional, Union

"""
足球预测系统日志管理模块

提供统一的日志配置和管理功能。
"""

import logging


class Logger:
    """日志管理类"""

    @staticmethod
    def setup_logger(name: str, level: str = "INFO") -> logging.Logger:
        """设置日志器 - 创建具有标准格式的日志器"""
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


def get_logger(name: str, level: str = "INFO") -> logging.Logger:
    """获取日志器 - 全局函数，方便使用"""
    return Logger.setup_logger(name, level)


# 默认日志器
logger = Logger.setup_logger("footballprediction")
