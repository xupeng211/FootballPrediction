"""
V41.480 Ultimate Feature Extractor - 五大联赛深度特征挖掘器
============================================================

V41.480 核心功能：
1. 伤病/禁赛战力损失计算 - 从 unavailable 提取 marketValue
2. 赛程疲劳度 (Fatigue Index) - 计算 rest_days 和 is_busy_week
3. 赔率动向捕捉 - odds_drop_ratio
4. 联赛等级特征 - is_top_5_league

目标：将特征维度从 110 维扩展到 300+ 维

Author: V41.480 Data Mining Team
Version: V41.480 "Ultimate Pre-Match Mine"
Date: 2026-01-21
"""

from __future__ import annotations

import json
import logging
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Any, Optional

import numpy as np
import psycopg2
from psycopg2.extras import RealDictCursor

from src.config_unified import get_settings
from src.processors.pure_feature_filter import PureFeatureFilter

logger = logging.getLogger(__name__)


# =============================================================================
# Configuration
# =============================================================================

@dataclass
class UltimateExtractorConfig:
    """V41.480 终极特征提取器配置"""

    # 疲劳度阈值
    busy_week_threshold: int = 4  # 休息天数 < 4 视为忙碌周
    default_rest_days: int = 14   # 无历史比赛时的默认值

    # 伤病/禁赛评分阈值
    star_market_value: float = 30_000_000  # 3000万欧元以上视为球星

    # 五大联赛
    TOP_5_LEAGUES = {
        "Premier League",
        "La Liga",
        "Bundesliga",
        "Serie A",
        "Ligue 1",
    }


DEFAULT_CONFIG = UltimateExtractorConfig()


# =============================================================================
# Ultimate Feature Extractor
# =============================================================================

