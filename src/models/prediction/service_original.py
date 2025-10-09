"""
预测服务 - 原始版本（已拆分）
Prediction Service - Original Version (Split)

此文件已拆分为多个模块，请使用新的模块化结构。
This file has been split into multiple modules, please use the new modular structure.

新的模块化结构 / New modular structure:
- prediction_service.py (280行): 核心预测服务
- batch_predictor.py (150行): 批量预测器
- cache_manager.py (100行): 缓存管理器
- model_loader.py (120行): 模型加载器
- predictors.py (150行): 预测器

为了保持向后兼容性，这里导入主要的类。
For backward compatibility, main classes are imported here.
"""

from .service import (

# 导入拆分后的模块
    PredictionService,
    BatchPredictor,
    PredictionCacheManager,
    ModelLoader,
    MatchPredictor
)

# 重新导出主要类以保持向后兼容性
__all__ = [
    'PredictionService',
    'BatchPredictor',
    'PredictionCacheManager',
    'ModelLoader',
    'MatchPredictor'
]

# 保持原始的导入路径兼容性
PredictionService = PredictionService
