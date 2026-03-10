#!/usr/bin/env python3
# ═══════════════════════════════════════════════════════════════════════════════
# ║   TITAN-V4.46.6 预测管道 - 真实战力版                                        ║
# ║   REAL COMBAT VERSION - AUTHENTICATED WIN RATE 45% - NO LEAKAGE              ║
# ═══════════════════════════════════════════════════════════════════════════════
#
# 【严格约束】
# 1. 特征集: 11 维纯净特征 (与 TITAN_CORE_TRAIN.py 完全一致)
# 2. 身价补偿: 未来比赛使用历史 5 场均值
# 3. 除零防御: 所有除法操作都有保护
#
# 【特征对齐】
# - Elo (5): home_elo_pre, away_elo_pre, elo_diff, expected_home_win, expected_away_win
# - 身价 (3): log_home_squad_value, log_away_squad_value, home_mv_share
# - H2H (3): h2h_home_win_ratio, h2h_draw_ratio, h2h_avg_goal_diff
#
# @module scripts.ops.predict_pipeline
# @version V4.46.6-REAL-COMBAT
# @updated 2026-03-11

import argparse
import json
import logging
import math
import os
import sys
from dataclasses import dataclass, asdict
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
# 11 维纯净特征集 (与 TITAN_CORE_TRAIN.py 完全一致!)
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

@dataclass
class MatchPrediction:
    match_id: str; home_team: str; away_team: str; league: str; match_time: str
    home_prob: float; draw_prob: float; away_prob: float
    recommendation: str; confidence: float
    kelly_fraction: float; kelly_stake: float
    home_odds: Optional[float] = None; draw_odds: Optional[float] = None; away_odds: Optional[float] = None
    value_edge: Optional[float] = None; elo_diff: float = 0.0; mv_share: float = 0.5

@dataclass
class PredictionReport:
    generated_at: str; total_matches: int; predictions: List[Dict[str, Any]]; summary: Dict[str, Any]

def get_db_connection():
    import psycopg2
    from psycopg2.extras import RealDictCursor
    return psycopg2.connect(
        host=os.getenv('DB_HOST', 'host.docker.internal'), port=int(os.getenv('DB_PORT', 5432)),
        database=os.getenv('DB_NAME', 'football_db'), user=os.getenv('DB_USER', 'football_user'),
        password=os.getenv('DB_PASSWORD', 'football_pass'), cursor_factory=RealDictCursor
    )

def safe_float(v, d=0.0):
    try: return float(v) if v is not None else d
    except: return d

def safe_log10(v, d=18.0):
    try: return math.log10(v) if v and v > 0 else d
    except: return d

def parse_jsonb(d):
    if not d: return {}
    if isinstance(d, str):
        try: return json.loads(d)
        except: return {}
    return d if isinstance(d, dict) else {}

def get_team_avg_market_value(conn, team_name, limit=5):
    cur = conn.cursor()
    cur.execute("SELECT AVG(mv) as avg_mv FROM (SELECT (l.lineup_features->>'home_squad_value_eur')::numeric as mv FROM matches m INNER JOIN l3_features l ON m.match_id = l.match_id WHERE m.status = 'finished' AND m.home_team = %s AND (l.lineup_features->>'home_squad_value_eur')::numeric > 100000000 ORDER BY m.match_date DESC LIMIT %s) sub", (team_name, limit))
    r = cur.fetchone()
    if r and r['avg_mv']: cur.close(); return float(r['avg_mv'])
    cur.execute("SELECT AVG(mv) as avg_mv FROM (SELECT (l.lineup_features->>'away_squad_value_eur')::numeric as mv FROM matches m INNER JOIN l3_features l ON m.match_id = l.match_id WHERE m.status = 'finished' AND m.away_team = %s AND (l.lineup_features->>'away_squad_value_eur')::numeric > 100000000 ORDER BY m.match_date DESC LIMIT %s) sub", (team_name, limit))
    r = cur.fetchone()
    if r and r['avg_mv']: cur.close(); return float(r['avg_mv'])
    short_name = team_name[:6] if len(team_name) > 6 else team_name
    cur.execute("SELECT AVG(mv) as avg_mv FROM (SELECT (l.lineup_features->>'home_squad_value_eur')::numeric as mv FROM matches m INNER JOIN l3_features l ON m.match_id = l.match_id WHERE m.status = 'finished' AND m.home_team ILIKE %s AND (l.lineup_features->>'home_squad_value_eur')::numeric > 100000000 ORDER BY m.match_date DESC LIMIT %s) sub", (f'%{short_name}%', limit))
    r = cur.fetchone()
    cur.close()
    if r and r['avg_mv']: return float(r['avg_mv'])
    return None

