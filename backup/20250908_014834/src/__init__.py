"""
AICultureKit - AI辅助文化产业工具包

一个专注于文化产业的AI辅助开发工具包，提供数据分析、内容生成、
用户画像等核心功能模块。
"""

__version__ = "0.1.0"
__author__ = "AICultureKit Team"
__email__ = "contact@aiculturekit.com"

# 导入核心模块
from . import core, models, services, utils

__all__ = [
    "core",
    "models",
    "services",
    "utils",
]
