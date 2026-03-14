#!/usr/bin/env python3
"""Top 3 价值比赛详细分析"""
import sys, os, json, math
sys.path.insert(0, '/app')


os.environ['DB_HOST'] = 'host.docker.internal'
os.environ['DB_PORT'] = '5432'
os.environ['DB_NAME'] = 'football_db'
os.environ['DB_USER'] = 'football_user'

import psycopg2
import joblib
import numpy as np
import pandas as pd
from pathlib import Path

# 加载模型
model_dir = Path('/app/models')
model = joblib.load(model_dir / 'TITAN_CORE_V5_PROD.joblib')
scaler = joblib.load(model_dir / 'TITAN_CORE_V5_PROD_scaler.joblib')

TITAN_COMBAT_FEATURES = [
    'home_elo_pre', 'away_elo_pre', 'elo_diff', 'expected_home_win', 'expected_away_win',
    'log_home_squad_value', 'log_away_squad_value', 'home_mv_share',
    'h2h_home_win_ratio', 'h2h_draw_ratio', 'h2h_avg_goal_diff',
    'home_last5_xg_avg', 'away_last5_xg_avg', 'home_last5_win_rate', 'away_last5_win_rate',
    'home_last5_draw_rate', 'away_last5_draw_rate', 'rest_days_diff',
    'home_shot_conversion', 'away_shot_conversion', 'home_finishing_efficiency', 
    'away_finishing_efficiency', 'finishing_efficiency_diff',
    'home_draw_rate', 'away_draw_rate', 'home_draw_tendency', 'away_draw_tendency',
    'combined_draw_probability', 'match_stalemate_index', 'tactical_stalemate_index'
]

def parse_jsonb(val):
    if val is None: return {}
    if isinstance(val, dict): return val
    if isinstance(val, str): return json.loads(val)
    return {}

conn = psycopg2.connect(
    host='host.docker.internal', port=5432, database='football_db',
    user='football_user', password=os.getenv('DB_PASSWORD')
)
cur = conn.cursor()
cur.execute("""
    SELECT m.match_id, m.home_team, m.away_team, m.match_date, m.league_name,
        l.elo_features, l.golden_features, l.tactical_features,
        l.rolling_features, l.efficiency_features, l.draw_features,
        COALESCE(home_elo.elo_rating, 1500) as home_elo_real,
        COALESCE(away_elo.elo_rating, 1500) as away_elo_real
    FROM matches m INNER JOIN l3_features l ON m.match_id = l.match_id
    LEFT JOIN team_elo_ratings home_elo ON m.home_team = home_elo.team_name
    LEFT JOIN team_elo_ratings away_elo ON m.away_team = away_elo.team_name
    WHERE m.match_date >= NOW() AND m.match_date <= NOW() + INTERVAL '48 hours'
      AND m.status = 'Harvested' AND m.match_id LIKE '%_20252026_%'
""")
colnames = [desc[0] for desc in cur.description]
rows = cur.fetchall()
conn.close()

RESULT_NAMES = ['客胜', '平局', '主胜']
predictions = []

