#!/usr/bin/env python3
# ═══════════════════════════════════════════════════════════════════════════════
# ║   TITAN-V4.46.7 预测管道 - 全量覆盖版                                        ║
# ║   FULL COVERAGE VERSION - H2H ESTIMATOR ENABLED                              ║
# ═══════════════════════════════════════════════════════════════════════════════
#
# 【V4.46.7 新增】
# 1. H2HEstimator: 当 H2H 数据缺失时，基于 Elo 差进行智能补位
# 2. 移除 h2h_features 非空强制约束，扩大预测覆盖率
# 3. 联赛主场胜率基准回退机制
#
# 【特征对齐】
# - Elo (5): home_elo_pre, away_elo_pre, elo_diff, expected_home_win, expected_away_win
# - 身价 (3): log_home_squad_value, log_away_squad_value, home_mv_share
# - H2H (3): h2h_home_win_ratio, h2h_draw_ratio, h2h_avg_goal_diff
#
# @module scripts.ops.predict_pipeline
# @version V4.46.7-FULL-COVERAGE
# @updated 2026-03-11

import argparse
import json
import logging
import math
import os
import sys
from dataclasses import dataclass, asdict, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import joblib
import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

logging.basicConfig(
    level=logging.INFO,
    format='[%(asctime)s] %(message)s',
    datefmt='%H:%M:%S'
)
logger = logging.getLogger(__name__)

# ============================================================================
# 配置常量
# ============================================================================

MODEL_DIR = Path(__file__).parent.parent.parent / "models"

RESULT_MAP = {"H": 2, "D": 1, "A": 0}
RESULT_NAMES = ["AWAY", "DRAW", "HOME"]
RESULT_MAP_REVERSE = {2: "H", 1: "D", 0: "A"}

# ============================================================================
# 11 维纯净特征集
# ============================================================================

TITAN_COMBAT_FEATURES = [
    "home_elo_pre", "away_elo_pre", "elo_diff", "expected_home_win", "expected_away_win",
    "log_home_squad_value", "log_away_squad_value", "home_mv_share",
    "h2h_home_win_ratio", "h2h_draw_ratio", "h2h_avg_goal_diff",
]

DEFAULT_VALUES = {
    "home_elo_pre": 1500.0, "away_elo_pre": 1500.0, "elo_diff": 0.0,
    "expected_home_win": 0.45, "expected_away_win": 0.30,
    "log_home_squad_value": 18.0, "log_away_squad_value": 18.0, "home_mv_share": 0.50,
    "h2h_home_win_ratio": 0.40, "h2h_draw_ratio": 0.25, "h2h_avg_goal_diff": 0.0,
}

LEAGUE_DEFAULT_MV = {
    'Premier League': 350_000_000, 'La Liga': 250_000_000,
    'Serie A': 250_000_000, 'Bundesliga': 250_000_000, 'Ligue 1': 200_000_000,
}

# ============================================================================
# 联赛主场胜率基准 (用于 H2H 冷启动回退)
# ============================================================================

LEAGUE_HOME_WIN_BASELINE = {
    'Premier League': 0.42, 'La Liga': 0.45, 'Serie A': 0.44,
    'Bundesliga': 0.43, 'Ligue 1': 0.41,
    # 默认值
    'default': 0.40,
}

LEAGUE_DRAW_BASELINE = {
    'Premier League': 0.24, 'La Liga': 0.25, 'Serie A': 0.26,
    'Bundesliga': 0.23, 'Ligue 1': 0.25,
    'default': 0.25,
}

# ============================================================================
# 数据类定义
# ============================================================================

@dataclass
class MatchPrediction:
    match_id: str
    home_team: str
    away_team: str
    league: str
    match_time: str
    home_prob: float
    draw_prob: float
    away_prob: float
    recommendation: str
    confidence: float
    kelly_fraction: float = 0.0
    kelly_stake: float = 0.0
    home_odds: Optional[float] = None
    draw_odds: Optional[float] = None
    away_odds: Optional[float] = None
    value_edge: Optional[float] = None
    elo_diff: float = 0.0
    mv_share: float = 0.5
    h2h_estimated: bool = False  # 新增: 标记 H2H 是否为估算值

