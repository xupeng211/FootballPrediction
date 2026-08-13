"""V26.5 production compatibility adapter implementation.

The public compatibility facade remains src.ml.feature_adapter.

lifecycle: permanent
"""

# These diagnostics predate this mechanical extraction; preserving the
# adapter's import, exception, logging, and class-name behavior is intentional.
# ruff: noqa: C901, E722, G004, N801, PERF401, PLC0415, PLR2004, RUF012, TRY300, TRY401
# mypy: disable_error_code="no-untyped-def,type-arg"

import logging
from typing import Any

import pandas as pd

from src.ml.feature_adapters.base import AdaptationResult, BaseFeatureAdapter

logger = logging.getLogger("src.ml.feature_adapter")


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

            # 动态获取滚动特征
            from src.database.schema_manager import SchemaManager

            home_stats = SchemaManager.get_team_rolling_stats(
                team_name=home_team, n_matches=5, before_match_date=match_time
            )
            away_stats = SchemaManager.get_team_rolling_stats(
                team_name=away_team, n_matches=5, before_match_date=match_time
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

                home_shots = self._safe_get(
                    raw_features, "content", "stats", "home", "shotsTotal", "total", default=10
                )
                away_shots = self._safe_get(
                    raw_features, "content", "stats", "away", "shotsTotal", "total", default=10
                )

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
            logger.exception(f"V26.5 特征适配失败: {e}")
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
            stats_container = self._safe_get(
                raw_data, "content", "stats", "Periods", "All", "stats", default=[]
            )
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


V26_5_ProductionAdapter.__module__ = "src.ml.feature_adapter"
