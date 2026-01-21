"""
V41.460 Pure Feature Filter - 纯净赛前特征过滤器
=================================================

严格时空隔离：100% 剔除赛中/赛后统计特征

V41.460 更新：
- 特征恢复：放行 rolling_*, last_*, h2h_* 历史特征
- 目标：将特征维度恢复到 150 维以上
- 明确区分：current_match_stat vs historical_rolling_avg

Author: V41.460 Data Science Team
Version: V41.460 "Balanced Calibration"
Date: 2026-01-21
"""

from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)


class PureFeatureFilter:
    """
    V41.410 纯净特征过滤器

    严格遵循 TDD 约束：
    - 测试驱动：tests/ai/test_temporal_integrity.py
    - 红线原则：任何数据泄露禁止合入主干
    """

    # === 红线黑名单 (与 TDD 测试保持一致) ===
    IN_GAME_STATS = {
        # 射门类
        "shots_total", "shots_on_target", "shots_off_target",
        "big_chances_created", "big_chances_missed", "saves",
        # 控球类
        "possession_percentage", "possession", "touches",
        # 传球类
        "passes_total", "passes_accurate", "pass_accuracy",
        "key_passes", "through_balls", "total_passes", "total_passes_total",
        "total_passes_accurate",
        # 防守类
        "tackles_won", "interceptions", "clearances", "blocks",
        "duels_won", "aerial_duels_won",
        # 进阶类
        "expected_goals", "expected_assists",
        "carries", "progressive_carries", "progressive_passes",
        # 犯规类
        "fouls", "fouls_won", "offsides", "corners",
        # 比率类 (赛中统计)
        "ratio_shots", "ratio_possession", "ratio_passes",
        "ratio_duels", "ratio_clearances",
        # V41.430 新增：total_* 统计（通常是赛中数据）
        "total_clearances", "total_big_chances_created", "total_shots_on_target",
        "total_shots_off_target", "total_shots_total", "total_shots_total_alt",
        "total_shots_blocked", "total_shots_woodwork",
        "total_tackles_won", "total_interceptions", "total_duels_won",
        "total_fouls", "total_corners", "total_offsides",
        "total_aerial_duels_won", "total_saves", "total_blocks",
        # V41.440 新增：合成特征（基于赛中数据）
        "synth_total_shots", "synth_total_passes",
        "momentum_mean", "momentum_std", "momentum_velocity", "momentum_acceleration",
        "tempo_total_shots", "tempo_total_passes",
    }

    IN_GAME_WITH_PREFIX = {
        "shots", "possession", "passes", "tackles", "interceptions",
        "clearances", "duels", "blocks", "saves", "big_chances",
        "expected_goals", "expected_assists", "carries",
        # xG 相关 (关键！)
        "xg", "expected_goals", "xa", "expected_assists",
        "npxg", "npxg_xa", "post_shot_xg",
        # V41.440 新增：合成特征前缀
        "synth_", "momentum_", "tempo_",
    }

    POST_GAME_RESULTS = {
        "home_score", "away_score", "total_goals",
        "goal_difference", "winner",
    }

    # 允许的前缀 (白名单) - V41.460 大幅扩展
    ALLOWED_PREFIXES = {
        # === 历史滚动窗口 (赛前已知) ===
        "last_", "h2h_", "rolling_",
        # === 身价信息 (赛前已知) ===
        "market_value_", "squad_value_", "team_value_",
        # === 伤病信息 (赛前已知) ===
        "injury_", "unavailable_", "suspended_",
        # === 历史评分 (赛前已知) ===
        "rating_last_", "rating_rolling_", "rating_trend_",
        # === 红牌历史 (赛前已知) ===
        "red_cards_last_", "yellow_cards_last_",
        # === V41.460 新增：更多历史模式 ===
        "home_form_", "away_form_",
        "home_last_", "away_last_",
        "diff_last_", "diff_rolling_", "diff_h2h_",
        # === 联赛排名 (赛前已知) ===
        "league_position_", "points_", "standings_",
        # === 特殊模式：允许 rolling_xg (历史 xG) ===
        # 注意：rolling_xg 是历史数据，不是当场统计
        "home_rolling_avg_xg_", "away_rolling_avg_xg_",
    }

    # V41.460: 完全允许的模式（这些模式表示历史数据）
    FULLY_ALLOWED_PATTERNS = {
        "rolling_avg_",  # 滚动平均
        "last_",        # 最近 N 场
        "h2h_",         # 历史交锋
        "form_",        # 状态趋势
    }

    def __init__(self, strict_mode: bool = True):
        """
        初始化过滤器

        Args:
            strict_mode: 严格模式 - 发现污染特征时记录警告
        """
        self.strict_mode = strict_mode
        self.filtered_count = 0
        self.total_count = 0

    def is_contaminated(self, feature_name: str) -> tuple[bool, str]:
        """
        检查特征是否被污染

        V41.460 更新：
        - 优先检查 FULLY_ALLOWED_PATTERNS
        - 明确区分 current_match_stat vs historical_rolling_avg

        Returns:
            (is_contaminated, reason)
        """
        feature_lower = feature_name.lower().strip()

        # V41.460 新增：0. 优先检查完全允许的模式（历史数据）
        for pattern in self.FULLY_ALLOWED_PATTERNS:
            if pattern in feature_lower:
                # 进一步检查：确保不是当场统计的伪装
                # 例如：rolling_shots_total (历史滚动平均) 应该允许
                # 但 shots_total (当场统计) 应该拒绝
                if pattern == "rolling_avg_":
                    # rolling_avg_xg, rolling_avg_rating 等是历史数据，允许
                    return False, ""
                elif pattern == "last_":
                    # last_5_xxx 是历史数据，允许
                    return False, ""
                elif pattern == "h2h_":
                    # h2h_xxx 是历史交锋，允许
                    return False, ""
                elif pattern == "form_":
                    # form_xxx 是状态趋势，允许
                    return False, ""

        # 1. 严格黑名单匹配
        if feature_lower in self.IN_GAME_STATS:
            return True, "IN_GAME_STATS"

        if feature_lower in self.POST_GAME_RESULTS:
            return True, "POST_GAME_RESULT"

        # 2. 主客队赛中统计检测
        for stat in self.IN_GAME_WITH_PREFIX:
            if f"home_{stat}" in feature_lower or f"away_{stat}" in feature_lower:
                has_allowed_prefix = any(
                    feature_lower.startswith(prefix)
                    for prefix in self.ALLOWED_PREFIXES
                )
                if not has_allowed_prefix:
                    return True, f"IN_GAME_STAT: {stat}"

        # 3. diff_xxx 模式检测
        if feature_lower.startswith("diff_"):
            # V41.460: 允许 diff_rolling_*, diff_last_*, diff_h2h_*
            for pattern in self.FULLY_ALLOWED_PATTERNS:
                if pattern in feature_lower:
                    return False, ""  # 历史差值特征，允许

            forbidden_diff_stats = {
                "shots", "possession", "passes", "tackles",
                "big_chances", "clearances", "duels"
            }
            for stat in forbidden_diff_stats:
                if stat in feature_lower:
                    return True, f"DIFF_IN_GAME: {stat}"

        # 4. ratio_xxx 模式检测 (更严格)
        if "ratio_" in feature_lower:
            # V41.460: 允许历史数据的 ratio
            for pattern in self.FULLY_ALLOWED_PATTERNS:
                if pattern in feature_lower:
                    return False, ""  # 历史 ratio，允许

            forbidden_in_ratio = {
                "shots", "possession", "passes", "tackles", "duels",
                "clearances", "interceptions", "blocks", "saves",
                "big_chances", "carries",
            }
            for stat in forbidden_in_ratio:
                if stat in feature_lower:
                    return True, f"RATIO_IN_GAME: {stat}"

        # 4.5 xG 相关特征检测（历史 vs 当场）
        xg_patterns = ["xg", "expected_goal", "npxg", "post_shot"]
        for pattern in xg_patterns:
            if pattern in feature_lower:
                # V41.460: rolling_xg 是历史数据，允许
                # 但 xg_single_match 是当场统计，拒绝
                if "rolling" in feature_lower or "last_" in feature_lower:
                    return False, ""  # 历史 xG，允许
                # 检查是否有其他允许的前缀
                has_allowed = any(
                    feature_lower.startswith(prefix)
                    for prefix in self.ALLOWED_PREFIXES
                )
                if not has_allowed:
                    return True, f"XG_STATISTIC: {pattern}"

        # 5. rating 特殊规则
        if "rating" in feature_lower:
            allowed_rating = any(
                feature_lower.startswith(prefix) or prefix in feature_lower
                for prefix in ["rating_last_", "rating_rolling_", "rating_trend_"]
            )
            if not allowed_rating:
                if feature_lower in ["home_team_rating", "away_team_rating", "team_rating"]:
                    return True, "POST_GAME_RATING"
                # V41.460: 允许 *_rolling_avg_5_rating 格式
                if "_rolling_avg_" in feature_lower or "_trend_" in feature_lower:
                    return False, ""  # 历史评分，允许
                if feature_lower.endswith("_rating") and not feature_lower.endswith("_rolling_avg_5"):
                    return True, "POST_GAME_RATING"

        return False, ""

    def filter_features(
        self,
        features: dict[str, Any],
        verbose: bool = False
    ) -> dict[str, Any]:
        """
        过滤特征字典，仅保留纯净赛前特征

        Args:
            features: 原始特征字典
            verbose: 是否打印详细信息

        Returns:
            纯净特征字典
        """
        filtered = {}
        rejected = []

        for name, value in features.items():
            self.total_count += 1
            is_bad, reason = self.is_contaminated(name)

            if is_bad:
                self.filtered_count += 1
                rejected.append((name, reason))
            else:
                filtered[name] = value

        if verbose and rejected:
            logger.warning(f"Filtered {len(rejected)} contaminated features:")
            for name, reason in rejected[:5]:  # 只显示前5个
                logger.warning(f"  - {name}: {reason}")
            if len(rejected) > 5:
                logger.warning(f"  ... and {len(rejected) - 5} more")

        return filtered

    def get_filter_rate(self) -> float:
        """获取过滤率"""
        if self.total_count == 0:
            return 0.0
        return self.filtered_count / self.total_count

    def reset_stats(self):
        """重置统计"""
        self.filtered_count = 0
        self.total_count = 0

    def get_allowed_features(self, all_features: list[str]) -> list[str]:
        """
        获取允许的特征列表

        Args:
            all_features: 所有特征名列表

        Returns:
            允许的特征名列表
        """
        allowed = []
        for name in all_features:
            is_bad, _ = self.is_contaminated(name)
            if not is_bad:
                allowed.append(name)
        return allowed


# 单例实例
_pure_filter_instance = None

def get_pure_filter() -> PureFeatureFilter:
    """获取纯净过滤器单例"""
    global _pure_filter_instance
    if _pure_filter_instance is None:
        _pure_filter_instance = PureFeatureFilter()
    return _pure_filter_instance