for row in rows:
    row_dict = {col: row[i] for i, col in enumerate(colnames)}
    elo = parse_jsonb(row_dict.get('elo_features'))
    golden = parse_jsonb(row_dict.get('golden_features'))
    tactical = parse_jsonb(row_dict.get('tactical_features'))
    rolling = parse_jsonb(row_dict.get('rolling_features'))
    efficiency = parse_jsonb(row_dict.get('efficiency_features'))
    draw = parse_jsonb(row_dict.get('draw_features'))
    
    home_elo = float(row_dict.get('home_elo_real', 1500))
    away_elo = float(row_dict.get('away_elo_real', 1500))
    
    f = {
        'home_elo_pre': home_elo, 'away_elo_pre': away_elo, 'elo_diff': home_elo - away_elo,
        'expected_home_win': float(elo.get('expected_home_win', 0.45)),
        'expected_away_win': float(elo.get('expected_away_win', 0.30)),
        'h2h_home_win_ratio': float(tactical.get('h2h_home_win_ratio', 0.4)),
        'h2h_draw_ratio': float(tactical.get('h2h_draw_ratio', 0.25)),
        'h2h_avg_goal_diff': float(tactical.get('h2h_avg_goal_diff', 0.0)),
        'home_last5_xg_avg': float(rolling.get('home_last5_xg_avg', 0.0)),
        'away_last5_xg_avg': float(rolling.get('away_last5_xg_avg', 0.0)),
        'home_last5_win_rate': float(rolling.get('home_last5_win_rate', 0.0)),
        'away_last5_win_rate': float(rolling.get('away_last5_win_rate', 0.0)),
        'home_last5_draw_rate': float(rolling.get('home_last5_draw_rate', 0.0)),
        'away_last5_draw_rate': float(rolling.get('away_last5_draw_rate', 0.0)),
        'rest_days_diff': float(rolling.get('rest_days_diff', 0.0)),
        'home_shot_conversion': float(efficiency.get('home_shot_conversion', 0.0)),
        'away_shot_conversion': float(efficiency.get('away_shot_conversion', 0.0)),
        'home_finishing_efficiency': float(efficiency.get('home_finishing_efficiency', 0.0)),
        'away_finishing_efficiency': float(efficiency.get('away_finishing_efficiency', 0.0)),
        'finishing_efficiency_diff': float(efficiency.get('finishing_efficiency_diff', 0.0)),
        'home_draw_rate': float(draw.get('home_draw_rate', 0.0)),
        'away_draw_rate': float(draw.get('away_draw_rate', 0.0)),
        'home_draw_tendency': float(draw.get('home_draw_tendency', 0.0)),
        'away_draw_tendency': float(draw.get('away_draw_tendency', 0.0)),
        'combined_draw_probability': float(draw.get('combined_draw_probability', 0.0)),
        'match_stalemate_index': float(draw.get('match_stalemate_index', 0.0)),
        'tactical_stalemate_index': float(draw.get('tactical_stalemate_index', 0.0))
    }
    
    home_mv = float(golden.get('home_market_value_total', 1e8))
    away_mv = float(golden.get('away_market_value_total', 1e8))
    f['log_home_squad_value'] = math.log10(home_mv) if home_mv > 0 else 18.0
    f['log_away_squad_value'] = math.log10(away_mv) if away_mv > 0 else 18.0
    total_mv = home_mv + away_mv
    f['home_mv_share'] = home_mv / total_mv if total_mv > 0 else 0.5
    
    X = pd.DataFrame([f], columns=TITAN_COMBAT_FEATURES)
    X_scaled = scaler.transform(X)
    proba = model.predict_proba(X_scaled)[0]
    pred_class = np.argmax(proba)
    max_proba = np.max(proba)
    
    if max_proba >= 0.58:
        key_factors = []
        if f['h2h_home_win_ratio'] > 0.6: key_factors.append("H2H压制")
        if abs(f['elo_diff']) > 100: key_factors.append("战力代差" if f['elo_diff'] > 0 else "战力劣势")
        if f['home_last5_win_rate'] > 0.6: key_factors.append("状态火热")
        if f['home_last5_xg_avg'] > 1.5: key_factors.append("进攻强劲")
        if f['match_stalemate_index'] > 0.8: key_factors.append("僵局风险")
        if f['home_mv_share'] > 0.65: key_factors.append("身价碾压")
        
        p, b = max_proba, 0.8
        kelly = max(0.01, min(0.025, ((p * (1 + b) - 1) / b) * 0.25))
        
        predictions.append({
            'home_team': row_dict['home_team'], 'away_team': row_dict['away_team'],
            'match_date': row_dict['match_date'], 'league': row_dict['league_name'],
            'prediction': RESULT_NAMES[pred_class], 'confidence': max_proba,
            'elo_diff': f['elo_diff'], 'proba_home': proba[2], 'proba_draw': proba[1], 'proba_away': proba[0],
            'key_factors': key_factors[:2], 'kelly_stake': kelly,
            'home_elo': home_elo, 'away_elo': away_elo,
            'home_mv': home_mv / 1e6, 'away_mv': away_mv / 1e6,
            'home_win_rate': f['home_last5_win_rate'], 'away_win_rate': f['away_last5_win_rate'],
            'h2h_ratio': f['h2h_home_win_ratio']
        })

