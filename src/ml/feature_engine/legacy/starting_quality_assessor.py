#!/usr/bin/env python3
"""
V79.200 Starting Quality Assessor - 首发质量评估器
=====================================================

V79.200 更新:
- 使用 InjuryDataExtractor (injury_parser.py) 进行深层 JSON 解析
- 专注于业务逻辑，不再处理路径导航

核心功能：
1. 计算缺阵球员战力损失
2. 评估首发阵容平均年龄
3. 评估首发阵容平均评分
4. 评估阵容强度

Author: V79.200 Engineering Team
Version: V79.200 "Business Logic Focused"
Date: 2026-01-25
"""

from __future__ import annotations

from dataclasses import dataclass
import logging
from typing import Any

import yaml

from src.config.config_loader import get_hyper_parameters_config
from src.ml.feature_engine.legacy.injury_parser import InjuryDataExtractor

logger = logging.getLogger(__name__)


# =============================================================================
# Configuration
# =============================================================================

@dataclass
class StartingQualityAssessorConfig:
    """首发质量评估器配置"""

    star_market_value: float = 30_000_000  # 3000万欧元以上视为球星

    # 首发阵容质量阈值
    min_starting_avg_age: float = 18.0  # 最小平均年龄
    max_starting_avg_age: float = 35.0  # 最大平均年龄
    min_starting_avg_rating: float = 5.0  # 最小平均评分


DEFAULT_STARTING_QUALITY_CONFIG = StartingQualityAssessorConfig()


# =============================================================================
# Starting Quality Assessor
# =============================================================================