@dataclass
class PredictionReport:
    generated_at: str
    total_matches: int
    predictions: List[Dict[str, Any]]
    summary: Dict[str, Any]

# ============================================================================
# H2H 补位引擎 (核心新增)
# ============================================================================

class H2HEstimator:
    """
    H2H 智能补位引擎

    当真实 H2H 数据缺失时，基于 Elo 差值进行线性推演:
    - h2h_avg_goal_diff = elo_diff / 100 * 0.5
    - h2h_home_win_ratio = 基于 expected_home_win 的平滑值
    - h2h_draw_ratio = 联赛平局基准
    """

    # Elo 差值到净胜球的转换系数 (每 100 分 Elo 差 ≈ 0.5 球)
    ELO_TO_GOAL_COEFF = 0.005

    # 主场胜率平滑参数
    HOME_WIN_SMOOTH_FACTOR = 0.85

    @classmethod
    def estimate_from_elo(cls, elo_diff: float, expected_home_win: float,
                          league_name: str = None) -> Dict[str, float]:
        """
        基于 Elo 数据估算 H2H 特征

        Args:
            elo_diff: 主队 Elo - 客队 Elo
            expected_home_win: Elo 期望主胜率
            league_name: 联赛名称 (用于获取基准值)

        Returns:
            估算的 H2H 特征字典
        """
        # 1. 估算历史净胜球差 (线性映射)
        # Elo 差 +200 → 预期 +1 球优势
        h2h_avg_goal_diff = elo_diff * cls.ELO_TO_GOAL_COEFF

        # 2. 估算主胜率 (基于 Elo 期望值平滑)
        # 使用加权平均: 70% Elo期望 + 30% 联赛基准
        league_baseline = cls._get_league_home_win_baseline(league_name)
        h2h_home_win_ratio = (
            expected_home_win * cls.HOME_WIN_SMOOTH_FACTOR +
            league_baseline * (1 - cls.HOME_WIN_SMOOTH_FACTOR)
        )

        # 3. 估算平局率 (使用联赛基准)
        h2h_draw_ratio = cls._get_league_draw_baseline(league_name)

        return {
            'h2h_avg_goal_diff': round(h2h_avg_goal_diff, 3),
            'h2h_home_win_ratio': round(h2h_home_win_ratio, 3),
            'h2h_draw_ratio': round(h2h_draw_ratio, 3),
            'estimated': True
        }

    @classmethod
    def _get_league_home_win_baseline(cls, league_name: str) -> float:
        """获取联赛主场胜率基准"""
        if not league_name:
            return LEAGUE_HOME_WIN_BASELINE['default']

        # 模糊匹配联赛名
        for key, value in LEAGUE_HOME_WIN_BASELINE.items():
            if key.lower() in league_name.lower() or league_name.lower() in key.lower():
                return value

        return LEAGUE_HOME_WIN_BASELINE['default']

    @classmethod
    def _get_league_draw_baseline(cls, league_name: str) -> float:
        """获取联赛平局率基准"""
        if not league_name:
            return LEAGUE_DRAW_BASELINE['default']

        for key, value in LEAGUE_DRAW_BASELINE.items():
            if key.lower() in league_name.lower() or league_name.lower() in key.lower():
                return value

        return LEAGUE_DRAW_BASELINE['default']

    @classmethod
    def needs_estimation(cls, h2h_data: Dict) -> bool:
        """
        判断 H2H 数据是否需要补位

        触发条件:
        1. h2h_data 为空
        2. h2h_avg_goal_diff 为 0 或缺失
        3. h2h_home_win_ratio 为 0 或缺失
        """
        if not h2h_data:
            return True

        avg_gd = h2h_data.get('h2h_avg_goal_diff', h2h_data.get('avg_goal_diff', 0))
        win_ratio = h2h_data.get('h2h_home_win_ratio', h2h_data.get('home_win_ratio', 0))

        # 如果两个关键特征都为 0，认为数据缺失
        return (avg_gd == 0 and win_ratio == 0) or (avg_gd is None and win_ratio is None)

