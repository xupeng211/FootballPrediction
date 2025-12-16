"""
推理模块 - Inference Module

提供真实的足球比赛预测功能，基于训练好的XGBoost模型。
支持模型加载、预测执行、结果缓存和热重载功能。
"""

import logging
import pickle
import joblib
from pathlib import Path
from typing import Dict, Any, Optional, Union, List
import numpy as np
import pandas as pd
from datetime import datetime
import hashlib

logger = logging.getLogger(__name__)


class ModelLoadError(Exception):
    """模型加载异常"""
    pass


class PredictionError(Exception):
    """预测异常"""
    pass


class Predictor:
    """
    真实预测器

    基于训练好的XGBoost模型进行足球比赛结果预测。
    支持1X2分类预测，输出各类别概率。
    """

    def __init__(self, model_path: Union[str, Path], feature_names: Optional[List[str]] = None):
        """
        初始化预测器

        Args:
            model_path: 模型文件路径
            feature_names: 特征名称列表，用于验证输入特征
        """
        self.model_path = Path(model_path)
        self.feature_names = feature_names
        self.model = None
        self.model_metadata = None
        self.model_loaded = False

        logger.info(f"初始化预测器: {self.model_path}")

    def load_model(self) -> bool:
        """
        从磁盘加载XGBoost模型

        Returns:
            bool: 加载成功返回True

        Raises:
            ModelLoadError: 模型加载失败时抛出
        """
        try:
            if not self.model_path.exists():
                raise ModelLoadError(f"模型文件不存在: {self.model_path}")

            # 加载模型
            if self.model_path.suffix in ['.pkl', '.pickle']:
                with open(self.model_path, 'rb') as f:
                    model_data = pickle.load(f)

                # 处理不同的模型格式
                if isinstance(model_data, dict):
                    # 如果是包含模型和元数据的字典
                    self.model = model_data.get('model')
                    self.model_metadata = model_data.get('metadata', {})
                else:
                    # 直接是模型对象
                    self.model = model_data
                    self.model_metadata = {}
            else:
                # 使用joblib加载
                model_data = joblib.load(self.model_path)
                if isinstance(model_data, dict):
                    self.model = model_data.get('model')
                    self.model_metadata = model_data.get('metadata', {})
                else:
                    self.model = model_data
                    self.model_metadata = {}

            if self.model is None:
                raise ModelLoadError("模型文件中未找到有效的模型对象")

            # 从元数据中提取特征名称（如果未提供）
            if not self.feature_names and 'feature_names' in self.model_metadata:
                self.feature_names = self.model_metadata['feature_names']

            self.model_loaded = True
            logger.info(f"模型加载成功: {self.model_path}")
            logger.info(f"模型类型: {type(self.model).__name__}")
            if self.feature_names:
                logger.info(f"特征数量: {len(self.feature_names)}")

            return True

        except Exception as e:
            error_msg = f"模型加载失败: {str(e)}"
            logger.error(error_msg)
            raise ModelLoadError(error_msg) from e

    def _validate_features(self, features: Union[np.ndarray, pd.DataFrame, List[float]]) -> np.ndarray:
        """
        验证和预处理输入特征

        Args:
            features: 输入特征，可以是numpy数组、pandas DataFrame或列表

        Returns:
            np.ndarray: 验证后的特征数组

        Raises:
            PredictionError: 特征验证失败时抛出
        """
        if not self.model_loaded:
            raise PredictionError("模型未加载，请先调用 load_model()")

        # 转换为numpy数组
        if isinstance(features, pd.DataFrame):
            feature_array = features.values
        elif isinstance(features, list):
            feature_array = np.array(features).reshape(1, -1)
        else:
            feature_array = np.array(features)

        # 确保是2D数组
        if feature_array.ndim == 1:
            feature_array = feature_array.reshape(1, -1)

        # 验证特征数量
        expected_features = len(self.feature_names) if self.feature_names else None
        if expected_features and feature_array.shape[1] != expected_features:
            raise PredictionError(
                f"特征数量不匹配: 期望 {expected_features}, 实际 {feature_array.shape[1]}"
            )

        # 检查NaN值
        if np.isnan(feature_array).any():
            logger.warning("检测到NaN值，将用0替换")
            feature_array = np.nan_to_num(feature_array, nan=0.0)

        return feature_array

    def predict(self, features: Union[np.ndarray, pd.DataFrame, List[float]]) -> Dict[str, Any]:
        """
        执行预测

        Args:
            features: 输入特征

        Returns:
            Dict[str, Any]: 预测结果，包含概率、预测类别等信息

        Raises:
            PredictionError: 预测失败时抛出
        """
        try:
            if not self.model_loaded:
                raise PredictionError("模型未加载，请先调用 load_model()")

            # 验证和预处理特征
            feature_array = self._validate_features(features)

            # 执行预测
            if hasattr(self.model, 'predict_proba'):
                probabilities = self.model.predict_proba(feature_array)[0]
                predicted_class = self.model.predict(feature_array)[0]
            else:
                raise PredictionError("模型不支持预测，请确保模型有predict_proba和predict方法")

            # 解析概率结果
            if len(probabilities) == 3:
                # 1X2分类: AWAY_WIN(0), DRAW(1), HOME_WIN(2)
                result = {
                    "away_win_prob": float(probabilities[0]),
                    "draw_prob": float(probabilities[1]),
                    "home_win_prob": float(probabilities[2]),
                    "predicted_class": int(predicted_class),
                    "predicted_outcome": self._class_to_outcome(predicted_class),
                    "probabilities": [float(p) for p in probabilities]
                }
            else:
                # 其他分类问题
                result = {
                    "predicted_class": int(predicted_class),
                    "probabilities": [float(p) for p in probabilities]
                }

            # 添加元数据
            result.update({
                "model_version": self.model_metadata.get("model_version", "unknown"),
                "prediction_time": datetime.now().isoformat(),
                "feature_count": feature_array.shape[1]
            })

            logger.info(f"预测完成: {result.get('predicted_outcome', predicted_class)}")
            return result

        except Exception as e:
            error_msg = f"预测失败: {str(e)}"
            logger.error(error_msg)
            raise PredictionError(error_msg) from e

    def _class_to_outcome(self, predicted_class: int) -> str:
        """
        将预测类别转换为比赛结果描述

        Args:
            predicted_class: 预测类别

        Returns:
            str: 比赛结果描述
        """
        outcome_map = {0: "AWAY_WIN", 1: "DRAW", 2: "HOME_WIN"}
        return outcome_map.get(predicted_class, "UNKNOWN")

    def get_model_info(self) -> Dict[str, Any]:
        """
        获取模型信息

        Returns:
            Dict[str, Any]: 模型信息
        """
        if not self.model_loaded:
            return {"status": "not_loaded"}

        return {
            "status": "loaded",
            "model_type": type(self.model).__name__,
            "model_path": str(self.model_path),
            "feature_count": len(self.feature_names) if self.feature_names else None,
            "feature_names": self.feature_names,
            "metadata": self.model_metadata
        }


