#!/usr/bin/env python3
"""
推理模块兼容性接口 (Inference Module Facade)

提供与原始 src/inference.py 兼容的接口，确保现有代码无需修改。
采用 Facade 模式，将重构后的组件组合成统一接口。
"""

from datetime import datetime
import logging
from pathlib import Path
from typing import TYPE_CHECKING, Any, Dict, List, Optional, Union
import warnings

# Import numpy and pandas for type annotations
from .cache_manager import CacheEntry, CacheStats
from .cache_manager import PredictionCache as _InternalPredictionCache

# 导入重构后的组件，使用别名避免循环引用
from .model_loader import ModelLoader as _InternalModelLoader
from .model_loader import ModelLoadError, ModelMetadata
from .predictor import MatchPredictor, PredictionError

if TYPE_CHECKING:
    import numpy as np
    import pandas as pd

logger = logging.getLogger(__name__)

# ============================================================================
# 兼容性接口 - 保持与原始代码相同的类名和接口
# ============================================================================


class Predictor:
    """
    兼容性预测器类 (原始接口)

    为了保持向后兼容，此类提供与原始 Predictor 类相同的接口。
    内部使用重构后的 MatchPredictor 实现。
    """

    def __init__(self, model_path: str | Path, feature_names: list[str] | None = None):
        """
        初始化兼容性预测器

        Args:
            model_path: 模型文件路径
            feature_names: 特征名称列表，用于验证输入特征
        """
        # 创建重构后的组件
        self._model_loader = _InternalModelLoader()
        self._cache_manager = _InternalPredictionCache(
            enable_auto_cleanup=False
        )  # 禁用自动清理以保持兼容性
        self._model_name = "compatibility_model"

        # 加载模型
        try:
            self._model_loader.load_model(self._model_name, model_path)
        except ModelLoadError as e:
            # 保持原始异常类型
            raise ModelLoadError(f"模型加载失败: {e!s}") from e

        # 创建预测器
        self._predictor = MatchPredictor(
            model_loader=self._model_loader,
            cache_manager=self._cache_manager,
            default_model_name=self._model_name,
        )

        # 保持原始属性兼容性
        self.model_path = Path(model_path)
        self.feature_names = feature_names
        self.model_metadata = self._model_loader.get_model_metadata(self._model_name)
        self.model_loaded = True

        logger.info(f"兼容性预测器初始化完成: {model_path}")

    def load_model(self) -> bool:
        """
        加载模型（兼容性方法）

        Returns:
            bool: 加载成功返回True
        """
        # 模型在初始化时已经加载，直接返回成功
        return True

    def predict(self, features: Union[list[float], "np.ndarray", "pd.DataFrame"]) -> dict[str, Any]:
        """
        执行预测（兼容性方法）

        Args:
            features: 输入特征

        Returns:
            Dict[str, Any]: 预测结果
        """
        try:
            # 调用重构后的预测器
            result = self._predictor.predict(features, use_cache=False)  # 禁用缓存以保持兼容性

            # 转换为原始格式
            return {
                "away_win_prob": result.get("away_win_prob", 0.0),
                "draw_prob": result.get("draw_prob", 0.0),
                "home_win_prob": result.get("home_win_prob", 0.0),
                "predicted_class": result.get("predicted_class", 0),
                "predicted_outcome": result.get("predicted_outcome", "UNKNOWN"),
                "probabilities": result.get("probabilities", []),
                "model_version": result.get("model_version", "unknown"),
                "prediction_time": result.get("prediction_time", datetime.now().isoformat()),
                "feature_count": result.get("feature_count", 0),
            }


        except Exception as e:
            raise PredictionError(f"预测失败: {e!s}") from e

    def get_model_info(self) -> dict[str, Any]:
        """
        获取模型信息（兼容性方法）

        Returns:
            Dict[str, Any]: 模型信息
        """
        if not self.model_loaded:
            return {"status": "not_loaded"}

        return {
            "status": "loaded",
            "model_type": "xgboost",  # 保持原始格式
            "model_path": str(self.model_path),
            "feature_count": len(self.feature_names) if self.feature_names else None,
            "feature_names": self.feature_names,
            "metadata": self.model_metadata.__dict__ if self.model_metadata else {},
        }

    # 保持原始的私有方法（虽然不再使用，但为了兼容性）
    def _validate_features(self, features) -> "np.ndarray":
        """特征验证（兼容性方法，已弃用）"""
        warnings.warn("_validate_features is deprecated", DeprecationWarning, stacklevel=2)
        return features  # 直接返回，验证已在重构版本中完成

    def _class_to_outcome(self, predicted_class: int) -> str:
        """类别转换（兼容性方法，已弃用）"""
        warnings.warn("_class_to_outcome is deprecated", DeprecationWarning, stacklevel=2)
        outcome_map = {0: "AWAY_WIN", 1: "DRAW", 2: "HOME_WIN"}
        return outcome_map.get(predicted_class, "UNKNOWN")


