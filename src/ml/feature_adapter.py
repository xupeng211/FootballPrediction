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

import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import Enum
from typing import Any

import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)


class ModelType(str, Enum):
    """支持的模型类型"""

    V19_ROLLING = "v19_rolling"  # 48 维滚动特征
    V26_BASELINE = "v26_baseline"  # 6000 维特征
    V26_MINI = "v26_mini"  # 微型特征集（用于快速验证）
    V26_5_PRODUCTION = "v26_5_production"  # V26.5 生产模型（37 维真实特征）
    V26_6_PRE_MATCH = "v26_6_pre_match"  # V26.6 真赛前模型（19 维，无泄露）


@dataclass
class AdaptationResult:
    """
    特征适配结果

    Attributes:
        success: 是否成功
        features: 适配后的特征矩阵
        feature_names: 特征名称列表
        missing_features: 缺失的特征列表
        errors: 错误信息
    """

    success: bool
    features: pd.DataFrame | np.ndarray | None
    feature_names: list[str]
    missing_features: list[str]
    errors: list[str]

    def to_dict(self) -> dict:
        """转换为字典"""
        return {
            "success": self.success,
            "feature_count": len(self.feature_names),
            "missing_features": self.missing_features,
            "errors": self.errors,
        }


class BaseFeatureAdapter(ABC):
    """特征适配器基类"""

    @abstractmethod
    def adapt(self, raw_features: dict[str, Any]) -> AdaptationResult:
        """
        将原始特征适配为目标模型所需的特征

        Args:
            raw_features: V25.1 提取的原始特征字典

        Returns:
            AdaptationResult: 适配结果
        """
        pass

    @abstractmethod
    def get_required_features(self) -> list[str]:
        """获取目标模型所需的特征列表"""
        pass


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
            home_score = self._safe_get(raw_features, "header", "teams", "home", "score", default=0)
            away_score = self._safe_get(raw_features, "header", "teams", "away", "score", default=0)

            # 统计数据
            home_xg = self._safe_get(raw_features, "content", "stats", "home", "xg", default=1.0)
            away_xg = self._safe_get(raw_features, "content", "stats", "away", "xg", default=1.0)

            home_shots = self._safe_get(raw_features, "content", "stats", "home", "shotsTotal", "total", default=10)
            away_shots = self._safe_get(raw_features, "content", "stats", "away", "shotsTotal", "total", default=10)

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
            logger.error(f"特征适配失败: {e}")
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
            adapted["home_score"] = self._safe_get(raw_features, "header", "teams", "home", "score", default=0)
            adapted["away_score"] = self._safe_get(raw_features, "header", "teams", "away", "score", default=0)

            home_poss = (
                self._safe_get(raw_features, "content", "stats", "home", "possession", "percentage", default=50) / 100
            )
            adapted["home_possession"] = home_poss
            adapted["away_possession"] = 1 - home_poss

            adapted["home_shots_total"] = self._safe_get(
                raw_features, "content", "stats", "home", "shotsTotal", "total", default=10
            )
            adapted["away_shots_total"] = self._safe_get(
                raw_features, "content", "stats", "away", "shotsTotal", "total", default=10
            )

            adapted["home_xg"] = self._safe_get(raw_features, "content", "stats", "home", "xg", default=1.0)
            adapted["away_xg"] = self._safe_get(raw_features, "content", "stats", "away", "xg", default=1.0)

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
            logger.error(f"微型特征适配失败: {e}")
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


