"""
V41.450 Starting-11 Delta Calculator - 首发11人战力差计算器
========================================================

核心逻辑：
- 计算两队"已确认首发"与"历史常备首发"的评分差
- 捕捉核心球员缺阵导致的战力断崖
- 如果强队首发缺了3个8.0分大腿，AI必须捕获到这个信号

Author: V41.450 Data Science Team
Version: V41.450 "Deep Temporal Alignment"
Date: 2026-01-21
"""

from __future__ import annotations

from dataclasses import dataclass, field
import logging
from typing import Any

import numpy as np

logger = logging.getLogger(__name__)


# =============================================================================
# Data Models
# =============================================================================

@dataclass
class PlayerInfo:
    """球员信息"""
    player_id: str
    player_name: str
    rating: float  # 最近评分
    is_starter: bool = False  # 是否首发
    position: str | None = None  # 位置
    market_value: float | None = None  # 身价（百万欧元）


@dataclass
class LineupInfo:
    """首发阵容信息"""
    team_id: str
    team_name: str
    confirmed_starters: list[PlayerInfo] = field(default_factory=list)
    historical_regulars: list[PlayerInfo] = field(default_factory=list)

    # 计算得出的指标
    starter_avg_rating: float = 0.0
    regular_avg_rating: float = 0.0
    rating_delta: float = 0.0  # 首发评分 - 常规评分

    # 缺阵大腿数（评分 >= 7.5 的常规首发但未首发）
    missing_stars_count: int = 0
    missing_stars_total_rating: float = 0.0


# =============================================================================
# Starting-11 Delta Calculator
# =============================================================================

class Starting11DeltaCalculator:
    """
    V41.450 首发11人战力差计算器

    计算逻辑：
    1. 获取已确认首发阵容
    2. 获取历史常规首发（近5场平均评分最高的11人）
    3. 计算评分差：starter_avg_rating - regular_avg_rating
    4. 识别缺阵大腿（评分>=7.5的常规首发但未首发）
    """

    # 评分阈值
    STAR_RATING_THRESHOLD = 7.5
    CRITICAL_RATING_THRESHOLD = 8.0

    def __init__(self, history_window: int = 5):
        """
        初始化计算器

        Args:
            history_window: 历史窗口大小（用于确定常规首发）
        """
        self.history_window = history_window

    def calculate_lineup_delta(
        self,
        confirmed_starters: list[dict[str, Any]],
        historical_players: list[dict[str, Any]],
        team_name: str
    ) -> LineupInfo:
        """
        计算首发阵容战力差

        Args:
            confirmed_starters: 已确认首发球员列表
            historical_players: 历史球员数据（近N场）
            team_name: 球队名称

        Returns:
            LineupInfo 对象
        """
        # 解析首发球员
        starters = self._parse_players(confirmed_starters, is_starter=True)

        # 解析历史球员并确定常规首发
        all_players = self._parse_players(historical_players, is_starter=False)
        regulars = self._get_regular_starters(all_players)

        # 计算平均评分
        starter_avg = np.mean([p.rating for p in starters]) if starters else 0.0
        regular_avg = np.mean([p.rating for p in regulars]) if regulars else 0.0

        # 计算评分差
        rating_delta = starter_avg - regular_avg

        # 识别缺阵大腿
        missing_stars = self._find_missing_stars(regulars, starters)
        missing_stars_count = len(missing_stars)
        missing_stars_total_rating = sum(p.rating for p in missing_stars)

        return LineupInfo(
            team_id=team_name,  # 简化：使用 team_name 作为 ID
            team_name=team_name,
            confirmed_starters=starters,
            historical_regulars=regulars,
            starter_avg_rating=round(starter_avg, 3),
            regular_avg_rating=round(regular_avg, 3),
            rating_delta=round(rating_delta, 3),
            missing_stars_count=missing_stars_count,
            missing_stars_total_rating=round(missing_stars_total_rating, 3),
        )

    def _parse_players(
        self,
        players_data: list[dict[str, Any]],
        is_starter: bool
    ) -> list[PlayerInfo]:
        """解析球员数据"""
        players = []

        for player_data in players_data:
            try:
                # 提取关键信息（容错）
                player_id = str(player_data.get("player_id", player_data.get("id", "")))
                player_name = player_data.get("player_name", player_data.get("name", "Unknown"))

                # 评分（容错）
                rating = float(player_data.get("rating", player_data.get("average_rating", 6.0)))
                if not np.isfinite(rating):
                    rating = 6.0

                # 位置
                position = player_data.get("position", player_data.get("position_short", None))

                # 身价（可选）
                market_value = player_data.get("market_value")
                if market_value is not None:
                    try:
                        market_value = float(market_value)
                    except (TypeError, ValueError):
                        market_value = None

                players.append(PlayerInfo(
                    player_id=player_id,
                    player_name=player_name,
                    rating=rating,
                    is_starter=is_starter,
                    position=position,
                    market_value=market_value,
                ))
            except Exception as e:
                logger.debug(f"Failed to parse player: {e}")
                continue

        return players

    def _get_regular_starters(
        self,
        all_players: list[PlayerInfo]
    ) -> list[PlayerInfo]:
        """
        从历史球员中确定常规首发

        逻辑：选择评分最高的11人作为"常规首发"
        """
        if not all_players:
            return []

        # 按评分降序排序
        sorted_players = sorted(all_players, key=lambda p: p.rating, reverse=True)

        # 取前11人
        return sorted_players[:11]

    def _find_missing_stars(
        self,
        regulars: list[PlayerInfo],
        starters: list[PlayerInfo]
    ) -> list[PlayerInfo]:
        """
        找出缺阵的大腿球员

        逻辑：常规首发中评分 >= STAR_RATING_THRESHOLD 但未首发的球员
        """
        starter_ids = {p.player_id for p in starters}

        missing_stars = []
        for regular in regulars:
            if regular.rating >= self.STAR_RATING_THRESHOLD:
                if regular.player_id not in starter_ids:
                    missing_stars.append(regular)

        return sorted(missing_stars, key=lambda p: p.rating, reverse=True)


