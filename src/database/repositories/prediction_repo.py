#!/usr/bin/env python3
"""
预测数据仓储层
==============

V4.46.8 重构：从 predict_pipeline.py 剥离的数据访问逻辑。

提供：
- load_pending_matches: 加载待预测比赛
- 特征提取工具函数
- 身价回溯查询

@module src.database.repositories.prediction_repo
@version V4.46.8
@updated 2026-03-11
"""

import json
import logging
import math
import os
from typing import Any, Dict, List, Optional, Tuple

import psycopg2

from src.constants.model_config import (
    DEFAULT_VALUES,
    TITAN_COMBAT_FEATURES,
    get_league_default_mv,
)

logger = logging.getLogger(__name__)


# ============================================================================
# 数据库连接
# ============================================================================


class ConfigError(Exception):
    """配置错误异常"""
    pass


def get_required_env(key: str) -> str:
    """获取必需的环境变量，缺失时报错"""
    value = os.getenv(key)
    if not value:
        raise ConfigError(f"缺少必需的环境变量: {key}")
    return value


def get_db_connection():
    """
    获取数据库连接 (安全加固版)

    V4.46.8: 强制要求 DB_PASSWORD 环境变量，无默认值回退

    Returns:
        psycopg2 连接对象

    Raises:
        ConfigError: 缺少必需的环境变量
    """
    # 强制要求密码
    db_password = get_required_env("DB_PASSWORD")

    return psycopg2.connect(
        host=os.getenv("DB_HOST", "host.docker.internal"),
        port=int(os.getenv("DB_PORT", "5432") or "5432"),
        database=os.getenv("DB_NAME", "football_db"),
        user=os.getenv("DB_USER", "football_user"),
        password=db_password,
    )


# ============================================================================
# 工具函数
# ============================================================================


def safe_float(v: Any, d: float = 0.0) -> float:
    """安全转换为浮点数"""
    try:
        return float(v) if v is not None else d
    except (TypeError, ValueError):
        return d


def safe_log10(v: Any, d: float = 18.0) -> float:
    """安全计算 log10"""
    try:
        return math.log10(v) if v and v > 0 else d
    except (TypeError, ValueError, ZeroDivisionError):
        return d


def parse_jsonb(d: Any) -> Dict:
    """
    安全解析 JSONB 数据

    支持类型:
    - dict: 直接返回
    - bytes: 安全解码后解析
    - str: JSON解析
    - 其他: 返回空字典
    """
    # 已经是字典，直接返回
    if isinstance(d, dict):
        return d

    # 空值检查
    if not d:
        return {}

    # 处理 bytes 对象
    if isinstance(d, bytes):
        try:
            # 使用 errors='ignore' 安全解码
            d = d.decode('utf-8', errors='ignore')
        except Exception:
            return {}

    # 处理字符串
    if isinstance(d, str):
        try:
            return json.loads(d)
        except json.JSONDecodeError:
            return {}

    # 其他类型，返回空字典
    return {}


# ============================================================================
# 数据加载
# ============================================================================


def load_pending_matches(
    conn,
    limit: int = 50,
    league: Optional[str] = None,
) -> List[Dict]:
    """
    加载待预测比赛

    V4.46.7 修改:
    - 移除 h2h_features 非空强制约束
    - 只要求 elo_features 存在即可

    Args:
        conn: 数据库连接
        limit: 最大返回数量
        league: 联赛过滤 (可选)

    Returns:
        比赛数据列表
    """
    cur = conn.cursor()

    # V5.0: 使用新的表结构 golden_features, tactical_features
    # 注意: 不使用 ::text 转换，让 psycopg2 自动处理 JSONB
    query = """
        SELECT m.match_id, m.home_team, m.away_team, m.league_name, m.match_date,
               l.elo_features, l.golden_features, l.tactical_features
        FROM matches m
        INNER JOIN l3_features l ON m.match_id = l.match_id
        WHERE m.match_date > NOW()
          AND m.match_date < NOW() + INTERVAL '7 days'
          AND l.elo_features IS NOT NULL
          AND l.elo_features != '{}'::jsonb
    """
    params = []

    if league:
        query += " AND m.league_name = %s"
        params.append(league)

    query += " ORDER BY m.match_date ASC LIMIT %s"
    params.append(limit)

    cur.execute(query, params)
    rows = cur.fetchall()
    cur.close()

    # 转换为字典列表
    result = []
    for row in rows:
        result.append({
            'match_id': row[0],
            'home_team': row[1],
            'away_team': row[2],
            'league_name': row[3],
            'match_date': row[4],
            'elo_features': row[5],
            'golden_features': row[6],
            'tactical_features': row[7],
        })
    return result


