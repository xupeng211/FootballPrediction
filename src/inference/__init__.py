"""
Inference Service Module
统一的推理服务模块

提供模型加载、预测执行、缓存管理和热更新等核心功能。

Architecture:
    loader.py          - 异步模型加载器
    predictor.py       - 核心预测器
    feature_builder.py - 在线特征计算
    cache.py           - Redis缓存层
    hot_reload.py      - 热更新机制
    schemas.py         - API Schema定义
    errors.py          - 错误定义
"""

from .loader import ModelLoader
from .cache import PredictionCache
from .feature_builder import FeatureBuilder
from .hot_reload import HotReloadManager
from .schemas import (
    PredictionRequest,
    PredictionResponse,
    BatchPredictionRequest,
    BatchPredictionResponse,
    ModelInfo,
    ErrorResponse,
)
from .errors import (
    InferenceError,
    ModelLoadError,
    FeatureBuilderError,
    PredictionError,
    CacheError,
    HotReloadError,
)


# 延迟导入predictor以避免循环依赖
def get_predictor():
    from . import predictor

    return predictor.get_predictor()


__all__ = [
    # Core classes
    "ModelLoader",
    "FeatureBuilder",
    "PredictionCache",
    "HotReloadManager",
    "get_predictor",
    # Schemas
    "PredictionRequest",
    "PredictionResponse",
    "BatchPredictionRequest",
    "BatchPredictionResponse",
    "ModelInfo",
    "ErrorResponse",
    # Errors
    "InferenceError",
    "ModelLoadError",
    "FeatureBuilderError",
    "PredictionError",
    "CacheError",
    "HotReloadError",
]