# ============================================================================
# 工具函数
# ============================================================================

def get_db_connection():
    import psycopg2
    from psycopg2.extras import RealDictCursor
    return psycopg2.connect(
        host=os.getenv('DB_HOST', 'host.docker.internal'),
        port=int(os.getenv('DB_PORT', 5432)),
        database=os.getenv('DB_NAME', 'football_db'),
        user=os.getenv('DB_USER', 'football_user'),
        password=os.getenv('DB_PASSWORD', 'football_pass'),
        cursor_factory=RealDictCursor
    )

def safe_float(v, d=0.0):
    try:
        return float(v) if v is not None else d
    except:
        return d

def safe_log10(v, d=18.0):
    try:
        return math.log10(v) if v and v > 0 else d
    except:
        return d

def parse_jsonb(d):
    if not d:
        return {}
    if isinstance(d, str):
        try:
            return json.loads(d)
        except:
            return {}
    return d if isinstance(d, dict) else {}

def get_team_avg_market_value(conn, team_name, limit=5):
    """获取球队历史平均身价 (回溯 5 场)"""
    cur = conn.cursor()

    # 第一层: 主队身份回溯
    cur.execute("""
        SELECT AVG(mv) as avg_mv FROM (
            SELECT (l.lineup_features->>'home_squad_value_eur')::numeric as mv
            FROM matches m INNER JOIN l3_features l ON m.match_id = l.match_id
            WHERE m.status = 'finished' AND m.home_team = %s
              AND (l.lineup_features->>'home_squad_value_eur')::numeric > 100000000
            ORDER BY m.match_date DESC LIMIT %s
        ) sub
    """, (team_name, limit))
    r = cur.fetchone()
    if r and r['avg_mv']:
        cur.close()
        return float(r['avg_mv'])

    # 第二层: 客队身份回溯
    cur.execute("""
        SELECT AVG(mv) as avg_mv FROM (
            SELECT (l.lineup_features->>'away_squad_value_eur')::numeric as mv
            FROM matches m INNER JOIN l3_features l ON m.match_id = l.match_id
            WHERE m.status = 'finished' AND m.away_team = %s
              AND (l.lineup_features->>'away_squad_value_eur')::numeric > 100000000
            ORDER BY m.match_date DESC LIMIT %s
        ) sub
    """, (team_name, limit))
    r = cur.fetchone()
    if r and r['avg_mv']:
        cur.close()
        return float(r['avg_mv'])

    # 第三层: 模糊匹配
    short_name = team_name[:6] if len(team_name) > 6 else team_name
    cur.execute("""
        SELECT AVG(mv) as avg_mv FROM (
            SELECT (l.lineup_features->>'home_squad_value_eur')::numeric as mv
            FROM matches m INNER JOIN l3_features l ON m.match_id = l.match_id
            WHERE m.status = 'finished' AND m.home_team ILIKE %s
              AND (l.lineup_features->>'home_squad_value_eur')::numeric > 100000000
            ORDER BY m.match_date DESC LIMIT %s
        ) sub
    """, (f'%{short_name}%', limit))
    r = cur.fetchone()
    cur.close()

    if r and r['avg_mv']:
        return float(r['avg_mv'])
    return None

def get_league_default_mv(league_name):
    return LEAGUE_DEFAULT_MV.get(league_name, 150_000_000)

# ============================================================================
# 特征提取 (集成 H2H 补位)
# ============================================================================

