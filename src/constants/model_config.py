#!/usr/bin/env python3
"""
TITAN 模型配置常量
==================

V4.46.8 重构：从 predict_pipeline.py 剥离的模型配置常量。

本模块提供：
- TITAN_COMBAT_FEATURES: 11 维特征列表
- DEFAULT_VALUES: 特征默认值
- RESULT_MAP: 结果编码映射
- LEAGUE_DEFAULT_MV: 联赛默认身价

@module src.constants.model_config
@version V4.46.8
@updated 2026-03-11
"""

from pathlib import Path
from typing import Dict, List

# ============================================================================
# 模型目录
# ============================================================================

MODEL_DIR = Path(__file__).parent.parent.parent / "models"

# ============================================================================
# 结果编码映射
# ============================================================================

RESULT_MAP: Dict[str, int] = {"H": 2, "D": 1, "A": 0}
RESULT_NAMES: List[str] = ["AWAY", "DRAW", "HOME"]
RESULT_MAP_REVERSE: Dict[int, str] = {2: "H", 1: "D", 0: "A"}

# ============================================================================
# 11 维纯净特征集 (TITAN Combat Features)
# ============================================================================

TITAN_COMBAT_FEATURES: List[str] = [
    # Elo 特征 (5 维)
    "home_elo_pre",
    "away_elo_pre",
    "elo_diff",
    "expected_home_win",
    "expected_away_win",
    # 身价特征 (3 维)
    "log_home_squad_value",
    "log_away_squad_value",
    "home_mv_share",
    # H2H 特征 (3 维)
    "h2h_home_win_ratio",
    "h2h_draw_ratio",
    "h2h_avg_goal_diff",
]

# ============================================================================
# 特征默认值
# ============================================================================

DEFAULT_VALUES: Dict[str, float] = {
    # Elo 默认值
    "home_elo_pre": 1500.0,
    "away_elo_pre": 1500.0,
    "elo_diff": 0.0,
    "expected_home_win": 0.45,
    "expected_away_win": 0.30,
    # 身价默认值 (log10 欧元)
    "log_home_squad_value": 18.0,
    "log_away_squad_value": 18.0,
    "home_mv_share": 0.50,
    # H2H 默认值
    "h2h_home_win_ratio": 0.40,
    "h2h_draw_ratio": 0.25,
    "h2h_avg_goal_diff": 0.0,
}

# ============================================================================
# 联赛默认身价 (欧元)
# ============================================================================

LEAGUE_DEFAULT_MV: Dict[str, int] = {
    "Premier League": 350_000_000,
    "La Liga": 250_000_000,
    "Serie A": 250_000_000,
    "Bundesliga": 250_000_000,
    "Ligue 1": 200_000_000,
}

# ============================================================================
# 联赛主场胜率基准 (用于 H2H 冷启动回退)
# ============================================================================

LEAGUE_HOME_WIN_BASELINE: Dict[str, float] = {
    "Premier League": 0.42,
    "La Liga": 0.45,
    "Serie A": 0.44,
    "Bundesliga": 0.43,
    "Ligue 1": 0.41,
    "default": 0.40,
}

LEAGUE_DRAW_BASELINE: Dict[str, float] = {
    "Premier League": 0.24,
    "La Liga": 0.25,
    "Serie A": 0.26,
    "Bundesliga": 0.23,
    "Ligue 1": 0.25,
    "default": 0.25,
}

# ============================================================================
# 工具函数
# ============================================================================


def get_league_default_mv(league_name: str) -> int:
    """
    获取联赛默认身价

    Args:
        league_name: 联赛名称

    Returns:
        默认身价 (欧元)
    """
    return LEAGUE_DEFAULT_MV.get(league_name, 150_000_000)


def get_league_home_win_baseline(league_name: str) -> float:
    """
    获取联赛主场胜率基准

    Args:
        league_name: 联赛名称

    Returns:
        主场胜率基准值
    """
    if not league_name:
        return LEAGUE_HOME_WIN_BASELINE["default"]

    # 模糊匹配联赛名
    for key, value in LEAGUE_HOME_WIN_BASELINE.items():
        if key.lower() in league_name.lower() or league_name.lower() in key.lower():
            return value

    return LEAGUE_HOME_WIN_BASELINE["default"]


def get_league_draw_baseline(league_name: str) -> float:
    """
    获取联赛平局率基准

    Args:
        league_name: 联赛名称

    Returns:
        平局率基准值
    """
    if not league_name:
        return LEAGUE_DRAW_BASELINE["default"]

    for key, value in LEAGUE_DRAW_BASELINE.items():
        if key.lower() in league_name.lower() or league_name.lower() in key.lower():
            return value

    return LEAGUE_DRAW_BASELINE["default"]


__all__ = [
    "MODEL_DIR",
    "RESULT_MAP",
    "RESULT_NAMES",
    "RESULT_MAP_REVERSE",
    "TITAN_COMBAT_FEATURES",
    "DEFAULT_VALUES",
    "LEAGUE_DEFAULT_MV",
    "LEAGUE_HOME_WIN_BASELINE",
    "LEAGUE_DRAW_BASELINE",
    "get_league_default_mv",
    "get_league_home_win_baseline",
    "get_league_draw_baseline",
]
