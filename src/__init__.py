"""
FootballPrediction - 基于机器学习的足球比赛结果预测系统

覆盖全球主要赛事的足球比赛结果预测，提供数据分析、特征工程、
模型训练和预测等核心功能模块。
"""

__version__ = "0.1.0"
__author__ = os.getenv("__INIT_____AUTHOR___9")
__email__ = os.getenv("__INIT_____EMAIL___9")

import os

# 🔧 设置警告过滤器 - 确保测试日志清洁，不再充满第三方库警告
try:
    from .utils.warning_filters import setup_warning_filters

    setup_warning_filters()
except ImportError:
    # 如果警告过滤器模块不可用，不影响正常功能
    pass

# 延迟导入核心模块 - 避免在导入时加载所有模块
if os.getenv("MINIMAL_API_MODE", "false").lower() == "true":
    __all__ = []
else:
    # 使用延迟导入，只在真正需要时加载
    __all__ = [
        "core",
        "models",
        "services",
        "utils",
    ]

def _lazy_import():
    """延迟导入模块"""
    from . import core, models, services, utils
    return core, models, services, utils

# 提供一个属性来按需加载
class LazyImporter:
    def __init__(self):
        self._modules = None

    def __getattr__(self, name):
        if self._modules is None:
            self._modules = _lazy_import()
        return getattr(self._modules, name)

# 创建延迟导入实例
_lazy_importer = LazyImporter()