class V26_5_ProductionAdapter(BaseFeatureAdapter):
    """
    V26.5 生产特征适配器

    将 V25.1 的原始特征映射到 V26.5 训练使用的 37 维特征集。
    使用 SQL 统计引擎动态计算滚动特征。
    """

    # V26.5 完整特征集 (37个)
    V26_5_FEATURES = [
        # 滚动特征 (8个) - 动态计算
        "rolling_xg_home",
        "rolling_xg_away",
        "rolling_shots_on_target_home",
        "rolling_shots_on_target_away",
        "rolling_possession_home",
        "rolling_possession_away",
        "rolling_team_rating_home",
        "rolling_team_rating_away",
        # 当前比赛特征 (8个) - 从原始 JSON 提取
        "home_xg",
        "away_xg",
        "home_possession",
        "away_possession",
        "home_shots_on_target",
        "away_shots_on_target",
        "home_team_rating",
        "away_team_rating",
        # 积分榜特征 (7个) - 使用默认值
        "home_table_position",
        "away_table_position",
        "table_position_diff",
        "home_points",
        "away_points",
        "points_diff",
        "home_recent_form_points",
        # 高级特征 (6个) - 使用默认值
        "raw_elo_gap",
        "adjusted_elo_gap",
        "home_fatigue_index",
        "away_fatigue_index",
        "fatigue_diff",
        "home_relegation_incentive",
    ]

    def adapt(self, raw_features: dict[str, Any]) -> AdaptationResult:
        """
        将原始特征适配为 V26.5 特征集

        使用 SQL 统计引擎动态计算滚动特征，而非硬编码默认值。
        """
        errors: list[str] = []
        missing_features: list[str] = []
        adapted = {}

        try:
            # 提取球队名称
            home_team = self._safe_get(raw_features, "header", "teams", "home", "name", default="")
            away_team = self._safe_get(raw_features, "header", "teams", "away", "name", default="")

            # 提取比赛时间（用于历史数据过滤）
            match_time = None
            try:
                match_time_str = self._safe_get(raw_features, "header", "status", "startTimeStr", default=None)
                if match_time_str:
                    from datetime import datetime

                    match_time = datetime.fromisoformat(match_time_str.replace("Z", "+00:00")).isoformat()
            except:
                pass

            # 动态获取滚动特征
            from src.database.schema_manager import SchemaManager

            home_stats = SchemaManager.get_team_rolling_stats(
                team_name=home_team, n_matches=5, before_match_time=match_time
            )
            away_stats = SchemaManager.get_team_rolling_stats(
                team_name=away_team, n_matches=5, before_match_time=match_time
            )

            logger.debug(
                f"滚动统计 [{home_team}]: xg={home_stats['rolling_xg']:.2f}, "
                f"shots={home_stats['rolling_shots_on_target']:.1f}, "
                f"poss={home_stats['rolling_possession']:.1f} ({home_stats['matches_count']} 场)"
            )
            logger.debug(
                f"滚动统计 [{away_team}]: xg={away_stats['rolling_xg']:.2f}, "
                f"shots={away_stats['rolling_shots_on_target']:.1f}, "
                f"poss={away_stats['rolling_possession']:.1f} ({away_stats['matches_count']} 场)"
            )

            # 从原始 JSON 提取当前比赛特征
            # 支持两种数据格式:
            # 1. V28 格式: content.stats.home.xg, content.stats.home.possession.percentage
            # 2. V51 格式 (FotMob API): content.stats.Periods.All.stats (嵌套数组格式)

            # 尝试方法 1: 简单格式 (V28)
            home_xg = self._safe_get(raw_features, "content", "stats", "home", "xg", default=None)
            away_xg = self._safe_get(raw_features, "content", "stats", "away", "xg", default=None)

            # 如果简单格式失败，尝试方法 2: FotMob API 格式 (V51)
            if home_xg is None or away_xg is None:
                home_xg, away_xg = self._extract_fotmob_stat(
                    raw_features, "expected_goals", default_home=1.0, default_away=1.0
                )
                home_possession, away_possession = self._extract_fotmob_stat(
                    raw_features, "BallPossesion", default_home=50.0, default_away=50.0
                )
                home_shots, away_shots = self._extract_fotmob_stat(
                    raw_features, "total_shots", default_home=10.0, default_away=10.0
                )
            else:
                # 使用简单格式
                home_possession = self._safe_get(
                    raw_features, "content", "stats", "home", "possession", "percentage", default=50
                )
                away_possession = self._safe_get(
                    raw_features, "content", "stats", "away", "possession", "percentage", default=50
                )

                home_shots = self._safe_get(raw_features, "content", "stats", "home", "shotsTotal", "total", default=10)
                away_shots = self._safe_get(raw_features, "content", "stats", "away", "shotsTotal", "total", default=10)

            # 估算射正次数（约 40% 的总射门）
            home_shots_on_target = home_shots * 0.4
            away_shots_on_target = away_shots * 0.4

            # 构建 37 维特征向量（使用动态滚动特征）
            adapted = {
                # 滚动特征 - 动态计算
                "rolling_xg_home": home_stats["rolling_xg"],
                "rolling_xg_away": away_stats["rolling_xg"],
                "rolling_shots_on_target_home": home_stats["rolling_shots_on_target"],
                "rolling_shots_on_target_away": away_stats["rolling_shots_on_target"],
                "rolling_possession_home": home_stats["rolling_possession"],
                "rolling_possession_away": away_stats["rolling_possession"],
                "rolling_team_rating_home": 6.7,  # 暂时保留默认值
                "rolling_team_rating_away": 6.6,  # 暂时保留默认值
                # 当前比赛特征 - 从原始数据提取
                "home_xg": home_xg,
                "away_xg": away_xg,
                "home_possession": home_possession,
                "away_possession": away_possession,
                "home_shots_on_target": home_shots_on_target,
                "away_shots_on_target": away_shots_on_target,
                "home_team_rating": 6.7,  # 暂时保留默认值
                "away_team_rating": 6.6,  # 暂时保留默认值
                # 积分榜特征 - 使用默认值
                "home_table_position": 10,
                "away_table_position": 10,
                "table_position_diff": 0,
                "home_points": 30,
                "away_points": 30,
                "points_diff": 0,
                "home_recent_form_points": 6,
                # 高级特征 - 使用默认值
                "raw_elo_gap": 0,
                "adjusted_elo_gap": 0,
                "home_fatigue_index": 0.5,
                "away_fatigue_index": 0.5,
                "fatigue_diff": 0,
                "home_relegation_incentive": 0,
            }

            # 检查缺失特征
            for feat in self.V26_5_FEATURES:
                if feat not in adapted:
                    missing_features.append(feat)

            success = len(missing_features) == 0

            if not success:
                errors.append(f"Missing {len(missing_features)} features")

            # 构建特征矩阵
            feature_values = [adapted.get(feat, 0) for feat in self.V26_5_FEATURES]
            feature_matrix = pd.DataFrame([feature_values], columns=self.V26_5_FEATURES)

            return AdaptationResult(
                success=success,
                features=feature_matrix,
                feature_names=self.V26_5_FEATURES,
                missing_features=missing_features,
                errors=errors,
            )

        except Exception as e:
            logger.error(f"V26.5 特征适配失败: {e}")
            return AdaptationResult(
                success=False,
                features=None,
                feature_names=[],
                missing_features=self.V26_5_FEATURES,
                errors=[str(e)],
            )

    def _extract_fotmob_stat(
        self, raw_data: dict, stat_key: str, default_home: float = 0.0, default_away: float = 0.0
    ) -> tuple[float, float]:
        """
        从 FotMob API 格式的 stats 中提取统计数据

        API 格式:
        {
          "content": {
            "stats": {
              "Periods": {
                "All": {
                  "stats": [
                    {
                      "key": "top_stats",
                      "stats": [
                        {"key": "BallPossesion", "stats": [54, 46]},
                        {"key": "expected_goals", "stats": ["1.12", "0.88"]},
                        {"key": "total_shots", "stats": [11, 12]}
                      ]
                    }
                  ]
                }
              }
            }
          }
        }

        Args:
            raw_data: 原始 JSON 数据
            stat_key: 要查找的统计 key (如 "expected_goals", "BallPossesion")
            default_home: 主队默认值
            default_away: 客队默认值

        Returns:
            (home_value, away_value)
        """
        try:
            stats_container = self._safe_get(raw_data, "content", "stats", "Periods", "All", "stats", default=[])
            if not stats_container:
                return default_home, default_away

            # 遍历 stats 数组
            for container in stats_container:
                if not isinstance(container, dict):
                    continue
                stats_list = container.get("stats", [])
                if not isinstance(stats_list, list):
                    continue

                # 在 stats 列表中查找目标 stat_key
                for stat_item in stats_list:
                    if not isinstance(stat_item, dict):
                        continue
                    if stat_item.get("key") == stat_key:
                        values = stat_item.get("stats", [])
                        if isinstance(values, list) and len(values) >= 2:
                            # 尝试转换为浮点数
                            try:
                                home_val = float(values[0])
                                away_val = float(values[1])
                                return home_val, away_val
                            except (ValueError, TypeError):
                                pass

            return default_home, default_away

        except Exception as e:
            logger.debug(f"提取 stat '{stat_key}' 失败: {e}")
            return default_home, default_away

    def get_required_features(self) -> list[str]:
        """获取 V26.5 特征集"""
        return self.V26_5_FEATURES.copy()

    def _safe_get(self, data: dict, *keys, default=None) -> Any:
        """安全获取嵌套字典值"""
        for key in keys:
            if isinstance(data, dict) and key in data:
                data = data[key]
            else:
                return default
        return data


