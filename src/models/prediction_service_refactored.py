"""
prediction_service_refactored.py
Prediction_Service_Refactored

此文件已被拆分为多个模块以提供更好的组织结构。
This file has been split into multiple modules for better organization.

为了向后兼容，此文件重新导出所有模块中的类。
For backward compatibility, this file re-exports all classes from the modules.
"""


import warnings

from .models.prediction.refactored.cache import *  # type: ignore
from .models.prediction.refactored.prediction_service import *  # type: ignore
from .models.prediction.refactored.predictors import *  # type: ignore
from .models.prediction.refactored.validators import *  # type: ignore

warnings.warn(
    "直接从 prediction_service_refactored 导入已弃用。"
    "请从 models.prediction.refactored 导入相关类。",
    DeprecationWarning,
    stacklevel=2,
)

# 从新模块导入所有内容

# 导出所有类
__all__ = [  # type: ignore
    "PredictionService" "Predictors" "Validators" "Cache"
]
