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
# TITAN V5.2 HOME-FORTRESS - 38 维主客场感知特征集
# ============================================================================

TITAN_COMBAT_FEATURES: List[str] = [
    # 基础特征 (11 维) - 保留原核心特征
    "home_elo_pre",
    "away_elo_pre",
    "elo_diff",
    "expected_home_win",
    "expected_away_win",
    "log_home_squad_value",
    "log_away_squad_value",
    "home_mv_share",
    "h2h_home_win_ratio",
    "h2h_draw_ratio",
    "h2h_avg_goal_diff",

    # 滚动统计特征 (7 维) - 关键滚动指标
    "home_last5_xg_avg",
    "away_last5_xg_avg",
    "home_last5_win_rate",
    "away_last5_win_rate",
    "home_last5_draw_rate",
    "away_last5_draw_rate",
    "rest_days_diff",

    # 效率特征 (5 维) - 进攻/防守效率
    "home_shot_conversion",
    "away_shot_conversion",
    "home_finishing_efficiency",
    "away_finishing_efficiency",
    "finishing_efficiency_diff",

    # 平局体质特征 (7 维) - 平局预测优化
    "home_draw_rate",
    "away_draw_rate",
    "home_draw_tendency",
    "away_draw_tendency",
    "combined_draw_probability",
    "match_stalemate_index",
    "tactical_stalemate_index",

    # V5.2 主客场分离特征 (8 维) - HOME-FORTRESS
    "home_last5_home_only_xg",
    "home_last5_home_only_win_rate",
    "home_home_win_rate",
    "home_home_draw_rate",
    "away_last5_away_only_xg",
    "away_last5_away_only_win_rate",
    "away_away_win_rate",
    "away_away_draw_rate",

    # V5.2 主场堡垒指数 (1 维)
    "fortress_index",

    # V5.2 特征交互 (3 维) - 化学反应
    "elo_rest_synergy",
    "value_form_boost",
    "fortress_strength",
]

# 兼容旧模型的11维特征
TITAN_COMBAT_FEATURES_LEGACY: List[str] = [
    "home_elo_pre",
    "away_elo_pre",
    "elo_diff",
    "expected_home_win",
    "expected_away_win",
    "log_home_squad_value",
    "log_away_squad_value",
    "home_mv_share",
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
    # 滚动统计默认值
    "home_last5_xg_avg": 1.2,
    "away_last5_xg_avg": 1.2,
    "home_last5_win_rate": 0.33,
    "away_last5_win_rate": 0.33,
    "home_last5_draw_rate": 0.25,
    "away_last5_draw_rate": 0.25,
    "rest_days_diff": 0.0,
    # 效率特征默认值
    "home_shot_conversion": 0.33,
    "away_shot_conversion": 0.33,
    "home_finishing_efficiency": 1.0,
    "away_finishing_efficiency": 1.0,
    "finishing_efficiency_diff": 0.0,
    # 平局体质默认值
    "home_draw_rate": 0.25,
    "away_draw_rate": 0.25,
    "home_draw_tendency": 0.0,
    "away_draw_tendency": 0.0,
    "combined_draw_probability": 0.25,
    "match_stalemate_index": 0.0,
    "tactical_stalemate_index": 1.0,
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
