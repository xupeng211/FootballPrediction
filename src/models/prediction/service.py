"""
预测服务 - 向后兼容性导入
Prediction Service - Backward Compatibility Import

此文件已拆分为模块化结构，为了保持向后兼容性，这里重新导出主要类。
This file has been split into a modular structure, main classes are re-exported here for backward compatibility.

新的模块化结构 / New modular structure:
- service/prediction_service.py: 核心预测服务
- service/batch_predictor.py: 批量预测器
- service/cache_manager.py: 缓存管理器
- service/model_loader.py: 模型加载器
- service/predictors.py: 预测器

使用新的模块化结构 / Use the new modular structure:
from src.models.prediction.service import PredictionService

或者使用原有的导入方式 / Or use the original import style:
from src.models.prediction.service import PredictionService  # 仍然有效
"""

from .service import PredictionService

# 导入拆分后的模块以保持向后兼容性

# 重新导出主要类
__all__ = ['PredictionService']
