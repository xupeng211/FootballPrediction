#!/usr/bin/env python3
"""
V79.000 Odds Trend Analyzer - 赔率动向分析器
===============================================

从 UltimateFeatureExtractor 拆分出来的赔率动向分析模块。

核心功能：
1. 赔率动向特征计算 (drop_ratio, change_ratio)
2. 初盘/终盘赔率解析
3. 总变化幅度计算
4. 数据库赔率数据查询

Author: V79.000 Engineering Team
Version: V79.000 "Odds Trend Analyzer"
Date: 2026-01-25
"""

from __future__ import annotations

import logging
from typing import Any

import psycopg2
from psycopg2.extras import RealDictCursor

from src.config_unified import get_settings

logger = logging.getLogger(__name__)


# =============================================================================
# Configuration
# =============================================================================

class OddsTrendConfig:
    """赔率动向分析配置"""

    # 最小赔率值（防止除零）
    min_odds_value: float = 0.01

    # 默认赔率动向特征值（数据缺失时）
    default_movement: float = 0.0


DEFAULT_ODDS_CONFIG = OddsTrendConfig()


# =============================================================================
# Odds Trend Analyzer
# =============================================================================

class OddsTrendAnalyzer:
    """
    V79.000 赔率动向分析器

    从 UltimateFeatureExtractor 拆分出来，专注于赔率动向特征计算。
    """

    def __init__(self, config: OddsTrendConfig | None = None):
        """
        初始化赔率动向分析器

        Args:
            config: 配置对象
        """
        self.config = config or DEFAULT_ODDS_CONFIG
        self.settings = get_settings()
        self._conn = None

    def _get_connection(self) -> psycopg2.extensions.connection:
        """
        获取数据库连接

        Returns:
            数据库连接对象

        Raises:
            psycopg2.Error: 数据库连接失败
        """
        if self._conn is None or self._conn.closed:
            self._conn = psycopg2.connect(
                host=self.settings.database.host,
                database=self.settings.database.name,
                user=self.settings.database.user,
                password=self.settings.database.password.get_secret_value(),
                cursor_factory=RealDictCursor,
            )
        return self._conn

    def close(self) -> None:
        """关闭数据库连接"""
        if self._conn and not self._conn.closed:
            self._conn.close()
            self._conn = None

    def calculate_odds_movement(
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
            赔率动向特征字典:
            - home_drop_ratio: 主胜赔率下降比率
            - draw_change_ratio: 平局赔率变化比率
            - away_change_ratio: 客胜赔率变化比率
            - total_movement: 总变化幅度
        """
        # 数据缺失时返回默认值
        if not initial_price or not closing_price:
            return {
                "home_drop_ratio": self.config.default_movement,
                "draw_change_ratio": self.config.default_movement,
                "away_change_ratio": self.config.default_movement,
                "total_movement": self.config.default_movement,
            }

        if len(initial_price) < 3 or len(closing_price) < 3:
            return {
                "home_drop_ratio": self.config.default_movement,
                "draw_change_ratio": self.config.default_movement,
                "away_change_ratio": self.config.default_movement,
                "total_movement": self.config.default_movement,
            }

        # 计算变化比率
        features = {}

        # 主胜赔率下降比率（正值表示下降）
        features["home_drop_ratio"] = (
            (initial_price[0] - closing_price[0]) /
            max(initial_price[0], self.config.min_odds_value)
        )

        # 平局赔率变化比率
        features["draw_change_ratio"] = (
            (initial_price[1] - closing_price[1]) /
            max(initial_price[1], self.config.min_odds_value)
        )

        # 客胜赔率变化比率
        features["away_change_ratio"] = (
            (initial_price[2] - closing_price[2]) /
            max(initial_price[2], self.config.min_odds_value)
        )

        # 总变化幅度
        features["total_movement"] = (
            abs(features["home_drop_ratio"]) +
            abs(features["draw_change_ratio"]) +
            abs(features["away_change_ratio"])
        )

        return features

    def get_odds_features(self, match_id: str) -> dict[str, float]:
        """
        从 match_odds_intelligence 表获取赔率特征

        Args:
            match_id: 比赛 ID

        Returns:
            赔率动向特征字典
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
            logger.debug(f"No odds data found for match {match_id}")
            return {}

        initial = result.get("initial_price")
        closing = result.get("closing_price")

        return self.calculate_odds_movement(initial, closing)

    def get_odds_features_batch(
        self,
        match_ids: list[str]
    ) -> dict[str, dict[str, float]]:
        """
        批量获取多场比赛的赔率特征

        Args:
            match_ids: 比赛 ID 列表

        Returns:
            {match_id: odds_features} 字典
        """
        if not match_ids:
            return {}

        conn = self._get_connection()
        cursor = conn.cursor()

        query = """
            SELECT match_id, initial_price, closing_price
            FROM match_odds_intelligence
            WHERE match_id = ANY(%s)
        """

        cursor.execute(query, (list(match_ids),))
        results = cursor.fetchall()
        cursor.close()

        odds_features = {}
        for result in results:
            match_id = result.get("match_id")
            initial = result.get("initial_price")
            closing = result.get("closing_price")
            odds_features[match_id] = self.calculate_odds_movement(initial, closing)

        return odds_features

    def cleanup(self) -> None:
        """清理资源（供子类扩展）"""
        self.close()


# =============================================================================
# Utility Functions
# =============================================================================

def validate_odds_price(price: Any) -> list[float] | None:
    """
    验证赔率数据格式

    Args:
        price: 赔率数据（list 或其他格式）

    Returns:
        标准化的赔率列表 [home, draw, away] 或 None
    """
    if not price:
        return None

    if isinstance(price, list):
        if len(price) >= 3:
            return price[:3]
        return None

    # 如果是其他格式，尝试转换
    if isinstance(price, dict):
        # 尝试从字典中提取
        return [
            float(price.get("home", 0)),
            float(price.get("draw", 0)),
            float(price.get("away", 0)),
        ]

    return None


# =============================================================================
# Type Aliases
# =============================================================================

# 常用类型别名
OddsPrice = list[float] | None
OddsFeatures = dict[str, float]
