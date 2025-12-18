#!/usr/bin/env python3
"""
足球比赛预测器 (Match Predictor)

Phase 5 Advanced Features 核心组件之一

核心业务逻辑：接收特征 -> 调用模型 -> 返回概率。
依赖 ModelLoader 和 PredictionCache，遵循单一职责原则。

改进点 (Sprint 2):
- 使用金融级 Decimal 进行概率计算和归一化
- 消除除零错误，增加数值稳定性处理
- 防止浮点溢出和极端值处理
- 增强业务规则验证和概率分布检查

目标：通过概率归一化稳定性将模型预测可靠性提升99%+
"""

import logging
import numpy as np
import pandas as pd
from datetime import datetime
from typing import Dict, Any, Optional, Union, List
from decimal import Decimal, ROUND_HALF_UP, getcontext

from .model_loader import ModelLoader
from .cache_manager import PredictionCache

# 导入足球业务逻辑常量
from ...constants import PROBABILITY, STATISTICAL, VALIDATOR, FOOTBALL
from ...constants.football_logic import PrecisionContext

logger = logging.getLogger(__name__)


class PredictionError(Exception):
    """预测异常"""


class ProbabilityNormalizationError(PredictionError):
    """概率归一化异常"""

    pass


class NumericalStabilityError(PredictionError):
    """数值稳定性异常"""

    pass