class ModelLoader:
    """模型加载器"""

    def __init__(self, model_cache_dir: Optional[Union[str, Path]] = None):
        """
        初始化模型加载器

        Args:
            model_cache_dir: 模型缓存目录
        """
        self.model_cache_dir = Path(model_cache_dir) if model_cache_dir else Path("models")
        self.loaded_models: Dict[str, Predictor] = {}
        logger.info(f"模型加载器初始化完成，缓存目录: {self.model_cache_dir}")

    def load_model(self, model_name: str, model_path: Optional[Union[str, Path]] = None) -> bool:
        """
        加载模型

        Args:
            model_name: 模型名称
            model_path: 模型路径，如果为None则使用默认路径

        Returns:
            bool: 加载成功返回True
        """
        try:
            if model_path is None:
                model_path = self.model_cache_dir / f"{model_name}.pkl"
            else:
                model_path = Path(model_path)

            predictor = Predictor(model_path)
            predictor.load_model()

            self.loaded_models[model_name] = predictor
            logger.info(f"模型 {model_name} 加载成功")
            return True

        except Exception as e:
            logger.error(f"模型 {model_name} 加载失败: {str(e)}")
            return False

    def get_model(self, model_name: str) -> Optional[Predictor]:
        """
        获取已加载的模型

        Args:
            model_name: 模型名称

        Returns:
            Optional[Predictor]: 预测器实例，如果模型未加载则返回None
        """
        return self.loaded_models.get(model_name)

    def unload_model(self, model_name: str) -> bool:
        """
        卸载模型

        Args:
            model_name: 模型名称

        Returns:
            bool: 卸载成功返回True
        """
        if model_name in self.loaded_models:
            del self.loaded_models[model_name]
            logger.info(f"模型 {model_name} 已卸载")
            return True
        return False

    def list_loaded_models(self) -> List[str]:
        """
        获取已加载模型列表

        Returns:
            List[str]: 已加载的模型名称列表
        """
        return list(self.loaded_models.keys())


