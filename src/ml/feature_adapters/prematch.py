"""V26.6 pre-match compatibility adapter implementation.

The public compatibility facade remains src.ml.feature_adapter.

lifecycle: permanent
"""

# These diagnostics predate this mechanical extraction; preserving the
# adapter's import, exception, logging, and class-name behavior is intentional.
# ruff: noqa: C901, ERA001, G004, N801, PERF401, PLC0415, PLR0912, PLR0915, RUF012, TRY401
# mypy: disable_error_code="call-arg,no-untyped-def,type-arg"

from datetime import datetime
import logging
from typing import Any, NoReturn

import numpy as np
import pandas as pd

from src.core.exceptions import InvalidPredictionInputError, RequiredFeatureDataUnavailableError
from src.ml.feature_adapters.base import AdaptationResult, BaseFeatureAdapter

logger = logging.getLogger("src.ml.feature_adapter")


def _raise_feature_data_unavailable(message: str) -> NoReturn:
    """在 strict canonical 适配路径上抛出特征不可用异常。"""
    raise RequiredFeatureDataUnavailableError(message)


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

    # V26.6 真赛前特征集 (20个) - 无泄露
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
        # 高级特征 (5个) - 赛前可计算，安全
        "raw_elo_gap",
        "adjusted_elo_gap",
        "home_fatigue_index",
        "away_fatigue_index",
        "fatigue_diff",
        # ⚠️ 移除：home_relegation_incentive (数据不完整)
    ]

    REQUIRED_ROLLING_HISTORY_COUNT = 5

    def adapt(self, raw_features: dict[str, Any], *, strict: bool = False) -> AdaptationResult:
        """
        将原始特征适配为 V26.6 真赛前特征集

        严格只使用赛前已知信息，拒绝任何赛中数据。``strict=True`` 是
        canonical ``v26_7_aligned`` 路径的显式可用性门禁；默认值保留
        V26.6/V26.8 兼容调用的历史 fallback 行为。
        """
        errors: list[str] = []
        missing_features: list[str] = []
        adapted = {}

        try:
            # 提取球队名称
            home_team = self._safe_get(raw_features, "header", "teams", "home", "name", default="")
            away_team = self._safe_get(raw_features, "header", "teams", "away", "name", default="")

            if strict:
                home_team = self._required_team_name(home_team, "home")
                away_team = self._required_team_name(away_team, "away")

            # 提取比赛时间（用于历史数据过滤）
            match_time = None
            match_time_str = self._safe_get(
                raw_features, "header", "status", "startTimeStr", default=None
            )
            if strict:
                match_time = self._required_match_time(match_time_str)
            else:
                try:
                    if match_time_str:
                        match_time = datetime.fromisoformat(
                            match_time_str.replace("Z", "+00:00")
                        ).isoformat()
                except (AttributeError, TypeError, ValueError):
                    pass

            # 动态获取滚动特征（历史平均值）
            from src.database.schema_manager import SchemaManager

            home_stats = self._invoke_provider(
                SchemaManager.get_team_rolling_stats,
                strict_mode=strict,
                team_name=home_team,
                n_matches=self.REQUIRED_ROLLING_HISTORY_COUNT,
                before_match_date=match_time,
                strict=strict,
            )
            away_stats = self._invoke_provider(
                SchemaManager.get_team_rolling_stats,
                strict_mode=strict,
                team_name=away_team,
                n_matches=self.REQUIRED_ROLLING_HISTORY_COUNT,
                before_match_date=match_time,
                strict=strict,
            )

            if strict:
                home_stats = self._validate_rolling_stats(
                    home_stats, home_team, self.REQUIRED_ROLLING_HISTORY_COUNT
                )
                away_stats = self._validate_rolling_stats(
                    away_stats, away_team, self.REQUIRED_ROLLING_HISTORY_COUNT
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
            home_standings = self._invoke_provider(
                SchemaManager.get_team_standings,
                strict_mode=strict,
                team_name=home_team,
                before_match_date=match_time,
                strict=strict,
            )
            away_standings = self._invoke_provider(
                SchemaManager.get_team_standings,
                strict_mode=strict,
                team_name=away_team,
                before_match_date=match_time,
                strict=strict,
            )

            if strict:
                home_standings = self._validate_standings(home_standings, home_team)
                away_standings = self._validate_standings(away_standings, away_team)

            # 动态计算 ELO 评分
            elo_ratings = self._invoke_provider(
                SchemaManager.get_elo_ratings,
                strict_mode=strict,
                team_names=[home_team, away_team],
                before_match_date=match_time,
                strict=strict,
            )
            if strict:
                home_elo = self._required_number(elo_ratings, home_team, "ELO")
                away_elo = self._required_number(elo_ratings, away_team, "ELO")
            else:
                home_elo = elo_ratings.get(home_team, 1500.0)
                away_elo = elo_ratings.get(away_team, 1500.0)

            # 动态计算疲劳度指数
            if match_time:
                home_fatigue = self._invoke_provider(
                    SchemaManager.get_team_fatigue_index,
                    strict_mode=strict,
                    team_name=home_team,
                    match_date=match_time,
                    lookback_days=7,
                    strict=strict,
                )
                away_fatigue = self._invoke_provider(
                    SchemaManager.get_team_fatigue_index,
                    strict_mode=strict,
                    team_name=away_team,
                    match_date=match_time,
                    lookback_days=7,
                    strict=strict,
                )
            else:
                home_fatigue = 0.5
                away_fatigue = 0.5

            if strict:
                home_fatigue = self._required_scalar(home_fatigue, "fatigue")
                away_fatigue = self._required_scalar(away_fatigue, "fatigue")

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

            # 构建 20 维真赛前特征向量（全动态）
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
                if strict:
                    _raise_feature_data_unavailable("required prediction feature data unavailable")
                errors.append(f"Missing {len(missing_features)} features")
                return AdaptationResult(
                    success=False,
                    features=None,
                    feature_names=self.V26_6_FEATURES.copy(),
                    missing_features=missing_features,
                    errors=errors,
                )

            # canonical strict 路径不允许用 0 填充缺失特征槽位。
            feature_values = [
                adapted[feat] if strict else adapted.get(feat, 0) for feat in self.V26_6_FEATURES
            ]
            if strict:
                try:
                    numeric_values = np.asarray(feature_values, dtype=float)
                except (TypeError, ValueError) as exc:
                    raise RequiredFeatureDataUnavailableError(
                        "required prediction feature data unavailable"
                    ) from exc
                if not np.isfinite(numeric_values).all():
                    _raise_feature_data_unavailable("required prediction feature data unavailable")
            feature_matrix = pd.DataFrame([feature_values], columns=self.V26_6_FEATURES)

            return AdaptationResult(
                success=success,
                features=feature_matrix,
                feature_names=self.V26_6_FEATURES.copy(),
                missing_features=missing_features,
                errors=errors,
            )

        except (InvalidPredictionInputError, RequiredFeatureDataUnavailableError):
            raise
        except Exception as e:
            logger.exception(f"V26.6 特征适配失败: {e}")
            return AdaptationResult(
                success=False,
                features=None,
                feature_names=self.V26_6_FEATURES.copy(),
                missing_features=self.V26_6_FEATURES.copy(),
                errors=[str(e)],
            )

    @staticmethod
    def _invoke_provider(provider: Any, *, strict_mode: bool, **kwargs: Any) -> Any:
        """调用特征 provider，并在 strict 模式下分类 provider 失败。"""
        if not strict_mode:
            kwargs.pop("strict", None)
            return provider(**kwargs)
        try:
            return provider(**kwargs)
        except (InvalidPredictionInputError, RequiredFeatureDataUnavailableError):
            raise
        except Exception as exc:
            raise RequiredFeatureDataUnavailableError(
                "required prediction feature data unavailable"
            ) from exc

    @staticmethod
    def _required_team_name(value: Any, label: str) -> str:
        """校验并规范 canonical 预测所需的球队身份。"""
        if not isinstance(value, str) or not value.strip():
            raise InvalidPredictionInputError(f"{label} team is required")
        return value.strip()

    @staticmethod
    def _required_match_time(value: Any) -> str:
        """校验 canonical 预测时间，并返回统一 ISO cutoff 字符串。"""
        if not isinstance(value, str) or not value.strip():
            raise InvalidPredictionInputError("match timestamp is required")
        try:
            return datetime.fromisoformat(value.strip().replace("Z", "+00:00")).isoformat()
        except (TypeError, ValueError) as exc:
            raise InvalidPredictionInputError("match timestamp is invalid") from exc

    @staticmethod
    def _required_number(values: Any, key: str, source: str) -> float:
        """读取 strict 特征值，不把缺失值转换为默认数字。"""
        try:
            value = float(values[key])
        except (KeyError, TypeError, ValueError) as exc:
            raise RequiredFeatureDataUnavailableError(f"{source} unavailable") from exc
        if not np.isfinite(value):
            raise RequiredFeatureDataUnavailableError(f"{source} unavailable")
        return value

    @staticmethod
    def _required_scalar(value: Any, source: str) -> float:
        """读取 strict 标量，不把解析或 provider 失败当成有效数值。"""
        try:
            numeric_value = float(value)
        except (TypeError, ValueError) as exc:
            raise RequiredFeatureDataUnavailableError(f"{source} unavailable") from exc
        if not np.isfinite(numeric_value):
            raise RequiredFeatureDataUnavailableError(f"{source} unavailable")
        return numeric_value

    @classmethod
    def _validate_rolling_stats(
        cls, values: Any, team_name: str, requested_matches: int
    ) -> dict[str, Any]:
        """验证 strict 滚动统计满足请求的五场历史窗口。"""
        if not isinstance(values, dict):
            raise RequiredFeatureDataUnavailableError("rolling history unavailable")
        try:
            matches_count = float(values["matches_count"])
        except (KeyError, TypeError, ValueError) as exc:
            raise RequiredFeatureDataUnavailableError("rolling history unavailable") from exc
        if (
            not np.isfinite(matches_count)
            or not matches_count.is_integer()
            or matches_count < requested_matches
        ):
            raise RequiredFeatureDataUnavailableError(
                f"rolling history unavailable for {team_name}"
            )

        validated = dict(values)
        validated["matches_count"] = int(matches_count)
        for key in ("rolling_xg", "rolling_shots_on_target", "rolling_possession"):
            validated[key] = cls._required_number(values, key, "rolling history")
        return validated

    @classmethod
    def _validate_standings(cls, values: Any, team_name: str) -> dict[str, Any]:
        """拒绝 strict 积分榜冷启动/default 对象。"""
        if not isinstance(values, dict):
            raise RequiredFeatureDataUnavailableError("standings unavailable")
        played = cls._required_number(values, "played", "standings")
        if played <= 0:
            raise RequiredFeatureDataUnavailableError(f"standings unavailable for {team_name}")

        validated = dict(values)
        for key in ("position", "points", "recent_form_points"):
            validated[key] = cls._required_number(values, key, "standings")
        validated["played"] = played
        return validated

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