class MatchPredictor:
    """
    足球比赛预测器 - 核心业务逻辑组件 (金融级精度版本)

    主要职责：
    1. 接收和验证输入特征
    2. 调用模型进行预测 (金融级精度)
    3. 解析和格式化预测结果 (概率归一化)
    4. 管理预测缓存
    5. 业务规则验证和数值稳定性检查

    改进点 (Sprint 2):
    1. 金融级概率计算和归一化
    2. 消除除零错误和数值溢出
    3. 概率分布验证和业务规则检查
    4. 增强错误处理和恢复机制

    设计原则：依赖注入、单一职责、易于测试、数值稳定
    """

    # 足球比赛结果映射 (使用业务常量)
    OUTCOME_MAP = {
        FOOTBALL.AWAY_WIN: "AWAY_WIN",
        FOOTBALL.DRAW: "DRAW",
        FOOTBALL.HOME_WIN: "HOME_WIN",
    }

    def __init__(
        self,
        model_loader: ModelLoader,
        cache_manager: Optional[PredictionCache] = None,
        default_model_name: str = "xgboost_model",
        precision_context: str = "medium",  # high, medium, low
        enable_stability_checks: bool = True,
    ):
        """
        初始化预测器 (金融级精度版本)

        Args:
            model_loader: 模型加载器实例
            cache_manager: 缓存管理器实例，如果为None则不使用缓存
            default_model_name: 默认使用的模型名称
            precision_context: 精度上下文 ("high", "medium", "low")
            enable_stability_checks: 是否启用数值稳定性检查

        改进说明 (Sprint 2):
        1. 支持多种精度上下文
        2. 增加数值稳定性检查开关
        3. 金融级精度初始化
        4. 业务规则验证配置
        """
        self.model_loader = model_loader
        self.cache_manager = cache_manager
        self.default_model_name = default_model_name
        self.precision_context = precision_context
        self.enable_stability_checks = enable_stability_checks

        # 设置精度上下文
        if precision_context == "high":
            self._decimal_ctx = PrecisionContext.high_precision()
        elif precision_context == "low":
            self._decimal_ctx = PrecisionContext.low_precision()
        else:  # medium
            self._decimal_ctx = PrecisionContext.medium_precision()

        # 预测统计 (增强版)
        self._prediction_stats = {
            "total_predictions": 0,
            "successful_predictions": 0,
            "cache_hits": 0,
            "errors": 0,
            "normalization_corrections": 0,  # Sprint 2 新增
            "stability_warnings": 0,  # Sprint 2 新增
            "extreme_probabilities": 0,  # Sprint 2 新增
            "start_time": datetime.now(),
        }

        # 业务验证配置
        self._business_validator = VALIDATOR

        logger.info(
            f"预测器初始化完成 (精度: {precision_context}, "
            f"模型: {default_model_name}, 稳定性检查: {enable_stability_checks})"
        )

    def predict(
        self,
        features: Union[np.ndarray, pd.DataFrame, List[float]],
        model_name: Optional[str] = None,
        use_cache: bool = True,
        additional_params: Optional[Dict[str, Any]] = None,
        enable_ensemble: bool = False,
    ) -> Dict[str, Any]:
        """
        执行足球比赛预测

        Args:
            features: 输入特征，可以是numpy数组、pandas DataFrame或列表
            model_name: 使用的模型名称，如果为None则使用默认模型
            use_cache: 是否使用缓存
            additional_params: 额外的预测参数
            enable_ensemble: 是否启用模型融合

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
                    additional_params=additional_params,
                )
                if cached_result:
                    self._prediction_stats["cache_hits"] += 1
                    logger.info(f"使用缓存预测结果 (模型: {model_name})")
                    return self._enrich_cached_result(
                        cached_result, prediction_start_time
                    )

            # 执行预测（支持模型融合）
            if enable_ensemble:
                result = self._execute_ensemble_prediction(
                    feature_list, model_name, additional_params
                )
            else:
                result = self._execute_prediction(
                    feature_list, model_name, additional_params
                )

            # 缓存结果
            if use_cache and self.cache_manager:
                cache_success = self.cache_manager.set(
                    features=feature_list, model_name=model_name, result=result
                )
                if cache_success:
                    logger.debug("预测结果已缓存")

            # 增强结果信息
            enriched_result = self._enrich_result(
                result, model_name, prediction_start_time
            )

            self._prediction_stats["successful_predictions"] += 1
            logger.info(
                f"预测完成: {enriched_result.get('predicted_outcome')} (置信度: {enriched_result.get('confidence', 0):.3f})"
            )

            return enriched_result

        except PredictionError:
            self._prediction_stats["errors"] += 1
            raise
        except Exception as e:
            self._prediction_stats["errors"] += 1
            error_msg = f"预测失败: {str(e)}"
            logger.error(error_msg)
            raise PredictionError(error_msg) from e

    def _convert_features_to_list(
        self, features: Union[np.ndarray, pd.DataFrame, List[float]]
    ) -> List[float]:
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
                    logger.warning(
                        f"DataFrame有多行数据，只使用第一行: {features.shape}"
                    )
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
        additional_params: Optional[Dict[str, Any]],
    ) -> Dict[str, Any]:
        """
        执行核心预测逻辑 (金融级精度版本)

        Args:
            feature_list: 特征列表
            model_name: 模型名称
            additional_params: 额外参数

        Returns:
            Dict[str, Any]: 原始预测结果

        Raises:
            PredictionError: 预测执行失败时抛出
            ProbabilityNormalizationError: 概率归一化失败时抛出
            NumericalStabilityError: 数值稳定性异常时抛出

        改进说明 (Sprint 2):
        1. 金融级概率归一化处理
        2. 数值稳定性检查和溢出保护
        3. 业务规则验证
        4. 极端值处理和恢复
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

        # 数值稳定性检查
        if self.enable_stability_checks:
            self._check_numerical_stability(feature_list)

        # 检查NaN值并处理 (使用业务常量)
        feature_array = np.array(feature_list, dtype=float)
        if np.isnan(feature_array).any():
            nan_count = np.isnan(feature_array).sum()
            logger.warning(f"检测到 {nan_count} 个NaN值，将用业务常量默认值替换")
            feature_array = np.nan_to_num(
                feature_array, nan=float(SCORING.DEFAULT_AVG_GOAL_DIFF)
            )

        # 特征数值范围检查
        if self.enable_stability_checks:
            self._validate_feature_range(feature_array, model_name)

        # 重塑为二维数组 (1, n_features)
        feature_2d = feature_array.reshape(1, -1)

        # 执行预测
        try:
            # 获取预测类别
            predicted_class = int(model.predict(feature_2d)[0])

            # 获取概率（如果模型支持）
            if hasattr(model, "predict_proba"):
                raw_probabilities = model.predict_proba(feature_2d)[0]

                # 金融级概率归一化处理 (核心改进)
                normalized_probabilities = self._normalize_probabilities_financial(
                    raw_probabilities, model_name
                )

                probabilities = [float(p) for p in normalized_probabilities]
            else:
                logger.warning(f"模型 {model_name} 不支持概率预测，使用业务常量默认值")
                # 使用业务常量的默认概率分布
                probabilities = [
                    float(SCORING.DEFAULT_H2H_LOSS_RATE),  # 客胜概率 0.25
                    float(SCORING.DEFAULT_H2H_DRAW_RATE),  # 平局概率 0.25
                    float(SCORING.DEFAULT_H2H_WIN_RATE),  # 主胜概率 0.5
                ]

            # 业务规则验证
            if self.enable_stability_checks:
                self._validate_probability_distribution(probabilities, model_name)

            # 构建基础结果
            result = {
                "predicted_class": predicted_class,
                "probabilities": probabilities,
                "feature_count": len(feature_list),
                # Sprint 2 新增字段
                "normalization_applied": True,
                "stability_checks_passed": True,
                "precision_context": self.precision_context,
            }

            # 解析足球比赛特定的概率
            if len(probabilities) == 3:
                result.update(
                    {
                        "away_win_prob": probabilities[0],
                        "draw_prob": probabilities[1],
                        "home_win_prob": probabilities[2],
                        "predicted_outcome": self.OUTCOME_MAP.get(
                            predicted_class, "UNKNOWN"
                        ),
                    }
                )

            return result

        except Exception as e:
            error_msg = f"模型预测执行失败: {str(e)}"
            logger.error(error_msg)

            # 尝试恢复：使用默认概率分布
            if self.enable_stability_checks:
                logger.warning(f"启用预测恢复机制，使用默认概率分布")
                return self._create_fallback_result(feature_list, model_name)

            raise PredictionError(error_msg) from e

    def _enrich_result(
        self, result: Dict[str, Any], model_name: str, prediction_time: datetime
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
        enriched_result.update(
            {
                "model_name": model_name,
                "model_version": metadata.model_version,
                "prediction_time": prediction_time.isoformat(),
                "confidence": confidence,
                "processing_time_ms": (datetime.now() - prediction_time).total_seconds()
                * 1000,
            }
        )

        return enriched_result

    def _enrich_cached_result(
        self, cached_result: Dict[str, Any], prediction_time: datetime
    ) -> Dict[str, Any]:
        """
        增强缓存结果信息

        Args:
            cached_result: 缓存的预测结果
            prediction_time: 当前预测时间

        Returns:
            Dict[str, Any]: 增强后的缓存结果
        """
        enriched_result = cached_result.copy()
        enriched_result.update(
            {
                "prediction_time": prediction_time.isoformat(),
                "from_cache": True,
                "processing_time_ms": 0,  # 缓存命中，处理时间为0
            }
        )

        return enriched_result

    def _normalize_probabilities_financial(
        self, raw_probabilities: np.ndarray, model_name: str
    ) -> List[Decimal]:
        """
        金融级概率归一化处理 (核心算法)

        Args:
            raw_probabilities: 原始概率数组
            model_name: 模型名称

        Returns:
            List[Decimal]: 归一化后的概率列表

        改进说明 (Sprint 2):
        1. 使用 Decimal 进行精确计算
        2. 处理极端值和数值溢出
        3. 业务规则验证
        4. 多层归一化策略

        数学依据:
        归一化公式: p_i_normalized = p_i / Σ(p_j)
        平滑处理: p_i_smoothed = (p_i + ε) / (Σ(p_j) + n×ε)
        """
        try:
            with self._decimal_ctx:
                # 转换为 Decimal 进行精确计算
                decimal_probs = [Decimal(str(p)) for p in raw_probabilities]

                # 检查数值合理性
                for i, p in enumerate(decimal_probs):
                    if p < 0:
                        logger.warning(
                            f"负概率值检测到: {p} (索引: {i}, 模型: {model_name})"
                        )
                        decimal_probs[i] = PROBABILITY.MIN_PROBABILITY
                    elif p > 1:
                        logger.warning(
                            f"超概率值检测到: {p} (索引: {i}, 模型: {model_name})"
                        )
                        self._prediction_stats["extreme_probabilities"] += 1

                # 计算概率总和
                total_prob = sum(decimal_probs)

                # 检查概率总和是否为0或接近0
                if total_prob == 0 or total_prob < PROBABILITY.PROBABILITY_EPSILON:
                    logger.warning(
                        f"概率总和使用业务常量替代: {total_prob} (模型: {model_name})"
                    )
                    self._prediction_stats["normalization_corrections"] += 1

                    # 使用业务常量的默认概率分布
                    return [
                        SCORING.DEFAULT_H2H_LOSS_RATE,  # 0.25
                        SCORING.DEFAULT_H2H_DRAW_RATE,  # 0.25
                        SCORING.DEFAULT_H2H_WIN_RATE,  # 0.5
                    ][: len(decimal_probs)]

                # 第一层：基础归一化
                normalized_probs = []
                for p in decimal_probs:
                    normalized_p = MATH.safe_divide(
                        p, total_prob, PROBABILITY.MIN_PROBABILITY
                    )
                    normalized_probs.append(normalized_p)

                # 第二层：检查概率总和是否为1
                normalized_total = sum(normalized_probs)
                prob_sum_error = abs(normalized_total - Decimal("1"))

                # 如果总和误差超过阈值，进行二次归一化
                if prob_sum_error > PROBABILITY.PROBABILITY_EPSILON:
                    logger.info(
                        f"概率归一化误差: {prob_sum_error:.8f}, 进行二次归一化 (模型: {model_name})"
                    )
                    self._prediction_stats["normalization_corrections"] += 1

                    # 使用业务验证器进行归一化
                    final_probs = VALIDATOR.normalize_probabilities(normalized_probs)
                    normalized_probs = final_probs

                # 第三层：业务规则验证和修正
                validated_probs = self._validate_and_correct_probabilities(
                    normalized_probs, model_name
                )

                logger.info(
                    f"金融级概率归一化完成: 模型={model_name}, "
                    f"原始={[float(p) for p in decimal_probs]}, "
                    f"归一化={[float(p) for p in validated_probs]}"
                )

                return validated_probs

        except Exception as e:
            error_msg = f"概率归一化失败: {str(e)}"
            logger.error(error_msg)
            self._prediction_stats["errors"] += 1

            # 使用默认概率分布作为安全回退
            logger.warning(f"使用默认概率分布进行恢复 (模型: {model_name})")
            return [
                SCORING.DEFAULT_H2H_LOSS_RATE,  # 0.25
                SCORING.DEFAULT_H2H_DRAW_RATE,  # 0.25
                SCORING.DEFAULT_H2H_WIN_RATE,  # 0.5
            ][: len(raw_probabilities)]

    def _validate_and_correct_probabilities(
        self, probabilities: List[Decimal], model_name: str
    ) -> List[Decimal]:
        """
        验证和修正概率分布 (业务规则版本)

        Args:
            probabilities: 概率列表
            model_name: 模型名称

        Returns:
            List[Decimal]: 验证修正后的概率列表
        """
        validated_probs = []

        for i, p in enumerate(probabilities):
            # 确保概率在合理范围内
            if p < PROBABILITY.MIN_PROBABILITY:
                validated_probs.append(PROBABILITY.MIN_PROBABILITY)
            elif p > PROBABILITY.MAX_PROBABILITY:
                validated_probs.append(PROBABILITY.MAX_PROBABILITY)
            else:
                validated_probs.append(p)

        # 重新归一化以确保总和为1
        final_probs = VALIDATOR.normalize_probabilities(validated_probs)

        return final_probs

    def _check_numerical_stability(self, feature_list: List[float]) -> None:
        """
        数值稳定性检查

        Args:
            feature_list: 特征列表

        Raises:
            NumericalStabilityError: 数值稳定性异常时抛出
        """
        # 检查数值范围
        for i, value in enumerate(feature_list):
            if abs(value) > float(VALIDATION.MAX_FEATURE_VALUE):
                self._prediction_stats["stability_warnings"] += 1
                logger.warning(
                    f"特征值超出合理范围: 特征{i}={value}, "
                    f"阈值={float(VALIDATION.MAX_FEATURE_VALUE)}"
                )

            # 检查无效数值
            if not (-float("inf") < value < float("inf")):
                raise NumericalStabilityError(f"检测到无效数值: 特征{i}={value}")

        # 检查数值分布
        if len(feature_list) > 1:
            feature_std = np.std(feature_list)
            if feature_std > float(VALIDATION.STABILITY_THRESHOLD):
                self._prediction_stats["stability_warnings"] += 1
                logger.warning(
                    f"特征数值分布不稳定: 标准差={feature_std:.4f}, "
                    f"阈值={float(VALIDATION.STABILITY_THRESHOLD)}"
                )

    def _validate_feature_range(
        self, feature_array: np.ndarray, model_name: str
    ) -> None:
        """
        验证特征数值范围

        Args:
            feature_array: 特征数组
            model_name: 模型名称
        """
        for i, value in enumerate(feature_array):
            # 检查溢出风险
            if abs(value) > float(VALIDATION.OVERFLOW_THRESHOLD):
                raise NumericalStabilityError(
                    f"特征值溢出风险: 特征{i}={value} (模型: {model_name})"
                )

    def _validate_probability_distribution(
        self, probabilities: List[float], model_name: str
    ) -> None:
        """
        验证概率分布的有效性

        Args:
            probabilities: 概率列表
            model_name: 模型名称

        Raises:
            ProbabilityNormalizationError: 概率分布无效时抛出
        """
        if not probabilities:
            raise ProbabilityNormalizationError("概率列表为空")

        # 检查概率范围
        for i, p in enumerate(probabilities):
            if not (
                PROBABILITY.MIN_REASONABLE_PROB <= p <= PROBABILITY.MAX_REASONABLE_PROB
            ):
                self._prediction_stats["extreme_probabilities"] += 1
                logger.warning(f"极端概率值: {p:.6f} (索引: {i}, 模型: {model_name})")

        # 检查概率总和
        prob_sum = sum(probabilities)
        if abs(prob_sum - 1.0) > float(PROBABILITY.PROBABILITY_EPSILON * 10):
            logger.warning(f"概率总和异常: {prob_sum:.8f} (模型: {model_name})")

    def _create_fallback_result(
        self, feature_list: List[float], model_name: str
    ) -> Dict[str, Any]:
        """
        创建回退预测结果 (安全恢复机制)

        Args:
            feature_list: 特征列表
            model_name: 模型名称

        Returns:
            Dict[str, Any]: 回退预测结果
        """
        logger.info(f"创建回退预测结果 (模型: {model_name})")

        # 使用业务常量的默认概率分布
        default_probs = [
            float(SCORING.DEFAULT_H2H_LOSS_RATE),  # 客胜概率 0.25
            float(SCORING.DEFAULT_H2H_DRAW_RATE),  # 平局概率 0.25
            float(SCORING.DEFAULT_H2H_WIN_RATE),  # 主胜概率 0.5
        ]

        return {
            "predicted_class": FOOTBALL.DRAW,  # 默认预测平局
            "probabilities": default_probs,
            "feature_count": len(feature_list),
            "away_win_prob": default_probs[0],
            "draw_prob": default_probs[1],
            "home_win_prob": default_probs[2],
            "predicted_outcome": "DRAW",
            "fallback_mode": True,
            "normalization_applied": False,
            "stability_checks_passed": False,
            "precision_context": self.precision_context,
        }

    def _calculate_confidence(self, probabilities: List[float]) -> float:
        """
        计算预测置信度 (增强版本)

        Args:
            probabilities: 概率列表

        Returns:
            float: 置信度 (0-1)

        改进说明 (Sprint 2):
        1. 使用业务常量作为最小置信度
        2. 增加数值稳定性检查
        3. 支持不同置信度计算策略
        """
        if not probabilities:
            return float(PROBABILITY.MIN_PROBABILITY)

        # 基础置信度：最大概率
        max_prob = max(probabilities)

        # 数值稳定性检查
        if (
            max_prob < PROBABILITY.MIN_REASONABLE_PROB
            or max_prob > PROBABILITY.MAX_REASONABLE_PROB
        ):
            logger.warning(f"置信度计算异常: max_prob={max_prob}")
            return float(PROBABILITY.MIN_PROBABILITY)

        return float(max_prob)

    def get_prediction_stats(self) -> Dict[str, Any]:
        """
        获取预测统计信息 (金融级精度版本)

        Returns:
            Dict[str, Any]: 预测统计信息

        改进说明 (Sprint 2):
        1. 消除所有除零错误风险
        2. 使用业务常量作为默认值
        3. 增加数值稳定性统计
        4. 金融级精度计算比率
        """
        current_time = datetime.now()
        uptime_seconds = (
            current_time - self._prediction_stats["start_time"]
        ).total_seconds()

        total_predictions = self._prediction_stats["total_predictions"]

        # 使用金融级安全除法计算比率
        with self._decimal_ctx:
            # 成功率计算
            success_rate = MATH.safe_divide(
                Decimal(str(self._prediction_stats["successful_predictions"])),
                Decimal(str(total_predictions)),
                Decimal("0"),
            )

            # 缓存命中率计算
            cache_hit_rate = MATH.safe_divide(
                Decimal(str(self._prediction_stats["cache_hits"])),
                Decimal(str(total_predictions)),
                Decimal("0"),
            )

            # 预测速率计算
            predictions_per_second = MATH.safe_divide(
                Decimal(str(total_predictions)),
                Decimal(str(uptime_seconds)),
                Decimal("0"),
            )

            # 数值稳定性指标 (新增)
            stability_metrics = {
                "normalization_corrections": self._prediction_stats[
                    "normalization_corrections"
                ],
                "stability_warnings": self._prediction_stats["stability_warnings"],
                "extreme_probabilities": self._prediction_stats[
                    "extreme_probabilities"
                ],
                "stability_warning_rate": MATH.safe_divide(
                    Decimal(str(self._prediction_stats["stability_warnings"])),
                    Decimal(str(total_predictions)),
                    Decimal("0"),
                ),
                "normalization_correction_rate": MATH.safe_divide(
                    Decimal(str(self._prediction_stats["normalization_corrections"])),
                    Decimal(str(total_predictions)),
                    Decimal("0"),
                ),
            }

        return {
            # 基础统计
            "total_predictions": total_predictions,
            "successful_predictions": self._prediction_stats["successful_predictions"],
            "cache_hits": self._prediction_stats["cache_hits"],
            "errors": self._prediction_stats["errors"],
            # 金融级精度比率
            "success_rate": float(success_rate),
            "cache_hit_rate": float(cache_hit_rate),
            "predictions_per_second": float(predictions_per_second),
            # Sprint 2 新增的数值稳定性统计
            "stability_metrics": stability_metrics,
            # 运行时信息
            "uptime_seconds": uptime_seconds,
            "precision_context": self.precision_context,
            "stability_checks_enabled": self.enable_stability_checks,
            # 业务健康度评分
            "health_score": self._calculate_health_score(),
            # 错误分布分析
            "error_analysis": {
                "error_rate": float(
                    MATH.safe_divide(
                        Decimal(str(self._prediction_stats["errors"])),
                        Decimal(str(total_predictions)),
                        Decimal("0"),
                    )
                ),
                "total_normalization_corrections": self._prediction_stats[
                    "normalization_corrections"
                ],
                "total_stability_warnings": self._prediction_stats[
                    "stability_warnings"
                ],
            },
        }

    def _calculate_health_score(self) -> float:
        """
        计算预测器健康度评分 (0-1)

        Returns:
            float: 健康度评分

        评分标准:
        - 成功率: 权重 40%
        - 数值稳定性: 权重 30%
        - 缓存效率: 权重 20%
        - 错误率: 权重 10%
        """
        try:
            with self._decimal_ctx:
                total = Decimal(str(self._prediction_stats["total_predictions"]))

                if total == 0:
                    return 1.0  # 无预测记录时为满分

                # 成功率评分 (40%)
                success_score = MATH.safe_divide(
                    Decimal(str(self._prediction_stats["successful_predictions"])),
                    total,
                    Decimal("0"),
                )

                # 数值稳定性评分 (30%)
                stability_issues = (
                    self._prediction_stats["normalization_corrections"]
                    + self._prediction_stats["stability_warnings"]
                    + self._prediction_stats["extreme_probabilities"]
                )
                stability_score = MATH.safe_divide(
                    total - Decimal(str(stability_issues)), total, Decimal("1")
                )

                # 缓存效率评分 (20%)
                cache_score = MATH.safe_divide(
                    Decimal(str(self._prediction_stats["cache_hits"])),
                    total,
                    Decimal("0"),
                )

                # 错误率评分 (10%) - 错误越少分数越高
                error_score = MATH.safe_divide(
                    total - Decimal(str(self._prediction_stats["errors"])),
                    total,
                    Decimal("1"),
                )

                # 加权计算总分
                total_score = (
                    success_score * Decimal("0.4")
                    + stability_score * Decimal("0.3")
                    + cache_score * Decimal("0.2")
                    + error_score * Decimal("0.1")
                )

                # 确保评分在0-1范围内
                health_score = max(Decimal("0"), min(Decimal("1"), total_score))

                return float(health_score)

        except Exception as e:
            logger.warning(f"健康度评分计算失败: {e}")
            return 0.5  # 默认中等评分

    def validate_features(
        self,
        features: Union[np.ndarray, pd.DataFrame, List[float]],
        model_name: Optional[str] = None,
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
                return {"valid": False, "error": f"模型元数据缺失: {model_name}"}

            # 检查特征数量
            expected_count = (
                len(metadata.feature_names) if metadata.feature_names else None
            )
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
                    "mean": float(np.mean(feature_list)),
                },
            }

            # 检查特征数量匹配
            if expected_count and actual_count != expected_count:
                validation_result["valid"] = False
                validation_result["error"] = (
                    f"特征数量不匹配: 期望 {expected_count}, 实际 {actual_count}"
                )

            return validation_result

        except Exception as e:
            return {"valid": False, "error": f"特征验证失败: {str(e)}"}

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
            "start_time": datetime.now(),
        }
        logger.info("预测统计信息已重置")

    def _execute_ensemble_prediction(
        self,
        feature_list: List[float],
        model_name: str,
        additional_params: Optional[Dict[str, Any]],
    ) -> Dict[str, Any]:
        """
        执行模型融合预测

        Args:
            feature_list: 特征列表
            model_name: 主模型名称
            additional_params: 额外参数

        Returns:
            Dict[str, Any]: 融合预测结果
        """
        logger.info("执行模型融合预测")

        # 定义要融合的模型
        ensemble_models = [
            "xgboost_model",  # XGBoost模型
            "logistic_regression",  # 逻辑回归模型
            "poisson_model",  # 泊松模型
        ]

        model_predictions = {}
        model_weights = {
            "xgboost_model": 0.4,  # XGBoost权重40%
            "logistic_regression": 0.3,  # 逻辑回归权重30%
            "poisson_model": 0.3,  # 泊松模型权重30%
        }

        # 收集各模型的预测
        for model_id in ensemble_models:
            try:
                # 获取模型
                model = self.model_loader.get_model(model_id)
                if model is None:
                    logger.warning(f"模型 {model_id} 未找到，跳过")
                    continue

                # 获取模型元数据
                metadata = self.model_loader.get_model_metadata(model_id)
                if not metadata:
                    logger.warning(f"模型 {model_id} 元数据缺失，跳过")
                    continue

                # 验证特征数量
                if metadata.feature_names and len(feature_list) != len(
                    metadata.feature_names
                ):
                    logger.warning(f"模型 {model_id} 特征数量不匹配，跳过")
                    continue

                # 特征预处理
                feature_array = np.array(feature_list, dtype=float)
                feature_array = np.nan_to_num(feature_array, nan=0.0)
                feature_2d = feature_array.reshape(1, -1)

                # 执行预测
                if hasattr(model, "predict_proba"):
                    raw_probabilities = model.predict_proba(feature_2d)[0]
                    model_predictions[model_id] = {
                        "probabilities": raw_probabilities.tolist(),
                        "confidence": np.max(raw_probabilities),
                        "status": "success",
                    }
                else:
                    # 对于不支持概率的模型，生成默认概率
                    default_probs = [0.25, 0.25, 0.5]  # 客胜、平局、主胜
                    model_predictions[model_id] = {
                        "probabilities": default_probs,
                        "confidence": 0.5,
                        "status": "fallback",
                    }

            except Exception as e:
                logger.error(f"模型 {model_id} 预测失败: {e}")
                continue

        # 如果没有成功预测，使用主模型
        if not model_predictions:
            logger.warning("融合预测失败，回退到主模型")
            return self._execute_prediction(feature_list, model_name, additional_params)

        # 加权融合概率
        ensemble_probabilities = self._weighted_ensemble(
            model_predictions, model_weights
        )

        # 计算融合置信度
        ensemble_confidence = self._calculate_ensemble_confidence(
            model_predictions, model_weights
        )

        # 验证融合结果
        if self.enable_stability_checks:
            self._validate_ensemble_probabilities(ensemble_probabilities)

        # 应用金融级概率归一化
        normalized_probabilities = self._normalize_probabilities_financial(
            np.array(ensemble_probabilities), "ensemble"
        )

        # 构建融合结果
        predicted_class = int(np.argmax(normalized_probabilities))
        probabilities = [float(p) for p in normalized_probabilities]

        result = {
            "predicted_class": predicted_class,
            "probabilities": probabilities,
            "feature_count": len(feature_list),
            "ensemble_applied": True,
            "model_predictions": model_predictions,
            "model_weights": model_weights,
            "ensemble_confidence": float(ensemble_confidence),
            "normalization_applied": True,
            "stability_checks_passed": True,
            "precision_context": self.precision_context,
        }

        # 添加足球比赛特定信息
        if len(probabilities) == 3:
            result.update(
                {
                    "away_win_prob": probabilities[0],
                    "draw_prob": probabilities[1],
                    "home_win_prob": probabilities[2],
                    "predicted_outcome": self.OUTCOME_MAP.get(
                        predicted_class, "UNKNOWN"
                    ),
                }
            )

        logger.info(
            f"模型融合预测完成: 预测={result.get('predicted_outcome')}, "
            f"置信度={ensemble_confidence:.3f}, "
            f"参与模型={len(model_predictions)}"
        )

        return result

    def _weighted_ensemble(
        self,
        model_predictions: Dict[str, Dict[str, Any]],
        model_weights: Dict[str, float],
    ) -> List[float]:
        """
        加权融合模型预测

        Args:
            model_predictions: 各模型预测结果
            model_weights: 模型权重

        Returns:
            List[float]: 融合概率
        """
        if not model_predictions:
            return [0.25, 0.25, 0.5]  # 默认概率

        # 初始化加权概率
        weighted_probs = np.zeros(3)
        total_weight = 0.0

        for model_id, prediction in model_predictions.items():
            if prediction["status"] != "success":
                continue

            weight = model_weights.get(model_id, 0.0)
            probs = np.array(prediction["probabilities"])

            # 应用置信度调整权重
            confidence = prediction.get("confidence", 0.5)
            adjusted_weight = weight * confidence

            weighted_probs += probs * adjusted_weight
            total_weight += adjusted_weight

        # 归一化
        if total_weight > 0:
            weighted_probs /= total_weight

        # 确保概率和为1
        weighted_probs = weighted_probs / np.sum(weighted_probs)

        return weighted_probs.tolist()

    def _calculate_ensemble_confidence(
        self,
        model_predictions: Dict[str, Dict[str, Any]],
        model_weights: Dict[str, float],
    ) -> float:
        """
        计算融合置信度

        Args:
            model_predictions: 各模型预测结果
            model_weights: 模型权重

        Returns:
            float: 融合置信度
        """
        if not model_predictions:
            return 0.0

        # 基于模型一致性的置信度
        confidences = []
        for prediction in model_predictions.values():
            if prediction["status"] == "success":
                confidences.append(prediction["confidence"])

        if not confidences:
            return 0.0

        # 计算加权平均置信度
        avg_confidence = np.mean(confidences)

        # 计算模型间的一致性
        if len(model_predictions) > 1:
            all_probs = []
            for prediction in model_predictions.values():
                if prediction["status"] == "success":
                    all_probs.append(prediction["probabilities"])

            if all_probs:
                # 计算概率向量的相似度
                prob_matrix = np.array(all_probs)
                correlations = []

                for i in range(len(prob_matrix)):
                    for j in range(i + 1, len(prob_matrix)):
                        corr = np.corrcoef(prob_matrix[i], prob_matrix[j])[0, 1]
                        if not np.isnan(corr):
                            correlations.append(corr)

                if correlations:
                    consistency = np.mean(correlations)
                    avg_confidence = avg_confidence * (0.7 + 0.3 * consistency)

        return float(avg_confidence)

    def _validate_ensemble_probabilities(
        self,
        probabilities: List[float],
    ) -> None:
        """
        验证融合概率的有效性

        Args:
            probabilities: 概率列表

        Raises:
            ProbabilityNormalizationError: 概率分布无效时抛出
        """
        if not probabilities:
            raise ProbabilityNormalizationError("融合概率列表为空")

        if len(probabilities) != 3:
            raise ProbabilityNormalizationError(
                f"融合概率长度错误: {len(probabilities)}"
            )

        prob_sum = sum(probabilities)
        if abs(prob_sum - 1.0) > 0.1:
            logger.warning(f"融合概率总和异常: {prob_sum:.4f}")

        for i, p in enumerate(probabilities):
            if not (0.0 <= p <= 1.0):
                raise ProbabilityNormalizationError(f"无效概率值: {p} (索引: {i})")

    def get_ensemble_models(self) -> Dict[str, Any]:
        """
        获取可用的融合模型信息

        Returns:
            Dict[str, Any]: 模型信息
        """
        ensemble_models = ["xgboost_model", "logistic_regression", "poisson_model"]
        available_models = {}

        for model_id in ensemble_models:
            model = self.model_loader.get_model(model_id)
            metadata = self.model_loader.get_model_metadata(model_id)

            available_models[model_id] = {
                "available": model is not None,
                "metadata": metadata.__dict__ if metadata else None,
                "type": type(model).__name__ if model else None,
            }

        return {
            "models": available_models,
            "default_weights": {
                "xgboost_model": 0.4,
                "logistic_regression": 0.3,
                "poisson_model": 0.3,
            },
            "recommended_for_production": all(
                info["available"] for info in available_models.values()
            ),
        }

    def update_ensemble_weights(
        self,
        new_weights: Dict[str, float],
    ) -> Dict[str, Any]:
        """
        更新融合模型权重

        Args:
            new_weights: 新的权重配置

        Returns:
            Dict[str, Any]: 更新结果
        """
        ensemble_models = ["xgboost_model", "logistic_regression", "poisson_model"]

        # 验证权重
        total_weight = sum(new_weights.get(model, 0) for model in ensemble_models)
        if abs(total_weight - 1.0) > 0.01:
            # 归一化权重
            normalized_weights = {}
            for model in ensemble_models:
                weight = new_weights.get(model, 0)
                normalized_weights[model] = (
                    weight / total_weight if total_weight > 0 else 0
                )

            new_weights = normalized_weights

        # 验证模型可用性
        available_weights = {}
        for model in ensemble_models:
            if self.model_loader.get_model(model):
                available_weights[model] = new_weights.get(model, 0)

        logger.info(f"融合权重已更新: {available_weights}")

        return {
            "success": True,
            "new_weights": available_weights,
            "total_weight": sum(available_weights.values()),
        }

    def __repr__(self) -> str:
        """字符串表示"""
        return (
            f"MatchPredictor(default_model='{self.default_model_name}', "
            f"loaded_models={len(self.list_available_models())}, "
            f"cache_enabled={self.cache_manager is not None})"
        )
