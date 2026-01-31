#!/usr/bin/env python3
"""
V79.000 Technical Feature Parser - 152维特征解析与赛前特征验证
================================================================

从 UltimateFeatureExtractor 拆分出来的特征解析模块。

核心功能：
1. PreMatchFeaturePlugin - 赛前特征验证插件
2. 特征白名单管理 (72个核心特征)
3. 动态特征前缀验证 (15个前缀)
4. 赛中特征黑名单过滤 (15个模式)

Author: V79.000 Engineering Team
Version: V79.000 "Technical Parser"
Date: 2026-01-25
"""

from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)


# =============================================================================
# V77.000: Pre-Match Feature White List (从 PreMatchFeatureExtractor 迁移)
# =============================================================================

# 赛前特征白名单 - 72个核心赛前特征
PRE_MATCH_FEATURE_WHITELIST = {
    # === 身价信息 (赛前已知) ===
    "home_market_value_total", "away_market_value_total",
    "home_market_value_avg", "away_market_value_avg",
    "market_value_gap", "market_value_ratio",

    # === 伤病信息 (赛前已知) ===
    "home_injury_count", "away_injury_count",
    "home_injury_core_count", "away_injury_core_count",
    "home_unavailable_count", "away_unavailable_count",
    "injury_count_gap", "unavailable_count_gap",

    # === 历史评分 (赛前已知) ===
    "home_rating_rolling_avg_5", "away_rating_rolling_avg_5",
    "home_rating_rolling_avg_3", "away_rating_rolling_avg_3",
    "home_rating_trend", "away_rating_trend",
    "rating_gap", "rating_trend_diff",

    # === 纪律信息 (赛前已知) ===
    "home_red_cards", "away_red_cards",
    "home_yellow_cards", "away_yellow_cards",
    "red_cards_gap", "yellow_cards_gap",

    # === 历史战绩 (赛前已知) ===
    "last_5_home_wins", "last_5_away_wins",
    "last_5_home_draws", "last_5_away_draws",
    "last_5_home_losses", "last_5_away_losses",
    "last_3_h2h_home_wins", "last_3_h2h_away_wins",
    "last_3_h2h_draws",
    "h2h_home_win_rate", "h2h_away_win_rate", "h2h_draw_rate",

    # === 主客优势 (赛前已知) ===
    "home_advantage", "away_disadvantage",
    "home_form", "away_form",

    # === 首发阵容 (赛前已知) ===
    "home_starting_avg_age", "away_starting_avg_age",
    "home_starting_avg_rating", "away_starting_avg_rating",
    "home_formation_strength", "away_formation_strength",

    # === 联赛排名 (赛前已知) ===
    "home_league_position", "away_league_position",
    "home_points_per_game", "away_points_per_game",
    "league_position_gap", "points_per_game_diff",
}

# V77.000: 允许的前缀模式 (用于动态特征验证)
ALLOWED_PREFIXES = {
    "last_", "h2h_", "rolling_",
    "market_value_", "injury_", "unavailable_",
    "rating_last_", "rating_rolling_", "rating_trend_",
    "home_starting_", "away_starting_",
    "home_league_", "away_league_",
    "home_rest_days", "away_rest_days", "home_is_busy", "away_is_busy",
    "home_unavailable_", "away_unavailable_", "diff_unavailable_",
    "home_drop_ratio", "draw_change_ratio", "away_change_ratio",
    "is_top_5_league", "diff_rest_days", "home_less_rest",
    "total_movement",
}

# V77.000: 黑名单模式 (赛中统计特征)
BLACKLIST_PATTERNS = {
    # 赛中统计
    "shots", "possession", "passes", "tackles", "interceptions",
    "clearances", "duels", "blocks", "saves", "big_chances",
    "xg", "expected_goal", "expected_assist",
    "total_", "synth_", "momentum_", "tempo_",
    # 赛后结果
    "score", "total_goals", "goal_difference", "winner",
}


# =============================================================================
# V77.000: Pre-Match Feature Plugin (验证插件)
# =============================================================================

class PreMatchFeaturePlugin:
    """
    V77.000/V79.000 赛前特征验证插件

    从 PreMatchFeatureExtractor 迁移而来，作为特征提取的验证层，
    确保所有提取的特征都符合赛前特征白名单要求。

    核心原则：
    - 只提取赛前30分钟能拿到的特征
    - 物理拆解 technical_features，拒绝赛中统计
    - 时间锚点：match_time - 30 minutes
    """

    def __init__(self, strict_mode: bool = True):
        """
        初始化验证插件

        Args:
            strict_mode: 严格模式 - 发现未知特征时记录警告
        """
        self.strict_mode = strict_mode
        self.extracted_count = 0
        self.rejected_count = 0
        self.unknown_features = set()

    def is_pre_match_feature(self, feature_name: str) -> tuple[bool, str]:
        """
        判断特征是否为赛前特征

        Returns:
            (is_pre_match, reason)
        """
        feature_lower = feature_name.lower().strip()

        # 1. 白名单直接通过
        if feature_lower in PRE_MATCH_FEATURE_WHITELIST:
            return True, "WHITELIST"

        # 2. 检查允许的前缀
        for prefix in ALLOWED_PREFIXES:
            if feature_lower.startswith(prefix):
                return True, f"ALLOWED_PREFIX: {prefix}"

        # 3. 黑名单直接拒绝
        for pattern in BLACKLIST_PATTERNS:
            if pattern in feature_lower:
                return False, f"BLACKLIST: {pattern}"

        # 4. 未知特征 - 根据模式判断
        if self.strict_mode:
            self.unknown_features.add(feature_name)

        # 默认拒绝（安全原则）
        return False, "UNKNOWN_PATTERN"

    def validate_and_filter_features(
        self,
        features: dict[str, Any],
        match_id: str | None = None,
        verbose: bool = False
    ) -> dict[str, Any]:
        """
        验证并过滤特征，只保留赛前特征

        Args:
            features: 原始特征字典
            match_id: 比赛 ID（用于日志）
            verbose: 是否打印详细信息

        Returns:
            纯净赛前特征字典
        """
        if not isinstance(features, dict):
            return {}

        validated_features = {}
        rejected = []

        for feature_name, feature_value in features.items():
            self.extracted_count += 1

            is_pre_match, reason = self.is_pre_match_feature(feature_name)

            if is_pre_match:
                validated_features[feature_name] = feature_value
            else:
                self.rejected_count += 1
                if verbose and len(rejected) < 10:
                    rejected.append((feature_name, reason))

        if verbose and rejected:
            match_str = f"match {match_id}" if match_id else "match"
            logger.debug(f"Rejected {len(rejected)} features for {match_str}:")
            for name, reason in rejected[:5]:
                logger.debug(f"  - {name}: {reason}")

        return validated_features

    def get_extraction_rate(self) -> float:
        """获取特征提取率"""
        if self.extracted_count == 0:
            return 0.0
        return (self.extracted_count - self.rejected_count) / self.extracted_count

    def get_unknown_features(self) -> set[str]:
        """获取未知特征集合"""
        return self.unknown_features.copy()

    def reset_stats(self):
        """重置统计"""
        self.extracted_count = 0
        self.rejected_count = 0
        self.unknown_features = set()


# =============================================================================
# Type Aliases
# =============================================================================

# 常用类型别名
FeatureDict = dict[str, float]
FeatureName = str
ValidationResult = tuple[bool, str]
