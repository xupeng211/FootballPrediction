from typing import Optional

import sys
from pathlib import Path

from .core.path_manager import PathManager
from .utils.warning_filters import setup_warning_filters

"""
足球预测系统主模块
Football Prediction System Main Module

提供系统初始化和基础配置功能.
Provides system initialization and basic configuration functions.
"""

# 🔧 路径配置 - 解决Python路径问题
try:
    # 添加src到Python路径
    src_path = Path(__file__).parent
    if str(src_path) not in sys.path:
        sys.path.insert(0, str(src_path))

    # 使用路径管理器
    path_manager = PathManager()
    path_manager.setup_paths()
except ImportError:
    # 如果路径管理器不可用,至少保证基本路径配置
    pass

    # 配置警告过滤器
    setup_warning_filters()

# 版本信息
__version__ = "2.0.0"
__author__ = "Football Prediction Team"
__description__ = "基于机器学习的足球比赛结果预测系统"

# 导出主要组件
__all__ = [
    "__version__",
    "__author__",
    "__description__",
    "PathManager",
    "setup_warning_filters",
]