class V26_6_PreMatchAdapter(BaseFeatureAdapter):
    """
    V26.6 真赛前特征适配器（无数据泄露）

    ⚠️ 防泄露设计原则：
    - 严格禁止使用任何比赛中的实时统计数据
    - 只能使用赛前已知的信息：
      * 滚动特征（历史平均值）
      * 积分榜数据（赛前已知）
      * ELO 评分（赛前已知）
      * 赛程密集度（可从赛程表计算）

    移除的泄露特征：
    - home_xg, away_xg (预期进球，赛中统计)
    - home_possession, away_possession (控球率，赛中统计)
    - home_shots_on_target, away_shots_on_target (射正，赛中统计)
    - home_team_rating, away_team_rating (赛中评分)
    """

    # V26.6 真赛前特征集 (19个) - 无泄露
    V26_6_FEATURES = [
        # 滚动特征 (8个) - 历史平均值，安全
        "rolling_xg_home",
        "rolling_xg_away",
        "rolling_shots_on_target_home",
        "rolling_shots_on_target_away",
        "rolling_possession_home",
        "rolling_possession_away",
        "rolling_team_rating_home",
        "rolling_team_rating_away",
        # 积分榜特征 (7个) - 赛前已知，安全
        "home_table_position",
        "away_table_position",
        "table_position_diff",
        "home_points",
        "away_points",
        "points_diff",
        "home_recent_form_points",
        # 高级特征 (4个) - 赛前可计算，安全
        "raw_elo_gap",
        "adjusted_elo_gap",
        "home_fatigue_index",
        "away_fatigue_index",
        "fatigue_diff",
        # ⚠️ 移除：home_relegation_incentive (数据不完整)
    ]

    def adapt(self, raw_features: dict[str, Any]) -> AdaptationResult:
        """
        将原始特征适配为 V26.6 真赛前特征集

        严格只使用赛前已知信息，拒绝任何赛中数据。
        """
        errors: list[str] = []
        missing_features: list[str] = []
        adapted = {}

        try:
            # 提取球队名称
            home_team = self._safe_get(raw_features, "header", "teams", "home", "name", default="")
            away_team = self._safe_get(raw_features, "header", "teams", "away", "name", default="")

            # 提取比赛时间（用于历史数据过滤）
            match_time = None
            try:
                match_time_str = self._safe_get(raw_features, "header", "status", "startTimeStr", default=None)
                if match_time_str:
                    from datetime import datetime

                    match_time = datetime.fromisoformat(match_time_str.replace("Z", "+00:00")).isoformat()
            except:
                pass

            # 动态获取滚动特征（历史平均值）
            from src.database.schema_manager import SchemaManager

            home_stats = SchemaManager.get_team_rolling_stats(
                team_name=home_team, n_matches=5, before_match_time=match_time
            )
            away_stats = SchemaManager.get_team_rolling_stats(
                team_name=away_team, n_matches=5, before_match_time=match_time
            )

            logger.debug(
                f"[V26.6] 滚动统计 [{home_team}]: xg={home_stats['rolling_xg']:.2f}, "
                f"shots={home_stats['rolling_shots_on_target']:.1f}, "
                f"poss={home_stats['rolling_possession']:.1f} ({home_stats['matches_count']} 场)"
            )
            logger.debug(
                f"[V26.6] 滚动统计 [{away_team}]: xg={away_stats['rolling_xg']:.2f}, "
                f"shots={away_stats['rolling_shots_on_target']:.1f}, "
                f"poss={away_stats['rolling_possession']:.1f} ({away_stats['matches_count']} 场)"
            )

            # ⚠️ 防泄露：不再提取任何本场比赛的实时统计数据！
            # 以下特征已从 V26.5 中移除：
            # - home_xg, away_xg (预期进球，赛中统计)
            # - home_possession, away_possession (控球率，赛中统计)
            # - home_shots_on_target, away_shots_on_target (射正，赛中统计)
            # - home_team_rating, away_team_rating (赛中评分)

            # 动态获取积分榜特征
            home_standings = SchemaManager.get_team_standings(team_name=home_team, before_match_time=match_time)
            away_standings = SchemaManager.get_team_standings(team_name=away_team, before_match_time=match_time)

            # 动态计算 ELO 评分
            elo_ratings = SchemaManager.get_elo_ratings(team_names=[home_team, away_team], before_match_time=match_time)
            home_elo = elo_ratings.get(home_team, 1500.0)
            away_elo = elo_ratings.get(away_team, 1500.0)

            # 动态计算疲劳度指数
            if match_time:
                home_fatigue = SchemaManager.get_team_fatigue_index(
                    team_name=home_team, match_time=match_time, lookback_days=7
                )
                away_fatigue = SchemaManager.get_team_fatigue_index(
                    team_name=away_team, match_time=match_time, lookback_days=7
                )
            else:
                home_fatigue = 0.5
                away_fatigue = 0.5

            # rolling_team_rating: 基于滚动统计中的 xg 和控球率估算
            # 这是一个综合实力评分，不是赛中评分
            home_rating = (
                home_stats["rolling_xg"] * 0.4
                + home_stats["rolling_possession"] / 100 * 0.3
                + home_stats["rolling_shots_on_target"] / 10 * 0.3
            ) * 2  # 归一化到 0-10 范围
            away_rating = (
                away_stats["rolling_xg"] * 0.4
                + away_stats["rolling_possession"] / 100 * 0.3
                + away_stats["rolling_shots_on_target"] / 10 * 0.3
            ) * 2

            # 构建 19 维真赛前特征向量（全动态）
            adapted = {
                # 滚动特征 - 历史平均值（安全）
                "rolling_xg_home": home_stats["rolling_xg"],
                "rolling_xg_away": away_stats["rolling_xg"],
                "rolling_shots_on_target_home": home_stats["rolling_shots_on_target"],
                "rolling_shots_on_target_away": away_stats["rolling_shots_on_target"],
                "rolling_possession_home": home_stats["rolling_possession"],
                "rolling_possession_away": away_stats["rolling_possession"],
                "rolling_team_rating_home": min(10.0, max(0.0, home_rating)),
                "rolling_team_rating_away": min(10.0, max(0.0, away_rating)),
                # 积分榜特征 - 动态计算（安全）
                "home_table_position": home_standings["position"],
                "away_table_position": away_standings["position"],
                "table_position_diff": home_standings["position"] - away_standings["position"],
                "home_points": home_standings["points"],
                "away_points": away_standings["points"],
                "points_diff": home_standings["points"] - away_standings["points"],
                "home_recent_form_points": home_standings["recent_form_points"],
                # 高级特征 - 动态计算（安全）
                "raw_elo_gap": home_elo - away_elo,
                "adjusted_elo_gap": (home_elo - away_elo) * 0.1,  # 调整后的 ELO 差距
                "home_fatigue_index": home_fatigue,
                "away_fatigue_index": away_fatigue,
                "fatigue_diff": home_fatigue - away_fatigue,
            }

            # 检查缺失特征
            for feat in self.V26_6_FEATURES:
                if feat not in adapted:
                    missing_features.append(feat)

            success = len(missing_features) == 0

            if not success:
                errors.append(f"Missing {len(missing_features)} features")

            # 构建特征矩阵
            feature_values = [adapted.get(feat, 0) for feat in self.V26_6_FEATURES]
            feature_matrix = pd.DataFrame([feature_values], columns=self.V26_6_FEATURES)

            return AdaptationResult(
                success=success,
                features=feature_matrix,
                feature_names=self.V26_6_FEATURES,
                missing_features=missing_features,
                errors=errors,
            )

        except Exception as e:
            logger.error(f"V26.6 特征适配失败: {e}")
            return AdaptationResult(
                success=False,
                features=None,
                feature_names=[],
                missing_features=self.V26_6_FEATURES,
                errors=[str(e)],
            )

    def get_required_features(self) -> list[str]:
        """获取 V26.6 真赛前特征集"""
        return self.V26_6_FEATURES.copy()

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
def adapt_features(raw_features: dict[str, Any], model_type: ModelType = ModelType.V26_MINI) -> AdaptationResult:
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