def get_league_default_mv(league_name):
    return LEAGUE_DEFAULT_MV.get(league_name, 150_000_000)

def extract_features(elo_data, lineup_data, h2h_data, home_team=None, away_team=None, league_name=None, conn=None):
    f = {}; elo = parse_jsonb(elo_data); lineup = parse_jsonb(lineup_data); h2h = parse_jsonb(h2h_data)
    home_elo = safe_float(elo.get('home_elo_pre', elo.get('home_elo', 1500)), 1500)
    away_elo = safe_float(elo.get('away_elo_pre', elo.get('away_elo', 1500)), 1500)
    f['home_elo_pre'] = home_elo; f['away_elo_pre'] = away_elo
    f['elo_diff'] = safe_float(elo.get('elo_diff', home_elo - away_elo))
    f['expected_home_win'] = safe_float(elo.get('expected_home_win', 0.45))
    f['expected_away_win'] = safe_float(elo.get('expected_away_win', 0.30))
    home_mv = safe_float(lineup.get('home_squad_value_eur', 0), 0)
    away_mv = safe_float(lineup.get('away_squad_value_eur', 0), 0)
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
    f['h2h_home_win_ratio'] = safe_float(h2h.get('h2h_home_win_ratio', h2h.get('home_win_ratio', 0.4)), 0.4)
    f['h2h_draw_ratio'] = safe_float(h2h.get('h2h_draw_ratio', h2h.get('draw_ratio', 0.25)), 0.25)
    f['h2h_avg_goal_diff'] = safe_float(h2h.get('h2h_avg_goal_diff', h2h.get('avg_goal_diff', 0)), 0)
    return {k: f.get(k, DEFAULT_VALUES.get(k, 0.0)) for k in TITAN_COMBAT_FEATURES}

class TitanModelLoader:
    def __init__(self): self._model = None; self._scaler = None
    @property
    def is_loaded(self): return self._model is not None
    @property
    def has_scaler(self): return self._scaler is not None
    def load(self):
        mp = MODEL_DIR / "titan_v4466_real_combat.joblib"
        sp = MODEL_DIR / "titan_v4466_real_combat_scaler.joblib"
        if not mp.exists():
            for m, s in [("titan_v4466_combat_final.joblib", "titan_v4466_combat_final_scaler.joblib")]:
                if (MODEL_DIR / m).exists(): mp, sp = MODEL_DIR / m, MODEL_DIR / s; break
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
        logger.warning("未找到可用模型"); return False
    def predict(self, features):
        if not self.is_loaded: raise RuntimeError("模型未加载")
        # 使用 DataFrame 保留特征名称，消除 sklearn 警告
        X_df = pd.DataFrame([[features.get(n, DEFAULT_VALUES.get(n, 0.0)) for n in TITAN_COMBAT_FEATURES]],
                            columns=TITAN_COMBAT_FEATURES)
        if self.has_scaler: X = self._scaler.transform(X_df)
        else: X = X_df.values
        probs = self._model.predict_proba(X)[0]
        return probs[0], probs[1], probs[2]

def get_titan_model():
    m = TitanModelLoader(); m.load(); return m

def load_pending_matches(conn, limit=50, league=None):
    cur = conn.cursor()
    q = "SELECT m.match_id, m.home_team, m.away_team, m.league_name, m.match_date, l.elo_features, l.lineup_features, l.h2h_features FROM matches m INNER JOIN l3_features l ON m.match_id = l.match_id WHERE m.match_date > NOW() AND m.match_date < NOW() + INTERVAL '7 days' AND l.elo_features IS NOT NULL"
    params = []
    if league: q += " AND m.league_name = %s"; params.append(league)
    q += " ORDER BY m.match_date ASC LIMIT %s"; params.append(limit)
    cur.execute(q, params); rows = cur.fetchall(); cur.close(); return rows

