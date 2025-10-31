"""
FootballPrediction - 基于机器学习的足球比赛结果预测系统

覆盖全球主要赛事的足球比赛结果预测,提供数据分析,特征工程,
模型训练和预测等核心功能模块.
"""

__version__ = "0.1.0"
__author__ = "FootballPrediction Team"
__email__ = "football@prediction.com"

import os
import sys
from pathlib import Path

# 🔧 路径配置 - 解决Python路径问题
try:
    # 添加src到Python路径
    src_path = Path(__file__).parent
    if str(src_path) not in sys.path:
        sys.path.insert(0, str(src_path))

    # 使用路径管理器
    from .core.path_manager import PathManager
    path_manager = PathManager()
    path_manager.setup_src_path()

except ImportError as e:
    # 如果路径管理器不可用，至少保证基本路径配置
    src_path = Path(__file__).parent
    if str(src_path) not in sys.path:
        sys.path.insert(0, str(src_path))
    print(f"警告: 路径管理器不可用 ({e}), 使用基本路径配置")

# 🔧 设置警告过滤器 - 确保测试日志清洁,不再充满第三方库警告
try:
    from .utils.warning_filters import setup_warning_filters
    setup_warning_filters()
except ImportError:
    # 如果警告过滤器模块不可用,不影响正常功能
    pass

# 导入核心模块 - 使用延迟导入避免循环依赖
if os.getenv("MINIMAL_API_MODE", "false").lower() == "true":
    __all__ = []
else:
    try:
        # 使用动态导入避免依赖问题
        import importlib

        # 尝试导入核心模块
        modules_to_import = []

        try:
            importlib.import_module('.services', __name__)
            modules_to_import.append('services')
        except ImportError as e:
            print(f"警告: services模块导入失败: {e}")

        try:
            importlib.import_module('.core', __name__)
            modules_to_import.append('core')
        except ImportError as e:
            print(f"警告: core模块导入失败: {e}")

        try:
            importlib.import_module('.models', __name__)
            modules_to_import.append('models')
        except ImportError as e:
            print(f"警告: models模块导入失败: {e}")

        try:
            importlib.import_module('.utils', __name__)
            modules_to_import.append('utils')
        except ImportError as e:
            print(f"警告: utils模块导入失败: {e}")

        __all__ = modules_to_import

        # 如果成功导入了模块，将它们添加到当前命名空间
        for module_name in modules_to_import:
            globals()[module_name] = importlib.import_module(f'.{module_name}', __name__)

    except Exception as e:
        print(f"警告: 模块导入过程中出现错误: {e}")
        __all__ = []