# =============================================================================
# Match-Level Calculator
# =============================================================================

class MatchStarting11Calculator:
    """
    V41.450 比赛级别首发计算器

    计算主客两队的首发战力差，并生成特征
    """

    # 评分阈值（从 Starting11DeltaCalculator 复制）
    STAR_RATING_THRESHOLD = 7.5
    CRITICAL_RATING_THRESHOLD = 8.0

    def __init__(self):
        self.delta_calculator = Starting11DeltaCalculator()

    def calculate_match_features(
        self,
        home_starters: list[dict[str, Any]],
        home_historical: list[dict[str, Any]],
        away_starters: list[dict[str, Any]],
        away_historical: list[dict[str, Any]],
        home_team_name: str,
        away_team_name: str
    ) -> dict[str, float]:
        """
        计算比赛的首发11人特征

        Returns:
            特征字典
        """
        # 计算主队首发差
        home_lineup = self.delta_calculator.calculate_lineup_delta(
            home_starters, home_historical, home_team_name
        )

        # 计算客队首发差
        away_lineup = self.delta_calculator.calculate_lineup_delta(
            away_starters, away_historical, away_team_name
        )

        # 生成特征
        features = {
            # === 主队首发特征 ===
            "home_starter_avg_rating": home_lineup.starter_avg_rating,
            "home_regular_avg_rating": home_lineup.regular_avg_rating,
            "home_rating_delta": home_lineup.rating_delta,
            "home_missing_stars_count": float(home_lineup.missing_stars_count),
            "home_missing_stars_total_rating": home_lineup.missing_stars_total_rating,

            # === 客队首发特征 ===
            "away_starter_avg_rating": away_lineup.starter_avg_rating,
            "away_regular_avg_rating": away_lineup.regular_avg_rating,
            "away_rating_delta": away_lineup.rating_delta,
            "away_missing_stars_count": float(away_lineup.missing_stars_count),
            "away_missing_stars_total_rating": away_lineup.missing_stars_total_rating,

            # === 差值特征 ===
            "diff_starter_avg_rating": home_lineup.starter_avg_rating - away_lineup.starter_avg_rating,
            "diff_rating_delta": home_lineup.rating_delta - away_lineup.rating_delta,
            "diff_missing_stars_count": float(home_lineup.missing_stars_count - away_lineup.missing_stars_count),

            # === 关键信号 ===
            "home_critical_weakened": 1.0 if home_lineup.missing_stars_total_rating >= self.CRITICAL_RATING_THRESHOLD else 0.0,
            "away_critical_weakened": 1.0 if away_lineup.missing_stars_total_rating >= self.CRITICAL_RATING_THRESHOLD else 0.0,
        }

        return features

    def calculate_from_lineup_data(
        self,
        lineup_data: dict[str, Any],
        home_team_name: str,
        away_team_name: str
    ) -> dict[str, float]:
        """
        从阵容数据中计算首发特征

        Args:
            lineup_data: 包含 home_lineup, away_lineup 的数据
            home_team_name: 主队名称
            away_team_name: 客队名称

        Returns:
            特征字典
        """
        # 提取阵容数据
        home_lineup_data = lineup_data.get("home_lineup", {})
        away_lineup_data = lineup_data.get("away_lineup", {})

        home_starters = home_lineup_data.get("starters", [])
        home_historical = home_lineup_data.get("historical_players", [])

        away_starters = away_lineup_data.get("starters", [])
        away_historical = away_lineup_data.get("historical_players", [])

        return self.calculate_match_features(
            home_starters, home_historical,
            away_starters, away_historical,
            home_team_name, away_team_name
        )