predictions.sort(key=lambda x: x['confidence'], reverse=True)

print("""
╔══════════════════════════════════════════════════════════════════════════════════════════════════════╗
║                    TITAN V5.0 周末收割作战简报 - Top 3 黄金价值信号                      ║
╚══════════════════════════════════════════════════════════════════════════════════════════════════════╝
""")

for i, p in enumerate(predictions[:3], 1):
    match_time = p['match_date'].strftime('%m月%d日 %H:%M') if hasattr(p['match_date'], 'strftime') else str(p['match_date'])
    elo_sign = "+" if p['elo_diff'] > 0 else ""
    mv_share = p['home_mv'] / (p['home_mv'] + p['away_mv']) * 100 if (p['home_mv'] + p['away_mv']) > 0 else 50
    
    print(f"""
┌──────────────────────────────────────────────────────────────────────────────────────────────────────┐
│ 【排名 #{i}】 {p['home_team']} vs {p['away_team']:<45} │
├──────────────────────────────────────────────────────────────────────────────────────────────────────┤
│  联赛: {p['league']:<20}  时间: {match_time:<25}                      │
│  预测: {p['prediction']:<6}           置信度: {p['confidence']*100:.1f}% (0.58阈值: 68.94%预期胜率)    │
├──────────────────────────────────────────────────────────────────────────────────────────────────────┤
│  核心数据指标:                                                                                       │
│     战力差(ELO): {elo_sign}{p['elo_diff']:.0f} ({p['home_elo']:.0f} vs {p['away_elo']:.0f})                            │
│     阵容身价: {p['home_mv']:.0f}M vs {p['away_mv']:.0f}M (主队占比{mv_share:.1f}%)                     │
│     近期状态: 主队近5场胜率{p['home_win_rate']*100:.0f}% | 客队近5场胜率{p['away_win_rate']*100:.0f}%                      │
│     H2H优势: 主队历史胜率{p['h2h_ratio']*100:.0f}%                                                   │
├──────────────────────────────────────────────────────────────────────────────────────────────────────┤
│  关键因子: {' | '.join(p['key_factors']) if p['key_factors'] else '综合优势':<50}              │
│  概率分布: 主胜 {p['proba_home']*100:.1f}% | 平局 {p['proba_draw']*100:.1f}% | 客胜 {p['proba_away']*100:.1f}%                      │
│  凯利仓位: {p['kelly_stake']*100:.1f}% (基于假设赔率1.80)                                             │
│  盈亏平衡: 需要赔率 > {1/p['confidence']:.2f}                                                         │
└──────────────────────────────────────────────────────────────────────────────────────────────────────┘""")

avg_conf = sum(p['confidence'] for p in predictions[:3]) / 3 if predictions else 0
print(f"""
═══════════════════════════════════════════════════════════════════════════════════════════════════════

执行建议:
   1. 在临场前1小时确认最终阵容，检查主力伤病/停赛情况
   2. 寻找 {1/predictions[0]['confidence']:.2f} 以上赔率进行投注
   3. 严格按照凯利仓位({predictions[0]['kelly_stake']*100:.1f}%)执行，禁止情绪化加仓
   4. Top 3 信号的预期胜率为 {avg_conf*100:.1f}% (目标: 68.94%)

═══════════════════════════════════════════════════════════════════════════════════════════════════════
""")