# ============================================================================
# 身价查询
# ============================================================================


def get_team_avg_market_value(
    conn,
    team_name: str,
    limit: int = 5,
) -> Optional[float]:
    """
    获取球队历史平均身价 (回溯 5 场)

    查询策略:
    1. 主队身份回溯
    2. 客队身份回溯
    3. 模糊匹配

    Args:
        conn: 数据库连接
        team_name: 球队名称
        limit: 回溯场次

    Returns:
        平均身价 (欧元)，未找到返回 None
    """
    cur = conn.cursor()

    # 第一层: 主队身份回溯 (V5.0: 使用 golden_features 和 home_market_value_total)
    cur.execute(
        """
        SELECT AVG(mv) as avg_mv FROM (
            SELECT (l.golden_features->>'home_market_value_total')::numeric as mv
            FROM matches m INNER JOIN l3_features l ON m.match_id = l.match_id
            WHERE m.status = 'finished' AND m.home_team = %s
              AND (l.golden_features->>'home_market_value_total')::numeric > 100000000
            ORDER BY m.match_date DESC LIMIT %s
        ) sub
    """,
        (team_name, limit),
    )
    r = cur.fetchone()
    if r and r[0]:
        cur.close()
        return float(r[0])

    # 第二层: 客队身份回溯
    cur.execute(
        """
        SELECT AVG(mv) as avg_mv FROM (
            SELECT (l.golden_features->>'away_market_value_total')::numeric as mv
            FROM matches m INNER JOIN l3_features l ON m.match_id = l.match_id
            WHERE m.status = 'finished' AND m.away_team = %s
              AND (l.golden_features->>'away_market_value_total')::numeric > 100000000
            ORDER BY m.match_date DESC LIMIT %s
        ) sub
    """,
        (team_name, limit),
    )
    r = cur.fetchone()
    if r and r[0]:
        cur.close()
        return float(r[0])

    # 第三层: 模糊匹配
    short_name = team_name[:6] if len(team_name) > 6 else team_name
    cur.execute(
        """
        SELECT AVG(mv) as avg_mv FROM (
            SELECT (l.golden_features->>'home_market_value_total')::numeric as mv
            FROM matches m INNER JOIN l3_features l ON m.match_id = l.match_id
            WHERE m.status = 'finished' AND m.home_team ILIKE %s
              AND (l.golden_features->>'home_market_value_total')::numeric > 100000000
            ORDER BY m.match_date DESC LIMIT %s
        ) sub
    """,
        (f"%{short_name}%", limit),
    )
    r = cur.fetchone()
    cur.close()

    if r and r[0]:
        return float(r[0])
    return None


# ============================================================================
# 特征提取
# ============================================================================