class ModelLoader:
    """
    兼容性模型加载器类 (原始接口)

    为了保持向后兼容，此类提供与原始 ModelLoader 类相同的接口。
    内部使用重构后的 ModelLoader 实现。
    """

    def __init__(self, model_cache_dir: str | Path | None = None):
        """
        初始化兼容性模型加载器

        Args:
            model_cache_dir: 模型缓存目录
        """
        # 使用重构后的 ModelLoader
        self._model_loader = _InternalModelLoader(model_cache_dir)

        logger.info(f"兼容性模型加载器初始化完成，缓存目录: {model_cache_dir}")

    def load_model(self, model_name: str, model_path: str | Path | None = None) -> bool:
        """
        加载模型（兼容性方法）

        Args:
            model_name: 模型名称
            model_path: 模型路径

        Returns:
            bool: 加载成功返回True
        """
        try:
            # 内部创建重构后的 Predictor
            predictor = Predictor(
                model_path or f"{self._model_loader.get_cache_directory()}/{model_name}.pkl"
            )
            # 存储到内部映射中（模拟原始行为）
            if not hasattr(self, "_loaded_models"):
                self._loaded_models = {}
            self._loaded_models[model_name] = predictor
            return True
        except Exception as e:
            logger.exception(f"模型 {model_name} 加载失败: {e!s}")
            return False

    def get_model(self, model_name: str) -> Predictor | None:
        """
        获取已加载的模型（兼容性方法）

        Args:
            model_name: 模型名称

        Returns:
            Optional[Predictor]: 预测器实例
        """
        if hasattr(self, "_loaded_models"):
            return self._loaded_models.get(model_name)
        return None

    def unload_model(self, model_name: str) -> bool:
        """
        卸载模型（兼容性方法）

        Args:
            model_name: 模型名称

        Returns:
            bool: 卸载成功返回True
        """
        if hasattr(self, "_loaded_models") and model_name in self._loaded_models:
            del self._loaded_models[model_name]
            return True
        return False

    def list_loaded_models(self) -> list[str]:
        """
        获取已加载模型列表（兼容性方法）

        Returns:
            List[str]: 已加载的模型名称列表
        """
        if hasattr(self, "_loaded_models"):
            return list(self._loaded_models.keys())
        return []


class PredictionCache:
    """
    兼容性预测缓存类 (原始接口)

    为了保持向后兼容，此类提供与原始 PredictionCache 类相同的接口。
    内部使用重构后的 PredictionCache 实现。
    """

    def __init__(self, default_ttl: int = 3600):
        """
        初始化兼容性缓存

        Args:
            default_ttl: 默认TTL（秒）
        """
        self._cache = _InternalPredictionCache(default_ttl=default_ttl, enable_auto_cleanup=False)
        logger.info("兼容性预测缓存初始化完成")

    def _generate_cache_key(self, features: "np.ndarray", model_name: str) -> str:
        """生成缓存键（兼容性方法）"""
        import hashlib

        features_hash = hashlib.sha256(features.tobytes(), usedforsecurity=False).hexdigest()
        return f"{model_name}:{features_hash}"

    def get(self, features: "np.ndarray", model_name: str) -> dict[str, Any] | None:
        """
        获取缓存（兼容性方法）

        Args:
            features: 特征数组
            model_name: 模型名称

        Returns:
            Optional[Dict[str, Any]]: 缓存的预测结果
        """
        feature_list = features.flatten().tolist()
        return self._cache.get(features=feature_list, model_name=model_name)

    def set(
        self,
        features: "np.ndarray",
        model_name: str,
        result: dict[str, Any],
        ttl: int | None = None,
    ) -> None:
        """
        设置缓存（兼容性方法）

        Args:
            features: 特征数组
            model_name: 模型名称
            result: 预测结果
            ttl: 生存时间（秒）
        """
        feature_list = features.flatten().tolist()
        self._cache.set(features=feature_list, model_name=model_name, result=result, ttl=ttl)

    def clear(self) -> None:
        """清空缓存（兼容性方法）"""
        self._cache.clear()


