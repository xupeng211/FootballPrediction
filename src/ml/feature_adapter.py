#!/usr/bin/env python3
"""
Feature Adapter - V26.4 特征适配层
=====================================

将 V25.1 提取的原始特征映射到模型所需的特定特征集。

设计原则:
    - 桥接模式: 连接特征提取器和模型
    - 类型安全: 确保特征类型正确
    - 可扩展: 支持多种特征映射策略

Author: Architecture Team
Version: V26.4
Date: 2025-12-28
"""

from abc import ABC, abstractmethod  # noqa: F401
from dataclasses import dataclass  # noqa: F401
from enum import Enum  # noqa: F401
import logging
from typing import Any

import numpy as np  # noqa: F401
import pandas as pd

from src.ml.feature_adapters.base import AdaptationResult, BaseFeatureAdapter, ModelType
from src.ml.feature_adapters.prematch import V26_6_PreMatchAdapter
from src.ml.feature_adapters.production import V26_5_ProductionAdapter

logger = logging.getLogger(__name__)


class V19RollingAdapter(BaseFeatureAdapter):
    """
    V19 滚动特征适配器

    将 V25.1 的原始特征映射到 V19 的 48 维滚动特征。
    由于 V25.1 不包含历史滚动数据，此类提供模拟值用于测试。
    """

    # V19.4 模型期望的 48 个特征
    V19_FEATURES = [
        # 主队滚动特征 (8个)
        "home_rolling_xg",
        "home_rolling_xg_std",
        "home_rolling_shots_on_target",
        "home_rolling_shots_on_target_std",
        "home_rolling_possession",
        "home_rolling_possession_std",
        "home_rolling_team_rating",
        "home_rolling_team_rating_std",
        # 客队滚动特征 (8个)
        "away_rolling_xg",
        "away_rolling_xg_std",
        "away_rolling_shots_on_target",
        "away_rolling_shots_on_target_std",
        "away_rolling_possession",
        "away_rolling_possession_std",
        "away_rolling_team_rating",
        "away_rolling_team_rating_std",
        # 积分榜特征 (8个)
        "home_table_position",
        "away_table_position",
        "table_position_diff",
        "home_points",
        "away_points",
        "points_diff",
        "home_recent_form_points",
        "away_recent_form_points",
        # ELO 评级特征 (7个)
        "elo_raw_elo_gap",
        "elo_adjusted_elo_gap",
        "elo_home_elo_effective",
        "elo_away_elo_effective",
        "elo_adjustment_factor",
        "elo_fatigue_impact",
        "elo_schedule_impact",
        # 疲劳度特征 (6个)
        "home_fatigue_index",
        "away_fatigue_index",
        "fatigue_diff",
        "home_rest_days",
        "away_rest_days",
        # 动机特征 (9个)
        "home_relegation_incentive",
        "away_relegation_incentive",
        "incentive_diff",
        "home_desperation",
        "away_desperation",
        "table_proximity",
        "low_scoring_tendency",
        "elo_diff_cluster",
        # 联赛标识特征 (7个)
        "league_epl",
        "league_championship",
        "league_primeira_liga",
        "league_bundesliga",
        "league_seriea",
        "league_ligue1",
        "league_laliga",
    ]

    def adapt(self, raw_features: dict[str, Any]) -> AdaptationResult:
        """
        将原始特征适配为 V19 滚动特征

        注意: 由于 V25.1 只包含单场比赛数据，无法计算真实的历史滚动特征。
        此方法提供基于单场比赛数据的近似值，用于测试和演示。
        """
        errors: list[str] = []
        missing_features: list[str] = []
        adapted = {}

        try:
            # 尝试从原始特征中提取可用数据
            # 比赛数据
            self._safe_get(raw_features, "header", "teams", "home", "score", default=0)
            self._safe_get(raw_features, "header", "teams", "away", "score", default=0)

            # 统计数据
            home_xg = self._safe_get(raw_features, "content", "stats", "home", "xg", default=1.0)
            away_xg = self._safe_get(raw_features, "content", "stats", "away", "xg", default=1.0)

            home_shots = self._safe_get(
                raw_features, "content", "stats", "home", "shotsTotal", "total", default=10
            )
            away_shots = self._safe_get(
                raw_features, "content", "stats", "away", "shotsTotal", "total", default=10
            )

            home_possession = self._safe_get(
                raw_features, "content", "stats", "home", "possession", "percentage", default=50
            )
            away_possession = 100 - home_possession

            # 构建特征向量
            adapted = {
                # 主队滚动特征 (使用单场比赛数据作为近似)
                "home_rolling_xg": home_xg,
                "home_rolling_xg_std": 0.5,
                "home_rolling_shots_on_target": home_shots * 0.4,
                "home_rolling_shots_on_target_std": 2.0,
                "home_rolling_possession": home_possession,
                "home_rolling_possession_std": 10.0,
                "home_rolling_team_rating": 6.8,
                "home_rolling_team_rating_std": 0.5,
                # 客队滚动特征
                "away_rolling_xg": away_xg,
                "away_rolling_xg_std": 0.5,
                "away_rolling_shots_on_target": away_shots * 0.4,
                "away_rolling_shots_on_target_std": 2.0,
                "away_rolling_possession": away_possession,
                "away_rolling_possession_std": 10.0,
                "away_rolling_team_rating": 6.7,
                "away_rolling_team_rating_std": 0.5,
                # 积分榜特征 (使用默认值)
                "home_table_position": 10,
                "away_table_position": 10,
                "table_position_diff": 0,
                "home_points": 30,
                "away_points": 30,
                "points_diff": 0,
                "home_recent_form_points": 6,
                "away_recent_form_points": 6,
                # ELO 评级特征
                "elo_raw_elo_gap": 0,
                "elo_adjusted_elo_gap": 0,
                "elo_home_elo_effective": 1500,
                "elo_away_elo_effective": 1500,
                "elo_adjustment_factor": 1.0,
                "elo_fatigue_impact": 0,
                "elo_schedule_impact": 0,
                # 疲劳度特征
                "home_fatigue_index": 0.5,
                "away_fatigue_index": 0.5,
                "fatigue_diff": 0,
                "home_rest_days": 7,
                "away_rest_days": 7,
                # 动机特征
                "home_relegation_incentive": 0,
                "away_relegation_incentive": 0,
                "incentive_diff": 0,
                "home_desperation": 0.5,
                "away_desperation": 0.5,
                "table_proximity": 0,
                "low_scoring_tendency": 0,
                "elo_diff_cluster": 1,
                # 联赛标识 (EPL)
                "league_epl": 1,
                "league_championship": 0,
                "league_primeira_liga": 0,
                "league_bundesliga": 0,
                "league_seriea": 0,
                "league_ligue1": 0,
                "league_laliga": 0,
            }

            # 检查缺失特征
            for feat in self.V19_FEATURES:
                if feat not in adapted:
                    missing_features.append(feat)

            success = len(missing_features) == 0

            if not success:
                errors.append(f"Missing {len(missing_features)} features")

            # 构建特征矩阵
            feature_values = [adapted.get(feat, 0) for feat in self.V19_FEATURES]
            feature_matrix = pd.DataFrame([feature_values], columns=self.V19_FEATURES)

            return AdaptationResult(
                success=success,
                features=feature_matrix,
                feature_names=self.V19_FEATURES,
                missing_features=missing_features,
                errors=errors,
            )

        except Exception as e:
            logger.exception(f"特征适配失败: {e}")
            return AdaptationResult(
                success=False,
                features=None,
                feature_names=[],
                missing_features=self.V19_FEATURES,
                errors=[str(e)],
            )

    def get_required_features(self) -> list[str]:
        """获取 V19.4 模型所需的特征列表"""
        return self.V19_FEATURES.copy()

    def _safe_get(self, data: dict, *keys, default=None) -> Any:
        """安全获取嵌套字典值"""
        for key in keys:
            if isinstance(data, dict) and key in data:
                data = data[key]
            else:
                return default
        return data