# =============================================================================
# Singleton
# =============================================================================

_starting_11_calculator_instance = None


def get_starting_11_calculator() -> MatchStarting11Calculator:
    """获取首发11人计算器单例"""
    global _starting_11_calculator_instance
    if _starting_11_calculator_instance is None:
        _starting_11_calculator_instance = MatchStarting11Calculator()
    return _starting_11_calculator_instance


# =============================================================================
# Demo / Test
# =============================================================================

if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG)

    # 模拟数据：主队（强队）缺了几个大腿
    home_starters = [
        {"player_id": "h1", "player_name": "Player H1", "rating": 7.2},
        {"player_id": "h2", "player_name": "Player H2", "rating": 6.8},
        {"player_id": "h3", "player_name": "Player H3", "rating": 7.0},
        {"player_id": "h4", "player_name": "Player H4", "rating": 6.5},
        {"player_id": "h5", "player_name": "Player H5", "rating": 6.9},
        {"player_id": "h6", "player_name": "Player H6", "rating": 7.1},
        {"player_id": "h7", "player_name": "Player H7", "rating": 6.7},
        {"player_id": "h8", "player_name": "Player H8", "rating": 6.6},
        {"player_id": "h9", "player_name": "Player H9", "rating": 7.3},
        {"player_id": "h10", "player_name": "Player H10", "rating": 6.4},
        {"player_id": "h11", "player_name": "Player H11", "rating": 6.8},
    ]

    # 历史球员（包含几个8.0+大腿，但本场没首发）
    home_historical = [
        *home_starters,
        {"player_id": "h12", "player_name": "Star H12", "rating": 8.2},  # 缺阵大腿
        {"player_id": "h13", "player_name": "Star H13", "rating": 7.8},  # 缺阵大腿
        {"player_id": "h14", "player_name": "Star H14", "rating": 7.6},  # 缺阵大腿
        {"player_id": "h15", "player_name": "Player H15", "rating": 6.5},
    ]

    # 客队（完整阵容）
    away_starters = [
        {"player_id": "a1", "player_name": "Player A1", "rating": 7.0},
        {"player_id": "a2", "player_name": "Player A2", "rating": 6.9},
        {"player_id": "a3", "player_name": "Player A3", "rating": 7.1},
        {"player_id": "a4", "player_name": "Player A4", "rating": 6.8},
        {"player_id": "a5", "player_name": "Player A5", "rating": 7.2},
        {"player_id": "a6", "player_name": "Player A6", "rating": 6.7},
        {"player_id": "a7", "player_name": "Player A7", "rating": 6.6},
        {"player_id": "a8", "player_name": "Player A8", "rating": 7.0},
        {"player_id": "a9", "player_name": "Player A9", "rating": 6.9},
        {"player_id": "a10", "player_name": "Player A10", "rating": 7.1},
        {"player_id": "a11", "player_name": "Player A11", "rating": 6.8},
    ]

    away_historical = [
        *away_starters,
        {"player_id": "a12", "player_name": "Player A12", "rating": 6.5},
        {"player_id": "a13", "player_name": "Player A13", "rating": 6.4},
    ]

    # 计算特征
    calculator = MatchStarting11Calculator()
    features = calculator.calculate_match_features(
        home_starters, home_historical,
        away_starters, away_historical,
        "Home Team", "Away Team"
    )

    logger.info("\n" + "=" * 70)
    logger.info("V41.450 Starting-11 Delta Calculator Demo")
    logger.info("=" * 70)
    logger.info("\n特征输出:")
    for key, value in sorted(features.items()):
        logger.info(f"  {key:35s} = {value}")

    logger.info("\n关键信号:")
    logger.info(f"  主队缺阵大腿数: {features['home_missing_stars_count']}")
    logger.info(f"  主队缺阵大腿总评分: {features['home_missing_stars_total_rating']:.2f}")
    logger.info(f"  主队战力削弱信号: {features['home_critical_weakened']}")
    logger.info("=" * 70)