class HotReloadManager:
    """
    兼容性热重载管理器类 (原始接口)

    为了保持向后兼容，此类提供与原始 HotReloadManager 类相同的接口。
    内部使用重构后的组件实现。
    """

    def __init__(self, model_loader: "ModelLoader", check_interval: int = 60):
        """
        初始化兼容性热重载管理器

        Args:
            model_loader: 模型加载器引用
            check_interval: 检查间隔（秒）
        """
        self._model_loader = model_loader._model_loader  # 使用内部重构版本
        self.check_interval = check_interval
        self.enabled = False
        self.model_timestamps = {}
        logger.info("兼容性热重载管理器初始化完成")

    def enable(self) -> None:
        """启用热重载（兼容性方法）"""
        self.enabled = True
        logger.info("兼容性热重载已启用")

    def disable(self) -> None:
        """禁用热重载（兼容性方法）"""
        self.enabled = False
        logger.info("兼容性热重载已禁用")

    def check_and_reload(self) -> list[str]:
        """
        检查并重载更新的模型（兼容性方法）

        Returns:
            List[str]: 重载的模型名称列表
        """
        # 简化实现，保持兼容性
        return []


# ============================================================================
# 全局实例和便捷函数（保持原始接口）
# ============================================================================

# 创建全局实例 - 延迟初始化以避免循环引用
_global_model_loader = None
_global_prediction_cache = None
_global_hot_reload_manager = None


def _get_global_model_loader():
    global _global_model_loader
    if _global_model_loader is None:
        _global_model_loader = ModelLoader()
    return _global_model_loader


def _get_global_prediction_cache():
    global _global_prediction_cache
    if _global_prediction_cache is None:
        _global_prediction_cache = PredictionCache()
    return _global_prediction_cache


def _get_global_hot_reload_manager():
    global _global_hot_reload_manager
    if _global_hot_reload_manager is None:
        _global_hot_reload_manager = HotReloadManager(_get_global_model_loader())
    return _global_hot_reload_manager


def get_predictor(model_path: str | Path, feature_names: list[str] | None = None) -> Predictor:
    """
    获取预测器实例（兼容性函数）

    Args:
        model_path: 模型文件路径
        feature_names: 特征名称列表

    Returns:
        Predictor: 预测器实例
    """
    return Predictor(model_path, feature_names)


def get_model_loader() -> ModelLoader:
    """获取模型加载器实例（兼容性函数）"""
    return _get_global_model_loader()


def get_prediction_cache() -> PredictionCache:
    """获取预测缓存实例（兼容性函数）"""
    return _get_global_prediction_cache()


def get_hot_reload_manager() -> HotReloadManager:
    """获取热重载管理器实例（兼容性函数）"""
    return _get_global_hot_reload_manager()


def predict_match(
    features: Union[list[float], "np.ndarray", "pd.DataFrame"],
    model_path: str | Path,
    feature_names: list[str] | None = None,
    use_cache: bool = True,
) -> dict[str, Any]:
    """
    便捷函数：执行单次预测（兼容性函数）

    Args:
        features: 输入特征
        model_path: 模型文件路径
        feature_names: 特征名称列表
        use_cache: 是否使用缓存

    Returns:
        Dict[str, Any]: 预测结果
    """
    try:
        # 获取预测器
        predictor = get_predictor(model_path, feature_names)

        # 验证特征格式
        if hasattr(features, "values"):  # DataFrame
            feature_array = features.values
        elif isinstance(features, list):
            feature_array = features
        else:  # numpy array
            feature_array = features.flatten()

        # 检查缓存
        if use_cache:
            cache_result = _get_global_prediction_cache().get(feature_array, Path(model_path).stem)
            if cache_result:
                logger.info("使用缓存预测结果")
                return cache_result

        # 执行预测
        result = predictor.predict(features)

        # 缓存结果
        if use_cache:
            _get_global_prediction_cache().set(feature_array, Path(model_path).stem, result)

        return result

    except Exception as e:
        logger.exception(f"预测失败: {e!s}")
        raise


# ============================================================================
# 重构后组件的导出（供新代码使用）
# ============================================================================

__all__ = [
    "CacheEntry",
    "CacheStats",
    "HotReloadManager",
    # 重构后组件（新代码推荐使用）
    "MatchPredictor",
    "ModelLoadError",
    "ModelLoader",
    "ModelMetadata",
    "PredictionCache",
    "PredictionError",
    # 兼容性接口
    "Predictor",
    "get_hot_reload_manager",
    "get_model_loader",
    "get_prediction_cache",
    "get_predictor",
    "predict_match",
]

# 版本信息
__version__ = "2.0.0-refactored"
__author__ = "FootballPrediction Team"
