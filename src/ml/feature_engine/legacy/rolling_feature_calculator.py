"""
V41.420 Rolling Feature Calculator - 历史滚动特征计算器
========================================================

为全部 8,877 场比赛计算历史滚动均值：
- rolling_avg_xg_5: 过去 5 场平均预期进球
- rolling_avg_rating_5: 过去 5 场平均评分
- rolling_total_xg_5: 过去 5 场累计预期进球

严格时空隔离：只使用 target_match_date 之前的数据

Author: V41.420 ML Team
Version: V41.420 "Historical Awakening"
Date: 2026-01-21
"""

from __future__ import annotations

from datetime import datetime
import json
import logging
from typing import Any

import numpy as np
import psycopg2
from psycopg2.extras import RealDictCursor

from src.config_unified import get_settings

logger = logging.getLogger(__name__)


class RollingFeatureCalculator:
    """
    V41.420 滚动特征计算器

    从数据库中提取历史比赛数据，计算滚动均值特征
    """

    def __init__(self, window_size: int = 5):
        self.window_size = window_size
        self.settings = get_settings()
        self._conn = None

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

    def load_historical_matches(
        self,
        team_id: str,
        target_date: datetime,
        limit: int | None = None
    ) -> list[dict[str, Any]]:
        """
        加载球队历史比赛

        Args:
            team_id: 球队ID
            target_date: 目标比赛日期（只取此日期之前）
            limit: 最多加载场数

        Returns:
            历史比赛列表
        """
        conn = self._get_connection()
        cursor = conn.cursor()

        limit_clause = f"LIMIT {limit}" if limit else ""

        query = f"""
            SELECT
                m.match_id,
                m.match_date,
                m.home_team_id,
                m.away_team_id,
                m.technical_features,
                m.home_score,
                m.away_score
            FROM matches m
            WHERE m.match_date < %s
              AND (m.home_team_id = %s OR m.away_team_id = %s)
              AND m.technical_features IS NOT NULL
            ORDER BY m.match_date DESC
            {limit_clause}
        """

        cursor.execute(query, (target_date, team_id, team_id))
        matches = cursor.fetchall()
        cursor.close()

        # 解析技术特征
        for match in matches:
            tech = match.get("technical_features")
            if isinstance(tech, str):
                tech = json.loads(tech)
            match["parsed_features"] = tech or {}

        return matches

    def extract_xg_and_rating(
        self,
        match: dict[str, Any],
        team_id: str
    ) -> tuple[float | None, float | None]:
        """
        从技术特征中提取 xG 和评分

        Returns:
            (xg, rating) 或 (None, None)
        """
        features = match.get("parsed_features", {})

        # 判断是主队还是客队
        is_home = match.get("home_team_id") == team_id

        # 提取 xG (尝试多个可能的字段名)
        xg = None
        xg_keys = ["home_xg", "away_xg", "xg", "expected_goals"]
        for key in xg_keys:
            if key in features:
                xg = features[key]
                break

        # 提取评分
        rating = None
        rating_keys = ["home_rating", "away_rating", "rating", "team_rating"]
        for key in rating_keys:
            if key in features:
                rating = features[key]
                break

        return xg, rating

    def calculate_rolling_features(
        self,
        team_id: str,
        target_date: datetime
    ) -> dict[str, float]:
        """
        计算球队滚动特征

        Args:
            team_id: 球队ID
            target_date: 目标比赛日期

        Returns:
            滚动特征字典
        """
        # 加载历史数据（取足够多的历史用于滚动窗口）
        matches = self.load_historical_matches(
            team_id,
            target_date,
            limit=self.window_size * 2  # 多取一些，用于过滤
        )

        xg_values = []
        rating_values = []

        for match in matches:
            xg, rating = self.extract_xg_and_rating(match, team_id)

            if xg is not None and xg > 0:
                xg_values.append(xg)

            if rating is not None and rating > 0:
                rating_values.append(rating)

            # 达到窗口大小即停止
            if len(xg_values) >= self.window_size and len(rating_values) >= self.window_size:
                break

        result = {}

        # xG 滚动特征
        if xg_values:
            result["rolling_avg_xg_5"] = float(np.mean(xg_values[:self.window_size]))
            result["rolling_total_xg_5"] = float(np.sum(xg_values[:self.window_size]))
        else:
            result["rolling_avg_xg_5"] = 0.0
            result["rolling_total_xg_5"] = 0.0

        # 评分滚动特征
        if rating_values:
            result["rolling_avg_rating_5"] = float(np.mean(rating_values[:self.window_size]))
        else:
            result["rolling_avg_rating_5"] = 0.0

        return result

    def calculate_for_all_matches(
        self,
        batch_size: int = 100
    ) -> dict[str, dict[str, float]]:
        """
        为全部比赛计算滚动特征

        Args:
            batch_size: 批处理大小

        Returns:
            {match_id: {rolling_features}}
        """
        conn = self._get_connection()
        cursor = conn.cursor()

        # 获取所有需要计算的比赛
        query = """
            SELECT
                m.match_id,
                m.match_date,
                m.home_team_id,
                m.away_team_id
            FROM matches m
            WHERE m.technical_features IS NOT NULL
            ORDER BY m.match_date ASC
        """

        cursor.execute(query)
        matches = cursor.fetchall()
        cursor.close()

        logger.info(f"Calculating rolling features for {len(matches)} matches...")

        results = {}

        # 按球队缓存历史数据
        home_team_history = {}
        away_team_history = {}

        for i, match in enumerate(matches):
            if i % 100 == 0:
                logger.info(f"  Progress: {i}/{len(matches)}")

            match_id = match["match_id"]
            match_date = match["match_date"]
            home_id = match["home_team_id"]
            away_id = match["away_team_id"]

            # 计算主队滚动特征
            home_features = self.calculate_rolling_features(home_id, match_date)

            # 计算客队滚动特征
            away_features = self.calculate_rolling_features(away_id, match_date)

            # 合并特征
            combined = {
                **{f"home_{k}": v for k, v in home_features.items()},
                **{f"away_{k}": v for k, v in away_features.items()},
            }

            # 计算差值特征
            if "home_rolling_avg_xg_5" in combined and "away_rolling_avg_xg_5" in combined:
                combined["diff_rolling_avg_xg_5"] = (
                    combined["home_rolling_avg_xg_5"] - combined["away_rolling_avg_xg_5"]
                )

            if "home_rolling_avg_rating_5" in combined and "away_rolling_avg_rating_5" in combined:
                combined["diff_rolling_avg_rating_5"] = (
                    combined["home_rolling_avg_rating_5"] - combined["away_rolling_avg_rating_5"]
                )

            results[match_id] = combined

        logger.info(f"  ✅ Calculated rolling features for {len(results)} matches")
        return results

    def save_to_database(
        self,
        rolling_features: dict[str, dict[str, float]]
    ) -> int:
        """
        保存滚动特征到数据库

        将滚动特征更新到 matches 表的 golden_features 字段
        """
        conn = self._get_connection()
        cursor = conn.cursor()

        updated = 0

        for match_id, features in rolling_features.items():
            # 获取现有 golden_features
            cursor.execute(
                "SELECT golden_features FROM matches WHERE match_id = %s",
                (match_id,)
            )
            row = cursor.fetchone()

            if row:
                existing = row.get("golden_features")
                if isinstance(existing, str):
                    existing = json.loads(existing) if existing else {}
                else:
                    existing = existing or {}

                # 合并滚动特征
                existing.update(features)

                # 更新数据库
                cursor.execute(
                    "UPDATE matches SET golden_features = %s::jsonb WHERE match_id = %s",
                    (json.dumps(existing), match_id)
                )
                updated += 1

        conn.commit()
        cursor.close()

        logger.info(f"  ✅ Updated {updated} matches with rolling features")
        return updated

    def cleanup(self):
        """清理资源"""
        if self._conn and not self._conn.closed:
            self._conn.close()


# =============================================================================
# Batch Processing
# =============================================================================

def calculate_and_save_rolling_features(window_size: int = 5) -> int:
    """
    批量计算并保存滚动特征

    Args:
        window_size: 滚动窗口大小

    Returns:
        更新的比赛数量
    """
    calculator = RollingFeatureCalculator(window_size=window_size)

    try:
        logger.info("=" * 70)
        logger.info("V41.420: 批量计算历史滚动特征")
        logger.info("=" * 70)

        # 计算滚动特征
        rolling_features = calculator.calculate_for_all_matches()

        # 保存到数据库
        updated = calculator.save_to_database(rolling_features)

        logger.info("=" * 70)
        logger.info(f"✅ V41.420 完成：更新了 {updated} 场比赛的滚动特征")
        logger.info("=" * 70)

        return updated

    finally:
        calculator.cleanup()


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )

    calculate_and_save_rolling_features(window_size=5)
