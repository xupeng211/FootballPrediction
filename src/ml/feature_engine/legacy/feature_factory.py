"""
V41.500 Feature Factory - 自动化特征加工厂
=========================================

核心功能：
1. 整合 V41.380-V41.480 的所有特征提取逻辑
2. 自动计算：疲劳度、赔率动向、首发战力、伤病损失
3. 提供统一的特征生成接口

集成模块：
- PathResolver: Schema-Agnostic 路径访问
- UltimateExtractor: 疲劳度、缺阵特征
- Starting11DeltaCalculator: 首发战力差
- OddsMovementCalculator: 赔率动向

Author: V41.500 Pipeline Team
Version: V41.500 "The Automated Pipeline"
Date: 2026-01-21
"""

from __future__ import annotations

from dataclasses import dataclass
import logging
from typing import TYPE_CHECKING, Any

import numpy as np
import psycopg2
from psycopg2.extras import RealDictCursor

from src.config_unified import get_settings
from src.ml.feature_engine.legacy.path_resolver import PathResolver, get_path_resolver

if TYPE_CHECKING:
    from datetime import datetime

logger = logging.getLogger(__name__)


# =============================================================================
# Feature Factory Configuration
# =============================================================================


@dataclass
class FeatureFactoryConfig:
    """特征工厂配置"""

    # 五大联赛
    TOP_5_LEAGUES = {
        "Premier League",
        "La Liga",
        "Bundesliga",
        "Serie A",
        "Ligue 1",
    }


DEFAULT_CONFIG = FeatureFactoryConfig()


# =============================================================================
# Feature Factory - 主工厂类
# =============================================================================