def run_prediction_pipeline(limit=50, league=None, dry_run=False):
    logger.info("=" * 70 + "\n  TITAN-V4.46.6 预测管道 - 真实战力版\n  特征: 11 维 (Elo + 身价 + H2H)\n" + "=" * 70)
    titan = get_titan_model()
    if not titan.is_loaded: logger.error("模型加载失败"); return PredictionReport(datetime.now().isoformat(), 0, [], {'error': 'Model not loaded'})
    conn = get_db_connection(); matches = load_pending_matches(conn, limit, league)
    logger.info(f"加载 {len(matches)} 场待预测比赛")
    if not matches: conn.close(); return PredictionReport(datetime.now().isoformat(), 0, [], {})
    preds = []; hc = dc = ac = 0; tc = 0.0
    for m in matches:
        try:
            f = extract_features(m['elo_features'], m['lineup_features'], m['h2h_features'], m['home_team'], m['away_team'], m['league_name'], conn)
            ap, dp, hp = titan.predict(f)
            if hp >= dp and hp >= ap: rec, conf = 'HOME', hp
            elif dp >= ap: rec, conf = 'DRAW', dp
            else: rec, conf = 'AWAY', ap
            if rec == 'HOME': hc += 1
            elif rec == 'DRAW': dc += 1
            else: ac += 1
            tc += conf
            preds.append(asdict(MatchPrediction(m['match_id'], m['home_team'], m['away_team'], m['league_name'], str(m['match_date'])[:16], round(hp,4), round(dp,4), round(ap,4), rec, round(conf,4), 0.0, 0.0, None, None, None, None, f['elo_diff'], f['home_mv_share'])))
        except Exception as e: logger.error(f"预测失败 [{m['match_id']}]: {e}")
    t = len(preds)
    summary = {'home_count': hc, 'draw_count': dc, 'away_count': ac, 'home_pct': (hc/t*100) if t else 0, 'draw_pct': (dc/t*100) if t else 0, 'away_pct': (ac/t*100) if t else 0, 'avg_confidence': (tc/t) if t else 0, 'model_version': 'TITAN-V4.46.6-REAL-COMBAT', 'feature_count': 11}
    conn.close()
    return PredictionReport(datetime.now().isoformat(), t, preds, summary)

def format_report(r):
    lines = ['', '═'*70, '  TITAN-V4.46.6 预测报告 - 真实战力版', '═'*70, f'  生成时间: {r.generated_at}', f'  比赛数量: {r.total_matches}']
    s = r.summary; lines.extend([f'  预测分布: 主{s.get("home_count",0)} | 平{s.get("draw_count",0)} | 客{s.get("away_count",0)}', f'  平均置信度: {s.get("avg_confidence",0):.1%}'])
    if not r.predictions: lines.append('  无预测结果'); return '\n'.join(lines)
    sp = sorted(r.predictions, key=lambda x: x['confidence'], reverse=True)
    lines.extend(['', '─'*70, '  高置信度推荐 (Top 10)', '─'*70])
    for i, p in enumerate(sp[:10], 1):
        e = {'HOME': '🏠', 'DRAW': '🤝', 'AWAY': '✈️'}.get(p['recommendation'], '❓')
        lines.extend(['', f'  {i:2d}. {p["home_team"]:<20} vs {p["away_team"]:<20}', f'      联赛: {p["league"]:<20} | 时间: {p["match_time"]}', f'      概率: 主{p["home_prob"]:.1%} 平{p["draw_prob"]:.1%} 客{p["away_prob"]:.1%}', f'      Elo差: {p["elo_diff"]:+.1f} | 身价占比: {p["mv_share"]:.1%}', f'      推荐: {e} {p["recommendation"]} (置信度: {p["confidence"]:.1%})'])
    lines.extend(['', '═'*70, '  TITAN-V4.46.6 REAL COMBAT - 11 维特征对齐 - 身价补偿启用', '═'*70])
    return '\n'.join(lines)

def main():
    pa = argparse.ArgumentParser(description='TITAN-V4.46.6 预测管道')
    pa.add_argument('--limit', type=int, default=50); pa.add_argument('--league'); pa.add_argument('--dry-run', action='store_true')
    a = pa.parse_args()
    print(format_report(run_prediction_pipeline(a.limit, a.league, a.dry_run)))

if __name__ == '__main__':
    main()