def extract_features(
    elo_data: Any,
    lineup_data: Any,
    h2h_data: Any,
    home_team: Optional[str] = None,
    away_team: Optional[str] = None,
    league_name: Optional[str] = None,
    conn=None,
) -> Tuple[Dict[str, float], bool]:
    """
    提取 11 维战斗特征

    Args:
        elo_data: Elo 特征数据 (JSONB)
        lineup_data: 阵容特征数据 (JSONB)
        h2h_data: H2H 特征数据 (JSONB)
        home_team: 主队名称
        away_team: 客队名称
        league_name: 联赛名称
        conn: 数据库连接 (用于身价回溯)

    Returns:
        (features_dict, h2h_estimated_flag)
    """
    # 延迟导入避免循环依赖
    from src.ml.feature_engine.h2h_estimator import H2HEstimator

    f = {}
    elo = parse_jsonb(elo_data)
    lineup = parse_jsonb(lineup_data)
    h2h = parse_jsonb(h2h_data)
    h2h_estimated = False

    # === Elo 特征 (5 维) ===
    home_elo = safe_float(elo.get("home_elo_pre", elo.get("home_elo", 1500)), 1500)
    away_elo = safe_float(elo.get("away_elo_pre", elo.get("away_elo", 1500)), 1500)
    f["home_elo_pre"] = home_elo
    f["away_elo_pre"] = away_elo
    f["elo_diff"] = safe_float(elo.get("elo_diff", home_elo - away_elo))
    f["expected_home_win"] = safe_float(elo.get("expected_home_win", 0.45))
    f["expected_away_win"] = safe_float(elo.get("expected_away_win", 0.30))

    # === 身价特征 (3 维) ===
    # V5.0: 兼容 golden_features 字段名 (home_market_value_total)
    home_mv = safe_float(
        lineup.get("home_squad_value_eur") or lineup.get("home_market_value_total", 0),
        0
    )
    away_mv = safe_float(
        lineup.get("away_squad_value_eur") or lineup.get("away_market_value_total", 0),
        0
    )

    # MV-Scout: 身价回溯
    if home_mv <= 50000000 and conn and home_team:
        avg = get_team_avg_market_value(conn, home_team)
        home_mv = avg if avg else get_league_default_mv(league_name)
    if away_mv <= 50000000 and conn and away_team:
        avg = get_team_avg_market_value(conn, away_team)
        away_mv = avg if avg else get_league_default_mv(league_name)

    f["log_home_squad_value"] = safe_log10(home_mv, 18.0) if home_mv > 0 else 18.0
    f["log_away_squad_value"] = safe_log10(away_mv, 18.0) if away_mv > 0 else 18.0
    total_mv = home_mv + away_mv
    f["home_mv_share"] = home_mv / total_mv if total_mv > 0 else 0.5

    # === H2H 特征 (3 维) - 核心修改 ===
    if H2HEstimator.needs_estimation(h2h):
        # 触发 H2H 补位
        estimated_h2h = H2HEstimator.estimate_from_elo(
            elo_diff=f["elo_diff"],
            expected_home_win=f["expected_home_win"],
            league_name=league_name,
        )
        f["h2h_home_win_ratio"] = estimated_h2h["h2h_home_win_ratio"]
        f["h2h_draw_ratio"] = estimated_h2h["h2h_draw_ratio"]
        f["h2h_avg_goal_diff"] = estimated_h2h["h2h_avg_goal_diff"]
        h2h_estimated = True
        logger.info(
            f"  [ESTIMATED_H2H] {home_team} vs {away_team} | "
            f"Elo差={f['elo_diff']:+.1f} → H2H_GD={f['h2h_avg_goal_diff']:.2f}"
        )
    else:
        # 使用真实 H2H 数据
        f["h2h_home_win_ratio"] = safe_float(
            h2h.get("h2h_home_win_ratio", h2h.get("home_win_ratio", 0.4)),
            0.4,
        )
        f["h2h_draw_ratio"] = safe_float(
            h2h.get("h2h_draw_ratio", h2h.get("draw_ratio", 0.25)),
            0.25,
        )
        f["h2h_avg_goal_diff"] = safe_float(
            h2h.get("h2h_avg_goal_diff", h2h.get("avg_goal_diff", 0)),
            0,
        )

    return {k: f.get(k, DEFAULT_VALUES.get(k, 0.0)) for k in TITAN_COMBAT_FEATURES}, h2h_estimated


__all__ = [
    "get_db_connection",
    "safe_float",
    "safe_log10",
    "parse_jsonb",
    "load_pending_matches",
    "get_team_avg_market_value",
    "extract_features",
]