class V26MiniAdapter(BaseFeatureAdapter):
    """
    V26 微型特征适配器

    使用最简单的特征子集，用于快速验证和测试。
    只需从 V25.1 的输出中提取少量关键特征。
    """

    # 微型特征集 (10个核心特征)
    MINI_FEATURES = [
        "home_score",
        "away_score",
        "home_possession",
        "away_possession",
        "home_shots_total",
        "away_shots_total",
        "home_xg",
        "away_xg",
        "possession_diff",
        "xg_diff",
    ]

    def adapt(self, raw_features: dict[str, Any]) -> AdaptationResult:
        """
        将原始特征适配为微型特征集
        """
        errors: list[str] = []
        missing_features: list[str] = []
        adapted = {}

        try:
            # 提取核心特征
            adapted["home_score"] = self._safe_get(
                raw_features, "header", "teams", "home", "score", default=0
            )
            adapted["away_score"] = self._safe_get(
                raw_features, "header", "teams", "away", "score", default=0
            )

            home_poss = (
                self._safe_get(
                    raw_features, "content", "stats", "home", "possession", "percentage", default=50
                )
                / 100
            )
            adapted["home_possession"] = home_poss
            adapted["away_possession"] = 1 - home_poss

            adapted["home_shots_total"] = self._safe_get(
                raw_features, "content", "stats", "home", "shotsTotal", "total", default=10
            )
            adapted["away_shots_total"] = self._safe_get(
                raw_features, "content", "stats", "away", "shotsTotal", "total", default=10
            )

            adapted["home_xg"] = self._safe_get(
                raw_features, "content", "stats", "home", "xg", default=1.0
            )
            adapted["away_xg"] = self._safe_get(
                raw_features, "content", "stats", "away", "xg", default=1.0
            )

            # 衍生特征
            adapted["possession_diff"] = adapted["home_possession"] - adapted["away_possession"]
            adapted["xg_diff"] = adapted["home_xg"] - adapted["away_xg"]

            # 检查缺失特征
            for feat in self.MINI_FEATURES:
                if feat not in adapted:
                    missing_features.append(feat)

            success = len(missing_features) == 0

            # 构建特征矩阵
            feature_values = [adapted.get(feat, 0) for feat in self.MINI_FEATURES]
            feature_matrix = pd.DataFrame([feature_values], columns=self.MINI_FEATURES)

            return AdaptationResult(
                success=success,
                features=feature_matrix,
                feature_names=self.MINI_FEATURES,
                missing_features=missing_features,
                errors=errors,
            )

        except Exception as e:
            logger.exception(f"微型特征适配失败: {e}")
            return AdaptationResult(
                success=False,
                features=None,
                feature_names=[],
                missing_features=self.MINI_FEATURES,
                errors=[str(e)],
            )

    def get_required_features(self) -> list[str]:
        """获取微型特征集"""
        return self.MINI_FEATURES.copy()

    def _safe_get(self, data: dict, *keys, default=None) -> Any:
        """安全获取嵌套字典值"""
        for key in keys:
            if isinstance(data, dict) and key in data:
                data = data[key]
            else:
                return default
        return data


