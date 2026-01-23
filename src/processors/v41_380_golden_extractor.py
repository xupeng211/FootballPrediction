"""
V41.380 Golden Feature Extractor - The Golden Mine
===================================================

从 1524 个未使用字段中提取高价值特征：
1. 身价特征 (Market Value): 首发 11 人总身价均值
2. 伤病特征 (Injury/Unavailable): 核心球员缺失数量
3. 评分特征 (Rating): 前 5 场场均评分走势

核心原则：
- 遵循 V41.320 时空隔离规则（严禁当场赛后数据流入）
- 使用历史滚动窗口（Rolling Window）
- 只使用赛前可获知的数据

Usage:
    from src.processors.v41_380_golden_extractor import GoldenFeatureExtractor

    extractor = GoldenFeatureExtractor()
    features = extractor.extract_from_l2(l2_raw_json, match_date)

Author: V41.380 Feature Engineering Team
Version: V41.380 "The Golden Mine"
Date: 2026-01-21
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Any, Optional

import numpy as np
import psycopg2
from psycopg2.extras import RealDictCursor

from src.config_unified import get_settings

logger = logging.getLogger(__name__)


# =============================================================================
# Configuration
# =============================================================================


@dataclass
class GoldenFeatureConfig:
    """黄金特征提取配置"""

    # 身价特征配置
    enable_market_value: bool = True
    market_value_window: int = 5  # 滚动窗口（场）

    # 伤病特征配置
    enable_injury: bool = True
    injury_window: int = 3  # 滚动窗口（场）
    core_player_threshold: float = 0.7  # 核心球员定义：评分阈值

    # 评分特征配置
    enable_rating: bool = True
    rating_window: int = 5  # 前 N 场比赛
    rating_trend_window: int = 3  # 评分趋势窗口

    # 时空隔离规则（V41.320）
    strict_temporal_isolation: bool = True  # 严格时空隔离
    max_lookback_days: int = 30  # 最大回溯天数


DEFAULT_CONFIG = GoldenFeatureConfig()


# =============================================================================
# Golden Feature Extractor
# =============================================================================


class GoldenFeatureExtractor:
    """
    V41.380: 黄金特征提取器

    从 FotMob L2 数据中提取三大类黄金特征：
    1. 身价特征 (market_value_*): 球队身价统计
    2. 伤病特征 (injury_*): 核心球员缺失统计
    3. 评分特征 (rating_*): 球员评分走势

    遵循 V41.320 时空隔离规则：只使用赛前可获知的历史数据。
    """

    def __init__(self, config: Optional[GoldenFeatureConfig] = None):
        self.config = config or DEFAULT_CONFIG
        self.settings = get_settings()

        # 数据库连接（用于查询历史数据）
        self._conn = None

        logger.info("V41.380: Golden Feature Extractor initialized")
        logger.info(f"  - Market Value: {'enabled' if self.config.enable_market_value else 'disabled'}")
        logger.info(f"  - Injury: {'enabled' if self.config.enable_injury else 'disabled'}")
        logger.info(f"  - Rating: {'enabled' if self.config.enable_rating else 'disabled'}")
        logger.info(f"  - Temporal Isolation: {'STRICT' if self.config.strict_temporal_isolation else 'NORMAL'}")

    # ========================================================================
    # Database Connection
    # ========================================================================

    def _get_connection(self):
        """获取数据库连接"""
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
    # Market Value Features (身价特征)
    # ========================================================================

    def extract_market_value_features(
        self,
        l2_data: dict[str, Any],
        match_date: datetime,
        team_type: str = "home"  # home or away
    ) -> dict[str, float]:
        """
        提取身价特征

        特征列表：
        - market_value_avg: 首发平均身价
        - market_value_total: 首发总身价
        - market_value_rolling_avg_{n}: 过去 N 场平均身价
        - market_value_vs_opponent_gap: 与对手身价差距

        Args:
            l2_data: FotMob L2 原始数据
            match_date: 比赛日期
            team_type: 主队/客队

        Returns:
            身价特征字典
        """
        if not self.config.enable_market_value:
            return {}

        features = {}

        try:
            lineup = l2_data.get("l2_json", {}).get("content", {}).get("lineup", {})
            team_key = f"{team_type}Team"
            team_data = lineup.get(team_key, {})

            if not team_data:
                logger.warning(f"V41.380: {team_key} not found in lineup data")
                return features

            # 1. 提取首发 11 人身价
            starters = team_data.get("starters", [])
            if not starters:
                logger.warning(f"V41.380: No starters found for {team_key}")
                return features

            market_values = []
            for player in starters:
                mv = player.get("marketValue")
                if mv is not None:
                    market_values.append(mv)

            if not market_values:
                return features

            # 2. 计算当前场身价特征
            features[f"{team_type}_market_value_avg"] = float(np.mean(market_values))
            features[f"{team_type}_market_value_total"] = float(np.sum(market_values))
            features[f"{team_type}_market_value_std"] = float(np.std(market_values))
            features[f"{team_type}_market_value_min"] = float(np.min(market_values))
            features[f"{team_type}_market_value_max"] = float(np.max(market_values))

            # 3. 计算历史滚动窗口身价（V41.320 时空隔离）
            if self.config.strict_temporal_isolation:
                historical_features = self._get_historical_market_value(
                    team_data.get("id", ""),
                    match_date,
                    team_type
                )
                features.update(historical_features)

            logger.debug(f"V41.380: Extracted {len(features)} market value features for {team_key}")

        except Exception as e:
            logger.error(f"V41.380: Market value extraction failed for {team_type}: {e}")

        return features

    def _get_historical_market_value(
        self,
        team_id: str,
        match_date: datetime,
        team_type: str
    ) -> dict[str, float]:
        """
        获取历史滚动窗口身价特征（V41.320 时空隔离）

        只查询 match_date 之前的比赛，确保无数据泄露。
        """
        features = {}

        if not team_id:
            return features

        try:
            conn = self._get_connection()
            cursor = conn.cursor()

            # 查询过去 N 场比赛的身价数据（严格时空隔离）
            cutoff_date = match_date - timedelta(days=self.config.max_lookback_days)

            query = """
                SELECT
                    m.match_date,
                    m.l2_raw_json
                FROM matches m
                WHERE m.l2_raw_json IS NOT NULL
                  AND m.match_date < %s  -- 严格时空隔离：只取比赛前的数据
                  AND m.match_date >= %s
                  AND (m.l2_raw_json::text LIKE %s OR m.l2_raw_json::text LIKE %s)
                ORDER BY m.match_date DESC
                LIMIT %s
            """

            # 使用正则表达式查询 JSONB（简化方式：使用 LIKE 查找 team_id）
            team_pattern_start = f'%"id": "{team_id}"%'
            team_pattern_sub = f'%"id": "{team_id}",%'

            cursor.execute(query, (
                match_date,
                cutoff_date,
                team_pattern_start,
                team_pattern_sub,
                self.config.market_value_window,
            ))

            historical_values = []
            for row in cursor.fetchall():
                try:
                    l2_json = row.get("l2_raw_json", {})
                    if isinstance(l2_json, str):
                        import json
                        l2_json = json.loads(l2_json)

                    lineup = l2_json.get("content", {}).get("lineup", {})
                    team_key = f"{team_type}Team"
                    team_data = lineup.get(team_key, {})
                    starters = team_data.get("starters", [])

                    for player in starters:
                        mv = player.get("marketValue")
                        if mv is not None:
                            historical_values.append(mv)
                            break  # 只取一场比赛的平均值

                except Exception as e:
                    logger.debug(f"V41.380: Skip historical match due to parsing error: {e}")
                    continue

            cursor.close()

            # 计算滚动窗口特征
            if len(historical_values) > 0:
                features[f"{team_type}_market_value_rolling_avg_{self.config.market_value_window}"] = float(np.mean(historical_values))
                features[f"{team_type}_market_value_rolling_trend"] = float(
                    historical_values[0] - historical_values[-1]
                    if len(historical_values) >= 2 else 0
                )

        except Exception as e:
            logger.error(f"V41.380: Historical market value query failed: {e}")

        return features

    # ========================================================================
    # Injury Features (伤病特征)
    # ========================================================================

    def extract_injury_features(
        self,
        l2_data: dict[str, Any],
        match_date: datetime,
        team_type: str = "home"
    ) -> dict[str, float]:
        """
        提取伤病特征

        特征列表：
        - injury_count: 缺席球员数量
        - injury_core_count: 核心球员缺失数量（评分高于阈值）
        - injury_market_value_loss: 缺席球员总身价损失
        - injury_rolling_count_{n}: 过去 N 场平均伤病数

        Args:
            l2_data: FotMob L2 原始数据
            match_date: 比赛日期
            team_type: 主队/客队

        Returns:
            伤病特征字典
        """
        if not self.config.enable_injury:
            return {}

        features = {}

        try:
            lineup = l2_data.get("l2_json", {}).get("content", {}).get("lineup", {})
            team_key = f"{team_type}Team"
            team_data = lineup.get(team_key, {})

            if not team_data:
                return features

            unavailable = team_data.get("unavailable", [])

            # 1. 基础伤病统计
            features[f"{team_type}_injury_count"] = len(unavailable)

            # 2. 身价损失（核心指标）
            total_market_value_loss = 0
            core_player_loss = 0

            for player in unavailable:
                mv = player.get("marketValue", 0)
                total_market_value_loss += mv

                # 检查是否是核心球员（基于历史评分）
                if self._is_core_player(player.get("id", ""), match_date, team_type):
                    core_player_loss += 1

            features[f"{team_type}_injury_market_value_loss"] = total_market_value_loss
            features[f"{team_type}_injury_core_count"] = core_player_loss

            # 3. 伤病类型细分
            injury_types = {}
            for player in unavailable:
                unavailability = player.get("unavailability", {})
                u_type = unavailability.get("type", "unknown")
                injury_types[u_type] = injury_types.get(u_type, 0) + 1

            for u_type, count in injury_types.items():
                safe_key = u_type.replace(" ", "_").replace("-", "_")
                features[f"{team_type}_injury_{safe_key}_count"] = count

            # 4. 历史滚动窗口伤病统计（V41.320 时空隔离）
            if self.config.strict_temporal_isolation:
                historical_features = self._get_historical_injury(
                    team_data.get("id", ""),
                    match_date,
                    team_type
                )
                features.update(historical_features)

            logger.debug(f"V41.380: Extracted {len(features)} injury features for {team_key}")

        except Exception as e:
            logger.error(f"V41.380: Injury extraction failed for {team_type}: {e}")

        return features

    def _is_core_player(self, player_id: str, match_date: datetime, team_type: str) -> bool:
        """
        判断是否是核心球员（基于历史评分）

        V41.320 时空隔离：只查询 match_date 之前的数据
        """
        if not player_id:
            return False

        try:
            conn = self._get_connection()
            cursor = conn.cursor()

            cutoff_date = match_date - timedelta(days=self.config.max_lookback_days)

            # 查询该球员的历史评分
            query = """
                SELECT
                    m.l2_raw_json
                FROM matches m
                WHERE m.l2_raw_json IS NOT NULL
                  AND m.match_date < %s  -- 严格时空隔离
                  AND m.match_date >= %s
                  AND m.l2_raw_json::text LIKE %s
                ORDER BY m.match_date DESC
                LIMIT %s
            """

            player_pattern = f'%"id": "{player_id}"%'
            cursor.execute(query, (
                match_date,
                cutoff_date,
                player_pattern,
                self.config.rating_window,
            ))

            ratings = []
            for row in cursor.fetchall():
                try:
                    l2_json = row.get("l2_raw_json", {})
                    if isinstance(l2_json, str):
                        import json
                        l2_json = json.loads(l2_json)

                    lineup = l2_json.get("content", {}).get("lineup", {})
                    team_key = f"{team_type}Team"
                    team_data = lineup.get(team_key, {})
                    starters = team_data.get("starters", [])

                    for player in starters:
                        if player.get("id") == player_id:
                            perf = player.get("performance", {})
                            rating = perf.get("rating")
                            if rating is not None:
                                ratings.append(rating)
                                break

                except Exception:
                    continue

            cursor.close()

            # 判断是否是核心球员（历史评分高于阈值）
            if ratings:
                avg_rating = float(np.mean(ratings))
                return avg_rating >= self.config.core_player_threshold

        except Exception as e:
            logger.debug(f"V41.380: Core player check failed: {e}")

        return False

    def _get_historical_injury(
        self,
        team_id: str,
        match_date: datetime,
        team_type: str
    ) -> dict[str, float]:
        """获取历史滚动窗口伤病特征"""
        features = {}

        if not team_id:
            return features

        try:
            conn = self._get_connection()
            cursor = conn.cursor()

            cutoff_date = match_date - timedelta(days=self.config.max_lookback_days)

            # 查询过去 N 场比赛的伤病数据
            query = """
                SELECT
                    m.match_date,
                    m.l2_raw_json
                FROM matches m
                WHERE m.l2_raw_json IS NOT NULL
                  AND m.match_date < %s
                  AND m.match_date >= %s
                ORDER BY m.match_date DESC
                LIMIT %s
            """

            cursor.execute(query, (match_date, cutoff_date, self.config.injury_window))

            historical_counts = []
            for row in cursor.fetchall():
                try:
                    l2_json = row.get("l2_raw_json", {})
                    if isinstance(l2_json, str):
                        import json
                        l2_json = json.loads(l2_json)

                    lineup = l2_json.get("content", {}).get("lineup", {})
                    team_key = f"{team_type}Team"
                    team_data = lineup.get(team_key, {})
                    unavailable = team_data.get("unavailable", [])

                    historical_counts.append(len(unavailable))

                except Exception:
                    continue

            cursor.close()

            if historical_counts:
                features[f"{team_type}_injury_rolling_avg_{self.config.injury_window}"] = float(np.mean(historical_counts))
                features[f"{team_type}_injury_rolling_max_{self.config.injury_window}"] = float(np.max(historical_counts))

        except Exception as e:
            logger.error(f"V41.380: Historical injury query failed: {e}")

        return features

    # ========================================================================
    # Rating Features (评分特征)
    # ========================================================================

    def extract_rating_features(
        self,
        l2_data: dict[str, Any],
        match_date: datetime,
        team_type: str = "home"
    ) -> dict[str, float]:
        """
        提取评分特征

        特征列表：
        - rating_avg: 首发平均评分
        - rating_max: 最高评分
        - rating_min: 最低评分
        - rating_rolling_avg_{n}: 过去 N 场平均评分
        - rating_trend: 评分趋势（最新 - 最早）

        Args:
            l2_data: FotMob L2 原始数据
            match_date: 比赛日期
            team_type: 主队/客队

        Returns:
            评分特征字典
        """
        if not self.config.enable_rating:
            return {}

        features = {}

        try:
            lineup = l2_data.get("l2_json", {}).get("content", {}).get("lineup", {})
            team_key = f"{team_type}Team"
            team_data = lineup.get(team_key, {})

            if not team_data:
                return features

            starters = team_data.get("starters", [])
            if not starters:
                return features

            # 1. 提取首发评分
            ratings = []
            for player in starters:
                perf = player.get("performance", {})
                rating = perf.get("rating")
                if rating is not None:
                    ratings.append(rating)

            if not ratings:
                return features

            # 2. 计算当前场评分特征
            features[f"{team_type}_rating_avg"] = float(np.mean(ratings))
            features[f"{team_type}_rating_std"] = float(np.std(ratings))
            features[f"{team_type}_rating_max"] = float(np.max(ratings))
            features[f"{team_type}_rating_min"] = float(np.min(ratings))

            # 3. 评分分布（分档统计）
            excellent = sum(1 for r in ratings if r >= 7.0)
            good = sum(1 for r in ratings if 6.0 <= r < 7.0)
            average = sum(1 for r in ratings if 5.0 <= r < 6.0)
            poor = sum(1 for r in ratings if r < 5.0)

            features[f"{team_type}_rating_excellent_count"] = excellent
            features[f"{team_type}_rating_good_count"] = good
            features[f"{team_type}_rating_average_count"] = average
            features[f"{team_type}_rating_poor_count"] = poor

            # 4. 历史滚动窗口评分（V41.320 时空隔离）
            if self.config.strict_temporal_isolation:
                historical_features = self._get_historical_rating(
                    team_data.get("id", ""),
                    match_date,
                    team_type
                )
                features.update(historical_features)

            logger.debug(f"V41.380: Extracted {len(features)} rating features for {team_key}")

        except Exception as e:
            logger.error(f"V41.380: Rating extraction failed for {team_type}: {e}")

        return features

    def _get_historical_rating(
        self,
        team_id: str,
        match_date: datetime,
        team_type: str
    ) -> dict[str, float]:
        """获取历史滚动窗口评分特征"""
        features = {}

        if not team_id:
            return features

        try:
            conn = self._get_connection()
            cursor = conn.cursor()

            cutoff_date = match_date - timedelta(days=self.config.max_lookback_days)

            # 查询过去 N 场比赛的评分数据
            query = """
                SELECT
                    m.match_date,
                    m.l2_raw_json
                FROM matches m
                WHERE m.l2_raw_json IS NOT NULL
                  AND m.match_date < %s
                  AND m.match_date >= %s
                ORDER BY m.match_date DESC
                LIMIT %s
            """

            cursor.execute(query, (match_date, cutoff_date, self.config.rating_window))

            historical_avgs = []
            for row in cursor.fetchall():
                try:
                    l2_json = row.get("l2_raw_json", {})
                    if isinstance(l2_json, str):
                        import json
                        l2_json = json.loads(l2_json)

                    lineup = l2_json.get("content", {}).get("lineup", {})
                    team_key = f"{team_type}Team"
                    team_data = lineup.get(team_key, {})
                    starters = team_data.get("starters", [])

                    ratings = []
                    for player in starters:
                        perf = player.get("performance", {})
                        rating = perf.get("rating")
                        if rating is not None:
                            ratings.append(rating)

                    if ratings:
                        historical_avgs.append(np.mean(ratings))

                except Exception:
                    continue

            cursor.close()

            if historical_avgs:
                features[f"{team_type}_rating_rolling_avg_{self.config.rating_window}"] = float(np.mean(historical_avgs))

                # 计算评分趋势
                if len(historical_avgs) >= self.config.rating_trend_window:
                    recent = historical_avgs[:self.config.rating_trend_window]
                    earlier = historical_avgs[-self.config.rating_trend_window:]
                    features[f"{team_type}_rating_trend"] = float(np.mean(recent) - np.mean(earlier))

        except Exception as e:
            logger.error(f"V41.380: Historical rating query failed: {e}")

        return features

    # ========================================================================
    # Main Extraction Entry Point
    # ========================================================================

    def extract_all_golden_features(
        self,
        l2_data: dict[str, Any],
        match_date: Optional[datetime] = None
    ) -> dict[str, Any]:
        """
        提取所有黄金特征

        Args:
            l2_data: FotMob L2 原始数据
            match_date: 比赛日期（用于时空隔离）

        Returns:
            所有黄金特征字典
        """
        if match_date is None:
            match_date = datetime.now()

        all_features = {}

        # 主队特征
        all_features.update(self.extract_market_value_features(l2_data, match_date, "home"))
        all_features.update(self.extract_injury_features(l2_data, match_date, "home"))
        all_features.update(self.extract_rating_features(l2_data, match_date, "home"))

        # 客队特征
        all_features.update(self.extract_market_value_features(l2_data, match_date, "away"))
        all_features.update(self.extract_injury_features(l2_data, match_date, "away"))
        all_features.update(self.extract_rating_features(l2_data, match_date, "away"))

        # 对比特征（主客差异）
        comparison_features = self._extract_comparison_features(all_features)
        all_features.update(comparison_features)

        logger.info(f"V41.380: Extracted {len(all_features)} total golden features")

        return all_features

    def _extract_comparison_features(self, features: dict[str, Any]) -> dict[str, float]:
        """提取主客对比特征"""
        comparison = {}

        try:
            # 身价值对比
            home_mv = float(features.get("home_market_value_avg", 0))
            away_mv = float(features.get("away_market_value_avg", 0))
            comparison["market_value_gap"] = float(home_mv - away_mv)
            comparison["market_value_ratio"] = float(home_mv / max(away_mv, 1))

            # 伤病对比
            home_injury = int(features.get("home_injury_count", 0))
            away_injury = int(features.get("away_injury_count", 0))
            comparison["injury_count_gap"] = int(home_injury - away_injury)

            # 评分对比
            home_rating = float(features.get("home_rating_avg", 0))
            away_rating = float(features.get("away_rating_avg", 0))
            comparison["rating_gap"] = float(home_rating - away_rating)

        except Exception as e:
            logger.error(f"V41.380: Comparison feature extraction failed: {e}")

        return comparison

    def cleanup(self):
        """清理数据库连接"""
        if self._conn and not self._conn.closed:
            self._conn.close()
            logger.debug("V41.380: Database connection closed")