class UltimateFeatureExtractor:
    """
    V41.480 终极特征提取器

    核心功能：
    1. 从 l2_raw_json 提取 unavailable 数据（伤病/禁赛）
    2. 从 match_odds_intelligence 提取赔率动向
    3. 从 matches 表计算赛程疲劳度
    4. 结合 PureFeatureFilter 的纯赛前特征
    """

    def __init__(self, config: Optional[UltimateExtractorConfig] = None):
        self.config = config or DEFAULT_CONFIG
        self.settings = get_settings()
        self.pure_filter = PureFeatureFilter(strict_mode=True)
        self._conn = None
        self._match_cache: dict[str, dict[str, Any]] = {}

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
    # Fatigue Index: 赛程疲劳度计算
    # ========================================================================

    def _calculate_rest_days(
        self,
        current_date: datetime,
        prev_date: Optional[datetime]
    ) -> int:
        """
        计算休息天数

        Args:
            current_date: 当前比赛日期
            prev_date: 上一场比赛日期

        Returns:
            休息天数（如果 prev_date 为 None 或异常，返回默认值）
        """
        if prev_date is None:
            return self.config.default_rest_days

        # 防护：确保 prev_date 不在 current_date 之后
        if prev_date > current_date:
            logger.warning(f"prev_date ({prev_date}) > current_date ({current_date}), using default")
            return self.config.default_rest_days

        delta = current_date - prev_date
        return max(0, delta.days)

    def _is_busy_week(self, rest_days: int) -> int:
        """判断是否为忙碌周（休息天数 < 阈值）"""
        return 1 if rest_days < self.config.busy_week_threshold else 0

    def _get_previous_match_date(
        self,
        team_name: str,
        current_match_date: datetime,
        league_name: Optional[str] = None
    ) -> Optional[datetime]:
        """
        获取指定球队上一场比赛的日期

        Args:
            team_name: 球队名称
            current_match_date: 当前比赛日期
            league_name: 联赛名称（可选，限制搜索范围）

        Returns:
            上一场比赛日期，如果没有则返回 None
        """
        conn = self._get_connection()
        cursor = conn.cursor()

        # 构建查询
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

    def _calculate_fatigue_features(
        self,
        match_data: dict[str, Any]
    ) -> dict[str, float]:
        """
        计算疲劳度特征

        Args:
            match_data: 比赛数据字典，包含 home_team, away_team, match_date

        Returns:
            疲劳度特征字典
        """
        features = {}
        match_date = match_data.get("match_date")
        home_team = match_data.get("home_team")
        away_team = match_data.get("away_team")
        league_name = match_data.get("league_name")

        if not all([match_date, home_team, away_team]):
            return {}

        # 主队疲劳度
        home_prev_date = self._get_previous_match_date(home_team, match_date, league_name)
        home_rest_days = self._calculate_rest_days(match_date, home_prev_date)
        home_is_busy = self._is_busy_week(home_rest_days)

        features.update({
            "home_rest_days": float(home_rest_days),
            "home_is_busy_week": float(home_is_busy),
        })

        # 客队疲劳度
        away_prev_date = self._get_previous_match_date(away_team, match_date, league_name)
        away_rest_days = self._calculate_rest_days(match_date, away_prev_date)
        away_is_busy = self._is_busy_week(away_rest_days)

        features.update({
            "away_rest_days": float(away_rest_days),
            "away_is_busy_week": float(away_is_busy),
        })

        # 差值特征
        features.update({
            "diff_rest_days": float(home_rest_days - away_rest_days),
            "home_less_rest": 1.0 if home_rest_days < away_rest_days else 0.0,
        })

        return features

    # ========================================================================
    # Injury/Suspension Power Loss
    # ========================================================================

    def _calculate_unavailable_power_loss(
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

    def _extract_unavailable_features(
        self,
        l2_raw_json: dict[str, Any] | str | None
    ) -> dict[str, float]:
        """
        从 l2_raw_json 提取缺阵特征

        Args:
            l2_raw_json: 原始 JSON 数据

        Returns:
            缺阵特征字典
        """
        features = {}

        # 解析 JSON
        if isinstance(l2_raw_json, str):
            try:
                l2_raw_json = json.loads(l2_raw_json)
            except json.JSONDecodeError:
                return {}

        if not isinstance(l2_raw_json, dict):
            return {}

        # 提取主客队 unavailable 数据
        lineup = l2_raw_json.get("content", {}).get("lineup", {})
        home_unavailable = lineup.get("homeTeam", {}).get("unavailable", [])
        away_unavailable = lineup.get("awayTeam", {}).get("unavailable", [])

        # 计算主队缺阵损失
        home_loss = self._calculate_unavailable_power_loss(home_unavailable)
        features.update({
            f"home_unavailable_{k}": float(v)
            for k, v in home_loss.items()
        })

        # 计算客队缺阵损失
        away_loss = self._calculate_unavailable_power_loss(away_unavailable)
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

    # ========================================================================
    # Odds Movement Features
    # ========================================================================

    def _calculate_odds_movement(
        self,
        initial_price: list[float] | None,
        closing_price: list[float] | None
    ) -> dict[str, float]:
        """
        计算赔率动向特征

        Args:
            initial_price: 初盘赔率 [home, draw, away]
            closing_price: 终盘赔率 [home, draw, away]

        Returns:
            赔率动向特征字典
        """
        if not initial_price or not closing_price:
            return {
                "home_drop_ratio": 0.0,
                "draw_change_ratio": 0.0,
                "away_change_ratio": 0.0,
                "total_movement": 0.0,
            }

        if len(initial_price) < 3 or len(closing_price) < 3:
            return {
                "home_drop_ratio": 0.0,
                "draw_change_ratio": 0.0,
                "away_change_ratio": 0.0,
                "total_movement": 0.0,
            }

        # 计算变化比率
        features = {}

        # 主胜赔率下降比率（正值表示下降）
        features["home_drop_ratio"] = (initial_price[0] - closing_price[0]) / max(initial_price[0], 0.01)

        # 平局赔率变化比率
        features["draw_change_ratio"] = (initial_price[1] - closing_price[1]) / max(initial_price[1], 0.01)

        # 客胜赔率变化比率
        features["away_change_ratio"] = (initial_price[2] - closing_price[2]) / max(initial_price[2], 0.01)

        # 总变化幅度
        features["total_movement"] = abs(features["home_drop_ratio"]) + \
                                    abs(features["draw_change_ratio"]) + \
                                    abs(features["away_change_ratio"])

        return features

    def _get_odds_features(self, match_id: str) -> dict[str, float]:
        """
        从 match_odds_intelligence 表获取赔率特征

        Args:
            match_id: 比赛 ID

        Returns:
            赔率特征字典
        """
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
            return {}

        initial = result.get("initial_price")
        closing = result.get("closing_price")

        return self._calculate_odds_movement(initial, closing)

    # ========================================================================
    # League Tier Features
    # ========================================================================

    def _is_top_5_league(self, league_name: str | None) -> int:
        """判断是否为五大联赛"""
        if not league_name:
            return 0
        return 1 if league_name in self.config.TOP_5_LEAGUES else 0

    # ========================================================================
    # Main Extraction Method
    # ========================================================================

    def extract_ultimate_features(
        self,
        match_data: dict[str, Any],
        verbose: bool = False
    ) -> dict[str, float]:
        """
        提取终极特征（整合所有特征源）

        Args:
            match_data: 比赛数据字典，包含：
                - match_id
                - league_name
                - home_team
                - away_team
                - match_date
                - technical_features
                - golden_features
                - l2_raw_json

        Returns:
            完整特征字典
        """
        all_features = {}

        # 1. 从 PureFeatureFilter 获取纯赛前特征
        tech_features = match_data.get("technical_features") or {}
        if tech_features and isinstance(tech_features, str):
            tech_features = json.loads(tech_features)

        golden_features = match_data.get("golden_features") or {}
        if golden_features and isinstance(golden_features, str):
            golden_features = json.loads(golden_features)

        combined = dict(tech_features)
        if golden_features:
            combined.update(golden_features)

        pure_features = self.pure_filter.filter_features(combined, verbose=False)
        all_features.update(pure_features)

        # 2. 添加联赛等级特征
        league_name = match_data.get("league_name")
        all_features["is_top_5_league"] = float(self._is_top_5_league(league_name))

        # 3. 添加疲劳度特征
        fatigue_features = self._calculate_fatigue_features(match_data)
        all_features.update(fatigue_features)

        # 4. 添加缺阵特征
        l2_raw_json = match_data.get("l2_raw_json")
        unavailable_features = self._extract_unavailable_features(l2_raw_json)
        all_features.update(unavailable_features)

        # 5. 添加赔率特征
        match_id = match_data.get("match_id")
        if match_id:
            odds_features = self._get_odds_features(match_id)
            all_features.update(odds_features)

        if verbose:
            logger.info(f"Extracted {len(all_features)} ultimate features for match {match_id}")

        return all_features

    def cleanup(self):
        """清理数据库连接"""
        if self._conn and not self._conn.closed:
            self._conn.close()


# =============================================================================
# Singleton Instance
# =============================================================================

_ultimate_extractor_instance = None


def get_ultimate_extractor() -> UltimateFeatureExtractor:
    """获取终极特征提取器单例"""
    global _ultimate_extractor_instance
    if _ultimate_extractor_instance is None:
        _ultimate_extractor_instance = UltimateFeatureExtractor()
    return _ultimate_extractor_instance