class StartingQualityAssessor:
    """
    V79.200 首发质量评估器

    专注于评估首发阵容的质量，包括缺阵战力损失、首发年龄、评分等。
    V79.200: 使用 InjuryDataExtractor 处理深层 JSON 解析。
    """

    def __init__(self, config: StartingQualityAssessorConfig | None = None):
        """
        初始化首发质量评估器

        Args:
            config: 配置对象
        """
        self.config = config or DEFAULT_STARTING_QUALITY_CONFIG
        self.injury_extractor = InjuryDataExtractor()

        # 从 hyper_parameters.yaml 加载配置（如果可用）
        try:
            hyper_params = get_hyper_parameters_config()
            self.config.star_market_value = hyper_params.star_market_value
        except (FileNotFoundError, yaml.YAMLError, KeyError, AttributeError) as e:
            logger.debug(f"Using default starting quality config: {e}")

    def calculate_unavailable_power_loss(
        self,
        unavailable_players: list[dict[str, Any]]
    ) -> dict[str, Any]:
        """
        计算缺阵球员的战力损失

        Args:
            unavailable_players: 缺阵球员列表

        Returns:
            战力损失统计字典
        """
        if not unavailable_players:
            return {
                "total_count": 0,
                "injury_count": 0,
                "suspension_count": 0,
                "other_count": 0,
                "total_market_value": 0.0,
                "avg_market_value": 0.0,
                "star_count": 0,  # 身价 > 30M 的球星数
            }

        injury_count = 0
        suspension_count = 0
        other_count = 0
        total_market_value = 0.0
        star_count = 0
        players_with_mv = 0

        for player in unavailable_players:
            unavailability = player.get("unavailability", {})
            unavail_type = unavailability.get("type", "unknown").lower()

            # 分类统计
            if "injury" in unavail_type:
                injury_count += 1
            elif "suspension" in unavail_type or "suspended" in unavail_type:
                suspension_count += 1
            else:
                other_count += 1

            # 统计身价
            mv = player.get("marketValue")
            if mv and isinstance(mv, (int, float)):
                total_market_value += mv
                players_with_mv += 1
                if mv >= self.config.star_market_value:
                    star_count += 1

        avg_mv = total_market_value / players_with_mv if players_with_mv > 0 else 0.0

        return {
            "total_count": len(unavailable_players),
            "injury_count": injury_count,
            "suspension_count": suspension_count,
            "other_count": other_count,
            "total_market_value": total_market_value,
            "avg_market_value": avg_mv,
            "star_count": star_count,
        }

    def extract_unavailable_features(
        self,
        l2_raw_json: dict[str, Any] | str | None
    ) -> dict[str, float]:
        """
        V79.200: 从 l2_raw_json 提取缺阵特征（委托给 InjuryDataExtractor）

        Args:
            l2_raw_json: 原始 JSON 数据

        Returns:
            缺阵特征字典
        """
        features = {}

        # V79.200: 使用 InjuryDataExtractor 提取数据
        home_unavailable = self.injury_extractor.extract_unavailable_players(l2_raw_json, "home")
        away_unavailable = self.injury_extractor.extract_unavailable_players(l2_raw_json, "away")

        # 计算主队缺阵损失
        home_loss = self.calculate_unavailable_power_loss(home_unavailable)
        features.update({
            f"home_unavailable_{k}": float(v)
            for k, v in home_loss.items()
        })

        # 计算客队缺阵损失
        away_loss = self.calculate_unavailable_power_loss(away_unavailable)
        features.update({
            f"away_unavailable_{k}": float(v)
            for k, v in away_loss.items()
        })

        # 差值特征
        features.update({
            "diff_unavailable_count": float(home_loss["total_count"] - away_loss["total_count"]),
            "diff_unavailable_mv": float(home_loss["total_market_value"] - away_loss["total_market_value"]),
            "diff_unavailable_stars": float(home_loss["star_count"] - away_loss["star_count"]),
            "home_more_unavailable": 1.0 if home_loss["total_count"] > away_loss["total_count"] else 0.0,
        })

        return features

    def calculate_starting_quality_features(
        self,
        l2_raw_json: dict[str, Any] | str | None,
        team_side: str = "home"  # "home" or "away"
    ) -> dict[str, float]:
        """
        V79.200: 计算首发阵容质量特征（委托给 InjuryDataExtractor）

        Args:
            l2_raw_json: 原始 JSON 数据
            team_side: 球队方 ("home" 或 "away")

        Returns:
            首发质量特征字典
        """
        features = {}

        # V79.200: 使用 InjuryDataExtractor 提取首发数据
        starting_data = self.injury_extractor.extract_starting_lineup(l2_raw_json, team_side)

        if not starting_data:
            # 没有首发数据，返回默认值
            return {
                f"{team_side}_starting_avg_age": 0.0,
                f"{team_side}_starting_avg_rating": 0.0,
                f"{team_side}_formation_strength": 0.0,
            }

        # 计算平均年龄
        ages = [self.injury_extractor.extract_player_attribute(p, "age", 0)
                for p in starting_data if self.injury_extractor.extract_player_attribute(p, "age")]
        avg_age = sum(ages) / len(ages) if ages else 0.0

        # 计算平均评分
        ratings = [self.injury_extractor.extract_player_attribute(p, "rating", 0)
                   for p in starting_data if self.injury_extractor.extract_player_attribute(p, "rating")]
        avg_rating = sum(ratings) / len(ratings) if ratings else 0.0

        # 计算阵容强度（基于评分和身价）
        strength_score = 0.0
        if avg_rating > 0:
            # 基础强度：平均评分 / 10
            strength_score = (avg_rating / 10.0) * 100

        features.update({
            f"{team_side}_starting_avg_age": float(avg_age),
            f"{team_side}_starting_avg_rating": float(avg_rating),
            f"{team_side}_formation_strength": float(strength_score),
        })

        return features

    def cleanup(self) -> None:
        """清理资源（供子类扩展）"""


# =============================================================================
# Utility Functions
# =============================================================================

def extract_unavailable_features_for_match(
    l2_raw_json: dict[str, Any] | str | None,
    assessor: StartingQualityAssessor | None = None
) -> dict[str, float]:
    """
    便捷函数：提取比赛的缺阵特征

    Args:
        l2_raw_json: 原始 JSON 数据
        assessor: 首发质量评估器实例（可选）

    Returns:
        缺阵特征字典
    """
    if assessor is None:
        assessor = StartingQualityAssessor()

    return assessor.extract_unavailable_features(l2_raw_json)


# =============================================================================
# Type Aliases
# =============================================================================

# 常用类型别名
PlayerData = dict[str, Any]
UnavailableStats = dict[str, Any]
StartingFeatures = dict[str, float]
