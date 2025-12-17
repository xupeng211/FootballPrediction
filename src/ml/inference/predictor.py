#!/usr/bin/env python3
"""
足球比赛预测器 (Match Predictor)

核心业务逻辑：接收特征 -> 调用模型 -> 返回概率。
依赖 ModelLoader 和 PredictionCache，遵循单一职责原则。
"""

import logging
import numpy as np
import pandas as pd
from datetime import datetime
from typing import Dict, Any, Optional, Union, List

from .model_loader import ModelLoader, ModelLoadError
from .cache_manager import PredictionCache

logger = logging.getLogger(__name__)


class PredictionError(Exception):
    """预测异常"""
    pass


class MatchPredictor:
    """
    足球比赛预测器 - 核心业务逻辑组件

    主要职责：
    1. 接收和验证输入特征
    2. 调用模型进行预测
    3. 解析和格式化预测结果
    4. 管理预测缓存

    设计原则：依赖注入、单一职责、易于测试
    """

    # 足球比赛结果映射
    OUTCOME_MAP = {
        0: "AWAY_WIN",
        1: "DRAW",
        2: "HOME_WIN"
    }

    def __init__(
        self,
        model_loader: ModelLoader,
        cache_manager: Optional[PredictionCache] = None,
        default_model_name: str = "xgboost_model"
    ):
        """
        初始化预测器

        Args:
            model_loader: 模型加载器实例
            cache_manager: 缓存管理器实例，如果为None则不使用缓存
            default_model_name: 默认使用的模型名称
        """
        self.model_loader = model_loader
        self.cache_manager = cache_manager
        self.default_model_name = default_model_name

        # 预测统计
        self._prediction_stats = {
            "total_predictions": 0,
            "successful_predictions": 0,
            "cache_hits": 0,
            "errors": 0,
            "start_time": datetime.now()
        }

        logger.info(f"预测器初始化完成，默认模型: {default_model_name}")

    def predict(
        self,
        features: Union[np.ndarray, pd.DataFrame, List[float]],
        model_name: Optional[str] = None,
        use_cache: bool = True,
        additional_params: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        执行足球比赛预测

        Args:
            features: 输入特征，可以是numpy数组、pandas DataFrame或列表
            model_name: 使用的模型名称，如果为None则使用默认模型
            use_cache: 是否使用缓存
            additional_params: 额外的预测参数

        Returns:
            Dict[str, Any]: 预测结果，包含概率、预测类别等信息

        Raises:
            PredictionError: 预测失败时抛出
        """
        model_name = model_name or self.default_model_name
        prediction_start_time = datetime.now()

        try:
            self._prediction_stats["total_predictions"] += 1

            # 转换特征为统一格式
            feature_list = self._convert_features_to_list(features)

            # 检查缓存
            if use_cache and self.cache_manager:
                cached_result = self.cache_manager.get(
                    features=feature_list,
                    model_name=model_name,
                    additional_params=additional_params
                )
                if cached_result:
                    self._prediction_stats["cache_hits"] += 1
                    logger.info(f"使用缓存预测结果 (模型: {model_name})")
                    return self._enrich_cached_result(cached_result, prediction_start_time)

            # 执行预测
            result = self._execute_prediction(feature_list, model_name, additional_params)

            # 缓存结果
            if use_cache and self.cache_manager:
                cache_success = self.cache_manager.set(
                    features=feature_list,
                    model_name=model_name,
                    result=result
                )
                if cache_success:
                    logger.debug(f"预测结果已缓存 (模型: {model_name})")

            # 增强结果信息
            enriched_result = self._enrich_result(result, model_name, prediction_start_time)

            self._prediction_stats["successful_predictions"] += 1
            logger.info(f"预测完成: {enriched_result.get('predicted_outcome')} (置信度: {enriched_result.get('confidence', 0):.3f})")

            return enriched_result

        except PredictionError:
            self._prediction_stats["errors"] += 1
            raise
        except Exception as e:
            self._prediction_stats["errors"] += 1
            error_msg = f"预测失败: {str(e)}"
            logger.error(error_msg)
            raise PredictionError(error_msg) from e

    def _convert_features_to_list(self, features: Union[np.ndarray, pd.DataFrame, List[float]]) -> List[float]:
        """
        将各种格式的特征转换为统一列表格式

        Args:
            features: 输入特征

        Returns:
            List[float]: 特征列表

        Raises:
            PredictionError: 特征格式无效时抛出
        """
        try:
            if isinstance(features, pd.DataFrame):
                # DataFrame -> 数组 -> 列表
                if features.shape[0] != 1:
                    logger.warning(f"DataFrame有多行数据，只使用第一行: {features.shape}")
                feature_array = features.iloc[0].values
                return feature_array.tolist()

            elif isinstance(features, np.ndarray):
                # 处理numpy数组
                if features.ndim == 1:
                    return features.tolist()
                elif features.ndim == 2 and features.shape[0] == 1:
                    return features[0].tolist()
                else:
                    logger.warning(f"numpy数组形状异常: {features.shape}，展平处理")
                    return features.flatten().tolist()

            elif isinstance(features, list):
                # 确保是数字列表
                if all(isinstance(x, (int, float)) for x in features):
                    return features
                else:
                    raise ValueError("列表包含非数字元素")

            else:
                raise ValueError(f"不支持的特征类型: {type(features)}")

        except Exception as e:
            raise PredictionError(f"特征格式转换失败: {str(e)}") from e

    def _execute_prediction(
        self,
        feature_list: List[float],
        model_name: str,
        additional_params: Optional[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        执行核心预测逻辑

        Args:
            feature_list: 特征列表
            model_name: 模型名称
            additional_params: 额外参数

        Returns:
            Dict[str, Any]: 原始预测结果

        Raises:
            PredictionError: 预测执行失败时抛出
        """
        # 获取模型
        model = self.model_loader.get_model(model_name)
        if model is None:
            raise PredictionError(f"模型未加载: {model_name}")

        # 获取模型元数据
        metadata = self.model_loader.get_model_metadata(model_name)
        if metadata is None:
            raise PredictionError(f"模型元数据缺失: {model_name}")

        # 验证特征数量
        if metadata.feature_names and len(feature_list) != len(metadata.feature_names):
            raise PredictionError(
                f"特征数量不匹配: 模型期望 {len(metadata.feature_names)}, 实际 {len(feature_list)}"
            )

        # 检查NaN值并处理
        feature_array = np.array(feature_list, dtype=float)
        if np.isnan(feature_array).any():
            logger.warning(f"检测到 {np.isnan(feature_array).sum()} 个NaN值，将用0替换")
            feature_array = np.nan_to_num(feature_array, nan=0.0)

        # 重塑为二维数组 (1, n_features)
        feature_2d = feature_array.reshape(1, -1)

        # 执行预测
        try:
            # 获取预测类别
            predicted_class = int(model.predict(feature_2d)[0])

            # 获取概率（如果模型支持）
            if hasattr(model, 'predict_proba'):
                probabilities = model.predict_proba(feature_2d)[0]
                probabilities = [float(p) for p in probabilities]
            else:
                logger.warning(f"模型 {model_name} 不支持概率预测，使用默认值")
                probabilities = [0.0] * 3  # 默认三分类

            # 构建基础结果
            result = {
                "predicted_class": predicted_class,
                "probabilities": probabilities,
                "feature_count": len(feature_list)
            }

            # 解析足球比赛特定的概率
            if len(probabilities) == 3:
                result.update({
                    "away_win_prob": probabilities[0],
                    "draw_prob": probabilities[1],
                    "home_win_prob": probabilities[2],
                    "predicted_outcome": self.OUTCOME_MAP.get(predicted_class, "UNKNOWN")
                })

            return result

        except Exception as e:
            raise PredictionError(f"模型预测执行失败: {str(e)}") from e

    def _enrich_result(
        self,
        result: Dict[str, Any],
        model_name: str,
        prediction_time: datetime
    ) -> Dict[str, Any]:
        """
        增强预测结果信息

        Args:
            result: 原始预测结果
            model_name: 模型名称
            prediction_time: 预测时间

        Returns:
            Dict[str, Any]: 增强后的预测结果
        """
        # 获取模型元数据
        metadata = self.model_loader.get_model_metadata(model_name) or {}

        # 计算置信度
        confidence = self._calculate_confidence(result.get("probabilities", []))

        enriched_result = result.copy()
        enriched_result.update({
            "model_name": model_name,
            "model_version": metadata.model_version,
            "prediction_time": prediction_time.isoformat(),
            "confidence": confidence,
            "processing_time_ms": (datetime.now() - prediction_time).total_seconds() * 1000
        })

        return enriched_result

    def _enrich_cached_result(self, cached_result: Dict[str, Any], prediction_time: datetime) -> Dict[str, Any]:
        """
        增强缓存结果信息

        Args:
            cached_result: 缓存的预测结果
            prediction_time: 当前预测时间

        Returns:
            Dict[str, Any]: 增强后的缓存结果
        """
        enriched_result = cached_result.copy()
        enriched_result.update({
            "prediction_time": prediction_time.isoformat(),
            "from_cache": True,
            "processing_time_ms": 0  # 缓存命中，处理时间为0
        })

        return enriched_result

    def _calculate_confidence(self, probabilities: List[float]) -> float:
        """
        计算预测置信度

        Args:
            probabilities: 概率列表

        Returns:
            float: 置信度 (0-1)
        """
        if not probabilities:
            return 0.0

        # 使用最大概率作为置信度
        max_prob = max(probabilities)
        return float(max_prob)

    def get_prediction_stats(self) -> Dict[str, Any]:
        """
        获取预测统计信息

        Returns:
            Dict[str, Any]: 预测统计信息
        """
        current_time = datetime.now()
        uptime_seconds = (current_time - self._prediction_stats["start_time"]).total_seconds()

        return {
            "total_predictions": self._prediction_stats["total_predictions"],
            "successful_predictions": self._prediction_stats["successful_predictions"],
            "cache_hits": self._prediction_stats["cache_hits"],
            "errors": self._prediction_stats["errors"],
            "success_rate": (
                self._prediction_stats["successful_predictions"] /
                self._prediction_stats["total_predictions"]
                if self._prediction_stats["total_predictions"] > 0 else 0.0
            ),
            "cache_hit_rate": (
                self._prediction_stats["cache_hits"] /
                self._prediction_stats["total_predictions"]
                if self._prediction_stats["total_predictions"] > 0 else 0.0
            ),
            "uptime_seconds": uptime_seconds,
            "predictions_per_second": (
                self._prediction_stats["total_predictions"] / uptime_seconds
                if uptime_seconds > 0 else 0.0
            )
        }

    def validate_features(
        self,
        features: Union[np.ndarray, pd.DataFrame, List[float]],
        model_name: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        验证特征数据的有效性

        Args:
            features: 特征数据
            model_name: 模型名称

        Returns:
            Dict[str, Any]: 验证结果
        """
        try:
            model_name = model_name or self.default_model_name
            feature_list = self._convert_features_to_list(features)

            # 获取模型元数据
            metadata = self.model_loader.get_model_metadata(model_name)
            if not metadata:
                return {
                    "valid": False,
                    "error": f"模型元数据缺失: {model_name}"
                }

            # 检查特征数量
            expected_count = len(metadata.feature_names) if metadata.feature_names else None
            actual_count = len(feature_list)

            validation_result = {
                "valid": True,
                "model_name": model_name,
                "feature_count": actual_count,
                "expected_feature_count": expected_count,
                "feature_names": metadata.feature_names,
                "has_nan_values": any(np.isnan(np.array(feature_list))),
                "feature_range": {
                    "min": float(np.min(feature_list)),
                    "max": float(np.max(feature_list)),
                    "mean": float(np.mean(feature_list))
                }
            }

            # 检查特征数量匹配
            if expected_count and actual_count != expected_count:
                validation_result["valid"] = False
                validation_result["error"] = (
                    f"特征数量不匹配: 期望 {expected_count}, 实际 {actual_count}"
                )

            return validation_result

        except Exception as e:
            return {
                "valid": False,
                "error": f"特征验证失败: {str(e)}"
            }

    def get_model_info(self, model_name: Optional[str] = None) -> Dict[str, Any]:
        """
        获取模型信息

        Args:
            model_name: 模型名称，如果为None则使用默认模型

        Returns:
            Dict[str, Any]: 模型信息
        """
        model_name = model_name or self.default_model_name
        return self.model_loader.get_model_info(model_name)

    def list_available_models(self) -> List[str]:
        """
        获取可用模型列表

        Returns:
            List[str]: 可用的模型名称列表
        """
        return self.model_loader.list_loaded_models()

    def reset_stats(self) -> None:
        """重置预测统计信息"""
        self._prediction_stats = {
            "total_predictions": 0,
            "successful_predictions": 0,
            "cache_hits": 0,
            "errors": 0,
            "start_time": datetime.now()
        }
        logger.info("预测统计信息已重置")

    def __repr__(self) -> str:
        """字符串表示"""
        return (
            f"MatchPredictor(default_model='{self.default_model_name}', "
            f"loaded_models={len(self.list_available_models())}, "
            f"cache_enabled={self.cache_manager is not None})"
        )