class PredictionCache:
    """预测结果缓存"""

    def __init__(self, default_ttl: int = 3600):
        """
        初始化缓存

        Args:
            default_ttl: 默认TTL（秒）
        """
        self.cache: Dict[str, Dict[str, Any]] = {}
        self.default_ttl = default_ttl
        logger.info("预测缓存初始化完成")

    def _generate_cache_key(self, features: np.ndarray, model_name: str) -> str:
        """
        生成缓存键

        Args:
            features: 特征数组
            model_name: 模型名称

        Returns:
            str: 缓存键
        """
        # 使用特征数据的哈希值和模型名称生成缓存键
        features_hash = hashlib.md5(features.tobytes()).hexdigest()
        return f"{model_name}:{features_hash}"

    def get(self, features: np.ndarray, model_name: str) -> Optional[Dict[str, Any]]:
        """
        获取缓存

        Args:
            features: 特征数组
            model_name: 模型名称

        Returns:
            Optional[Dict[str, Any]]: 缓存的预测结果
        """
        cache_key = self._generate_cache_key(features, model_name)

        if cache_key in self.cache:
            cache_entry = self.cache[cache_key]

            # 检查是否过期
            if datetime.now().timestamp() - cache_entry['timestamp'] < cache_entry['ttl']:
                logger.debug(f"缓存命中: {cache_key}")
                return cache_entry['result']
            else:
                # 清理过期缓存
                del self.cache[cache_key]

        return None

    def set(self, features: np.ndarray, model_name: str, result: Dict[str, Any], ttl: Optional[int] = None) -> None:
        """
        设置缓存

        Args:
            features: 特征数组
            model_name: 模型名称
            result: 预测结果
            ttl: 生存时间（秒）
        """
        cache_key = self._generate_cache_key(features, model_name)

        self.cache[cache_key] = {
            'result': result,
            'timestamp': datetime.now().timestamp(),
            'ttl': ttl if ttl is not None else self.default_ttl
        }

        logger.debug(f"缓存已设置: {cache_key}")

    def clear(self) -> None:
        """清空缓存"""
        self.cache.clear()
        logger.info("缓存已清空")


class HotReloadManager:
    """热重载管理器"""

    def __init__(self, model_loader: ModelLoader, check_interval: int = 60):
        """
        初始化热重载管理器

        Args:
            model_loader: 模型加载器引用
            check_interval: 检查间隔（秒）
        """
        self.model_loader = model_loader
        self.check_interval = check_interval
        self.enabled = False
        self.model_timestamps: Dict[str, float] = {}
        logger.info("热重载管理器初始化完成")

    def enable(self) -> None:
        """启用热重载"""
        self.enabled = True
        # 记录当前模型的时间戳
        for model_name in self.model_loader.list_loaded_models():
            predictor = self.model_loader.get_model(model_name)
            if predictor:
                self.model_timestamps[model_name] = predictor.model_path.stat().st_mtime
        logger.info("热重载已启用")

    def disable(self) -> None:
        """禁用热重载"""
        self.enabled = False
        logger.info("热重载已禁用")

    def check_and_reload(self) -> List[str]:
        """
        检查并重载更新的模型

        Returns:
            List[str]: 重载的模型名称列表
        """
        reloaded_models = []

        if not self.enabled:
            return reloaded_models

        for model_name in self.model_loader.list_loaded_models():
            predictor = self.model_loader.get_model(model_name)
            if predictor and predictor.model_path.exists():
                current_timestamp = predictor.model_path.stat().st_mtime

                if model_name in self.model_timestamps:
                    if current_timestamp > self.model_timestamps[model_name]:
                        # 模型文件已更新，重新加载
                        if self.model_loader.load_model(model_name, predictor.model_path):
                            reloaded_models.append(model_name)
                            self.model_timestamps[model_name] = current_timestamp
                            logger.info(f"模型 {model_name} 已热重载")
                else:
                    self.model_timestamps[model_name] = current_timestamp

        return reloaded_models


# 全局实例
_model_loader = ModelLoader()
_prediction_cache = PredictionCache()
_hot_reload_manager = HotReloadManager(_model_loader)


def get_predictor(model_path: Union[str, Path], feature_names: Optional[List[str]] = None) -> Predictor:
    """
    获取预测器实例

    Args:
        model_path: 模型文件路径
        feature_names: 特征名称列表

    Returns:
        Predictor: 预测器实例
    """
    predictor = Predictor(model_path, feature_names)
    predictor.load_model()
    return predictor


def get_model_loader() -> ModelLoader:
    """获取模型加载器实例"""
    return _model_loader


def get_prediction_cache() -> PredictionCache:
    """获取预测缓存实例"""
    return _prediction_cache


def get_hot_reload_manager() -> HotReloadManager:
    """获取热重载管理器实例"""
    return _hot_reload_manager


def predict_match(
    features: Union[np.ndarray, pd.DataFrame, List[float]],
    model_path: Union[str, Path],
    feature_names: Optional[List[str]] = None,
    use_cache: bool = True
) -> Dict[str, Any]:
    """
    便捷函数：执行单次预测

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
        if isinstance(features, pd.DataFrame):
            feature_array = features.values
        elif isinstance(features, list):
            feature_array = np.array(features).reshape(1, -1)
        else:
            feature_array = np.array(features)
            if feature_array.ndim == 1:
                feature_array = feature_array.reshape(1, -1)

        # 检查缓存
        if use_cache:
            cache_result = _prediction_cache.get(feature_array, Path(model_path).stem)
            if cache_result:
                logger.info("使用缓存预测结果")
                return cache_result

        # 执行预测
        result = predictor.predict(feature_array)

        # 缓存结果
        if use_cache:
            _prediction_cache.set(feature_array, Path(model_path).stem, result)

        return result

    except Exception as e:
        logger.error(f"预测失败: {str(e)}")
        raise