class FeatureFactory:
    """
    V41.500 特征工厂

    核心方法：
    - process_match(): 处理单场比赛，生成所有特征
    - process_batch(): 批量处理比赛

    生成的特征类别：
    1. 疲劳度特征 (Fatigue Index)
    2. 缺阵特征 (Unavailability Power Loss)
    3. 首发战力特征 (Starting-11 Delta)
    4. 赔率特征 (Odds Movement)
    5. 联赛等级特征 (League Tier)
    """

    def __init__(
        self, config: FeatureFactoryConfig | None = None, path_resolver: PathResolver | None = None
    ):
        """
        初始化特征工厂

        Args:
            config: 配置对象
            path_resolver: 路径解析器
        """
        self.config = config or DEFAULT_CONFIG
        self.path_resolver = path_resolver or get_path_resolver()
        self.settings = get_settings()
        self._conn = None

        # 从 schema_map 读取参数
        self.busy_week_threshold = self.path_resolver.schema.get_param(
            "fatigue", "busy_week_threshold", 4
        )
        self.default_rest_days = self.path_resolver.schema.get_param(
            "fatigue", "default_rest_days", 14
        )
        self.star_market_value = self.path_resolver.schema.get_param(
            "unavailability", "star_market_value", 30_000_000
        )

    def _get_connection(self):
        if self._conn is None or self._conn.closed:
            self._conn = psycopg2.connect(
                host=self.settings.database.host,
                database=self.settings.database.name,
                user=self.settings.database.user,
                password=self.settings.database.password.get_secret_value(),
                cursor_factory=RealDictCursor,
            )
        return self._conn

    # ========================================================================
    # 1. 疲劳度特征 (Fatigue Index)
    # ========================================================================

    def _get_previous_match_date(
        self, team_name: str, current_match_date: datetime, league_name: str | None = None
    ) -> datetime | None:
        """获取上一场比赛日期"""
        conn = self._get_connection()
        cursor = conn.cursor()

        query = """
            SELECT match_date
            FROM matches
            WHERE match_date < %s
              AND (home_team = %s OR away_team = %s)
        """
        params = [current_match_date, team_name, team_name]

        if league_name:
            query += " AND league_name = %s"
            params.append(league_name)

        query += " ORDER BY match_date DESC LIMIT 1"

        cursor.execute(query, params)
        result = cursor.fetchone()
        cursor.close()

        return result["match_date"] if result else None

    def _calculate_rest_days(self, current_date: datetime, prev_date: datetime | None) -> int:
        """计算休息天数"""
        if prev_date is None:
            return self.default_rest_days

        # 处理时区问题：统一转换为 naive datetime
        if hasattr(current_date, "tzinfo") and current_date.tzinfo is not None:
            current_date = current_date.replace(tzinfo=None)
        if hasattr(prev_date, "tzinfo") and prev_date.tzinfo is not None:
            prev_date = prev_date.replace(tzinfo=None)

        if prev_date > current_date:
            logger.warning("prev_date > current_date, using default")
            return self.default_rest_days

        delta = current_date - prev_date
        return max(0, delta.days)

    def _extract_fatigue_features(self, match_data: dict[str, Any]) -> dict[str, float]:
        """提取疲劳度特征"""
        features = {}
        match_date = match_data.get("match_date")
        home_team = match_data.get("home_team")
        away_team = match_data.get("away_team")
        league_name = match_data.get("league_name")

        if not all([match_date, home_team, away_team]):
            return {}

        # 主队疲劳度
        home_prev = self._get_previous_match_date(home_team, match_date, league_name)
        home_rest = self._calculate_rest_days(match_date, home_prev)
        features.update(
            {
                "home_rest_days": float(home_rest),
                "home_is_busy_week": 1.0 if home_rest < self.busy_week_threshold else 0.0,
            }
        )

        # 客队疲劳度
        away_prev = self._get_previous_match_date(away_team, match_date, league_name)
        away_rest = self._calculate_rest_days(match_date, away_prev)
        features.update(
            {
                "away_rest_days": float(away_rest),
                "away_is_busy_week": 1.0 if away_rest < self.busy_week_threshold else 0.0,
            }
        )

        # 差值特征
        features.update(
            {
                "diff_rest_days": float(home_rest - away_rest),
                "home_less_rest": 1.0 if home_rest < away_rest else 0.0,
            }
        )

        return features

    # ========================================================================
    # 2. 缺阵特征 (Unavailability Power Loss)
    # ========================================================================

    def _calculate_unavailable_power_loss(
        self, unavailable_players: list[dict[str, Any]]
    ) -> dict[str, Any]:
        """计算缺阵战力损失"""
        if not unavailable_players:
            return {
                "total_count": 0,
                "injury_count": 0,
                "suspension_count": 0,
                "other_count": 0,
                "total_market_value": 0.0,
                "avg_market_value": 0.0,
                "star_count": 0,
            }

        injury_count = 0
        suspension_count = 0
        other_count = 0
        total_mv = 0.0
        star_count = 0
        players_with_mv = 0

        for player in unavailable_players:
            unavail_type = self.path_resolver.get_unavailability_type(player)

            if unavail_type == "injury":
                injury_count += 1
            elif unavail_type == "suspension":
                suspension_count += 1
            else:
                other_count += 1

            mv = self.path_resolver.get_player_market_value(player)
            if mv > 0:
                total_mv += mv
                players_with_mv += 1
                if mv >= self.star_market_value:
                    star_count += 1

        avg_mv = total_mv / players_with_mv if players_with_mv > 0 else 0.0

        return {
            "total_count": len(unavailable_players),
            "injury_count": injury_count,
            "suspension_count": suspension_count,
            "other_count": other_count,
            "total_market_value": total_mv,
            "avg_market_value": avg_mv,
            "star_count": star_count,
        }

    def _extract_unavailability_features(
        self, l2_raw_json: dict[str, Any] | str | None
    ) -> dict[str, float]:
        """提取缺阵特征"""
        features = {}

        home_unavailable = self.path_resolver.get_unavailable_players(l2_raw_json, "home")
        away_unavailable = self.path_resolver.get_unavailable_players(l2_raw_json, "away")

        home_loss = self._calculate_unavailable_power_loss(home_unavailable)
        away_loss = self._calculate_unavailable_power_loss(away_unavailable)

        features.update({f"home_unavailable_{k}": float(v) for k, v in home_loss.items()})
        features.update({f"away_unavailable_{k}": float(v) for k, v in away_loss.items()})

        features.update(
            {
                "diff_unavailable_count": float(
                    home_loss["total_count"] - away_loss["total_count"]
                ),
                "diff_unavailable_mv": float(
                    home_loss["total_market_value"] - away_loss["total_market_value"]
                ),
                "diff_unavailable_stars": float(home_loss["star_count"] - away_loss["star_count"]),
                "home_more_unavailable": 1.0
                if home_loss["total_count"] > away_loss["total_count"]
                else 0.0,
            }
        )

        return features

    # ========================================================================
    # 3. 首发战力特征 (Starting-11 Delta)
    # ========================================================================

    def _extract_starting_11_features(
        self, l2_raw_json: dict[str, Any] | str | None
    ) -> dict[str, float]:
        """提取首发战力特征"""
        features = {}

        home_starters = self.path_resolver.get_starters(l2_raw_json, "home")
        away_starters = self.path_resolver.get_starters(l2_raw_json, "away")

        # 计算首发平均评分
        home_ratings = [self.path_resolver.get_player_rating(p) for p in home_starters]
        away_ratings = [self.path_resolver.get_player_rating(p) for p in away_starters]

        home_avg = np.mean(home_ratings) if home_ratings else 6.0
        away_avg = np.mean(away_ratings) if away_ratings else 6.0

        features.update(
            {
                "home_starter_avg_rating": float(home_avg),
                "away_starter_avg_rating": float(away_avg),
                "diff_starter_avg_rating": float(home_avg - away_avg),
            }
        )

        # 计算缺阵大腿数（评分 >= 7.5）
        home_unavailable = self.path_resolver.get_unavailable_players(l2_raw_json, "home")
        away_unavailable = self.path_resolver.get_unavailable_players(l2_raw_json, "away")

        home_missing_stars = sum(
            1 for p in home_unavailable if self.path_resolver.get_player_rating(p, 0) >= 7.5
        )
        away_missing_stars = sum(
            1 for p in away_unavailable if self.path_resolver.get_player_rating(p, 0) >= 7.5
        )

        features.update(
            {
                "home_missing_stars_count": float(home_missing_stars),
                "away_missing_stars_count": float(away_missing_stars),
                "diff_missing_stars_count": float(home_missing_stars - away_missing_stars),
            }
        )

        return features

    # ========================================================================
    # 4. 赔率特征 (Odds Movement)
    # ========================================================================

    def _extract_odds_features(self, match_id: str) -> dict[str, float]:
        """提取赔率动向特征"""
        conn = self._get_connection()
        cursor = conn.cursor()

        query = """
            SELECT initial_price, closing_price
            FROM match_odds_intelligence
            WHERE match_id = %s
            LIMIT 1
        """

        cursor.execute(query, (match_id,))
        result = cursor.fetchone()
        cursor.close()

        if not result:
            return {
                "home_drop_ratio": 0.0,
                "draw_change_ratio": 0.0,
                "away_change_ratio": 0.0,
                "total_movement": 0.0,
            }

        initial = result.get("initial_price")
        closing = result.get("closing_price")

        if not initial or not closing or len(initial) < 3 or len(closing) < 3:
            return {
                "home_drop_ratio": 0.0,
                "draw_change_ratio": 0.0,
                "away_change_ratio": 0.0,
                "total_movement": 0.0,
            }

        features = {
            "home_drop_ratio": (initial[0] - closing[0]) / max(initial[0], 0.01),
            "draw_change_ratio": (initial[1] - closing[1]) / max(initial[1], 0.01),
            "away_change_ratio": (initial[2] - closing[2]) / max(initial[2], 0.01),
        }
        features["total_movement"] = (
            abs(features["home_drop_ratio"])
            + abs(features["draw_change_ratio"])
            + abs(features["away_change_ratio"])
        )

        return features

    # ========================================================================
    # 5. 联赛等级特征 (League Tier)
    # ========================================================================

    def _extract_league_features(self, match_data: dict[str, Any]) -> dict[str, float]:
        """提取联赛等级特征"""
        league_name = match_data.get("league_name")

        return {
            "is_top_5_league": 1.0 if league_name in self.config.TOP_5_LEAGUES else 0.0,
        }

    # ========================================================================
    # V41.560: 数据完整性门禁 (Factory Gatekeeper)
    # ========================================================================

    def validate_data_integrity(self, match_id: str) -> tuple[bool, str | None]:
        """V41.560: 验证数据完整性，确保只有全维度数据才能生成特征。

        门禁规则：
        1. 必须有 metrics_multi_source_data 记录
        2. 必须有完整的变盘轨迹 (initial + final)
        3. 必须有时间戳锚定
        4. 拒绝 `initial_price: []` 这种残疾数据

        Args:
            match_id: 比赛 ID

        Returns:
            (is_valid, error_message): 验证结果和错误信息
        """
        conn = self._get_connection()
        cursor = conn.cursor()

        # 检查多源数据是否存在且完整
        cursor.execute(
            """
            SELECT
                COUNT(*) as total_records,
                COUNT(CASE WHEN init_h IS NOT NULL THEN 1 END) as has_initial,
                COUNT(CASE WHEN final_h IS NOT NULL THEN 1 END) as has_final,
                COUNT(CASE WHEN opening_time_h IS NOT NULL OR opening_time_d IS NOT NULL OR opening_time_a IS NOT NULL THEN 1 END) as has_timestamp,
                COUNT(CASE WHEN is_valid = TRUE THEN 1 END) as valid_records
            FROM metrics_multi_source_data
            WHERE match_id = %s
        """,
            (match_id,),
        )

        result = cursor.fetchone()
        cursor.close()

        if not result or result["total_records"] == 0:
            return False, "No multi-source data found"

        # 门禁规则：必须有终盘数据
        if result["has_final"] == 0:
            return False, "Missing final odds (closing)"

        # 门禁规则：必须有初盘数据（至少一个方向）
        if result["has_initial"] == 0:
            return False, "Missing initial odds (no opening data)"

        # 门禁规则：必须有时间戳锚定
        if result["has_timestamp"] == 0:
            return False, "Missing timestamp anchoring (no time data)"

        # 门禁规则：必须有有效数据
        if result["valid_records"] == 0:
            return False, "No valid multi-source data (all failed integrity check)"

        # 检查数据源数量 - 多源数据更可靠
        source_count = result["total_records"]
        if source_count < 1:
            return False, f"Insufficient data sources: {source_count}"

        logger.info(
            f"[V41.560 Gatekeeper] match_id={match_id} PASSED: "
            f"{result['total_records']} records, "
            f"{result['has_initial']} with initial, "
            f"{result['has_final']} with final, "
            f"{result['has_timestamp']} with timestamp, "
            f"{result['valid_records']} valid"
        )

        return True, None

    # ========================================================================
    # 主处理方法
    # ========================================================================

    def process_match(self, match_data: dict[str, Any], verbose: bool = False) -> dict[str, float]:
        """
        处理单场比赛，生成所有 V41.500 特征

        Args:
            match_data: 比赛数据字典
            verbose: 是否打印日志

        Returns:
            特征字典
        """
        all_features = {}

        # 1. 疲劳度特征
        fatigue_features = self._extract_fatigue_features(match_data)
        all_features.update(fatigue_features)

        # 2. 缺阵特征
        l2_raw_json = match_data.get("l2_raw_json")
        unavailability_features = self._extract_unavailability_features(l2_raw_json)
        all_features.update(unavailability_features)

        # 3. 首发战力特征
        starting_features = self._extract_starting_11_features(l2_raw_json)
        all_features.update(starting_features)

        # 4. 赔率特征
        match_id = match_data.get("match_id")
        if match_id:
            odds_features = self._extract_odds_features(match_id)
            all_features.update(odds_features)

        # 5. 联赛等级特征
        league_features = self._extract_league_features(match_data)
        all_features.update(league_features)

        if verbose:
            logger.info(f"Generated {len(all_features)} features for match {match_id}")

        return all_features

    def process_batch(
        self, matches: list[dict[str, Any]], verbose: bool = False
    ) -> list[dict[str, float]]:
        """
        批量处理比赛

        Args:
            matches: 比赛数据列表
            verbose: 是否打印日志

        Returns:
            特征字典列表
        """
        results = []

        for i, match in enumerate(matches):
            features = self.process_match(match, verbose=False)
            results.append(features)

            if verbose and (i + 1) % 100 == 0:
                logger.info(f"Processed {i + 1}/{len(matches)} matches")

        return results

    def cleanup(self):
        """清理数据库连接"""
        if self._conn and not self._conn.closed:
            self._conn.close()


# =============================================================================
# Singleton Instance
# =============================================================================

_feature_factory_instance = None


def get_feature_factory() -> FeatureFactory:
    """获取特征工厂单例"""
    global _feature_factory_instance
    if _feature_factory_instance is None:
        _feature_factory_instance = FeatureFactory()
    return _feature_factory_instance