def extract_features(elo_data, lineup_data, h2h_data, home_team=None, away_team=None,
                     league_name=None, conn=None) -> Tuple[Dict, bool]:
    """
    提取 11 维战斗特征

    Returns:
        (features_dict, h2h_estimated_flag)
    """
    f = {}
    elo = parse_jsonb(elo_data)
    lineup = parse_jsonb(lineup_data)
    h2h = parse_jsonb(h2h_data)
    h2h_estimated = False

    # === Elo 特征 (5 维) ===
    home_elo = safe_float(elo.get('home_elo_pre', elo.get('home_elo', 1500)), 1500)
    away_elo = safe_float(elo.get('away_elo_pre', elo.get('away_elo', 1500)), 1500)
    f['home_elo_pre'] = home_elo
    f['away_elo_pre'] = away_elo
    f['elo_diff'] = safe_float(elo.get('elo_diff', home_elo - away_elo))
    f['expected_home_win'] = safe_float(elo.get('expected_home_win', 0.45))
    f['expected_away_win'] = safe_float(elo.get('expected_away_win', 0.30))

    # === 身价特征 (3 维) ===
    home_mv = safe_float(lineup.get('home_squad_value_eur', 0), 0)
    away_mv = safe_float(lineup.get('away_squad_value_eur', 0), 0)

    # MV-Scout: 身价回溯
    if home_mv <= 50000000 and conn and home_team:
        avg = get_team_avg_market_value(conn, home_team)
        home_mv = avg if avg else get_league_default_mv(league_name)
    if away_mv <= 50000000 and conn and away_team:
        avg = get_team_avg_market_value(conn, away_team)
        away_mv = avg if avg else get_league_default_mv(league_name)

    f['log_home_squad_value'] = safe_log10(home_mv, 18.0) if home_mv > 0 else 18.0
    f['log_away_squad_value'] = safe_log10(away_mv, 18.0) if away_mv > 0 else 18.0
    total_mv = home_mv + away_mv
    f['home_mv_share'] = home_mv / total_mv if total_mv > 0 else 0.5

    # === H2H 特征 (3 维) - 核心修改 ===
    if H2HEstimator.needs_estimation(h2h):
        # 触发 H2H 补位
        estimated_h2h = H2HEstimator.estimate_from_elo(
            elo_diff=f['elo_diff'],
            expected_home_win=f['expected_home_win'],
            league_name=league_name
        )
        f['h2h_home_win_ratio'] = estimated_h2h['h2h_home_win_ratio']
        f['h2h_draw_ratio'] = estimated_h2h['h2h_draw_ratio']
        f['h2h_avg_goal_diff'] = estimated_h2h['h2h_avg_goal_diff']
        h2h_estimated = True
        logger.info(f"  [ESTIMATED_H2H] {home_team} vs {away_team} | Elo差={f['elo_diff']:+.1f} → H2H_GD={f['h2h_avg_goal_diff']:.2f}")
    else:
        # 使用真实 H2H 数据
        f['h2h_home_win_ratio'] = safe_float(
            h2h.get('h2h_home_win_ratio', h2h.get('home_win_ratio', 0.4)), 0.4
        )
        f['h2h_draw_ratio'] = safe_float(
            h2h.get('h2h_draw_ratio', h2h.get('draw_ratio', 0.25)), 0.25
        )
        f['h2h_avg_goal_diff'] = safe_float(
            h2h.get('h2h_avg_goal_diff', h2h.get('avg_goal_diff', 0)), 0
        )

    return {k: f.get(k, DEFAULT_VALUES.get(k, 0.0)) for k in TITAN_COMBAT_FEATURES}, h2h_estimated

# ============================================================================
# 模型加载器
# ============================================================================

