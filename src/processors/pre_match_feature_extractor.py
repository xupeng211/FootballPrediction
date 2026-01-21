"""
V41.450 Pre-Match Feature Extractor - 赛前特征提取器
====================================================

物理拆解 technical_features：
- 只提取赛前30分钟能拿到的特征
- 100% 剔除赛中/赛后统计数据
- 专注赛前已知信息：身价、伤病、历史评分、首发阵容

Author: V41.450 Data Science Team
Version: V41.450 "Deep Temporal Alignment"
Date: 2026-01-21
"""

from __future__ import annotations

import json
import logging
from typing import Any

logger = logging.getLogger(__name__)


# =============================================================================
# Pre-Match Feature White List (赛前特征白名单)
# =============================================================================

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

# V41.450 滚动特征白名单 (历史数据，赛前已知)
ROLLING_FEATURE_WHITELIST = {
    "last_5_", "last_3_", "rolling_", "h2h_",
    "rating_last_", "rating_rolling_", "rating_trend_",
}

# V41.450 允许的前缀模式
ALLOWED_PREFIXES = {
    "last_", "h2h_", "rolling_",
    "market_value_", "injury_", "unavailable_",
    "rating_last_", "rating_rolling_", "rating_trend_",
    "home_starting_", "away_starting_",
    "home_league_", "away_league_",
}


# =============================================================================
# Pre-Match Feature Extractor
# =============================================================================

class PreMatchFeatureExtractor:
    """
    V41.450 赛前特征提取器

    核心原则：
    - 只提取赛前30分钟能拿到的特征
    - 物理拆解 technical_features，拒绝赛中统计
    - 时间锚点：match_time - 30 minutes
    """

    def __init__(self, strict_mode: bool = True):
        """
        初始化提取器

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
        BLACKLIST_PATTERNS = {
            # 赛中统计
            "shots", "possession", "passes", "tackles", "interceptions",
            "clearances", "duels", "blocks", "saves", "big_chances",
            "xg", "expected_goal", "expected_assist",
            "total_", "synth_", "momentum_", "tempo_",
            # 赛后结果
            "score", "total_goals", "goal_difference", "winner",
        }

        for pattern in BLACKLIST_PATTERNS:
            if pattern in feature_lower:
                return False, f"BLACKLIST: {pattern}"

        # 4. 未知特征 - 根据模式判断
        if self.strict_mode:
            self.unknown_features.add(feature_name)

        # 默认拒绝（安全原则）
        return False, "UNKNOWN_PATTERN"

    def extract_from_technical_features(
        self,
        technical_features: dict[str, Any] | str | None,
        match_id: str | None = None,
        verbose: bool = False
    ) -> dict[str, Any]:
        """
        从 technical_features 中提取纯赛前特征

        Args:
            technical_features: 技术特征（dict 或 JSON 字符串）
            match_id: 比赛 ID（用于日志）
            verbose: 是否打印详细信息

        Returns:
            纯净赛前特征字典
        """
        # 解析 JSON 字符串
        if isinstance(technical_features, str):
            try:
                technical_features = json.loads(technical_features)
            except json.JSONDecodeError as e:
                logger.warning(f"Failed to parse technical_features for match {match_id}: {e}")
                return {}

        if not isinstance(technical_features, dict):
            return {}

        pre_match_features = {}
        rejected = []

        for feature_name, feature_value in technical_features.items():
            self.extracted_count += 1

            is_pre_match, reason = self.is_pre_match_feature(feature_name)

            if is_pre_match:
                pre_match_features[feature_name] = feature_value
            else:
                self.rejected_count += 1
                if verbose and len(rejected) < 10:
                    rejected.append((feature_name, reason))

        if verbose and rejected:
            match_str = f"match {match_id}" if match_id else "match"
            logger.debug(f"Rejected {len(rejected)} features for {match_str}:")
            for name, reason in rejected[:5]:
                logger.debug(f"  - {name}: {reason}")

        return pre_match_features

    def extract_from_golden_features(
        self,
        golden_features: dict[str, Any] | str | None,
        verbose: bool = False
    ) -> dict[str, Any]:
        """
        从 golden_features 中提取纯赛前特征

        golden_features 通常是 V41.390 提取的高级特征
        需要严格过滤，确保不包含赛中数据
        """
        # 解析 JSON 字符串
        if isinstance(golden_features, str):
            try:
                golden_features = json.loads(golden_features)
            except json.JSONDecodeError:
                return {}

        if not isinstance(golden_features, dict):
            return {}

        pre_match_features = {}
        for feature_name, feature_value in golden_features.items():
            is_pre_match, _ = self.is_pre_match_feature(feature_name)
            if is_pre_match:
                pre_match_features[feature_name] = feature_value

        return pre_match_features

    def extract_combined_features(
        self,
        technical_features: dict[str, Any] | str | None = None,
        golden_features: dict[str, Any] | str | None = None,
        match_id: str | None = None,
        verbose: bool = False
    ) -> dict[str, Any]:
        """
        提取组合特征（technical + golden）

        Args:
            technical_features: 技术特征
            golden_features: 黄金特征
            match_id: 比赛 ID
            verbose: 是否打印详细信息

        Returns:
            合并后的纯净赛前特征
        """
        tech_pre = self.extract_from_technical_features(
            technical_features, match_id, verbose
        )
        gold_pre = self.extract_from_golden_features(
            golden_features, verbose
        )

        # 合并特征（golden 优先级更高）
        combined = dict(tech_pre)
        combined.update(gold_pre)

        return combined

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
# Singleton Instance
# =============================================================================

_pre_match_extractor_instance = None


def get_pre_match_extractor() -> PreMatchFeatureExtractor:
    """获取赛前特征提取器单例"""
    global _pre_match_extractor_instance
    if _pre_match_extractor_instance is None:
        _pre_match_extractor_instance = PreMatchFeatureExtractor()
    return _pre_match_extractor_instance


# =============================================================================
# Usage Example
# =============================================================================

if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG)

    # 模拟 technical_features (包含赛中数据)
    sample_tech = {
        # 赛前特征
        "home_market_value_total": 150_000_000,
        "away_market_value_total": 120_000_000,
        "home_injury_count": 2,
        "home_rating_rolling_avg_5": 6.8,
        # 赛中数据（必须剔除）
        "home_total_passes": 520,
        "away_total_shots": 12,
        "home_synth_total_shots": 15,
        "momentum_mean": 0.5,
    }

    extractor = PreMatchFeatureExtractor(strict_mode=True)
    pre_match = extractor.extract_from_technical_features(
        sample_tech, match_id="test_001", verbose=True
    )

    print("\n" + "=" * 70)
    print("V41.450 Pre-Match Feature Extraction Demo")
    print("=" * 70)
    print(f"Original features: {extractor.extracted_count}")
    print(f"Rejected features: {extractor.rejected_count}")
    print(f"Extraction rate: {extractor.get_extraction_rate():.1%}")
    print(f"\nPre-match features ({len(pre_match)}):")
    for key, value in sorted(pre_match.items()):
        print(f"  {key}: {value}")
    print("=" * 70)
