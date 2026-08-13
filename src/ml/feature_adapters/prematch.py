"""V26.6 pre-match compatibility adapter implementation.

The public compatibility facade remains src.ml.feature_adapter.

lifecycle: permanent
"""

# These diagnostics predate this mechanical extraction; preserving the
# adapter's import, exception, logging, and class-name behavior is intentional.
# ruff: noqa: ERA001, E722, G004, N801, PERF401, PLC0415, RUF012, TRY401
# mypy: disable_error_code="call-arg,no-untyped-def,type-arg"

import logging
from typing import Any

import pandas as pd

from src.ml.feature_adapters.base import AdaptationResult, BaseFeatureAdapter

logger = logging.getLogger("src.ml.feature_adapter")


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
                match_time_str = self._safe_get(
                    raw_features, "header", "status", "startTimeStr", default=None
                )
                if match_time_str:
                    from datetime import datetime

                    match_time = datetime.fromisoformat(
                        match_time_str.replace("Z", "+00:00")
                    ).isoformat()
            except:
                pass

            # 动态获取滚动特征（历史平均值）
            from src.database.schema_manager import SchemaManager

            home_stats = SchemaManager.get_team_rolling_stats(
                team_name=home_team, n_matches=5, before_match_date=match_time
            )
            away_stats = SchemaManager.get_team_rolling_stats(
                team_name=away_team, n_matches=5, before_match_date=match_time
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
            home_standings = SchemaManager.get_team_standings(
                team_name=home_team, before_match_date=match_time
            )
            away_standings = SchemaManager.get_team_standings(
                team_name=away_team, before_match_date=match_time
            )

            # 动态计算 ELO 评分
            elo_ratings = SchemaManager.get_elo_ratings(
                team_names=[home_team, away_team], before_match_date=match_time
            )
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
            logger.exception(f"V26.6 特征适配失败: {e}")
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


V26_6_PreMatchAdapter.__module__ = "src.ml.feature_adapter"