class TitanModelLoader:
    def __init__(self):
        self._model = None
        self._scaler = None

    @property
    def is_loaded(self):
        return self._model is not None

    @property
    def has_scaler(self):
        return self._scaler is not None

    def load(self):
        mp = MODEL_DIR / "titan_v4466_real_combat.joblib"
        sp = MODEL_DIR / "titan_v4466_real_combat_scaler.joblib"

        if not mp.exists():
            for m, s in [("titan_v4466_combat_final.joblib", "titan_v4466_combat_final_scaler.joblib")]:
                if (MODEL_DIR / m).exists():
                    mp, sp = MODEL_DIR / m, MODEL_DIR / s
                    break

        if mp.exists():
            try:
                self._model = joblib.load(str(mp))
                if sp.exists():
                    self._scaler = joblib.load(str(sp))
                logger.info(f"模型加载成功: {mp.name}")
                return True
            except Exception as e:
                logger.warning(f"模型加载失败: {e}")
                return False
        logger.warning("未找到可用模型")
        return False

    def predict(self, features):
        if not self.is_loaded:
            raise RuntimeError("模型未加载")

        X_df = pd.DataFrame(
            [[features.get(n, DEFAULT_VALUES.get(n, 0.0)) for n in TITAN_COMBAT_FEATURES]],
            columns=TITAN_COMBAT_FEATURES
        )

        if self.has_scaler:
            X = self._scaler.transform(X_df)
        else:
            X = X_df.values

        probs = self._model.predict_proba(X)[0]
        return probs[0], probs[1], probs[2]

def get_titan_model():
    m = TitanModelLoader()
    m.load()
    return m

# ============================================================================
# 数据加载 (移除 H2H 强制约束)
# ============================================================================

def load_pending_matches(conn, limit=50, league=None):
    """
    加载待预测比赛

    【V4.46.7 修改】
    - 移除 h2h_features 非空强制约束
    - 只要求 elo_features 存在即可
    """
    cur = conn.cursor()

    # 核心修改: 不再强制要求 h2h_features
    q = """
        SELECT m.match_id, m.home_team, m.away_team, m.league_name, m.match_date,
               l.elo_features, l.lineup_features, l.h2h_features
        FROM matches m
        INNER JOIN l3_features l ON m.match_id = l.match_id
        WHERE m.match_date > NOW()
          AND m.match_date < NOW() + INTERVAL '7 days'
          AND l.elo_features IS NOT NULL
          AND l.elo_features != '{}'::jsonb
    """
    params = []

    if league:
        q += " AND m.league_name = %s"
        params.append(league)

    q += " ORDER BY m.match_date ASC LIMIT %s"
    params.append(limit)

    cur.execute(q, params)
    rows = cur.fetchall()
    cur.close()
    return rows

# ============================================================================
# 预测管道主逻辑
# ============================================================================

def run_prediction_pipeline(limit=50, league=None, dry_run=False):
    logger.info("=" * 70)
    logger.info("  TITAN-V4.46.7 预测管道 - 全量覆盖版")
    logger.info("  特征: 11 维 (Elo + 身价 + H2H[补位引擎])")
    logger.info("=" * 70)

    titan = get_titan_model()
    if not titan.is_loaded:
        logger.error("模型加载失败")
        return PredictionReport(datetime.now().isoformat(), 0, [], {'error': 'Model not loaded'})

    conn = get_db_connection()
    matches = load_pending_matches(conn, limit, league)
    logger.info(f"加载 {len(matches)} 场待预测比赛")

    if not matches:
        conn.close()
        return PredictionReport(datetime.now().isoformat(), 0, [], {})

    preds = []
    hc = dc = ac = 0
    tc = 0.0
    estimated_count = 0  # 统计 H2H 补位数量

    for m in matches:
        try:
            f, h2h_est = extract_features(
                m['elo_features'], m['lineup_features'], m['h2h_features'],
                m['home_team'], m['away_team'], m['league_name'], conn
            )

            if h2h_est:
                estimated_count += 1

            ap, dp, hp = titan.predict(f)

            if hp >= dp and hp >= ap:
                rec, conf = 'HOME', hp
            elif dp >= ap:
                rec, conf = 'DRAW', dp
            else:
                rec, conf = 'AWAY', ap

            if rec == 'HOME':
                hc += 1
            elif rec == 'DRAW':
                dc += 1
            else:
                ac += 1
            tc += conf

            preds.append(asdict(MatchPrediction(
                match_id=m['match_id'],
                home_team=m['home_team'],
                away_team=m['away_team'],
                league=m['league_name'],
                match_time=str(m['match_date'])[:16],
                home_prob=round(hp, 4),
                draw_prob=round(dp, 4),
                away_prob=round(ap, 4),
                recommendation=rec,
                confidence=round(conf, 4),
                elo_diff=f['elo_diff'],
                mv_share=f['home_mv_share'],
                h2h_estimated=h2h_est
            )))
        except Exception as e:
            logger.error(f"预测失败 [{m['match_id']}]: {e}")

    t = len(preds)
    summary = {
        'home_count': hc,
        'draw_count': dc,
        'away_count': ac,
        'home_pct': (hc / t * 100) if t else 0,
        'draw_pct': (dc / t * 100) if t else 0,
        'away_pct': (ac / t * 100) if t else 0,
        'avg_confidence': (tc / t) if t else 0,
        'h2h_estimated_count': estimated_count,
        'h2h_real_count': t - estimated_count,
        'model_version': 'TITAN-V4.46.7-FULL-COVERAGE',
        'feature_count': 11
    }

    logger.info(f"预测完成: {t} 场 | H2H补位: {estimated_count} 场 | 真实H2H: {t - estimated_count} 场")

    conn.close()
    return PredictionReport(datetime.now().isoformat(), t, preds, summary)

