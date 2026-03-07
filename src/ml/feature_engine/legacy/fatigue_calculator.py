#!/usr/bin/env python3
"""
V79.100 Fatigue Calculator - 疲劳度计算器
==========================================

从 UltimateFeatureExtractor 拆分出来的疲劳度计算模块。

核心功能：
1. 计算休息天数 (rest_days)
2. 判断忙碌周 (busy_week)
3. 查询历史比赛日期
4. 生成疲劳度特征

Author: V79.100 Engineering Team
Version: V79.100 "Fatigue Calculator"
Date: 2026-01-25
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
import logging
from typing import Any

import psycopg2
from psycopg2.extras import RealDictCursor

from src.config.config_loader import get_hyper_parameters_config
from src.config_unified import get_settings
from src.ml.feature_engine.legacy.base_processor import calculate_date_difference

logger = logging.getLogger(__name__)


# =============================================================================
# Configuration
# =============================================================================

@dataclass
class FatigueCalculatorConfig:
    """疲劳度计算器配置"""

    busy_week_threshold: int = 4  # 休息天数 < 4 视为忙碌周
    default_rest_days: int = 14   # 无历史比赛时的默认值


DEFAULT_FATIGUE_CONFIG = FatigueCalculatorConfig()


# =============================================================================
# Fatigue Calculator
# =============================================================================

class FatigueCalculator:
    """
    V79.100 疲劳度计算器

    专注于计算球队的疲劳度相关特征，包括休息天数、忙碌周判断等。
    """

    def __init__(self, config: FatigueCalculatorConfig | None = None):
        """
        初始化疲劳度计算器

        Args:
            config: 配置对象
        """
        self.config = config or DEFAULT_FATIGUE_CONFIG
        self.settings = get_settings()
        self._conn = None

        # 从 hyper_parameters.yaml 加载配置（如果可用）
        try:
            hyper_params = get_hyper_parameters_config()
            self.config.busy_week_threshold = hyper_params.busy_week_threshold
            self.config.default_rest_days = hyper_params.default_rest_days
        except (FileNotFoundError, yaml.YAMLError, KeyError, AttributeError) as e:
            logger.debug(f"Using default fatigue config: {e}")

    def _get_connection(self) -> psycopg2.extensions.connection:
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

    def close(self) -> None:
        """关闭数据库连接"""
        if self._conn and not self._conn.closed:
            self._conn.close()
            self._conn = None

    def calculate_rest_days(
        self,
        current_date: datetime,
        prev_date: datetime | None
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

        # 使用 base_processor 的工具函数
        rest_days = calculate_date_difference(current_date, prev_date)

        # 如果返回默认值，使用配置的默认值
        if rest_days == 14:  # base_processor 返回的默认值
            return self.config.default_rest_days

        return rest_days

    def is_busy_week(self, rest_days: int) -> int:
        """
        判断是否为忙碌周（休息天数 < 阈值）

        Args:
            rest_days: 休息天数

        Returns:
            1 如果是忙碌周，0 否则
        """
        return 1 if rest_days < self.config.busy_week_threshold else 0

    def get_previous_match_date(
        self,
        team_name: str,
        current_match_date: datetime,
        league_name: str | None = None
    ) -> datetime | None:
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

    def calculate_fatigue_features(
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
        home_prev_date = self.get_previous_match_date(home_team, match_date, league_name)
        home_rest_days = self.calculate_rest_days(match_date, home_prev_date)
        home_is_busy = self.is_busy_week(home_rest_days)

        features.update({
            "home_rest_days": float(home_rest_days),
            "home_is_busy_week": float(home_is_busy),
        })

        # 客队疲劳度
        away_prev_date = self.get_previous_match_date(away_team, match_date, league_name)
        away_rest_days = self.calculate_rest_days(match_date, away_prev_date)
        away_is_busy = self.is_busy_week(away_rest_days)

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

    def cleanup(self) -> None:
        """清理资源"""
        self.close()


# =============================================================================
# Utility Functions
# =============================================================================

def calculate_fatigue_for_match(
    match_data: dict[str, Any],
    calculator: FatigueCalculator | None = None
) -> dict[str, float]:
    """
    便捷函数：计算单场比赛的疲劳度特征

    Args:
        match_data: 比赛数据
        calculator: 疲劳度计算器实例（可选）

    Returns:
        疲劳度特征字典
    """
    if calculator is None:
        calculator = FatigueCalculator()

    try:
        return calculator.calculate_fatigue_features(match_data)
    finally:
        calculator.cleanup()


# =============================================================================
# Type Aliases
# =============================================================================

# 常用类型别名
MatchData = dict[str, Any]
FatigueFeatures = dict[str, float]
