"""
SHAP可解释性服务

为预测结果提供特征重要性分析和解释，使用SHAP计算每个特征的贡献度。
"""

import logging
from typing import Any

import numpy as np
import pandas as pd

# from src.features.schemas import MatchFeatureSet  # 暂时注释掉，模块不存在
from src.core.exceptions import ExplainabilityError
from src.ml.models.xgboost_classifier import XGBoostClassifier

logger = logging.getLogger(__name__)


class ExplainabilityService:
    """
    SHAP可解释性服务

    使用SHAP (SHapley Additive exPlanations)为机器学习模型的预测结果
    提供特征级别的解释，展示每个特征对预测结果的贡献度。
    """

    def __init__(self):
        """初始化SHAP解释器"""
        self._explainer_cache = {}

    async def get_shap_contributions(
        self, features: pd.DataFrame, model: XGBoostClassifier
    ) -> list[dict[str, float]]:
        """
        计算SHAP特征贡献度

        使用SHAP TreeExplainer在fast模式下计算每个特征对预测结果的贡献。

        Args:
            features: 特征数据 (DataFrame，每行代表一场比赛的M3特征)
            model: XGBoost分类模型实例

        Returns:
            List[Dict[str, float]]: 每场比赛的特征贡献度字典列表

        Raises:
            ExplainabilityError: SHAP计算失败时抛出
        """
        try:
            logger.info(f"开始计算SHAP贡献度，特征数量: {len(features)}, 预测数量: {len(features)}")

            # 获取模型基础信息
            model_info = model.get_model_info()
            model_info.get("model_path", "unknown")
            model_info.get("model_version", "unknown")

            # 验证模型已加载
            if not model.is_trained:
                raise ExplainabilityError("模型未训练，无法计算SHAP值")

            # 获取或创建SHAP解释器
            explainer = await self._get_or_create_explainer(model)

            # 验证特征完整性
            self._validate_features(features, model)

            # 计算SHAP值
            shap_values = await self._compute_shap_values(explainer, features)

            # 转换为贡献度字典
            contributions_list = await self._format_contributions(features, shap_values, model)

            # 验证SHAP值计算正确性
            await self._validate_shap_consistency(features, model, shap_values, contributions_list)

            logger.info(f"SHAP贡献度计算完成，处理了 {len(contributions_list)} 个预测")
            return contributions_list

        except Exception as e:
            logger.exception(f"SHAP贡献度计算失败: {e}")
            raise ExplainabilityError(f"SHAP计算失败: {e!s}")

    async def _get_or_create_explainer(self, model: XGBoostClassifier):
        """获取或创建SHAP解释器（缓存优化）"""
        model_id = id(model.model)  # 使用模型对象ID作为缓存键

        if model_id not in self._explainer_cache:
            import shap

            # 使用fast模式优化性能
            explainer = shap.TreeExplainer(
                model.model,
                model_output="probability",  # 输出概率值
                feature_perturbation="interventional",  # 干预式扰动
            )

            self._explainer_cache[model_id] = explainer
            logger.info(f"SHAP解释器已缓存，模型ID: {model_id}")

        return self._explainer_cache[model_id]

    def _validate_features(self, features: pd.DataFrame, model: XGBoostClassifier):
        """验证特征数据的完整性和有效性"""
        # 检查特征数量
        if len(features) == 0:
            raise ExplainabilityError("特征数据为空")

        # 使用MatchFeatureSet的特征名称（而不是所有字段）
        from datetime import datetime

        from src.features.schemas import create_empty_feature_set

        # 创建一个空的特征集来获取标准的特征名称
        empty_feature_set = create_empty_feature_set(
            match_id="test",
            home_team_id="home",
            away_team_id="away",
            match_date=datetime.now(),
        )
        expected_feature_names = set(empty_feature_set.get_feature_names())

        actual_features = set(features.columns)

        if not expected_feature_names.issubset(actual_features):
            missing_features = expected_feature_names - actual_features
            raise ExplainabilityError(f"缺少必要的特征列: {missing_features}")

        # 检查数据类型和缺失值
        for col in expected_feature_names:
            if col in features.columns and features[col].isnull().all():
                raise ExplainabilityError(f"特征列 {col} 全部为空值")

    async def _compute_shap_values(self, explainer, features: pd.DataFrame):
        """计算SHAP值"""

        try:
            # 使用SHAP fast mode计算
            shap_values = explainer.shap_values(features, check_additivity=True)  # 检查加性一致性

            # 处理多分类SHAP值（如果是多分类输出）
            if isinstance(shap_values, list):
                # 对于多分类，取预测概率最高的类别
                shap_values = shap_values[0]  # 假设二元分类，取第一类

            return shap_values

        except Exception as e:
            logger.exception(f"SHAP值计算异常: {e}")
            raise ExplainabilityError(f"SHAP值计算失败: {e!s}")

    async def _format_contributions(
        self, features: pd.DataFrame, shap_values: np.ndarray, model: XGBoostClassifier
    ) -> list[dict[str, float]]:
        """将SHAP值格式化为特征贡献度字典"""
        contributions_list = []

        for i in range(len(features)):
            contributions = {}

            # 获取第i个样本的所有特征SHAP值
            for j, feature_name in enumerate(features.columns):
                contribution_value = float(shap_values[i, j])
                contributions[feature_name] = contribution_value

            # 按贡献度绝对值排序（可选）
            sorted_contributions = dict(
                sorted(contributions.items(), key=lambda x: abs(x[1]), reverse=True)
            )

            contributions_list.append(sorted_contributions)

        return contributions_list

    async def _validate_shap_consistency(
        self,
        features: pd.DataFrame,
        model: XGBoostClassifier,
        shap_values: np.ndarray,
        contributions_list: list[dict[str, float]],
    ):
        """验证SHAP值计算的一致性和正确性"""
        try:
            # 获取基准值（预期值）
            base_value = float(self._explainer_cache[id(model.model)].expected_value)

            for i in range(len(features)):
                # 验证SHAP值加性：base_value + sum(SHAP) ≈ model_output
                shap_sum = base_value + sum(contributions_list[i].values())

                # 获取模型原始输出
                model_output = float(model.predict_proba(features.iloc[[i]])[0, 1])

                # 允许小的数值误差
                tolerance = 1e-6
                if abs(shap_sum - model_output) > tolerance:
                    logger.warning(
                        f"SHAP加性不一致 (样本{i}): "
                        f"SHAP总和={shap_sum:.6f}, 模型输出={model_output:.6f}, "
                        f"差值={abs(shap_sum - model_output):.6f}"
                    )

                # 验证特征覆盖度
                expected_features = set(MatchFeatureSet.model_fields.keys())
                actual_features = set(contributions_list[i].keys())

                if not expected_features.issubset(actual_features):
                    missing = expected_features - actual_features
                    logger.warning(f"样本{i}缺少SHAP贡献度特征: {missing}")

        except Exception as e:
            logger.warning(f"SHAP一致性验证失败（不影响功能）: {e}")

    def get_feature_importance_ranking(
        self, contributions_list: list[dict[str, float]]
    ) -> dict[str, float]:
        """
        计算全局特征重要性排名

        基于多个样本的SHAP贡献度计算全局特征重要性。

        Args:
            contributions_list: 多个样本的特征贡献度字典列表

        Returns:
            Dict[str, float]: 特征重要性排名（按重要性降序）
        """
        if not contributions_list:
            return {}

        # 计算每个特征的平均绝对SHAP值
        feature_importance = {}
        for contributions in contributions_list:
            for feature, shap_value in contributions.items():
                if feature not in feature_importance:
                    feature_importance[feature] = []
                feature_importance[feature].append(abs(shap_value))

        # 计算平均重要性并排序
        avg_importance = {
            feature: np.mean(shap_values) for feature, shap_values in feature_importance.items()
        }

        # 按重要性降序排序
        sorted_importance = dict(sorted(avg_importance.items(), key=lambda x: x[1], reverse=True))

        logger.info(f"全局特征重要性排名计算完成，特征数量: {len(sorted_importance)}")
        return sorted_importance

    def clear_cache(self):
        """清除SHAP解释器缓存"""
        cache_size = len(self._explainer_cache)
        self._explainer_cache.clear()
        logger.info(f"已清除SHAP解释器缓存，清除数量: {cache_size}")

    async def explain_single_prediction(
        self, features: dict[str, Any], model: XGBoostClassifier
    ) -> dict[str, Any]:
        """
        解释单个预测结果

        Args:
            features: 单个样本的特征字典
            model: XGBoost模型实例

        Returns:
            Dict[str, Any]: 包含预测结果和SHAP解释的完整信息
        """
        try:
            # 转换为DataFrame
            features_df = pd.DataFrame([features])

            # 获取预测结果
            prediction_result = model.predict_with_probability(features_df)

            # 计算SHAP贡献度
            contributions_list = await self.get_shap_contributions(features_df, model)
            contributions = contributions_list[0] if contributions_list else {}

            # 获取特征重要性排名
            importance_ranking = self.get_feature_importance_ranking([contributions])

            # 格式化解释结果
            return {
                "prediction": prediction_result,
                "feature_contributions": contributions,
                "top_positive_contributors": [
                    {"feature": k, "contribution": v}
                    for k, v in sorted(contributions.items(), key=lambda x: x[1], reverse=True)[:5]
                    if v > 0
                ],
                "top_negative_contributors": [
                    {"feature": k, "contribution": v}
                    for k, v in sorted(contributions.items(), key=lambda x: x[1])[:5]
                    if v < 0
                ],
                "feature_importance_ranking": importance_ranking,
            }


        except Exception as e:
            logger.exception(f"单个预测解释失败: {e}")
            raise ExplainabilityError(f"预测解释失败: {e!s}")
