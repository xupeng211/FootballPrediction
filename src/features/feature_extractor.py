"""
特征提取器 (Feature Extractor)

统一的特征提取逻辑，确保训练和推理使用相同的特征工程。
与scripts/train/prepare_training_data.py保持一致。

主要功能:
- 统一的特征提取接口
- 特征工程逻辑
- 数据验证和清洗
- 特征名称标准化

作者: Feature Engineer (P2-5)
创建时间: 2025-12-06
版本: 1.0.0
"""

import pandas as pd
import numpy as np
from typing import , Any, , Optional
import logging

logger = logging.getLogger(__name__)


class FeatureExtractor:
    """统一的特征提取器"""

    # 必需的基础特征（从数据库获取）
    BASE_FEATURES = [
        "home_xg",
        "away_xg",
        "home_possession",
        "away_possession",
        "home_shots",
        "away_shots",
        "home_shots_on_target",
        "away_shots_on_target",
    ]

    # 衍生特征（通过特征工程生成）
    DERIVED_FEATURES = [
        "xg_difference",
        "xg_ratio",
        "possession_difference",
        "shots_difference",
        "home_shot_efficiency",
        "away_shot_efficiency",
    ]

    # 完整特征列表
    ALL_FEATURES = BASE_FEATURES + DERIVED_FEATURES

    @staticmethod
    def extract_features_from_match(match_data: dict[str, Any]) -> dict[str, float]:
        """
        从比赛数据中提取特征

        Args:
            match_data: 包含比赛数据的字典

        Returns:
            特征字典
        """
        features = {}

        # 1. 提取基础特征
        for feature in FeatureExtractor.BASE_FEATURES:
            value = match_data.get(feature)
            if value is None or pd.isna(value):
                # 使用默认值
                if "xg" in feature:
                    value = 1.2  # 默认xG值
                elif "possession" in feature:
                    value = 50.0  # 默认控球率
                elif "shots" in feature and "on_target" not in feature:
                    value = 10  # 默认射门数
                elif "shots_on_target" in feature:
                    value = 3  # 默认射正数
                else:
                    value = 0.0

                logger.warning(f"特征 {feature} 缺失，使用默认值: {value}")

            features[feature] = float(value)

        # 2. 生成衍生特征（与训练脚本逻辑一致）
        # xG差值
        features["xg_difference"] = features["home_xg"] - features["away_xg"]

        # xG比率
        features["xg_ratio"] = features["home_xg"] / (features["away_xg"] + 0.001)

        # 控球率差值
        features["possession_difference"] = (
            features["home_possession"] - features["away_possession"]
        )

        # 射门差值
        features["shots_difference"] = features["home_shots"] - features["away_shots"]

        # 射门效率
        features["home_shot_efficiency"] = features["home_shots_on_target"] / (
            features["home_shots"] + 0.001
        )
        features["away_shot_efficiency"] = features["away_shots_on_target"] / (
            features["away_shots"] + 0.001
        )

        return features

    @staticmethod
    def extract_features_from_dataframe(df: pd.DataFrame) -> pd.DataFrame:
        """
        从DataFrame中批量提取特征

        Args:
            df: 包含基础特征数据的DataFrame

        Returns:
            包含完整特征的DataFrame
        """
        result_df = df.copy()

        # 确保基础特征存在
        missing_features = []
        for feature in FeatureExtractor.BASE_FEATURES:
            if feature not in result_df.columns:
                missing_features.append(feature)

        if missing_features:
            logger.warning(f"DataFrame中缺少基础特征: {missing_features}")
            # 为缺失特征添加默认值
            for feature in missing_features:
                if "xg" in feature:
                    result_df[feature] = 1.2
                elif "possession" in feature:
                    result_df[feature] = 50.0
                elif "shots" in feature and "on_target" not in feature:
                    result_df[feature] = 10
                elif "shots_on_target" in feature:
                    result_df[feature] = 3
                else:
                    result_df[feature] = 0.0

        # 填充缺失值
        for feature in FeatureExtractor.BASE_FEATURES:
            if result_df[feature].isnull().any():
                median_val = result_df[feature].median()
                result_df[feature] = result_df[feature].fillna(median_val)
                logger.info(f"填充特征 {feature} 的缺失值: 中位数={median_val}")

        # 生成衍生特征
        # xG差值
        result_df["xg_difference"] = result_df["home_xg"] - result_df["away_xg"]

        # xG比率
        result_df["xg_ratio"] = result_df["home_xg"] / (result_df["away_xg"] + 0.001)

        # 控球率差值
        result_df["possession_difference"] = (
            result_df["home_possession"] - result_df["away_possession"]
        )

        # 射门差值
        result_df["shots_difference"] = (
            result_df["home_shots"] - result_df["away_shots"]
        )

        # 射门效率
        result_df["home_shot_efficiency"] = result_df["home_shots_on_target"] / (
            result_df["home_shots"] + 0.001
        )
        result_df["away_shot_efficiency"] = result_df["away_shots_on_target"] / (
            result_df["away_shots"] + 0.001
        )

        logger.info(f"特征工程完成，总特征数: {len(result_df.columns)}")
        return result_df

    @staticmethod
    def validate_features(features: dict[str, float]) -> dict[str, Any]:
        """
        验证特征数据的有效性

        Args:
            features: 特征字典

        Returns:
            验证结果
        """
        validation_result = {
            "is_valid": True,
            "missing_features": [],
            "invalid_features": [],
            "warnings": [],
        }

        # 检查必需特征
        for feature in FeatureExtractor.ALL_FEATURES:
            if feature not in features:
                validation_result["missing_features"].append(feature)
                validation_result["is_valid"] = False

        # 检查特征值的合理性
        for feature, value in features.items():
            if pd.isna(value) or value is None:
                validation_result["invalid_features"].append(f"{feature}: 空值")
                validation_result["is_valid"] = False
                continue

            # 检查数值范围
            if "possession" in feature:
                if not (0 <= value <= 100):
                    validation_result["warnings"].append(
                        f"{feature}: 控球率应在0-100之间，当前值: {value}"
                    )
            elif "efficiency" in feature:
                if not (0 <= value <= 1):
                    validation_result["warnings"].append(
                        f"{feature}: 效率应在0-1之间，当前值: {value}"
                    )
            elif "xg" in feature:
                if value < 0 or value > 10:
                    validation_result["warnings"].append(
                        f"{feature}: xG值异常，当前值: {value}"
                    )
            elif "shots" in feature:
                if value < 0 or value > 50:
                    validation_result["warnings"].append(
                        f"{feature}: 射门数异常，当前值: {value}"
                    )

        return validation_result

    @staticmethod
    def get_feature_vector(
        features: dict[str, float], feature_order: Optional[list[str]] = None
    ) -> list[float]:
        """
        将特征字典转换为特征向量

        Args:
            features: 特征字典
            feature_order: 特征顺序（如果为None，使用默认顺序）

        Returns:
            特征向量
        """
        if feature_order is None:
            feature_order = FeatureExtractor.ALL_FEATURES

        feature_vector = []
        for feature in feature_order:
            if feature in features:
                feature_vector.append(float(features[feature]))
            else:
                # 缺失特征使用默认值
                if "efficiency" in feature:
                    feature_vector.append(0.3)
                elif "difference" in feature or "ratio" in feature:
                    feature_vector.append(0.0)
                elif "possession" in feature:
                    feature_vector.append(50.0)
                elif "shots" in feature:
                    feature_vector.append(10)
                else:
                    feature_vector.append(1.0)

                logger.warning(f"特征向量构建时缺失特征 {feature}，使用默认值")

        return feature_vector

    @staticmethod
    def create_feature_dataframe(
        feature_dicts: list[dict[str, float]], feature_order: Optional[list[str]] = None
    ) -> pd.DataFrame:
        """
        从特征字典列表创建DataFrame

        Args:
            feature_dicts: 特征字典列表
            feature_order: 特征顺序

        Returns:
            特征DataFrame
        """
        if feature_order is None:
            feature_order = FeatureExtractor.ALL_FEATURES

        # 确保所有特征字典都有相同的特征
        standardized_dicts = []
        for _i, feature_dict in enumerate(feature_dicts):
            standardized_dict = {}
            for feature in feature_order:
                if feature in feature_dict:
                    standardized_dict[feature] = feature_dict[feature]
                else:
                    # 使用默认值
                    if "efficiency" in feature:
                        standardized_dict[feature] = 0.3
                    elif "difference" in feature or "ratio" in feature:
                        standardized_dict[feature] = 0.0
                    elif "possession" in feature:
                        standardized_dict[feature] = 50.0
                    elif "shots" in feature:
                        standardized_dict[feature] = 10
                    else:
                        standardized_dict[feature] = 1.0

            standardized_dicts.append(standardized_dict)

        return pd.DataFrame(standardized_dicts)

    @staticmethod
    def get_default_features() -> dict[str, float]:
        """
        获取默认特征值

        Returns:
            默认特征字典
        """
        return {
            # 基础特征默认值
            "home_xg": 1.5,
            "away_xg": 1.2,
            "home_possession": 50.0,
            "away_possession": 50.0,
            "home_shots": 12,
            "away_shots": 10,
            "home_shots_on_target": 4,
            "away_shots_on_target": 3,
            # 衍生特征默认值
            "xg_difference": 0.3,
            "xg_ratio": 1.25,
            "possession_difference": 0.0,
            "shots_difference": 2,
            "home_shot_efficiency": 0.33,
            "away_shot_efficiency": 0.30,
        }

    @staticmethod
    def get_feature_descriptions() -> dict[str, str]:
        """
        获取特征描述

        Returns:
            特征描述字典
        """
        return {
            # 基础特征
            "home_xg": "主队期望进球数",
            "away_xg": "客队期望进球数",
            "home_possession": "主队控球率(%)",
            "away_possession": "客队控球率(%)",
            "home_shots": "主队射门数",
            "away_shots": "客队射门数",
            "home_shots_on_target": "主队射正数",
            "away_shots_on_target": "客队射正数",
            # 衍生特征
            "xg_difference": "主客队期望进球差值",
            "xg_ratio": "主客队期望进球比率",
            "possession_difference": "主客队控球率差值",
            "shots_difference": "主客队射门数差值",
            "home_shot_efficiency": "主队射门效率",
            "away_shot_efficiency": "客队射门效率",
        }


# 全局特征提取器实例
feature_extractor = FeatureExtractor()