# ============================================================================
# 报告格式化
# ============================================================================

def format_report(r):
    lines = [
        '',
        '═' * 70,
        '  TITAN-V4.46.7 预测报告 - 全量覆盖版',
        '═' * 70,
        f'  生成时间: {r.generated_at}',
        f'  比赛数量: {r.total_matches}',
    ]

    s = r.summary
    lines.extend([
        f'  预测分布: 主{s.get("home_count", 0)} | 平{s.get("draw_count", 0)} | 客{s.get("away_count", 0)}',
        f'  平均置信度: {s.get("avg_confidence", 0):.1%}',
        f'  H2H 数据: 真实 {s.get("h2h_real_count", 0)} 场 | 补位 {s.get("h2h_estimated_count", 0)} 场',
    ])

    if not r.predictions:
        lines.append('  无预测结果')
        return '\n'.join(lines)

    sp = sorted(r.predictions, key=lambda x: x['confidence'], reverse=True)

    lines.extend(['', '─' * 70, '  高置信度推荐 (Top 10)', '─' * 70])

    for i, p in enumerate(sp[:10], 1):
        e = {'HOME': '🏠', 'DRAW': '🤝', 'AWAY': '✈️'}.get(p['recommendation'], '❓')
        h2h_tag = ' [补位]' if p.get('h2h_estimated') else ''

        lines.extend([
            '',
            f'  {i:2d}. {p["home_team"]:<20} vs {p["away_team"]:<20}{h2h_tag}',
            f'      联赛: {p["league"]:<20} | 时间: {p["match_time"]}',
            f'      概率: 主{p["home_prob"]:.1%} 平{p["draw_prob"]:.1%} 客{p["away_prob"]:.1%}',
            f'      Elo差: {p["elo_diff"]:+.1f} | 身价占比: {p["mv_share"]:.1%}',
            f'      推荐: {e} {p["recommendation"]} (置信度: {p["confidence"]:.1%})',
        ])

    lines.extend([
        '',
        '═' * 70,
        '  TITAN-V4.46.7 FULL COVERAGE - H2H Estimator Enabled',
        '═' * 70,
    ])

    return '\n'.join(lines)

# ============================================================================
# 主入口
# ============================================================================

def main():
    pa = argparse.ArgumentParser(description='TITAN-V4.46.7 预测管道 - 全量覆盖版')
    pa.add_argument('--limit', type=int, default=100)
    pa.add_argument('--league')
    pa.add_argument('--dry-run', action='store_true')
    a = pa.parse_args()

    print(format_report(run_prediction_pipeline(a.limit, a.league, a.dry_run)))

if __name__ == '__main__':
    main()
