"""
FootballPrediction - 基于机器学习的足球比赛结果预测系统

覆盖全球主要赛事的足球比赛结果预测,提供数据分析,特征工程,
模型训练和预测等核心功能模块.
"""

__version__ = "0.1.0"
__author__ = "FootballPrediction Team"
__email__ = "football@prediction.com"

import os

# 🔧 设置警告过滤器 - 确保测试日志清洁,不再充满第三方库警告
try:
    from .utils.warning_filters import setup_warning_filters

    setup_warning_filters()
except ImportError:
    # 如果警告过滤器模块不可用,不影响正常功能
    pass

# 导入核心模块
if os.getenv("MINIMAL_API_MODE", "false").lower() == "true":
    __all__ = []
else:
    from . import services  # runtime import for minimal mode
    from . import core, models, utils

    __all__ = [
        "core",
        "models",
        "services",
        "utils",
    ]