class FeatureAdapterFactory:
    """特征适配器工厂"""

    _adapters: dict[ModelType, BaseFeatureAdapter] = {
        ModelType.V19_ROLLING: V19RollingAdapter(),
        ModelType.V26_MINI: V26MiniAdapter(),
        ModelType.V26_5_PRODUCTION: V26_5_ProductionAdapter(),
        ModelType.V26_6_PRE_MATCH: V26_6_PreMatchAdapter(),
    }

    @classmethod
    def get_adapter(cls, model_type: ModelType) -> BaseFeatureAdapter:
        """
        获取指定类型的特征适配器

        Args:
            model_type: 模型类型

        Returns:
            BaseFeatureAdapter: 特征适配器实例
        """
        adapter = cls._adapters.get(model_type)
        if adapter is None:
            raise ValueError(f"不支持的模型类型: {model_type}")
        return adapter

    @classmethod
    def register_adapter(cls, model_type: ModelType, adapter: BaseFeatureAdapter) -> None:
        """注册新的特征适配器"""
        cls._adapters[model_type] = adapter


# 便捷函数
def adapt_features(
    raw_features: dict[str, Any], model_type: ModelType = ModelType.V26_MINI
) -> AdaptationResult:
    """
    适配特征到指定模型类型

    Args:
        raw_features: V25.1 提取的原始特征
        model_type: 目标模型类型

    Returns:
        AdaptationResult: 适配结果
    """
    adapter = FeatureAdapterFactory.get_adapter(model_type)
    return adapter.adapt(raw_features)
